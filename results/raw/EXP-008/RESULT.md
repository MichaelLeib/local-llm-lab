# EXP-008 Phase 1 — initial envelope result

**Date:** 2026-09-18  
**Pinned runtime/model:** Slipstream `3a892465729406944778a24064664d817617f558`; EXP-005's verified `mlx-community/Qwen3.6-35B-A3B-4bit` `.gturbo` artifact at revision `38740b847e4cb78f352aba30aa41c76e08e6eb46`.  The runtime was built in EXP-008's independent `exp008-long-context` worktree. No source, default Hermes profile, FAST, or DEEP configuration was changed.

## Decision

**Do not run 64K or add 128K support in the present machine state.** The untouched 32K FP16 arm crossed its preset swap-growth stop condition before completing prefill. The 64K and 128K tests would increase the active KV reserve and are not justified after this safety result.

## Completed controls

| Arm | Outcome | Prompt tokens / generation | Timing | Swap result | Footprint evidence |
|---|---|---:|---:|---:|---|
| 16K short control | Completed, but non-clean baseline | 2,157 / 16 | 35.52 s prefill; 5.519 tok/s decode | 990.25 → 990.25 MiB | CLI peak physical footprint 2.6 GiB; server peak 2.6 GiB |
| 32K, 78% requested fill | **Stopped for swap** during standalone prefill; server/cache stage not started | No completed footer | SIGTERM at 929.558 s | 990.25 → 1,427.12 MiB; **+436.87 MiB** | Peak sampled physical footprint 3.3 GiB; minimum reported free 26% |

All arms fixed FP16 KV, 16 expert-cache slots, `lfu-aging`, auto prefill chunking, temperature 0, seed 12345, and a single model process. The local lane manager reported FAST and DEEP down before the run, and cleanup verified no Slipstream listener/process remained afterward.

## 32K safety evidence

The 32K CLI arm began with 990.25 MiB system swap and 58% memory free. Swap first rose at 67 seconds, then reached a 183.44 MiB arm delta, and finally 436.87 MiB at the 929.6-second sample. `vm_stat` recorded 31,032 additional swapout pages and 3,225 additional pageout pages. The runner's 256 MiB delta gate therefore terminated the process as designed.

The raw `summary.json` originally labels this arm `completed` despite recording `cli.stopped_for_swap: true` and return code `-15`; this is a runner-status propagation defect, not a successful run. `arm-status-correction.json` is the durable correction and the runner now emits `stopped_for_swap` for future arms.

## Interpretation

This does **not** answer whether 32K/64K FP16 could work after a controlled clean baseline or with a different memory budget. It does answer the immediate operational question: with the observed normal-workload baseline, an approximately 25.6K-token prefill is not compatible with the experiment's no-swap-heavy-usability criterion. The run was intentionally stopped rather than allowing a potentially disruptive 64K attempt.

The 16K control also exposes a separate measurement correction: `vm.swapusage` did not grow, but its `vmmap` showed per-process swapped-out mappings inherited from the machine state. Zero system-swap delta alone must not be presented as fully clean residency.

## Deferred work

1. Do not implement Q8 KV yet: this phase did not finish a healthy FP16 64K comparison and cannot attribute the 32K stop solely to active KV.
2. Before any retry, establish a separately labelled, low-background-load baseline with enough swap headroom, then repeat **only** the 32K arm using the corrected runner.
3. If that clean 32K arm passes, test existing 64K support unchanged; only then make the minimal server allow-list patch for 131,072 and repeat the same safety envelope.
4. Prefix-cache behavior and long-context retrieval were not measured at 32K because the safety gate stopped before the server stage. Do not infer them from the 16K short control; that control's identical request had `cached_tokens: 0` because its 16-token completion ended at the length cap and did not form a reusable cache continuation.

## Artifacts

- `audit/phase1-kv-context-audit.md`
- `run_phase1_context.py`
- `runs/ctx-16384-20260918T121018Z/summary.json`
- `runs/ctx-32768-20260918T121338Z/summary.json`
- `runs/ctx-32768-20260918T121338Z/arm-status-correction.json`
- `runs/ctx-32768-slots-8-20260918T142956Z/summary.json`
- `runs/ctx-32768-slots-8-20260918T142956Z/configuration-validation.json`

## Follow-up: 32K cache-slot reduction validation

The requested next cache-residency step, **16 → 8 slots**, was launched with every workload field held constant: 32K max context, 78% fill, 64 output tokens, FP16 KV, `auto` prefill, `lfu-aging`, temperature 0, and seed 12345. It failed immediately at 6.87 s, before model prefill/allocation telemetry could be collected:

```text
error: prefill routed tile depth 1 with 8 experts/tile needs 16 slots, has 8
```

This is a **runtime configuration constraint**, not a swap-guard result and not a quality or memory measurement. In the pinned runtime, the prefill scheduler (`RealForwardRunner.swift:2159-2166`) keeps a depth-1 pipeline of two 8-expert tiles, so its minimum valid routed-expert cache is `(1 + 1) × 8 = 16` slots. Although the CLI lists 8 as a general accepted value, it cannot serve this unchanged auto-prefill workload.

The failed validation left no local model resident and did not increase system swap (1,315.12 → 1,307.12 MiB). It therefore establishes neither a measured cache-memory saving nor a healthy 32K configuration, and **64K was not run**.

To make an 8-slot arm meaningful requires a separate source/runtime intervention—e.g., changing the prefill tile scheduler's pending depth or tile width—then rebuilding and treating that as a distinct variable. That would violate the requested "reduce only expert-cache slots" comparison, so it has not been done.

## Follow-up: approved 8-slot zero-lookahead runtime variant

An approved, isolated scheduler variant changed the prefill routed-tile maximum pending depth from `1 → 0` and then enabled the 8-slot cache. The release CLI/server builds succeeded and the variant reached actual 32K prefill, proving the scheduler change removes the former 16-slot admission constraint. It still failed the operational gate: the CLI prefill was stopped at 102.577 s when incremental system swap reached **+310.44 MiB** (1,307.12 → 1,617.56 MiB), above the 256 MiB limit. No completion, retrieval correctness, decode measurement, or server/prefix-cache stage was reached.

This arm is **not healthy** and therefore does not permit 64K. Its source change and full evidence are recorded in `8-slot-zero-lookahead-result.md` and `patches/8-slot-zero-lookahead.patch`. It must not be treated as a pure 16-to-8 cache-slot comparison: the scheduler lookahead change was required for validity, and the host began with a different swap baseline than the earlier 16-slot arm.
