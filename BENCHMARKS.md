# Benchmark methodology

The benchmark answers: **is this configuration more useful in real Hermes work under its resource budget?** It is not a leaderboard-only project.

## Measurement dimensions

| Dimension | Metrics / evidence |
|---|---|
| Responsiveness | time to first token; prompt/prefill tokens per second; cold versus warm cache |
| Generation | decode tokens/sec, output length, sustained rate, wall-clock completion |
| Memory | resident/unified-memory footprint, peak pressure, swap used, OOMs |
| Capability | exact-match or rubric score on fixed tasks; factual/reasoning error patterns |
| Agent reliability | native tool-call rate, malformed-call rate, fabricated tool-result rate, task completion |
| Stability | crashes, hangs, retries, context failures, quality drift during long runs |
| Usability | qualitative notes on interaction, interruption, and coexistence with normal work |
| Thermal/sustained | rate over time, temperature/power proxies where available, responsiveness after 20–30 minutes |

Report prefill separately from decode. A high decode rate does not compensate for a multi-minute first-turn prefill in an agent session.

## Task sets

The set should grow slowly and remain versioned:

- **A — capability microtasks:** reasoning, instruction following, concise explanation, factual synthesis, and structured output with deterministic rubrics.
- **B — coding:** small bug fixes, code review, multi-file reasoning, tests, and explanation; private/proprietary material stays on-machine.
- **C — Hermes agent:** terminal/file/web/tool selection, native tool calls, recovery after tool output, and multi-turn completion.
- **D — research:** source-oriented search, citation-grounded synthesis, uncertainty handling, and resistance to unsupported claims.
- **E — context:** the same tasks at increasing prompt/context sizes, with cache state recorded.
- **F — sustained systems:** a realistic 20–30 minute mixed workload for fanless-machine behavior.

Every task set needs a version, task definitions, expected output or rubric, and a change log. Do not silently change prompts or scoring mid-comparison.

## Standard procedure

1. Record machine state: active model lanes, memory pressure, swap, power/thermal context, background load, and commit/config revision.
2. Verify only one local model is resident. If the machine is already under swap pressure, mark the run invalid as a clean baseline rather than hiding the condition.
3. Fix the model revision, runtime, server flags, context/KV settings, system prompt, tool schemas, sampling, seed, and task order.
4. Run a named baseline and candidate with one meaningful variable changed. Keep cold-cache and warm-cache observations distinct.
5. Repeat enough to expose variance; report individual runs and an aggregate (median plus range at minimum). Do not invent confidence intervals where repeat count is too small.
6. Capture both direct API measurements and at least one real Hermes end-to-end turn for any agent/tool claim.
7. Save raw output, logs, commands, and environment metadata before writing the interpretation.
8. Recheck memory/swap and process state after the run. A timeout, OOM, or fabricated tool result is a failure mode to preserve.

## Promotion rules

- Compare like with like: same tasks, prompt/template, tool schema, runtime family, model revision, context target, and machine state.
- A speed win with a quality or tool-use regression is not a promotion unless the trade-off is explicitly accepted.
- A toy tool-call prompt does not validate agent reliability. The full Hermes prompt and real executor path are required.
- Benchmark scores do not override observed instability, swap-thrash, or poor interactive coexistence.
- Keep the previous proven configuration available as a one-step rollback.
- Report inherited measurements separately from measurements reproduced by this project.
