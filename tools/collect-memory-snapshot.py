#!/usr/bin/env python3
"""Capture a read-only macOS memory/VM/process snapshot as JSON.

This script never allocates pressure. It records raw command output alongside
small parsed fields so later analysis can improve without rerunning a level.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path


def run(command: list[str], timeout: float = 5.0) -> dict:
    try:
        completed = subprocess.run(command, text=True, capture_output=True,
                                   timeout=timeout, check=False)
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": (exc.stderr or "") + "timeout",
        }
    except OSError as exc:
        return {"command": command, "returncode": None, "stdout": "", "stderr": str(exc)}


def parse_first_int(text: str, key: str) -> int | None:
    match = re.search(rf"^{re.escape(key)}:\s*(\d+)", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default="EXP-001", help="experiment ID for metadata")
    parser.add_argument("--label", default="snapshot", help="baseline or pressure level label")
    parser.add_argument("--target-gib", type=float, default=None)
    parser.add_argument("--pid", type=int, default=None, help="optional target PID for vmmap -summary")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    commands = {
        "sw_vers": ["sw_vers"],
        "sysctl_memory": ["sysctl", "hw.memsize", "hw.ncpu", "vm.swapusage", "vm.loadavg"],
        "vm_stat": ["vm_stat"],
        # -l is required with -S on this macOS build. This simulates the
        # query and does not invoke memory_pressure's real allocator mode.
        "memory_pressure_simulated": ["memory_pressure", "-S", "-l", "warn", "-Q"],
        "processes_by_rss": ["ps", "-axo", "pid=,ppid=,rss=,%cpu=,comm="],
        "disk_root": ["df", "-h", "/"],
    }
    if args.pid is not None:
        commands["target_vmmap"] = ["vmmap", "-summary", str(args.pid)]
    raw = {name: run(command, timeout=4.0 if name != "processes_by_rss" else 8.0)
           for name, command in commands.items()}

    vm_text = raw["vm_stat"]["stdout"]
    page_match = re.search(r"page size of (\d+) bytes", vm_text)
    page_size = int(page_match.group(1)) if page_match else None
    vm_pages = {}
    if page_size:
        for line in vm_text.splitlines():
            match = re.match(r"([^:]+):\s+(\d+)", line)
            if match:
                pages = int(match.group(2).rstrip("."))
                vm_pages[match.group(1).strip()] = {
                    "pages": pages,
                    "bytes": pages * page_size,
                }

    rss_rows = []
    for line in raw["processes_by_rss"]["stdout"].splitlines():
        fields = line.split(None, 4)
        if len(fields) == 5:
            try:
                rss_rows.append({
                    "pid": int(fields[0]),
                    "ppid": int(fields[1]),
                    "rss_kib": int(fields[2]),
                    "cpu_percent": fields[3],
                    "command": fields[4],
                })
            except ValueError:
                pass
    rss_rows.sort(key=lambda row: row["rss_kib"], reverse=True)

    pressure_text = raw["memory_pressure_simulated"]["stdout"] + raw["memory_pressure_simulated"]["stderr"]
    pressure_match = re.search(r"System-wide memory free percentage:\s*([0-9.]+)%", pressure_text)
    pressure_free_percent = float(pressure_match.group(1)) if pressure_match else None

    record = {
        "schema": "local-llm-lab.memory-snapshot.v1",
        "experiment": args.experiment,
        "label": args.label,
        "target_gib": args.target_gib,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": platform.node(),
        "pid": os.getpid(),
        "observed_pid": args.pid,
        "parsed": {
            "page_size_bytes": page_size,
            "vm_stat": vm_pages,
            "memory_pressure_free_percent": pressure_free_percent,
            "top_processes_by_rss": rss_rows[:20],
        },
        "raw": raw,
    }
    encoded = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
