#!/usr/bin/env python3
"""Create one sealed, fresh-label EXP-007 v2 scoreable pair assignment.

The program never prints model-to-label bindings.  Its public receipt contains
only new opaque labels, integrity hashes, and frozen-control references.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/Users/<user>/HermesProjects/Local-LLM-Lab')
EXP = ROOT / 'results/raw/EXP-007'
OUT = EXP / 'real-repo-ab-v2-scoreable'
PRIVATE = OUT / 'private/assignment.json'
PUBLIC = OUT / 'public/assignment-receipt.json'
FREEZE = EXP / 'context-safe-harness/v2/freeze-manifest.json'
PROMPT = EXP / 'real-repo-ab/prompts/T01/task.md'
FIXTURE = EXP / 'real-repo-ab/fixtures/T01-ios-layout'
CANDIDATE = re.compile(r'candidate-[A-Z][0-9]\b')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def existing_labels() -> set[str]:
    labels: set[str] = set()
    for path in EXP.rglob('*'):
        if not path.is_file() or path == PRIVATE:
            continue
        try:
            if path.stat().st_size > 5_000_000:
                continue
            labels.update(CANDIDATE.findall(path.read_text(encoding='utf-8', errors='ignore')))
        except OSError:
            continue
    return labels


def fresh_ids(used: set[str]) -> list[str]:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    ids: list[str] = []
    while len(ids) < 2:
        candidate = f'candidate-{secrets.choice(alphabet)}{secrets.randbelow(10)}'
        if candidate not in used and candidate not in ids:
            ids.append(candidate)
    return ids


def main() -> int:
    if PRIVATE.exists() or PUBLIC.exists():
        raise SystemExit('refusing to overwrite an existing scoreable-v2 sealed assignment or public receipt')
    freeze = json.loads(FREEZE.read_text(encoding='utf-8'))
    if freeze.get('freeze_status') != 'validated-no-model; candidate launch permitted':
        raise SystemExit('v2 freeze manifest does not permit candidate launch')
    ids = fresh_ids(existing_labels())
    entries = [
        {'engine': 'slipstream', 'artifact': str(EXP / 'stock-hybrid-control/qwen36-stock-hybrid-control.gturbo')},
        {'engine': 'slipstream', 'artifact': str(EXP / 'carnice-hybrid/Carnice-Qwen3.6-MoE-35B-A3B.gturbo')},
    ]
    secrets.SystemRandom().shuffle(entries)
    created = datetime.now(timezone.utc).isoformat()
    assignment = {
        'schema': 2,
        'sealed': True,
        'created_at_utc': created,
        'assignment': {ids[0]: entries[0], ids[1]: entries[1]},
        'controls': {
            'freeze_manifest_sha256': sha(FREEZE),
            'v2_policy': 'EXP-007-context-safe-v2',
            't01_prompt_sha256': sha(PROMPT),
            't01_fixture_commit': __import__('subprocess').check_output(['git', '-C', str(FIXTURE), 'rev-parse', 'HEAD'], text=True).strip(),
        },
    }
    PRIVATE.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE.write_text(json.dumps(assignment, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    receipt = {
        'receipt_version': 'EXP-007-v2-scoreable-pair-assignment-v1',
        'created_at_utc': created,
        'sealed_assignment_path': 'private/assignment.json',
        'sealed_assignment_sha256': sha(PRIVATE),
        'opaque_candidate_ids': sorted(ids),
        'v2_freeze_manifest_sha256': sha(FREEZE),
        't01_prompt_sha256': sha(PROMPT),
        't01_fixture_commit': assignment['controls']['t01_fixture_commit'],
        'mapping_disclosure': 'sealed; no model, artifact, or engine identity is present in this public receipt',
    }
    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'created_at_utc': created, 'opaque_candidate_ids': sorted(ids),
                      'sealed_assignment_sha256': receipt['sealed_assignment_sha256'],
                      'public_receipt': str(PUBLIC)}, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
