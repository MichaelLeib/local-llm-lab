#!/usr/bin/env python3
"""Guarded large-prefix prefill A/B: current runtime 128 vs 2048 chunks."""
import json, os, re, signal, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/"raw"/("mference-prefill-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")); out.mkdir(parents=True)
bin=root/"source/Mference/.build/out/Products/Release/MferenceCLI"
model=Path("/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/model/qwen36.gturbo")
prompt=("A stable local-agent system reuses its verified instruction prefix, preserves tool schemas, and records state safely. ")*350

def sh(s): return subprocess.run(s,shell=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout
def snap(): return {"swap":sh("sysctl vm.swapusage").strip(),"pressure":sh("memory_pressure -Q").strip(),"vm":sh("vm_stat")}
results=[]
for chunk in ["128","2048"]:
  before=snap()
  cmd=[str(bin),"--model",str(model),"--prompt",prompt,"--max-new","1","--max-context","8192","--temperature","0","--top-k","1","--top-p","1","--expert-cache-slots","32","--prefill-chunk",chunk,"--verify","trusted-receipt"]
  t=time.time(); p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=os.environ|{"MFERENCE_PHASES":"1"},start_new_session=True)
  try: txt,_=p.communicate(timeout=420); timeout=False
  except subprocess.TimeoutExpired:
    timeout=True; os.killpg(p.pid, signal.SIGTERM); txt,_=p.communicate(timeout=20)
  after=snap(); (out/f"chunk-{chunk}.log").write_text(txt)
  results.append({"chunk":chunk,"exit":p.returncode,"timeout":timeout,"wall_s":round(time.time()-t,3),"before":before,"after":after,"footer":re.findall(r".*(?:prefill=|tok/s=|decode=).*",txt),"command":cmd})
(out/"result.json").write_text(json.dumps(results,indent=2))
print(out)
