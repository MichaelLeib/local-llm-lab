#!/usr/bin/env python3
"""Guarded populated-context/retrieval test for streamed ERNIE."""
from __future__ import annotations
import json, os, re, signal, subprocess, time
from pathlib import Path

EXP = Path.home() / "HermesProjects/Local-LLM-Lab/results/raw/EXP-017-ernie-streamed-gguf"
BIN = EXP / "source/llama.cpp-moe-streaming/build-exp017/bin/llama-cli"
TOK = EXP / "source/llama.cpp-moe-streaming/build-exp017/bin/llama-tokenize"
MODEL = Path.home() / "HermesProjects/Local-LLM-Lab/results/raw/EXP-016-small-moe-feasibility/ernie/gguf/model/ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf"
ROOT = EXP / "context-retrieval-1k-4k-rerun1"
ROOT.mkdir(exist_ok=True)


def text(cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False).stdout

def snap(label):
    return {"timestamp": time.time(), "label": label,
            "vm_stat": text(["vm_stat"]), "memory_pressure": text(["memory_pressure"]),
            "swap": text(["sysctl", "vm.swapusage"])}

def free_pct(s):
    m = re.search(r"free percentage: (\d+)%", s["memory_pressure"])
    return int(m.group(1)) if m else None

def count_tokens(prompt_path):
    out = text([str(TOK), "--log-disable", "--show-count", "-m", str(MODEL), "-f", str(prompt_path)])
    m = re.search(r"Total number of tokens:\s*(\d+)", out)
    if not m:
        raise RuntimeError(f"could not parse tokenizer output: {out[-1000:]}")
    return int(m.group(1)), out

def build_prompt(target_words, secret):
    # Each line is deliberately ordinary filler; the last record is the only retrieval target.
    filler = "A quiet archive contains ordinary records about rivers, maps, stones, and weather.\n" * target_words
    return filler + f"\nIMPORTANT RETRIEVAL RECORD: The secret code is {secret}.\nQuestion: What is the secret code? Answer with only the code.\n"

def run_arm(label, words, ctx, secret):
    arm = ROOT / label; arm.mkdir(exist_ok=True)
    prompt = build_prompt(words, secret)
    (arm / "prompt.txt").write_text(prompt)
    n_tok, token_log = count_tokens(arm / "prompt.txt")
    (arm / "tokenize.log").write_text(token_log)
    cmd = [str(BIN), "-m", str(MODEL),
           "--moe-stream-cache", "18s", "--moe-stream-io-threads", "2", "--moe-stream-direct",
           "--no-mmap", "--no-warmup", "--fit", "off", "-ngl", "99", "-c", str(ctx), "-b", "512", "-ub", "1",
           "-n", "128", "--temp", "0", "--seed", "1234", "--single-turn", "--simple-io", "-f", str(arm / "prompt.txt")]
    (arm / "command.json").write_text(json.dumps(cmd, indent=2) + "\n")
    before = snap("before"); (arm / "before.json").write_text(json.dumps(before, indent=2) + "\n")
    with (arm / "run.log").open("w") as log:
        log.write("input_tokens=" + str(n_tok) + "\ncommand=" + " ".join(cmd) + "\n")
        log.flush()
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        samples=[]; abort=None
        while p.poll() is None:
            s=snap("active"); s["pid"]=p.pid; samples.append(s)
            free=free_pct(s)
            if free is not None and free < 6:
                abort={"reason":"free_memory_below_6_percent", "free_percent":free, "timestamp":time.time()}
                os.killpg(p.pid, signal.SIGTERM)
                try: p.wait(timeout=20)
                except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL)
                break
            time.sleep(2)
        code=p.wait()
    after=snap("after")
    (arm / "samples.json").write_text(json.dumps(samples, indent=2) + "\n")
    (arm / "after.json").write_text(json.dumps(after, indent=2) + "\n")
    log_text=(arm / "run.log").read_text(errors="replace")
    result={"label":label,"input_tokens":n_tok,"ctx":ctx,"exit_code":code,"aborted":abort,
            "secret":secret,"secret_visible_in_output":secret in log_text,
            "minimum_free_percent":min([free_pct(x) for x in samples if free_pct(x) is not None] or [free_pct(before),free_pct(after)])}
    (arm / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result

results=[]
for cfg in [("1k-populated", 58, 2048, "ORBIT-271"), ("4k-populated", 232, 8192, "CEDAR-914")]:
    r=run_arm(*cfg); results.append(r)
    if r["exit_code"] != 0 or r["aborted"] is not None:
        break
(ROOT / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
