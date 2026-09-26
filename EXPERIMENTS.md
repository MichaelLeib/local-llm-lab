# Experiments

This register uses IDs local to Local LLM Lab (`EXP-001`, `EXP-002`, …). Each experiment is preregistered before execution. Results are appended rather than silently rewritten.

## Status

**EXP-001 complete through the exploratory 11 GiB level.** All subjective ratings were 0/5; its raw measurements are preserved unchanged. **EXP-002 primary 4/6/8-bit real-MLX ladder is complete; EXP-003 direct 8/16-slot inference and the Hermes bridge verification are complete; EXP-004 is paused at its GPT-OSS disk gate after the unprobed Gemma payload was removed with provenance retained; EXP-005 native Qwen install, standalone feasibility, stable prefill/decode sweep, disk-KV test, OpenAI API/tool loop, and a constrained Hermes terminal-tool turn are complete; EXP-006 Phase 1/2 and isolated TinyTitan build are complete. EXP-011 Qwen3-Coder-Next/Swiftlet completed static compatibility, direct streamed QPACK acquisition, and tiny smoke. Its intended-~5K guarded populated-context arms were stopped before a completion at both cache sizes: +315.75 MiB incremental swap at 2 GiB cache and +375.94 MiB at 1 GiB cache. No long-context, tool-use, or Hermes qualification is claimed.**

## Backlog

| ID | Candidate | Hypothesis / question | Primary gate |
|---|---|---|---|
| EXP-001 | Practical LLM RAM budget under normal workload | How much resident memory can a local LLM occupy continuously before normal Mac use becomes noticeably or unacceptably degraded? | Objective VM measurements combined with the user's subjective responsiveness rating |
| EXP-002 | Practical RAM budget using real Ornith MLX workloads | How much actual MLX/Metal working set can coexist with the user's normal workload before idle or active inference becomes uncomfortable? | OS-visible footprint plus MLX counters and separate idle/active subjective ratings |
| EXP-003 | MoE active-memory feasibility | Can a capable MoE reduce active RAM through expert offloading/streaming without unacceptable prefill, decode, or reliability cost? | Exact resident/active memory accounting and sustained end-to-end Hermes run |
| EXP-004 | Context and KV-cache sweep | Which context/KV settings preserve task quality while reducing memory and first-turn latency? | Fixed model and task set; quality regression threshold recorded first |
| EXP-005 | Slipstream + Qwen3.6-35B-A3B | Practical SSD-streamed MoE runtime, persistent prefix reuse, and Hermes tool-use viability | Native standalone correctness, measured memory/latency, cache benefit, and tool-call success |
| EXP-006 | Qwen3.8-Flash-Next on TinyTitan | Can a 125B-A6B Flash-Next model remain usable through bounded SSD streaming on the actively cooled M3 MacBook Air? | Install/runtime correctness, sustained throughput drift, memory pressure, thermal proxy, and Hermes tool use |
| EXP-007 | Agent/tool-use reliability | Which model/runtime/scaffold combinations complete Hermes coding and research tasks without fake or malformed tool calls? | Native tool-call success and task completion rubric |
| EXP-008 | Cross-machine portability | Which findings survive on a second Apple Silicon machine or a different memory tier? | Same protocol, explicit hardware normalization, no extrapolation from one Mac |
| EXP-009 | Qwen3.8-Flash-Next current-runtime long-context requalification | Can a newer TinyTitan runtime safely reach a real 64K Hermes envelope on this 16 GiB M3? | Real 4K–8K gate first; then populated 32K/64K/128K only if swap, decode, and prefix reuse remain operational |
| EXP-011 | Qwen3-Coder-Next 80B-A3B + Swiftlet | Can a 3B-active 80B coding MoE fit safely through direct SSD expert streaming and qualify for 64K Hermes use? | Storage-safe direct qpack acquisition, then real 5K–8K gate before any long-context or Hermes claim |
| EXP-013 | Qwen3.8-Flash-Next TurboQuant 2-bit expert streaming | Can native top-10 2-bit routed experts exceed 4 tok/s safely on this 16 GiB M3? | **Stopped:** corrected memory accounting passed, but real 1 GB-cache native-top-10 smoke measured 1.475 tok/s / 1.0 end-to-end (<3.5 hard stop); no Stage 2+ work |

## EXP-001 — Practical LLM RAM Budget Under Normal Workload

**Status:** complete through the exploratory 11 GiB level; raw measurements and subjective records are preserved under `results/raw/EXP-001/`.

