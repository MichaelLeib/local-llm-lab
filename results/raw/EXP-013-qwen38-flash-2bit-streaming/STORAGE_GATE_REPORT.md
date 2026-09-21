# EXP-013 — Qwen3.8-Flash-Next 2-bit expert streaming
## Storage and resident-memory gate

**Date:** 2026-09-18  
**Status:** `stopped_before_download_and_inference`

## Hypothesis

2-bit routed-expert compression might cut Flash-Next's streamed bytes per output token enough to exceed 4.0 tok/s at native top-10 on the 16 GB M3.

## What was checked

- Exact Hugging Face revision: `9e5c4343ab3a3917100c94e1b0dd39dea617faab`.
- Exact TurboQuant-MLX source already isolated for EXP-010: `d1c34c63bc99f5744f409868b198cc692b84b65c` (2026-09-17), package version `turboquant-mlx-full 0.27.0`.
- Live APFS immediate free space, existing payload inventory, local-model process/lane state, model-tree file metadata, and runtime streaming implementation.
- No model bytes were downloaded; no local model was loaded; FAST and DEEP were down.

## Disk result

At measurement time, raw APFS immediate free was **61,603,139,584 bytes (57.37 GiB)**. The pinned model tree totals **56,757,557,995 bytes (52.860 GiB)**, including eleven text shards and the 897,899,165-byte bf16 vision tower.

A theoretical direct, single-copy acquisition would leave **4,845,581,589 bytes (4.513 GiB)**. That is already below a modest 10 GiB operational reserve by **5,891,836,651 bytes (5.487 GiB)** and does not budget resumable-transfer metadata/cache, telemetry artifacts, or normal macOS working headroom. Any temporary duplicate/repack would require additional space. Therefore the acquisition cannot proceed safely on the current volume.

### Largest obvious space candidates — no deletion authorized

| Payload | Logical size | Why it is not deleted |
|---|---:|---|
| EXP-006 native 4-bit Qwen3.8 Flash-Next control | 162.02 GiB | Explicitly protected 4-bit control and reproduction evidence. |
| EXP-007 stock-hybrid-control | 18.36 GiB | Existing Qwen3.6-derived control; no deletion permission. |
| EXP-007 Carnice hybrid | 18.36 GiB | Existing derived experiment artifact; no deletion permission. |
| EXP-005 Qwen3.6 Slipstream control | 18.21 GiB | Established Qwen3.6 baseline; preserve. |
| DEEP Bonsai HF cache | 7.94 GiB | Current managed-lane payload; no deletion permission. |
| Ollama store | 2.72 GiB | User payload; no deletion permission. |

There is one non-purgeable macOS update APFS snapshot. It is not a removable model payload and was not altered.

## Independent resident-memory stop

The disk gate is sufficient to stop. Separately, the candidate's own pinned model card and the checked runtime planner partition this model as follows with `--ngram-offload`:

- total text weights: 55.84 GB;
- streamable experts: 33.97 GB;
- **non-expert resident weights: 21.86 GB**;
- n-gram/PLE table: 19.20 GB, moved from wired Metal memory to memory-mapped/page-cache-backed disk by `--ngram-offload`.

TurboQuant's `load_streaming()` loads non-expert tensors first and only replaces `switch_mlp.{gate,up,down}_proj` with byte-budgeted `StreamingSwitchLinear` readers. It computes `resident_bytes = model_bytes - expert_bytes - offloaded_ngram_bytes` before allocating the expert cache. Thus `--ngram-offload` does preserve PLE offload semantics, but it does **not** stream the 21.86 GB dense/attention/router/shared-expert remainder. That remainder alone exceeds this Mac's 16 GiB unified memory before any expert cache, KV/state, activations, or OS workload.

The published streamed configuration is 34.4 GB peak with a 12 GB expert cache; it is not a 16 GB configuration. A 1–2 GB cache cannot fix a non-expert resident floor above physical RAM. Launching it would violate the lab's safety rule, so this is not a throughput or quality result.

## Verified runtime/provenance facts

- Architecture support is explicit: vendored `qwen4_exp`, 48 layers, 512 routed experts, native top-10, Gated DeltaNet + QSA, QSA indexer cache, and PLE/n-gram support.
- Representation from the pinned card: 4-bit TurboQuant attention/core/lm_head, 2-bit TurboQuant routed experts (g64), 2-bit affine token + PLE/n-gram table (g32); routers, QSA indexer, and hyper-connection gating are protected full precision. MTP is dropped.
- `--ngram-offload` uses `HostShardedEmbedding` memory-mapped shards and leaves the PLE table out of the wired model allocation. The code documents bit-identical output.
- Expert streaming is wired for exact MoE projections: `load_streaming()` replaces quantized expert projections with `StreamingSwitchLinear`, uses a process-wide byte-budgeted LRU, `os.pread`, F_NOCACHE when the full model is too large for RAM, coalesced reads, and exposed cache/byte/read-run telemetry. The exact native-routing setting requires `--max-active-experts 0`; the runtime default is quality-changing top-k 4 and is explicitly excluded from this experiment.

## Decision

**Stop EXP-013 before download and inference.** The candidate is not feasible in the requested 16 GB TurboQuant streaming configuration because both the safe disk gate and the runtime's irreducible resident-memory floor fail. No claim is made about decode speed, quality, PLE traffic, or Hermes suitability.

A reopen requires (1) at least 5.49 GiB more immediate free space just to preserve a 10 GiB post-download reserve, plus any measured transfer scratch, **and** (2) a materially different representation/runtime that proves a non-expert resident footprint below the machine's safe operating budget. Deleting existing artifacts alone does not solve the latter constraint.
