#!/usr/bin/env python3
"""Map sparse Carnice Q/K/V/O targets to stock MLX-4bit representation sizes."""
import json,pathlib
ROOT=pathlib.Path('/Users/<user>/HermesProjects/Local-LLM-Lab'); OUT=ROOT/'results/raw/EXP-007'
allh=json.loads((OUT/'source/safetensors-headers.json').read_text())['headers']
# Each source header stores only tensor metadata; no payload acquisition.
def index(group,skip_fp8=False):
 out={}
 for f in group:
  if skip_fp8 and f['file'].startswith('fp8/'):continue
  for n,e in f['tensors'].items():out[n]=(f['file'],e)
 return out
C=index(allh['carnice'],True); M=index(allh['stock'])
targets=json.loads((OUT/'sparse-range-manifest.json').read_text())['records']
rows=[]; missing=[]
for t in targets:
 # Slipstream's stock MLX source contains the ten main full-attention layers only;
 # it intentionally has no MTP tensors and the current runtime does not consume them.
 n=t['name']
 if not n.startswith('model.language_model.'):
  missing.append({'carnice':n,'reason':'MTP tensor: absent from frozen stock MLX source/runtime scope'})
  continue
 mlx='language_model.model.'+n[len('model.language_model.'):]
 if mlx not in M:
  missing.append({'carnice':n,'expected_mlx':mlx});continue
 f,e=M[mlx]
 group=[(mlx,f,e)]
 # MLX tensor sidecars are siblings of the base name, not children of `.weight`.
 base=mlx.removesuffix('.weight')
 for suffix in ('.scales','.biases'):
  companion=base+suffix
  if companion not in M: missing.append({'carnice':n,'expected_mlx_companion':companion})
  else:group.append((companion,*M[companion]))
 rows.append({'carnice_tensor':n,'mlx_base':mlx,'source_bf16_bytes':t['http_range']['length'],'mlx_records':[{'name':x,'shard':ff,'dtype':ee['dtype'],'shape':ee['shape'],'bytes':ee['offsets'][1]-ee['offsets'][0]} for x,ff,ee in group],'mlx_total_bytes':sum(ee['offsets'][1]-ee['offsets'][0] for _,_,ee in group)})
out={'all_training_targets':len(targets),'runtime_applicable_targets':len(rows),'missing_or_out_of_scope':missing,'source_bf16_bytes_runtime_scope':sum(x['source_bf16_bytes'] for x in rows),'stock_mlx_quantized_record_bytes':sum(x['mlx_total_bytes'] for x in rows),'rows':rows,'note':'MLX stock representation is a packed U32 weight plus sibling `.scales`/`.biases`; this is the exact target layout used by the frozen importer, but the importer copies this representation and does not quantize BF16 itself.'}
(OUT/'stock-mlx-projection-layout.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:out[k] for k in ('all_training_targets','runtime_applicable_targets','missing_or_out_of_scope','source_bf16_bytes_runtime_scope','stock_mlx_quantized_record_bytes')},indent=2))
