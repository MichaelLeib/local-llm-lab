#!/usr/bin/env python3
"""EXP-008 isolated FP16 context envelope runner.

Runs one max-context arm at a time, sequentially: cold CLI telemetry then a
fresh loopback server prefix-cache probe. It never starts if another local
model is resident and terminates the arm if swap grows beyond the configured
per-arm budget. It writes all raw output to results/raw/EXP-008/runs/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path.home() / "HermesProjects/Local-LLM-Lab"
EXP = ROOT / "results/raw/EXP-008"
SOURCE = EXP / "source/slipstream"
MODEL = ROOT / "results/raw/EXP-005/model/qwen36.gturbo"
SNAPSHOT = ROOT / "tools/collect-memory-snapshot.py"
NEEDLE = "EXP008_NEEDLE_AURORA_7391"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run(command: list[str], timeout: float = 30.0) -> dict[str, Any]:
    try:
        p = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        return {"command": command, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "returncode": None, "stdout": exc.stdout or "", "stderr": (exc.stderr or "") + "timeout"}


def swap_mib() -> float | None:
    text = run(["/usr/sbin/sysctl", "vm.swapusage"])["stdout"]
    match = re.search(r"used =\s*([0-9.]+)M", text)
    return float(match.group(1)) if match else None


def free_percent() -> float | None:
    result = run(["/usr/bin/memory_pressure", "-S", "-l", "warn", "-Q"])
    match = re.search(r"System-wide memory free percentage:\s*([0-9.]+)%", result["stdout"] + result["stderr"])
    return float(match.group(1)) if match else None


def model_processes() -> list[str]:
    # Inspect the executable column first. Do not substring-match the full
    # command: Hermes terminal wrappers legitimately contain this experiment's
    # source path and would otherwise be misclassified as a resident model.
    output = run(["/bin/ps", "-axo", "pid=,comm=,command="])["stdout"]
    exact = {"slipstream", "slipstream-server", "llama-server", "TinyTitanCLI", "TinyTitanServer", "rapid-mlx"}
    conflicts: list[str] = []
    for line in output.splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) != 3:
            continue
        executable = Path(fields[1]).name
        command = fields[2]
        if executable in exact or re.search(r"(?:^|/)mlx_lm(?:\.server)?(?:\s|$)|rapid_mlx", command):
            conflicts.append(line.strip())
    return conflicts


def capture(outdir: Path, label: str, pid: int | None = None) -> dict[str, Any]:
    target = outdir / f"{label}.json"
    command = [sys.executable, str(SNAPSHOT), "--experiment", "EXP-008", "--label", label, "--output", str(target)]
    if pid is not None:
        command += ["--pid", str(pid)]
    result = run(command, timeout=45)
    return {"snapshot": str(target), "collector": result, "swap_mib": swap_mib(), "free_percent": free_percent()}


def terminate(process: subprocess.Popen[str], grace: float = 15.0) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def monitor(process: subprocess.Popen[str], outdir: Path, label: str, baseline_swap: float | None, stop_delta_mib: float, active: Callable[[], bool] | None = None) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    stopped = False
    while process.poll() is None and (active is None or active()):
        row = capture(outdir, f"{label}-sample-{len(rows):04d}", process.pid)
        row["captured_at"] = now()
        delta = None if baseline_swap is None or row["swap_mib"] is None else row["swap_mib"] - baseline_swap
        row["swap_delta_mib"] = delta
        rows.append(row)
        if delta is not None and delta > stop_delta_mib:
            row["stop_reason"] = f"swap growth {delta:.2f} MiB exceeds {stop_delta_mib:.2f} MiB"
            terminate(process)
            stopped = True
            break
        time.sleep(5)
    return rows, stopped


def make_prompt(context: int, fill_fraction: float) -> str:
    # Qwen's tokenizer normally emits one token for leading-space `x`; the
    # actual token count from runtime usage/footer is preserved as authoritative.
    filler = " x" * int(context * fill_fraction)
    return f"{filler}\n\nArchive verification marker: {NEEDLE}\n\nReply with exactly the archive verification marker."


def parse_cli_footer(text: str) -> dict[str, Any]:
    match = re.search(r"\[stop=(\S+) prefill=(\d+)tok/([0-9.]+)s new=(\d+)tok decode=([0-9.]+)s tok/s=([0-9.]+)\]", text)
    if not match:
        return {}
    return {"stop": match.group(1), "prompt_tokens": int(match.group(2)), "prefill_seconds": float(match.group(3)), "new_tokens": int(match.group(4)), "decode_seconds": float(match.group(5)), "decode_tok_s": float(match.group(6))}


def run_cli(binary: Path, context: int, slots: int, prompt_file: Path, outdir: Path, baseline_swap: float | None, stop_delta_mib: float) -> dict[str, Any]:
    env = os.environ.copy()
    env["TURBO_FIELDFARE_PHASES"] = "1"
    command = [str(binary), "--model", str(MODEL), "--prompt", prompt_file.read_text(), "--max-new", "64", "--max-context", str(context), "--temperature", "0", "--seed", "12345", "--expert-cache-slots", str(slots), "--expert-cache-policy", "lfu-aging", "--prefill-chunk", "auto"]
    stdout_path, stderr_path = outdir / "cli.stdout.txt", outdir / "cli.stderr.txt"
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        started = now(); t0 = time.monotonic()
        process = subprocess.Popen(command, text=True, stdout=stdout, stderr=stderr, env=env)
        samples, stopped = monitor(process, outdir, "cli", baseline_swap, stop_delta_mib)
        returncode = process.wait()
    stderr_text = stderr_path.read_text(errors="replace")
    output_text = stdout_path.read_text(errors="replace")
    return {"command": command, "started_at": started, "finished_at": now(), "wall_seconds": round(time.monotonic() - t0, 3), "returncode": returncode, "stopped_for_swap": stopped, "samples": samples, "footer": parse_cli_footer(stderr_text), "correctness_contains_needle": NEEDLE in output_text, "stdout_path": str(stdout_path), "stderr_path": str(stderr_path)}


def wait_port(port: int, process: subprocess.Popen[str], timeout: float = 240.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited early with {process.returncode}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(1)
    raise TimeoutError(f"server did not bind 127.0.0.1:{port} within {timeout}s")


def http_request(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(payload).encode()
    request = urllib.request.Request(url, data=raw, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=7200) as response:
        body = response.read().decode("utf-8", errors="replace")
        return {"status": response.status, "headers": dict(response.headers.items()), "body": body, "json": json.loads(body)}


def run_server(binary: Path, context: int, slots: int, prompt: str, outdir: Path, baseline_swap: float | None, stop_delta_mib: float, port: int) -> dict[str, Any]:
    command = [str(binary), "--model", str(MODEL), "--model-id", "qwen3.6-35b-a3b-exp008", "--port", str(port), "--max-context", str(context), "--queue-limit", "1", "--prompt-cache-mode", "single-prefix", "--expert-cache-slots", str(slots), "--expert-cache-policy", "lfu-aging"]
    stdout_path, stderr_path = outdir / "server.stdout.txt", outdir / "server.stderr.txt"
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(command, text=True, stdout=stdout, stderr=stderr)
        try:
            wait_port(port, process)
            loaded_idle = capture(outdir, "server-loaded-idle", process.pid)
            payload = {"model": "qwen3.6-35b-a3b-exp008", "messages": [{"role": "user", "content": prompt}], "max_tokens": 64, "temperature": 0, "seed": 12345, "stream": False}
            results: list[dict[str, Any]] = []
            for index in range(2):
                if index == 1 and results and "response" in results[0]:
                    first_json = results[0]["response"].get("json", {})
                    first_choices = first_json.get("choices", [])
                    first_content = first_choices[0].get("message", {}).get("content", "") if first_choices else ""
                    payload = {"model": "qwen3.6-35b-a3b-exp008", "messages": [{"role": "user", "content": prompt}, {"role": "assistant", "content": first_content}, {"role": "user", "content": "Repeat exactly the archive verification marker."}], "max_tokens": 64, "temperature": 0, "seed": 12345, "stream": False}
                box: dict[str, Any] = {}
                def call() -> None:
                    try: box["response"] = http_request(f"http://127.0.0.1:{port}/v1/chat/completions", payload)
                    except BaseException as exc: box["error"] = repr(exc)
                thread = threading.Thread(target=call, daemon=True)
                before = capture(outdir, f"server-request-{index + 1}-before", process.pid)
                started = now(); t0 = time.monotonic(); thread.start()
                samples, stopped = monitor(process, outdir, f"server-request-{index + 1}", baseline_swap, stop_delta_mib, thread.is_alive)
                thread.join(timeout=5)
                after = capture(outdir, f"server-request-{index + 1}-after", process.pid if process.poll() is None else None)
                row = {"request_index": index + 1, "started_at": started, "finished_at": now(), "wall_seconds": round(time.monotonic()-t0, 3), "before": before, "after": after, "samples": samples, "stopped_for_swap": stopped, **box}
                if "response" in row:
                    response_json = row["response"].get("json", {})
                    row["usage"] = response_json.get("usage")
                    choices = response_json.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    row["correctness_contains_needle"] = NEEDLE in content
                results.append(row)
                if stopped or process.poll() is not None: break
            return {"command": command, "loaded_idle": loaded_idle, "requests": results}
        finally:
            terminate(process)
            capture(outdir, "server-post-stop")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=int, choices=(16384, 32768, 65536), required=True)
    parser.add_argument("--expert-cache-slots", type=int, choices=(8, 16, 24, 32, 48, 64, 96, 128, 192, 256), default=16)
    parser.add_argument("--fill-fraction", type=float, default=0.78)
    parser.add_argument("--swap-growth-stop-mib", type=float, default=256.0)
    parser.add_argument("--port", type=int, default=18080)

    args = parser.parse_args()
    if not 0.1 <= args.fill_fraction <= 0.9:
        raise SystemExit("--fill-fraction must be within [0.1, 0.9]")
    binary_cli = SOURCE / ".build/release/slipstream"
    binary_server = SOURCE / ".build/release/slipstream-server"
    missing = [str(p) for p in (MODEL, SNAPSHOT, binary_cli, binary_server) if not p.exists()]
    if missing: raise SystemExit("missing prerequisite(s): " + ", ".join(missing))
    conflicts = model_processes()
    if conflicts: raise SystemExit("refusing: local model process already present: " + " | ".join(conflicts))
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%SZ")
    outdir = EXP / "runs" / f"ctx-{args.context}-slots-{args.expert_cache_slots}-{stamp}"
    outdir.mkdir(parents=True)
    prompt = make_prompt(args.context, args.fill_fraction)
    prompt_file = outdir / "prompt.txt"; prompt_file.write_text(prompt)
    baseline = capture(outdir, "baseline")
    record: dict[str, Any] = {"schema": "exp008.phase1.v1", "experiment": "EXP-008", "started_at": now(), "context": args.context, "fill_fraction": args.fill_fraction, "prompt_bytes": len(prompt.encode()), "needle": NEEDLE, "config": {"expert_cache_slots": args.expert_cache_slots, "expert_cache_policy": "lfu-aging", "prefill_chunk": "auto", "temperature": 0, "seed": 12345, "kv": "FP16", "source_commit": "3a892465729406944778a24064664d817617f558"}, "baseline": baseline}
    baseline_swap = baseline["swap_mib"]
    try:
        record["cli"] = run_cli(binary_cli, args.context, args.expert_cache_slots, prompt_file, outdir, baseline_swap, args.swap_growth_stop_mib)
        if record["cli"]["stopped_for_swap"]:
            record["status"] = "stopped_for_swap"
        elif record["cli"]["returncode"] != 0:
            record["status"] = "cli_failure"
        else:
            record["server"] = run_server(binary_server, args.context, args.expert_cache_slots, prompt, outdir, baseline_swap, args.swap_growth_stop_mib, args.port)
            server_stopped = any(row.get("stopped_for_swap") for row in record["server"].get("requests", []))
            server_errors = any("error" in row for row in record["server"].get("requests", []))
            record["status"] = "stopped_for_swap" if server_stopped else ("server_failure" if server_errors else "completed")
    except BaseException as exc:
        record["status"] = "failed_or_stopped"; record["error"] = repr(exc)
    finally:
        record["finished_at"] = now()
        record["post_run"] = capture(outdir, "post-run")
        (outdir / "summary.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "outdir": str(outdir)}, indent=2))
    return 0 if record["status"] == "completed" else 1

if __name__ == "__main__":
    raise SystemExit(main())
