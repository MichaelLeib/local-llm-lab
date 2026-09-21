#!/usr/bin/env python3
"""Run fresh deterministic 8/16-slot comparisons for EXP-003."""
import datetime as dt
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/raw/EXP-003/source/llama.cpp-moe-expert-residency"
MODEL = Path.home() / ".cache/huggingface/hub/models--ornith-ai--Ornith-1.5-35B-A3B-GGUF/snapshots/12393612fd4f730ff5aadc23e9b8f9648aa49ceb/Ornith-1.5-35B-Q4_K_M.gguf"
OUT = ROOT / "results/raw/EXP-003/deterministic-compare"
PROMPT = (ROOT / "results/raw/EXP-003/first-load-prompt.txt").read_text()
PORT = 18903


def health_ready():
    try:
        with urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def sample(pid, path, stop):
    with path.open("w") as f:
        while not stop.is_set():
            record = {"captured_at": dt.datetime.now(dt.timezone.utc).isoformat()}
            for name, cmd in {
                "footprint": ["footprint", "-p", str(pid), "-f", "bytes", "--noCategories"],
                "ps": ["ps", "-p", str(pid), "-o", "rss=,pcpu="],
                "ioreg": ["ioreg", "-l", "-w0", "-r", "-c", "IOAccelerator"],
                "memory_pressure": ["memory_pressure", "-Q"],
                "swap": ["sysctl", "vm.swapusage"],
            }.items():
                try:
                    record[name + "_raw"] = subprocess.run(cmd, text=True, capture_output=True, timeout=10).stdout
                except Exception as exc:
                    record[name + "_error"] = repr(exc)
            f.write(json.dumps(record) + "\n")
            f.flush()
            stop.wait(2.0)


def request_result():
    payload = {
        "model": "Ornith-1.5-35B-A3B-Q4_K_M",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 128,
        "temperature": 0.0,
        "top_p": 1.0,
        "seed": 12345,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    first_event = first_content = None
    pieces, raw = [], []
    status = None
    error = None
    try:
        with urlopen(req, timeout=900) as response:
            status = response.status
            for raw_line in response:
                line = raw_line.decode("utf-8", "replace").rstrip("\n")
                raw.append(line)
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    continue
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                now = time.time()
                first_event = first_event or now
                delta = (((obj.get("choices") or [{}])[0]).get("delta") or {})
                text = delta.get("content")
                if text:
                    first_content = first_content or now
                    pieces.append(text)
    except Exception as exc:
        error = repr(exc)
    ended = time.time()
    return {
        "request": payload,
        "http_status": status,
        "started_unix": started,
        "first_event_unix": first_event,
        "first_content_unix": first_content,
        "ended_unix": ended,
        "time_to_first_event_s": first_event - started if first_event else None,
        "time_to_first_content_s": first_content - started if first_content else None,
        "elapsed_s": ended - started,
        "content": "".join(pieces),
        "content_chars": sum(len(x) for x in pieces),
        "error": error,
        "raw_sse_lines": raw,
    }


def stop_server(server):
    if server.poll() is None:
        server.send_signal(signal.SIGTERM)
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


def run_slot(slots):
    OUT.mkdir(parents=True, exist_ok=True)
    log_path = OUT / f"{slots}slot-server.log"
    result_path = OUT / f"{slots}slot-request.json"
    metrics_path = OUT / f"{slots}slot-metrics.jsonl"
    args = [
        str(SOURCE / "build/bin/llama-server"), "-m", str(MODEL),
        "--host", "127.0.0.1", "--port", str(PORT), "--no-webui",
        "-ngl", "99", "-c", "2048", "-b", "2048", "-ub", "1",
        "--moe-n-slots", str(slots), "--moe-n-layers", "40",
        "--no-mmap", "--no-warmup", "--parallel", "1", "--metrics",
    ]
    with log_path.open("w") as log:
        server = subprocess.Popen(args, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.time() + 360
    while time.time() < deadline and server.poll() is None and not health_ready():
        time.sleep(2)
    if server.poll() is not None:
        raise RuntimeError(f"{slots}-slot server exited {server.returncode}; see {log_path}")
    if not health_ready():
        stop_server(server)
        raise RuntimeError(f"{slots}-slot server did not become ready; see {log_path}")
    stop = threading.Event()
    monitor = threading.Thread(target=sample, args=(server.pid, metrics_path, stop), daemon=True)
    monitor.start()
    try:
        result = request_result()
        result["slot_count"] = slots
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        stop.set()
        monitor.join(timeout=15)
        stop_server(server)
    return result


def main():
    results = {}
    for slots in (8, 16):
        results[str(slots)] = run_slot(slots)
        time.sleep(8)
    a, b = results["8"], results["16"]
    comparison = {
        "seed": 12345,
        "same_prompt": True,
        "same_request_settings": True,
        "eight_slot_content_sha256": __import__("hashlib").sha256(a["content"].encode()).hexdigest(),
        "sixteen_slot_content_sha256": __import__("hashlib").sha256(b["content"].encode()).hexdigest(),
        "exact_content_match": a["content"] == b["content"],
        "eight_slot_content_chars": a["content_chars"],
        "sixteen_slot_content_chars": b["content_chars"],
        "eight_slot_http_status": a["http_status"],
        "sixteen_slot_http_status": b["http_status"],
        "eight_slot_error": a["error"],
        "sixteen_slot_error": b["error"],
        "eight_slot_decode_tok_s_estimate": 128 / max(a["elapsed_s"] - a["time_to_first_content_s"], 1e-9) if a["time_to_first_content_s"] else None,
        "sixteen_slot_decode_tok_s_estimate": 128 / max(b["elapsed_s"] - b["time_to_first_content_s"], 1e-9) if b["time_to_first_content_s"] else None,
    }
    (OUT / "comparison.json").write_text(json.dumps(comparison, indent=2))
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
