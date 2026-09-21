#!/usr/bin/env python3
"""Plan Carnice sparse Q/K/V/O retrieval from cached SafeTensors headers only."""
import hashlib,json,pathlib,urllib.request,urllib.error
from datetime import datetime,timezone
ROOT=pathlib.Path('/Users/<user>/HermesProjects/Local-LLM-Lab'); OUT=ROOT/'results/raw/EXP-007'
head=json.loads((OUT/'source/safetensors-headers.json').read_text())['headers']['carnice']
# Ignore fp8; the proposed sparse source is the merged root BF16 release.
records=[]
for f in head:
 if f['file'].startswith('fp8/'): continue
 hbytes=f['header_bytes']
 for name,e in f['tensors'].items():
  # Actual QLoRA module targets in Qwen full-attention blocks plus the MTP block.
  if '.self_attn.' in name and name.endswith(('.q_proj.weight','.k_proj.weight','.v_proj.weight','.o_proj.weight')):
   start,end=e['offsets']; size=end-start
   records.append({'name':name,'shard':f['file'],'dtype':e['dtype'],'shape':e['shape'],'safetensors_data_offsets':e['offsets'],'http_range':{'start':8+hbytes+start,'end_inclusive':8+hbytes+end-1,'length':size},'target_class':'QLoRA Q/K/V/O module'})
records.sort(key=lambda x:(x['shard'],x['http_range']['start']))
# A one-byte range request proves an actual 206/content-range path, without acquiring any tensor range.
probe=records[0]
url=f"https://huggingface.co/samuelcardillo/Carnice-Qwen3.6-MoE-35B-A3B/resolve/d86a0cea3cd6794a294ad72a08598294249c761e/{probe['shard']}"
def probe_once(i):
 req=urllib.request.Request(url,headers={'User-Agent':'Local-LLM-Lab-EXP-007/1.0','Range':f"bytes={probe['http_range']['start']}-{probe['http_range']['start']}"})
 with urllib.request.urlopen(req,timeout=60) as r:
  body=r.read(); h=dict(r.headers)
  return {'attempt':i,'status':getattr(r,'status',None),'final_url':r.geturl(),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'content_range':h.get('Content-Range'),'accept_ranges':h.get('Accept-Ranges'),'x_xet_hash':h.get('X-Xet-Hash'),'x_linked_size':h.get('X-Linked-Size'),'etag':h.get('ETag')}
probes=[]; errors=[]
for i in range(1,4):
 try: probes.append(probe_once(i))
 except Exception as e: errors.append({'attempt':i,'error':repr(e)})
by_shard={}
for r in records: by_shard.setdefault(r['shard'],{'tensors':0,'bytes':0});by_shard[r['shard']]['tensors']+=1;by_shard[r['shard']]['bytes']+=r['http_range']['length']
plan={'experiment':'EXP-007','phase':'sparse_range_preacquisition_plan','created_at_utc':datetime.now(timezone.utc).isoformat(),'source':{'repo':'samuelcardillo/Carnice-Qwen3.6-MoE-35B-A3B','revision':'d86a0cea3cd6794a294ad72a08598294249c761e','format':'root BF16 SafeTensors only; fp8 excluded'},'selection_rule':'Every serialized Q/K/V/O projection tensor in main-model and MTP self-attention. This is the conservative complete set implied by the published LoRA targets; observed samples show changed main-model Q/K/V, but a range importer must not infer unchanged status from samples.','tensor_count':len(records),'total_bf16_bytes':sum(r['http_range']['length'] for r in records),'per_shard':by_shard,'records':records,'range_probe':{'method':'Three independent one-byte requests at the first selected tensor data byte. SafeTensors data start is 8 + header_bytes + data_offset; this corrects the earlier range sampler offset calculation.','record':probe,'attempts':probes,'errors':errors,'reliable':len(probes)==3 and not errors and all(x['status']==206 and x['bytes']==1 for x in probes) and len({x['sha256'] for x in probes})==1},'limitations':['This plan does not establish that all selected tensors changed; it conservatively acquires every eligible training target.','No selected tensor payload was persisted by this planning operation; the probe obtained one byte per attempt.','Stock BF16-to-MLX-affine conversion must be separately validated before Carnice payload acquisition.']}
(OUT/'sparse-range-manifest.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n')
print(json.dumps({'tensor_count':plan['tensor_count'],'total_bf16_bytes':plan['total_bf16_bytes'],'per_shard':by_shard,'range_reliable':plan['range_probe']['reliable'],'probes':probes,'errors':errors},indent=2))
