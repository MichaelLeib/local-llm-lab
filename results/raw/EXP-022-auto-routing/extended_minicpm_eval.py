#!/usr/bin/env python3
"""Extended direct quality/structured-output checks for the MiniCPM candidate."""
import json, time, urllib.request
from pathlib import Path

BASE='http://127.0.0.1:8921/v1/chat/completions'
OUT=Path('/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-022-auto-routing/raw/minicpm5-2b-q4km/extended.json')

def post(payload):
    req=urllib.request.Request(BASE,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=180) as r: x=json.loads(r.read().decode())
    return {'seconds':round(time.monotonic()-t,3),'response':x}

tools=[{'type':'function','function':{'name':'terminal','description':'Run a safe read-only shell command on the local computer.','parameters':{'type':'object','properties':{'command':{'type':'string'}},'required':['command']}}}, {'type':'function','function':{'name':'web_search','description':'Search the public web for current facts.','parameters':{'type':'object','properties':{'query':{'type':'string'}},'required':['query']}}}]
checks=[]
for name,prompt,expect in [
 ('basic_capital','What is the capital of France? Answer in one word.','Paris'),
 ('branch_tool','Find the current git branch. Use terminal; do not guess.','terminal'),
 ('status_tool','Check whether the current repository has uncommitted changes. Use terminal; do not guess.','terminal'),
 ('symbol_tool','Find occurrences of the symbol _handle_runs in this repository. Use terminal.','terminal'),
 ('port_tool','Identify what process listens on TCP port 8901. Use terminal.','terminal'),
 ('error_explain','Explain concisely what "connection refused" means for a localhost HTTP request.','refused'),
 ('current_research_tool','Find the official current Python release. Use web_search rather than guessing.','web_search'),
]:
    r=post({'model':'minicpm5-2b-q4km','messages':[{'role':'user','content':prompt}],'tools':tools if expect in ('terminal','web_search') else None,'temperature':0,'max_tokens':192,'chat_template_kwargs':{'enable_thinking':False}})
    msg=(r['response'].get('choices') or [{}])[0].get('message',{})
    calls=msg.get('tool_calls') or []
    r['name']=name; r['expect']=expect; r['content']=msg.get('content',''); r['tool_names']=[x.get('function',{}).get('name') for x in calls]
    checks.append(r)

route_prompts=[
 ('route_fast','What command shows my current git branch?'),
 ('route_think','A local HTTP service fails intermittently with connection refused. Compare likely causes and give an investigation order.'),
 ('route_deep','Design and implement an offline-first multi-profile mobile frontend with secure session synchronization, including migrations and a test plan.'),
]
for name,prompt in route_prompts:
  r=post({'model':'minicpm5-2b-q4km','messages':[{'role':'system','content':'Classify the request for a local agent router. Output exactly one token: FAST, THINK, or DEEP. FAST=direct fact or one tool. THINK=multi-step investigation/light coding. DEEP=architecture, broad multi-file autonomous work, difficult debugging, or serious research.'},{'role':'user','content':prompt}],'temperature':0,'max_tokens':5,'chat_template_kwargs':{'enable_thinking':False}})
  r['name']=name; r['content']=((r['response'].get('choices') or [{}])[0].get('message',{}).get('content',''))
  checks.append(r)

history='''DECISIONS: keep gateway loopback-only; use port 8901 for FAST and port 8919 for Ornith.\nUNRESOLVED TODO: test recovery after restarting fast server.\nFILES: /Users/<user>/.hermes/bin/hermes-local-model and HermesMobile/src/app/core/run-gateway-impl.ts.\nCOMMAND: hermes-local-model start fast.\nERROR: ECONNREFUSED 127.0.0.1:8901.\nCONSTRAINT: do not delete model files or alter production data.\nPREFERENCE: user wants Auto default with Fast and Deep manual escape hatches.\nMEASUREMENT: Ornith Q6_K decode 12.4-12.7 tok/s; warm session 4.7 seconds at 99% cache.\nCODE DECISION: preserve X-Hermes-Session-Key when calling /v1/runs.\n'''
r=post({'model':'minicpm5-2b-q4km','messages':[{'role':'system','content':'Compress the history faithfully. Preserve every identifier, path, command, port, unresolved TODO, error, constraint, preference, and numeric measurement. Return concise bullets only.'},{'role':'user','content':history}],'temperature':0,'max_tokens':350,'chat_template_kwargs':{'enable_thinking':False}})
r['name']='compression_preservation'; r['content']=((r['response'].get('choices') or [{}])[0].get('message',{}).get('content',''))
checks.append(r)
OUT.write_text(json.dumps(checks,indent=2))
for x in checks:
 print(x['name'], x.get('tool_names'), repr(x.get('content','')[:260]), x['seconds'])
