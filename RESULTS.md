# Results

This file is a concise evidence ledger. New runs should include an experiment ID and point to raw artifacts. EXP-001's raw snapshots and subjective records are preserved under `results/raw/EXP-001/`; inherited model measurements remain labeled separately.

## Current lab status

- **EXP-001 is complete through the exploratory 11 GiB level.** Every subjective rating was 0/5; no pain threshold was reached with the synthetic allocator.
- Both local lanes and the synthetic allocator are down after cleanup. The FAST lane remains user-stopped.
- The key result is a methodological caveat: this anonymous-memory test cannot establish a safe real-LLM budget because it mostly produced swapped/unresident pages and did not reproduce the user's prior Ornith MLX slowdown.

## EXP-002 Phase 1 inventory and downloads — no model run yet

EXP-002 exists specifically because EXP-001 established that pageable anonymous memory is an inadequate proxy for an active MLX/Metal workload. EXP-001 raw measurements are unchanged.

- Current lanes: FAST and DEEP down; no local model is resident.
- Existing official reference: `ornith-ai/Ornith-1.5-9B-MLX-4bit`, revision `a48173b246ac705be75c05bedf1a0666db522d53`, 5.060 GB repository files / 4.712 GiB.
- Existing custom build: `mlx-community/Ornith-1.5-9B-OptiQ-4bit`, revision `15fa783d15b32f030b7bf2356940ba5cfb55c8ec`, 7.121 GB / 6.632 GiB; its runtime dependency is absent and it is not part of the primary ladder yet.
- The user approved the downloads. Official 6-bit (7.298 GB / 6.797 GiB) and 8-bit (9.536 GB / 8.881 GiB) snapshots were downloaded at the recorded revisions; local file totals exactly matched Hub metadata. Download artifact: `results/raw/EXP-002/downloads.json`.
- Combined new repository data is 15.678 GiB; root free space is now 58 GiB. Both local lanes and all model servers remain down after download.
- Primary proposed sequence: existing official 4-bit → official 6-bit → official 8-bit. Per-model testing will separate loaded-idle from active inference and will stop for subjective rating before advancing.
- Initial inventory artifact: `results/raw/EXP-002/inventory.json`; download artifact: `results/raw/EXP-002/downloads.json`.

### EXP-002 official 4-bit checkpoint — complete

Raw summary: `results/raw/EXP-002/official-4bit-summary.json`. The exact prompt, warm-up, pre/inference/post snapshots, `footprint` outputs, rapid-mlx metrics, timing, and subjective records are preserved alongside it.

| Model/build | Quant | Repository size | Idle OS footprint | Active peak OS footprint | rapid-mlx Metal active / peak | Swap used: idle → active → post | Pressure-free: idle / active / post | Prompt / decode | Idle rating | Active rating |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ornith-1.5-9B official MLX | 4-bit | 5.060 GB | 5,750 MB | 6,282 MB | 5.86 / 6.81 GB decimal | 3.44 → 3.78 → 3.72 GiB | 32% / 26% / 43% | 1,958 prompt / ~7.89 decode tok/s | 0/5 | 0/5 |

- Load duration was 17.75 seconds. The standardized request generated all 512 requested tokens successfully in 65.38 seconds, with a 0.50-second first streamed event.
- The model's ordinary RSS was only approximately 28 MiB, while `footprint` showed 5.75–6.28 GB and the `IOAccelerator` category accounted for 5.12–5.61 GB. RSS is therefore not a useful total-memory metric for this workload.
- rapid-mlx exposed `rapid_mlx_metal_active_memory_bytes` and `rapid_mlx_metal_peak_memory_bytes`; no separate MLX allocator counters were exposed through this server endpoint. The raw `/metrics` captures are retained.
- **Subjective result:** the user reported fully responsive operation with no symptoms while loaded-idle and during active inference: **0/5 degradation at both stages**.
- After stopping the lane, no local model process remained and simulated free memory returned to 70%. EXP-002 does not yet promote a final RAM boundary; this is one checkpoint in the ladder.

### EXP-002 official 6-bit checkpoint — complete

Raw summary: `results/raw/EXP-002/official-6bit-summary.json`. The exact prompt, warm-up, pre/inference/peak/post snapshots, `footprint` outputs, rapid-mlx metrics, timing, and subjective records are preserved alongside it.

| Model/build | Quant | Repository size | Idle OS footprint | Active peak OS footprint | rapid-mlx Metal active / peak | Swap used: idle → active → post | Pressure-free: idle / active / post | Prompt / decode | Idle rating | Active rating |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ornith-1.5-9B official MLX | 6-bit | 7.298 GB | 7,884 MB | 8,694 MB | 8.32 / 9.05 GB decimal | 4.60 → 3.88 → 6.61 GiB | 29% / 11% / 34% | 1,958 prompt / ~4.32 decode tok/s | 0/5 | 0/5 |

- Load duration was 33.27 seconds. The standardized request generated all 512 requested tokens successfully in 118.97 seconds, with a 0.44-second first streamed event.
- The 6-bit model's OS footprint was approximately 2.1–2.4 GB higher than the 4-bit model, and client-measured decode speed was approximately 45% lower in this run.
- rapid-mlx reported a 9.05 GB Metal peak after generation. The active-inference system snapshot reached 11% simulated pressure-free memory, while the user reported no perceptible degradation.
- **Subjective result:** the user reported fully responsive operation with no symptoms while loaded-idle and during active inference: **0/5 degradation at both stages**.
- After stopping the lane, no model process remained. An immediate reclamation sample was still pressured, but a delayed sample recovered to 66% simulated free memory with 3.08 GiB swap used. EXP-002 does not yet promote a final RAM boundary.

### EXP-002 official 8-bit checkpoint — load stability failure

Raw result: `results/raw/EXP-002/official-8bit-load-failure.json`; server log: `/Users/<user>/.hermes/logs/local-llm/fast-20260917_095902.log`.

- The 8-bit model repository is 9.536 GB. The model completed a one-token warm-up request successfully, but the server then received `SIGTERM` and shut down before a stable loaded-idle checkpoint could be captured.
- rapid-mlx itself warned that the model was likely too large for the hardware: model on disk 8.9 GB, estimated short-chat working set 13.3 GB, current OS use 9.4 GB, projected utilization 142%. The log explicitly warned of possible kernel-panic risk under continued pressure.
- The load log records Metal limits of 10.8 GB allocation and then successful engine/model warm-up; it does **not** prove that the SIGTERM was an OOM kill or kernel action. No user-facing idle or active rating is assigned, and no active 512-token run was attempted.
- After the failure, no model server remained; a read-only snapshot showed 71% simulated free memory and 3.65 GiB swap used.
- **Result:** official 8-bit is a load/stability failure under the current rapid-mlx 0.14.1 configuration and normal workload, not a measured subjective usability point. Do not promote it or retry blindly.

### EXP-002 interim ladder interpretation

The 4-bit and 6-bit points both produced **0/5 idle and active degradation**, but objective working-set and pressure costs rose substantially. The 8-bit point could not reach a stable idle state and emitted a severe memory-safety warning. A final comfortable/heavy/practical ceiling is not declared until the planned analysis reconciles these observations and the remaining uncertainty around the 8-bit SIGTERM.

### EXP-002 final primary-ladder analysis

Machine-readable analysis: `results/raw/EXP-002/final-analysis.json`.

| Model/build | Quant | Idle OS footprint | Active peak OS footprint | rapid-mlx Metal peak | Decode | Idle rating | Active rating | Outcome |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Ornith-1.5-9B official MLX | 4-bit | 5.750 GB | 6.282 GB | 6.81 GB | 7.891 tok/s | 0/5 | 0/5 | Stable |
| Ornith-1.5-9B official MLX | 6-bit | 7.884 GB | 8.694 GB | 9.05 GB | 4.320 tok/s | 0/5 | 0/5 | Stable, high pressure |
| Ornith-1.5-9B official MLX | 8-bit | — | — | — | — | — | — | Warm-up completed; stable-server validation failed |

