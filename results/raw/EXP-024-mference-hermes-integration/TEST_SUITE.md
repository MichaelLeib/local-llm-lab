# EXP-024 — Mference / Qwen3.6 Hermes Integration Qualification

**Status:** designed; not yet run.  
**Scope:** a bounded, paired qualification of Mference as a replacement for the *narrow warm-session* Qwen3.6/Slipstream lane on the 16 GiB M3 MacBook Air.

## Decision this suite can make

This suite has one decision, deliberately narrower than a new autonomy benchmark:

> Does the currently built Mference server provide a measurable, safe, end-to-end Hermes benefit over the retained Slipstream configuration at an 8K context limit?

It is not a 16K/32K/64K campaign. EXP-008 already safety-stopped populated 32K FP16 prefill twice for incremental swap growth, and a cache-policy sweep was resource-unsafe before it completed a 2K request. Repeating those conditions in a new server would not answer the integration question.

The candidate is Mference at `c67e85788e9ae89142436292cc31c10144b701a7`, using the existing verified Qwen `.gturbo` artifact. Its short 64-token control measured 7.495 tok/s at the automatic 16-GiB cache rung versus 7.312 tok/s at the 16-slot control (+2.5%), with no incremental swap. That is enough to justify a bounded integration test, not a promotion.

## Fixed configurations

| Role | Runtime | Model | Context | Prompt cache | Transport |
|---|---|---|---:|---|---|
| Control | Slipstream `3a892465729406944778a24064664d817617f558` | Existing `qwen36.gturbo` | 8192 | `single-prefix` or `off` as named by arm | loopback Chat Completions |
| Candidate | Mference `c67e85788e9ae89142436292cc31c10144b701a7` | The same existing `qwen36.gturbo` | 8192 | `single-prefix` or `off` as named by arm | loopback Chat Completions |

Use `temperature=0`, `top_p=1`, `top_k=1`, `seed=12345`, and a 96-token cap unless an arm explicitly requires a longer completion.

**Important configuration correction:** `MferenceServer --help` documents `--model`, `--port`, `--max-context`, `--queue-limit`, and `--prompt-cache-mode`; it does **not** document `--expert-cache-slots` or `--prefill-chunk`. The server qualification must use only its documented flags and record startup telemetry. Do not pass undocumented expert-cache flags or infer that a CLI cache setting was applied to the server.

Candidate launch shape:

```bash
/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-015-github-runtime-dive/source/Mference/.build/out/Products/Release/MferenceServer \
  --model /Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/model/qwen36.gturbo \
  --port 8914 \
  --max-context 8192 \
  --queue-limit 1 \
  --prompt-cache-mode single-prefix
```

The server must remain bound to loopback. It is stopped by the harness at the end of every arm. No FAST, DEEP, default Hermes profile, normal `local-dev` profile, or persistent model-lane setting is changed.

## Test assets to prepare once

Create `fixtures/` and commit only small, non-secret artifacts:

1. **`base-prefix.json`** — a stable slim-Hermes system instruction plus the five already validated tools: `terminal`, `read_file`, `search_files`, `patch`, and `write_file`.
2. **`prefill-1k.json`, `prefill-2k.json`, `prefill-4k.json`** — deterministic untooled message payloads. Generate filler once, then record both SHA-256 and runtime-reported `usage.prompt_tokens`; do not rely on character count as token count.
3. **`tool-loop.json`** — a deterministic first-turn request that should call `terminal` with the read-only argument `pwd`.
4. **`tool-result.json`** — the fixed, captured output for `pwd` used in the direct-protocol loop. It is intentionally simulated so raw protocol testing never mutates a repository.
5. **`hermes-smoke-task.md`** — a disposable, read-only task: inspect a fixture repository, identify its package manager and test command, then call `terminal` to run `pwd` and `git status --short`; summarize without editing files.

The harness writes each outgoing request, canonical JSON SHA-256, response/SSE transcript, server stderr, and a `summary.json`. Captured historical Hermes payloads may seed the fixture, but every resulting fixture must be redacted and reviewed before persistence.

## Safety envelope — enforced, not merely recorded

### Admission checks before *each* server launch

Refuse the arm when any condition fails:

- another local inference process is resident;
- a listener already occupies the selected loopback port;
- root free disk is below **12 GiB**;
- baseline `memory_pressure -S -l warn -Q` reports under **55%** free memory;
- model artifact, binary, fixture manifest, or source revision is missing/mismatched;
- a prior arm failed to stop its server cleanly.

