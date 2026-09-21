#!/usr/bin/env python3
"""Minimal loopback compatibility proxy for EXP-007 Hermes↔Slipstream runs.

It deliberately removes only request fields that the pinned Slipstream OpenAI
surface rejects. Every candidate/harness arm uses the exact same proxy.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin

STRIP_FIELDS = {"reasoning_effort", "session_id"}


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    upstream = ""

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _forward(self) -> None:
        body = b""
        if self.command in {"POST", "PUT", "PATCH"}:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.headers.get("Content-Type", "").split(";", 1)[0] == "application/json":
                try:
                    payload = json.loads(body)
                    if isinstance(payload, dict):
                        for key in STRIP_FIELDS:
                            payload.pop(key, None)
                        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                except json.JSONDecodeError:
                    pass
        # Keep the /v1 prefix exactly once: client paths already include it.
        target = self.upstream.rstrip("/") + self.path
        headers = {key: value for key, value in self.headers.items() if key.lower() not in {"host", "content-length", "connection"}}
        headers["Content-Length"] = str(len(body))
        request = urllib.request.Request(target, data=body if self.command != "GET" else None, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(request, timeout=1900) as response:
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in {"transfer-encoding", "connection", "content-length"}:
                        self.send_header(key, value)
                # Relay incrementally, including SSE responses. Buffering a long
                # local decode makes the client appear disconnected before it sees
                # the first chunk.
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                while chunk := response.read(16_384):
                    self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                    self.wfile.write(chunk)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        except urllib.error.HTTPError as exc:
            data = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get_content_type())
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    do_GET = _forward
    do_POST = _forward


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--upstream", required=True)
    args = parser.parse_args()
    Proxy.upstream = args.upstream
    server = ThreadingHTTPServer(("127.0.0.1", args.listen_port), Proxy)
    server.serve_forever()


if __name__ == "__main__":
    main()
