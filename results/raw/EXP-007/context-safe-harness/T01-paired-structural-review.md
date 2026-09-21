# EXP-007 paired structural-harness review: T01

**Review status:** threshold met; `EXP-007-context-safe-v1` remains immutable.  
**Paired score rows:** `score-sheets/T01-candidate-K7.json`, `score-sheets/T01-candidate-R2.json`  
**Unblinding receipt:** `score-sheets/T01-unblinding.json`

## Locked v1 result

Both independently completed Hermes process orchestration and real tool execution,
but exhausted the fixed 16,384-token server context before producing an edit:

| Blind arm | Tool calls | Serialized tool-result tokens | Maximum prompt | Context failure |
|---|---:|---:|---:|---|
| `candidate-K7` | 17 | 11,907 | 15,270 | `prompt exceeds the configured context` |
| `candidate-R2` | 20 | 10,281 | 16,190 | `effective prompt exceeds the configured context` |

The task-level scores are locked before unblinding. Each arm remains a candidate
failure in v1; this review does **not** rewrite either outcome.

## Structural finding

At a fixed 4,096-token completion allowance, the `800`-token result cap admits
roughly 10–12k tokens of tool observations after 17–20 ordinary inspection calls.
Both candidates independently reached that regime. This satisfies the
predeclared condition for a *new, separately versioned* harness policy.

## v2 proposal (not yet applied)

Create `EXP-007-context-safe-v2` in a new profile/runner only; do not edit the
v1 plugin, profile, policy, runner, score sheets, or prior run directories.

| Control | v1 | proposed v2 |
|---|---:|---:|
| Server context | 16,384 | 16,384 (unchanged) |
| Completion allowance | 4,096 | 4,096 (unchanged) |
| Per serialized tool result | 800 | **350 exact Qwen tokens** |
| Tools, task, fixture, sampling, transport | fixed | unchanged |

A deterministic replay of the already-executed raw observation sizes gives this
conservative (token-only) ceiling, prior to any v2 model launch:

| Blind arm | v1 serialized | v2-350 simulated ceiling | reduction |
|---|---:|---:|---:|
| `candidate-K7` | 11,907 | 5,851 | 6,056 |
| `candidate-R2` | 10,281 | 5,772 | 4,509 |

The replay uses `sum(min(original_tokens, 350))`; actual v2 serialized envelopes
must be token-measured and validated separately before any rescored arm. The
350 cap is chosen over 400 because the 400-token replay leaves only a marginal
buffer once message/tool-call framing and the fixed completion reservation are
included.

## Required v2 admission gates

1. Clone the benchmark profile and runner; do not mutate v1.
2. Re-run all deterministic hook/schema/telemetry tests with the v2 cap.
3. Replay both v1 JSONL observation traces through v2 and record exact envelope
   tokens, including truncation/recovery markers.
4. Verify v2 model-visible tool schemas match v1 exactly.
5. Run no-model profile-load/integration checks.
6. Only then perform a fresh paired Stock/Carnice T01 retry, score blind, and
   compare v2 against the locked v1 task evidence as a separately labelled
   harness arm.
