#!/usr/bin/env python3
"""Guarded loopback-server cache-slot/policy sweep for EXP-014."""
import json, os, re, signal, subprocess, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'raw'/('cache-sweep-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')); OUT.mkdir(parents=True)
MODEL=Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/model/qwen36.gturbo')
BIN=Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/source/slipstream/.build/out/Products/Release/slipstream-server')
PROMPT='Summarize this instruction in one sentence: '+'reliable local tool calling requires genuine function invocations and accurate tool-result handling. '*85
ARMS=[(16,'lfu-aging'),(16,'lru'),(24,'lfu-aging'),(32,'lfu-aging')]; LIMIT=256.0; PORT=8914
def swap():
 s=subprocess.check_output(['sysctl','vm.swapusage'],text=True); m=re.search(r'used = ([0-9.]+)M',s); return float(m.group(1))
def free():
 s=subprocess.check_output(['memory_pressure'],text=True,stderr=subprocess.STDOUT); m=re.search(r'Pages free:\s+(\d+)',s); return round(int(m.group(1))*100/1048576,2) if m else None
def snap(label,pid=None):
 x={'at':datetime.now(timezone.utc).isoformat(),'label':label,'swap_mib':swap(),'free_percent':free()}
 if pid:
  try:x['ps']=subprocess.check_output(['ps','-o','pid,rss,etime,command','-p',str(pid)],text=True)
  except:pass
 return x
def get(url, data=None):
 req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'} if data else {})
 return urllib.request.urlopen(req,timeout=5).read().decode()
initial=snap('initial'); (OUT/'initial.json').write_text(json.dumps(initial,indent=2)); results=[]
for slots,policy in ARMS:
 arm=OUT/f'slots-{slots}-{policy}'; arm.mkdir(); before=snap('before')
 cmd=[str(BIN),'--model',str(MODEL),'--port',str(PORT),'--max-context','8192','--prompt-cache-mode','off','--expert-cache-slots',str(slots),'--expert-cache-policy',policy]
 srv=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True); ready=False; server_samples=[]
 for i in range(90):
  time.sleep(1)
  try:get(f'http://127.0.0.1:{PORT}/v1/models'); ready=True; break
  except:pass
 if not ready:
  os.killpg(srv.pid,signal.SIGTERM); o,e=srv.communicate(timeout=20); rec={'slots':slots,'policy':policy,'command':cmd,'before':before,'server_ready':False,'server_stdout':o,'server_stderr':e}; results.append(rec); break
 payload=json.dumps({'model':'qwen3.6-35b-a3b','messages':[{'role':'user','content':PROMPT}],'temperature':0,'seed':12345,'max_tokens':64,'stream':False}).encode()
 req=subprocess.Popen(['curl','--silent','--show-error','--max-time','600','-H','Content-Type: application/json','--data-binary','@-',f'http://127.0.0.1:{PORT}/v1/chat/completions'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=False,start_new_session=True)
 req.stdin.write(payload); req.stdin.close(); req.stdin=None; started=time.monotonic(); stopped=False
 while req.poll() is None:
  time.sleep(3); z=snap('request-sample',srv.pid); z['elapsed_s']=round(time.monotonic()-started,3); server_samples.append(z)
  if z['swap_mib']-before['swap_mib']>LIMIT or z['free_percent']<15:
   os.killpg(req.pid,signal.SIGTERM); stopped=True; break
 try:o,er=req.communicate(timeout=30)
 except: os.killpg(req.pid,signal.SIGKILL); o,er=req.communicate(); stopped=True
 after=snap('after-request'); os.killpg(srv.pid,signal.SIGTERM)
 try:so,se=srv.communicate(timeout=30)
 except:os.killpg(srv.pid,signal.SIGKILL); so,se=srv.communicate()
 (arm/'response.json').write_bytes(o); (arm/'curl-stderr.txt').write_bytes(er); (arm/'server-stdout.txt').write_text(so); (arm/'server-stderr.txt').write_text(se)
 rec={'slots':slots,'policy':policy,'command':cmd,'before':before,'after':after,'server_ready':True,'server_samples':server_samples,'curl_returncode':req.returncode,'stopped_by_guard':stopped,'wall_s':round(time.monotonic()-started,3),'response':o.decode(errors='replace'),'server_stderr':se}
 (arm/'result.json').write_text(json.dumps(rec,indent=2)); results.append(rec)
 if stopped:break
summary={'experiment':'EXP-014','hypothesis':'Qwen3.6 cache slots/policy can beat 16-slot baseline without unsafe swap growth.','runtime_commit':'3a892465729406944778a24064664d817617f558','model':'mlx-community/Qwen3.6-35B-A3B-4bit@38740b847e4cb78f352aba30aa41c76e08e6eb46 / EXP-005 qwen36.gturbo','initial':initial,'results':results,'safety':{'max_incremental_swap_mib':LIMIT,'minimum_free_percent':15}}
(ROOT/'raw'/'cache-sweep-latest.json').write_text(json.dumps(summary,indent=2)); print(json.dumps({'output':str(OUT),'arms':[{'slots':r['slots'],'policy':r['policy'],'ready':r.get('server_ready'),'returncode':r.get('curl_returncode'),'stopped':r.get('stopped_by_guard'),'wall_s':r.get('wall_s'),'swap_delta':r.get('after',{}).get('swap_mib',0)-r['before']['swap_mib'] if r.get('after') else None} for r in results]},indent=2))
