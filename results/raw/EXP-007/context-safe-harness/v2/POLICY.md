# EXP-007 Context-Safe Hermes Harness — v2

## Frozen policy label: `EXP-007-context-safe-v2`

This is a separate harness arm created after the locked v1 T01 pair showed the
same structural context exhaustion in both candidates. It does **not** modify,
replace, or reinterpret `EXP-007-context-safe-v1` or any v1 result.

## Invariants retained from v1

- Server context: **16,384 tokens**.
- Completion allowance: **4,096 tokens**.
- Same T01 prompt, fixture commit, tools, schemas, Hermes system prompt,
  sampling, runtime, loopback transport, timeout, rubric, fresh-session,
  fresh-worktree, and blinded-assignment procedure.
- Transformation occurs only after real tool execution and before the result
  enters model history. It adds no tool, calls no model, performs no network
  action, and has no candidate-specific branch.

## Sole substantive policy change

| Control | v1 | v2 |
|---|---:|---:|
| Final serialized model-visible tool-result cap | 800 | **350 exact Qwen tokenizer tokens** |

The exact shared Qwen tokenizer measures the fully serialized payload, not a
character estimate. All output-specific shaping is deterministic and uniform.

## Recoverability contract

No evidence is silently removed. Every shortened payload has an explicit
`EXP-007 bounded observation` marker. File results retain line evidence and a
concrete `offset=` continuation; terminal/generic output retains bounded head,
tail, and error/exit fields and asks for a narrower follow-up; search/list
results report the exact retained/total record count and direct the agent to
narrow pattern/path or use an offset window.

## Freeze boundary

The v2 profile plugin, v2 profile configuration, v2 runner, this policy, and
v2 tests/replay output must be hashed after validation. Candidate model launch
is forbidden until the validation receipt is complete. Candidate behavior may
not modify v2; any subsequent revision is `v3`.
