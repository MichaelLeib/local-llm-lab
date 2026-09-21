# Current state

Updated: 2026-09-20

## Latest experiment

**EXP-022 Ornith MLX-4bit vs GGUF-Q6_K quality A/B is complete: MLX4 is rejected as a ≤5 percentage-point quality-loss replacement for Q6.** On the deterministic 16-item exact-answer gate, Q6 scored 14/16 (87.50%) and MLX4 scored 11/16 (68.75%), a -18.75-point MLX4 regression. MLX4 did complete a real Hermes read → reverse/write → reread file workflow in 107 s with a verified artifact; its speed-first lane status is unchanged, but it is not a no-quality-loss substitute. The Q6 fresh native rerun was resource-inconclusive and stopped safely; EXP-019's existing Q6 native-tool evidence remains the reference. On 2026-09-20 Q6_K + Q8_0 KV at a 64K endpoint was promoted to the FAST server (`hermes-fast`, port 8901) and made the default for Matrix's default/routed profiles and fresh myChatty sessions. A gateway default-model smoke and an explicit myChatty `local-fast`/`hermes-fast` run both returned their exact expected values. Full report: `results/raw/EXP-022-ornith-quality-ab/REPORT.md`; structured summary: `results/raw/EXP-022-ornith-quality-ab/summary.json`.

**EXP-021 Nanbeige4.2-3B is complete and rejected for Hermes use.** The official Nanbeige llama.cpp fork loaded verified Q6/Q5 GGUFs; Q6 + Q8 K/V reached 13.26 tok/s short decode and correct retrieval through 16K, but 32K populated tests were safety-stopped at 10–16% free memory and 64K FP16 KV was unsafe. Native Hermes tools completed a verified read/transform/write/reread task, but it took 229.48 s versus frozen Ornith Q5's ~86.7 s cold comparable turn. No coding/research A/B was run after the runtime gate failed. Full report: `results/raw/EXP-021-nanbeige42/REPORT.md`; structured summary: `results/raw/EXP-021-nanbeige42/summary.json`. Keep Ornith primary; retain `~/.hermes/bin/local-nanbeige` stopped and isolated only.

## Phase

**EXP-001 through EXP-005 retain their recorded status. EXP-006 TinyTitan/Qwen3.8-Flash-Next is complete and rejected for interactive-default use after standalone/API/Hermes and bounded cache work. EXP-009 separately rebuilt current TinyTitan and was safety-stopped for unsafe swap during real multi-thousand-token prefill before decode. EXP-010 Laguna S 2.1/TurboQuant completed the required populated short-context gate and was stopped for memory pressure (13% free) before any emitted generation; no 32K/64K/128K or Hermes qualification proceeded. EXP-011 Qwen3-Coder-Next/Swiftlet passed the static architecture audit, direct-streamed the exact 4-bit Coder checkpoint to a verified QPACK, and passed a tiny smoke request. Its two guarded intended-~5K Hermes-shaped arms both exceeded the +256 MiB incremental-swap budget before a completion: +315.75 MiB at 2 GiB cache and +375.94 MiB at 1 GiB cache. It is rejected at the first populated-context safety gate. EXP-004 remains paused at its GPT-OSS disk gate; EXP-005 remains a separate frozen Qwen3.6/Slipstream track.**

## Working direction

EXP-006 is concluded as a bounded negative result for interactive-default use. TinyTitan is isolated at `results/raw/EXP-006/source/tinytitan/`; its release build, verified native Qwen3.8-Flash-Next 4-bit install, standalone probes, loopback API/tool-call checks, isolated Hermes attempt, and optimization sprint are complete. The clean traced 24-slot arm reached 2.839 tok/s but caused 1,493.12 MiB swap; a 16-slot aging-LFU I/O-reduction arm reached 2.442 tok/s with unchanged cache behavior. EXP-009 separately rebuilt current TinyTitan commit `9c03db58d86e7ac35917ee3f05cf58fbab97f666` without changing EXP-006, then safety-stopped a real ~7K-shaped prefill at 16 slots before decode: incremental swap peaked at 2,801.50 MiB and process physical-footprint peak was 8.06 GiB. EXP-010 selected isolated TurboQuant-MLX and the exact tqTe Laguna checkpoint, but stopped the first 6,159-token actual populated-context arm when system memory free reached 13%; the swap increment was +33.88 MiB, so no speed/quality or generation metric is claimed. Neither experiment qualifies for 32K/64K/128K, prefix reuse, or Hermes. No promotion is allowed. EXP-005 remains frozen and unchanged; no default Hermes profile setting was changed.

## Next steps