Capture baseline and five-second samples with `tools/collect-memory-snapshot.py`, `sysctl vm.swapusage`, `vm_stat`, `memory_pressure -S -l warn -Q`, process RSS, and server PID.

### Abort an active arm immediately when

- incremental swap exceeds **64 MiB** from the arm baseline;
- sampled free memory falls below **10%** twice in succession;
- the server exits, returns an SSE `error`, or returns a non-2xx response other than an expected context-rejection test;
- the first useful SSE event is absent by the arm time cap;
- any request grows beyond the 8192-token configuration limit.

Time caps: **120 s** for the 1K arm, **180 s** for the 2K arm, **360 s** for the 4K/Hermes-base arm, and **90 s** for a warm continuation. A safety stop is a valid result, not a retry condition. Terminate the process group, wait for exit, and take a post-stop snapshot.

No automatic retry after a safety stop. A failed protocol-only request may be retried once only after its complete error and server log are preserved.

## Measurements and definitions

For streaming requests, collect monotonic timestamps at:

- server process launch;
- loopback health ready;
- request dispatch;
- first non-empty assistant text delta **or first tool-call delta**;
- first complete valid tool-call object, where applicable;
- final `[DONE]` frame;
- server exit and post-stop recovery.

Definitions:

- **Server-ready time:** health endpoint available minus process launch.
- **TTF-action:** first non-empty text *or* tool-call delta minus request dispatch. This is the relevant first-response measure for tool-using turns.
- **Completion rate:** server-reported completion tokens divided by final-token time minus first useful event time. Preserve the raw server timing footer/log; do not infer a rate when usage is absent.
- **Approximate uncached prefill rate:** `(prompt_tokens - cached_tokens) / TTF-action`, explicitly labelled approximate because TTF-action includes the first generated event.
- **Cache ratio:** `cached_tokens / prompt_tokens` from `usage.prompt_tokens_details.cached_tokens`.
- **Swap delta:** `used_swap_after - used_swap_before`; absolute macOS swap is recorded but is not treated as experimental swap.

All report tables show raw token counts, elapsed values, and cache counts. They must not label full-response wall time as TTFT.

## Ordered test stages

### Stage 0 — Harness and protocol contract (candidate only)

Purpose: fail cheaply before any large prefill.

1. Launch Mference with only documented server options, `--max-context 8192`, `--queue-limit 1`, and `--prompt-cache-mode off`.
2. Validate `/health` and `/v1/models`; the returned model ID must match the request model ID used by all later fixtures.
3. Send the following 96-token-cap requests, with `stream=true` and `stream_options.include_usage=true`:
   - minimal text response (`READY.` exact-match control);
   - five-tool schema request that must return a `terminal` tool call with JSON-decodable arguments;
   - full direct tool loop: append the unchanged assistant tool-call message and the fixed `role: tool` result with matching `tool_call_id`, then request a concise completion.
4. Validate: SSE completes normally, no in-band error frame, tool-call ID is preserved, arguments parse, finish reason is correct, and usage includes prompt/cached-token data.

**Advance gate:** all three requests succeed without a resource stop. Otherwise stop EXP-024 and retain Slipstream; a cache/prefill comparison would not be interpretable.

### Stage 1 — Paired cold-prefill A/B

Purpose: detect an actual cold-turn benefit, independent of cache reuse.

Run every arm with prompt cache **off**, a fresh server process, the same fixture, and one server at a time.

| Arm | Corpus | Required samples | Pairing order |
|---|---|---:|---|
| C1 | 1K plain prompt | 1 per runtime | Slipstream → Mference |
| C2 | 2K plain prompt | 2 per runtime | Slipstream → Mference → Mference → Slipstream |
| C3 | 4K slim-Hermes base prefix + five schemas | 1 per runtime | Slipstream → Mference |

Record server-ready time separately from request TTF-action. Preserve the client request exactly; do not use different templates or schemas between runtimes.

**Advance gate:** Mference must complete every candidate arm inside the safety envelope and must not be more than 5% slower on median 2K TTF-action or completion rate. If it is materially slower, stop. If it is merely non-inferior, continue to cache qualification; the cold-prefill promotion decision remains open.

### Stage 2 — Prefix-cache behavior and invalidation (paired)

Purpose: test the feature most likely to change real Hermes latency.

For each runtime in a fresh process with `single-prefix` enabled:

