import json, os, pathlib, subprocess, sys, time
from pathlib import Path
model_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
def snap():
    def sh(cmd):
        try: return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
        except Exception as e: return repr(e)
    return {'rss': sh(['ps','-o','rss=','-p',str(os.getpid())]), 'swap': sh(['sysctl','-n','vm.swapusage']), 'memory_pressure': sh(['memory_pressure'])}
t0=time.time()
import optiq
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler
model,tok=load(str(model_path), tokenizer_config={'trust_remote_code': True})
load_s=time.time()-t0
prompt=tok.apply_chat_template([{'role':'user','content':'Identify yourself as Nanbeige4.2-3B. Which number is bigger, 9.11 or 9.8? Answer in one sentence.'}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
start=time.time()
text=generate(model,tok,prompt,max_tokens=128,sampler=make_sampler(temp=0.6,top_p=0.95))
elapsed=time.time()-start
row={'model':str(model_path),'load_s':load_s,'generation_s':elapsed,'output_tokens':len(tok.encode(text)),'decode_tok_s':len(tok.encode(text))/elapsed if elapsed else None,'output':text,'prompt_chars':len(prompt),'prompt_tokens':len(tok.encode(prompt)),'after':snap()}
out_path.write_text(json.dumps(row,ensure_ascii=False,indent=2))
print(json.dumps({'load_s':load_s,'generation_s':elapsed,'output':text,'after':row['after']},ensure_ascii=False))
