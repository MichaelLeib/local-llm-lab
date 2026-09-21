# Gate 0 — NVIDIA Nemotron-3-Nano-30B-A3B on 16 GiB M3 Air

**Date:** 2026-09-21  
**Decision:** **Do not advance to a local 64K/128K qualification run on this 16 GiB MacBook Air.**

## Question

Can `NVIDIA-Nemotron-3-Nano-30B-A3B` be the next local candidate for reliable autonomous coding/research with a 64–128K context window?

## Result

The model is a **good capability and long-context design**, but it is **not a viable local candidate on this machine**. Its smallest credible production-oriented 4-bit releases already exceed the entire 16 GiB unified-memory capacity before runtime workspaces, model-recurrent state, macOS, or a context cache are accounted for.

No model weights were downloaded and no new inference server was started for this gate.

## Evidence

### Model relevance

NVIDIA describes Nano as a 30B-total/3.5B-active hybrid MoE model: 23 Mamba-2+MoE layers and six grouped-query-attention layers. It advertises up to a 1M-token context (the stock HF configuration defaults to 256K due to VRAM requirements). Its published evaluation includes LiveCodeBench 68.3, SWE-Bench/OpenHands 38.8, BFCL-v4 53.8, and RULER-100 92.9/91.3/86.3 at 256K/512K/1M. These are vendor-reported results, not a Hermes qualification.

* NVIDIA model card: https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16

### Weight residency blocks the machine

| Runtime/form | Source-reported size or measured peak | 16 GiB Mac conclusion |
|---|---:|---|
| MLX Community 4-bit | 17.8 GB weights; 18.4 GB measured Metal peak on an M4 Max | cannot fit in 16 GiB, even with no usable headroom |
| llama.cpp Unsloth Q4_K_M | 24.6 GB file; 24.4 GB max RSS on an M4 Max | cannot fit |
| Smallest listed GGUFs in `unsloth/Nemotron-3-Nano-30B-A3B-GGUF` | Q2_K 16.85 GiB; Q3_K_S 18.26 GiB | even Q2_K exceeds physical unified memory and is not a responsible reliability baseline |

* Apple Silicon measurements and commands: https://github.com/ggml-org/llama.cpp/discussions/20421
* GGUF repository: https://huggingface.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF

The 17.8/18.4 GB MLX figure is from an M4 Max with 128 GB. It does **not** predict M3 throughput, but it decisively establishes that the 4-bit artifact alone has no 16 GiB-safe residency envelope.

### Context is not the blocker here

Using the published six attention layers, two KV heads, 128-dimension heads, and FP16 K/V, the attention KV lower bound is:

| Context | FP16 attention KV lower bound |
|---:|---:|
| 64K | 0.375 GiB |
| 128K | 0.750 GiB |

The hybrid Mamba design is therefore unusually favorable for long context: unlike the prior Qwen 35B-A3B test, *64–128K KV itself is not the dominant memory problem*. But recurrent state, compute buffers, runtime allocations, and macOS add further memory demand; they cannot make a 17.8–24.6 GB weight footprint fit into 16 GiB.

## Current-machine safety state

Read-only check at evaluation time: 16 GiB physical RAM; 3.23 GiB swap already in use with only 864 MiB swap free. TensorSharp is listening on the existing deep lane (`127.0.0.1:8919`). Therefore no resident-model swap or local inference test was started.

## Decision

**Not a Gate 1 candidate for this Mac.** A download/run would predictably force severe memory pressure and swapping, not produce a valid 64K/128K Hermes result.

`Nemotron-3-Nano-4B` is small enough to be useful as a *runtime/long-context mechanics* experiment (the same llama.cpp discussion reports 2.24 GB MLX 4-bit and 262K context), but it is not an equivalent replacement for a serious coding/research capability lane. Do not mistake its fit for a solution to the capability requirement.

To qualify the 30B-A3B model honestly, use a machine with at least 24 GB of unified memory for a constrained 64K experiment; 32 GB+ is the practical minimum for a stable 64–128K Hermes/tool loop with OS headroom. This is a planning estimate, not a measured qualification on that hardware.
