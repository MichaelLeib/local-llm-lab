# Decisions

Durable decisions belong here. Each entry includes the reason and a condition that would justify revisiting it.

## D-001 — Documentation before experimentation (2026-09-17)

Create a small canonical record before installing, downloading, swapping, or launching expensive experiments. Reason: comparisons are otherwise hard to reproduce and failures become indistinguishable from environment drift. Revisit only if the documentation itself is blocking a clearly bounded measurement.

## D-002 — Single-resident-model rule on the primary Mac (2026-09-17)

Never intentionally keep two local models resident on the 16 GB unified-memory machine. Reason: the machine must remain usable for normal work and double residency can turn a benchmark into swap-thrash. Revisit only for a separately approved machine or a measured streaming design that proves its residency behavior.

## D-003 — End-to-end Hermes tool use is a promotion gate (2026-09-17)

A model must produce genuine native tool calls through the real Hermes executor at realistic prompt scale. Text that merely resembles a command or tool result does not pass. Reason: agent usefulness is the target and large rendered prompts can expose failures hidden by toy probes.

## D-004 — Separate inherited evidence from reproduced results (2026-09-17)

Existing profile measurements may seed hypotheses, but are not treated as newly verified lab results until exact builds, conditions, and artifacts are recovered or re-run. Reason: provenance and comparison validity matter more than convenient numbers.

## D-005 — MoE offloading/streaming is a hypothesis, not the architecture (2026-09-17)

Investigate expert offloading/streaming as an early direction because it may improve capability per active-RAM budget, but compare it against dense, quantized, cache, and scaffold alternatives. Reason: the project must not be locked to an attractive mechanism before measuring latency, stability, and quality.

## D-006 — Keep QwenLoop separate (2026-09-17)

QwenLoop remains its own project with its own experiment IDs and mechanism-specific conclusions. This lab may cite its evidence but will not silently merge its results. Reason: separation keeps scope and baselines legible.

## D-007 — Initialization makes no system or model changes (2026-09-17)

The documentation phase creates no model or system changes. Resource-affecting actions require explicit user instruction and must remain reversible.

## D-008 — Synthetic anonymous pressure is not an LLM budget (2026-09-17)

Do not promote the 11 GiB synthetic result as a safe model-RAM budget. Reason: macOS made most anonymous pages swapped/unresident while the user reported no degradation, yet a prior real Ornith MLX run with a reported 7–8 GiB footprint made the Mac very slow. Revisit only with a model-specific Metal/MLX test under the same subjective protocol.

## D-009 — Treat official 8-bit as a stability failure under the current lane (2026-09-17)

Do not promote or blindly retry the official Ornith 8-bit MLX model under the current rapid-mlx 0.14.1 / 16 GB configuration. Reason: rapid-mlx projected a 13.3 GB short-chat working set, warned of 142% utilization and possible kernel-panic risk, and the server received SIGTERM before a stable idle checkpoint. Revisit only with a separately justified diagnostic plan that identifies the SIGTERM source and protects the Mac; this decision does not claim a confirmed OOM or kernel cause.

## D-010 — EXP-003 uses an isolated Metal PoC pending a single-model gate (2026-09-17)

Use `kisasexypantera94/llama.cpp` branch `moe-expert-residency` only in the isolated EXP-003 source tree; do not replace or modify the system/Homebrew llama.cpp. Reason: the fork is the only reviewed implementation found with Metal SSD expert-slot paging, while upstream 0.4.1 exposes CPU MoE offload but not this feature. The fork builds and contains Qwen35MOE support, but the original public demonstration used Qwen3-30B-A3B, so first-load correctness remains mandatory. Revisit if GGUF tensor metadata or runtime output proves incompatible.

## D-011 — One large EXP-003 download, Q4_K_M only (2026-09-17)

Do not download Q5/Q6 or the projector for EXP-003. Request explicit approval before downloading the single 21.713 GB official Q4_K_M GGUF. Reason: the experiment is a feasibility gate on a 16 GB Mac, disk space is finite, and one quantization is sufficient to test the SSD-streaming mechanism. Revisit only after Q4 correctness and memory/speed results justify another quantization.

## D-012 — 8-slot Ornith-35B streaming is feasible but not yet promoted (2026-09-17)

