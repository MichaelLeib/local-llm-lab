# EXP-007 Context-Safe Hermes Harness

## Frozen policy: `EXP-007-context-safe-v1`

This policy is profile-local to `exp007bench` and is applied through the
Hermes `transform_tool_result` hook **after** a real tool runs and **before**
its result becomes a model-visible tool message. It does not add, remove, or
modify tool schemas; it invokes no model and makes no external request.

| Control | Value | Behavior |
|---|---:|---|
| Server context | 16,384 tokens | Fixed; not enlarged by this policy. |
| Completion allowance | 4,096 tokens | Fixed; not lowered by this policy. |
| Per serialized tool result | 800 Qwen tokenizer tokens | Exact `tokenizer.json` measurement, not character estimate. |
| `read_file` default page | 250 lines | Hermes profile `tool_output.max_lines`; each line max 500 chars. |
| Terminal raw capture | 4,000 bytes | Hermes profile `tool_output.max_bytes`, then exact-token hook cap. |
| Search match list | 24 records | First deterministic records retained; omitted count and narrowing instruction returned. |

## Recoverability contract

No result is silently shortened. A bounded result carries an `EXP-007 bounded
observation` marker. File excerpts name the retained line ranges, total line
count when supplied by the file tool, and a concrete next `offset` request.
Terminal/generic output preserves head and tail and directs the agent to narrow
the command or request a file-specific follow-up. Search results state their
omitted count and direct the agent to narrow `pattern`/`path` or use a result
window.

The raw tool action still executes. This policy only constrains the observation
returned to the model, so task evidence remains accessible through deliberate
follow-up retrieval rather than broad dumping.

## Instrumentation

Set `EXP007_CONTEXT_SAFE_METRICS_PATH` for each run. The hook appends one JSONL
record per model-visible result, including original/serialized exact token
counts, character counts, truncation status, tool arguments, and omitted search
matches. The runner derives aggregate context-efficiency fields from these
records plus server-side prompt/completion telemetry.

## Scope

The policy applies uniformly to every tool result, with structured handling for
file reads, file search, and generic text output. It therefore covers terminal,
read/search/listing outputs, build/test logs, git results, and diffs without
changing a candidate's available tools, task, system prompt, fixture, runtime,
or sampling.
