# 24-slot standalone bundle arm

- Date: 2026-09-17 UTC
- Hypothesis: increasing the numerics-preserving per-layer expert cache from 16 to 24 slots may materially reduce decode I/O and improve sustained decode without unacceptable pressure.
- Command: `TINYTITAN_DECODE_IO_TRACE=1 TinyTitanCLI --model ../model/qwen3.8-flash-next_125B_A6B_4Bit --messages-file ../throughput-messages.json --max-new 64 --max-context 4096 --temperature 0 --seed 12345 --thinking off --concise --expert-cache-slots 24`
- TinyTitan commit: `008510e2753cc16a674cb75169ba3133cf56fa4e`
- Model: pinned Qwen3.8-Flash-Next 4-bit native GTURBO install.

## Result

Correctness completed with exit code 0. Prefill was 238 tokens in 15.94 s. Sustained decode was 64 tokens in 22.54 s, **2.839 tok/s**.

Decode-only I/O telemetry: 19,862 cache hits, 10,378 misses, **65.7% hit rate**, and **26.76 GiB / 428.2 MiB per generated token**. This is direct evidence that routed-expert I/O remains a major decode cost.

The clean pre-run swap baseline was 0 MiB. Post-run swap was 1,493.12 MiB. The experiment therefore does not pass the controlled-memory prerequisite for a full-prefix/server/Hermes continuation, despite the decode increase.

## Comparison with frozen 16-slot baseline

| Arm | Prefill | Decode | Decode I/O | Swap delta |
|---|---:|---:|---|---:|
| Frozen 16-slot (non-clean) | 238 / 14.79 s | 2.629 tok/s | unavailable | 3458 → 3402 MiB (confounded) |
| 24-slot bundle arm (clean) | 238 / 15.94 s | 2.839 tok/s | 65.7% hit; 428.2 MiB/token | 0 → 1493.12 MiB |

The 24-slot arm gained 0.210 tok/s (about 8%) but remains well below the 4 tok/s operational gate and created substantial new swap. Do not run the planned full-prefix cache or real Hermes portions on this condition. A 32-slot cache is not justified: it adds another ~0.990 GiB expert-cache allocation beyond 24 slots while 24 slots already produced 1.46 GiB of swap.

Raw transcript: `run.log`.
