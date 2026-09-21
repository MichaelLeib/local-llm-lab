# EXP-006 optimization sprint

## Scope

This isolated sub-experiment tests whether numerics-preserving runtime configuration can move Qwen3.8-Flash-Next/TinyTitan from the frozen 16-slot baseline toward practical Hermes use on the 16 GiB M3.

## Frozen baseline

- TinyTitan source commit: `008510e2753cc16a674cb75169ba3133cf56fa4e`
- Model: installed `qwen3.8-flash-next_125B_A6B_4Bit`; native 4-bit GTURBO representation
- Baseline CLI: 16 expert-cache slots, max context 4096, temperature 0, seed 12345, thinking off, concise messages
- Baseline sustained result: prefill 238 tokens / 14.79 s; decode 64 tokens / 24.34 s = 2.629 tok/s
- Baseline swap: 3458 MiB before / 3402 MiB after; therefore not a clean baseline
- Baseline server: 16 slots, context 4096, prompt cache off. API tool envelope passed; full Hermes did not complete.

## First bundle hypothesis

A clean post-reboot run with 24 slots (rather than 16), bounded in-process single-prefix KV reuse, explicit Hermes context accounting, and decode I/O telemetry may improve warm practical latency without altering weights or numerics.

## First bundle configuration

- 24 expert-cache slots per layer: 3,189,768,192 bytes / 2.971 GiB. The 16-slot cache is 2,126,512,128 bytes / 1.980 GiB, so 24 slots add 1,063,256,064 bytes / 0.990 GiB.
- `TINYTITAN_DECODE_IO_TRACE=1` to report decode-only expert hits, misses, and bytes.
- Server: one sequence; `--prompt-cache-mode single-prefix`; one retained prefix; 256 MiB RAM snapshot budget; no disk snapshot/cache.
- Context: target 16,384 only after request accounting validates the full Hermes prompt plus bounded output. No 65,536 context setting.
- No changed quantization, no MTP, no speculative decoding, no lossy routing, no new kernels.
- Prefetch remains at runtime default until an exposed supported control is identified and separately justified.

## Measurement order and stop rules

1. Clean resource gate and no-model snapshot.
2. 24-slot standalone correctness + 64-token sustained decode with I/O trace.
3. Stop if swap grows materially, correctness fails, or decode is not healthy enough for server testing.
4. If healthy, start isolated loopback server and measure cold/warm full-prefix cache behavior.
5. Only then test the isolated Hermes profile using a constrained real terminal tool call.

Every command, raw log, and telemetry capture is stored beneath this directory. EXP-005, its source/model, the default Hermes profile, and FAST/DEEP remain unchanged.