- **Comfortable real-LLM footprint:** the largest observed stable point with 0/5 idle and active degradation was official 6-bit: 7.884 GB idle OS footprint, 8.694 GB active OS footprint, and 9.05 GB rapid-mlx Metal peak. This is an observed session maximum, not a universal safe budget.
- **Normal-use maximum:** official 6-bit was subjectively fully comfortable in this session, but its 11% simulated pressure-free sample and 6.61 GiB post-generation swap make it a high-risk normal configuration rather than the default recommendation.
- **Heavy-work budget:** no rating-3 boundary was reached; the largest deliberately tolerated configuration was 6-bit. The 8-bit point could not be classified.
- **Practical ceiling:** not numerically isolated. It is below the official 8-bit configuration under this launcher/workload because 8-bit failed stable-server validation. The nearest stable measured point was a 9.05 GB Metal peak; the 8-bit warning projected a 13.3 GB working set, but those are not a calibrated threshold pair.
- **Base-workload reserve:** no single GB reserve is promoted. The live baseline, compression, swap, and application mix varied, and VM categories overlap; subtracting model file size from 16 GB is invalid.
- **Main bottleneck:** resident Metal/unified-memory working set and resulting compression/swap pressure, not ordinary RSS. The 4-to-6-bit step added 2.412 GB to active OS footprint and reduced measured decode speed from 7.891 to 4.320 tok/s.
- **Recommended practical configuration:** treat official 4-bit as the robust default. Treat 6-bit as the largest observed high-memory option, pending repeated trials and separate Hermes quality/tool-use validation. Do not retry 8-bit blindly; any SIGTERM-source investigation is a separately approved diagnostic experiment.
- **Operational note:** after the 8-bit failure, the FAST manager unexpectedly auto-healed a default 4-bit lazy-standby server; it was stopped and verified down. Raw cleanup evidence is `results/raw/EXP-002/post-run-autoheal-cleanup.json`.
- **Confidence:** moderate for the relative 4/6/8-bit behavior and this session's subjective ratings; low-to-moderate for generalizing a universal RAM threshold. Remaining uncertainty includes the unproven SIGTERM source, single-run stable points, dynamic swap state, workload variation, and absent context/KV sweep.

## EXP-001 measurements — complete

Baseline and pressure-level measurements are preserved below. Every target has a JSON snapshot, allocator log, and subjective record under `results/raw/EXP-001/`.

### Baseline captured after readiness

- Raw artifact: `results/raw/EXP-001/baseline.json`
- Capture: 2026-09-17 06:37:26 UTC
- FAST and DEEP lanes were stopped to avoid double-counting an already-resident local model; the user workload remained open.
- Physical RAM: 16 GiB; simulated memory-pressure query reported 52% system-wide free; swap used was 1,019.31 MiB.
- Load average: 10.29 / 8.72 / 8.64 at capture. Major RSS consumers included Microsoft Teams helpers, Hermes renderer, and Brave; exact process data is preserved in the JSON.
- This is an observed baseline snapshot, not a claim that the machine was a clean/low-load baseline.

### 6 GiB level — objective and subjective record

- Raw artifacts: `level-06.0-gib.json`, `level-06.0-vmmap.txt`, and allocator log.
- Allocator PID: 93932; target: 6.000 GiB; 393,216 pages touched.
- `vmmap` reported physical footprint 6.0 GiB, with approximately 9 MiB resident and 6.0 GiB swapped out/unresident at the latest capture.
- System-wide free percentage was 52%; system swap remained 1,019.31 MiB in the snapshot.
- **User report:** rating **0/5** — “6GB i did not even notice at all - amazing.” User explicitly instructed continuation.
- Interpretation so far: the allocator committed the requested footprint, but anonymous pages were not kept physically resident. This is an important macOS/anonymous-memory limitation, not evidence that 6 GiB of model-like resident RAM is comfortable.

### 6 GiB subjective result

- Raw artifact: `level-06.0-subjective.json`
- Rating: **0/5**, no noticeable degradation.
- Decision: release 6 GiB and proceed to 7 GiB under the user's explicit instruction.

### 7 GiB level — objective and subjective record

- Raw artifact: `level-07.0-gib.json` and allocator log.
- Allocator PID: 95905; target: 7.000 GiB; 458,752 pages touched.
- `vmmap` reported physical footprint 7.0 GiB, with approximately 1.2 GiB resident and 5.8 GiB swapped out/unresident at capture.
- System-wide free percentage was 55%; system swap was 1,011.31 MiB.
- **User report:** rating **0/5** — “Fully responsive - great! No issues at all”. User explicitly instructed continuation to 8 GiB.

### 7 GiB subjective result

- Raw artifact: `level-07.0-subjective.json`
- Rating: **0/5**, fully responsive with no issues.
- Decision: release 7 GiB and proceed to 8 GiB under the user's explicit instruction.

### 8 GiB level — objective and subjective record

- Raw artifact: `level-08.0-gib.json` and allocator log.
- Allocator PID: 97919; target: 8.000 GiB; 524,288 pages touched.
- `vmmap` reported physical footprint 8.0 GiB, with approximately 963 MiB resident and 7.1 GiB swapped out/unresident at capture.
- System-wide free percentage was 50%; system swap was 1,011.31 MiB.
- **User report:** rating **0/5** — “Still all good - no lags - all fluent. All works good still”. User explicitly instructed continuation to 9 GiB.

### 8 GiB subjective result

- Raw artifact: `level-08.0-subjective.json`
- Rating: **0/5**, no lag and fluent operation.
- Decision: release 8 GiB and proceed to 9 GiB under the user's explicit instruction.

### 9 GiB level — objective and subjective record

- Raw artifact: `level-09.0-gib.json` and allocator log.
- Allocator PID: 99232; target: 9.000 GiB; 589,824 pages touched.
- `vmmap` reported physical footprint 9.0 GiB, with approximately 14 MiB resident and 9.0 GiB swapped out/unresident at capture.
- System-wide free percentage was 45%; system swap was 1,011.31 MiB.
- **User report:** rating **0/5** — “Still no problems. This is interesting :)”. User explicitly instructed continuation to 10 GiB.

### 9 GiB subjective result

- Raw artifact: `level-09.0-subjective.json`
- Rating: **0/5**, no problems reported.
- Decision: release 9 GiB and proceed to 10 GiB under the user's explicit instruction.

### 10 GiB level — objective and subjective record

- Raw artifact: `level-10.0-gib.json` and allocator log.
- Allocator PID: 864; target: 10.000 GiB; 655,360 pages touched.
- `vmmap` reported physical footprint 10.0 GiB, with approximately 1.1 GiB resident and 8.9 GiB swapped out/unresident at capture.
- System-wide free percentage was 49%; system swap was 1,003.31 MiB.
- Load average was 10.06 / 8.47 / 8.29 at capture.
- **User report:** rating **0/5** — “Still all good.” User explicitly instructed going higher.

### 10 GiB subjective result

- Raw artifact: `level-10.0-subjective.json`
- Rating: **0/5**, no issues reported.
- Decision: release 10 GiB and run an exploratory 11 GiB extension, one level at a time. This extends beyond the original 6–10 GiB sequence under explicit user instruction.

### 11 GiB exploratory level — objective and subjective record

- Raw artifact: `level-11.0-gib.json` and allocator log.
- Allocator PID: 2656; target: 11.000 GiB; 720,896 pages touched.
- `vmmap` reported physical footprint 11.0 GiB, with approximately 15 MiB resident and 11.0 GiB swapped out/unresident at capture.
- System-wide free percentage was 47%; system swap was 1,003.31 MiB.
- Load average was 9.32 / 8.77 / 8.45 at capture.
- **User report:** rating **0/5** — “Still all smooth...weird yesterday I had less apps open and ornith loaded with 7-8 GB footprint - mac became really slow... Interesting.” User requested complete-run analysis.

