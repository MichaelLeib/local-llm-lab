#!/usr/bin/env python3
"""Transparent local HTTP capture proxy for one EXP-003 Hermes request."""
from __future__ import annotations

import json
import os
import threading
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LISTEN = ("127.0.0.1", 8905)
UPSTREAM = ("127.0.0.1", 8901)
CAPTURE = Path("results/raw/EXP-003/bridge-fix/hermes-request-capture.json")


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)

    def do_GET(self):
        self._forward(body=None)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            # Ornith's Qwen3.5 template otherwise enters unrestricted thinking
            # for Hermes auxiliary calls (title generation included). Inject the
            # model-specific switch at the transport boundary for every request.
            template_kwargs = payload.get("chat_template_kwargs")
            if not isinstance(template_kwargs, dict):
                template_kwargs = {}
            template_kwargs["enable_thinking"] = False
            payload["chat_template_kwargs"] = template_kwargs
            allow = {x.strip() for x in os.environ.get("HERMES_BRIDGE_TOOLS", "").split(",") if x.strip()}
            if allow and isinstance(payload.get("tools"), list):
                payload["tools"] = [
                    tool for tool in payload["tools"]
                    if tool.get("function", {}).get("name") in allow
                ]
            if os.environ.get("HERMES_BRIDGE_MAX_TOKENS"):
                payload["max_tokens"] = int(os.environ["HERMES_BRIDGE_MAX_TOKENS"])
            body = json.dumps(payload, ensure_ascii=False).encode()
            CAPTURE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        except Exception as exc:
            CAPTURE.write_text(json.dumps({"parse_error": str(exc), "raw_bytes": len(body)}) + "\n")
        self._forward(body=body)

    def _forward(self, body: bytes | None):
        conn = HTTPConnection(*UPSTREAM, timeout=900)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length", "connection"}}
        if body is not None:
            headers["Content-Length"] = str(len(body))
        conn.request(self.command, self.path, body=body, headers=headers)
        response = conn.getresponse()
        self.send_response(response.status, response.reason)
        for key, value in response.getheaders():
            if key.lower() not in {"connection", "transfer-encoding", "content-length"}:
                self.send_header(key, value)
        # SSE responses from llama.cpp are commonly chunked or close-delimited;
        # do not claim a zero content length. HTTP/1.1 close-delimiting preserves
        # each upstream chunk while allowing the client to detect end-of-stream.
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        while True:
            chunk = response.read(8192)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()
        conn.close()


if __name__ == "__main__":
    CAPTURE.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(LISTEN, Proxy)
    print(f"capture proxy listening on http://{LISTEN[0]}:{LISTEN[1]}", flush=True)
    server.serve_forever()
