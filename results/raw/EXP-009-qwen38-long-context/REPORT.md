# EXP-009 — Qwen3.8-Flash-Next current-runtime long-context qualification

**Status:** stopped early for memory/swap safety. This is a controlled negative gate, not a completed throughput benchmark.

## Question

Can Qwen3.8-Flash-Next become the primary local Hermes model on this 16 GiB M3 by using the current TinyTitan runtime, with at least a real 64K usable context and approximately 4 tok/s warm decode?

## Preserved starting state

- No Qwen Flash/TinyTitan process was live before this experiment; FAST and DEEP were both down.
- Baseline machine state at `2026-09-18T12:58:19Z`: swap **1,593.56 MiB**, memory-pressure free **60%**, no local-model listener.
- Existing EXP-006 source was not changed: `008510e2753cc16a674cb75169ba3133cf56fa4e`.
- Reused verified native model in place (not copied or converted): `RockTalk/Qwen3.8-Flash-Next-MLX-4bit` revision `478474da92599ad0cf9f8bd447e658b29cb8480a`, native 4-bit GTURBO, receipt hash/contents in `../EXP-006/model/.../verified-install.json`.

## Current-runtime change under test

A separate current TinyTitan checkout was cloned and built under `source/tinytitan-current/`:

- Commit: `9c03db58d86e7ac35917ee3f05cf58fbab97f666`
- Commit subject: `qsa: measure the host prefill selection before moving it to the GPU (TT-010)`
- Build: Swift 6.4, release `TinyTitanCLI`, `TinyTitanServer`, and `TinyTitanRepack`; arm64 binary hashes are in `raw/current-runtime-binaries.txt`.
- Material runtime differences versus EXP-006 include a 16-GiB-aware default expert-cache cap (half physical RAM) and newer QSA/prefill work. The arm deliberately pinned the old conservative **16 expert slots**; it did not claim the 24-GiB developer-machine 96-slot profile was safe on this host.

## Phase 2 current-runtime 7K-shaped arm

**Classification:** `stopped_for_swap` (the runner’s raw `summary.json` says `runtime_failure` only because the verified CLI PID was safety-terminated externally; `manual-safety-stop.txt` is the authoritative safety classification).

- Intended request: deterministic repeated natural-language corpus with 350 units, plus a 256-integer generation task; 36,496 prompt characters. It was constructed for an approximately 7K-token prompt, inside an 8,192-token configured context.
- The run was stopped during prefill. It never reached a timing footer, so **no accepted-token count, TTFT, prefill throughput, decode rate, cache-hit rate, or output-quality claim exists** for this arm.
- Exact CLI configuration: `--max-context 8192 --max-new 256 --temperature 0 --seed 12345 --thinking off --expert-cache-slots 16 --prefill-chunk 4096`, with `TINYTITAN_DECODE_IO_TRACE=1`, `TINYTITAN_KEEP_WIRED=1`, and default read-ahead advice. Full command/environment: `arms/phase2-short-16slot-current-7k/command.json`.
- At the manual stop after approximately 4m16s of prefill, process RSS was **5.48 GiB**; process physical footprint was **7.68 GiB** and its sampled physical-footprint peak was **8.06 GiB**.
- Swap rose from **1,585.56 MiB** to a sampled maximum of **4,387.06 MiB**, a **2,801.50 MiB / 2.736 GiB** increment. At the immediate safety capture, memory-pressure free was **21%** (the contemporaneous concise query showed 26%).
- The generated/active Metal counters in the raw `ioreg` capture are system-wide contextual telemetry, not a TinyTitan-only allocation claim.
- The CLI was stopped before decode to protect a normally active Mac. After termination, no TinyTitan/other local-model process or test listener remained; memory-pressure free recovered to 70%, while swap remained 4,227.06 MiB (macOS retains swap allocation, so this is recorded, not treated as an active footprint).

## Control comparison

EXP-006 remains the direct short-prompt control, with a different runtime commit and a much smaller 238-token prompt:

| Arm | Prompt / result | Decode | Swap increment |
|---|---|---:|---:|
| EXP-006 old TinyTitan, 16 slots clean | 238-token prefill completed | 2.368 tok/s | 400.88 MiB |
| EXP-006 old TinyTitan, 24 slots clean | 238-token prefill completed | 2.839 tok/s | 1,493.12 MiB |
| EXP-009 current TinyTitan, 16 slots, ~7K-shaped | stopped during prefill before first generated token | not measured | 2,801.50 MiB peak |

These are **not** a prefill-speed A/B: the prompt lengths and runtime commits differ. They do establish that the first realistic multi-thousand-token prefill was unsafe at only 16 slots on the present host state, before any decode benefit could be assessed.

## Decision

Do **not** advance this configuration to 32K, 64K, 128K, prefix-reuse, Hermes integration, coding, or research tests. A primary-model claim would require an actual filled 64K context and controlled memory, and the current runtime failed the much smaller real-prompt safety gate before decode.

Do not treat cooling as a remedy: this stop was unified-memory/swap pressure during prefill, not a thermal-throttling result. Do not compensate by increasing expert slots: EXP-006 already showed 24 slots consumed 1,493.12 MiB of fresh swap at a 238-token prompt; the current 7K-shaped 16-slot run already exceeded that increment.

## Next smallest useful experiment

Only if the primary-model question is reopened, first isolate a **source-level long-prefill memory fix** in a separate runtime variant and validate it with a real 4K–8K prompt and a hard swap guard **before** trying 32K. Candidate diagnosis targets are the current runtime’s prefill/KV/wired-cache lifetime, not routing top-k, model approximation, or a large parameter sweep.

## Raw artifacts

- `raw/initial-no-model-observation.json`
- `raw/current-runtime-provenance.txt`
- `raw/current-runtime-binaries.txt`
- `logs/source-clone.log`, `logs/current-runtime-build.log`
- `arms/phase2-short-16slot-current/` — preserved configuration rejection (`9047` prompt tokens exceeded the configured 8192 context; no model computation)
- `arms/phase2-short-16slot-current-7k/` — full command, prompt, pre/post snapshots, 79 samples, iostat, explicit safety-stop record, and raw stdout/stderr
