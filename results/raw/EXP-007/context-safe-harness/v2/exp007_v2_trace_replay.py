#!/usr/bin/env python3
"""Project locked v1 trace token budgets under context-safe-v2.

Raw pre-hook payload text was deliberately not persisted by v1; its per-tool
exact original token counts were.  This replay is therefore a conservative
budget replay, not a claim to reproduce unavailable raw strings: every v2
serialized payload is bounded by min(original_tokens, 350), because v2 measures
its final envelope against that cap.  A live v2 arm will record actual final
envelope tokens separately.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def replay(trace: Path, *, cap: int, context_limit: int, completion_allowance: int, initial_prompt_tokens: int) -> dict:
    rows = load_jsonl(trace)
    original_pre_hook = sum(int(row["original_tokens"]) for row in rows)
    v1_serialized = sum(int(row["serialized_tokens"]) for row in rows)
    projected = sum(min(int(row["original_tokens"]), cap) for row in rows)
    tool_budget = context_limit - completion_allowance - initial_prompt_tokens
    return {
        "trace": str(trace),
        "tool_results": len(rows),
        "original_pre_hook_tool_result_tokens": original_pre_hook,
        "v1_model_visible_tool_result_tokens": v1_serialized,
        "projected_v2_serialized_tool_tokens_upper_bound": projected,
        "v1_to_v2_projected_reduction_tokens": v1_serialized - projected,
        "pre_hook_to_v2_projected_reduction_tokens": original_pre_hook - projected,
        "v2_cap_tokens": cap,
        "context_limit": context_limit,
        "completion_allowance": completion_allowance,
        "initial_prompt_tokens": initial_prompt_tokens,
        "tool_result_budget_after_initial_and_reserve": tool_budget,
        "projected_tool_budget_headroom": tool_budget - projected,
        "method": "conservative token-budget replay: sum(min(v1 exact original token count, v2 cap)); raw pre-hook text was not persisted",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("--cap", type=int, default=350)
    parser.add_argument("--context-limit", type=int, default=16384)
    parser.add_argument("--completion-allowance", type=int, default=4096)
    parser.add_argument("--initial-prompt-tokens", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.trace, cap=args.cap, context_limit=args.context_limit,
                    completion_allowance=args.completion_allowance,
                    initial_prompt_tokens=args.initial_prompt_tokens)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
