# EXP-007 — Sparse Range Import Pre-Acquisition Report

**Status:** planned; no multi-byte Carnice tensor range has been acquired or persisted. Three one-byte transport probes were fetched only to validate range addressing and are recorded as hashes, not retained as model data. This report changes the proposed import spike from full-checkpoint acquisition to a conservative sparse-range path.

## Pinned source and discovery scope

| Field | Value |
|---|---|
| Carnice source | `samuelcardillo/Carnice-Qwen3.6-MoE-35B-A3B` @ `d86a0cea3cd6794a294ad72a08598294249c761e` |
| Source representation | Root BF16 SafeTensors only; FP8 and GGUF excluded |
| Metadata acquired | Index/tree, `config.json`, tokenizer config/template, model card, and every root SafeTensors header |
| Full source checkout | Not downloaded |

## Exact target enumeration

The published training targets are Q/K/V/O projections. The Carnice SafeTensors headers contain **44** such projection tensors:

- **40** main-model tensors: four Q/K/V/O projections in each of the ten full-attention layers (3, 7, 11, 15, 19, 23, 27, 31, 35, 39).
- **4** MTP-layer tensors.

The frozen stock MLX source and present Slipstream runtime contain **no MTP tensors**, so the first hybrid runtime scope is the 40 main-model tensors. The four MTP tensors remain recorded in the full manifest but are explicitly out of scope rather than silently discarded.

| Scope | Tensor count | Exact Carnice BF16 bytes |
|---|---:|---:|
| All declared Q/K/V/O training targets | 44 | 599,785,472 bytes (572 MiB) |
| Current Slipstream runtime-applicable targets | 40 | 545,259,520 bytes (520 MiB) |

The 40 targets span ten Carnice shards. The complete shard names, SafeTensors header offsets, and correct absolute HTTP byte ranges are in `sparse-range-manifest.json`.

## Range retrieval verification

For a selected target tensor, three independent one-byte requests at its **actual data byte** were sent through the pinned Hugging Face resolve URL. Each followed the Xet bridge redirect, returned HTTP **206**, returned exactly one byte, and produced the same SHA-256. Xet did not forward `Content-Range`/`Accept-Ranges` headers to this client, so the evidence is status/body-length/repeatability rather than those header fields.

The correct SafeTensors calculation is:

```text
absolute HTTP data start = 8 + safetensors_header_length + tensor.data_offsets[0]
absolute HTTP data end   = 8 + safetensors_header_length + tensor.data_offsets[1] - 1
```

This establishes a working sparse byte-range transport path. It does not yet establish large-range retry behavior; the stock conversion gate will do so before any Carnice tensor-range acquisition.

## Generated-artifact and disk estimate

The 40 corresponding frozen-stock MLX quantized records occupy exactly **153,354,240 bytes** (U32 packed weights plus BF16 `.scales` and `.biases`). The stock `.gturbo` logical artifact is **19,546,491,213 bytes**, including a **1,389,476,096-byte** resident `model_weights.bin` and 40 packed expert files.

| Item | Logical / transferred size | Physical-disk implication |
|---|---:|---|
| Sparse Carnice BF16 fetch | 545,259,520 bytes | Required sparse cache/input; no 67 GB source checkout |
| Replacement MLX-affine records | 153,354,240 bytes | Changed resident records only |
| Hybrid derivative, logical size | approximately stock `.gturbo` size, 19,546,491,213 bytes | Separate manifest/model identity; expert files can be hardlinked read-only |
| Conservative construction workspace | ~2.06 GB | 520 MiB sparse source + 146 MiB generated records + one complete 1.294 GiB resident-file rewrite, excluding small metadata and reserve |
| APFS clone/COW target | ~0.67 GB incremental before metadata/reserve | Only if a verified clone-and-rewrite method preserves unchanged resident extents; this must not be assumed for the first build |

**Conclusion:** the sparse path eliminates the need for the 67 GB BF16 checkout. It does not make the final derivative logically small: a complete self-contained `.gturbo` directory still has stock-like logical size, though expert files can be shared safely only after the conversion gate proves equivalence.

## Required stock conversion gate — not yet passed

Current Slipstream does **not** quantize BF16; it copies an already-quantized MLX affine representation. Therefore “run BF16 through the exact same Slipstream quantization path” is not currently possible—the exact runtime import path begins after quantization.

The next isolated validation must identify and pin the MLX affine group-64 quantizer that produced `mlx-community/Qwen3.6-35B-A3B-4bit`, then demonstrate:

1. representative stock BF16 Q/K/V/O range → pinned quantizer → MLX U32/scales/biases → exact frozen stock record equality;
2. representative stock BF16 routed-expert tensors → same quantizer → exact corresponding bytes/records in frozen packed-expert layer files;
3. deterministic repeat and bounded retry/hash behavior for multi-megabyte ranges.

If that gate fails, sparse Carnice payload acquisition is blocked; reuse of the EXP-005 expert store is not justified.

## Correction to earlier EXP-007 byte-comparison evidence

The first EXP-007 range scripts omitted the SafeTensors header length when translating `data_offsets` to HTTP ranges. Consequently, the reported byte-equality samples in `tensor-compatibility.json` and `expert-byte-range-samples.json` are **invalid** and must not be used to claim expert or attention equality. The architecture, tensor-name/shape, and model-card findings remain valid. This report uses the corrected addressing formula; no revised multi-byte Carnice tensor comparison has been run before the requested pre-acquisition report.
