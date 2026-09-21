#!/usr/bin/env python3
"""Header + bounded-tensor comparison: Carnice merged BF16 vs Qwen BF16."""
import hashlib, json, pathlib, random, urllib.parse, urllib.request
from datetime import datetime, timezone
ROOT=pathlib.Path('/Users/<user>/HermesProjects/Local-LLM-Lab')
OUT=ROOT/'results/raw/EXP-007'
SRC=OUT/'source'
UA={'User-Agent':'Local-LLM-Lab-EXP-007/1.0'}

def get(url, headers=None):
 h=dict(UA); h.update(headers or {})
 with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=90) as r: return r.read()
def api(repo): return json.loads(get('https://huggingface.co/api/models/'+urllib.parse.quote(repo,safe='/')))
def tree(repo,rev): return json.loads(get('https://huggingface.co/api/models/{}/tree/{}?recursive=true&expand=true'.format(urllib.parse.quote(repo,safe='/'),urllib.parse.quote(rev,safe=''))))
def resolve(repo,rev,p): return f'https://huggingface.co/{repo}/resolve/{rev}/{p}'
def header(repo,rev,p):
 a=get(resolve(repo,rev,p),{'Range':'bytes=0-7'}); n=int.from_bytes(a,'little')
 b=get(resolve(repo,rev,p),{'Range':f'bytes=8-{7+n}'})
 d=json.loads(b)
 return {k:{'dtype':v.get('dtype'),'shape':v.get('shape'),'offsets':v.get('data_offsets')} for k,v in d.items() if k!='__metadata__'}
def tensor_bytes(repo,rev,file,entry):
 s,e=entry['offsets']; return get(resolve(repo,rev,file),{'Range':f'bytes={8+s}-{8+e-1}'})
def classify(n):
 n=n.lower()
 if '.mlp.experts.' in n: return 'routed_expert'
 if '.mlp.shared_expert' in n: return 'shared_expert'
 if any(x in n for x in ('.q_proj.', '.k_proj.', '.v_proj.', '.o_proj.')): return 'attention_qkvo'
 if '.mlp.gate.' in n: return 'router_gate'
 if 'embed_tokens' in n: return 'embedding'
 if 'lm_head' in n: return 'lm_head'
 if 'norm' in n: return 'norm'
 return 'other'

base='Qwen/Qwen3.6-35B-A3B'; car='samuelcardillo/Carnice-Qwen3.6-MoE-35B-A3B'
base_api, car_api=api(base),api(car); br,cr=base_api['sha'],car_api['sha']
bt,ct=tree(base,br),tree(car,cr)
bfiles=[x['path'] for x in bt if x.get('type')=='file' and x['path'].endswith('.safetensors')]
cfiles=[x['path'] for x in ct if x.get('type')=='file' and x['path'].endswith('.safetensors') and not x['path'].startswith('fp8/')]
# Both root variants should have exactly the BF16 26 shards.
BH={p:header(base,br,p) for p in bfiles}; CH={p:header(car,cr,p) for p in cfiles}
(SRC/'base-api.json').write_text(json.dumps(base_api,indent=2,sort_keys=True)+'\n')
(SRC/'base-tree.json').write_text(json.dumps(bt,indent=2,sort_keys=True)+'\n')
# Build name indexes with source file.
def index(headers): return {name:(file,ent) for file,hs in headers.items() for name,ent in hs.items()}
BI,CI=index(BH),index(CH)
common=sorted(set(BI)&set(CI)); only_base=sorted(set(BI)-set(CI)); only_car=sorted(set(CI)-set(BI))
shape_equal=[n for n in common if BI[n][1]['shape']==CI[n][1]['shape']]
dtype_equal=[n for n in common if BI[n][1]['dtype']==CI[n][1]['dtype']]
classes={}
for n in common:
 c=classify(n); z=classes.setdefault(c,{'common':0,'shape_equal':0,'dtype_equal':0,'examples':[]})
 z['common']+=1; z['shape_equal']+=BI[n][1]['shape']==CI[n][1]['shape']; z['dtype_equal']+=BI[n][1]['dtype']==CI[n][1]['dtype']
 if len(z['examples'])<3: z['examples'].append({'name':n,'base':BI[n][1],'carnice':CI[n][1]})
# Bounded direct content verification: samples are selected deterministically, each must be no more than 4 MiB.
random.seed(7007)
sample=[]
for category, target in [('routed_expert',32),('shared_expert',8),('router_gate',8),('attention_qkvo',8),('norm',16),('other',8)]:
 candidates=[n for n in common if classify(n)==category and BI[n][1]['shape']==CI[n][1]['shape'] and BI[n][1]['dtype']==CI[n][1]['dtype']]
 candidates=[n for n in candidates if BI[n][1]['offsets'][1]-BI[n][1]['offsets'][0] <= 4*1024*1024]
 if len(candidates)>target: candidates=random.sample(candidates,target)
 sample.extend(candidates)
comparisons=[]
for n in sample:
 bf,be=BI[n]; cf,ce=CI[n]
 bb=tensor_bytes(base,br,bf,be); cb=tensor_bytes(car,cr,cf,ce)
 comparisons.append({'name':n,'category':classify(n),'bytes':len(bb),'base_file':bf,'carnice_file':cf,
                     'base_sha256':hashlib.sha256(bb).hexdigest(),'carnice_sha256':hashlib.sha256(cb).hexdigest(),
                     'identical':bb==cb})
bycat={}
for r in comparisons:
 z=bycat.setdefault(r['category'],{'sampled_tensors':0,'identical':0,'bytes':0})
 z['sampled_tensors']+=1;z['identical']+=int(r['identical']);z['bytes']+=r['bytes']
report={'experiment':'EXP-007','phase':'phase2_tensor_compatibility','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'method':{'headers':'complete SafeTensors headers only; no checkpoint payload persisted','content':'bounded deterministic direct byte comparison of tensors <=4 MiB; hashed immediately; total transfer listed below'},
 'base':{'repo':base,'revision':br,'files':bfiles},'carnice':{'repo':car,'revision':cr,'files':cfiles},
 'names':{'base':len(BI),'carnice':len(CI),'common':len(common),'only_base_count':len(only_base),'only_carnice_count':len(only_car),'only_base_examples':only_base[:20],'only_carnice_examples':only_car[:20]},
 'compatibility':{'shape_equal_common':len(shape_equal),'dtype_equal_common':len(dtype_equal),'classes':classes},
 'bounded_content_comparison':{'total_tensors':len(comparisons),'total_bytes':sum(x['bytes'] for x in comparisons),'by_category':bycat,'records':comparisons},
 'interpretation_limit':'Equality of sampled exported BF16 tensors supports but cannot prove equality of every expert tensor. File/shard hashes cannot establish tensor equality across different sharding/serialization.'}
(OUT/'tensor-compatibility.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'base_revision':br,'carnice_revision':cr,'tensor_names':{'base':len(BI),'carnice':len(CI),'common':len(common)},'sample':{'tensors':len(comparisons),'bytes':sum(x['bytes'] for x in comparisons),'by_category':bycat}},indent=2))