### 11 GiB subjective result

- Raw artifact: `level-11.0-subjective.json`
- Rating: **0/5**, no perceptible degradation.
- User-provided counterexample: a prior real Ornith MLX run with a reported 7–8 GiB footprint made the Mac very slow despite fewer apps being open.
- Decision: stop the synthetic allocator and analyze EXP-001; do not begin EXP-002.

## EXP-001 analysis and conclusion

### Objective run table

`vmmap` resident and swapped/unresident values refer to the allocator's writable region. System swap is the macOS `vm.swapusage` value. The baseline free-percentage value is recovered from the preserved raw command output; baseline JSON was captured before the parser began recording that field separately.

| Level | vmmap footprint | Writable resident | Writable swapped/unresident | System free % | System swap used | User rating |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | — | — | — | 52% | 1,019.31 MiB | — |
| 6 GiB | 6.0 GiB | 8.8 MiB | 6.0 GiB | 52% | 1,019.31 MiB | 0/5 |
| 7 GiB | 7.0 GiB | 1,228.8 MiB | 5,939.2 MiB | 55% | 1,011.31 MiB | 0/5 |
| 8 GiB | 8.0 GiB | 963.4 MiB | 7,270.4 MiB | 50% | 1,011.31 MiB | 0/5 |
| 9 GiB | 9.0 GiB | 13.8 MiB | 9.0 GiB | 45% | 1,011.31 MiB | 0/5 |
| 10 GiB | 10.0 GiB | 1,126.4 MiB | 9,113.6 MiB | 49% | 1,003.31 MiB | 0/5 |
| 11 GiB | 11.0 GiB | 14.8 MiB | 11.0 GiB | 47% | 1,003.31 MiB | 0/5 |

The 10 GiB writable-unresident value is 9,113.6 MiB, as preserved in the source artifact.

### Conclusion

- **Normal-workload baseline:** no single additive “GB already occupied” number is trustworthy because macOS VM categories overlap. The snapshot showed 119 MiB free pages, 3,343.5 MiB occupied by the compressor, 4,085.7 MiB wired, 5,564.3 MiB anonymous pages, and 1,019.31 MiB swap used; the workload was dynamic and already heavily compressed.
- **Comfortable synthetic budget:** at least **11 GiB** for this allocator under this session; every level scored 0/5 subjectively.
- **Heavy-work synthetic budget:** at least **11 GiB**; no user-visible degradation was reported.
- **Practical ceiling:** **not reached** by the synthetic allocator at 11 GiB. This is not a safe model-configuration ceiling.
- **Observed pain threshold:** **not reached** in this synthetic test.
- **Main limiting behavior:** macOS committed the requested footprint but made most pages non-resident. Across levels, writable-region residency ranged from roughly 9 MiB to 1.2 GiB while the virtual/physical footprint matched the requested 6–11 GiB. System swap stayed near 1 GiB and the simulated free-percentage output fluctuated between 45–55% rather than showing a clean monotonic boundary.
- **Most important caveat:** this experiment did **not** reproduce the user's prior real-world Ornith MLX behavior, where a reported 7–8 GiB model footprint made the Mac very slow. The difference strongly suggests that Metal/unified-memory allocation, model access patterns, KV cache, compression behavior, and workload composition matter more than an anonymous virtual footprint alone.
- **Confidence:** high for the recorded subjective result and this allocator's behavior under this session; low for inferring a safe actual LLM RAM budget.
- **Next implication:** do not promote 11 GiB as an LLM budget. The next useful experiment is a model-specific Metal/MLX test using the real Ornith workload and the same subjective gate. EXP-002 remains unstarted.

The final analysis must distinguish:

- **comfortable budget:** no material effect on normal work;
- **heavy-work budget:** degraded but acceptable when deliberately running a demanding model;
- **practical ceiling:** not a design target for normal configurations;
- **pain threshold:** where the user reports an annoying or disruptive experience.

## Inherited local-lane measurements

Source: existing `local-llm-lanes` profile skill, described as measured on this Mac with one resident model; conditions and raw artifacts are not yet linked here.

| Candidate | Decode tok/s | Prefill note | Capability / reliability note | Lab interpretation |
|---|---:|---:|---|---|
| Ornith-1.5-9B MLX-4bit | 15.1 | ~180 tok/s at ~21k tokens | Profile notes native tool calls verified at full Hermes-prompt scale | Current FAST reference; reproduce first |
| Qwen3.5-9B 4-bit MLX | 15.6 | ~780 tok/s at ~21k tokens | Profile notes BFCL-V4 ranking | Strong prefill comparison; exact build unknown |
| Ornith-1.5-9B OptiQ-4bit | 12.3–12.8 | ~114 tok/s | No reported win over uniform 4-bit | Do not assume selective quantization helps |
| Qwen3.8-9B-Distill GGUF Q4_K_M | 12.6 | ~400 cold; near-instant warm | Profile notes tool-call degradation at large agent prompt scale | Reliability gate may dominate benchmark score |
| Ternary-Bonsai-27B MLX 2-bit | ~2–4 | ~140–190 tok/s | No published agentic benchmark in the note | DEEP research candidate, not a default |
| Qwen3.8-27B TQ3 | 3.6–3.9 | ~20 tok/s | Profile notes runtime/agent failures on this 16 GB setup | High-risk; not a first experiment |

These numbers are directional only: exact revision, repetitions, machine state, and raw logs must be recovered or re-measured.

## Cross-project evidence

`QwenLoop` reports a separate baseline on Qwen3-0.6B for its variable-depth arithmetic benchmark: greedy MPS fp32, d2 65.6%, d4 56.2%, d8 40.6%, d12 40.6%, d16/d24 0% (small/deep sample sizes as documented there). This is relevant evidence about local evaluation discipline and capability-vs-compute questions, not a Local LLM Lab model ranking.

## EXP-003 Phase 1/2/3/5/7 first-load and slot comparison — 8/16-slot checkpoints complete

The compatibility report is `results/raw/EXP-003/compatibility-gate.md`; machine-readable provenance is in `source-provenance.json`, `cache-cleanup.json`, `download-verification.json`, `gguf-header.json`, `memory-model-estimate.json`, `first-load-8slot-summary.json`, and `16slot-summary.json`.

