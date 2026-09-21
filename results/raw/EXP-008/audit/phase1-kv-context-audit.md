# EXP-008 phase-1 KV/context audit

**Audited source:** `dwijenpatel/slipstream` commit `3a892465729406944778a24064664d817617f558` in the frozen EXP-005 checkout.  EXP-008 has an independent git worktree at the same commit on branch `exp008-long-context`; no source change has been made.

## Architecture and exact FP16 KV size

The Qwen3.6 manifest has 40 layers: 30 Gated DeltaNet (`fullAttentionLayerMask == 2`) and 10 full-attention layers (`== 1`).  `KVCacheManager` allocates one shared page placeholder for the linear layers; their recurrent state is handled by `GDNStateManager`.  Only the 10 full-attention layers obtain growing K and V buffers.

The full-attention shape is 2 KV heads × 256 head dimension.  Each token therefore consumes:

```
10 full layers × 2 (K and V) × 2 KV heads × 256 elements × 2 bytes (FP16)
= 20,480 bytes/token = 20 KiB/token
```

Allocation is `maxContext × stride` independently for K and V in each full layer (`KVCacheManager.swift:125–140`).  In the current non-ring Qwen configuration, this gives 1.25 GiB at 65,536 and 2.50 GiB at 131,072, before GDN state, scratch, resident common weights, expert cache, and macOS/Metal accounting.

`MTLBuffer` allocations are shared-memory, demand-resident unified-memory allocations.  Allocation size must therefore be recorded separately from observed process physical footprint and the loaded-idle → post-prefill footprint delta. `reset()` issues `POSIX_MADV_DONTNEED` across the KV buffers, so a completed standalone request should not be assumed to retain the prior request's resident KV pages.

## Current 64K path

* `slipstream-server` accepts only `4096, 8192, 16384, 32768, 65536` (`ServerArguments.swift:80–85`). The 65,536 limit is an argument allow-list, not a model or Metal-index limit.
* The CLI accepts an arbitrary positive integer for `--max-context`; it already provides a non-server control for 128K boundary checks.
* Context and positions are Swift `Int` through `KVCacheManager`, `RealForwardRunner`, CLI/server admission, and prefill span planning. Attention validity/count information is dispatched as 32-bit unsigned values, not 16-bit positions. 131,072 is well below both `Int32` and `UInt32` limits.
* The prefill path rejects a span only if `startPosition + tokenCount > maxContext`; the default auto prefill chunk is bounded separately. The existing 4096-token chunking does not scale scratch allocation with the maximum context.
* `Sampler` receives position as `UInt32`; 128K is safe. The `UInt16` uses found in Metal/Swift are quantization/FP16 or tile-local values, not sequence-position storage.
* The Qwen path does not use the sliding-window FP16 KV ring. If it were enabled, `executePrefillChunk` has a capacity check based on `slidingWindow + chunkTokens`; this is not the active Qwen growing-full-attention path.

## 128K minimal change, deferred until the 64K envelope passes

The smallest server-support change is to add `131_072` to the `--max-context` allow-list and usage text in `Sources/TurboFieldfareServer/Core/ServerArguments.swift`, then add parser tests for acceptance/rejection.  The server, CLI, KV manager, request admission, prefill ranges, and 32-bit kernel arguments do not show another 65,536-specific guard in the audited paths.

Before any source edit, EXP-008 must demonstrate that 64K has acceptable physical-footprint and swap deltas with the identical model, 16-slot expert cache, `auto` prefill chunks, deterministic sampling, and one process at a time.  No KV quantization, expert-cache-slot change, or Hermes-default change is part of phase 1.

## Existing evidence and implications

* EXP-005 clean 4K controls reached 8.42 tok/s at 273 prompt tokens and 5.90 tok/s at 2,210 prompt tokens, with 0 MiB swap delta. They do not establish a 32K/64K envelope.
* EXP-005's isolated Hermes tool loop passed at an 8K server context, 6.9–7.1 decode tok/s, and 98.94% exact-prefix cache reuse. This validates the relevant API/cache mechanism but not long-context residency.
* EXP-007's locked v1 structural harness failed both candidate arms by exhausting a 16,384-token server context after 17–20 normal tool calls. This gives a concrete Hermes reason to characterize 32K/64K before attempting a broad agent task; it does not establish model quality or a long-context memory result.
* Published M5/24GB figures and the source profile's 24GB phase split are inherited evidence only. EXP-008 reports M3 measurements separately.

## Measurement design committed for phase 1

Each context arm fixes: pinned source/model, `--expert-cache-slots 16`, `--expert-cache-policy lfu-aging`, `--prefill-chunk auto`, temperature 0, seed 12345, loopback-only server, and one process. The only planned independent variable is `--max-context`.

The runner captures raw `vm_stat`, `memory_pressure -S -l warn -Q`, `vm.swapusage`, `footprint`, `vmmap -summary`, server/client logs, exit status, and parsed timing fields at baseline, loaded-idle, before/after each request, and after stop. It stops the arm when swap use grows more than its configured 256 MiB safety budget over that arm's baseline and preserves all partial records.