- **Purpose:** estimate a comfortable budget, heavy-work budget, practical ceiling, and observed pain threshold for a continuously resident local-LLM-like footprint.
- **Hypothesis:** the useful design limit is set by the combination of objective memory behavior and perceived responsiveness, not by the largest allocation macOS can technically sustain.
- **Machine:** detect and record at run time; current known machine is documented in `ENVIRONMENT.md`.
- **Synthetic allocator:** `tools/resident-memory` commits and touches anonymous pages once, then idles. It does not continuously sweep memory and does not use `mlock`.
- **Snapshot collector:** `tools/collect-memory-snapshot.py` records JSON containing `vm_stat`, swap/load sysctls, simulated memory-pressure output, disk, and top process RSS data. It applies no pressure itself.
- **Targets:** 6, 7, 8, 9, and 10 GiB, in that order; refine around the comfortable/annoying transition only after the first pass.
- **Baseline:** capture only after the user confirms the normal workload is ready.
- **Per-level procedure:** allocate and stabilize; capture objective snapshot; tell the user the target is active; let the user use the Mac; collect a 0–5 rating and symptoms; do not advance automatically.
- **Subjective scale:** 0 indistinguishable; 1 tiny; 2 noticeable but comfortable; 3 clearly degraded but tolerable; 4 annoying; 5 painful/disruptive.
- **Abort conditions:** stop before increasing if memory pressure is severe, swap is growing rapidly, the system becomes unstable, or the user reports pain. Release with Ctrl-C/SIGTERM.
- **Raw artifacts:** `results/raw/EXP-001/baseline.json`, then `level-06.0-gib.json` through `level-10.0-gib.json`, plus any refinement levels and a run log.
- **Limitations:** anonymous resident pages are not identical to memory-mapped weights, Metal allocations, wired memory, KV cache, or expert streaming. This experiment establishes a planning constraint; later model-specific runs must validate it.

## EXP-002 — Practical RAM Budget Using Real Ornith MLX Workloads

**Status:** primary 4/6/8-bit ladder complete. Official 4-bit and 6-bit checkpoints scored 0/5 idle and active degradation; official 8-bit completed warm-up but failed stable-server validation, so no 8-bit usability rating is assigned. All lanes are stopped. EXP-001 raw artifacts are not modified.

- **Purpose:** measure the actual MLX/Metal working set and usability boundary of real Ornith inference under the user's normal Mac workload.
- **Reason for this experiment:** EXP-001 showed that pageable anonymous allocation is an inadequate proxy: macOS made most of the requested footprint non-resident while the Mac remained responsive.
- **Current reference already present:** `ornith-ai/Ornith-1.5-9B-MLX-4bit`, revision `a48173b246ac705be75c05bedf1a0666db522d53`, 5.060 GB decimal repository files / 4.712 GiB, uniform 4-bit affine group-size-64 quantization.
- **Additional existing build:** `mlx-community/Ornith-1.5-9B-OptiQ-4bit`, revision `15fa783d15b32f030b7bf2356940ba5cfb55c8ec`, 7.121 GB decimal / 6.632 GiB, mixed 4/8-bit OptiQ quantization. `optiq`/`mlx-optiq` is not installed, so this is not silently included in the primary ladder.
- **Primary ladder:** official 4-bit already present (~5.06 GB) → official 6-bit (~7.298 GB; downloaded and verified) → official 8-bit (~9.536 GB; downloaded and verified). The official variants keep the repository family, architecture, tokenizer, and serving path as constant as practical.
- **Optional secondary point:** evaluate the existing OptiQ build only after runtime compatibility and any dependency approval are resolved; do not install its runtime as part of this inventory.
- **Storage event:** official 6-bit plus 8-bit repository files added 15.678 GiB; current root free space is 58 GiB. Verification details are in `results/raw/EXP-002/downloads.json`.
- **Runtime inventory:** rapid-mlx 0.14.1, MLX 0.32.1, mlx-lm 0.31.3, Python 3.14.7 at `/opt/homebrew/Cellar/rapid-mlx/0.14.1/libexec/bin/python`.
- **Serving configuration to preserve:** `rapid-mlx serve`, loopback only, FAST port 8901, `--gpu-memory-utilization 0.85`, `--cache-memory-mb 3072`, `--lazy-load`, `--idle-unload-seconds 1800`, Hermes tool parser, Qwen3 reasoning parser, and no-thinking mode. No limits will be changed for the experiment.
- **Measurement split:** before load; loaded/idle; during active standardized inference; immediately after generation; post-stop release verification. Capture `footprint`, RSS, VM statistics, memory pressure, swap delta, compressor, wired memory, MLX active/peak/cache counters, and generation/prefill timing.
- **Subjective gate:** the user rates idle and active inference separately on the existing 0–5 scale. Do not advance to a larger model automatically; stop at rating 4–5 or clearly severe pressure.
- **Raw artifacts:** `results/raw/EXP-002/` with an inventory snapshot first, then per-model commands, system snapshots, MLX metrics, timings, and subjective records.
- **Not in scope:** quality ranking, thermal optimization, BF16/full precision, context sweep, MoE work, or memory-limit tuning. Those remain separate experiments.