1. **T0 cold:** send the 2K stable base prefix plus a brief request.
2. **T1 exact continuation:** resend the complete T0 history unchanged, append one user instruction, and measure cache ratio and TTF-action.
3. **T2 tool continuation:** send the complete history including an unchanged assistant tool-call message and matching fixed tool result, then a follow-up instruction.
4. **T3 deliberate invalidation:** modify one early stable-prefix character in a copy of T0 and send a new request. Verify that it does not falsely report a near-full cached prefix or reuse an incorrect prior response.

Use separate fresh server processes for the two runtimes. Do not interleave unrelated requests: both servers retain exactly one prefix, so a branch replaces the retained state.

**Advance gate:** candidate cache ratio for exact continuation must be at least 95%, tool continuation must preserve a substantial common prefix without a protocol failure, and median warm TTF-action must be no worse than the retained 3.12–4.50 s Slipstream reference. The invalidation request must be correct and must not display a stale response.

### Stage 3 — Hermes black-box smoke, isolated overlay (paired)

Purpose: establish that direct API success actually survives Hermes request rendering, tool dispatch, and history handling.

Create a temporary, isolated Hermes overlay pointing only to the currently running loopback server. It uses the slim five-tool schema and does **not** replace the normal full `local-dev` configuration. Run the same `hermes-smoke-task.md` sequence against control and candidate:

1. cold turn asks the model to inspect the disposable repository and call read-only `terminal(pwd)`;
2. Hermes executes only the requested read-only tool and returns its native result;
3. model produces a concise evidence-based follow-up;
4. a third continuation asks for the repository test command and a short justification.

Capture gateway dispatch, first rendered response/action, native tool-call success, tool-result submission, final text, complete Chat Completions payloads, usage/cache data, server logs, and host snapshots. The task contains no write, patch, delete, network, credential, or production-repository operation.

**Advance gate:** both control and candidate complete all three turns, candidate calls the correct tool with valid arguments, Hermes matches tool IDs correctly, no context rejection occurs, and no safety threshold trips. A direct-server success does not substitute for this gate.

### Stage 4 — Stability and recovery (candidate only)

Purpose: avoid promoting a fast but fragile one-off server.

After a clean Stage 3 candidate run:

1. stop only the server launched by the harness and verify no listener/process remains;
2. restart the same candidate command;
3. rerun the Stage 0 minimal text control and one cached two-turn continuation;
4. verify post-stop memory/swap returns near the arm baseline and no stale socket, cache corruption, or request-history error occurs.

No persistent disk-KV test is included: EXP-014 measured fast snapshot restore but an unacceptable 1.546 tok/s subsequent decode. That is a separate regression topic, not a Hermes interaction optimization.

## Promotion rules

### Candidate is *integration-qualified* only if all are true

- Stages 0–4 pass without an abort.
- The full native Hermes tool loop works in the isolated overlay.
- Mference is non-inferior on median 2K cold TTF-action and completion rate (no more than 5% regression).
- Exact history reuse is at least 95% cached and warm TTF-action is within the prior 3.12–4.50 s range.
- No request exceeds the 64 MiB swap guard and post-stop state settles without a persistent negative trend.

### Candidate earns the narrow warm-session lane only if it also gives a user-facing win

At least one must be true without any material regression:

- median paired 2K and 4K cold TTF-action improves by **15% or more**; or
- the real Hermes cold-to-warm loop is measurably faster while retaining correct native tool use, and the effect is larger than normal run-to-run variance; or
- it solves a reproducible Slipstream protocol/cache failure demonstrated by the identical fixture.

A 2.5% synthetic decode gain alone is **not** a promotion criterion. If Mference merely matches the existing warm lane, retain Slipstream and archive EXP-024 as a negative integration result.

## Explicit exclusions

- No 16K/32K/48K/64K populated-context rerun.
- No KV quantization or compression change.
- No expert-cache policy sweep; the Mference server does not expose the CLI cache-slot control in its documented interface.
- No speculative decoding/MTP, model download, model conversion, or second giant model.
- No autonomous coding or research benchmark. That requires a practical context envelope first; an 8K-only, slim-schema smoke is a transport test, not evidence of autonomous-agent readiness.

## Required final record

Write `REPORT.md` and a machine-readable `summary.json` containing the runtime/model revisions, commands, fixture hashes, server logs, raw SSE traces, system snapshots, tool-call validation, stop reasons, paired tables, and an unambiguous result:

- **promote narrow warm lane**;
- **retain Slipstream, candidate non-inferior but no meaningful benefit**; or
- **retain Slipstream, candidate failed protocol/resource/reliability gate**.

The report must explicitly state that 64K remains untested and impractical on this 16 GiB configuration unless a separate, evidence-backed memory-model change is later demonstrated.
