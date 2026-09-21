#!/usr/bin/env python3
"""EXP-022 deterministic direct-quality gate; stdlib only."""
from __future__ import annotations
import json, re, subprocess, sys, time, urllib.request
from pathlib import Path

if len(sys.argv) != 5:
    raise SystemExit("usage: direct_quality.py ARM BASE_URL MODEL OUT_DIR")
arm, base, model, out_arg = sys.argv[1:]
out = Path(out_arg); out.mkdir(parents=True, exist_ok=True)

TASKS = [
    ("arithmetic", "Compute (87*19)-((47*13)+29).", "1013"),
    ("calendar", "What weekday was 2024-02-29? Reply with the uppercase English weekday.", "THURSDAY"),
    ("bitwise", "Compute the decimal value of binary 101101 XOR binary 011011.", "54"),
    ("units", "Convert 2 hours 45 minutes plus 38 minutes to total seconds.", "12180"),
    ("sorting", "Sort these integers ascending and join them with commas, no spaces: [12,-3,7,7,0,19].", "-3,0,7,7,12,19"),
    ("reverse", "Reverse this exact ASCII string: Hermes-42", "24-semreH"),
    ("logic", "Let P=true, Q=false, R=true. Evaluate (P AND Q) OR (NOT Q AND R). Reply TRUE or FALSE.", "TRUE"),
    ("median", "Find the median of [9,2,13,5,5].", "5"),
    ("hex", "Convert hexadecimal 3AF to decimal.", "943"),
    ("code_trace_1", "What integer does this Python print?\ns=0\nfor i in range(1,6):\n    s += i*i\nprint(s)", "55"),
    ("code_trace_2", "What exact string does this Python print?\ns='ab'\nfor _ in range(3):\n    s=s[::-1]+'x'\nprint(s)", "xxabx"),
    ("json_extract", "Given JSON {\"name\":\"Ada\",\"scores\":[8,17,4],\"meta\":{\"color\":\"blue\"}}, output meta.color, then a pipe, then the maximum score.", "blue|17"),
    ("set_count", "How many distinct integers are in [4,4,1,9,1,2,9,9,3]?", "5"),
    ("modular", "Compute (17^2 + 23^2) mod 10.", "8"),
    ("fraction", "Reduce 84/126 to lowest terms, formatted numerator/denominator.", "2/3"),
    ("instruction", "Return the third word of this sequence exactly as written: red green BLUE yellow", "BLUE"),
]

def snap():
    def run(cmd):
        try: return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=30).strip()
        except Exception as e: return f"ERROR:{e}"
    return {"time": time.time(), "swap": run(["sysctl","vm.swapusage"]), "pressure": run(["memory_pressure"]).splitlines()[-1:] , "vm": run(["vm_stat"])}

def normalize(s):
    s=s.strip()
    s=re.sub(r"\s+", "", s)
    return s.upper()

def extract(content):
    m=re.findall(r"(?im)^\s*FINAL\s*:\s*(.+?)\s*$", content or "")
    return m[-1].strip() if m else ""

def request(prompt):
    payload={"model":model,"messages":[
        {"role":"system","content":"You are in a deterministic evaluation. Solve the user task. Your final line must be exactly `FINAL: <answer>` with no Markdown around that line."},
        {"role":"user","content":prompt}],"temperature":0,"top_p":1,"max_tokens":256,
        "chat_template_kwargs":{"enable_thinking":False},"stream":False}
    req=urllib.request.Request(base+"/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    t=time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r: data=json.loads(r.read())
    wall=time.perf_counter()-t
    choice=data["choices"][0]
    msg=choice.get("message",{})
    return data, wall, msg.get("content") or "", msg.get("reasoning_content") or ""

before=snap(); rows=[]
for idx,(category,prompt,expected) in enumerate(TASKS,1):
    row={"id":idx,"category":category,"prompt":prompt,"expected":expected}
    try:
        data,wall,content,reasoning=request(prompt)
        answer=extract(content)
        row.update({"ok":True,"wall_seconds":round(wall,3),"answer":answer,"content":content,"reasoning":reasoning,"usage":data.get("usage",{}),"finish":data["choices"][0].get("finish_reason"),"pass":normalize(answer)==normalize(expected)})
    except Exception as e:
        row.update({"ok":False,"error":repr(e),"pass":False})
    rows.append(row)
    print(json.dumps({k:row.get(k) for k in ("id","category","answer","expected","pass","wall_seconds","error")}, separators=(",",":")), flush=True)
after=snap()
passed=sum(bool(r["pass"]) for r in rows); total=len(rows)
summary={"arm":arm,"base_url":base,"model":model,"total":total,"passed":passed,"score_percent":round(passed*100/total,2),"by_category":{},"before":before,"after":after,"rows":rows}
for group in {"arithmetic_logic":{"arithmetic","bitwise","units","logic","median","hex","set_count","modular","fraction"},"data_code":{"sorting","reverse","code_trace_1","code_trace_2","json_extract"},"instruction":{"calendar","instruction"}}.items():
    name,cats=group; subset=[r for r in rows if r["category"] in cats]; p=sum(r["pass"] for r in subset); summary["by_category"][name]={"passed":p,"total":len(subset),"score_percent":round(p*100/len(subset),2)}
(out/f"direct-{arm}.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"SUMMARY": {"arm":arm,"passed":passed,"total":total,"score_percent":summary["score_percent"],"by_category":summary["by_category"]}}, separators=(",",":")))
