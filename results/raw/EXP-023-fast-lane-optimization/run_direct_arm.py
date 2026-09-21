#!/usr/bin/env python3
"""EXP-023 direct MiniCPM arm runner using the managed FAST port.

The shell invokes this with a model path/context/KV settings.  It leaves raw
requests, responses, metric snapshots and OS samples in a fresh arm dir.
"""
from __future__ import annotations
import argparse, json, os, subprocess, time, urllib.request
from pathlib import Path

ROOT = Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-023-fast-lane-optimization')
MANAGER = '/Users/<user>/.hermes/bin/hermes-local-model'
BASE = 'http://127.0.0.1:8901'


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, text=True, capture_output=True, check=False).stdout + subprocess.run(['true'], text=True, capture_output=True).stdout


def shell(cmd: str) -> str:
    return subprocess.run(['/bin/bash', '-lc', cmd], text=True, capture_output=True).stdout


def request(payload: dict) -> tuple[dict, float]:
    req = urllib.request.Request(BASE + '/v1/chat/completions', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    t = time.monotonic()
    with urllib.request.urlopen(req, timeout=480) as res:
        return json.load(res), time.monotonic() - t


def snap(label: str, arm: Path) -> None:
    pid = shell("lsof -tiTCP:8901 -sTCP:LISTEN | head -n1").strip()
    text = [f'label={label}', f'pid={pid}', shell('sysctl vm.swapusage').strip(), shell('vm_stat'), shell('memory_pressure')]
    if pid:
        text.append(shell(f'ps -p {pid} -o pid=,rss=,etime=,command='))
        text.append(shell(f'footprint {pid} 2>&1 || true'))
    try:
        with urllib.request.urlopen(BASE + '/metrics', timeout=10) as res:
            text.append(res.read().decode())
    except Exception as e: text.append(f'metrics_error={e!r}')
    (arm / f'{label}-snapshot.txt').write_text('\n'.join(text))


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument('--name', required=True); ap.add_argument('--model', required=True); ap.add_argument('--context',type=int,required=True); ap.add_argument('--kv-k',default='f16');ap.add_argument('--kv-v',default='f16')
    a=ap.parse_args(); arm=ROOT/'raw'/'arms'/a.name; arm.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.update(HERMES_FAST_GGUF=a.model,HERMES_FAST_CONTEXT=str(a.context),HERMES_FAST_KV_K=a.kv_k,HERMES_FAST_KV_V=a.kv_v)
    baseline={'swap':shell('sysctl vm.swapusage'),'vm_stat':shell('vm_stat'),'memory_pressure':shell('memory_pressure')}
    # Model/context/KV are variables of this arm.  A healthy previous FAST
    # listener must be stopped first; `ensure fast` is intentionally idempotent.
    stopped=subprocess.run([MANAGER,'stop','fast'],text=True,capture_output=True)
    (arm/'stop-previous.txt').write_text(stopped.stdout+stopped.stderr)
    t=time.monotonic(); r=subprocess.run([MANAGER,'ensure','fast'],env=env,text=True,capture_output=True)
    (arm/'launch.txt').write_text(r.stdout+r.stderr); (arm/'baseline.json').write_text(json.dumps(baseline,indent=2))
    if r.returncode: raise SystemExit(f'launch failed: {r.stderr}')
    load_s=time.monotonic()-t; snap('loaded-idle',arm)
    tool={"type":"function","function":{"name":"get_git_status","description":"Return git status.","parameters":{"type":"object","properties":{},"additionalProperties":False}}}
    common={'model':'minicpm-fast','temperature':0,'max_tokens':180}
    tests=[
      ('factual', {**common,'messages':[{'role':'user','content':'What is the capital of France? Reply with one word.'}]}),
      ('no_think', {**common,'messages':[{'role':'user','content':'What is 7 times 8? Reply with only the number.'}],'chat_template_kwargs':{'enable_thinking':False}}),
      ('think', {**common,'messages':[{'role':'user','content':'What is 7 times 8? Briefly reason then give the answer.'}],'chat_template_kwargs':{'enable_thinking':True}}),
      ('tool', {**common,'messages':[{'role':'user','content':'Call get_git_status now.'}],'tools':[tool],'tool_choice':'auto'}),
      ('structured', {**common,'messages':[{'role':'user','content':'Return only valid JSON: {"route":"FAST","confidence":0.9}'}], 'response_format':{'type':'json_object'}}),
      ('compression', {**common,'max_tokens':360,'messages':[{'role':'user','content':'Compress this preserving every fact: Decision: use MiniCPM. TODO: test /srv/app/a.py. Command: git status. Error: EADDRINUSE 8901. Constraint: never run two models. User prefers concise reports. Measurement: 47 tok/s and 1.56GB.'}]}),
    ]
    results=[]
    for name,p in tests:
      try:
       out,sec=request(p);results.append({'name':name,'seconds':round(sec,4),'response':out})
      except Exception as e: results.append({'name':name,'error':repr(e)})
    # A populated context probe is generated within the allocated window; runtime reports prompt_n.
    filler=' '.join(f'item{i}: stable filler token sequence' for i in range(max(1,a.context//22)))
    probe={**common,'max_tokens':12,'messages':[{'role':'user','content':f'{filler}\nWhat marker follows item7? Reply only item7.'}]}
    try:
      out,sec=request(probe);results.append({'name':'populated_context','seconds':round(sec,4),'response':out})
    except Exception as e: results.append({'name':'populated_context','error':repr(e)})
    (arm/'results.json').write_text(json.dumps({'arm':vars(a),'load_seconds':round(load_s,3),'results':results},indent=2))
    snap('post-work',arm)
    print(json.dumps({'arm':a.name,'load_seconds':round(load_s,3),'result_count':len(results)}))

if __name__=='__main__': main()
