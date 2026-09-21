#!/usr/bin/env python3
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

root = pathlib.Path.home() / "HermesProjects/Local-LLM-Lab"
base = root / "results/raw/EXP-005"
src = base / "source/slipstream"
model = base / "model/qwen36.gturbo"
outdir = base / "first-probe-clean"
outdir.mkdir(parents=True, exist_ok=True)

binary = src / ".build/release/slipstream"
cmd = [
    str(binary), "--model", str(model),
    "--prompt", "Reply with exactly READY.",
    "--max-new", "8", "--max-context", "4096",
    "--temperature", "0", "--seed", "12345",
    "--expert-cache-slots", "16", "--prefill-chunk", "auto",
]

def run_capture(args, path):
    p = subprocess.run(args, text=True, capture_output=True)
    pathlib.Path(path).write_text(p.stdout + ("\n--- STDERR ---\n" + p.stderr if p.stderr else ""))
    return p.returncode

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

meta = {"started_at": now(), "command": cmd, "cwd": str(src), "pid": None, "python": sys.version, "uid": os.getuid()}
(base / "first-probe-clean-command.json").write_text(json.dumps(meta, indent=2) + "\n")
run_capture(["/usr/bin/memory_pressure", "-Q"], outdir / "memory-before.txt")
run_capture(["/usr/sbin/sysctl", "vm.swapusage"], outdir / "swap-before.txt")
run_capture(["/bin/df", "-h", "/"], outdir / "disk-before.txt")

stdout = (outdir / "stdout.txt").open("w")
stderr = (outdir / "stderr.txt").open("w")
p = subprocess.Popen(cmd, cwd=src, stdout=stdout, stderr=stderr, text=True)
meta["pid"] = p.pid
(base / "first-probe-clean-command.json").write_text(json.dumps(meta, indent=2) + "\n")
samples = (outdir / "samples.jsonl").open("w")
footprint = shutil.which("footprint")
try:
    while p.poll() is None:
        row = {"timestamp": now(), "pid": p.pid}
        ps = subprocess.run(["/bin/ps", "-p", str(p.pid), "-o", "pid=,rss=,vsz=,%cpu=,%mem=,etime="], capture_output=True, text=True)
        row["ps"] = ps.stdout.strip()
        if footprint:
            fp = subprocess.run([footprint, "-p", str(p.pid)], capture_output=True, text=True)
            row["footprint_rc"] = fp.returncode
            row["footprint"] = fp.stdout[-12000:]
            row["footprint_stderr"] = fp.stderr[-2000:]
        samples.write(json.dumps(row) + "\n")
        samples.flush()
        time.sleep(1)
finally:
    rc = p.wait()
    stdout.close(); stderr.close(); samples.close()

meta.update({"finished_at": now(), "exit_code": rc})
(base / "first-probe-clean-command.json").write_text(json.dumps(meta, indent=2) + "\n")
run_capture(["/usr/bin/memory_pressure", "-Q"], outdir / "memory-after.txt")
run_capture(["/usr/sbin/sysctl", "vm.swapusage"], outdir / "swap-after.txt")
run_capture(["/bin/df", "-h", "/"], outdir / "disk-after.txt")
print(json.dumps(meta, indent=2))
raise SystemExit(rc)
