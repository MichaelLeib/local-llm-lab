# Phase 0 — Laguna runtime and artifact survey

**Survey time:** 2026-09-18  
**Host:** MacBook Air `Mac15,13`, Apple M3, 16 GiB unified memory, macOS 27.0.  
**Scope:** source/config/model-host primary evidence; no performance assertion below is presented as a local result unless explicitly marked.

## Verified architecture/checkpoint contract

**Canonical model:** `poolside/Laguna-S-2.1` (OpenMDW-1.1).

The upstream `config.json` verifies:

| Property | Verified value |
|---|---:|
| Architecture / model type | `LagunaForCausalLM` / `laguna` |
| Context maximum | 1,048,576 positions |
| Layers | 48 |
| Attention pattern | 12 global full-attention layers; 36 sliding-window layers, window 512 |
| Hidden size / head geometry | 3,072; 48 Q heads; 8 KV heads; head dim 128 |
| Routed experts | 256; top-10 per token |
| Shared expert | yes; intermediate 1,024 |
| Routed expert intermediate | 1,024 |
| MoE / routing | normalized top-k probability, scaling factor 2.5 |
| RoPE | YaRN factor 128 on global layers, original 8,192; default RoPE on sliding layers |

The published 118B / approximately 8B-active figure is model-card metadata, not recomputed locally. Poolside positions S-2.1 for coding/long-horizon agent work; its official config establishes the exact implementation contract used here.

## Candidate 1 — TurboQuant-MLX (chosen first)

| Field | Evidence / value |
|---|---|
| Runtime | `https://github.com/manjunathshiva/turboquant-mlx` |
| Pinned source | `d1c34c63bc99f5744f409868b198cc692b84b65c` (`perf: 2-token forwards…`) |
| Installed runtime | source editable `turboquant-mlx-full` 0.27.0; Python 3.13.11; MLX 0.32.2; mlx-lm 0.31.3 |
| Exact artifact | `manjunathshiva/Laguna-S-2.1-tqTe-g64`, revision `5c08cd7e895257df166dece30405219af66034de` |
| Format | MLX SafeTensors; 3-bit TurboQuant always-on tensors, g64 Hadamard/codebook; routed experts ternary trit-packed (~1.58-bit); `expert_down_bits=null` |
| Remote download | 15 required files, 28,695,108,446 bytes; six model shards: 5.2, 5.3, 5.3, 5.3, 5.3, 2.2 GB reported by Hub dry-run |
| Planner tensor accounting | total 28,695,108,446 B; experts 26,415,726,592 B; resident trunk 2,279,381,854 B |
| Streaming method | `--cache-budget-gb` activates expert streaming; a bounded expert cache pages router-selected experts from SafeTensors. Native top-10 will be kept (`--max-active-experts 0`). |
| Context/KV | hybrid cache; planner reports 58,368 B/token FP16 at 8K and 50,304 B/token at 64K due sliding-window layers. K8 roughly halves 64K projected KV to 1.648 GB, but model-card guidance says not to use KV quantization for Laguna because most layers are sliding and it reduces decode. Exact vs compressed KV is an explicit later tradeoff, not a baseline assumption. |
| Prefix reuse | `turboquant-serve` has bounded in-memory prompt-cache controls plus `--disk-cache` persistent prefix checkpoints, including mid-prefill checkpoints. Must be measured after a safe standalone arm. |
| API/Hermes | loopback OpenAI Chat Completions via `turboquant-serve`; function/tool parsing is based on the Laguna GLM/XML path, including the shipped parser fix. It does not itself execute tools. Hermes feasibility remains unproven until a full round trip. |
| Metal/MLX | native MLX/Metal path. 16 GiB planner reports a 12.71 GB Metal working-set ceiling. |
| 16 GiB external evidence | Model-card M4 Mac mini streaming: 2/4/auto/8 GiB expert-cache budgets measured 1.15/1.26/1.36/1.58 tok/s at 5.31/7.32/9.23/11.35 GB peak. This is not a local result and is materially below the 4 tok/s target. |
| Qualitative caveat | The artifact’s claimed Opencode pass and 5.5/6 stress battery are author evidence, not a local Hermes or coding qualification. Reported weak point: arithmetic-distance reasoning. |

### Planner result on this M3

`turboquant-doctor` classifies the artifact as **streaming**, not resident. At 8K it recommends a 128-token prefill step and auto cache about 7.4 GB (runtime projection: cache peaks around 10.8 GB). At 64K, even K8 projects an unreconciled resident-style total 32.19 GB against a 15.46 GB usable ceiling; only the expert-streaming placement is plausible. Planner results guide launch flags, not safety claims.

