# EXP-005 runtime inspection

## Isolated runtime

Slipstream is a Swift/Metal package whose upstream target names remain `TurboFieldfare`. The relevant executable products are:

- `slipstream-repack`: ranged Hugging Face installer and `.gturbo` verifier
- `slipstream`: standalone prompt/messages CLI
- `slipstream-server`: loopback OpenAI/Anthropic API server

The package pins Swift tools 6.2, `swift-nio` 2.99.0, and allows `swift-transformers` from 1.3.0; the resolved package graph is preserved in the checkout's `Package.resolved`.

## Expert streaming

The runtime stores common model tensors in resident files and routed experts in page-aligned per-layer blobs. A configurable number of experts per layer remains in a bounded cache; misses are filled from SSD. The documented default is 64 slots per layer, with `lfu-aging` replacement. The published measurements warn that excessive slots can evict the macOS file cache and reduce throughput.

Prefill is chunked, with `auto` selecting up to 4,096-token chunks. This matters because each chunk rereads much of the expert pool. The CLI exposes `--prefill-chunk` and the server uses 4,096-token chunks.

## KV/prefix behavior

The CLI's `--kv-snapshot` writes the full state after a fresh prefill and restores it only when the exact prompt matches. The server has a separate single-prefix in-process cache. It verifies the runtime/model/template domain, tool definitions, token prefix, assistant turn, and continuation shape. It reports cached token counts and named miss reasons. A server restart loses this in-memory prefix; a tool/schema/domain change causes a cache miss.

Qwen3.6's linear-attention state is included in the snapshot and cannot be sliced by token; the server's prefix bridge therefore only accepts supported history-extension/tool-result shapes.

## API/tool path

The server uses OpenAI-style `tools` function definitions and emits `finish_reason: tool_calls` with JSON argument objects. It accepts tool results as `role: tool` messages. It explicitly does not execute tools. This is compatible with a dedicated Hermes profile using a single terminal tool, subject to Hermes's exact provider adapter and streaming parser behavior.

## Published evidence limits

Slipstream's published quantitative measurements are from a base M5 MacBook Pro with 24 GB RAM, macOS 26.5.2, and a 10-core GPU. They show mechanism plausibility but are not EXP-005 measurements on this M3 16 GiB Mac. Published claims include approximately 2.5 GB at 16 slots/27 tok/s, 5.6 GB at 64 slots/31 tok/s, and 14.3 GB at 192 slots/25 tok/s for a 2,940-token prompt, plus a reported 0.03-second exact-prefix CLI snapshot restore. All of these remain inherited evidence until reproduced locally.