- Chosen implementation: `kisasexypantera94/llama.cpp` branch `moe-expert-residency`, head `41ec4c4e94fd5ff6c258691f35f2fcd0d3dde892`, isolated under `results/raw/EXP-003/source/`.
- Isolated Metal build passed on AppleClang 21/macOS 27 with `llama-server` and `llama-cli`; `--moe-n-slots` and `--moe-n-layers` are present. Homebrew upstream 0.4.1 has no equivalent disk-slot flags/offloader source.
- Official GGUF header verifies `qwen35moe`, GGUF v3, 41 blocks, 256 experts, 8 experts/token, 512 expert intermediate, 123 expert tensors, and mixed Q4_K/Q6_K routed tensors. The full file hash matches SHA-256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`.
- Before download, removed only the obsolete EXP-002 official 6-bit and 8-bit caches; HF reported 16.8 GB freed. FAST 4-bit, DEEP Bonsai, OptiQ, GPT-OSS, Qwen candidates and GGUF fallback were retained.
- Official target acquired: `ornith-ai/Ornith-1.5-35B-A3B-GGUF`, revision `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`, 21,713,463,040 bytes. Q5/Q6 and mmproj were not downloaded.
- First launch required `-b 2048 -ub 1`: an initial `-b 1 -ub 1` attempt hit `GGML_ASSERT(n_tokens_all <= cparams.n_batch)` before readiness and is preserved as a configuration failure, not a model failure.
- 8-slot checkpoint: process footprint 3.307 GB idle / 3.863 GB active peak; decode 4.32–4.95 tok/s; minimum simulated free 25%; coherent repeated output; no missing-tensor, NaN, GPU or crash errors. User rating: primary 0/5, possible unrelated transient 1/5 for a few seconds.
- Clean no-model GPU baseline: IOAccelerator allocated 5.508 GB / in-use 1.943 GB, simulated free 70%.
- 16-slot checkpoint: process footprint 3.581 GB idle / 4.204 GB active peak; decode 4.43 tok/s; prompt 4.20 tok/s; minimum simulated free 31%; coherent HTTP 200 output; no runtime errors. System-wide IOAccelerator peaked at 8.866 GB allocated / 5.896 GB in use, but this is not solely attributable to llama-server.
- 16 slots produced no meaningful speed improvement over 8 slots (~2.7% in this single comparison) while adding ~0.34 GB process footprint. User rating was likewise primary 0/5, with a possible brief 1/5 that may be unrelated. Server and port were explicitly stopped and verified unreachable; FAST and DEEP remain down.
- Fresh deterministic equivalence check: with the same prompt, `temperature=0`, `seed=12345`, no-thinking mode, and fresh servers, 8 and 16 slots both returned HTTP 200 and the exact same 661-character output (`sha256=362239f568d44589166e74dfb06a56a250aace5cd2e18f132ca333b610fad82d`). This establishes internal slot-count consistency, not equivalence against an independent reference implementation. Artifacts: `results/raw/EXP-003/deterministic-compare/`.
- Minimal Hermes-native tool-call smoke test was attempted with 8 slots and only the terminal tool. Direct generation was previously successful, but Hermes integration did not complete: the existing local-minimal profile used `codex_responses` against a chat-completions endpoint and produced no parsed SSE events; a temporary protocol-correct `chat_completions` profile, server-side reasoning-off, and 600-second timeout still saw the client request canceled before any response/tool call. Peak server footprint was approximately 3.65 GB; simulated free remained 31–39%. The user's normal-workload rating during this activity was again primary 0/5, with only the previously noted possible brief 1/5. Temporary profile `exp003-smoke` was deleted and ports 8901/8902 are closed. Artifact: `results/raw/EXP-003/hermes-tool-call-summary.json`.

### EXP-003 option 2 — MLX-native runtime checkpoint

Artifact: `results/raw/EXP-003/mlx-option2/summary.json`.

- Downloaded the exact official MLX-4bit checkpoint `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit` at snapshot `19504d912fa8fc7622bf6b1de3db5d5d890b1f02`; four safetensor shards total `19,530,936,278` bytes (~18.2 GiB). The config identifies `model_type: qwen3_5_moe` and 4-bit affine group-size-64 quantization.
- Rapid-MLX 0.14.1 server startup and OpenAI-compatible health/models endpoints succeeded with `--disk-stream --disk-stream-cache-gb 1 --lazy-load`. No model weights were resident before the first request.
- The first short completion request returned HTTP 503 before generation. Root cause: `UnsupportedModelTypeError`; Rapid-MLX's disk-stream registry has no `StreamingAdapter` for `qwen3_5_moe`, and explicitly refuses to fall back to resident loading.
- Rapid-MLX estimated a 27.3 GB short-chat working set for the 18.2 GiB checkpoint on this 16 GiB machine and warned of possible macOS kernel-panic risk. A resident-load retry was deliberately not attempted because it would exceed the established safety envelope without answering the SSD-streaming question.
- Version check against Rapid-MLX 0.14.2 showed the same registry state: `qwen3_5_moe` absent, `qwen3_next` present. Upgrading is therefore not expected to change this result. No Hermes defaults, FAST/DEEP lanes, or installed runtime version were changed.
- **Result:** MLX is a viable API/tool-serving framework, but the currently available MLX disk-stream implementation cannot serve this exact 35B model. This is a runtime adapter gap, not evidence that the MLX checkpoint itself is corrupt.

## EXP-003 Phase 8 — Hermes streaming bridge repaired and verified

Artifact: `results/raw/EXP-003/bridge-fix/summary.json`; bridge implementation: `tools/exp003_capture_proxy.py`.

- The bridge transparently forwards llama.cpp SSE responses without advertising a false zero-length body. It injects `chat_template_kwargs.enable_thinking=false` into every request, including Hermes's auxiliary session-title request.
- For the controlled verification, the bridge restricted the request to the required `terminal` tool and capped output at 256 tokens. This removed Hermes's large deferred-tool catalog from the model request; the production Hermes profile/defaults were not modified.
- The real Hermes agent parsed the streamed response, issued a native `terminal` call with `{"command":"date"}`, executed it, and returned the actual output `Thu Sep 17 14:02:17 CEST 2026`. Hermes exited 0. This passes the native tool-call correctness gate for the bridge path.
- Latency is the limiting factor: the 241-token title request took 62.19 s; the full 3,332-token Hermes prompt took 773.51 s at approximately 4.31 prompt tok/s; follow-up tool-result turns took 13.69 s and 34.05 s. Protocol correctness is therefore established, but this 35B SSD-streaming lane is not practically interactive with the full Hermes prompt.
- All test processes were stopped afterward. Ports 8901 and 8905 were verified closed. FAST, DEEP, and Hermes defaults were unchanged.

## EXP-004 Phase 1/2 — GPT-OSS-120B ExpertCache prerequisite and disk gate

Artifacts: `results/raw/EXP-004/phase1/phase1-freeze.json`, `compatibility-gate.md`, `disk-gate.json`, `disk-inventory.json`, and `runtime-prepare-no-build.log`.

- Frozen EXP-003 before changes: Ornith 35B Q4_K_M, isolated fork commit `41ec4c4e94fd5ff6c258691f35f2fcd0d3dde892`, 8-slot active peak 3.863 GB, 4.32–4.95 tok/s direct decode, and verified native Hermes bridge path. EXP-003 source, Hermes defaults, FAST, and DEEP were not modified.
- Cloned `amos-labs/expertcache` at `e6a3b940a8cd8465be0cd8cdf0f39829ebfa6ade` into a separate EXP-004 source tree.
- Prepared the pinned llama.cpp revision `7e1e28cae36d41fe7bbe9dae7c9625de6565c063` with the exact ExpertCache patch. Patch application passed and SHA-256 matched `6bb978ab189ded46b131edea81fbe0740d7d527797be553f91312e4704f76a63`. No full build or model inference was started.
- `npm run check` passed. After creating the documented project-local Python 3.11 venv and installing only `numpy==1.26.4`, `npm test` passed 29/29.
- Official GPT-OSS config confirms `gpt_oss`, 36 layers, 128 experts, 4 experts/token, 2,880 hidden/intermediate dimensions, MXFP4 quantization, and 131,072 maximum positions. The manifest pins `ggml-org/gpt-oss-120b-GGUF` revision `238abdd290bb874b90a5da1b4549881b7d05c091`, file `gpt-oss-120b-MXFP4.gguf`, 63,387,346,208 bytes, SHA-256 `582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d`.
- No GPT-OSS-120B file exists in the local cache. Internal free space is approximately 20 GiB; the documented physical-16-GiB runbook requires at least 80 GB free before the 59.0 GiB binary checkpoint is copied and temporary build/download headroom is considered.
- **Result:** download deferred and EXP-004 paused at the disk gate. This is a resource prerequisite failure, not a model/runtime failure.

### EXP-004-Gemma 4 26B-A4B follow-up

- The official `unsloth/gemma-4-26B-A4B-it-GGUF` MXFP4 MoE file was downloaded at revision `c099eb48e663fd284577b04978a94ffccb261841`: `gemma-4-26B-A4B-it-MXFP4_MOE.gguf`, 16,551,048,928 bytes, SHA-256 `a8908250f2a72a5824382d488158f12b65effa24e6c6b1244e5b4818ac0a1459`.
- The same pinned ExpertCache runtime built successfully, and the patched MXFP4 Metal operation test passed on Apple M3 (`supported=1`).
- The ordinary official Q4_0 Gemma file was not selected because the ExpertCache patch specifically targets MXFP4 expert tensors; the MXFP4 file exercises the requested same streaming path.
- Architecture metadata confirms Gemma4ForConditionalGeneration, 30 layers, hidden size 2,816, 128 experts, 8 routed experts/token plus one shared expert, 704 expert intermediate size, and 262,144 context.
- The protected first-load probe has not started: system swap is currently 2.38 GiB used, above the runbook's 2 GiB precondition. Memory pressure is otherwise 54% free and no `llama-server` is running. This is a deferred safety gate, not an inference failure.
- **Artifact:** `results/raw/EXP-004/gemma4-26B-A4B/acquisition.json`.

## EXP-005 Phase 1/2 — Slipstream inspection, isolated build, and compatibility/resource gate

Artifacts: `results/raw/EXP-005/phase1-freeze.json`, `compatibility-gate.md`, `runtime-inspection.md`, `build-source.log`, product build logs, and `server-tests.log`.

- Preserved EXP-003 and EXP-004 exactly; no Hermes defaults, FAST/DEEP lane, system llama.cpp, or existing model tree was modified. No local model process is running.
- Cloned `dwijenpatel/slipstream` at pinned commit `3a892465729406944778a24064664d817617f558` into `results/raw/EXP-005/source/slipstream/`.
- Verified the native target: `mlx-community/Qwen3.6-35B-A3B-4bit`, revision `38740b847e4cb78f352aba30aa41c76e08e6eb46`, approximate ranged download `19,529,025,048` bytes, installed `.gturbo` estimate `19,546,491,213` bytes, plus a 1 GiB reserve. The isolated native install is complete and verified under `results/raw/EXP-005/model/qwen36.gturbo/`.
- Verified the pinned Qwen architecture against the runtime cross-check: `qwen3_5_moe`, 40 layers, 256 experts, top-8 routing, hidden 2048, expert intermediate 512, 30 Gated-DeltaNet layers, 10 full-attention layers, affine 4-bit group-size-64 weights, and 262,144 source context positions.
- Built `.build/release/slipstream-repack`, `.build/release/slipstream`, and `.build/release/slipstream-server` successfully with Swift 6.4 on macOS 27 using Command Line Tools. Exercised `--help` for all three.
- Full package build failed only in the optional SwiftUI Mac app because `SwiftUIMacros` is unavailable under the active CLT-only developer directory. The CLT contains `TestingMacros`; an explicit plugin-path retry still did not produce a complete server-test run. No test pass count is claimed.
- Server inspection confirms loopback-only OpenAI Chat Completions and Anthropic Messages endpoints, JSON/SSE streaming, function tools, Qwen tool-call parsing, and one in-process single-prefix cache. The CLI supports exact-prompt disk KV snapshots; a server restart loses its in-memory prefix. Cache misses are explicit for model/template/domain, tool-schema, history, assistant-turn, and unsupported continuation changes.
- Resource gate snapshot: 56 GiB free disk, 59,243,948 KiB exact available blocks, 2,350.38 MiB swap used, 60% memory-pressure free, no model process. Disk capacity passed; the pre-install memory state was not a clean first-inference baseline.
- **Result:** Slipstream passed the source/runtime gate, native install gate, and first standalone correctness gate. Subsequent measured phases are recorded below; no candidate has been promoted to Hermes defaults or FAST/DEEP.

## EXP-005 Phase 3 — Native Qwen install and first standalone probe

- Approved native ranged install completed using the pinned Slipstream repacker. The verified artifact is `results/raw/EXP-005/model/qwen36.gturbo/`; its manifest covers 40 packed expert layer files, `model_weights.bin`, tokenizer data, and the `.gturbo` layout. Apparent footprint is 19,094,088 KiB (approximately 19.55 GB).
- First guarded run used the isolated `slipstream` CLI with 16 expert-cache slots, `--max-context 4096`, `--prefill-chunk auto`, temperature 0, seed 12345, prompt `Reply with exactly READY.`, and `--max-new 8`.
- Standalone correctness passed: output contained the expected `READY.` and process exit code was 0. The timing footer reported 5 prompt tokens in 8.81 s and 8 generated tokens at 8.325 tok/s.
- Sampled peak process footprint was 1,445 MB, peak sampled RSS 363.9 MB, and maximum sampled CPU 99.3%. System-wide free memory moved from 58% to 51%; swap remained exactly 2,310.38 MiB before/after. Because swap was already elevated, this is not a clean memory-baseline result.
- First clean post-reboot probe used the same 16-slot deterministic settings: exact `READY.`, 5-token cold prefill 14.22 s, 8-token decode 8.404 tok/s, peak physical footprint 1,460 MB, peak sampled RSS 269,056 KiB, and swap 0 → 0 MiB. Artifact: `results/raw/EXP-005/first-probe-clean/summary.json`.

## EXP-005 Phase 4–7 — Prefill/decode, KV snapshots, API, and Hermes tool use

- Clean post-reboot fresh-process sweep at 16 slots passed all five arms with swap remaining 0 MiB before/after each arm: 273 prompt tokens → 9.74 s prefill / 8.417 tok/s decode; 546 → 11.40 s / 8.219 tok/s; 1,105 → 15.14 s / 7.531 tok/s; 2,210 → 37.99 s / 5.903 tok/s. Artifact: `results/raw/EXP-005/prefill-sweep-clean/summary.json` and `prefill-sweep-clean/results.json`.
- Clean post-reboot disk-KV repeat reproduced exact-prompt restore with swap remaining 0 MiB: 1,196-token cold save took 16.67 s prefill / 7.563 tok/s decode; the 88,883,888-byte snapshot restored in 0.04 s prefill but decoded at 1.546 tok/s and took 12.405 s total. Artifact: `results/raw/EXP-005/kv-snapshot-clean/summary.json`.
- Loopback OpenAI API passed `/v1/models`, non-streaming and SSE streaming requests, and a native function-tool loop. Slipstream emitted a valid `terminal({"command":"date"})` call, accepted the returned tool message, and finished with the correct timestamp. The initial request with `parallel_tool_calls: false` correctly returned HTTP 400 because Slipstream rejects that unsupported field; the corrected request passed.
- Clean post-reboot Hermes integration passed in the isolated `exp005` profile with wrapper exit 0 and 0 MiB swap at launch. The real terminal tool call and follow-up completed; first request measured 5,003 prompt tokens / 107.87 s TTFT, then 5,052 cached of 5,106 tokens / 4.50 s follow-up TTFT. Post-test swap was only 84.38 MiB. Artifact: `results/raw/EXP-005/hermes-tool-test-clean-reboot-result.json`.
- **Decision:** runtime, native API, and one constrained Hermes tool turn pass; no default model or lane promotion. The main remaining questions are sustained responsiveness, quality across coding/research, expert-cache-slot trade-offs, and whether the slower warm disk-KV decode is reproducible.

## Findings not yet established

- Exact expert-streaming token-for-token equivalence against an independent reference execution.
- MLX-native serving of the exact `qwen3_5_moe` checkpoint; current Rapid-MLX disk streaming lacks the required architecture adapter.
- Interactive Hermes latency at full prompt scale without the controlled terminal-only bridge constraint; the native tool-call protocol itself is verified.
- Expert-cache hit rate/locality instrumentation and 24/32-slot comparisons.
- Whether 24/32 slots provide a worthwhile speed gain relative to their higher memory risk; current 8/16 evidence does not justify running them automatically.
- No candidate has been promoted to FAST or made the Hermes default.

## EXP-006 Phase 1/2 — TinyTitan discovery, storage gate, and isolated build

- NVMAI is now named **TinyTitan**. `https://github.com/Pummelchen/NVMAI` and `https://github.com/Pummelchen/TinyTitan` resolve to the same current repository; EXP-006 pins commit `008510e2753cc16a674cb75169ba3133cf56fa4e` in `results/raw/EXP-006/source/tinytitan/`.
- The current tree explicitly supports Qwen3.8-Flash-Next `qwen38flash`: 48 layers, 512 experts/top-10, Gated-DeltaNet + QSA, hyper-connections, and hashed n-gram/PLE embeddings. The shipped 4-bit profile uses a 12 GiB expert-cache target, no predictive prefetch, and a 4,096-token prefill chunk.
- TinyTitan pins `RockTalk/Qwen3.8-Flash-Next-MLX-4bit` at revision `478474da92599ad0cf9f8bd447e658b29cb8480a`. The main 4-bit install estimate is 174,228,562,488 bytes plus a 4 GiB reserve; the optional MTP draft is deferred.
- The user-reported Storage Settings value was 228.88 GB available. `diskutil` initially reported only ~40.8 GB immediate APFS free space because three local Time Machine snapshots were marked purgeable. TinyTitan's first install attempt correctly refused with `required 178265077776, available 39169024000`.
- Apple-supported `tmutil thinlocalsnapshots / 200000000000 4` successfully thinned all three local snapshots. Immediate APFS free space rose to approximately 210–212 GiB, satisfying the TinyTitan guard without bypassing it. The model is being installed on the internal Macintosh HD; `/Volumes/Backup` was not used because it is the Time Machine destination and is not writable by the current user.
- `swift build -c release` completed with `build_exit=0` under Swift 6.4/macOS 27 Command Line Tools. TinyTitanRepack, TinyTitanCLI, TinyTitanServer, and TinyTitanBench all report arm64. TinyTitanBench traps on `--help` while initializing a Metal function; this is recorded as a separate CLI defect and does not block the repacker/server path.
- The native repacker completed with exit 0 and reported `Installed Qwen3.8-Flash-Next 125B-A6B 4-bit` at source revision `478474da92599ad0cf9f8bd447e658b29cb8480a`. The final verified tree contains 58 files and 173,970,097,278 logical bytes (~162.02 GiB), including the 102,400,491,520-byte n-gram table. `manifest.json` and `verified-install.json` are present.
- Non-inference preflight passed: source/model directories and all TinyTitan arm64 binaries are present; no competing local model process; system-wide swap is 0 MiB; memory free is 56%; internal free space is 50 GiB. No inference process or Hermes configuration has been started or changed.
- Raw artifacts: `results/raw/EXP-006/phase1-freeze.json`, `storage-gate.json`, `runtime-inspection.md`, `launch-plan.md`, `build-source.log`, `binary-verification.log`, and `qwen38-install.log`.
- Preparation artifacts added without launching inference: `INFERENCE-GATE.md`, `preflight.py`, `run-probe-gated.sh`, `comparison-template.md`, `hermes-runbook.md`, `thermal-runbook.md`, and captured CLI/server help. The probe script requires an exact explicit approval marker and the verified model receipt.

