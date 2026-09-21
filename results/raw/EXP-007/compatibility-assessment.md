# EXP-007 — Carnice/Qwen3.6 Compatibility Assessment

**Status:** Phase 1 freeze and Phase 2 remote metadata/tensor compatibility analysis complete. No Carnice model artifact was downloaded, no Slipstream source/configuration was modified, and no Carnice inference was launched.

## Pinned identities

| Item | Identity |
|---|---|
| Existing operational reference | `mlx-community/Qwen3.6-35B-A3B-4bit` @ `38740b847e4cb78f352aba30aa41c76e08e6eb46` → verified `qwen36.gturbo` |
| Existing runtime | `dwijenpatel/slipstream` @ `3a892465729406944778a24064664d817617f558` |
| Carnice evaluated | `samuelcardillo/Carnice-Qwen3.6-MoE-35B-A3B` @ `d86a0cea3cd6794a294ad72a08598294249c761e` |
| Canonical base used for tensor comparison | `Qwen/Qwen3.6-35B-A3B` @ `995ad96eacd98c81ed38be0c5b274b04031597b0` |

The Carnice card identifies Qwen/Qwen3.6-35B-A3B as its base; it describes Stage A reasoning repair (Stratos/NuminaMath) and Stage B Hermes/agent traces (including `kai-os/carnice-glm5-hermes-traces`), each with rank-64 QLoRA targeting Q/K/V/O. Those are author claims, not capability results.

## Frozen EXP-005 reference

`stock-reference-freeze.json` records pointers and hashes without copying or touching EXP-005.

* Slipstream commit and source/build references are pinned above.
* The stock `.gturbo` manifest SHA-256 is `bfaa17cbca7755969c9a1e02216b5bb28f55701529c0f07dafbc07080517badd`; all 40 packed-expert file hashes and resident/tokenizer file hashes are recorded in the freeze.
* Reference configuration: 16 expert slots, 4,096 context, automatic prefill chunk, `temperature=0`, `seed=12345`; loopback Chat Completions/SSE/function-tools; `exp005` profile.
* Clean results retained: 0 MiB swap growth through the prefill/decode sweep; 5-token decode 8.778 tok/s and 1,105-token decode 7.531 tok/s. The clean Hermes `terminal(date)` turn had 5,003 cold prompt tokens / 107.87 s TTFT and a 5,052-token reused prefix / 4.50 s follow-up TTFT.

## Architecture and format compatibility

| Component | Stock Qwen3.6 / EXP-005 source | Carnice | Reusable unchanged? |
|---|---|---|---|
| Architecture | `qwen3_5_moe`; 40 layers | `qwen3_5_moe`; 40 layers | **Yes** at architecture level |
| Hidden / attention | hidden 2048; 16 Q heads; 2 KV heads; head dim 256; hybrid 30 linear + 10 full attention | Same values and layer pattern | **Yes** |
| MoE | 256 routed experts; top-8; expert and shared-expert intermediate 512 | Same | **Yes** at shape level |
| Tensor namespace/shape | MLX 4-bit source, 1,045 logical tensors | BF16 merged release, same 1,045 tensor names and all 1,045 shapes | **Yes** semantically; **not directly** at source-layout level |
| Routed experts | MLX affine 4-bit → existing 40 packed expert files | BF16 release tensors | **Unproven**; requires corrected BF16 samples plus stock quantization/packing equivalence |
| Attention Q/K/V/O | Existing quantized resident bundle | BF16 merged tensors; all 40 runtime-applicable targets must be treated as candidate replacements | **No** |
| Router gates | Existing quantized resident bundle | Shapes match; content not yet validly compared | **Unproven** |
| Shared expert | Existing quantized resident bundle | Shapes match; content not yet validly compared | **Unproven** |
| Embeddings, LM head, norms | Existing quantized resident bundle | Shapes/dtypes match; content not yet validly compared | **Not yet safe to reuse as a whole bundle** |
| Tokenizer | Same 248,320 vocab / 262,144 context contract | Same contract | **Likely**, but artifacts/template differ |
| Chat/tool template | Stock Jinja SHA-256 `e84f…4259`, 7,764 bytes | Carnice Jinja SHA-256 `55d4…ea0c`, 8,057 bytes | **No** — template must be treated as model-specific until rendered tool-call equivalence is tested |

## Tensor evidence — correction

Complete headers from the canonical base and Carnice BF16 releases contain **1,045 / 1,045** matching logical tensor names, and every matching tensor has the same shape. This remains valid architecture evidence.

The earlier byte-range sampling records are **invalid**: the scripts omitted the SafeTensors header length when translating a tensor `data_offsets` pair into its absolute HTTP range. They must not be used to claim expert, router, norm, or attention equality. `sparse-range-preacquisition-report.md` records the corrected address formula and replaces those claims with a planned stock conversion gate.

Accordingly, the current evidence supports architecture compatibility and the publisher's stated Q/K/V/O target scope, but does **not yet** prove that Carnice expert data are byte-identical to canonical Qwen or that the installed MLX/`.gturbo` expert store can be reused.

## Slipstream adaptation finding

This is not a manifest-only extension:

* The committed installer has only two accepted model IDs and pins `qwen36` to the exact stock MLX repository/revision/index fingerprint.
* Its current remote planner expects MLX quantized tensors and sidecars (`.weight`, `.scales`, `.biases`) in the stock Qwen namespace; Carnice's published BF16 checkpoint uses merged Hugging Face tensor names and fused routed-expert tensors.
* The current importer therefore cannot safely consume Carnice by changing only a repo ID. Using the stock manifest while silently inserting Carnice resident tensors would be invalid and is rejected as a design.

## Decision at this gate

**Do not download Carnice or modify Slipstream yet.** Runtime efficiency is likely to remain close only if a clean representation-preserving overlay/import path exists, but that has not been demonstrated.

The smallest defensible next experiment is a **non-inference import-compatibility spike**, after explicit approval for any source acquisition:

1. Verify whether the publisher provides an MLX affine-4bit Carnice checkpoint or separately publishes the merged LoRA adapters. Either could reduce the importer scope materially.
2. If neither exists, make an isolated EXP-007 source extension that accepts the BF16 Carnice layout and produces a distinct `carnice-qwen36.gturbo` manifest; do not change stock selectors/files.
3. Reuse stock packed expert files only after comparing a deterministic, broad set of quantized expert records from the proposed importer with the frozen EXP-005 files. Otherwise repack the experts into the separate artifact.
4. Quantize/import the changed resident tensor set under the exact EXP-005 affine settings, preserve Carnice's own template, and then run standalone correctness before any server/Hermes test.

At the current 48 GiB raw free-space snapshot, a full 67 GB BF16 acquisition cannot fit under a conservative reserve; the 34 GB FP8 form is not evidence of compatibility with Slipstream's MLX-affine importer. The GGUF releases are a different runtime/quantization path and do not answer reuse of EXP-005 artifacts.

## Artifacts

* `stock-reference-freeze.json`
* `metadata-acquisition-summary.json`
* `source/` (raw pinned Hub metadata, config/template/model-card evidence, and SafeTensors headers)
* `tensor-compatibility.json`
* `expert-byte-range-samples.json`

No project-wide state/result/decision document has been updated because the experiment has not yet established a runtime or capability result.
