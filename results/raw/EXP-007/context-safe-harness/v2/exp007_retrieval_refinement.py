#!/usr/bin/env python3
"""Derive post-hoc retrieval-refinement evidence from EXP-007 tool telemetry.

This is diagnostic only: it never changes model messages, tool behavior, or
scores. It inspects the recorded argument sequence after each bounded result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_offset(row: dict[str, Any]) -> int | None:
    args = row.get("args") if isinstance(row.get("args"), dict) else {}
    value = args.get("offset")
    return value if isinstance(value, int) and value > 0 else None


def derive(rows: list[dict[str, Any]]) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    counts = {"bounded_results": 0, "explicit_file_offset_followup": 0,
              "search_narrowing_followup": 0, "unrefined_repeat": 0,
              "no_classified_followup": 0}
    for i, row in enumerate(rows):
        if not row.get("truncated"):
            continue
        counts["bounded_results"] += 1
        args = row.get("args") if isinstance(row.get("args"), dict) else {}
        name = str(row.get("tool_name") or "")
        next_row = rows[i + 1] if i + 1 < len(rows) else None
        next_name = str(next_row.get("tool_name") or "") if next_row else ""
        next_args = next_row.get("args") if isinstance(next_row, dict) and isinstance(next_row.get("args"), dict) else {}
        kind = "no_classified_followup"
        if name == "read_file" and next_name == "read_file" and args.get("path") == next_args.get("path"):
            old, new = _read_offset(row), _read_offset(next_row)
            if new is not None and new != old:
                kind = "explicit_file_offset_followup"
        elif name == "search_files" and next_name == "search_files":
            old_pattern, new_pattern = str(args.get("pattern") or ""), str(next_args.get("pattern") or "")
            if args == next_args:
                kind = "unrefined_repeat"
            elif next_args.get("path") or len(new_pattern) > len(old_pattern):
                kind = "search_narrowing_followup"
        counts[kind] += 1
        observations.append({"index": i, "tool_name": name, "args": args,
                             "next_tool_name": next_name, "next_args": next_args,
                             "classification": kind})
    return {"diagnostic": "post-hoc only; no model or harness behavior changed",
            "counts": counts, "observations": observations}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("telemetry", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = derive(_rows(args.telemetry))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
