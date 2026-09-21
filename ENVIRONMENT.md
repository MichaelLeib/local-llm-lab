# Environment

Observed during project initialization on 2026-09-17. Facts below are tagged by source and should be rechecked before a performance claim.

## Primary machine

| Field | Observed value | Source / status |
|---|---|---|
| Machine | MacBook Air, identifier `Mac15,13` | `system_profiler SPHardwareDataType`; observed |
| SoC | Apple M3, 8 cores (4 performance, 4 efficiency) | system profiler; observed |
| Unified memory | 16 GB (`17179869184` bytes) | system profiler + `sysctl`; observed |
| OS family/version | macOS 27.0, build `26A428` | `sw_vers`; observed |
| Root volume | 460 GiB total, 20 GiB available, 40% used | `df -h /`; observed at EXP-004 gate |
| Thermal design | Fanless MacBook Air, thermal-hacked with active water cooling | hardware class; sustained behavior still to measure |
| Other machines | Unknown | To be added only when actually inspected |

## Current local serving setup

| Component | Configured value | Status / evidence |
|---|---|---|
| Lane manager | `~/.hermes/bin/hermes-local-model` | present; status command used read-only |
| **Lane identity (authoritative)** | `~/.hermes/state/local-lanes.json` | **written by the manager on every start/ensure/stop/status — this table below is a 2026-09-17 snapshot and may be stale** |
| FAST model | ~~`ornith-ai/Ornith-1.5-9B-MLX-4bit`~~ → **`MiniCPM5-2B-Q4_K_M` (GGUF)** | promoted 2026-09-21 from EXP-020/EXP-022; verified live via `ps` on :8901 |
| FAST endpoint | `127.0.0.1:8901` | see manifest `up` flag for current state |
| DEEP model | ~~`prism-ml/Ternary-Bonsai-27B-mlx-2bit`~~ → **`Gemma-4-E4B-it-Q6_K` (+MTP)** | via `~/.hermes/bin/local-gemma4`; promoted 2026-09-21 |
| DEEP endpoint | `127.0.0.1:8919` | changed from :8902; see manifest |
| GGUF fallback | `Qwen3.8-9B-Q4_K_M.gguf` under `~/.cache/gguf/` | configured fallback path; file/revision not verified here |
| Hermes local context map | 65,536 tokens for both local providers | profile `config.yaml`; configured ceiling, not a capability claim |
| Residency rule | one local model at a time | lane-manager design; required for this machine |

The initialization status snapshot also showed 1,843.44 MiB swap used of 3,072 MiB at the EXP-004 disk gate. This is transient system state, not a benchmark baseline; do not use it to compare models.

## Installed toolchain

| Tool | Observed version / path | Notes |
|---|---|---|
| `rapid-mlx` | 0.14.1 at `/opt/homebrew/bin/rapid-mlx` | local MLX serving runtime; Python environment below |
| MLX / mlx-lm | MLX 0.32.1 / mlx-lm 0.31.3 | rapid-mlx environment; observed via package metadata |
| rapid-mlx Python | Python 3.14.7 at `/opt/homebrew/Cellar/rapid-mlx/0.14.1/libexec/bin/python` | experiment runtime candidate; no model loaded during inventory |
| `llama-server` | 0.4.1, build 10964, commit `b29c606e2` | llama.cpp server, arm64 build |
| `hf` | 1.24.0 | upgrade notice reported 1.31.0 available; no upgrade performed |
| `ollama` | installed at `/usr/local/bin/ollama` | `ollama version` is not supported by this install; version unknown |
| `python3` | `/usr/bin/python3`, 3.9.6 | do not assume this is the project experiment environment |
| `git` | `/usr/bin/git` | available |
| `clang` | Apple clang 21.0.0, arm64 target | used to compile the allocator; observed |

## EXP-001 measurement tools

Available native tools: `memory_pressure`, `vm_stat`, `sysctl`, `ps`, `top`, `iostat`, `vmmap`, `sw_vers`, and `df`. The project adds `tools/resident-memory` and `tools/collect-memory-snapshot.py` without external dependencies.

