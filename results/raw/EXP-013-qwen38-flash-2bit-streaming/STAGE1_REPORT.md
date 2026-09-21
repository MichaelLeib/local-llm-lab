# EXP-013 Stage 1 — native top-10 2-bit streaming smoke

**Date:** 2026-09-19  
**Status:** `completed; speed-stop`  
**Raw run:** `stage1-smoke-20260919-090037/`

## Configuration

| Item | Value |
|---|---|
| Model | `manjunathshiva/Qwen3.8-Flash-Next-tq4a-tq2e-g64` revision `9e5c4343ab3a3917100c94e1b0dd39dea617faab` |
| Runtime | TurboQuant-MLX source commit `d1c34c63bc99f5744f409868b198cc692b84b65c`; package 0.27.0 |
| MLX / MLX-LM | 0.32.2 / 0.31.3 |
| Expert cache | 1.0 GB |
| Routing | `--max-active-experts 0`: native top-10; no K reduction |
| PLE | `--ngram-offload` on; runtime reported 17.88 GiB kept out of GPU memory |
| Decode tricks | No MTP, no speculation, no lookahead/prefetch-ahead, no router approximation, no `--fast` |
| Prompt | 30 tokenizer tokens, deterministic factual task |
| Generation | requested 48 tokens; runtime generated 31 (timing footer reports 30 accepted generated tokens) |

## Functional result

The smoke path is real and functionally coherent:

- Loader completed in 1.0 s with 0.51 GB resident RSS before decode.
- Runtime replaced 144 routed expert projections with streaming readers.
- It reported PLE/n-gram offload active and automatically selected F_NOCACHE for the 55.8 GB model on 17.2 GB RAM.
- The output correctly answered **Paris** and supplied a coherent explanation; no malformed logits, repetition collapse, or runtime corruption occurred.

## Decode and I/O result

| Metric | Observed |
|---|---:|
| Runtime generation footer | **1.475 tok/s** for 31 generated tokens |
| End-to-end accepted-token footer | **1.0 tok/s** for 30 tokens in 30.3 s |
| Peak process RSS | 3.71 GB |
| Peak MLX memory | 3.87 GB |
| Expert-cache hit rate | 23.6% |
| Cache resident | 1.00 GB |
| Critical expert reads | 21.6 GB |
| Coalescing | 46,770 expert loads in 43,036 range reads; 1.09 experts/read |
| Approx. bytes/output token | 697–720 MB decimal / 664–687 MiB, depending on the runtime footer token convention |
| Approx. effective expert-read throughput | 0.96–0.99 GiB/s at the 1.475 tok/s footer rate |

The result is below the **3.5 tok/s hard stop**, and far below the 4.0 tok/s target. There is no basis for Stage 2, quality A/B, long-context, or a custom runtime port under the experiment protocol.

## Safety result

No severe swap event occurred during this tiny generation.

- System swap: 1,859.25 MiB before and after (delta 0 MiB).
- Pageouts: +122 pages = approximately 1.91 MiB.
- Swapouts: +0 pages.
- Memory-pressure free: 80% before, 59% immediately after; it recovered to 70% on the subsequent idle check.
- The system compressed memory substantially during the run (+401,628 compression events), but process/MLX peaks remained below 4 GB and no host-instability guard fired.

The smoke arm is therefore **memory-safe but decisively too slow**. This is an I/O/cache-miss-limited result: 1 GB cache attained only 23.6% hit rate and required roughly 0.7 GB of critical expert traffic per output token, instead of the approximately <=300 MiB/token budget implied by the 4 tok/s target.

## Decision

**Stop EXP-013 after Stage 1.** The central 2-bit hypothesis did not cross the minimum speed gate. Do not spend engineering effort on a custom Slotstream/TurboQuant hybrid, Stage 2 decode sweep, quality A/B, or long-context work for this representation on the 16 GB M3. Preserve the acquired model, runtime, raw telemetry, and corrected accounting evidence.
