#!/usr/bin/env python3
"""Run one guarded, reproducible TinyTitan CLI context arm.

No timeout is applied to inference.  The only automatic stop is an explicit
incremental swap guard, recorded as stopped_for_swap rather than a result.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import threading
import time
from typing import Any

ROOT = pathlib.Path("/Users/<user>/HermesProjects/Local-LLM-Lab")
EXP = ROOT / "results/raw/EXP-009-qwen38-long-context"
MODEL = ROOT / "results/raw/EXP-006/model/qwen3.8-flash-next_125B_A6B_4Bit"
CLI = EXP / "source/tinytitan-current/.build/release/TinyTitanCLI"

FOOTER = re.compile(
    r"\[stop=(\S+) prefill=(\d+)tok/([\d.]+)s new=(\d+)tok "
    r"decode=([\d.]+)s tok/s=([\d.]+)\]"
)
IO = re.compile(
    r"\[decode expert io\] hits (\d+) misses (\d+) \(([\d.]+)% hit\) "
    r"([\d.]+) GiB(?: = ([\d.]+) MiB/token)?"
)
SWAP = re.compile(r"used = ([\d.]+)M")
PAGES = re.compile(r"^([^:]+):\s+(\d+)", re.M)
FOOTPRINT = re.compile(r"Physical footprint:\s*([\d,]+)")


def run(args: list[str], timeout: float = 10.0) -> dict[str, Any]:
    try:
        p = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
        return {"command": args, "returncode": p.returncode, "stdout": p.stdout,
                "stderr": p.stderr}
    except Exception as exc:
        return {"command": args, "returncode": None, "stdout": "", "stderr": repr(exc)}


def swap_mib() -> float | None:
    text = run(["sysctl", "-n", "vm.swapusage"])["stdout"]
    m = SWAP.search(text)
    return float(m.group(1)) if m else None


def sample(pid: int | None) -> dict[str, Any]:
    vm = run(["vm_stat"])
    vm_pages = {key.strip(): int(value.rstrip("."))
                for key, value in PAGES.findall(vm["stdout"])}
    row: dict[str, Any] = {
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "swap_mib": swap_mib(),
        "memory_pressure": run(["memory_pressure", "-Q"]),
        "vm_stat": vm,
        "vm_pages": vm_pages,
        "compression_pages": vm_pages.get("Pages occupied by compressor"),
        "pageouts": vm_pages.get("Pageouts"),
        "swapouts": vm_pages.get("Swapouts"),
    }
    if pid is not None:
        row["process"] = run(["ps", "-p", str(pid), "-o", "pid=,ppid=,rss=,%cpu=,%mem=,etime=,command="])
        fp = run(["footprint", "-p", str(pid), "-f", "bytes", "--noCategories"], timeout=8.0)
        row["footprint"] = fp
        found = FOOTPRINT.search(fp["stdout"])
        if found:
            row["physical_footprint_bytes"] = int(found.group(1).replace(",", ""))
    return row


def current_model_processes() -> str:
    cmd = "ps -axo pid=,command= | grep -E '[T]inyTitanCLI|[T]inyTitanServer|[s]lipstream|[l]lama-server|[r]apid-mlx|[m]lx_lm' || true"
    return subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout.strip()


def make_messages(repetitions: int) -> list[dict[str, str]]:
    # Repeated natural-language units are deterministic, inspectable, and avoid
    # using a character count as a proxy for accepted tokenizer length.
    unit = "This deterministic local-model measurement corpus preserves a factual record for later retrieval."
    corpus = "\n".join(f"{i:04d}: {unit}" for i in range(1, repetitions + 1))
    prompt = (corpus + "\n\nAfter reading the corpus, output the integers 1 through 256, "
              "one per line, with no explanation.")
    return [
        {"role": "system", "content": "Follow the requested output exactly."},
        {"role": "user", "content": prompt},
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--expert-cache-slots", type=int, required=True)
    parser.add_argument("--max-context", type=int, default=8192)
    parser.add_argument("--max-new", type=int, default=256)
    parser.add_argument("--repetitions", type=int, default=450)
    parser.add_argument("--swap-stop-delta-mib", type=float, default=4096.0)
    parser.add_argument("--sample-seconds", type=float, default=3.0)
    args = parser.parse_args()

    out = EXP / "arms" / args.label
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing arm: {out}")
    out.mkdir(parents=True)
    if not (CLI.is_file() and os.access(CLI, os.X_OK) and (MODEL / "verified-install.json").is_file()):
        raise SystemExit("runtime binary or verified model receipt is missing")
    busy = current_model_processes()
    if busy:
        raise SystemExit(f"refusing competing local model process:\n{busy}")

    messages = make_messages(args.repetitions)
    messages_path = out / "messages.json"
    messages_path.write_text(json.dumps(messages, indent=2) + "\n")
    baseline = sample(None)
    (out / "before.json").write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")

    command = [str(CLI), "--model", str(MODEL), "--messages-file", str(messages_path),
               "--max-new", str(args.max_new), "--max-context", str(args.max_context),
               "--temperature", "0", "--seed", "12345", "--thinking", "off",
               "--expert-cache-slots", str(args.expert_cache_slots), "--prefill-chunk", "4096"]
    environment = dict(os.environ)
    environment.update({
        "TINYTITAN_DECODE_IO_TRACE": "1",
        "TINYTITAN_KEEP_WIRED": "1",
        "TINYTITAN_RDADVISE_POLICY": "default",
    })
    (out / "command.json").write_text(json.dumps({"command": command, "environment": {
        k: environment[k] for k in ("TINYTITAN_DECODE_IO_TRACE", "TINYTITAN_KEEP_WIRED", "TINYTITAN_RDADVISE_POLICY")
    }}, indent=2) + "\n")

    iostat_file = (out / "iostat.log").open("w")
    iostat = subprocess.Popen(["iostat", "-d", "-w", "2"], stdout=iostat_file, stderr=subprocess.STDOUT,
                               text=True)
    stdout = (out / "stdout.txt").open("w")
    stderr = (out / "stderr.txt").open("w")
    proc = subprocess.Popen(command, stdout=stdout, stderr=stderr, text=True, env=environment)
    samples: list[dict[str, Any]] = []
    stopped_for_swap = False
    max_swap = baseline.get("swap_mib") or 0.0
    deadline = time.monotonic() + args.sample_seconds
    try:
        while proc.poll() is None:
            if time.monotonic() >= deadline:
                row = sample(proc.pid)
                samples.append(row)
                if row.get("swap_mib") is not None:
                    max_swap = max(max_swap, row["swap_mib"])
                    if row["swap_mib"] > (baseline.get("swap_mib") or 0.0) + args.swap_stop_delta_mib:
                        stopped_for_swap = True
                        proc.terminate()
                deadline = time.monotonic() + args.sample_seconds
            time.sleep(0.2)
        exit_code = proc.wait()
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=30)
        iostat.terminate()
        try:
            iostat.wait(timeout=5)
        except subprocess.TimeoutExpired:
            iostat.kill()
            iostat.wait()
        stdout.close(); stderr.close(); iostat_file.close()

    after = sample(None)
    (out / "samples.json").write_text(json.dumps(samples, indent=2, sort_keys=True) + "\n")
    (out / "after.json").write_text(json.dumps(after, indent=2, sort_keys=True) + "\n")
    error_text = (out / "stderr.txt").read_text(errors="replace")
    footer = FOOTER.search(error_text)
    io = IO.search(error_text)
    summary: dict[str, Any] = {
        "experiment": "EXP-009-qwen38-long-context", "arm": args.label,
        "status": "stopped_for_swap" if stopped_for_swap else ("completed" if exit_code == 0 else "runtime_failure"),
        "exit_code": exit_code, "command": command, "baseline_swap_mib": baseline.get("swap_mib"),
        "after_swap_mib": after.get("swap_mib"), "max_sampled_swap_mib": max_swap,
        "swap_stop_delta_mib": args.swap_stop_delta_mib,
        "prompt_characters": len(messages[1]["content"]), "repetitions": args.repetitions,
        "max_context": args.max_context, "max_new": args.max_new,
        "sample_count": len(samples),
        "metal_telemetry": run(["ioreg", "-r", "-c", "IOAccelerator", "-a"], timeout=10.0),
        "post_model_process_check": current_model_processes(),
    }
    if footer:
        stop, toks, prefill_s, new, decode_s, rate = footer.groups()
        summary["timing"] = {"stop": stop, "prompt_tokens": int(toks), "prefill_s": float(prefill_s),
                             "prefill_tok_s": int(toks) / float(prefill_s), "new_tokens": int(new),
                             "decode_s": float(decode_s), "decode_tok_s": float(rate)}
    if io:
        hits, misses, hit_pct, gib, per_token = io.groups()
        summary["decode_expert_io"] = {"hits": int(hits), "misses": int(misses),
                                       "hit_pct": float(hit_pct), "gib": float(gib),
                                       "mib_per_token": float(per_token) if per_token else None}
    if samples:
        footprints = [x.get("physical_footprint_bytes") for x in samples if x.get("physical_footprint_bytes")]
        if footprints:
            summary["peak_sampled_physical_footprint_bytes"] = max(footprints)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
