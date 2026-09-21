# EXP-007 real-repository A/B benchmark

## Purpose

Measure three local models on the same real HermesMobile tasks in two execution harnesses:

- **Primary:** a deliberately slim Hermes coding profile, with native tool calls.
- **Diagnostic:** Pi 0.73.1, using only `read`, `write`, `edit`, and `bash`.

This is a model × harness interaction experiment. Hermes is the promotion gate; Pi diagnoses whether a result is primarily model capability or harness fit.

## Candidate identities (sealed until scoring)

| Blind candidate | Model artifact |
|---|---|
| `candidate-K7` | mapping sealed in `private/assignment.json` |
| `candidate-M9` | mapping sealed in `private/assignment.json` |
| `candidate-R2` | mapping sealed in `private/assignment.json` |

The scorer must not receive the mapping. The runner must write only blind IDs into task folders, logs, and score sheets.

## Frozen source and backup

- Production repo HEAD at setup: `a2aafdafeaa91d41d73acc60e5d0a27dcecb7e2c`
- Production repository is never a benchmark worktree.
- Recoverable source backup: `backups/20260918-065703/`
- Baseline test status at setup: **89 passing / 1 failing**. The known pre-existing failure is the live `workshop` proxy contract timing out; it is excluded from deterministic benchmark acceptance suites.

## Global controls

- One model resident at a time; record `memory_pressure`, `vm.swapusage`, disk availability, and process state before/after every run.
- One fresh agent session and one fresh Git worktree per `task × candidate × harness` run.
- Same fixture commit, prompt file hash, environment, Node executable, tool budget, context limit, temperature, seed, and 4096-output-token cap for all candidate runs in a task/harness arm.
- No network-dependent acceptance test. No production service starts/stops. The production HermesMobile checkout is read-only for this experiment.
- A run is **not solved** unless its task acceptance command exits zero.

### Frozen paired-arm rules — T01

- `EXP-007-context-safe-v1` is frozen. Do not change its profile-local result policy, token caps, server context, output allowance, or telemetry interpretation because one candidate behaves badly.
- Run the Stock/Carnice paired arm from the same fresh T01 fixture commit, same frozen harness, same local profile, same tool/output policy, and same completion allowance.
- Treat a context exhaustion caused by excessive model-driven retrieval as a **candidate execution failure**, not a harness failure. Revise the harness only if both paired candidates independently encounter essentially the same structural limitation; preserve both raw traces before any revision.
- Keep candidate identities sealed. Write task-level score sheets using only blind IDs; unblind only after the paired task scores are locked.

## Scoring

### Coding outcome (70)

- 30: explicit + hidden acceptance conditions pass
- 15: deterministic relevant regression suite passes
- 15: correct/minimal diff, no observed regression
- 10: maintainable scope and tests

### Agent execution (30)

- 6: evidence inspected before edit
- 6: relevant/efficient tool use
- 5: avoids speculative edits
- 5: recovers from a failed hypothesis
- 5: verifies final state
- 3: concise and accurate final response

The automated functional score is decided before a blinded human trace review. Tool calls, failed commands, generated tokens, wall time, decode speed, final diff, test commands, swap delta, and memory-pressure observations are preserved as secondary metrics.

### T01 four-dimension scorecard (record separately; no composite before pair lock)

1. **Coding outcome (0–70):** held-out acceptance, deterministic regressions, build, diff correctness/minimality, and maintainability/tests. A nonzero acceptance exit is an unsolved task.
2. **Agent execution (0–30):** evidence gathered before edit, relevance/efficiency of calls, restraint, recovery, final verification, and accurate concise completion.
3. **Context and retrieval discipline (observational):** initial prompt tokens, maximum accumulated prompt tokens, completion reservation, per-call result tokens, cumulative tool-result tokens, truncation count, repeated file-range reads, and repeated unrefined searches. Context exhaustion after model-driven broad retrieval is recorded here as a candidate execution failure under the frozen paired-arm rule.
4. **Resource and transport reliability (observational):** wall time, request count, pre/post swap delta and I/O, memory pressure, server/API failures, natural agent completion, and clean model/process shutdown. A valid edit that cannot complete naturally remains a functional result but an agent/reliability failure.

Lock each blind candidate’s four-dimension record and evidence paths before opening `private/assignment.json` or comparing model identities.

## Task set

| ID | Type | Status |
|---|---|---|
| T01 | Known historical iOS horizontal-pan / focus-zoom regression | fixture seeded; oracle patch held privately |
| T02 | Multi-file reconnect/reconciliation behavioral regression | fixture design pending deterministic seed validation |
| T03 | Small, deterministic user feature | fixture design pending source/API review |
| T04 | Existing failing-test/build diagnosis and recovery | fixture design pending baseline normalization |
| T05 | Review-only subtle side-effect regression | fixture design pending hidden-oracle creation |

## Pi installation

Pi was installed only under this experiment tree at `tools/pi-agent/`; no global user configuration was changed.

- package: `@mariozechner/pi-coding-agent@0.73.1`
- observed CLI version: `0.73.1`
- note: its package reports a deprecation rename to `@earendil-works/pi-coding-agent`; the pinned package remains executable and is retained for reproducibility.