1. FAST's deliberate default is Ornith Q6_K + Q8_0 KV on port 8901. Do not start a second local model while it is resident; the lane manager may auto-heal FAST under its existing policy.
2. Preserve EXP-003 and EXP-004 evidence and source artifacts; the unprobed EXP-004 Gemma payload was removed under the authorized storage cleanup with its acquisition provenance and hash retained. Do not resume Gemma unless explicitly requested.
3. Keep EXP-004 GPT-OSS paused until at least the documented 80 GB free internal-disk gate is met and the user explicitly approves the checkpoint download.
4. For EXP-005, keep the native Qwen install and runtime isolated; do not convert or reuse Ornith/Gemma files.
5. Keep the native Qwen install and runtime isolated; do not convert or reuse Ornith/Gemma files.
6. Keep Slipstream loopback-only and run one local model process at a time; stop the temporary server after measurements.
7. Do not promote Slipstream/Qwen to Hermes defaults or FAST/DEEP until native tool use, practical wall-clock latency, memory safety, and coding/research quality pass.
8. Repeat the disk-KV warm-decode result and run controlled quality/sustained-thermal tests before any promotion.
9. Do not promote EXP-006: current evidence shows severe latency/swap pressure and Hermes timeout. Any follow-up must target a smaller resident-memory configuration or runtime fix before repeating Hermes.
10. Do not advance EXP-009 to 32K, 64K, 128K, or Hermes: its current-runtime 16-slot real multi-thousand-token prefill was stopped for unsafe incremental swap before first generated token. Any reopen must first isolate and validate a source-level long-prefill memory fix under a hard swap guard.
11. Do not advance EXP-010 Laguna beyond its first short populated-context arm: with the tqTe TurboQuant path it reached the independent memory-pressure guard at 13% free before an emitted completion. Any reopen must use a materially different runtime/representation and again pass a real 4K–8K short-context guard first. The original 4.1 GiB post-download free-space observation is historical; any new representation needs a fresh storage gate.
12. A subsequent macOS watchdog panic during an associated agent-launched Python workload recorded 904 free pages, a compressor at 100% segment limit, and a 56.26 GB-recorded Python task. The panic lacks the command line, but it reinforces EXP-010 as a host-safety rejection. Do not rerun current TurboQuant/tqTe Laguna on this Mac; only a non-inference source-level bounded-working-set audit is eligible without new explicit approval.
13. EXP-011's verified QPACK is installed, but both its 2 GiB and 1 GiB cache populated-context arms exceeded the hard +256 MiB incremental-swap guard before completion. Do not advance the current Swiftlet path to long context, tool bridging, or Hermes promotion. Any reopening needs a material source/runtime prefill-memory change and a fresh exact-token-count safety gate; do not download a duplicate raw checkpoint or delete Qwen Flash/Qwen3.8 or protected baselines.
14. EXP-013 correction established a 2.482 GiB wired core after PLE plus expert offload, and the user-authorized direct text-model acquisition completed. Its actual 1 GB-cache, native-top-10 Stage 1 smoke was memory-safe and coherent but only 1.475 tok/s generation (1.0 tok/s end-to-end), 23.6% cache hit rate, and 21.6 GB critical expert reads. This is below the <3.5 tok/s hard stop; do not advance to Stage 2, quality A/B, long context, or custom-runtime work. Preserve the 55.84 GB text model and raw evidence.

## Blockers / unknowns

- EXP-003 has no token-for-token reference comparison yet; current evidence is coherent repeated text generation with no runtime errors.
- The fork builds and includes Qwen35MOE support, but the disk-streaming path has only been demonstrated publicly on Qwen3-30B-A3B.
- The source-level 8-slot/ubatch relationship is clear; exact expert-cache locality and a clean system-wide GPU delta remain unknown.
- The official MLX-4bit checkpoint is cached at `results/raw/EXP-003/mlx-option2/`; serving reached the API but failed at first-load with `UnsupportedModelTypeError` for `qwen3_5_moe`.

## Recent discoveries

