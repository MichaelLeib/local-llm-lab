#!/usr/bin/env python3
"""Serve one guarded Laguna short-context arm on a private loopback port."""
from __future__ import annotations
import argparse, http.client, json, os, re, signal, subprocess, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWAP_RE = re.compile(r"used =\s*([0-9.]+)M")
FREE_RE = re.compile(r"free percentage:\s*(\d+)%")

def out(cmd, timeout=20):
    try:
        return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, check=False).stdout
    except Exception as e: return f"<capture error {e}>\n"
def snap(pid, label):
    sw, mp = out(["sysctl","vm.swapusage"]), out(["memory_pressure","-Q"])
    sm, fm = SWAP_RE.search(sw), FREE_RE.search(mp)
    return {"at":datetime.now(timezone.utc).isoformat(),"label":label,"pid":pid,
      "swap_mib":float(sm.group(1)) if sm else None,"memory_free_pct":int(fm.group(1)) if fm else None,
      "swap_raw":sw,"memory_pressure_raw":mp,"ps_raw":out(["ps","-o","pid=,ppid=,rss=,etime=,command=","-p",str(pid)]) if pid else "",
      "footprint_raw":out(["footprint","-p",str(pid)]) if pid else "","vm_stat_raw":out(["vm_stat"])}
def alive(port):
    try:
        c=http.client.HTTPConnection("127.0.0.1",port,timeout=3); c.request("GET","/v1/models"); r=c.getresponse(); r.read(); return r.status==200
    except OSError: return False