`memory_pressure` is an allocator/control utility, not a passive status query. The snapshot script uses its documented simulated mode with a timeout and never invokes its real allocation mode. EXP-001's raw artifacts are preserved; EXP-002 will use read-only snapshots around a real model process.

## EXP-002 Ornith/MLX inventory

Observed 2026-09-17 before any EXP-002 model launch or large download. Full machine-readable inventory: `results/raw/EXP-002/inventory.json`.

| Repository / build | Local status | Revision | Repository files | Quantization / notes |
|---|---|---|---:|---|
| `ornith-ai/Ornith-1.5-9B-MLX-4bit` | present at `~/.cache/huggingface/hub/models--ornith-ai--Ornith-1.5-9B-MLX-4bit/snapshots/a48173b246ac705be75c05bedf1a0666db522d53/` | `a48173b246ac705be75c05bedf1a0666db522d53` | 5.060 GB / 4.712 GiB | uniform affine 4-bit, group size 64; 5,038,161,163-byte weight file |
| `mlx-community/Ornith-1.5-9B-OptiQ-4bit` | present at `~/.cache/huggingface/hub/models--mlx-community--Ornith-1.5-9B-OptiQ-4bit/snapshots/15fa783d15b32f030b7bf2356940ba5cfb55c8ec/` | `15fa783d15b32f030b7bf2356940ba5cfb55c8ec` | 7.121 GB / 6.632 GiB | mixed 4/8-bit OptiQ; `optiq` runtime not installed |
| `ornith-ai/Ornith-1.5-9B-MLX-6bit` | downloaded and verified at `~/.cache/huggingface/hub/models--ornith-ai--Ornith-1.5-9B-MLX-6bit/snapshots/538eb2e517a3adf8691e77cc20232ef1a3af39f3/` | `538eb2e517a3adf8691e77cc20232ef1a3af39f3` | 7.298 GB / 6.797 GiB | official uniform 6-bit |
| `ornith-ai/Ornith-1.5-9B-MLX-8bit` | downloaded and verified at `~/.cache/huggingface/hub/models--ornith-ai--Ornith-1.5-9B-MLX-8bit/snapshots/b4b70543d60c81e7c418a001b74cd4352212bd44/` | `b4b70543d60c81e7c418a001b74cd4352212bd44` | 9.536 GB / 8.881 GiB | official uniform 8-bit |

The manager's FAST launch path is `/opt/homebrew/bin/rapid-mlx serve "$model" --host 127.0.0.1 --port 8901 --gpu-memory-utilization 0.85 --cache-memory-mb 3072 --lazy-load --idle-unload-seconds 1800 --no-thinking --enable-auto-tool-choice --tool-call-parser hermes --reasoning-parser qwen3`, with additional manager-controlled prefix-cache/QOS settings. This command was exercised for the 4/6/8-bit EXP-002 ladder; the download event is recorded in `results/raw/EXP-002/downloads.json`.

## Hermes profile context

- Active profile home: `/Users/<user>/.hermes/profiles/lllmtinkering`.
- Profile description: local open-weight LLM optimization and evaluation.
- Default chat model is cloud-backed `gpt-5.6-luna`; local aliases are `fast-local` and `deep-local`.
- The profile's existing local-model notes record prior measurements for several candidates; those are summarized in `RESULTS.md` as inherited evidence until raw artifacts are linked.
- QwenLoop is at `~/HermesProjects/QwenLoop`; its working tree had uncommitted experiment outputs at inspection time. This lab did not modify it.
- At setup, the existing FAST lane was up and DEEP was down. Swap usage varied across read-only status checks, so no value is treated as the EXP-001 baseline.
- At EXP-001 completion, both local lanes were down and the synthetic allocator had been released; the FAST lane remains user-stopped.
## Unknowns to resolve before benchmarking

