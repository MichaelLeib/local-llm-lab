#!/usr/bin/env python3
import json, sys, time
from pathlib import Path
from urllib.request import Request, urlopen

url = sys.argv[1]
out_path = Path(sys.argv[2])
prompt = Path(sys.argv[3]).read_text()
payload = {
    "model": "Ornith-1.5-35B-A3B-Q4_K_M",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 128,
    "temperature": 0.0,
    "top_p": 1.0,
    "stream": True,
    "chat_template_kwargs": {"enable_thinking": False},
}
body = json.dumps(payload).encode()
req = Request(url + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"}, method="POST")
started = time.time()
first_event = None
first_content = None
content = []
raw = []
error = None
status = None
try:
    with urlopen(req, timeout=900) as r:
        status = r.status
        for raw_line in r:
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
            if first_event is None:
                first_event = time.time()
            delta = (((obj.get("choices") or [{}])[0]).get("delta") or {})
            piece = delta.get("content")
            if piece:
                if first_content is None:
                    first_content = time.time()
                content.append(piece)
except Exception as exc:
    error = repr(exc)
ended = time.time()
result = {
    "url": url,
    "request": payload,
    "http_status": status,
    "started_unix": started,
    "first_event_unix": first_event,
    "first_content_unix": first_content,
    "ended_unix": ended,
    "time_to_first_event_s": (first_event-started) if first_event else None,
    "time_to_first_content_s": (first_content-started) if first_content else None,
    "elapsed_s": ended-started,
    "content": "".join(content),
    "content_chars": sum(len(x) for x in content),
    "error": error,
    "raw_sse_lines": raw,
}
out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(json.dumps({k: result[k] for k in ["http_status", "time_to_first_event_s", "time_to_first_content_s", "elapsed_s", "content_chars", "error"]}, indent=2))