## EXP-006 approved inference — first operational boundary

- **Default CLI raw-prompt probe:** process exit 0, but correctness failed. Output was an incomplete `<think>` fragment rather than `READY.`; prefill was 5.61 s for 5 prompt tokens and the reported decode rate was 0.263 tok/s for the 8-token cap. Swap rose from 0 to 5,916.75 MiB during the run.
- **Chat-template CLI probe with reasoning off:** correctness passed (`READY`), but default cache behavior was not practical: 17.11 s prefill for 225 prompt tokens and 0.036 tok/s for a 2-token answer. Swap rose from 3,282.19 to 5,445.19 MiB.
- **8 expert slots:** correctly rejected before generation because the model routes 10 experts and cannot fit them in 8 slots.
- **16 expert slots:** correctness passed (`READY`), 14.03 s prefill for 225 tokens and 2.778 tok/s on a 2-token answer. A 64-token capped throughput task measured 14.79 s prefill for 238 tokens and 2.629 tok/s decode. The counting task reached 24, then repeated `2` until the cap; this is not a quality pass. Swap did not grow during the 64-token run.
- **OpenAI-compatible API:** TinyTitanServer bound to loopback and passed `GET /health`, `GET /v1/models`, and a non-streaming Chat Completions request. Exact `READY` returned in 6.652 s with 31 prompt tokens, 2 completion tokens, and 0 reasoning tokens. A function-tool request emitted a valid `get_weather({"city":"Berlin"})` call, but took 35.954 s for 292 prompt / 38 completion tokens.
- **Hermes profile:** isolated `~/.hermes/profiles/exp006` was created and pointed at the loopback server; the default profile was not changed. The first Hermes request exposed the 4,096-token server ceiling; an 8,192-token retry still rejected Hermes' large output allowance; a 65,536-token retry ran for the 420-second tool limit while the server remained in generation. Hermes integration is therefore **timeout/fail**, not passed. The server was stopped afterward.
- **Operational interpretation:** TinyTitan/Qwen3.8-Flash-Next is format-compatible and API/tool-call-compatible, but the tested 16 GiB M3 configuration is currently not interactively practical: 2.6 tok/s best measured short decode, very slow prompt processing, substantial swap pressure, and Hermes timeout. No promotion or default change is allowed.

