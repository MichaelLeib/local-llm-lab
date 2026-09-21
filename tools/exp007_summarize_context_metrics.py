#!/usr/bin/env python3
"""Aggregate deterministic EXP-007 context-efficiency telemetry for one run."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

REQUEST = re.compile(r"\brequest\s+prompt=(\d+)\b.*?\bcompletion=(\d+)\b")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def _server_requests(path: Path) -> list[tuple[int, int]]:
    if not path.exists():
        return []
    return [(int(m.group(1)), int(m.group(2))) for m in REQUEST.finditer(path.read_text(encoding="utf-8", errors="replace"))]


def _key(record: dict[str, Any], name: str) -> tuple:
    args = record.get("args") if isinstance(record.get("args"), dict) else {}
    if name == "read_file":
        return (args.get("path"), args.get("offset"), args.get("limit"))
    if name == "search_files":
        return (args.get("path"), args.get("pattern"), args.get("file_glob"), args.get("output_mode"))
    return ()


def summarize(run: Path, *, context_limit: int, completion_allowance: int) -> dict[str, Any]:
    records = _jsonl(run / "context-safe-tool-results.jsonl")
    requests = _server_requests(run / "server.log")
    tool_counts = Counter(str(r.get("tool_name") or "unknown") for r in records)
    repeats = Counter((str(r.get("tool_name") or "unknown"), _key(r, str(r.get("tool_name") or ""))) for r in records)
    repeated_file_ranges = sum(1 for (name, _), n in repeats.items() if name == "read_file" and n > 1)
    repeated_unrefined_searches = sum(1 for (name, _), n in repeats.items() if name == "search_files" and n > 1)
    prompts = [prompt for prompt, _ in requests]
    completions = [completion for _, completion in requests]
    maximum_prompt = max(prompts, default=0)
    result = {
        "policy": "EXP-007-context-safe-v1",
        "context_limit": context_limit,
        "completion_allowance": completion_allowance,
        "initial_prompt_tokens": prompts[0] if prompts else 0,
        "maximum_accumulated_prompt_tokens": maximum_prompt,
        "tool_calls_made": len(records),
        "tool_calls_by_name": dict(sorted(tool_counts.items())),
        "tool_result_tokens": [int(r.get("serialized_tokens") or 0) for r in records],
        "cumulative_tool_result_tokens": sum(int(r.get("serialized_tokens") or 0) for r in records),
        "truncated_tool_outputs": sum(bool(r.get("truncated")) for r in records),
        "repeated_file_ranges": repeated_file_ranges,
        "repeated_unrefined_searches": repeated_unrefined_searches,
        "completion_tokens": sum(completions),
        "server_request_count": len(requests),
        "context_limit_approached": bool(maximum_prompt and maximum_prompt + completion_allowance >= int(context_limit * 0.9)),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--context-limit", type=int, default=16384)
    parser.add_argument("--completion-allowance", type=int, default=4096)
    args = parser.parse_args()
    output = summarize(args.run, context_limit=args.context_limit, completion_allowance=args.completion_allowance)
    target = args.run / "context-efficiency.json"
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
