#!/usr/bin/env python3
"""One direct coding-tool payload probe using the captured local-dev prompt."""
import copy, json, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAPTURE = Path('/Users/<user>/.hermes/profiles/local-dev/sessions/request_dump_20260918_213640_a941d2_20260918_213702_331627.json')
KEEP = {'terminal', 'read_file', 'search_files', 'patch', 'write_file'}
body = json.loads(CAPTURE.read_text())['request']['body']
body = copy.deepcopy(body)
body['tools'] = [t for t in body['tools'] if t['function']['name'] in KEEP]
body.update(max_completion_tokens=96, temperature=0, stream=False)
req = urllib.request.Request('http://127.0.0.1:8901/v1/chat/completions', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
t0=time.monotonic()
record={'tool_names':[t['function']['name'] for t in body['tools']]}
try:
    with urllib.request.urlopen(req,timeout=360) as r: data=json.load(r)
    record.update(ok=True, elapsed_s=round(time.monotonic()-t0,2), finish_reason=data['choices'][0].get('finish_reason'), message=data['choices'][0]['message'], usage=data.get('usage'))
except Exception as e:
    record.update(ok=False, elapsed_s=round(time.monotonic()-t0,2), error_type=type(e).__name__, error=str(e))
(ROOT/'coding-five-tools-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
