# EXP-015 — GitHub runtime deep dive: Qwen3.6-35B-A3B on 16 GB M3

**Date:** 2026-09-19  
**Question:** Can the existing Qwen3.6 / Slipstream configuration materially improve its decode, prefill, repeat-turn, or context numbers?

## Executive answer

There is **one measured, safe incremental improvement**: upgrade the runtime lineage to [Mference](https://github.com/NeelM0906/Mference) at `c67e85788e9ae89142436292cc31c10144b701a7` and use **32 expert-cache slots** on this 16 GiB Mac, with the existing verified `.gturbo` artifact. On the identical 64-token greedy control this produced **7.495 tok/s vs 7.312 tok/s at 16 slots** (+2.5%), without swap growth. This is a small win, not a path to 10–13 tok/s or safe 64K.

The projects with theoretically much larger speed claims require a completely different, larger GGUF model artifact and substantially more working-set/disk headroom. They are not safe or credible upgrades for this 16 GiB / 16 GiB-free-SSD envelope.

## Local measurements

Same runtime, model, prompt, temperature=0, 64 generated tokens, 8192 context, trusted receipt verification:

| Runtime | slots | prefill | decode | decode rate | swap delta | free memory after |
|---|---:|---:|---:|---:|---:|---:|
| Mference `c67e857`, control | 16 | 19 tok / 2.30 s | 8.75 s | **7.312 tok/s** | +0.19 MiB | 72% |
| Mference `c67e857`, candidate | 32 | 19 tok / 2.34 s | 8.54 s | **7.495 tok/s** | **0 MiB** | 63% during test; 72% after cleanup |

`32` slots increases all-hit layer steps from 45/2520 (1.8%) to 194/2520 (7.7%), but most latency remains GPU gaps/unaccounted waits; cache is not the dominant bottleneck. Both runs exited successfully; no Mference or other inference process remained.

Raw data:
- `raw/mference-control-20260919T073036Z/`
- `raw/mference-control-20260919T073114Z/`

A larger-prefix A/B was launched but halted rather than permitting a long unbounded run after it exceeded the short experiment window. It yields **no prefill result** and must not be interpreted as a regression.

## Candidate evaluation

### 1. Mference — **adopt for controlled integration test**
- Repository: <https://github.com/NeelM0906/Mference>
- Built locally: release `MferenceCLI` and `MferenceServer`; build succeeded (warnings only).
- Same Qwen checkpoint revision as the existing model (`mlx-community/Qwen3.6-35B-A3B-4bit` revision `38740b...`), and it accepted the existing `.gturbo` artifact: no model download or conversion.
- Relevant changes: 32-slot automatic rung for 16 GiB hosts; chunked prefill; bounded expert streaming; one-prefix OpenAI server cache with returned cached-token count; OpenAI-style function calls.
- Evidence: measured +2.5% decode at 32 slots with no incremental swap. 
- Caveat: its public high-memory benchmark claims are **24 GiB M5 / 256 GiB M3 Ultra**, not this machine. Do not transfer them to M3/16 GiB.

Recommended next measured experiment: a bounded 1K/2K/4K Hermes-prefix prefill comparison using this runtime with watchdogs and baseline-matched prompt rendering. Do not alter the global local lane until it passes real Hermes tool-call compatibility and repeat-turn cache tests.

### 2. AtomicBot `atomic-llama-cpp-turboquant` — **do not install/test on this machine now**
- Repository: <https://github.com/AtomicBot-ai/atomic-llama-cpp-turboquant>
- It offers Qwen3.6 NextN / MTP shared-model decoding plus `turbo3` KV cache, with reported 24–36% MoE throughput improvement on a **48 GiB M4 Max**.
- Required recommended Q4 MTP GGUF is about **20.7 GiB**, exceeding current 16 GiB free disk before caches/build artifacts, and its GPU working set also exceeds this Mac’s practical envelope.
- Independent upstream Apple Metal evidence is adverse: [llama.cpp issue #23011](https://github.com/ggml-org/llama.cpp/issues/23011) reports Qwen3.6 self-MTP falling from 26.23 to 1.93 tok/s on an M1 Pro despite 95.6% acceptance, plus memory pressure/OOM at normal parallelism.
- Decision: reject for this M3/16 GiB lane. The headline speedup is neither same hardware nor same memory regime.

### 3. TurboQuant-MLX — **not a Qwen3.6 improvement on 16 GiB**
- Repository: <https://github.com/manjunathshiva/turboquant-mlx>
- It supports streamed Qwen3.6 and KV compression, but published 35B results are on 48+ GiB devices. Its own long-context tests show compressed KV can reduce decode speed while helping prompt throughput, and the benefit is model/hardware dependent.
- The Qwen3.6 tq3 model is ~16 GB on disk, leaving essentially no safe disk headroom here. A resident run is reported at ~18 GB peak on a 48 GB M5 Pro.
- Decision: no download or conversion. It cannot safely solve our 32K/64K memory ceiling.

### 4. vMLX — **feature-rich server, unsupported performance claim for this target**
- Repository: <https://github.com/jjang-ai/vmlx>
- Advertises prefix cache, paged/KV disk cache, KV quantization, and speculative decoding, but no verified 16 GiB Qwen3.6-35B-A3B measurements were found in this investigation. Its broad model compatibility is not evidence that its cache mechanisms improve Qwen3.6’s hybrid MoE path.
- Decision: reject as a primary performance candidate without a target-specific reproducible benchmark.

### 5. Swiftlet — **no demonstrated improvement relative to current lane**
- Repository: <https://github.com/leonickson1/Swiftlet>
- Its own M5 results for the Qwen3.6 4-bit streamed container are 7–11 tok/s; M1/16 GB anchor is ~2.45 tok/s, and documentation says long-prompt prefill runs roughly at decode speed.
- It requires a separate 18 GB qpack artifact, beyond available disk headroom, and does not promise a solution to cold-prefill or 64K.
- Decision: reject.

## What cannot be improved with a configuration switch

1. **64K:** Qwen3.6’s 32K populated FP16 envelope already stopped on swap growth. A runtime configuration cannot create safe unified-memory capacity. KV compression on this architecture is a memory experiment, not a proven speed or quality win; the investigated MLX project’s data also warns that FP16 can remain faster.
2. **Cold Hermes prefill:** it remains the highest-value target, but must be tested with a strict watchdog. Mference adds chunked prefill, yet no controlled result at a Hermes-like 1K–5K prefix was completed here.
3. **Decode:** expert-cache enlargement is diminishing-return territory. Measured all-hit rate rose substantially while decode increased only 2.5%, showing scheduling/GPU waits dominate.

## Reproducible candidate command

```bash
/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-015-github-runtime-dive/source/Mference/.build/out/Products/Release/MferenceServer \
  --model /Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/model/qwen36.gturbo \
  --port 8914 \
  --max-context 8192 \
  --expert-cache-slots 32
```

Use loopback only. Do **not** promote this command into Hermes yet: validate OpenAI request shape, tool calling, full conversation history prefix reuse, and a bounded cold/warm TTFT benchmark first.

## Sources

- Mference repository and local source inspection: <https://github.com/NeelM0906/Mference>
- Mference Qwen cache/prefill controls: local `docs/QWEN36_PERFORMANCE.md` and `docs/RUNTIME_CONTROLS.md` at `c67e857`.
- AtomicBot NextN implementation and its M4 Max benchmark context: <https://github.com/AtomicBot-ai/atomic-llama-cpp-turboquant/blob/master/NEXTN.md>
- Apple Metal MTP negative evidence: <https://github.com/ggml-org/llama.cpp/issues/23011>
- TurboQuant-MLX 48 GiB Qwen3.6 KV results: <https://github.com/manjunathshiva/turboquant-mlx/issues/14>
- Swiftlet stated 16 GiB / Qwen3.6 design and performance: <https://github.com/leonickson1/Swiftlet>
