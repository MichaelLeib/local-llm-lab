#!/usr/bin/env python3
"""Record real MyChatty -> Hermes /v1/runs timing under the currently live FAST lane."""
import argparse,json,time,urllib.request
from pathlib import Path
ROOT=Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-023-fast-lane-optimization')
BASE='http://100.x.x.x.51:9120/h/lllmtinkering/v1'

def one(name,prompt,session):
 p={'input':prompt,'session_id':session,'model':'auto','provider':'local-auto'}
 req=urllib.request.Request(BASE+'/runs',data=json.dumps(p).encode(),headers={'Content-Type':'application/json','Idempotency-Key':f'exp023-{session}-{name}'})
 t0=time.monotonic();
 with urllib.request.urlopen(req,timeout=480) as r:run=json.load(r)
 t_start=time.monotonic()
 with urllib.request.urlopen(f"{BASE}/runs/{run['run_id']}/events",timeout=1200) as r:
  raw=r.read().decode()
 events=[]
 for line in raw.splitlines():
  if line.startswith('data: '):
   try:events.append(json.loads(line[6:]))
   except:pass
 first=next((e for e in events if e.get('event') in {'run.delta','tool.started','reasoning.available'}),None)
 final=next((e for e in reversed(events) if str(e.get('event','')).startswith('run.')),{})
 return {'name':name,'run_id':run['run_id'],'request_admission_seconds':round(t_start-t0,4),'total_seconds':round(time.monotonic()-t0,4),'first_event':first,'final':final,'events':events,'raw_sse':raw}

ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--session',required=True);a=ap.parse_args()
result={'label':a.label,'created_at':time.time(),'runs':[
 one('simple','What is the capital of France? Reply with one word.',a.session+'-simple'),
 one('terminal','Use the terminal tool to run git status. Report whether the working tree is clean.',a.session+'-tool'),
 one('web','Use web search to identify the official Hermes Agent documentation URL. Reply with only its URL.',a.session+'-web'),
 one('think','Diagnose two plausible reasons a local HTTP server returns connection refused, then state the first command to run.',a.session+'-think'),
]}
for r in result['runs']: r['raw_sse_path']=str(ROOT/'raw'/'e2e'/f"{a.label}-{r['name']}.sse");(ROOT/'raw'/'e2e').mkdir(parents=True,exist_ok=True);Path(r['raw_sse_path']).write_text(r.pop('raw_sse'))
(ROOT/'raw'/'e2e'/f'{a.label}.json').write_text(json.dumps(result,indent=2))
print(json.dumps([{k:r[k] for k in ('name','run_id','request_admission_seconds','total_seconds')} for r in result['runs']],indent=2))
