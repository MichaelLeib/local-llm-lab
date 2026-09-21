# EXP-003 Phase 1/2 compatibility gate

Date: 2026-09-17
Machine: Apple M3, 16 GiB unified memory, macOS 27.0
Project: `~/HermesProjects/Local-LLM-Lab`

## Decision status

The isolated implementation builds and appears structurally compatible with the official Ornith Qwen3.5-MoE architecture. The gate is **conditionally positive for the first-load test**. The approved 21.713 GB Q4_K_M GGUF is downloaded and hash-verified; no model inference has been launched for EXP-003.

## Chosen implementation

- Repository/fork: `https://github.com/kisasexypantera94/llama.cpp`
- Branch: `moe-expert-residency`
- HEAD: `41ec4c4e94fd5ff6c258691f35f2fcd0d3dde892`
- PR: `https://github.com/kisasexypantera94/llama.cpp/pull/2`
- PR base: `fda8528aa8c1d8ecb2a5cd2b6e85c43ef5425b6b`
- PR merge ref: `ab7abd4d8a062c0aa460ac40bac016db6004da2e`
- Fork branch is six commits ahead of the recorded PR base; the branch tag is `moe-expert-residency-b9368-41ec4c4`.
- Build source is isolated under `results/raw/EXP-003/source/llama.cpp-moe-expert-residency/`.

The implementation is the original Metal/SSD expert-slot PoC described in llama.cpp Discussion #23324. It uses compact per-layer Metal pools, a Metal interceptor kernel, shared CPU/GPU message buffers and events, `pread()` from the GGUF, and an LRU expert-to-slot mapping. The relevant controls are `--moe-n-slots`, `--moe-n-layers`, `--no-mmap`, and `--no-warmup`.

## Build result

Configuration:

```text
cmake -S . -B build -DGGML_METAL=ON -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel 4
```

Result: **success** on AppleClang 21 / arm64 / macOS 27 SDK. `build/bin/llama-server` and `build/bin/llama-cli` were linked. The build compiled `src/llama-moe-offloader.cpp`, `ggml-metal` and `models/qwen35moe.cpp`. Warnings were limited to macOS 27 Metal deprecations and a Dispatch nullability extension. The incremental rebuild log is `source/build-rerun.log`.

The isolated binary reports:

```text
MTL0: Apple M3 (12124 MiB, 12123 MiB free)
--moe-n-slots
--moe-n-layers
--no-mmap
--no-warmup
```

CMake 4.4.3 was the only additional package installed, because CMake was absent and required for the isolated build. The system/Homebrew `llama-server` was not modified.

## Upstream comparison

Homebrew upstream llama.cpp is 0.4.1, commit `b29c606e2`. It has `--cpu-moe` and `--n-cpu-moe`, but does not expose `--moe-n-slots` or `--moe-n-layers`; the current upstream tree has no `src/llama-moe-offloader.cpp`. Current upstream does recognize `qwen35moe`, but that architecture support is separate from SSD expert-slot paging.

The newer RFC at Discussion #24528 describes a persistent expert cache, but its proposed implementation is CUDA-only and uses a different CPU/GPU hybrid cache design. It is not a drop-in replacement for this Apple Metal SSD test.

## Ornith compatibility evidence

Official Transformers repository:

- Repo: `ornith-ai/Ornith-1.5-35B-A3B`
- Revision: `10fbf86fed7ecee4a061f8b499a618f46001cac1`
- `model_type`: `qwen3_5_moe`
- Architecture: `Qwen3_5MoeForConditionalGeneration`
- Main layers: 40
- Experts: 256
- Experts/token: 8
- Hidden size: 2048
- Routed expert intermediate size: 512
- Layer pattern: 30 linear-attention and 10 full-attention layers in the 40-layer main trunk
- Max position: 262144

Official GGUF repository:

- Repo: `ornith-ai/Ornith-1.5-35B-A3B-GGUF`
- Revision: `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`
- Q4_K_M: `Ornith-1.5-35B-Q4_K_M.gguf`, 21,713,463,040 bytes (20.222 GiB), Hub OID `c64b9535c518b1aa0fe44e46e808a3ea5f46c281`, LFS SHA-256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`
- Q5/Q6 were not downloaded or tested.
- The optional `mmproj` is not needed for the planned text-only test.

Source-level compatibility findings:

1. The offloader reads expert count from the tensor shape (`orig->ne[2]`), not a 128-expert constant.
2. It reads the per-expert stride from `orig->nb[2]` and uses `pread(file_offset + expert_id * stride)`, which is compatible with standard contiguous GGUF expert tensors if the Q4 conversion preserves that layout.
3. It indexes routed tensors by names containing `_exps.`, matching the fork's Qwen3.5-MoE tensor naming path (`ffn_gate_exps`, `ffn_up_exps`/fused gate-up, and `ffn_down_exps`).
4. The Qwen3.5-MoE loader creates routed tensors with shapes `[512, 2048, 256]` for down and a fused gate/up tensor with the corresponding 2x intermediate dimension.
5. The graph enables the offloader per main MoE layer and remaps selected expert IDs before Metal `MUL_MAT_ID`. It does not assume 40 layers, 256 experts or 8 experts/token in the offloader itself.
6. The implementation does assume one shared expert-to-slot mapping across all routed pools in a layer and assumes the slot count can cover the selected unique experts in the current microbatch.

Conclusion: **no source adaptation is indicated before the first-load test**. The material risks are GGUF tensor naming/layout, hybrid Qwen3.5 graph correctness, and runtime correctness under the fork—not an obvious hard-coded 128-expert or Qwen3-only limitation.

## SSD baseline

Non-destructive benchmark over the existing 4.98 GiB first shard of the local Ornith 9B 8-bit safetensors model, using `F_NOCACHE`:

- Sequential read: 5,346,606,498 bytes in 2.144 s = 2.322 GiB/s
- 8,192 deterministic random 4 KiB reads: 32 MiB in 0.229 s = 0.028 ms/read average, 139.6 MiB/s aggregate
- Artifact: `results/raw/EXP-003/ssd-baseline.json`

This is a local-file baseline, not a guarantee for the GGUF expert access pattern. The PoC performs parallel `pread()` calls for misses; actual throughput and latency must be measured during inference.

## Verified slot-memory model

Artifact: `results/raw/EXP-003/memory-model-estimate.json`.

The verified estimate uses the GGUF tensor descriptors: Q4_K/Q6_K block sizes, 41 expert layers in the file, 256 experts, hidden size 2048 and expert intermediate size 512. Exact conservative expert-pool allocation, excluding allocator overhead:

| Slots | Pool estimate | Source-level ubatch upper bound (`slots // 8`) | Preliminary risk |
|---:|---:|---:|---|
| 8 | 596.8 MiB | 1 | Preferred first load |
| 16 | 1.17 GiB | 2 | Candidate after correctness/safety |
| 24 | 1.75 GiB | 3 | Candidate after measurement |
| 32 | 2.33 GiB | 4 | Near ceiling; defer until measured |

The estimate is not a total-footprint prediction. Dense/non-expert weights, shared experts, recurrent state, KV/cache, compute buffers and Metal allocator behavior remain to be measured. The first run should use 8 slots, short text context, `--no-mmap`, `--no-warmup`, and minimal `ubatch=1` if the server exposes it. Do not start 16/24/32 automatically after a failure.

## Disk and safety gate

- Root free space before cleanup: 54.24 GiB.
- EXP-002 cache cleanup freed 16.8 GB; the verified Q4_K_M download completed with approximately 40 GiB free.
- Only Q4_K_M was downloaded; Q5/Q6 and the projector remain excluded.
- Preferred steady-state target: <=7.5 GiB; acceptable experimental target <=8.5 GiB; hard target approximately 9 GiB, inherited from EXP-002.
- No Hermes default or local lane configuration was changed. FAST and DEEP are down.

## Gate decision

**Phase 3 acquisition is complete.** The downloaded GGUF header, tensor descriptors and SHA-256 are verified. First launch should be the 8-slot configuration only; correctness and memory safety precede any slot sweep.