- Exact DEEP model revision/checksum and tokenizer details remain unknown; the FAST Ornith revision and local file sizes are now recorded above.
- Actual server launch flags, quantization metadata, KV-cache defaults, and prompt-template behavior for each lane.
- Clean baseline memory pressure, swap, free disk, temperature, and power/thermal conditions.
- Repeat count and confidence intervals for inherited measurements.
- A reproducible private Hermes task set and scoring rubrics.

## EXP-003 compatibility-gate inventory

- Isolated source: `results/raw/EXP-003/source/llama.cpp-moe-expert-residency/`.
- PoC fork/branch/head: `kisasexypantera94/llama.cpp`, `moe-expert-residency`, `41ec4c4e94fd5ff6c258691f35f2fcd0d3dde892`.
- Isolated build: Metal enabled, Release, `llama-server` and `llama-cli` built successfully with AppleClang 21; CMake 4.4.3 installed for this build only.
- Official Transformers metadata: `ornith-ai/Ornith-1.5-35B-A3B`, revision `10fbf86fed7ecee4a061f8b499a618f46001cac1`; Qwen3.5-MoE, 40 main layers, 256 experts, 8 experts/token, hidden 2048, expert intermediate 512.
- Official GGUF metadata: `ornith-ai/Ornith-1.5-35B-A3B-GGUF`, revision `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`; Q4_K_M is 21,713,463,040 bytes, SHA-256 verified as `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`, and stored in the pinned snapshot. Q5/Q6 and mmproj were not downloaded.
- EXP-002-only official 6-bit and 8-bit caches were removed before the download; raw experiment artifacts remain in `results/raw/EXP-002/`.
- Free space after cleanup and Q4_K_M download: approximately 40 GiB; no model inference process is running.
- SSD read baseline: 2.322 GiB/s sequential with `F_NOCACHE`; 0.028 ms average deterministic random 4 KiB reads. Raw: `results/raw/EXP-003/ssd-baseline.json`.
- Upstream Homebrew llama.cpp remains unchanged at 0.4.1 / `b29c606e2`; it has CPU MoE offload but not the PoC disk-slot flags.

## EXP-003 first-load checkpoint

- First successful launch: isolated `llama-server`, port `18903`, `--moe-n-slots 8`, `--moe-n-layers 40`, `--no-mmap`, `--no-warmup`, `-c 2048`, `-b 2048`, `-ub 1`, `-ngl 99`.
- Initial `-b 1 -ub 1` attempt failed at `GGML_ASSERT(n_tokens_all <= cparams.n_batch)` before readiness; preserved as a configuration failure.
- Loaded-idle process footprint: 3.307 GB; active peak: 3.863 GB. Cold decode: 4.95 tok/s for 64 tokens; repeat decode: 4.32 tok/s for 128 tokens. Both text outputs were coherent and HTTP 200; no runtime tensor/NaN/GPU errors.
- System-wide IOAccelerator allocation peaked at 9.719 GB and in-use at 6.271 GB during 8 slots; these values include other Metal applications and are not a per-process model footprint.
- 16-slot comparison: 3.581 GB idle / 4.204 GB active process footprint, 4.43 tok/s decode, 31% minimum simulated free; no clear speed win over 8 slots. System-wide IOAccelerator peaked at 8.866 GB allocated / 5.896 GB in use.
- Port 18903 was stopped and verified unreachable after both runs; FAST and DEEP remained down. No 24/32-slot sweep has started.

## EXP-004 prerequisite inventory