## EXP-003 — Ornith-1.5-35B-A3B SSD-backed MoE expert streaming feasibility

**Status:** Phase 1 compatibility research, Phase 2 SSD baseline, approved Phase 3 Q4_K_M acquisition, guarded 8-slot first-load/text-generation checkpoint, and a controlled 16-slot comparison are complete. Both configurations generated coherent text; 16 slots showed no meaningful speed advantage. No 24/32-slot test has started. A subjective usability rating for the 16-slot run and reference-equivalence check remain.

- **Purpose:** determine whether exact text inference can keep most 35B-A3B expert weights on SSD while maintaining a bounded Metal working set and useful decode speed on the 16 GiB Mac.
- **Chosen implementation:** `kisasexypantera94/llama.cpp`, branch `moe-expert-residency`, head `41ec4c4e94fd5ff6c258691f35f2fcd0d3dde892`, PR base `fda8528aa8c1d8ecb2a5cd2b6e85c43ef5425b6b`. Full provenance: `results/raw/EXP-003/source-provenance.json` and `results/raw/EXP-003/compatibility-gate.md`.
- **Build:** isolated `GGML_METAL=ON`, `llama-server` and `llama-cli` built successfully with AppleClang 21. CMake 4.4.3 was the only added build dependency.
- **Architecture verification:** official config revision `10fbf86fed7ecee4a061f8b499a618f46001cac1` confirms `qwen3_5_moe`, 40 main layers, 256 experts, 8 experts/token, 2048 hidden, 512 expert intermediate, and hybrid linear/full-attention layers. The fork's offloader is shape/stride/name based rather than hard-coded to 128 experts or Qwen3.
- **Official target:** `ornith-ai/Ornith-1.5-35B-A3B-GGUF`, revision `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`, Q4_K_M file 21,713,463,040 bytes, SHA-256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`. Download verification: `results/raw/EXP-003/download-verification.json`; header/tensor metadata: `results/raw/EXP-003/gguf-header.json`. Q5/Q6 and mmproj remain excluded.
- **Initial slot plan:** 8 slots first (exact conservative descriptor estimate 596.8 MiB across 41 GGUF expert layers, source-level ubatch ceiling 1); 16/24/32 only after correctness and memory safety. Exact estimate: `results/raw/EXP-003/memory-model-estimate.json`.
- **Safety gate:** preferred active working set <=7.5 GiB, acceptable experimental <=8.5 GiB, hard target approximately 9 GiB. Abort on unstable behavior or approaching the ceiling; do not configure a sustained ~13 GiB Metal footprint.
- **Next action:** do not promote the model. The MLX-native option is preserved as a blocked compatibility result; pursue either a Qwen3.5-MoE adapter for MLX disk streaming or the previously proven llama.cpp backend with a compatible Hermes bridge. Do not start 24/32 automatically.

## EXP-004 — GPT-OSS-120B page-aware SSD expert streaming on 16 GiB Apple Silicon

**Status:** Phase 1 freeze and Phase 2 compatibility checks complete; blocked at the pre-download disk gate on 2026-09-17. No GPT-OSS-120B weights were downloaded, no ExpertCache model build was started, and no local model service was launched.

- **Purpose:** test whether page-aware expert views and routed prefetch can execute the official 63.4 GB GPT-OSS-120B MXFP4 checkpoint on this 16 GiB M3 Mac, then characterize correctness, working set, prefill/decode, and Hermes tool use.
- **ExpertCache source:** `amos-labs/expertcache`, checkout `e6a3b940a8cd8465be0cd8cdf0f39829ebfa6ade`, isolated under `results/raw/EXP-004/source/expertcache/`.
- **Pinned runtime:** llama.cpp revision `7e1e28cae36d41fe7bbe9dae7c9625de6565c063`; ExpertCache patch applied cleanly with SHA-256 `6bb978ab189ded46b131edea81fbe0740d7d527797be553f91312e4704f76a63`.
- **Model target:** `ggml-org/gpt-oss-120b-GGUF`, revision `238abdd290bb874b90a5da1b4549881b7d05c091`, `gpt-oss-120b-MXFP4.gguf`, 63,387,346,208 bytes, expected SHA-256 `582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d`.
- **Architecture:** official config confirms `gpt_oss`, 36 layers, 128 experts, 4 experts/token, hidden/intermediate size 2,880, MXFP4 quantization, and 131,072 maximum positions.
- **Toolchain:** Node 26.8.1, Python 3.11.16 project venv, NumPy 1.26.4, CMake 4.4.3, AppleClang 21, and CommandLineTools. `npm run check` passes; `npm test` passes 29/29 in the local venv.
- **Disk gate:** only approximately 20 GiB free versus the documented 80 GB minimum and a 59.0 GiB binary checkpoint before build/temp headroom. Download explicitly deferred; ask for approval only after sufficient internal space is freed.
- **Raw artifacts:** `results/raw/EXP-004/phase1/phase1-freeze.json`, `compatibility-gate.md`, `disk-gate.json`, `disk-inventory.json`, `runtime-prepare-no-build.log`.
- **Preserved baseline:** EXP-003 Ornith source, model, bridge, Hermes defaults, FAST, and DEEP were not modified.

### EXP-004-Gemma — Gemma 4 26B-A4B MXFP4 follow-up

- **Status:** model acquisition and runtime build complete; first inference deferred because current swap use is 2.38 GiB, above the protected 2 GiB baseline limit.
- **Model:** `unsloth/gemma-4-26B-A4B-it-GGUF`, revision `c099eb48e663fd284577b04978a94ffccb261841`, `gemma-4-26B-A4B-it-MXFP4_MOE.gguf`, 16,551,048,928 bytes, SHA-256 `a8908250f2a72a5824382d488158f12b65effa24e6c6b1244e5b4818ac0a1459`.
- **Why MXFP4:** the ExpertCache patch activates on MXFP4 expert tensors; the official ggml-org Q4_0 file would not test the same page-aware path.
- **Architecture:** Gemma4ForConditionalGeneration, 30 layers, hidden size 2,816, 128 experts, 8 routed experts/token plus a shared expert, 704 expert intermediate size, 262,144 context, 1,024 sliding window.
- **Runtime:** same isolated ExpertCache patch and pinned llama.cpp build as EXP-004; Apple M3 `MUL_MAT_ID` MXFP4 operation test passed (`supported=1`).
- **Intended first probe:** context 4,096; batch 4; micro-batch 1; 128 ExpertCache slots; CPU fill and zero-copy; no grouping or prefetch; one generated token.
- **No multimodal projector or MTP drafter was downloaded.**
- **Artifact:** `results/raw/EXP-004/gemma4-26B-A4B/acquisition.json`.

## EXP-005 — Slipstream + Qwen3.6-35B-A3B practical local Hermes model

**Status:** Phase 1 repository/runtime inspection, Phase 2 compatibility/resource gate, native Qwen install, and first guarded standalone probe complete on 2026-09-17. Slipstream source is isolated and pinned; the model is verified. No Hermes server or default lane has been started. The next measurements must separate cold startup from stable prefill/decode and must retain the non-clean swap baseline.

- **Purpose:** determine whether Slipstream's bounded SSD expert streaming and persistent KV/prefix reuse make Qwen3.6-35B-A3B practical for interactive Hermes coding and research on the 16 GiB M3 Mac.
- **Isolated source:** `dwijenpatel/slipstream`, commit `3a892465729406944778a24064664d817617f558`, under `results/raw/EXP-005/source/slipstream/`. No local source modifications.
- **Native model path:** selector `qwen36`, source `mlx-community/Qwen3.6-35B-A3B-4bit`, revision `38740b847e4cb78f352aba30aa41c76e08e6eb46`, ranged download approximately 19,529,025,048 bytes, installed `.gturbo` estimate 19,546,491,213 bytes, with 1,073,741,824-byte reserve.
- **Architecture verified:** `qwen3_5_moe`, 40 layers, 256 experts, top-8, hidden 2048, expert intermediate 512, 30 linear-attention layers, 10 full-attention layers, 4-bit affine group-size-64 weights plus 8-bit router/gate tensors, source context 262,144.
- **Build:** `swift build -c release --product slipstream-repack`, `slipstream`, and `slipstream-server` all pass under Swift 6.4/macOS 27 Command Line Tools. The optional SwiftUI Mac app fails because `SwiftUIMacros` is unavailable. The CLT contains `TestingMacros`; supplying its plugin path allows compilation to proceed, but the full package still cannot complete because the SwiftUI target is unavailable. No test pass count is claimed.
- **API:** loopback OpenAI Chat Completions and Anthropic Messages, SSE streaming, function tools, Qwen tool-call parser, one in-process single-prefix cache. Standalone CLI supports disk KV snapshots. Server does not implement Responses API or structured outputs.
- **Resource gate:** native install completed; final verification reports approximately 36 GiB free after the 19.55 GB model install and source build. The post-reboot clean probe and prefill sweep both maintained 0 MiB swap at 16 slots; the clean full Hermes turn ended at 84.38 MiB swap. FAST, DEEP, Hermes defaults, EXP-003, and EXP-004 are unchanged.
- **First probe:** 16 expert slots, 4,096 context, automatic prefill chunk, deterministic 8-token completion. Output was exactly `READY.` with exit code 0; cold prefill footer was 5 tokens in 8.81 s and decode was 8.325 tok/s. Peak sampled process footprint was 1,445 MB; peak RSS was 363.9 MB; no swap growth. This is a correctness/feasibility result, not a stable prefill benchmark.
- **Clean post-reboot probe:** same settings after reboot with 0 MiB swap; exact `READY.` at 8.404 tok/s, 1,460 MB peak physical footprint, 269,056 KiB peak sampled RSS, and no swap growth. The clean cold prefill was 14.22 s because the model/file cache was cold.
- **Raw artifacts:** `results/raw/EXP-005/phase1-freeze.json`, `compatibility-gate.md`, `runtime-inspection.md`, build logs, `model/qwen36.gturbo/verified-install.json`, `first-probe/summary.json`, `first-probe-clean/summary.json`, `prefill-sweep-clean/summary.json`, `kv-snapshot-clean/summary.json`, and `hermes-tool-test-clean-reboot-result.json`.

## EXP-006 — TinyTitan + Qwen3.8-Flash-Next SSD-streamed capability jump

**Status:** Phase 1 freeze, Phase 2 runtime/model/storage inspection, isolated TinyTitan release build, main native 4-bit model install, operational probe, and bounded optimization sprint are complete. The model/API/tool envelope is compatible but the candidate failed the interactive-default gate on this 16 GiB M3: a clean 24-slot arm reached 2.839 tok/s with 1,493.12 MiB swap, and the one evidence-supported 16-slot aging-LFU I/O-reduction arm did not reduce cache misses. No further default-oriented optimization is planned; preserve the artifacts and do not promote.

- **Purpose:** determine whether Qwen3.8-Flash-Next can provide a substantially higher capability ceiling while remaining usable on the 16 GiB actively cooled M3 MacBook Air through bounded expert caching and SSD streaming.
- **Runtime identity:** NVMAI is now TinyTitan. Repository `https://github.com/Pummelchen/TinyTitan`, pinned commit `008510e2753cc16a674cb75169ba3133cf56fa4e`, isolated under `results/raw/EXP-006/source/tinytitan/`.
- **Host gate:** macOS 27.0 build 26A428, Mac15,13/M3/8 cores/16 GiB, Swift 6.4 arm64, Command Line Tools; repository macOS 26+/Swift 6.4+ requirements are satisfied.
- **Flash-Next support:** current TinyTitan explicitly implements `qwen38flash`, 48 layers, 512 experts/top-10 routing, Gated-DeltaNet plus QSA, hyper-connections, and the hashed n-gram/PLE table. The shipped 4-bit profile declares a 12 GiB expert-cache budget and no predictive prefetch.
- **Storage gate:** TinyTitan pins `RockTalk/Qwen3.8-Flash-Next-MLX-4bit` revision `478474da92599ad0cf9f8bd447e658b29cb8480a`; main install estimate is 174,228,562,488 bytes plus 4 GiB reserve. Settings reported 228.88 GB available, while raw APFS free space was ~40.8 GB because three local Time Machine snapshots were purgeable. `tmutil thinlocalsnapshots / 200000000000 4` reclaimed them through the supported macOS path, raising immediate free space to ~210–212 GiB. Artifact: `results/raw/EXP-006/storage-gate.json`.
- **Build:** `swift build -c release` passed (`build_exit=0`); TinyTitanRepack, TinyTitanCLI, TinyTitanServer, and TinyTitanBench are arm64. The benchmark binary traps on `--help` while initializing a Metal kernel; this is recorded as a non-model CLI defect and does not block the repacker/server path.
- **Current install:** main 4-bit native install complete; optional 1.47 GB MTP draft deferred. The repacker exited 0, reported the pinned source revision, and produced `manifest.json` plus `verified-install.json`. The verified tree contains 58 files / 173,970,097,278 logical bytes (~162.02 GiB); post-install internal free space is 50 GiB and swap is 0 MiB.
- **Raw artifacts:** `results/raw/EXP-006/phase1-freeze.json`, `storage-gate.json`, `runtime-inspection.md`, `launch-plan.md`, `build-source.log`, `binary-verification.log`, and `qwen38-install.log`.