The isolated fork also passed a controlled 16-slot comparison, but decode was only 4.43 tok/s versus 4.32 tok/s for the comparable 8-slot repeat, while active process footprint increased from 3.863 GB to 4.204 GB. The user rated normal-workload impact the same as 8 slots: primary 0/5, with a possible brief 1/5 that may be unrelated. Do not automatically test 24/32 slots; revisit only if cache-locality or reference-equivalence evidence identifies a specific reason.

## D-013 — Stop automatic EXP-003 slot scaling at 16 (2026-09-17)

Treat 8 and 16 slots as the current EXP-003 feasibility checkpoints. Both were coherent, stable, and subjectively 0/5 primary impact, but 16 slots did not provide a meaningful measured speed improvement and added active footprint. Revisit 24/32 slots only under an explicit, instrumented hypothesis; do not run a blind sweep on the 16 GB Mac.

## D-014 — MLX option 2 is blocked by an architecture adapter gap (2026-09-17)

Do not use Rapid-MLX's `--disk-stream` path for the official Ornith-1.5-35B-A3B MLX checkpoint until a `qwen3_5_moe` streaming adapter exists and is independently exercised. The exact 4-bit checkpoint downloaded successfully and the server API started, but first inference failed before generation because Rapid-MLX 0.14.1 lacks that registry entry; the checked 0.14.2 source has the same omission. Do not attempt resident loading on this 16 GiB Mac: the runtime estimated a 27.3 GB short-chat working set and warned of possible kernel-panic risk.

## D-015 — Bridge protocol is fixed; 35B interactive latency is not (2026-09-17)

Use a reversible SSE bridge that injects `chat_template_kwargs.enable_thinking=false` for every Hermes chat-completion request and forwards close-delimited streams without a false zero-length header. The bridge passed a genuine Hermes native `terminal(date)` execution with exit 0. Do not promote the 35B lane for interactive Hermes use yet: the full 3,332-token prompt took 773.51 seconds at approximately 4.31 prompt tok/s, and the controlled verification used a terminal-only tool allowlist plus a 256-token cap. Revisit after reducing Hermes prompt/tool overhead or improving expert-streaming prefill.

## D-016 — EXP-004 requires a storage gate before GPT-OSS download (2026-09-17)

Keep EXP-004's ExpertCache source and pinned runtime isolated from EXP-003, and do not download `gpt-oss-120b-MXFP4.gguf` until internal free space is at least the documented 80 GB minimum and the user explicitly approves the approximately 63.4 GB download. Reason: the exact model is 59.0 GiB before temporary download/build headroom, while the current internal volume has only 20 GiB free; starting anyway would risk exhausting the development disk and invalidate the experiment. Revisit after cleanup or additional internal capacity is available.

## D-017 — Gemma 4 uses the MXFP4 ExpertCache arm and requires a clean swap baseline (2026-09-17)

Test `unsloth/gemma-4-26B-A4B-it-MXFP4_MOE.gguf` rather than the official Q4_0 file when the hypothesis is the same ExpertCache page-aware path, because the patched Metal staging candidate is specifically MXFP4. Do not launch the first-load probe while swap exceeds 2 GiB; the Gemma file is acquired and the runtime is built, but the current 2.38 GiB swap baseline would confound the protected 16 GiB safety result. Revisit after a reboot or equivalent clean baseline.

## D-018 — EXP-005 uses isolated Slipstream native Qwen path (2026-09-17)

Use `dwijenpatel/slipstream` commit `3a892465729406944778a24064664d817617f558` only under `results/raw/EXP-005/source/`, with the pinned native `mlx-community/Qwen3.6-35B-A3B-4bit` source revision `38740b847e4cb78f352aba30aa41c76e08e6eb46`. Do not convert or reuse the existing Ornith/Gemma artifacts, and do not alter system llama.cpp, MLX, Hermes defaults, FAST, or DEEP. Reason: Slipstream's repacker and Qwen runtime contract are architecture-specific, while the experiment's value depends on measuring its own page-aligned expert layout and prefix-cache behavior. Revisit only after native standalone correctness, memory, latency, and Hermes tool-use measurements.

## D-020 — First EXP-005 probe is correctness-only; later sweep is measured separately (2026-09-17)

