#!/usr/bin/env python3
"""Fail closed if an EXP-007 frozen harness file changed after its receipt."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: verify_v2_freeze.py <freeze-manifest.json>')
    manifest_path = Path(sys.argv[1])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    failures=[]
    for item in manifest['files']:
        path=Path(item['path'])
        actual=sha256(path) if path.exists() else None
        if actual != item['sha256']:
            failures.append({'path':str(path),'expected':item['sha256'],'actual':actual})
    if failures:
        print(json.dumps({'freeze_valid':False,'failures':failures},indent=2), file=sys.stderr)
        return 1
    print('EXP-007-context-safe-v2 freeze receipt verified')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
