#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys, time, urllib.request

base = pathlib.Path(sys.argv[1])
url = sys.argv[2].rstrip('/')
target = int(sys.argv[3])
label = sys.argv[4]

def post(path, obj, timeout=60):
    req = urllib.request.Request(url + path, data=json.dumps(obj).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def snap():
    def run(cmd):
        try: return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
        except Exception as e: return str(e)
    rss = run(['ps','-o','rss=','-p',os.environ.get('CANDIDATE_PID','')]) if os.environ.get('CANDIDATE_PID') else ''
    return {
        'time': time.time(),
        'rss_kib': int(rss.split()[0]) if rss.split() and rss.split()[0].isdigit() else None,
        'swap': run(['sysctl','-n','vm.swapusage']),
        'vm_stat': run(['vm_stat']),
        'memory_pressure': run(['memory_pressure']),
    }

unit = f'The archive entry records a neutral observation for deterministic context benchmark rung {label}. '
needle = f'NANBEIGE_CONTEXT_NEEDLE_{label.upper()}_7391'
# Build a prompt near target tokenizer tokens, then append a unique needle and query.
lo, hi = 1, max(2, target * 2)
def count(s): return len(post('/tokenize', {'content': s}, timeout=120)['tokens'])
while lo < hi:
    mid = (lo + hi) // 2
    if count(unit * mid) < target - 100: lo = mid + 1
    else: hi = mid
filler = unit * lo
while count(filler) > target - 100 and lo > 1:
    lo -= 1; filler = unit * lo
prefix = filler + '\nBuried record: ' + needle + '\n'
actual = count(prefix)
messages = [{'role':'user','content':prefix + '\nWhat is the exact buried record? Reply with only the identifier.'}]
row = {'label':label,'requested_target_tokens':target,'actual_prompt_text_tokens':count(messages[0]['content']),'before':snap()}
start=time.time()
try:
    d=post('/v1/chat/completions', {'model':'nanbeige','messages':messages,'temperature':0.0,'top_p':1.0,'max_tokens':64,'stream':False}, timeout=1800)
    row['http_ok']=True; row['response']=d; row['elapsed_s']=time.time()-start
    c=d.get('choices',[{}])[0]
    text=(c.get('message') or {}).get('content','')
    row['retrieval_correct']=needle in text
    row['finish_reason']=c.get('finish_reason')
except Exception as e:
    row['http_ok']=False; row['error']=repr(e); row['elapsed_s']=time.time()-start
row['after']=snap()
(base / f'{label}.json').write_text(json.dumps(row, indent=2, ensure_ascii=False))
print(json.dumps({'label':label,'actual_prompt_text_tokens':row['actual_prompt_text_tokens'],'elapsed_s':row.get('elapsed_s'),'retrieval_correct':row.get('retrieval_correct'),'finish_reason':row.get('finish_reason'),'timings':row.get('response',{}).get('timings'),'error':row.get('error')},ensure_ascii=False))