## EXP-010 — Laguna S 2.1 long-context Hermes qualification

**Status:** complete on 2026-09-18; stopped at the required short populated-context safety gate. No 32K/64K/128K, prefix-reuse, Hermes, or coding phase ran.

- **Question:** whether Laguna S 2.1 can preserve known coding quality while reaching real 64K usable context, about 4+ tok/s warm decode, and safe operation on this 16 GiB M3.
- **Runtime survey:** TurboQuant-MLX was selected first because it has the exact supported `manjunathshiva/Laguna-S-2.1-tqTe-g64` representation, MLX/Metal expert streaming, a bounded expert cache, and compressed-KV controls. streamlx remains a research comparator, but its published Laguna evidence uses a separate ~34.7 GB artifact on a 32 GiB M4 Air; it was not downloaded because the tqTe acquisition left only 4.1 GiB immediately free.
- **Frozen short arm:** 4.0 GiB expert cache, native top-10 routing, default FP16 KV, no DFlash, loopback-only API, deterministic Hermes-shaped **6,159-token** prompt, 256-token cap, +512 MiB incremental-swap / 20%-free-memory guard.
- **Result:** safety-stopped at **13% system-wide free memory**. Swap increment was only +33.88 MiB (3,437.06 → 3,470.94 MiB), so this is precisely classified `stopped_for_memory_pressure`; it is not a swap failure. HTTP 200 was observed but the server was terminated during the request with no SSE completion event, so no generation, timing, throughput, quality, or tool-use pass is claimed.
- **Implication:** the mandatory 4K–8K actual-context gate failed. Do not run the requested long-context or Hermes phases. Treat the current TurboQuant/tqTe Laguna path as **not viable for primary local Hermes use on this 16 GiB machine**. Revisit only with a materially different runtime/representation that first proves a safe actual populated short-context arm.
- **Artifacts:** `results/raw/EXP-010-laguna-long-context/REPORT.md`, `runtime-survey.md`, model/runtime provenance, and guarded-arm telemetry.

