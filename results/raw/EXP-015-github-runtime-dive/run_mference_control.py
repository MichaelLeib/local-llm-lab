#!/usr/bin/env python3
"""One guarded Mference/Qwen3.6 control measurement; exits before swap escalation."""
import json, os, re, signal, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent
out = root / "raw" / ("mference-control-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
out.mkdir(parents=True)
model = Path("/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/model/qwen36.gturbo")
bin = root / "source/Mference/.build/out/Products/Release/MferenceCLI"

def sh(cmd):
    return subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout

def vm():
    return {"swapusage": sh("sysctl vm.swapusage").strip(), "vm_stat": sh("vm_stat"), "pressure": sh("memory_pressure -Q").strip()}

before = vm()
slots = os.environ.get("EXP_SLOTS", "16")
cmd = [str(bin), "--model", str(model), "--prompt", "In exactly four concise sentences, explain why stable prompt prefixes matter for local tool-using language models.", "--max-new", "64", "--max-context", "8192", "--temperature", "0", "--top-k", "1", "--top-p", "1", "--expert-cache-slots", slots, "--prefill-chunk", "128", "--verify", "trusted-receipt"]
env = os.environ | {"MFERENCE_PHASES": "1"}
started = time.time()
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, start_new_session=True)
lines=[]; timed_out=False
try:
    stdout, _ = p.communicate(timeout=300)
    lines.append(stdout)
except subprocess.TimeoutExpired:
    timed_out=True
    os.killpg(p.pid, signal.SIGTERM)
    stdout, _ = p.communicate(timeout=20)
    lines.append(stdout)
after=vm()
text="".join(lines)
(out/"command.txt").write_text(" ".join(cmd)+"\n")
(out/"stdout-stderr.log").write_text(text)
(out/"result.json").write_text(json.dumps({"timestamp":datetime.now(timezone.utc).isoformat(),"exit_code":p.returncode,"timeout":timed_out,"wall_seconds":round(time.time()-started,3),"before":before,"after":after,"timing_footers":re.findall(r".*(?:prefill=|tok/s=|decode=).*", text),"command":cmd},indent=2))
print(out)
print("exit",p.returncode,"timeout",timed_out,"wall",round(time.time()-started,2))