def main():
 p=argparse.ArgumentParser(); p.add_argument("--model",required=True); p.add_argument("--arm",required=True); p.add_argument("--port",type=int,default=8910); p.add_argument("--cache-budget-gb",type=float,default=4.0); p.add_argument("--max-tokens",type=int,default=256); p.add_argument("--target-tokens",type=int,default=6144); p.add_argument("--swap-limit-mib",type=float,default=512); p.add_argument("--free-limit-pct",type=int,default=20); a=p.parse_args()
 arm=Path(a.arm).resolve(); arm.mkdir(parents=True,exist_ok=False); model=Path(a.model).resolve(); py=str(ROOT/".venv/bin/python")
 if not model.is_dir(): raise SystemExit(f"missing model: {model}")
 lanes=out([str(Path.home()/".hermes/bin/hermes-local-model"),"status"])
 if "FAST: down" not in lanes or "DEEP: down" not in lanes: raise SystemExit("refusing: managed lane not down\n"+lanes)
 if out(["lsof","-nP",f"-iTCP:{a.port}","-sTCP:LISTEN"]).strip(): raise SystemExit(f"refusing: port {a.port} already listening")
 pre=snap(0,"pre-run"); base=pre["swap_mib"]
 prompt_path=arm/"prompt.txt"; made=subprocess.run([py,str(ROOT/"scripts/make_prompt.py"),"--model",str(model),"--out",str(prompt_path),"--target-tokens",str(a.target_tokens)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (arm/"prompt-build.log").write_text(made.stdout,encoding="utf-8")
 if made.returncode: raise SystemExit("prompt construction failed")
 prompt=prompt_path.read_text(encoding="utf-8"); prompt_meta=json.loads(prompt_path.with_suffix(".json").read_text())
 cmd=[py,"-m","turboquant_mlx.serve","--model",str(model),"--host","127.0.0.1","--port",str(a.port),"--temp","0","--top-p","0.9","--max-tokens",str(a.max_tokens),"--chat-template-args",'{"enable_thinking":false}',"--prompt-concurrency","1","--prefill-step-size","128","--prompt-cache-size","1","--cache-budget-gb",str(a.cache_budget_gb),"--max-active-experts","0","--prefetch-workers","8","--no-page-cache","--no-hotlist","--prefill-stats","--prefill-stats-file",str(arm/"prefill-stats.jsonl")]
 (arm/"command.json").write_text(json.dumps({"server_command":cmd,"request":{"model":str(model),"messages":[{"role":"user","content":"<prompt in prompt.txt>"}],"stream":True,"max_tokens":a.max_tokens,"temperature":0},"configuration":{"native_top_k":10,"dflash":"off","kv":"fp16","prefill_step_size":128,"cache_budget_gb":a.cache_budget_gb,"swap_limit_mib":a.swap_limit_mib,"memory_free_limit_pct":a.free_limit_pct},"prompt":prompt_meta},indent=2)+"\n")
 iof=(arm/"iostat.txt").open("w"); io=subprocess.Popen(["iostat","-d","-w","1"],stdout=iof,stderr=subprocess.STDOUT,start_new_session=True)
 log=(arm/"server.log").open("w"); server=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True)
 samples=[pre,snap(server.pid,"server-spawned")]; stop=None; result={"done":False}; request_started=None
 try:
  while server.poll() is None and not alive(a.port):
   time.sleep(2); s=snap(server.pid,"server-starting"); samples.append(s)
   if base is not None and s["swap_mib"] is not None and s["swap_mib"]-base>a.swap_limit_mib: stop=f"incremental_swap>{a.swap_limit_mib}MiB ({s['swap_mib']-base:.2f} MiB)"
   if s["memory_free_pct"] is not None and s["memory_free_pct"]<a.free_limit_pct: stop=f"memory_free<{a.free_limit_pct}% ({s['memory_free_pct']}%)"
   if stop: break
  if server.poll() is not None and not stop: stop=f"server_exited_before_health:{server.returncode}"
  if not stop:
   request_started=time.monotonic()
   payload=json.dumps({"model":str(model),"messages":[{"role":"user","content":prompt}],"stream":True,"max_tokens":a.max_tokens,"temperature":0}).encode()
   def req():
    raw=(arm/"response.sse").open("wb")
    try:
     c=http.client.HTTPConnection("127.0.0.1",a.port,timeout=1800); c.request("POST","/v1/chat/completions",body=payload,headers={"Content-Type":"application/json","Accept":"text/event-stream"}); r=c.getresponse(); result["http_status"]=r.status
     while True:
      line=r.readline()
      if not line: break
      raw.write(line); raw.flush()
      if result.get("first_sse_s") is None and line.startswith(b"data:") and line.strip()!=b"data: [DONE]": result["first_sse_s"]=round(time.monotonic()-request_started,3)
     result["done"]=True
    except Exception as e: result["error"]=repr(e)
    finally: raw.close()
   t=threading.Thread(target=req,daemon=True); t.start()
   while t.is_alive() and server.poll() is None:
    time.sleep(2); s=snap(server.pid,"request-active"); samples.append(s)
    if base is not None and s["swap_mib"] is not None and s["swap_mib"]-base>a.swap_limit_mib: stop=f"incremental_swap>{a.swap_limit_mib}MiB ({s['swap_mib']-base:.2f} MiB)"
    if s["memory_free_pct"] is not None and s["memory_free_pct"]<a.free_limit_pct: stop=f"memory_free<{a.free_limit_pct}% ({s['memory_free_pct']}%)"
    if stop: break
   if stop: result["safety_stop_during_request"]=True
 finally:
  if server.poll() is None:
   os.killpg(server.pid,signal.SIGTERM)
   try: server.wait(timeout=30)
   except subprocess.TimeoutExpired: os.killpg(server.pid,signal.SIGKILL); server.wait(timeout=30)
  if io.poll() is None: os.killpg(io.pid,signal.SIGTERM); io.wait(timeout=10)
  iof.close(); log.close()
 post=snap(0,"post-run"); samples.append(post); (arm/"telemetry.json").write_text(json.dumps(samples,indent=2)+"\n")
 deltas=[x["swap_mib"]-base for x in samples if base is not None and x.get("swap_mib") is not None]
 summary={"status":"completed" if not stop and result.get("done") and result.get("http_status")==200 else ("stopped_for_swap" if stop and "swap" in stop else ("stopped_for_memory_pressure" if stop and "memory_free" in stop else "runtime_failure")),"stop_reason":stop,"server_exit_code":server.returncode,"baseline_swap_mib":base,"peak_swap_mib":max((x["swap_mib"] for x in samples if x.get("swap_mib") is not None),default=None),"max_incremental_swap_mib":max(deltas,default=None),"min_memory_free_pct":min((x["memory_free_pct"] for x in samples if x.get("memory_free_pct") is not None),default=None),"request":result,"prompt":prompt_meta,"lane_status_before":lanes,"lane_status_after":out([str(Path.home()/".hermes/bin/hermes-local-model"),"status"])}
 (arm/"summary.json").write_text(json.dumps(summary,indent=2)+"\n"); print(json.dumps(summary,indent=2)); return 0 if summary["status"]=="completed" else 1
if __name__=="__main__": raise SystemExit(main())