Treat the first Slipstream/Qwen run as a standalone feasibility and correctness result, not a clean memory result. It produced exact `READY.` at 8.325 tok/s decode and 1,445 MB peak sampled process footprint with no swap growth, but started with 2,310.38 MiB swap already used and system-wide free memory fell from 58% to 51%. The later 16-slot prefill/decode sweep passed all arms and provides warm OS-cache speed measurements, but does not retroactively make the first probe a clean baseline.

## D-022 — EXP-006 uses supported APFS snapshot thinning before the native install (2026-09-17)

Treat macOS Storage Settings' reported 228.88 GB available as reclaimable capacity only after verifying the raw APFS free-space guard. TinyTitan correctly refused the first install attempt because only ~39.17 GB was immediately unallocated while three local Time Machine snapshots held purgeable space. Use Apple's supported `tmutil thinlocalsnapshots / 200000000000 4` request rather than bypassing TinyTitan's disk check or manually deleting snapshot files. Revisit if the resulting headroom falls below the 4 GiB runtime reserve plus a substantial normal-use margin.

## D-023 — EXP-006 is not promoted after the approved operational probe (2026-09-17)

Do not promote Qwen3.8-Flash-Next/TinyTitan on this 16 GiB M3 based on the current run. The model format, loopback API, and function-tool envelope work, but the best controlled 16-slot result was only 2.629 tok/s with 14.79 s prefill for 238 tokens, swap pressure remained substantial, and an isolated Hermes turn exceeded the 420-second execution limit. Treat this as an operational-feasibility failure pending a smaller-memory/runtime optimization experiment; preserve all raw runs unchanged.

## D-024 — Stop EXP-006 Flash-Next interactive-default optimization (2026-09-17)

After a clean 16-slot traced control, a 24-slot numerics-preserving cache expansion, and one evidence-supported 16-slot aging-LFU I/O-reduction attempt, stop optimization of Qwen3.8-Flash-Next/TinyTitan as an interactive Hermes default on this 16 GiB M3. The 24-slot configuration reduced expert traffic 32.1% but reached only 2.839 tok/s and created 1,493.12 MiB swap; aging-LFU did not reduce misses or bytes/token and reached 2.442 tok/s. Reason: the bounded sprint did not approach the >=4 tok/s usability gate, and further tuning would violate the stopping rule. Preserve EXP-006 and return the default-interactive direction to Qwen3.6 + Slipstream. Revisit only with materially different hardware, a runtime architecture change, or an explicitly scoped research project.

## D-025 — Stop current-runtime Flash-Next long-context qualification before 32K (2026-09-18)

EXP-009 tested the materially newer TinyTitan commit `9c03db58d86e7ac35917ee3f05cf58fbab97f666` in an isolated source tree, reusing the verified Qwen3.8-Flash-Next native 4-bit install without changing EXP-006 or Hermes defaults. A real approximately-7K-shaped prompt at only 16 expert slots and an 8,192-token ceiling was safety-stopped during prefill, before decode: incremental swap reached 2,801.50 MiB and process physical-footprint peak was 8.06 GiB, with memory-pressure free 21–26%. Do not proceed to 32K, 64K, 128K, prefix reuse, or Hermes; no throughput result is claimed. Revisit only with a separately isolated and measured source-level long-prefill memory fix that passes a real 4K–8K hard-swap gate first.

## D-021 — Full Xcode is not required for EXP-005 runtime evaluation (2026-09-17)

Do not install full Xcode solely for Slipstream/Qwen inference, loopback API serving, or Hermes integration: all three runtime products build and run with the installed Command Line Tools. Install Xcode only if the optional SwiftUI Mac app or a complete Swift package/test-plugin environment is specifically needed; `SwiftUIMacros` remains unavailable under CLT-only tooling while the runtime path is unaffected.

## D-026 — Stop the current Laguna TurboQuant path before prefix/long-context work (2026-09-18)