### EXP-006 optimization sprint — bounded conclusion

Artifacts: `results/raw/EXP-006/optimization-sprint/`.

- Clean traced 16-slot control: 238-token prefill in 15.30 s; 64-token decode 2.368 tok/s; 49.5% expert-cache hit rate (14,964 hits / 15,276 misses); 39.39 GiB decode expert traffic / 630.3 MiB per generated token; swap 0 → 400.88 MiB.
- Numerics-preserving 24-slot bundle arm: 238-token prefill in 15.94 s; decode 2.839 tok/s; hit rate 65.7% (19,862 / 10,378); 26.76 GiB / 428.2 MiB per generated token; swap 0 → 1,493.12 MiB. It reduced SSD expert traffic 32.1% but remained below the operational threshold and introduced unacceptable swap.
- Evidence-supported I/O-reduction arm: 16-slot `aging-lfu` policy, with every other setting unchanged, decoded at 2.442 tok/s with 14,967 hits / 15,273 misses, 49.5% hit rate, and 630.2 MiB/token. It did not materially change cache behavior or I/O.
- **Decision:** after the Usability Bundle and one I/O-reduction attempt, Flash-Next remains below the >=4 tok/s gate. Stop optimizing it as an interactive Hermes default on this Mac. Preserve the model and artifacts; return the interactive-default branch to Qwen3.6 + Slipstream. Carnice-Qwen3.6 is the next low-risk candidate when separately approved.

## EXP-009 — current TinyTitan long-context requalification gate

- **Runtime change isolated:** current TinyTitan commit `9c03db58d86e7ac35917ee3f05cf58fbab97f666` was separately cloned and release-built (Swift 6.4 arm64) under `results/raw/EXP-009-qwen38-long-context/source/`; EXP-006 source/model/default profiles were not modified. The existing verified native 4-bit Qwen3.8-Flash-Next install was reused in place.
- **Initial state:** no Qwen Flash process and no FAST/DEEP lane were live; baseline swap was 1,585.56 MiB and memory-pressure free was 60%.
- **Real short-context gate:** a deterministic 350-unit natural-language corpus plus a 256-token task was constructed for approximately 7K tokens and run with `max-context=8192`, `prefill-chunk=4096`, 16 expert slots, exact routing, greedy decoding, and current runtime settings. The model was stopped during prefill before a timing footer or first generated token, so no accepted-token count, TTFT, prefill rate, decode rate, or cache hit rate is claimed.
- **Safety result:** swap peaked at 4,387.06 MiB, a **2,801.50 MiB / 2.736 GiB** increment; at the stop the process RSS was 5.48 GiB and process physical-footprint peak was 8.06 GiB. Memory-pressure free was captured at 21% (contemporaneous query: 26%). The CLI was terminated to protect host usability; after stop no model process or local test port remained, and free pressure recovered to 70% while macOS retained allocated swap.
- **Decision:** classify as `stopped_for_swap`, not as a runtime crash or a performance score. Do not advance to 32K/64K/128K, prefix cache, Hermes, coding, or research qualification. The immediate bottleneck is long-prefill unified-memory/swap pressure, not cooling or a measured decode shortfall. Raw report: `results/raw/EXP-009-qwen38-long-context/REPORT.md`.

