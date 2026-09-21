# EXP-017 — ERNIE streamed-GGUF compatibility/smoke gate

**Date:** 2026-09-19  
**Status:** PASS at the load + 512-context + 24-token smoke gate; not yet a context-envelope or Hermes result.

## Hypothesis

The `llama.cpp` streamed-MoE branch can avoid the full-Metal-residency failure seen in EXP-016 by keeping a bounded per-layer routed-expert slot cache instead of materialising all ERNIE routed experts.

## Pinned implementation

- Model: `ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf`
- Model bytes: 13,331,018,624
- Runtime fork/ref: `freedomljc/llama.cpp`, commit `1248fd8fa8cfebaece5ea992e4d951c1e18bb9d5` (build reports `b9881-1248fd8fa`)
- Build: local arm64 Metal `llama-cli`, CMake Release build
- Runtime patch, local experimental clone only: classify `LLM_ARCH_ERNIE4_5_MOE` with the larger graph-node reservation used by Qwen3.5/DeepSeek4. Without it, graph construction hit `GGML_ASSERT(obj_new)` while creating ERNIE QKV graph metadata. No upstream commit/push was made.

## Final successful command

```bash
.../llama-cli \
  -m .../ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf \
  --moe-stream-cache 18s --moe-stream-io-threads 2 --moe-stream-direct \
  --no-mmap --no-warmup --fit off \
  -ngl 99 -c 512 -b 512 -ub 1 \
  -n 24 --temp 0 --seed 1234 --single-turn --simple-io \
  -p 'Return the single word PASS.'
```

`18s` is required by this branch's current multi-pass Metal implementation: ERNIE routes top-6 and the branch requires at least `3 * n_expert_used = 18` slots even for a one-token physical microbatch.

## Results

| Check | Result |
|---|---|
| Arm64 Metal binary built from pinned source | PASS |
| Streamed-MoE flags present | PASS (`--moe-stream-cache`, I/O threads, direct I/O) |
| Model load with streamed experts | PASS |
| Full GPU-layer request | PASS (`-ngl 99`) |
| Context allocation / short prefill | PASS at 512 tokens configured |
| 24-token decode | PASS, clean exit 0 |
| Prompt throughput | 4.5 tok/s |
| Generation throughput | 4.2 tok/s |
| System free-memory percentage | 73% before / 73% after |
| Swap used | 1,964.19 MiB before / 1,964.19 MiB after (0.00 MiB delta) |
| Swapouts | 0 delta |
| Pageouts | +239 (short cold disk-backed run; no sustained swapout) |
| Local FAST/DEEP lanes | remained down |
| Residual inference process after arm | none |

The model emitted an intelligible in-progress reasoning response but the 24-token cap ended before its final one-word answer. That is expected for a thinking checkpoint and is **not** scored as instruction-following success. This campaign arm only proves runtime execution, not quality or tool behavior.

## Preparation/failure sequence

1. A 6-slot cache failed before loading: this branch correctly requires 18 slots for ERNIE top-6 routing under its multi-pass Metal GEMM implementation.
2. With 18 slots, the unmodified fork failed during ERNIE graph reservation (`GGML_ASSERT(obj_new)` in QKV construction). The experimental one-line architecture classification patch increased the graph reservation and removed that failure.
3. With an artificially tiny logical batch (`-b 1`), the CLI's startup sequence failed an internal `n_tokens_all <= n_batch` assertion. Restoring the normal logical batch of 512 while retaining physical microbatch `-ub 1` resolved it.
4. The final 8-token and 24-token smoke arms both completed normally at 4.3 and 4.2 tok/s generation respectively.

## Decision

**ERNIE is no longer blocked at the basic streamed-runtime gate.** This is a real difference from EXP-016's full-residency GGUF Metal failure. It has earned the next staged feasibility arm, but it is not yet a survivor for Hermes promotion.

## Next smallest experiment

Keep the exact runtime/quant/model configuration and run a **populated 1K then 4K context** with `-ub 1`, route/cache telemetry enabled if available, and the same free-memory/swap guard. Do not move to 16K, server API, or Hermes until 4K is stable and retrieval-correct.

## Raw evidence

- `prepare/` — pinned source/build logs and CLI flag capture
- `smoke-6slots-ctx512/` — required-cache-size gate failure
- `smoke-18slots-ctx512/` — initial graph reservation failure
- `smoke-18slots-ctx512-contextfix/` — tiny-logical-batch failure
- `smoke-18slots-ctx512-batch512/` — 8-token successful arm
- `smoke-18slots-ctx512-24tok/` — final 24-token successful arm with before/after telemetry

## Matrix notification

Milestone, failure, and success notice delivered to `matrix:development`; Matrix accepted event `$9CjQCwVMjulFbT5wwTF-KX5Nz06yNw01OuLZxc4Wf0w` (`mirrored: true`).