- Chosen PoC: `kisasexypantera94/llama.cpp`, branch `moe-expert-residency`, head `41ec4c4e94fd5ff6c258691f35f2fcd0d3dde892`, PR base `fda8528aa8c1d8ecb2a5cd2b6e85c43ef5425b6b`.
- Isolated Metal build succeeded with AppleClang 21/macOS 27 after installing only CMake 4.4.3; `llama-server` exposes `--moe-n-slots` and `--moe-n-layers`.
- Official GGUF header verifies `qwen35moe`, 41 blocks, 256 experts, 8 experts/token, 512 expert intermediate and 123 expert tensors using mixed Q4_K/Q6_K routed weights.
- Official target revision `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`; Q4_K_M is 21,713,463,040 bytes with SHA-256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`. Q5/Q6 and mmproj remain excluded.
- Before downloading, EXP-002-only 6-bit and 8-bit caches were removed, preserving their raw results; HF reported 16.8 GB freed. FAST 4-bit, DEEP Bonsai, OptiQ, GPT-OSS, Qwen candidates and GGUF fallback were retained.
- Local SSD baseline: 2.322 GiB/s sequential with `F_NOCACHE`; 0.028 ms average for deterministic random 4 KiB reads. Raw artifact: `results/raw/EXP-003/ssd-baseline.json`.
- Exact conservative expert-pool estimates: 8 slots 596.8 MiB, 16 slots 1.17 GiB, 24 slots 1.75 GiB, 32 slots 2.33 GiB.
- Hermes bridge verification passed native `terminal(date)` execution through streamed llama.cpp responses; full 3,332-token prompt latency was 773.51 seconds at approximately 4.31 prompt tok/s. Artifact: `results/raw/EXP-003/bridge-fix/summary.json`.
- EXP-004 ExpertCache checkout `e6a3b940a8cd8465be0cd8cdf0f39829ebfa6ade` and pinned llama.cpp revision `7e1e28cae36d41fe7bbe9dae7c9625de6565c063` are preserved in an isolated source tree; patch applied cleanly. Official GPT-OSS-120B metadata is verified, but its download remains gated by the documented 80 GB free-disk requirement. The unprobed Gemma 4 MXFP4 payload was deleted in the authorized storage cleanup; acquisition metadata and its SHA-256 provenance remain.
- EXP-005 Slipstream is pinned at `dwijenpatel/slipstream` commit `3a892465729406944778a24064664d817617f558`; runtime products `slipstream-repack`, `slipstream`, and `slipstream-server` build under Swift 6.4/macOS 27 CLT. Native Qwen target is pinned to `mlx-community/Qwen3.6-35B-A3B-4bit` revision `38740b847e4cb78f352aba30aa41c76e08e6eb46`; the verified `.gturbo` artifact is installed at `results/raw/EXP-005/model/qwen36.gturbo/`.
- EXP-005 first standalone probe passed at 16 expert slots: exact `READY.` output, exit code 0, 8.325 tok/s decode, 8.81 s cold 5-token prefill, 1,445 MB peak sampled footprint, and no swap growth. Baseline swap was already 2,310.38 MiB, so longer measurements remain guarded.
- EXP-006 resolves NVMAI's current name as TinyTitan at commit `008510e2753cc16a674cb75169ba3133cf56fa4e`; the pinned Flash-Next main install is approximately 174.23 GB plus a 4 GiB reserve. The internal volume initially exposed only ~40.8 GB raw free because three local Time Machine snapshots were purgeable; supported `tmutil thinlocalsnapshots / 200000000000 4` reclaimed them and raised raw free space above 210 GiB. The isolated TinyTitan release build passed with arm64 products. The model install remains active and no local model is resident.
- EXP-006 approved inference: chat-template correctness passed, but default caching produced 0.036 tok/s and 5.4 GiB swap; 16 expert slots improved the short decode to 2.629 tok/s without additional swap growth but still took 14.79 s to prefill 238 tokens. Loopback API and native tool-call formatting passed; isolated Hermes timed out after 420 s even with a 65,536-token server ceiling. The TinyTitan server was stopped; no model process remains resident.

## Raw EXP-003 artifacts

- `results/raw/EXP-003/compatibility-gate.md`
- `results/raw/EXP-003/source-provenance.json`
- `results/raw/EXP-003/cache-cleanup.json`
- `results/raw/EXP-003/download-verification.json`
- `results/raw/EXP-003/gguf-header.json`
- `results/raw/EXP-003/memory-model-estimate.json`
- `results/raw/EXP-003/ssd-baseline.json`
- `results/raw/EXP-003/first-load-8slot-configuration-failure.json`
- `results/raw/EXP-003/first-load-8slot-server.log`
- `results/raw/EXP-003/first-load-8slot-server-retry.log`
- `results/raw/EXP-003/first-load-8slot-idle.json`
- `results/raw/EXP-003/first-load-8slot-no-thinking-request.json`
- `results/raw/EXP-003/first-load-8slot-no-thinking-metrics.jsonl`
- `results/raw/EXP-003/first-load-8slot-repeat-128-request.json`
- `results/raw/EXP-003/first-load-8slot-repeat-128-metrics.jsonl`
- `results/raw/EXP-003/first-load-8slot-post-stop.json`
- `results/raw/EXP-003/first-load-8slot-summary.json`
- `results/raw/EXP-003/first-load-8slot-subjective.json`
- `results/raw/EXP-003/no-model-gpu-baseline.json`
- `results/raw/EXP-003/16slot-idle.json`
- `results/raw/EXP-003/16slot-request.json`
- `results/raw/EXP-003/16slot-metrics.jsonl`
- `results/raw/EXP-003/16slot-summary.json`
- `results/raw/EXP-003/deterministic-compare/`
- `results/raw/EXP-003/hermes-tool-call-prompt.txt`
- `results/raw/EXP-003/hermes-tool-call-summary.json`
- `results/raw/EXP-003/hermes-8slot-server.log`
- `results/raw/EXP-003/hermes-8slot-server-retry.log`
- `results/raw/EXP-003/hermes-8slot-server-chatcompletions.log`
- `results/raw/EXP-003/mlx-option2/summary.json`
- `results/raw/EXP-003/mlx-option2/server.log`
- `results/raw/EXP-003/mlx-option2/request-response.json`
- `results/raw/EXP-003/mlx-option2/request-metrics.txt`
- `results/raw/EXP-003/bridge-fix/summary.json`
- `tools/exp003_capture_proxy.py`
- `results/raw/EXP-003/source/llama.cpp-moe-expert-residency/`
