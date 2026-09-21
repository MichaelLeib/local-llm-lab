# I/O reduction attempt — 16-slot aging-LFU policy

- Date: 2026-09-17 UTC
- TinyTitan commit: `008510e2753cc16a674cb75169ba3133cf56fa4e`
- Only variable versus the clean 16-slot trace: `TINYTITAN_EXPERT_CACHE_POLICY=aging-lfu`.
- All numerical weights, cache size, prompt, seed, sampling, context, and decode-I/O instrumentation were unchanged.

## Result

Correctness passed with exit code 0. Prefill was 238 tokens in 15.29 s; 64-token decode was **2.442 tok/s**. Decode I/O was 14,967 hits and 15,273 misses, a **49.5% hit rate**, 39.39 GiB total, and **630.2 MiB/token**. Swap grew from 0 to only 0.25 MiB.

## Comparison

| 16-slot policy | Decode | Hits | Misses | Hit rate | I/O/token |
|---|---:|---:|---:|---:|---:|
| Default LFU | 2.368 tok/s | 14,964 | 15,276 | 49.5% | 630.3 MiB |
| aging-LFU | 2.442 tok/s | 14,967 | 15,273 | 49.5% | 630.2 MiB |

The policy changed only three expert requests across the sampled decode and did not reduce I/O. The +0.074 tok/s result is within the scale of run-to-run variation and is not a promotion signal.

## Decision

This is the one evidence-supported I/O-reduction attempt permitted by the sprint stopping rule. It fails the ≥4 tok/s operational threshold; therefore do not pursue more interactive-default optimization of Flash-Next/TinyTitan on this 16 GiB M3. Do not run full-prefix cache/Hermes stages for this condition. Preserve the artifacts and return the interactive-default path to Qwen3.6 + Slipstream; Carnice-Qwen3.6 is the next low-risk model experiment when separately approved.

Raw transcript: `run.log`.
