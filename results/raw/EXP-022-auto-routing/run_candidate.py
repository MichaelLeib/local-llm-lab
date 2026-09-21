#!/usr/bin/env python3
"""One-model-at-a-time loopback benchmark for EXP-022.

Uses only the already-installed llama.cpp server and writes raw JSON evidence.
The caller must have stopped managed lanes first. This supervisor owns exactly
one child server and terminates it in finally.
"""
from __future__ import annotations
import argparse, json, os, signal, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-022-auto-routing')
LLAMA = '/opt/homebrew/bin/llama-server'


def command(args: list[str]) -> str:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout


def vm_snapshot() -> dict[str, str]:
    return {
        'swapusage': command(['sysctl', 'vm.swapusage']).strip(),
        'memory_pressure': command(['memory_pressure']).strip(),
        'vm_stat': command(['vm_stat']).strip(),
    }


def rss(pid: int) -> str:
    return command(['ps', '-o', 'pid=,rss=,etime=,command=', '-p', str(pid)]).strip()


def get(url: str, timeout: float = 5) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def post(url: str, data: dict, timeout: float = 180) -> tuple[dict, float]:
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.loads(r.read().decode())
    return payload, time.monotonic() - started


def run_arm(name: str, model: Path, port: int) -> int:
    out = ROOT / 'raw' / name
    out.mkdir(parents=True, exist_ok=True)
    result: dict = {'candidate': name, 'model': str(model), 'port': port, 'started_at_epoch': time.time(), 'before': vm_snapshot()}
    log = (out / 'server.log').open('w')
    proc = subprocess.Popen([
        LLAMA, '-m', str(model), '--host', '127.0.0.1', '--port', str(port), '-ngl', '99', '-c', '8192',
        '--jinja', '--flash-attn', 'on', '--no-warmup', '--metrics', '--alias', name,
    ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    result['pid'] = proc.pid
    try:
        deadline = time.monotonic() + 180
        health = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f'server exited {proc.returncode}')
            try:
                health = get(f'http://127.0.0.1:{port}/health', 2)
                if health.get('status') == 'ok': break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError('health timeout')
        result['load_seconds'] = round(time.monotonic() - (deadline - 180), 3)
        result['health'] = health
        result['models'] = get(f'http://127.0.0.1:{port}/v1/models')
        result['props'] = get(f'http://127.0.0.1:{port}/props')
        result['loaded_idle_rss'] = rss(proc.pid)
        result['loaded_idle'] = vm_snapshot()
        base = f'http://127.0.0.1:{port}/v1/chat/completions'
        direct = {
            'model': name, 'messages': [{'role':'user','content':'Answer with only the capital of France.'}],
            'temperature': 0, 'max_tokens': 32, 'stream': False,
            'chat_template_kwargs': {'enable_thinking': False},
        }
        response, elapsed = post(base, direct)
        result['direct_no_think'] = {'seconds': elapsed, 'response': response}
        # Warm repeat enables server-side prompt reuse when supported.
        response2, elapsed2 = post(base, direct)
        result['warm_direct'] = {'seconds': elapsed2, 'response': response2}
        tools = [{
            'type': 'function',
            'function': {'name': 'get_git_status', 'description': 'Return branch and clean/dirty status for a repository.',
                         'parameters': {'type': 'object', 'properties': {'path': {'type':'string'}}, 'required':['path']}}
        }]
        tool_req = {
            'model': name,
            'messages': [{'role':'user','content':'Use get_git_status for /tmp/repo. Do not guess and do not answer until you have called the tool.'}],
            'tools': tools, 'tool_choice': 'auto', 'temperature': 0, 'max_tokens': 256,
            'chat_template_kwargs': {'enable_thinking': False},
        }
        tool_response, tool_elapsed = post(base, tool_req)
        result['tool_call'] = {'seconds': tool_elapsed, 'response': tool_response}
        msg = ((tool_response.get('choices') or [{}])[0].get('message') or {})
        calls = msg.get('tool_calls') or []
        if calls:
            continuation_messages = tool_req['messages'] + [msg]
            for call in calls:
                continuation_messages.append({'role':'tool', 'tool_call_id':call['id'], 'content':'{"branch":"main","dirty":false}'})
            final, final_elapsed = post(base, {
                'model': name, 'messages': continuation_messages, 'tools': tools,
                'temperature': 0, 'max_tokens': 128, 'chat_template_kwargs': {'enable_thinking': False},
            })
            result['tool_continuation'] = {'seconds': final_elapsed, 'response': final}
        result['active_rss'] = rss(proc.pid)
        try:
            result['metrics'] = urllib.request.urlopen(f'http://127.0.0.1:{port}/metrics', timeout=5).read().decode()
        except Exception as exc:
            result['metrics_error'] = repr(exc)
        result['after'] = vm_snapshot()
        result['outcome'] = 'completed'
    except Exception as exc:
        result['outcome'] = 'runtime_failure'
        result['error'] = repr(exc)
        result['after'] = vm_snapshot()
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=30)
            except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL)
        log.close()
        result['exit_code'] = proc.returncode
        result['post_stop'] = vm_snapshot()
        (out / 'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(json.dumps({'candidate': name, 'outcome': result.get('outcome'), 'error': result.get('error'), 'exit_code': proc.returncode}, indent=2))
    return 0 if result.get('outcome') == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    sys.exit(run_arm(args.name, Path(args.model), args.port))
