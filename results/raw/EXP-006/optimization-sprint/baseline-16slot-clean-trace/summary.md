# Clean 16-slot decode-I/O baseline

- Date: 2026-09-17 UTC
- Command: `TINYTITAN_DECODE_IO_TRACE=1 TinyTitanCLI --model ../model/qwen3.8-flash-next_125B_A6B_4Bit --messages-file ../throughput-messages.json --max-new 64 --max-context 4096 --temperature 0 --seed 12345 --thinking off --concise --expert-cache-slots 16`
- TinyTitan commit: `008510e2753cc16a674cb75169ba3133cf56fa4e`

## Result

The clean 16-slot control passed correctness with exit code 0. It prefilled 238 tokens in 15.30 s and decoded 64 tokens in 27.02 s: **2.368 tok/s**.

Decode-only I/O telemetry: 14,964 cache hits, 15,276 misses, **49.5% hit rate**, **39.39 GiB total**, and **630.3 MiB per generated token**. Swap changed from 0 to 400.88 MiB.

## Paired comparison

| Configuration | Decode | Hit rate | Misses | Expert I/O/token | Swap delta |
|---|---:|---:|---:|---:|---:|
| 16 slots, clean trace | 2.368 tok/s | 49.5% | 15,276 | 630.3 MiB | +400.88 MiB |
| 24 slots, clean trace | 2.839 tok/s | 65.7% | 10,378 | 428.2 MiB | +1493.12 MiB |

The larger cache reduced misses by 4,898 (32.1%) and expert SSD traffic by 202.1 MiB/token (32.1%), while increasing decode by 19.9%. This establishes cache-miss/I/O as a material decode bottleneck, but the extra 24-slot working set produces unacceptable swap for an interactive configuration.

Raw transcript: `run.log`.