## Lightweight experiment template

Copy this block into a dated section or experiment file before running:

```markdown
## EXP-XXX — <title>
- Status / date:
- Hypothesis or question (falsifiable, one sentence):
- Model and exact build/revision:
- Quantization / format:
- Runtime and exact version:
- Machine/environment:
- Code/config revision:
- Configuration (context, KV, sampling, prompts, tool schema, server flags):
- Baseline arm and comparison variable:
- Test procedure (cold/warm cache, repeats, task order, stopping rules):
- Measurements (TTFT/prefill, decode, total latency, memory, swap, quality, failures):
- Qualitative observations:
- Result (measured facts first):
- Confidence and limitations:
- Next implication if positive / negative:
- Raw artifacts and commands:
```

## Recording rules

- Preserve the exact prompt, system/tool schema, model revision, server command, runtime version, and git/config revision.
- Record cold and warm behavior separately when caching can matter.
- Keep raw machine-readable output where practical; summarize only after the raw result exists.
- A failed run records the failure mode and environment state.
- Do not use a local model for an experiment until the user has explicitly approved that run.

## EXP-016 — Small-active MoE feasibility tournament

**Status:** complete on 2026-09-19. Runtime feasibility only; coding and research-quality evaluations were not run. All three required primary candidates were processed in order, with FAST and DEEP preserved down throughout.

