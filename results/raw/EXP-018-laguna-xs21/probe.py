#!/usr/bin/env python3
"""OpenAI-compatible deterministic timing and retrieval probe (stdlib only)."""
import json, sys, time, urllib.request
if len(sys.argv)!=5: raise SystemExit('usage: probe.py BASE_URL TARGET_WORDS MODE(short|needle) OUT_JSON')
base, target, mode, out=sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
needle='LAGUNA_NEEDLE_ORCHID_7391'
unit='The coastal observatory records tides, winds, minerals, and migratory birds in a durable notebook. '
text=(unit*((target*5)//len(unit.split())+1))
if mode=='needle':
    middle=len(text)//2; text=text[:middle]+f' Critical archival identifier: {needle}. '+text[middle:]
    question='What is the exact archival identifier? Answer only the identifier.'
else: question='State the single central purpose of this passage in one sentence.'
payload={'model':'laguna-xs21','messages':[{'role':'system','content':'Answer accurately and concisely.'},{'role':'user','content':text+'\n\n'+question}],'temperature':0,'max_tokens':96,'stream':False}
req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
t0=time.perf_counter()
try:
 with urllib.request.urlopen(req,timeout=1800) as r: data=json.loads(r.read())
 elapsed=time.perf_counter()-t0
 usage=data.get('usage',{}); content=data['choices'][0]['message'].get('content','')
 result={'ok':True,'elapsed_seconds':elapsed,'usage':usage,'content':content,'needle_correct':needle in content,'target_words':target,'mode':mode,'raw_response':data}
except Exception as e:
 result={'ok':False,'elapsed_seconds':time.perf_counter()-t0,'error':repr(e),'target_words':target,'mode':mode}
open(out,'w').write(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='raw_response'},separators=(',',':')))