Do not advance `manjunathshiva/Laguna-S-2.1-tqTe-g64` through the isolated TurboQuant-MLX path to cache sweeps, prefix reuse, 32K, 64K, 128K, Hermes, coding, or DFlash on this 16 GiB M3. The first real 6,159-token Hermes-shaped arm used a conservative 4.0 GiB expert-cache budget, native top-10 routing, default FP16 KV, and DFlash off; it was stopped by the independent memory-pressure guard at 13% system-wide free memory before any emitted completion. Swap increment was +33.88 MiB, so the result is `stopped_for_memory_pressure`, not a fabricated decode failure. Reason: the task’s operational prerequisite is a safe actual 4K–8K context before any longer context, and the current configuration failed that prerequisite. Revisit only with a materially different, separately justified representation/runtime that passes the same populated short-context gate; the original 4.1 GiB immediate-free observation was a historical storage gate, and any new comparator needs a fresh gate.

### D-026 addendum — watchdog panic makes this a host-safety rejection (2026-09-19)

Do not use a user-space polling guard as justification to rerun the current Laguna TurboQuant/tqTe arm. The associated post-restart kernel panic was a 92-second watchdog timeout with a compressor at 100% segment limit, 44 swapfiles, only 904 free pages, and a 56.26 GB-recorded agent-descended Python task. The panic report lacks command-line data, so it does not prove the exact model process; it does prove that this allocation regime can outpace or wedge the supervisor. Revisit only after non-inference source-level accounting identifies a bounded memory mechanism, followed by a separately approved micro-probe with external monitoring.

## D-027 — Stop Flash-Next `tq4a-tq2e-g64` before acquisition on the 16 GiB M3 (2026-09-18)

Do not download or launch `manjunathshiva/Qwen3.8-Flash-Next-tq4a-tq2e-g64` on this machine. The pinned 52.860 GiB model tree would leave 4.513 GiB immediate free even with a direct single-copy transfer, below a 10 GiB operational reserve. More fundamentally, the pinned TurboQuant-MLX `load_streaming()` path keeps the non-expert model remainder resident; the model card/planner reports 21.86 GB after `--ngram-offload`, already above 16 GiB before an expert cache, KV/state, or activations. `--ngram-offload` correctly keeps the PLE table memory-mapped/page-cache-backed and streaming correctly replaces routed expert projections, but neither reduces that dense resident floor. The 4 tok/s speed hypothesis cannot be measured safely with this representation; reopening needs a representation/runtime that materially lowers the non-expert resident footprint.

## D-028 — Supersede EXP-013's resident-backbone conclusion; retain the disk gate (2026-09-19)

D-027 correctly preserved the disk-safety stop but incorrectly treated `ngram_bytes` as disjoint from `resident_bytes`. Pinned TurboQuant `plan.py` defines `resident_bytes = total_bytes - expert_bytes`; its 19,200,092,160-byte n-gram/PLE table is therefore a subset of that 21,864,923,704-byte resident subtotal. With both expert streaming and `--ngram-offload`, the actual loader computes a 2,664,831,544-byte / 2.482 GiB wired core. The model is feasible on paper with a bounded expert cache; D-027's architecture-wall claim is superseded. The independent disk gate is now **passed** after the user-authorized removal of the 7.94 GiB DEEP Bonsai managed-lane payload: live immediate APFS free is 67.888 GiB. A direct 52.860 GiB full-tree candidate acquisition would leave 15.028 GiB (and the text-only planned tensor set would leave 15.884 GiB), above the 10 GiB reserve before transfer overhead. The original direct/resumable, single-copy acquisition and 1 GB-cache smoke gate are now authorized by the experiment plan; do not delete remaining protected controls.

## D-029 — Stop 2-bit Qwen3.8 Flash-Next TurboQuant after native smoke speed failure (2026-09-19)

The corrected EXP-013 accounting was memory-feasible and its 1 GB-cache smoke was functionally coherent and free of a severe swap event, but native top-10 decode measured 1.475 tok/s (1.0 tok/s end-to-end), with only 23.6% expert-cache hits and 21.6 GB critical expert reads for roughly 30 output tokens. This is below the explicit <3.5 tok/s stop threshold and far below the 4.0 tok/s requirement. Do not run a larger decode sweep, quality A/B, long-context arm, or custom Slotstream/TurboQuant hybrid for this checkpoint on the 16 GiB M3. Preserve the acquired text model and evidence; treat this as a valid negative measurement, not a memory-fit failure.

