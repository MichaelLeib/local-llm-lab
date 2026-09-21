# EXP-015 Arm: Nemotron 3 Nano / oMLX / 8K admission

**Classification:** `invalid_configuration` — rejected before model-weight allocation, prefill, or decode.

## Frozen inputs

| Item | Value |
|---|---|
| Runtime source | `jundot/omlx` @ `95d5bf0b613098726de5f992d8085a311d9da39b` |
| Runtime | oMLX `0.7.0.dev4`; MLX `0.32.2`; mlx-lm `0.32.0` |
| Model | `mlx-community/NVIDIA-Nemotron-3-Nano-30B-A3B-4bit` @ `832f602eba5d22436c258c1462bdedc5afddb42b` |
| Local checkpoint footprint | 17 GiB (`du`); Hub metadata: 17,792,505,784 bytes |
| Context request | 8,099 prompt tokens by local tokenizer; 32-token generation cap |
| Expert settings | `moe_expert_offload_enabled: true`; resident fraction `0.125` |
| Server isolation | `127.0.0.1:8925`, one request, no Hermes profile rebinding |
| Safety settings | oMLX `--memory-guard-gb 12`, 16 initial KV-cache blocks, 8 GB paged-SSD-cache limit |

## Verification before the arm

- The oMLX CLI initialized in an experiment-local `uv` environment; it did not modify the proven Hermes lane.
- The focused expert-offload suite passed: **46 passed, 3 deselected in 13.53 s**.
- The downloaded directory contains the pinned local checkpoint and `hf download` completed successfully.
- The request fixture was built with the checkpoint's tokenizer. The initial token-count implementation accidentally measured a returned mapping (`2`) rather than token IDs; it was corrected before the live request. The final fixture is documented in `request-8k-manifest.json`.

## Measured admission result

The server returned HTTP **507** in **0.01 s**:

> Model `mlx-community--NVIDIA-Nemotron-3-Nano-30B-A3B-4bit` (17.38GB) does not fit under the `metal_cap` memory ceiling (11.84GB).

The same oMLX log records Apple’s recommended Metal working-set ceiling of **11.8 GB** and intentionally leaves it unchanged because `iogpu.wired_limit_mb` is unset. Therefore the server rejected the full checkpoint before its MoE-offload path could open the expert store; the current admission accounting uses the full 17.38-GB checkpoint for this model.

### OS deltas around the rejected request

| Signal | Before | After | Arm delta |
|---|---:|---:|---:|
| Swap used | 1,671.25 MiB | 1,671.25 MiB | 0 MiB |
| `vm_stat` pageouts | 405,397 | 405,397 | 0 |
| `vm_stat` swapouts | 22,479,029 | 22,479,029 | 0 |
| Inference output | none | none | no load / prefill / decode |

A small free-page movement occurred while the server was running; it must not be attributed to model inference because the model loader did not run.

## Cleanup and lane state

- The oMLX server was explicitly stopped; port `8925` was verified closed.
- The experiment-local oMLX generated settings file was removed because it held a server auth secret. No secret value is retained in experiment documentation.
- During oMLX server startup, the pre-existing FAST auto-heal controller started `llama-server` for the MiniCPM fallback lane on `127.0.0.1:8901` (PID and log provenance captured separately). This did **not** overlap with a Nemotron weight load because oMLX rejected the request pre-allocation. No further local inference will be attempted while that lane remains resident.

## Decision

**Do not promote oMLX’s generic expert-streaming claim to a viable Nemotron-3-Nano path on this 16-GB M3.** In this exact source revision the model fails admission before offload reduces the projected resident set, so an 8K runtime measurement does not exist.

The next possible variable is a *temporary* Metal working-set-cap increase to at least 14,336 MB, followed by a fresh 8K guarded admission arm. That is a privileged system change and needs separate explicit approval. It remains an experimental path, not a recommendation: the 17.38-GB model already exceeds the 16-GB unified-memory budget, and a raised Metal cap cannot establish that SSD expert streaming or 64K/128K context will be usable.
