#!/usr/bin/env python3
"""EXP-017 physical-ubatch ladder; all model/runtime parameters fixed but -ub."""
from __future__ import annotations
import json, os, re, signal, subprocess, time
from pathlib import Path

EXP = Path.home() / "HermesProjects/Local-LLM-Lab/results/raw/EXP-017-ernie-streamed-gguf"
ROOT = EXP / "ubatch-ladder-4k"
ROOT.mkdir(exist_ok=True)
BIN = EXP / "source/llama.cpp-moe-streaming/build-exp017/bin/llama-cli"
MODEL = Path.home() / "HermesProjects/Local-LLM-Lab/results/raw/EXP-016-small-moe-feasibility/ernie/gguf/model/ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf"
PROMPT = EXP / "context-retrieval-1k-4k-rerun1/4k-populated/prompt.txt"
INPUT_TOKENS = 3982
BASE = [str(BIN), "-m", str(MODEL), "--moe-stream-cache", "18s", "--moe-stream-io-threads", "2", "--moe-stream-direct", "--no-mmap", "--no-warmup", "--fit", "off", "-ngl", "99", "-c", "8192", "-b", "512"]
TAIL = ["-n", "128", "--temp", "0", "--seed", "1234", "--single-turn", "--simple-io", "-f", str(PROMPT)]

def text(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False).stdout

def intmatch(text_, pat):
    m=re.search(pat,text_); return int(m.group(1)) if m else None

def floatmatch(text_, pat):
    m=re.search(pat,text_); return float(m.group(1)) if m else None

def snapshot(label, model_pid=None):
    vm=text(["vm_stat"]); pressure=text(["memory_pressure"]); swap=text(["sysctl","vm.swapusage"])
    ps=text(["ps","-p",str(model_pid),"-o","pid=,rss=,etime=,command="]) if model_pid else ""
    return {"timestamp":time.time(),"label":label,"model_pid":model_pid,"vm_stat":vm,"memory_pressure":pressure,"swap":swap,"process":ps,
            "free_percent":intmatch(pressure,r"free percentage: (\d+)%"),"swap_used_mib":floatmatch(swap,r"used = ([0-9.]+)M"),
            "swapouts":intmatch(vm,r"Swapouts:\s+(\d+)"),"swapins":intmatch(vm,r"Swapins:\s+(\d+)"),"pageouts":intmatch(vm,r"Pageouts:\s+(\d+)"),
            "rss_kib":intmatch(ps,r"^\s*\d+\s+(\d+)")}

def unsafe(before, now):
    # Existing resident swap is baseline. Abort only on severe new pressure/thrashing.
    if now["free_percent"] is not None and now["free_percent"] < 6:
        return f"free_memory_{now['free_percent']}pct"
    if (now["swap_used_mib"] is not None and before["swap_used_mib"] is not None and
        now["swap_used_mib"] - before["swap_used_mib"] > 512 and
        now["swapouts"] is not None and before["swapouts"] is not None and now["swapouts"] - before["swapouts"] > 100):
        return "swap_growth_over_512MiB_with_swapouts"
    return None

def parse_rates(log):
    m=re.search(r"\[ Prompt: ([0-9.]+) t/s \| Generation: ([0-9.]+) t/s \]",log)
    return {"prompt_tok_s":float(m.group(1)) if m else None,"decode_tok_s":float(m.group(2)) if m else None}

def run(ub):
    arm=ROOT/f"ub{ub}"; arm.mkdir(exist_ok=True)
    cmd=BASE+["-ub",str(ub)]+TAIL
    (arm/"command.json").write_text(json.dumps(cmd,indent=2)+"\n")
    before=snapshot("before"); (arm/"before.json").write_text(json.dumps(before,indent=2)+"\n")
    with (arm/"run.log").open("w") as log:
        log.write(f"input_tokens={INPUT_TOKENS}\nphysical_ubatch={ub}\ncommand="+" ".join(cmd)+"\n"); log.flush()
        p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,text=True,start_new_session=True)
        samples=[]; stopped=None
        while p.poll() is None:
            s=snapshot("active",p.pid); samples.append(s)
            reason=unsafe(before,s)
            if reason:
                stopped={"reason":reason,"timestamp":time.time()}; os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=20)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL)
                break
            time.sleep(2)
        code=p.wait()
    after=snapshot("after")
    logtext=(arm/"run.log").read_text(errors="replace")
    rates=parse_rates(logtext)
    vals=[x["free_percent"] for x in samples if x["free_percent"] is not None]
    rss=[x["rss_kib"] for x in samples if x["rss_kib"] is not None]
    result={"ubatch":ub,"input_tokens":INPUT_TOKENS,"context":8192,"logical_batch":512,"generated_token_cap":128,
            "exit_code":code,"protective_stop":stopped,"wall_seconds":after["timestamp"]-before["timestamp"],"minimum_free_percent":min(vals) if vals else None,
            "peak_rss_kib":max(rss) if rss else None,"swap_delta_mib":after["swap_used_mib"]-before["swap_used_mib"],
            "swapouts_delta":after["swapouts"]-before["swapouts"],"swapins_delta":after["swapins"]-before["swapins"],"pageouts_delta":after["pageouts"]-before["pageouts"],
            "retrieval_needle_in_visible_output":"CEDAR-914" in logtext,"visible_output_ended_at_cap": "Exiting..." in logtext,**rates}
    (arm/"samples.json").write_text(json.dumps(samples,indent=2)+"\n")
    (arm/"after.json").write_text(json.dumps(after,indent=2)+"\n")
    (arm/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

results=[]
for ub in [2,4,8,16]:
    r=run(ub); results.append(r)
    if r["exit_code"] != 0 or r["protective_stop"]:
        break
# Optional 32 only after all mandated arms have remained objectively healthy.
if len(results)==4 and all(r["minimum_free_percent"] is not None and r["minimum_free_percent"] >= 20 and r["swapouts_delta"] == 0 and r["exit_code"] == 0 for r in results):
    results.append(run(32))
(ROOT/"summary.json").write_text(json.dumps(results,indent=2)+"\n")
print(json.dumps(results,indent=2))
