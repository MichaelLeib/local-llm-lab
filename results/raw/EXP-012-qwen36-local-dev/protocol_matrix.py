#!/usr/bin/env python3
"""Compare captured Hermes request shapes against a local Slipstream server.

This is a diagnostic, not a qualification. It limits completion to 96 tokens
and writes a durable JSON record with request-shape identifiers and responses.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GOOD = Path('/Users/<user>/.hermes/profiles/exp005/sessions/request_dump_20260917_152247_afb0b8_20260917_152309_064006.json')
BAD = Path('/Users/<user>/.hermes/profiles/local-dev/sessions/request_dump_20260918_213640_a941d2_20260918_213702_331627.json')
URL = 'http://127.0.0.1:8901/v1/chat/completions'


def sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def request(name: str, body: dict) -> dict:
    payload = copy.deepcopy(body)
    payload['max_completion_tokens'] = 96
    payload['temperature'] = 0
    payload['stream'] = False
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    row = {
        'name': name,
        'system_chars': len(payload['messages'][0]['content']),
        'tool_names': [t['function']['name'] for t in payload.get('tools', [])],
        'payload_sha256': sha(payload),
    }
    try:
        with urllib.request.urlopen(req, timeout=360) as response:
            data = json.load(response)
        row.update({
            'ok': True,
            'elapsed_s': round(time.monotonic() - started, 2),
            'finish_reason': data['choices'][0].get('finish_reason'),
            'content': data['choices'][0]['message'].get('content'),
            'tool_calls': data['choices'][0]['message'].get('tool_calls', []),
            'usage': data.get('usage'),
        })
    except urllib.error.HTTPError as error:
        row.update({'ok': False, 'elapsed_s': round(time.monotonic() - started, 2), 'http_status': error.code, 'error': error.read().decode(errors='replace')})
    except Exception as error:
        row.update({'ok': False, 'elapsed_s': round(time.monotonic() - started, 2), 'error_type': type(error).__name__, 'error': str(error)})
    return row


def main() -> int:
    good = json.loads(GOOD.read_text())['request']['body']
    bad = json.loads(BAD.read_text())['request']['body']
    terminal = next(t for t in bad['tools'] if t['function']['name'] == 'terminal')
    cases = [
        ('exp005_captured_4_tools', good),
        ('localdev_system_terminal_only', {**bad, 'tools': [terminal]}),
        ('localdev_captured_13_tools', bad),
    ]
    result = {'purpose': 'protocol minimization', 'captured_at_unix': time.time(), 'cases': []}
    for name, body in cases:
        row = request(name, body)
        result['cases'].append(row)
        print(json.dumps({k: row.get(k) for k in ('name', 'ok', 'elapsed_s', 'http_status', 'error_type', 'error', 'finish_reason', 'tool_calls', 'usage')}, ensure_ascii=False), flush=True)
        # Avoid continuing after a server crash; preserve the result file first.
        (ROOT / 'protocol-matrix-result.json').write_text(json.dumps(result, indent=2) + '\n')
        if row.get('error_type') in {'RemoteDisconnected', 'IncompleteRead', 'RemoteProtocolError'}:
            break
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