- **Question:** which next-generation small-active MoEs can run safely and usefully enough on the 16 GiB M3 MacBook Air to deserve later intelligence testing?
- **ERNIE:** source `baidu/ERNIE-4.5-21B-A3B-Thinking`, revision `4341bb42644d5422859509fa25d41544c57181f8`; community MLX 4-bit rapid-mlx projected a 17.2 GB working set on 16 GB and was stopped before inference. The acquired GGUF Q4_K_M fallback then failed with repeated Metal `Insufficient Memory` and no response.
- **Instella:** source revision `74d28c1a8425583d7805b58e2caa9c13d6b62929`; publisher `instella-moe` branch commit `7a3c74eb0b5e58bc8cc3949f416fbc2b3959774c`; Q4_K_M produced a short four-token standalone output but a longer arm reached 9% free memory and 9,438.19 MiB swap, so Q3 escalation was stopped.
- **North:** source `CohereLabs/North-Mini-Code-1.0`, revision `d11e61a842617a22dc328552fa5bb86231ee4f37`; 4-bit artifacts were gated out by practical size, then UD-Q3_K_M was tested with ExpertCache llama.cpp commit `7e1e28cae36d41fe7bbe9dae7c9625de6565c063`. Metal failed; CPU-only `--n-gpu-layers 0 --cpu-moe` completed standalone and server/API/tool smoke.
- **North measurements:** standalone ctx 256 measured 6.7 prompt / 11.2 generation tok/s for an 8-token arm. Persistent loopback server health was HTTP 200; first fixed chat was 19.572 s, warm repeat 1.102 s with 116/121 cached prompt tokens; server metrics showed 13.0999 prompt and 8.3201 predicted tok/s. A 2,740-token context needle was correct on warm retry but cold prefill took 179.798 s. Direct compact native terminal-tool loop passed and ended with `finish_reason=stop`; full rendered Hermes turn was intentionally not run.
- **Decision:** survivor set contains only North UD-Q3_K_M in experimental CPU-only mode. Do not promote it to production Hermes. The next intelligence test is a full realistic Hermes native-tool turn followed by the separately authorized quality batteries; neither is part of EXP-016.
- **Raw artifacts:** `results/raw/EXP-016-small-moe-feasibility/REPORT.md`, `comparison.json`, `storage-receipt.json`, candidate dossiers, acquisition receipts/hashes, resource gates, isolated source/build logs, runtime probe directories, server metrics, context retrieval, and direct tool-loop files.

