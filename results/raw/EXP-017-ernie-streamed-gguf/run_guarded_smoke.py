#!/usr/bin/env python3
"""Run one guarded streamed-ERNIE smoke arm and preserve raw telemetry."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

EXP = Path.home() / "HermesProjects/Local-LLM-Lab/results/raw/EXP-017-ernie-streamed-gguf"
BIN = EXP / "source/llama.cpp-moe-streaming/build-exp017/bin/llama-cli"
MODEL = Path.home() / "HermesProjects/Local-LLM-Lab/results/raw/EXP-016-small-moe-feasibility/ernie/gguf/model/ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf"
OUT = EXP / "smoke-18slots-ctx512-24tok"
OUT.mkdir(parents=True, exist_ok=True)

cmd = [
    str(BIN), "-m", str(MODEL),
    "--moe-stream-cache", "18s", "--moe-stream-io-threads", "2", "--moe-stream-direct",
    "--no-mmap", "--no-warmup", "--fit", "off", "-ngl", "99", "-c", "512", "-b", "512", "-ub", "1",
    "-n", "24", "--temp", "0", "--seed", "1234", "--single-turn", "--simple-io",
    "-p", "Return the single word PASS.",
]
(OUT / "command.json").write_text(json.dumps(cmd, indent=2) + "\n")

def run_text(args: list[str]) -> str:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout

def snapshot(label: str) -> dict:
    vm = run_text(["vm_stat"])
    pressure = run_text(["memory_pressure"])
    swap = run_text(["sysctl", "vm.swapusage"])
    proc = run_text(["ps", "-axo", "pid=,rss=,etime=,command="])
    return {"timestamp": time.time(), "label": label, "vm_stat": vm, "memory_pressure": pressure, "swap": swap, "processes": proc}

baseline = snapshot("before")
(OUT / "before.json").write_text(json.dumps(baseline, indent=2) + "\n")
with (OUT / "run.log").open("w") as log:
    log.write("command=" + " ".join(cmd) + "\n")
    log.flush()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    samples = []
    aborted = None
    while proc.poll() is None:
        s = snapshot("active")
        s["pid"] = proc.pid
        samples.append(s)
        # Protect the host only at a severe objective threshold. Existing swap is a baseline,
        # so use free-memory state rather than an absolute swap value.
        text = s["memory_pressure"]
        free = None
        for line in text.splitlines():
            if "System-wide memory free percentage:" in line:
                free = int(line.split(":", 1)[1].strip().rstrip("%"))
                break
        if free is not None and free < 6:
            aborted = {"reason": "free_memory_below_6_percent", "free_percent": free, "timestamp": time.time()}
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
            break
        time.sleep(2)
    code = proc.wait()
(OUT / "samples.json").write_text(json.dumps(samples, indent=2) + "\n")
(OUT / "result.json").write_text(json.dumps({"exit_code": code, "aborted": aborted, "finished_at": time.time()}, indent=2) + "\n")
(OUT / "after.json").write_text(json.dumps(snapshot("after"), indent=2) + "\n")
print(json.dumps({"exit_code": code, "aborted": aborted, "out": str(OUT)}, indent=2))
