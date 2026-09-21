#!/usr/bin/env python3
import datetime as dt
import json
import pathlib
import re
import subprocess
import time

root = pathlib.Path.home() / "HermesProjects/Local-LLM-Lab"
base = root / "results/raw/EXP-005"
src = base / "source/slipstream"
model = base / "model/qwen36.gturbo"
outdir = base / "prefill-sweep"
outdir.mkdir(parents=True, exist_ok=True)
binary = src / ".build/release/slipstream"

# Fresh process per arm; OS file cache is intentionally not purged. The first
# short probe already establishes a cold-start result; this sweep measures the
# warm steady path at increasing prompt lengths.
arms = [5, 256, 512, 1024, 2048]
rows = []

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def capture(args):
    p = subprocess.run(args, text=True, capture_output=True)
    return p.returncode, p.stdout, p.stderr

def parse_footer(stderr):
    m = re.search(r"\[stop=(\S+) prefill=(\d+)tok/([0-9.]+)s new=(\d+)tok decode=([0-9.]+)s tok/s=([0-9.]+)\]", stderr)
    if not m: return {}
    return {"stop": m.group(1), "prompt_tokens": int(m.group(2)), "prefill_seconds": float(m.group(3)), "new_tokens": int(m.group(4)), "decode_seconds": float(m.group(5)), "decode_tok_s": float(m.group(6))}

for i, n in enumerate(arms):
    prompt = " ".join(["alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"] * max(1, n // 12))
    if n == 5: prompt = "Reply with exactly READY."
    run = {
        "arm": n, "started_at": now(), "settings": {"slots": 16, "max_context": 4096, "max_new": 16, "temperature": 0, "seed": 12345, "prefill_chunk": "auto"}
    }
    capture(["/usr/bin/memory_pressure", "-Q"])[1]
    sb = capture(["/usr/sbin/sysctl", "vm.swapusage"])[1]
    run["swap_before"] = sb.strip()
    t0 = time.monotonic()
    rc, out, err = capture([str(binary), "--model", str(model), "--prompt", prompt, "--max-new", "16", "--max-context", "4096", "--temperature", "0", "--seed", "12345", "--expert-cache-slots", "16", "--prefill-chunk", "auto"])
    run["wall_seconds"] = round(time.monotonic() - t0, 3)
    run["finished_at"] = now(); run["exit_code"] = rc; run["footer"] = parse_footer(err)
    run["stdout"] = out; run["stderr"] = err
    run["swap_after"] = capture(["/usr/sbin/sysctl", "vm.swapusage"])[1].strip()
    run["memory_after"] = capture(["/usr/bin/memory_pressure", "-Q"])[1].strip()
    (outdir / f"arm-{n}.stdout.txt").write_text(out)
    (outdir / f"arm-{n}.stderr.txt").write_text(err)
    rows.append(run)
    (outdir / "results.json").write_text(json.dumps(rows, indent=2) + "\n")

print(json.dumps(rows, indent=2))