## EXP-017 — ERNIE streamed-MoE expert-slot residency ladder

**Status:** complete on 2026-09-19 through the safety/headroom boundary. At fixed Q4_K_M, streamed-MoE runtime, 3,982-token populated prompt, 8,192 context, and `-ub 2`, 22/26/30 resident slots measured 6.1/6.9/8.0 prompt tok/s versus the existing 18-slot 5.0 baseline. All completed with 0 swapouts, but 30 slots reached only 20% minimum free memory; 34/38 were not eligible. Decision: **materially helps but insufficient**; deprioritize further low-level Q4 ERNIE optimization on this 16 GiB Mac. Raw report: `results/raw/EXP-017-ernie-streamed-gguf/EXPERT-SLOT-LADDER-REPORT.md`; comparison: `expert-slot-ladder-comparison.json`.

## EXP-021 — Nanbeige4.2-3B local Hermes qualification

**Status:** complete on 2026-09-20 through the runtime/promotion gate; decision **NANBEIGE REJECTED**. Coding and research A/B phases were correctly not run after the candidate failed the healthy-runtime gate.

- **Question:** can Nanbeige4.2-3B replace or materially complement the frozen Ornith-1.5-9B Q5 Hermes lane on the 16 GiB M3 MacBook Air?
- **Candidate/runtime freeze:** official `Nanbeige/Nanbeige4.2-3B` revision `b82e54bd609793562a75cbf9337970a93369eab5`; official Nanbeige llama.cpp fork branch `nanbeige42`, commit `c6640a1c0cf7b38df342b67021a3900b04d092e7`; isolated loopback port 8921. Q6_K and Q5_K_M GGUFs were tested, plus a bounded MLX OptiQ 4-bit smoke.
- **Direct results:** Q6 + Q8 K/V measured 171.0/147.7/117.4/72.5 prompt tok/s and 13.26/12.45/11.49/7.81 decode tok/s at actual ~1K/~4K/~8K/~16K prompts. Needle retrieval was correct at each completed rung; 16K took ~223 s and was not interactive.
- **Context gate:** 64K Q8-KV was allocatable but the Q6 32K arm reached 10% free memory and the Q5 arm reached 13% while still running; both were safety-stopped. FP16-KV 64K was unsafe during load (~10.7 GB RSS and ~1.1 GB swap growth observed). No healthy completed 32K+ envelope was established.
- **Hermes gate:** direct OpenAI tool parsing passed; isolated native Hermes read → transform → write → reread completed with 7 tool calls and verified output, but took 229.48 s versus the frozen Ornith Q5 cold ~11K tool turn ~86.7 s. The reasoning-enabled smoke hit the 256-token cap without final content; scored arms used reasoning off.
- **Decision:** reject Nanbeige as primary and FAST complement. Its modest short-input decode edge did not become an end-to-end time or context-health advantage. Keep Ornith Q5 primary and preserve the candidate only as an isolated reproducible experiment.
- **Report/evidence:** `results/raw/EXP-021-nanbeige42/REPORT.md`, `summary.json`, pinned source/build, verified model hashes, raw context probes, MLX smoke, and Hermes transcript/resource logs.

## EXP-020 — TensorSharp runtime + Gemma-4-E4B Q6_K DEEP-lane promotion

**Status:** complete and **promoted** on 2026-09-21. Gemma-4-E4B Q6_K + MTP draft on TensorSharp v2026.09.01 (ggml_metal) is the current DEEP lane; Ornith Q6 GGUF is retained as instant rollback.