## Candidate 2 — streamlx (comparison/control; not acquired)

| Field | Evidence / value |
|---|---|
| Runtime | `https://github.com/srcterm/streamlx` |
| Pinned source | `146507b59293058b3a1cecc43f47947b25012297` (2026-08-11, `readme updated`) |
| Maintenance | v0.1, API explicitly described as changeable; upstream MLX integration RFC still in preparation. It is substantially less mature than the selected runtime. |
| Exact reported Laguna artifact | `mlx-community/Laguna-S-2.1-oQ2e-fast`, 34.7 GB community imatrix / 2-bit-expert MLX artifact. No local copy exists and it is not representation-compatible with TurboQuant’s 28.7 GB ternary artifact. |
| Streaming | SafeTensor-range `pread`, span coalescing, fixed-budget LRU pool, next-layer routing prediction, expert-major prefill, optional S3FIFO, bounded MLX buffer cache. |
| Context/prefix | MLX prompt-cache LRU with a byte cap; no documented disk-persistent prompt-state cache.  Its own code notes hybrid caches can be non-trimmable, so valid history-extension reuse must be measured rather than assumed. |
| API/Hermes | loopback OpenAI-compatible Chat Completions; server controls include `--prompt-cache-gib`, but no documented tool parser or verified Hermes trace. |
| Metal/MLX | native MLX path; requires `mlx-lm` git main for its stated Laguna support. |
| Closest published hardware | M4 Air 32 GB, ~2.4 GB/s SSD: Laguna decode at 8/12/16/18 GiB expert budgets is 3.4/4.5/7.2/9.2 tok/s with 12/16/20/22 GB resident. Those are not transferable to 16 GiB: its lowest reported Laguna setting already consumes ~12 GB resident. |

## Runtime recommendation

**Test TurboQuant-MLX first.** It is the only surveyed route with (1) an explicitly published 16 GiB Laguna streaming measurement, (2) a 28.7 GB artifact that fits the present 36 GiB raw storage envelope without conversion, (3) verified Laguna support at the pinned current source/runtime, (4) bounded in-memory plus persistent disk prefix-cache machinery, and (5) a defined OpenAI/tool path suitable for a later Hermes qualification.

This is an evidence-led choice, not a prediction of success: the closest M4 16 GiB result is only 1.58 tok/s at the largest safe cache, so the 4 tok/s primary target is already **low-probability** on the slower M3. `streamlx` is retained as the control if TurboQuant’s local failure is primarily TQ kernel/quality behavior rather than the unavoidable 16 GiB cache envelope.

## Acquisition/storage gate

- Before acquisition: raw APFS `df`: 37,758,452 KiB = **36.0 GiB** immediately available; no lane/model process; FAST and DEEP down.
- Baseline: swap 2,709.94 MiB and memory-pressure free 67%. Swap is explicitly retained as baseline; only arm-local growth is judged.
- The model’s 28.695 GB decimal / ~26.72 GiB payload should leave about **9.3 GiB raw** before minor provenance/result files. This is tight but exceeds the model’s content plus experiment scratch needs; it does **not** allow a second model representation.
- Four local Time Machine snapshots exist. They were observed but are not being thinned, deleted, or bypassed because the raw available-space gate currently passes.
- Model acquisition was explicitly requested in the experiment brief and began only after the source build, plan/doctor checks, lane check, and storage gate. It writes directly into this experiment’s `model/` directory; no existing model/artifact is deleted or duplicated intentionally.

## Baseline launch contract (frozen before acquisition completes)

- One loopback-only, standalone stream process; FAST/DEEP stay down; no lane/default/profile config changes.
- Actual context: deterministic tokenizer-counted prompt target 6,144 tokens (within 4K–8K), greedy/no-think, top-p 0.9, native top-10 experts, 256 generated tokens.
- First arm: 4 GiB expert cache, FP16 KV, 128-token prefill chunks. This intentionally favors safety and records the cold cache behavior before any sweep.
- Safety guard: capture VM/pressure/swap/footprint/IO continuously and terminate as `stopped_for_swap` if arm-local swap grows >512 MiB, system free falls <20%, or swap climbs rapidly. No score is claimed if generation never starts.
- No DFlash/draft model, K-reduction, KV compression, source modification, context extension, or Hermes connection in the exact baseline.