- ExpertCache source: `results/raw/EXP-004/source/expertcache/`, checkout `e6a3b940a8cd8465be0cd8cdf0f39829ebfa6ade`.
- Pinned runtime preparation: llama.cpp `7e1e28cae36d41fe7bbe9dae7c9625de6565c063` with patch SHA-256 `6bb978ab189ded46b131edea81fbe0740d7d527797be553f91312e4704f76a63`; patch applied cleanly with `--no-build`.
- Toolchain validation: Node 26.8.1, Python 3.11.16 local venv, NumPy 1.26.4, CMake 4.4.3, AppleClang 21. `npm run check` passed and `npm test` passed 29/29.
- Target metadata: `ggml-org/gpt-oss-120b-GGUF`, revision `238abdd290bb874b90a5da1b4549881b7d05c091`, `gpt-oss-120b-MXFP4.gguf`, 63,387,346,208 bytes, expected SHA-256 `582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d`.
- Official config: `gpt_oss`, 36 layers, 128 experts, 4 experts/token, hidden/intermediate size 2,880, MXFP4, max position embeddings 131,072.
- No GPT-OSS-120B artifact is cached. Current root volume has 20 GiB available; documented runbook minimum is 80 GB before download. Download and full build are deferred; no EXP-004 model process is running.

## EXP-004 Gemma 4 follow-up

- Downloaded target: `unsloth/gemma-4-26B-A4B-it-GGUF`, revision `c099eb48e663fd284577b04978a94ffccb261841`, `gemma-4-26B-A4B-it-MXFP4_MOE.gguf`.
- Model size/hash: 16,551,048,928 bytes; SHA-256 `a8908250f2a72a5824382d488158f12b65effa24e6c6b1244e5b4818ac0a1459`.
- Same pinned ExpertCache llama.cpp build is present; MXFP4 Metal operation test passed on Apple M3.
- No `mmproj` or MTP drafter was downloaded. FAST, DEEP, and all local test ports remain down.
- First inference is deferred because `vm.swapusage` reports 2,382.38 MiB used, above the protected probe's 2 GiB maximum baseline. Memory pressure query reports 54% free.

## EXP-005 Slipstream inspection and gate

Observed 2026-09-17 before model download. Full records: `results/raw/EXP-005/phase1-freeze.json`, `compatibility-gate.md`, and `runtime-inspection.md`.

- Source: `dwijenpatel/slipstream`, pinned commit `3a892465729406944778a24064664d817617f558`, isolated under `results/raw/EXP-005/source/slipstream/`.
- Native model: `mlx-community/Qwen3.6-35B-A3B-4bit`, revision `38740b847e4cb78f352aba30aa41c76e08e6eb46`; ranged download estimate 19,529,025,048 bytes; installed `.gturbo` estimate 19,546,491,213 bytes; 1,073,741,824-byte reserve.
- Qwen runtime contract: `qwen3_5_moe`, 40 layers, 256 experts, top-8 routing, hidden 2048, expert intermediate 512, 30 linear-attention layers, 10 full-attention layers, 4-bit affine group-size 64, and 262,144 source context positions.
- Toolchain: Swift 6.4, macOS 27.0 Command Line Tools. `slipstream-repack`, `slipstream`, and `slipstream-server` built successfully; optional SwiftUI app build is blocked by missing `SwiftUIMacros` under the CLT-only developer path. The CLT contains `TestingMacros` and an explicit plugin path gets past that lookup. `xcodebuild` is unavailable.
- API: loopback OpenAI Chat Completions and Anthropic Messages, SSE streaming, function tools, and a single-prefix in-process KV cache. CLI disk snapshots are supported. The server is not a Responses API server and does not execute tools.
- Current gate snapshot: `df -h /` reports 56 GiB free (`59,243,948 KiB` exact available blocks); swap is 2,350.38 MiB used; `memory_pressure -Q` reports 60% free; no Slipstream, llama-server, or rapid-mlx model process is running.
- Disk/model state: approximately 38 GiB free at the current post-reboot clean baseline; native `.gturbo` model verified under `results/raw/EXP-005/model/qwen36.gturbo/`.
- Runtime/API state: no local model process is running after the controlled measurements. The earlier pre-reboot API/Hermes run ended at approximately 36 GiB free and 3,126.06 MiB swap; the current post-reboot clean baseline was 0 MiB swap, and the clean Hermes turn ended at 84.38 MiB swap. A dedicated `exp005` Hermes profile points only to the loopback Slipstream server; the active profile/default model was not changed. Native API/tool and Hermes results are recorded under `results/raw/EXP-005/`.

