# EXP-005 compatibility and resource gate

Date: 2026-09-17

## Decision

**Source/runtime gate and native model install: pass. First standalone probe: pass. Model download and repack completed; Hermes integration and stable benchmark phases have not started.**

Slipstream natively supports the pinned Qwen3.6-35B-A3B family. It does not consume the existing GGUF files and should not be replaced by a converted Ornith/Gemma artifact. The native path downloads byte ranges from the pinned MLX safetensors source and writes a `.gturbo` directory with page-aligned expert files and verified metadata.

## Provenance

- Repository: `https://github.com/dwijenpatel/slipstream`
- Pinned commit: `3a892465729406944778a24064664d817617f558`
- Commit title: `README: rewrite from the pain point, with charts, a latency deep-dive, and the rejected ideas`
- Isolated checkout: `results/raw/EXP-005/source/slipstream/`
- No local source modifications.

## Supported model and representation

- Model selector: `qwen36`
- Source repository: `mlx-community/Qwen3.6-35B-A3B-4bit`
- Source revision: `38740b847e4cb78f352aba30aa41c76e08e6eb46`
- Approximate ranged download: `19,529,025,048` bytes
- Installed `.gturbo` estimate: `19,546,491,213` bytes
- Required free reserve: `1,073,741,824` bytes
- Existing local Qwen3.6 checkpoint: none found
- Reuse of Ornith/Gemma artifacts: no; architectures and formats are different

The pinned source config and Slipstream cross-check agree on: `qwen3_5_moe`, hidden size 2048, 40 layers, 256 experts, top-8 routing, 512 expert intermediate size, 30 linear-attention layers, 10 full-attention layers, Qwen/NeoX partial rotary settings, 4-bit affine group-size-64 weights, and 262,144 source context positions.

## Runtime prerequisites

- macOS 26 or newer: **pass** (`27.0`)
- Swift 6.2 or newer: **pass** (`Apple Swift 6.4`)
- Metal runtime: source compiles against the installed macOS 27 SDK
- Xcode app: not present in the active developer path; `xcodebuild` is unavailable
- Command-line/server products: **built successfully** with Command Line Tools
- Optional SwiftUI app: **not built successfully** because `SwiftUIMacros` is unavailable under CLT-only toolchain
- Source test suite: **not green under CLT-only toolchain** because `TestingMacros` is unavailable; this is recorded in `server-tests.log`

## API and Hermes relevance

The isolated server binds to `127.0.0.1` and implements:

- OpenAI Chat Completions JSON and SSE streaming
- Anthropic Messages JSON and streaming
- system/developer/user/assistant/tool messages
- OpenAI function tools and Qwen tool-call parsing
- one request at a time with a bounded queue
- single-prefix in-process KV reuse across exact history extensions
- standalone CLI disk KV snapshots via `--kv-snapshot`

The server does not implement the Responses API, structured JSON output, image input, batching, or model switching. It does not execute tools; Hermes remains the executor and must perform the tool loop.

The following resource snapshot was captured before the model download and remains the formal pre-install gate record:

- Machine: MacBook Air Mac15,13, Apple M3, 16 GiB unified memory
- Free disk: `56 GiB` in `df -h /`; exact available blocks `59,243,948 KiB`
- Swap used: `2,350.38 MiB`
- Memory-pressure query: `60%` system-wide free
- Slipstream/llama/MLX model processes: none
- Existing EXP-003 and EXP-004 artifacts: preserved

Disk capacity is sufficient for the estimated `.gturbo` install plus the 1 GiB runtime reserve, with approximately 37.3 GiB remaining before the existing source build and other activity. The disk gate is therefore a pass, but the first inference baseline should not be claimed clean while swap is already above 2 GiB.

## Build verification

The following products exist and are executable:

- `.build/release/slipstream-repack`
- `.build/release/slipstream`
- `.build/release/slipstream-server`

`--help` was exercised for all three products. Full package build failure is isolated to the optional Mac SwiftUI target. The CLT contains the TestingMacros dylib; an explicit plugin path was sufficient to get past that macro lookup, but the full package still stops at SwiftUIMacros. No test pass count is claimed.

After explicit approval, the native ranged install completed and verified successfully. The next controlled action is stable prefill/decode and KV-snapshot measurement, followed by a loopback server test. Do not start Hermes or change defaults until those standalone measurements are recorded.