- **Question:** can the TensorSharp runtime serving Gemma-4-E4B Q6_K with its MTP draft replace the Ornith GGUF DEEP lane within the 16 GB envelope?
- **Direct results:** 11.1 tok/s decode small-prompt; ~184 tok/s prefill through 15,036 tokens; load 30.6 s cold / 9.9 s warm. Native tool-call loop and JSON mode PASS. Radix prefix cache reused 89–91% of the Hermes prefix on append-only turns.
- **Speculative decoding:** MTP draft (per-token, maxDraft 7) at 59–64% acceptance; short outputs ≈ break-even, populated turns nearly halve effective ms/tok (plain 200.5 → spec 108.1).
- **Memory:** 64K KV via `MAX_CONTEXT=65536` env (KV reservation ~1.07 GB); a 15K prefill pushed the host to ~10% free with +1.7 GB swap on a quiet machine — populated deep work is the binding constraint. Restart writes a 22.8 MB prefix-cache checkpoint, but restart restore is not applied (first big prompt after restart is a cold prefill).
- **Rollout:** profile `local-gemma4`, provider `local-deep` @ 127.0.0.1:8919, exact served id `gemma-4-E4B-it-Q6_K` everywhere; lane manager wired (`start deep`); research runner deep/super tiers default to the DEEP lane; alias/help/doctor tooling refreshed across all profiles.
- **Report/evidence:** `results/raw/EXP-020-tensorsharp-gemma4-e4b/PROGRESS.md`, `bench/`, `logs/`, `gen-test*.json`, `release.json` (runtime + models dirs are local-only).

## EXP-024 — Mference / Qwen3.6 Hermes integration qualification

**Status:** designed 2026-09-21; **not yet run** (awaits explicit approval). Bounded paired qualification of the Mference runtime versus the retained Slipstream configuration at an 8K context, same `qwen36.gturbo` artifact, loopback-only, documented flags only (`--model --port --max-context --queue-limit --prompt-cache-mode`). Full spec: `results/raw/EXP-024-mference-hermes-integration/TEST_SUITE.md`.

## EXP-026 — Nemotron 3.5 Lightning 30B-A3B, resident Branch 1

**Status:** complete 2026-09-21; **rejected at the first direct-load safety gate.** The verified `vcruz305` 2.47-bpw mixed Q2/Q4 GGUF is 9,759,494,016 bytes / 9.09 GiB and SHA-256 `5128d93446d9bf416a1d22eb466caea193a2c6537c96a841398959b45aaa280a`. Isolated llama.cpp `9655061`, full Metal offload, 8K context reservation, Q8 K/V, flash attention, one sequence, batch 128 / ubatch 32, no mlock, vision, or draft: it made the host reach 13% free memory before populated prefill. The independent guard stopped it at the hard 15% floor. A small raw-completion smoke was finite (52.64 prompt / 33.57 decode tok/s) but not a chat-template/quality pass; no 8K populated retrieval, 16–128K test, native tool call, or Hermes claim exists. Resident weights/Metal allocation—not long KV—is the measured blocker; Q8 KV lower bound is 384 MiB even at 128K. Installed TensorSharp ggml_metal parses the `nemotron_h_moe` metadata but refuses this mixed file before weight allocation (`Unknown GGML tensor type: 42`), so it cannot be evaluated as the alternate runtime until its GGML reader supports that type. Do not move into SSD streaming; that is a separately scoped branch. Evidence: `results/raw/EXP-026-nemotron35-lightning-resident/REPORT.md`.

## EXP-025 — Nemotron-3-Nano-30B-A3B Gate 0

**Status:** complete 2026-09-21. **Decision: not a candidate on this 16 GiB Mac.** Smallest credible production 4-bit releases (MLX community 4-bit 17.8 GB weights / 18.4 GB measured peak; Unsloth Q4_K_M 24.6 GB; even Q2_K GGUF 16.85 GiB) exceed physical unified memory before runtime workspaces. No weights downloaded, no server started. Its hybrid Mamba KV lower bound is unusually small (0.75 GiB @128K FP16), so context is not the blocker — weight residency is. Honest qualification needs ≥24 GB (constrained 64K) / 32 GB+ (stable 64–128K loop). Report: `results/raw/EXP-025-nemotron3nano-gate0/REPORT.md`.

### EXP-015 arm — oMLX 8K admission check (Nemotron 3 Nano)

**Status:** complete 2026-09-21; `invalid_configuration` before model allocation. In an isolated oMLX 0.7.0.dev4 / MLX 0.32.2 environment, the pinned `mlx-community/NVIDIA-Nemotron-3-Nano-30B-A3B-4bit` checkpoint (17.38 GB) was submitted one 8,099-token request with 32-token output cap, expert offload enabled, 12-GB memory guard, and an 8-GB paged-SSD-cache limit. The server returned HTTP 507 in 0.01 s because the 17.38-GB checkpoint exceeded the 11.84-GB current Metal cap. Swap used, pageouts, and swapouts were unchanged; there was no weight load, prefill, decode, or Hermes rebinding. The focused expert-offload test suite passed 46 tests, but it does not change this admission result. Decision: do not claim oMLX expert streaming as a viable Nemotron path on this 16-GB Mac; any raised Metal-cap probe requires separate explicit approval. Reviewed evidence: `results/raw/EXP-015-github-runtime-dive/ARM-8K-RESULT.md` and `VERIFIED-REASSESSMENT.md`.

