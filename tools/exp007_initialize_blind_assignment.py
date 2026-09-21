#!/usr/bin/env python3
"""Create the sealed EXP-007 candidate assignment exactly once."""
from __future__ import annotations

import hashlib
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "results/raw/EXP-007/real-repo-ab/private"
PATH = PRIVATE / "assignment.json"
CANDIDATES = [
    {
        "engine": "slipstream",
        "key": "carnice-hybrid",
        "artifact": str(ROOT / "results/raw/EXP-007/carnice-hybrid/Carnice-Qwen3.6-MoE-35B-A3B.gturbo"),
    },
    {
        "engine": "slipstream",
        "key": "stock-hybrid-control",
        "artifact": str(ROOT / "results/raw/EXP-007/stock-hybrid-control/qwen36-stock-hybrid-control.gturbo"),
    },
    {
        "engine": "managed-fast",
        "key": "ornith-fast",
        "artifact": None,
    },
]
BLIND_IDS = ["candidate-K7", "candidate-M9", "candidate-R2"]

if PATH.exists():
    raise SystemExit(f"refusing to replace sealed assignment: {PATH}")

rng = secrets.SystemRandom()
rng.shuffle(CANDIDATES)
PRIVATE.mkdir(parents=True, exist_ok=True)
payload = {
    "schema": 1,
    "assignment": dict(zip(BLIND_IDS, CANDIDATES)),
}
PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("created sealed assignment")
print("blind_ids=" + ",".join(BLIND_IDS))
print("sha256=" + hashlib.sha256(PATH.read_bytes()).hexdigest())
