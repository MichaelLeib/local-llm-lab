#!/usr/bin/env python3
"""Run one reproducible OpenAI-compatible streaming completion for EXP-002."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8901/v1/chat/completions")
    parser.add_argument("--model", default="hermes-fast")
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args()

    prompt = args.prompt_file.read_text()
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": "You are a careful senior software engineer. Follow the user's requested format."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    encoded = json.dumps(payload).encode()
    request = Request(args.url, data=encoded, headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    wall_started = dt.datetime.now(dt.timezone.utc).isoformat()
    chunks: list[dict] = []
    text_parts: list[str] = []
    usage = None
    first_event = None
    status = None
    error = None
    try:
        with urlopen(request, timeout=args.timeout) as response:
            status = response.status
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    continue
                event_time = time.monotonic()
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    chunks.append({"received_seconds": event_time - started, "raw": data})
                    continue
                if first_event is None:
                    first_event = event_time
                chunks.append({"received_seconds": event_time - started, "event": event})
                if event.get("usage"):
                    usage = event["usage"]
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {})
                    content = delta.get("content")
                    if content:
                        text_parts.append(content)
    except Exception as exc:  # preserve failure as an artifact rather than hiding it
        error = f"{type(exc).__name__}: {exc}"
    finished = time.monotonic()
    result = {
        "schema": "local-llm-lab.exp002-inference.v1",
        "experiment": "EXP-002",
        "captured_at": wall_started,
        "request": payload,
        "prompt_file": str(args.prompt_file),
        "http_status": status,
        "error": error,
        "timing": {
            "elapsed_seconds": finished - started,
            "time_to_first_event_seconds": (first_event - started) if first_event is not None else None,
        },
        "usage_from_server": usage,
        "text": "".join(text_parts),
        "stream_event_count": len(chunks),
        "stream_events": chunks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "http_status": status,
        "error": error,
        "elapsed_seconds": round(result["timing"]["elapsed_seconds"], 3),
        "time_to_first_event_seconds": round(result["timing"]["time_to_first_event_seconds"], 3) if result["timing"]["time_to_first_event_seconds"] is not None else None,
        "server_usage": usage,
        "output_chars": len(result["text"]),
        "stream_event_count": len(chunks),
        "artifact": str(args.output),
    }))
    return 0 if status == 200 and error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
