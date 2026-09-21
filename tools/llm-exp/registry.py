#!/usr/bin/env python3
import json,sys
from pathlib import Path
FIELDS=['experiment_id','model','revision','runtime','quantization','full_config','context_allocation','prompt_tokens','output_tokens','prefill_seconds','decode_tps','ttft_seconds','memory_swap_stats','correctness','exit_code','classification','raw_path']
if len(sys.argv)!=3: raise SystemExit('usage: registry.py RESULTS_JSONL RECORD_JSON')
p=Path(sys.argv[1]); data=json.loads(Path(sys.argv[2]).read_text()); missing=[x for x in FIELDS if x not in data]
if missing: raise SystemExit('missing fields: '+','.join(missing))
p.parent.mkdir(parents=True,exist_ok=True)
with p.open('a') as f:f.write(json.dumps(data,separators=(',',':'))+'\n')
print('registered',data['experiment_id'],data['classification'])
