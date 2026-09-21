#!/usr/bin/env python3
"""Parse llm-exp sysmon jsonl -> compact delta summary."""
import json, sys, re

def num(s, key):
    m = re.search(key + r":\s+([0-9.]+)", s)
    return float(m.group(1)) if m else None

def swap_used(s):
    m = re.search(r"used = ([0-9.]+)M", s)
    return float(m.group(1)) if m else 0.0

def free_pct(s):
    m = re.search(r"free percentage: ([0-9.]+)%", s)
    return float(m.group(1)) if m else None

path = sys.argv[1]
rows = [json.loads(l) for l in open(path) if l.strip()]
if not rows: print("EMPTY"); sys.exit(0)

def extract(r):
    vm = r["vm_stat"]
    return {
        "ts": r["ts"],
        "free_pct": free_pct(r["pressure"]),
        "swap_used_mb": swap_used(r["swap"]),
        "pages_free": num(vm, "Pages free"),
        "pageins": num(vm, "Pageins:"),
        "pageouts": num(vm, "Pageouts:"),
        "swapins": num(vm, "Swapins:"),
        "swapouts": num(vm, "Swapouts:"),
        "compressor_occupied": num(vm, "Pages occupied by compressor"),
        "wired": num(vm, "Pages wired down"),
    }

e = [extract(r) for r in rows]
d = lambda k: int((e[-1][k] or 0) - (e[0][k] or 0))
summary = {
    "samples": len(e),
    "start_free_pct": e[0]["free_pct"],
    "end_free_pct": e[-1]["free_pct"],
    "min_free_pct": min(x["free_pct"] for x in e if x["free_pct"] is not None),
    "min_pages_free": min(x["pages_free"] for x in e if x["pages_free"] is not None),
    "min_pages_free_mb": round(min(x["pages_free"] for x in e if x["pages_free"] is not None) * 0.016384, 1),
    "swap_start_mb": e[0]["swap_used_mb"],
    "swap_end_mb": e[-1]["swap_used_mb"],
    "swap_delta_mb": round(e[-1]["swap_used_mb"] - e[0]["swap_used_mb"], 1),
    "swapins_delta": d("swapins"),
    "swapouts_delta": d("swapouts"),
    "pageouts_delta": d("pageouts"),
    "compressor_end_mb": round((e[-1]["compressor_occupied"] or 0) * 0.016384, 1),
    "wired_end_mb": round((e[-1]["wired"] or 0) * 0.016384, 1),
}
print(json.dumps(summary, separators=(",", ":")))