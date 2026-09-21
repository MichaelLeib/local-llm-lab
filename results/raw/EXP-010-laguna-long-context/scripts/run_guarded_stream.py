#!/usr/bin/env python3
"""Run one Laguna streaming arm with an arm-local hard swap guard.

The script owns exactly one child process. It does not start/stop a managed lane,
modify global configuration, or advance to another context/cache configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWAP_RE = re.compile(r"used =\s*([0-9.]+)M")
FREE_RE = re.compile(r"free percentage:\s*(\d+)%")


def capture(cmd: list[str], timeout: int = 20) -> str:
    try:
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout,
                              check=False).stdout
    except Exception as exc:
        return f"<capture error: {exc}>\n"


def swap_mib() -> float | None:
    text = capture(["sysctl", "vm.swapusage"])
    match = SWAP_RE.search(text)
    return float(match.group(1)) if match else None


def pressure_free_pct() -> int | None:
    text = capture(["memory_pressure", "-Q"])
    match = FREE_RE.search(text)
    return int(match.group(1)) if match else None


def snapshot(pid: int, label: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    pressure = capture(["memory_pressure", "-Q"])
    swap = capture(["sysctl", "vm.swapusage"])
    fp = capture(["footprint", "-p", str(pid)]) if pid > 0 else ""
    ps = capture(["ps", "-o", "pid=,ppid=,rss=,etime=,command=", "-p", str(pid)])
    vm = capture(["vm_stat"])
    return {
        "at": now,
        "label": label,
        "pid": pid,
        "swap_mib": float(SWAP_RE.search(swap).group(1)) if SWAP_RE.search(swap) else None,
        "memory_free_pct": int(FREE_RE.search(pressure).group(1)) if FREE_RE.search(pressure) else None,
        "swap_raw": swap,
        "memory_pressure_raw": pressure,
        "footprint_raw": fp,
        "ps_raw": ps,
        "vm_stat_raw": vm,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--cache-budget-gb", type=float, default=4.0)
    ap.add_argument("--max-tokens", type=int, default=256)
    ap.add_argument("--target-tokens", type=int, default=6144)
    ap.add_argument("--swap-limit-mib", type=float, default=512.0)
    ap.add_argument("--free-limit-pct", type=int, default=20)
    args = ap.parse_args()

    arm = Path(args.arm).resolve()
    arm.mkdir(parents=True, exist_ok=False)
    model = Path(args.model).resolve()
    if not model.is_dir():
        raise SystemExit(f"model directory missing: {model}")
    if (ROOT / ".venv/bin/python").resolve() == Path(sys.executable).resolve():
        python = str(ROOT / ".venv/bin/python")
    else:
        python = str(ROOT / ".venv/bin/python")

    lane_status = capture([str(Path.home() / ".hermes/bin/hermes-local-model"), "status"])
    if "FAST: down" not in lane_status or "DEEP: down" not in lane_status:
        raise SystemExit("refusing custom model run: managed lane is not down\n" + lane_status)

    pre = snapshot(0, "pre-run")
    baseline_swap = pre["swap_mib"]
    prompt_path = arm / "prompt.txt"
    cmd_prompt = [python, str(ROOT / "scripts/make_prompt.py"), "--model", str(model),
                  "--out", str(prompt_path), "--target-tokens", str(args.target_tokens)]
    prompt_build = subprocess.run(cmd_prompt, text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, check=False)
    if prompt_build.returncode:
        (arm / "prompt-build.log").write_text(prompt_build.stdout, encoding="utf-8")
        raise SystemExit("prompt build failed")
    prompt = prompt_path.read_text(encoding="utf-8")
    prompt_meta = json.loads(prompt_path.with_suffix(".json").read_text(encoding="utf-8"))

    command = [
        python, "-m", "turboquant_mlx.stream.stream_generate",
        "--model", str(model), "--prompt", prompt,
        "--max-tokens", str(args.max_tokens),
        "--temp", "0", "--top-p", "0.9", "--no-think",
        "--cache-budget-gb", str(args.cache_budget_gb),
        "--max-active-experts", "0",  # native top-10: no quality-changing K-reduction
        "--prefetch-workers", "8", "--prefetch-ahead", "0",
        "--no-page-cache", "--no-learn-experts", "--no-hotlist",
    ]
    (arm / "command.json").write_text(json.dumps({
        "command": command[:6] + ["<prompt in prompt.txt>"] + command[7:],
        "configuration": {
            "cache_budget_gb": args.cache_budget_gb,
            "max_tokens": args.max_tokens,
            "target_prompt_tokens": args.target_tokens,
            "swap_limit_mib": args.swap_limit_mib,
            "free_limit_pct": args.free_limit_pct,
            "native_top_k": 10,
            "dflash": "off",
            "kv": "fp16",
            "prefill_step": "runtime default (no explicit override; standalone streaming CLI)",
        },
        "prompt": prompt_meta,
    }, indent=2) + "\n", encoding="utf-8")

    iostat = subprocess.Popen(["iostat", "-d", "-w", "1"], stdout=(arm / "iostat.txt").open("w"),
                              stderr=subprocess.STDOUT, start_new_session=True)
    started = time.monotonic()
    with (arm / "stdout-stderr.log").open("w", encoding="utf-8") as stream:
        child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                 text=True, start_new_session=True)
        samples = [pre, snapshot(child.pid, "started")]
        stop_reason = None
        try:
            while child.poll() is None:
                time.sleep(2)
                sample = snapshot(child.pid, "active")
                samples.append(sample)
                if baseline_swap is not None and sample["swap_mib"] is not None:
                    if sample["swap_mib"] - baseline_swap > args.swap_limit_mib:
                        stop_reason = (f"incremental_swap>{args.swap_limit_mib}MiB "
                                       f"({sample['swap_mib'] - baseline_swap:.2f} MiB)")
                if sample["memory_free_pct"] is not None and sample["memory_free_pct"] < args.free_limit_pct:
                    stop_reason = f"memory_free<{args.free_limit_pct}% ({sample['memory_free_pct']}%)"
                if stop_reason:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=20)
                    break
            rc = child.wait()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=20)
            if iostat.poll() is None:
                os.killpg(iostat.pid, signal.SIGTERM)
                iostat.wait(timeout=10)

    post = snapshot(0, "post-run")
    samples.append(post)
    (arm / "telemetry.json").write_text(json.dumps(samples, indent=2) + "\n", encoding="utf-8")
    deltas = [s["swap_mib"] - baseline_swap for s in samples
              if baseline_swap is not None and s.get("swap_mib") is not None]
    completed = stop_reason is None and rc == 0
    summary = {
        "status": "completed" if completed else ("stopped_for_swap" if stop_reason else "runtime_failure"),
        "stop_reason": stop_reason,
        "exit_code": rc,
        "started_at": pre["at"],
        "elapsed_s": round(time.monotonic() - started, 3),
        "baseline_swap_mib": baseline_swap,
        "peak_swap_mib": max((s["swap_mib"] for s in samples if s.get("swap_mib") is not None), default=None),
        "max_incremental_swap_mib": max(deltas, default=None),
        "min_memory_free_pct": min((s["memory_free_pct"] for s in samples if s.get("memory_free_pct") is not None), default=None),
        "prompt": prompt_meta,
        "lane_status_before": lane_status,
        "lane_status_after": capture([str(Path.home() / ".hermes/bin/hermes-local-model"), "status"]),
    }
    (arm / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if completed else 1

if __name__ == "__main__":
    raise SystemExit(main())