## EXP-013 — Qwen3.8-Flash-Next 2-bit TurboQuant expert-streaming storage/resident-memory gate

- **Status:** `stopped_before_download_and_inference`; no candidate bytes were acquired and no model process was launched. FAST/DEEP were down.
- **Pinned candidate:** `manjunathshiva/Qwen3.8-Flash-Next-tq4a-tq2e-g64` revision `9e5c4343ab3a3917100c94e1b0dd39dea617faab`; exact model tree **56,757,557,995 bytes / 52.860 GiB** (11 text shards plus 0.836 GiB bf16 vision tower).
- **Disk gate:** immediate APFS free space was **61,603,139,584 bytes / 57.372 GiB**. A direct single-copy payload would leave only **4.513 GiB**, short of a modest 10 GiB operating reserve by **5.487 GiB**, before transfer-cache/scratch overhead. No protected baseline or user payload was deleted.
- **More decisive runtime gate:** inspected pinned TurboQuant-MLX `d1c34c63bc99f5744f409868b198cc692b84b65c` / `turboquant-mlx-full 0.27.0`. `load_streaming()` replaces only `switch_mlp` routed projections, while the rest is resident. The model card/planner reports **21.86 GB non-expert resident weights** after `--ngram-offload`; this is already above 16 GiB before expert cache, recurrent/QSA state, KV, activations, or macOS. The `--ngram-offload` implementation is genuine memory-mapped PLE offload and is bit-identical, but cannot lower the remaining resident floor.
- **Decision:** the native-top-10 2-bit expert-streaming speed hypothesis is **not safely measurable with this representation on this Mac**. Do not infer decode speed or quality. Reopen only with a representation/runtime that materially lowers the non-expert resident footprint; freeing disk alone is not a fix.
- **Raw evidence:** `results/raw/EXP-013-qwen38-flash-2bit-streaming/STORAGE_GATE_REPORT.md` and `model-and-runtime-provenance.json`.

### EXP-013 correction — n-gram overlap and remote header-only planning (2026-09-19)

- **Correction:** the 21.865 GB `resident_bytes` value includes the 19.200 GB PLE/n-gram table. Both pinned `plan.py` and actual `stream/loader.py` calculate post-offload wired resident as `resident_bytes - ngram_bytes`, yielding **2,664,831,544 bytes / 2.482 GiB**, not 21.865 GB. D-027's resident-memory conclusion is superseded; the original record remains preserved.
- **Remote plan:** header-only planning at the exact current HF revision `9e5c4343ab3a3917100c94e1b0dd39dea617faab`, 16 GB assumed RAM, 8,192 context, and `--ngram-offload` classified the model `streaming`, `runnable: true`. Its cache-budget helper projects 9.439 GB with its conservative auto cache; loader-consistent fixed 1 GB and 2 GB cache projections are 5.049 GB and 6.049 GB respectively. These are projections, not local measurements.
- **Planner caveat:** `projection.peak_bytes` (37.923 GB) includes the complete expert bank despite a streaming verdict, so it is internally inconsistent and must not be used as the streaming peak. The verdict/cache helper use the corrected 2.665 GB core.
- **Independent blocker remains:** live immediate APFS free is 59.941 GiB. A direct 52.860 GiB candidate acquisition would leave 7.081 GiB, **2.919 GiB below** a 10 GiB reserve before transfer overhead. No download or inference occurred.
- **Correction artifacts:** `results/raw/EXP-013-qwen38-flash-2bit-streaming/CORRECTION-2026-09-19.md`, `correction-accounting.json`, `correction-remote-plan-raw.json`, and `correction-summary.json`.

### EXP-013 Stage 1 — native-top-10 2-bit streaming smoke (2026-09-19)

- **Acquisition/runtime:** user-authorized direct text-model-only acquisition completed at exact revision `9e5c4343ab3a3917100c94e1b0dd39dea617faab` (11 shards, 55,839,256,949 bytes; optional `vision.safetensors` excluded). Isolated pinned TurboQuant-MLX 0.27.0 ran with MLX 0.32.2 / MLX-LM 0.31.3.
- **Controlled arm:** 1.0 GB expert cache, native top-10 (`--max-active-experts 0`), `--ngram-offload`, F_NOCACHE auto-selected, no MTP/speculation/reduced top-k/router approximation/`--fast`; 30-token factual prompt and 31 generated tokens.
- **Function/safety:** loader completed in 1.0 s, PLE offload was active (17.88 GiB out of GPU memory), 144 projections were streamed, and output was coherent. Peak RSS/MLX were 3.71/3.87 GB. Swap delta was 0 MiB, swapouts +0, and pageouts +1.91 MiB; no severe memory event.
- **Performance:** **1.475 tok/s** generation footer and **1.0 tok/s** end-to-end accepted-token footer; cache hit rate 23.6%, critical expert reads 21.6 GB, and approximately 664–687 MiB critical expert bytes/output token. This is below the **<3.5 tok/s hard stop** and therefore rejects the 4 tok/s hypothesis before any quality or long-context work.
- **Decision:** stop EXP-013 after Stage 1. Preserve assets/evidence; do not attempt Stage 2, quality A/B, long context, or a custom hybrid runtime for this representation on this Mac. Raw report: `results/raw/EXP-013-qwen38-flash-2bit-streaming/STAGE1_REPORT.md`.

## EXP-010 — Laguna S 2.1 TurboQuant-MLX short populated-context safety gate

- **Runtime/model:** isolated `manjunathshiva/turboquant-mlx` with `manjunathshiva/Laguna-S-2.1-tqTe-g64`, a TQ 3-bit-attention / 1.58-bit ternary-routed-expert artifact. Runtime/model provenance, source survey, configuration, download log, and SHA-256 file hashes are preserved under `results/raw/EXP-010-laguna-long-context/`. The single downloaded model tree measured `28,034,372 KiB`; no second runtime/model representation was acquired.
- **Controlled actual-context arm:** loopback-only TurboQuant server, 4.0 GiB expert-cache budget, native top-10 routing, default FP16 KV, DFlash off, and a deterministic Hermes-shaped prompt of **6,159 rendered tokenizer tokens**. FAST and DEEP were down before and after the arm; Hermes defaults were unchanged.
- **Safety result:** the strict guard stopped the process at system-wide free memory **13%**, below its 20% threshold. System swap moved 3,437.06 → 3,470.94 MiB (**+33.88 MiB**), so the authoritative classification is `stopped_for_memory_pressure`, not `stopped_for_swap`. The request returned HTTP 200 but was terminated during the request and emitted no completion events; therefore no generation, TTFT, prefill rate, decode rate, cache-hit rate, physical footprint, Metal-memory, or thermal score is claimed.
- **Decision:** do not advance to prefix reuse, cache-budget tuning, 32K, 64K, 128K, Hermes tool use, coding, or DFlash. The required 4K–8K populated short-context safety prerequisite failed before sustained decode, so Laguna is **not viable as the requested primary local Hermes coder in this current 16 GiB TurboQuant/tqTe configuration**. This does not establish that every future radically different Laguna runtime is impossible; any reopen requires a new short populated-context safety pass and a non-duplicating storage plan. At EXP-010's original post-download gate, immediate root free space was 4.1 GiB, so the streamlx comparison artifact was correctly not added; any later acquisition must use a fresh storage measurement.
- **Raw report:** `results/raw/EXP-010-laguna-long-context/REPORT.md`.

### EXP-010 postmortem — host watchdog restart

