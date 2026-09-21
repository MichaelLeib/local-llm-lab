#!/usr/bin/env python3
"""EXP-019 OpenAI-compatible probe: timing, decode rate, tool calls, reasoning split.

Usage: probe.py MODE OUT_JSON [ARGS]
Modes: chat, tool, needle
Emits compact JSON summary to stdout; full response stored in OUT_JSON.
Stdlib only.
"""
import json, sys, time, urllib.request

BASE = "http://127.0.0.1:8919/v1"

def post(path, payload, timeout=1800):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data, time.perf_counter() - t0

def summarize(data, elapsed):
    ch = data["choices"][0]
    msg = ch.get("message", {})
    usage = data.get("usage", {})
    s = {
        "ok": True, "elapsed": round(elapsed, 3),
        "prompt_tokens": usage.get("prompt_tokens"),
        "gen_tokens": usage.get("completion_tokens"),
        "decode_tps": round(usage.get("completion_tokens", 0) / elapsed, 2) if elapsed > 0 else None,
        "finish": ch.get("finish_reason"),
        "has_reasoning": bool(msg.get("reasoning_content")),
        "content_head": (msg.get("content") or "")[:300],
        "tool_calls": msg.get("tool_calls"),
    }
    return s

def main():
    mode, out = sys.argv[1], sys.argv[2]
    if mode == "chat":
        payload = {"model": "ornith", "messages": [
            {"role": "system", "content": "You are a precise technical assistant. Answer concisely."},
            {"role": "user", "content": "Explain in 3 sentences why unified memory matters for local LLM inference on Apple Silicon, then give one concrete number from your knowledge."}],
            "temperature": 0.6, "top_p": 0.95, "max_tokens": 512, "stream": False}
        data, el = post("/chat/completions", payload)
    elif mode == "reason":
        payload = {"model": "ornith", "messages": [
            {"role": "user", "content": "A server processes jobs in FIFO order. Jobs arrive at t=0,3,5,9,12 taking 4,2,7,1,3 seconds respectively. What is the average waiting time? Show your reasoning step by step, then give a single final number."}],
            "temperature": 0.6, "top_p": 0.95, "max_tokens": 2048, "stream": False}
        data, el = post("/chat/completions", payload)
    elif mode == "tool":
        tools = [{"type": "function", "function": {"name": "get_directory_listing",
                  "description": "List files in a directory path",
                  "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory path"}}, "required": ["path"]}}},
                 {"type": "function", "function": {"name": "read_text_file",
                  "description": "Read a UTF-8 text file",
                  "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
                 {"type": "function", "function": {"name": "run_shell",
                  "description": "Run a shell command and return stdout",
                  "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}}]
        payload = {"model": "ornith", "messages": [
            {"role": "system", "content": "You are an agent that must use tools to answer. Use the available functions."},
            {"role": "user", "content": "How many CPU cores does this machine have? Use a tool to find out."}],
            "tools": tools, "tool_choice": "auto",
            "temperature": 0.6, "top_p": 0.95, "max_tokens": 1024, "stream": False}
        data, el = post("/chat/completions", payload)
    elif mode == "needle":
        # needle test: target tokens roughly via filler; needle placed mid-prompt
        ntok = int(sys.argv[3])
        unit = ("The coastal observatory records tides, winds, minerals, and migratory birds in a durable notebook. ")
        # unit is ~14 words ~= 19 tokens; scale repeat count directly on target tokens
        unit_tokens = 19
        reps = max(1, ntok // unit_tokens)
        text = unit * reps
        needle = "LAGUNA_ORNITH_QUARTZ_7391"
        middle = len(text) // 2
        text = text[:middle] + f" Critical archival identifier: {needle}. " + text[middle:]
        question = "What is the exact archival identifier? Answer only the identifier."
        payload = {"model": "ornith", "messages": [
            {"role": "system", "content": "Answer accurately and concisely."},
            {"role": "user", "content": text + "\n\n" + question}],
            "temperature": 0.0, "max_tokens": 96, "stream": False}
        data, el = post("/chat/completions", payload)
        s = summarize(data, el)
        s["needle_correct"] = needle in json.dumps(data["choices"][0].get("message", {}))
        s["target_tokens_approx"] = ntok
        open(out, "w").write(json.dumps({"summary": s, "raw": data}, indent=2) + "\n")
        print(json.dumps(s, separators=(",", ":")))
        return
    else:
        raise SystemExit("unknown mode")
    s = summarize(data, el)
    open(out, "w").write(json.dumps({"summary": s, "raw": data}, indent=2) + "\n")
    print(json.dumps(s, separators=(",", ":")))

main()