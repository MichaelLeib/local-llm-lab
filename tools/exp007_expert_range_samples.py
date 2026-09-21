#!/usr/bin/env python3
"""Bounded byte-range sampling of routed expert tensors (no full tensors)."""
import hashlib,json,pathlib,urllib.request
ROOT=pathlib.Path('/Users/<user>/HermesProjects/Local-LLM-Lab'); OUT=ROOT/'results/raw/EXP-007'; report=json.loads((OUT/'tensor-compatibility.json').read_text())
base,br=report['base']['repo'],report['base']['revision']; car,cr=report['carnice']['repo'],report['carnice']['revision']
def get(url,h=None):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Local-LLM-Lab-EXP-007/1.0',**(h or {})}),timeout=90) as r:return r.read()
def url(repo,rev,p):return f'https://huggingface.co/{repo}/resolve/{rev}/{p}'
def header(repo,rev,p):
 n=int.from_bytes(get(url(repo,rev,p),{'Range':'bytes=0-7'}),'little'); d=json.loads(get(url(repo,rev,p),{'Range':f'bytes=8-{7+n}'}));return {k:v for k,v in d.items() if k!='__metadata__'}
def idx(repo,rev,fs):return {n:(p,e) for p in fs for n,e in header(repo,rev,p).items()}
BI=idx(base,br,report['base']['files']);CI=idx(car,cr,report['carnice']['files'])
experts=sorted(n for n in BI if '.mlp.experts.' in n and n in CI)
# 12 tensors distributed by layer/component; sample three 1MiB blocks per tensor.
selected=[]
for n in experts:
 layer=int(n.split('.layers.')[1].split('.')[0])
 if layer in (0,3,7,11,15,19,23,27,31,35,39) and n.endswith(('down_proj','gate_up_proj')):
  selected.append(n)
# exactly 12: deterministic spread from the available set
selected=selected[::max(1,len(selected)//12)][:12]
records=[]; unit=1024*1024
for n in selected:
 bf,be=BI[n];cf,ce=CI[n]; s,e=be['data_offsets']; size=e-s
 points=sorted(set([0,max(0,(size-unit)//2),max(0,size-unit)]))
 chunks=[]
 for off in points:
  a=get(url(base,br,bf),{'Range':f'bytes={8+s+off}-{8+s+off+min(unit,size-off)-1}'})
  b=get(url(car,cr,cf),{'Range':f'bytes={8+ce["data_offsets"][0]+off}-{8+ce["data_offsets"][0]+off+min(unit,size-off)-1}'})
  chunks.append({'offset':off,'bytes':len(a),'base_sha256':hashlib.sha256(a).hexdigest(),'carnice_sha256':hashlib.sha256(b).hexdigest(),'identical':a==b})
 records.append({'name':n,'shape_base':be['shape'],'shape_carnice':ce['shape'],'dtype_base':be['dtype'],'dtype_carnice':ce['dtype'],'tensor_bytes':size,'ranges':chunks,'all_sampled_ranges_identical':all(x['identical'] for x in chunks)})
out={'method':'Three 1MiB direct byte ranges (start/middle/end) per sampled routed-expert tensor. No full expert tensor or checkpoint was downloaded or persisted. This is sample evidence, not an all-bytes proof.','sampled_tensors':len(records),'total_transferred_bytes':sum(sum(x['bytes']*2 for x in r['ranges']) for r in records),'all_ranges_identical':all(r['all_sampled_ranges_identical'] for r in records),'records':records}
(OUT/'expert-byte-range-samples.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'sampled_tensors':len(records),'total_transferred_bytes':out['total_transferred_bytes'],'all_ranges_identical':out['all_ranges_identical'],'identical_tensors':sum(r['all_sampled_ranges_identical'] for r in records)},indent=2))