- A macOS panic report from 2026-09-19 records a watchdog timeout after `watchdogd` missed check-ins for 92 seconds. At the snapshot the compressor was at 100% of its segments limit, 44 swapfiles were present, and only 904 16 KiB free pages remained. An agent-descended `python3.11` task had 56,261,951,536 recorded resident bytes and had run for 144.96 seconds; the panic report omits its command line, so exact-command attribution is not claimed.
- This is nevertheless consistent with the pre-restart Laguna safety failure and means the 2-second in-process guard is not adequate protection for this allocation pattern. **Do not rerun the current TurboQuant/tqTe Laguna path on this Mac.** Full evidence: `results/raw/EXP-010-laguna-long-context/POSTMORTEM-2026-09-19.md`.

## EXP-016 — Small-active MoE feasibility tournament

- **Scope/result:** runtime feasibility only; coding and research-quality evaluations were not run. All three required candidates were processed in order under single-resident, loopback-only conditions. Full report: `results/raw/EXP-016-small-moe-feasibility/REPORT.md`; machine-readable table: `comparison.json`.
- **ERNIE:** community MLX 4-bit rapid-mlx projected a 17.2 GB working set on this 16 GB host and was stopped before inference. The acquired GGUF Q4_K_M fallback produced repeated Metal `Insufficient Memory` / `llama_decode` failures with no response. No API/tool smoke was claimed.
- **Instella:** publisher llama.cpp branch Q4_K_M emitted a short four-token standalone result, but the longer arm reached 9% free memory and 9,438.19 MiB swap. It was safety-stopped; no Q3 escalation or quality test ran.
- **North:** available 4-bit artifacts were gated out by practical size; the pinned unsloth UD-Q3_K_M GGUF loaded and completed CPU-only standalone and server/API tests with `--n-gpu-layers 0 --cpu-moe`. Standalone ctx 256 measured 6.7 prompt / 11.2 generation tok/s for an 8-token arm. Loopback server health was HTTP 200; first fixed chat took 19.572 s and warm repeat 1.102 s with 116/121 cached tokens. Server metrics reported 13.0999 prompt and 8.3201 predicted tok/s.
- **Context/tool evidence:** a 2,740-token needle was allocatable/completable/correct on warm retry, but cold prefill took 179.798 s. A compact direct native terminal-tool call passed, its exact executor result was returned, and the final continuation ended `finish_reason=stop`. A full realistic Hermes prompt/turn was not run; this is not a production promotion.
- **Decision:** the only runtime survivor is North UD-Q3_K_M in experimental CPU-only mode. The next intelligence test is a full realistic Hermes native-tool turn followed by the separately authorized quality batteries; neither belongs to EXP-016.
- **Residency/storage:** FAST and DEEP remained down; after cleanup the North port was unreachable and no custom model process remained. Final observed swap was 2,406.50 MiB and memory-pressure free was 77%. Storage receipt and hashes: `results/raw/EXP-016-small-moe-feasibility/storage-receipt.json`.

## EXP-017 — ERNIE Q4 streamed-MoE expert-slot residency ladder

- **Measured result:** fixed `-ub 2`, 3,982-token populated input, and 8,192 context: 18-slot prior baseline 5.0 prompt / 4.0 decode tok/s; new 22-slot 6.1 / 4.6; 26-slot 6.9 / 5.6; 30-slot 8.0 / 6.0. The 30-slot arm is 1.60× prompt speedup versus 18 slots.
- **Safety:** all new arms exited 0 with 0 MiB swap increase and 0 swapouts. Minimum free memory declined 32% → 26% → **20%** at 22/26/30 slots; therefore 34 and optional 38 were not run. FAST/DEEP were down and no ERNIE/llama process or listener remained after cleanup.
- **Interpretation:** resident slots materially help but are insufficient for safe operational promotion on this 16 GiB host. CLI cache hit/miss/load/eviction stats were unavailable even after inspection of existing diagnostics; Darwin process disk reads fell 1.249 TB → 1.014 TB → 0.772 TB across new arms, supportive but not expert-attributed evidence. Deprioritize more low-level Q4 ERNIE optimization. Full evidence: `results/raw/EXP-017-ernie-streamed-gguf/EXPERT-SLOT-LADDER-REPORT.md`, `expert-slot-ladder-comparison.json`, and `expert-slot-ladder-4k/`.

## EXP-019/022/022b/023 — lane consolidation (earlier runs, summarized)

- **EXP-019:** Ornith-1.5-9B GGUF Q6_K + Q8_0 KV qualified as DEEP lane (decode 12.4–12.7 tok/s; prefill 145–172 tok/s; needle correct @61.9K; Hermes cold 78.5 s / warm 4.7 s @99% cache). Q5_K_M rejected on prefill.
- **EXP-022/022b:** MiniCPM5-2B promoted FAST/THINK (native tool calls, Paris ✓); MLX 4-bit Ornith regressed 11/16 vs Q6 14/16 on exact-answer suite — speed-only.
- **EXP-023:** MiniCPM5-1B rejected (3/4 real-Hermes failures despite 82–87 tok/s); Q4_0 K/V promoted at 64K (857 MB idle vs 2,787 MB F16).

## EXP-020 — TensorSharp + Gemma-4-E4B Q6_K DEEP promotion

- **Result:** Gemma-4-E4B Q6_K + MTP draft on TensorSharp ggml_metal **promoted as the DEEP lane** (2026-09-21). 11.1 tok/s decode; ~184 tok/s prefill through 15K; native tool loop + JSON PASS; radix cache 89–91% reuse on append-only Hermes turns. MTP spec decoding nearly halves effective ms/tok on populated turns (200.5 → 108.1 ms/tok, 59–64% acceptance).
- **Memory envelope:** 64K KV reservation via `MAX_CONTEXT=65536`; 15K prefill reaches ~10% free + 1.7 GB swap — populated deep context remains the binding constraint on 16 GB. Restart checkpoints (22.8 MB) are written but not restored: treat post-restart first big prompt as cold.
- **Rollout:** exact served id `gemma-4-E4B-it-Q6_K` wired across lane manager, root config, all profile alias maps/providers, research runner (deep/super → DEEP), and user tooling; Ornith Q6 retained as instant rollback.
- **Evidence:** `results/raw/EXP-020-tensorsharp-gemma4-e4b/` (PROGRESS.md, bench/, logs/, gen-test JSON, release.json).

## EXP-025 — Nemotron-3-Nano-30B-A3B Gate 0

- **Decision:** **not a candidate on this 16 GiB Mac** (2026-09-21). Smallest credible 4-bit releases are 17.8–24.6 GB weights — above physical unified memory before any runtime workspace. No download, no inference. KV is not the blocker (0.75 GiB @128K FP16 hybrid-Mamba bound); weight residency is. Needs ≥24/32 GB hardware. Report: `results/raw/EXP-025-nemotron3nano-gate0/REPORT.md`.

### EXP-015 arm — oMLX 8K admission check (Nemotron 3 Nano)

- **Measured admission result:** the isolated oMLX 0.7.0.dev4 / MLX 0.32.2 server rejected a one-request, 8,099-token arm for pinned `mlx-community/NVIDIA-Nemotron-3-Nano-30B-A3B-4bit` in **0.01 s** with HTTP **507**: its **17.38-GB** checkpoint exceeded the current **11.84-GB** Metal cap. The experiment used `moe_expert_offload_enabled=true`, a 12-GB memory guard, and 8-GB paged SSD-cache limit, but admission accounting rejected the complete checkpoint before expert offload could run.
- **Safety and interpretation:** swap used, `vm_stat` pageouts, and swapouts had zero delta. There was no model load, prefill, generation, or Hermes integration result. A focused expert-offload unit suite passed 46 tests, which verifies code-path health but does not prove this model can be admitted. **Decision:** do not promote oMLX's expert-streaming claim to a viable Nemotron-3-Nano path on the 16-GB M3. A temporary Metal working-set-cap change is a privileged separate experiment requiring explicit approval. Reviewed evidence: `results/raw/EXP-015-github-runtime-dive/ARM-8K-RESULT.md` and `VERIFIED-REASSESSMENT.md`.

