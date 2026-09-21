#!/usr/bin/env python3
"""Measure one forced MyChatty Auto route including managed lane transition."""
import argparse,json,time,urllib.request
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--route',choices=['fast','deep'],required=True);ap.add_argument('--label',required=True);a=ap.parse_args()
base='http://100.x.x.x.51:9120/h/lllmtinkering/v1'
p={'input':f'Reply with exactly {a.route.upper()}_OK.','session_id':f'exp023-switch-{a.label}','model':a.route,'provider':'local-auto'}
t0=time.monotonic(); req=urllib.request.Request(base+'/runs',data=json.dumps(p).encode(),headers={'Content-Type':'application/json','Idempotency-Key':f'exp023-switch-{a.label}'})
with urllib.request.urlopen(req,timeout=360) as r: run=json.load(r)
t_admit=time.monotonic()
with urllib.request.urlopen(f"{base}/runs/{run['run_id']}/events",timeout=900) as r:raw=r.read().decode()
e=[]
for l in raw.splitlines():
 if l.startswith('data: '):
  try:e.append(json.loads(l[6:]))
  except:pass
res={'route':a.route,'run_id':run['run_id'],'admission_seconds':round(t_admit-t0,3),'total_seconds':round(time.monotonic()-t0,3),'events':e,'raw_sse':raw}
out=Path('raw/e2e');out.mkdir(parents=True,exist_ok=True);(out/f'{a.label}.json').write_text(json.dumps(res,indent=2));(out/f'{a.label}.sse').write_text(raw)
print(json.dumps({'route':a.route,'run_id':res['run_id'],'admission_seconds':res['admission_seconds'],'total_seconds':res['total_seconds'],'final':e[-1] if e else None},indent=2))
