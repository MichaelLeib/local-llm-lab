#!/usr/bin/env python3
import datetime as dt
import json
import pathlib
import subprocess
import time

root = pathlib.Path.home() / "HermesProjects/Local-LLM-Lab"
base = root / "results/raw/EXP-005"
src = base / "source/slipstream"
model = base / "model/qwen36.gturbo"
outdir = base / "kv-snapshot-clean"
outdir.mkdir(parents=True, exist_ok=True)
snapshot = outdir / "qwen36-1105-prefix.kv"
binary = src / ".build/release/slipstream"
prompt = " ".join(["alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"] * 92)
rows = []
for name in ["cold-save", "warm-restore"]:
    cmd = [str(binary), "--model", str(model), "--prompt", prompt, "--max-new", "16", "--max-context", "4096", "--temperature", "0", "--seed", "12345", "--expert-cache-slots", "16", "--prefill-chunk", "auto", "--kv-snapshot", str(snapshot)]
    before = subprocess.run(["/usr/sbin/sysctl", "vm.swapusage"], capture_output=True, text=True).stdout.strip()
    memory_before = subprocess.run(["/usr/bin/memory_pressure", "-Q"], capture_output=True, text=True).stdout.strip()
    t = time.monotonic(); p = subprocess.run(cmd, cwd=src, capture_output=True, text=True); wall = time.monotonic() - t
    after = subprocess.run(["/usr/sbin/sysctl", "vm.swapusage"], capture_output=True, text=True).stdout.strip()
    memory_after = subprocess.run(["/usr/bin/memory_pressure", "-Q"], capture_output=True, text=True).stdout.strip()
    row = {"name": name, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "command": cmd, "exit_code": p.returncode, "wall_seconds": round(wall, 3), "stdout": p.stdout, "stderr": p.stderr, "swap_before": before, "swap_after": after, "memory_before": memory_before, "memory_after": memory_after}
    rows.append(row)
    (outdir / f"{name}.stdout.txt").write_text(p.stdout)
    (outdir / f"{name}.stderr.txt").write_text(p.stderr)
    (outdir / f"{name}.swap-before.txt").write_text(before + "\n")
    (outdir / f"{name}.swap-after.txt").write_text(after + "\n")
    (outdir / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps({"snapshot": str(snapshot), "snapshot_exists": snapshot.exists(), "snapshot_bytes": snapshot.stat().st_size if snapshot.exists() else None, "runs": rows}, indent=2))
if any(r["exit_code"] != 0 for r in rows): raise SystemExit(1)
