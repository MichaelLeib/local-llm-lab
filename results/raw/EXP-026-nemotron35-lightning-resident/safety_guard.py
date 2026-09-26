#!/usr/bin/env python3
"""Independent macOS safety guard for EXP-026 only.
Kills only the PID passed on the command line when hard limits are crossed.
"""
import argparse, json, re, signal, subprocess, time
from pathlib import Path

PAGESZ = 16384

def run(*args):
    return subprocess.run(args, text=True, capture_output=True, check=False).stdout

def swap_bytes():
    text = run("sysctl", "vm.swapusage")
    m = re.search(r"used = ([0-9.]+)([MG])", text)
    if not m:
        return None
    return int(float(m.group(1)) * (1024**2 if m.group(2) == "M" else 1024**3))

def memory_free_pct():
    text = run("/usr/bin/memory_pressure", "-Q")
    m = re.search(r"free percentage: (\d+)%", text)
    return int(m.group(1)) if m else None

def vmstat():
    text = run("/usr/bin/vm_stat")
    result = {}
    for key in ("Pages occupied by compressor", "Pageouts", "Swapouts", "Pageins", "Swapins"):
        m = re.search(re.escape(key) + r":\s+(\d+)", text)
        result[key] = int(m.group(1)) if m else None
    result["raw"] = text
    return result

def process_stats(pid):
    text = run("ps", "-o", "pid=,rss=,%mem=,%cpu=,etime=,command=", "-p", str(pid)).strip()
    return {"ps": text, "alive": bool(text)}

def snapshot(pid):
    return {
        "ts_epoch": time.time(),
        "free_pct": memory_free_pct(),
        "swap_bytes": swap_bytes(),
        "vm": vmstat(),
        "process": process_stats(pid),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--min-free-pct", type=int, default=18)
    ap.add_argument("--max-swap-growth-mib", type=int, default=384)
    ap.add_argument("--max-pageout-growth", type=int, default=2000)
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    baseline = snapshot(args.pid)
    baseline["event"] = "baseline"
    with out.open("a") as f:
        f.write(json.dumps(baseline) + "\n")
        f.flush()
        while True:
            s = snapshot(args.pid)
            if not s["process"]["alive"]:
                s["event"] = "target_exited"
                f.write(json.dumps(s) + "\n")
                break
            reasons = []
            if s["free_pct"] is not None and s["free_pct"] < args.min_free_pct:
                reasons.append(f"free_pct<{args.min_free_pct}")
            if baseline["swap_bytes"] is not None and s["swap_bytes"] is not None:
                if s["swap_bytes"] - baseline["swap_bytes"] > args.max_swap_growth_mib * 1024**2:
                    reasons.append(f"swap_growth>{args.max_swap_growth_mib}MiB")
            bp, cp = baseline["vm"]["Pageouts"], s["vm"]["Pageouts"]
            if bp is not None and cp is not None and cp - bp > args.max_pageout_growth:
                reasons.append(f"pageouts_growth>{args.max_pageout_growth}")
            s["event"] = "guard_stop" if reasons else "sample"
            s["reasons"] = reasons
            f.write(json.dumps(s) + "\n")
            f.flush()
            if reasons:
                subprocess.run(["kill", "-TERM", str(args.pid)], check=False)
                break
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
