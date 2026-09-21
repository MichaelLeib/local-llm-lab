# EXP-013 correction — resident accounting and remote plan

**Date:** 2026-09-19  
**Status:** `memory-feasible-on-paper; blocked-before-download-by-disk-reserve`

## Correction

EXP-013's previous "21.86 GB irreducible resident backbone" conclusion was wrong. It treated the n-gram/PLE table as disjoint from `resident_bytes`. In the pinned TurboQuant source, they overlap:

```text
resident_bytes = total_bytes - expert_bytes
ngram_bytes ⊂ resident_bytes
wired resident after --ngram-offload = resident_bytes - ngram_bytes
```

The current HF revision is still the requested pinned revision `9e5c4343ab3a3917100c94e1b0dd39dea617faab`.

## Header-only source accounting

Source: pinned TurboQuant-MLX `d1c34c63bc99f5744f409868b198cc692b84b65c`, `plan.py:140-158`, remote SafeTensors headers only. No candidate checkpoint data was downloaded.

| Component | Exact bytes | Decimal GB | Binary GiB | Relationship / residency |
|---|---:|---:|---:|---|
| Text model total | 55,838,786,104 | 55.839 | 52.004 | Complete text tensor set in the 11 model shards; vision tower is not in this planning total. |
| Routed expert projections | 33,973,862,400 | 33.974 | 31.641 | Subset of total; replaced by disk-backed streaming readers. |
| `resident_bytes` | 21,864,923,704 | 21.865 | 20.363 | `total - experts`; **includes** n-gram/PLE. |
| n-gram/PLE table | 19,200,092,160 | 19.200 | 17.881 | Subset of `resident_bytes`; memory-mapped/page-cache-backed with `--ngram-offload`. |
| **Wired resident after both mechanisms** | **2,664,831,544** | **2.665** | **2.482** | `resident - ngram`; core/attention/router/QSA/hyperconnection/etc. |

The key reconciliation is exact:

```text
55,838,786,104 - 33,973,862,400 = 21,864,923,704
21,864,923,704 - 19,200,092,160 = 2,664,831,544
```

## Remote planner result (16 GB, 8,192 context, n-gram offload)

Command executed from the pinned source via a temporary import shim:

```bash
python -m turboquant_mlx.plan \
  --model manjunathshiva/Qwen3.8-Flash-Next-tq4a-tq2e-g64 \
  --ngram-offload --context 8192 --ram-gb 16 --json
```

The current planner CLI has no revision flag. A separate HF API read confirmed `main` remains the required revision above.

Planner facts:

- 24,576 bytes/token KV; 201,326,592 bytes (192 MiB) at 8,192 tokens.
- 128-token selected prefill step; 83,099,648 bytes workspace.
- Verdict: `streaming`, `runnable: true`.
- Correct flags: `--streaming`, auto cache ~5.674 GB and cache-budget helper projected peak ~9.439 GB (8.790 GiB), `--prefill-step-size 128`.

### Planner reporting defect

`build_plan()` computes the verdict using `wired_resident = resident_bytes - ngram_offloaded_bytes`, correctly selects streaming, and uses `auto_cache_budget(wss, wired_resident, expert_bytes)`. However its public `projection.peak_bytes` uses `wired_weights = total_bytes - ngram_offloaded_bytes`, which still includes the entire on-disk expert bank. It therefore reports an inconsistent 37.923 GB "peak" and negative headroom while simultaneously declaring streaming runnable. That `projection.peak_bytes` is **not** a valid streaming peak.

The streaming-loader-consistent projections are:

| Expert cache | Peak formula | Exact bytes | Decimal GB | Binary GiB |
|---|---|---:|---:|---:|
| 1 GB | core + cache + 1.1 GB runtime + actual KV + workspace | 5,049,257,784 | 5.049 | 4.702 |
| 2 GB | core + cache + 1.1 GB runtime + actual KV + workspace | 6,049,257,784 | 6.049 | 5.634 |
| auto cache | helper's conservative 1.9 GB KV reserve | 9,438,713,661 | 9.439 | 8.790 |

These are planning projections, not local measured residency.

## Loader agreement

The actual pinned loader agrees with the corrected accounting:

1. `load_streaming()` calls `load_turboquant(... lazy=True, ngram_offload=True)`.
2. Before `_prepare_polar_layers()` or `model.load_weights()`, `offload_ngram_tables()` removes n-gram tensors from the lazy weight dictionary and replaces each NGramEmbedding with `HostShardedEmbedding`. This object holds NumPy memory maps, no MLX parameters, and is not wired.
3. The loader computes `resident_bytes = model_bytes - expert_bytes - offloaded_ngram_bytes(model)`.
4. It constructs one byte-bounded `ExpertCache` and swaps every quantized routed `switch_mlp.{gate,up,down}_proj` to `StreamingSwitchLinear` before inference. The replacement reads selected SafeTensors slices with `pread`; `F_NOCACHE` is selected automatically when the artifact does not fit RAM.
5. The top-k preservation requirement is met by `--max-active-experts 0`; the runtime default of 4 is excluded.
6. The source's lazy path does initially create MLX lazy objects for all shard tensors, but does not `mx.eval(model.parameters())` before the streaming swap. Static inspection supports no full expert-bank materialization; the first smoke arm must verify this with OS/MLX telemetry after a safe acquisition.

## Revised classification

**A — feasible on paper.** The corrected always-wired model core is about 2.665 GB, not 21.865 GB. With a 1–2 GB cache and bounded 128-token prefill, the corrected loader-consistent projection is well inside the 16 GB RAM envelope. EXP-013's architectural-wall conclusion is superseded.

## Remaining independent blocker: storage

Live immediate APFS free space is **64,361,140,224 bytes / 59.941 GiB**. The full candidate tree is **52.860 GiB** including the optional bf16 vision tower. A best-case direct single-copy acquisition would leave **7.081 GiB**, which is **2.919 GiB short** of a 10 GiB reserve before resumable-transfer/cache overhead. Therefore no acquisition or inference has begun.

Potential reclaim candidates require explicit authorization; none were changed:

| Candidate | Logical size | Notes |
|---|---:|---|
| EXP-007 stock-hybrid-control | 18.36 GiB | Existing control artifact. |
| EXP-007 Carnice hybrid | 18.36 GiB | Existing derived artifact. |
| EXP-005 Qwen3.6 Slipstream model | 18.21 GiB | Established baseline; preserve by default. |
| DEEP Bonsai cache | 7.94 GiB | Managed-lane model payload. |
| Ollama store | 2.72 GiB | User payload. |

EXP-006 Flash 4-bit control (162.02 GiB) remains explicitly protected. The prior Coder-Next raw QPACK is not present in the current inventory; no assumption or deletion was made.

## Next gate

After sufficient storage is made safely available through an authorized action, run only the original Stage 1 smoke: exact native top-10, `--ngram-offload`, streaming enabled, `--max-active-experts 0`, 1 GB expert cache, no MTP, no speculative decoding, bounded prefill. Capture the required OS/MLX/cache/PLE/I/O telemetry before any decode sweep.
