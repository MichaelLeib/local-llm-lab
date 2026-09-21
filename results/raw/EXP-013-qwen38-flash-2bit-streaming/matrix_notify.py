#!/usr/bin/env python3
"""Send one important Local LLM Lab milestone to the private Matrix room.

Reads the existing default-profile Matrix token only from ~/.hermes/.env; it
never prints it. The event is read back from room history before success.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: matrix_notify.py 'important milestone text'")
body = sys.argv[1]
root = Path(__file__).resolve().parent
room_id = json.loads((root / "matrix-room.json").read_text())["room_id"]
env = {}
for line in Path.home().joinpath(".hermes", ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
base = env["MATRIX_HOMESERVER"].rstrip("/")
token = env["MATRIX_ACCESS_TOKEN"]

def request(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": "Bearer " + token}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read() or b"{}")

encoded_room = urllib.parse.quote(room_id, safe="")
txn = "llm-lab-" + uuid.uuid4().hex
sent = request("PUT", f"/_matrix/client/v3/rooms/{encoded_room}/send/m.room.message/{txn}", {"msgtype": "m.notice", "body": body})
history = request("GET", f"/_matrix/client/v3/rooms/{encoded_room}/messages?dir=b&limit=20")
if not any(event.get("event_id") == sent["event_id"] and event.get("content", {}).get("body") == body for event in history.get("chunk", [])):
    raise RuntimeError("Matrix event not found in post-send history readback")
print(json.dumps({"event_id": sent["event_id"], "verified": True, "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
