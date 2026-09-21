# EXP-020 — TensorSharp + Gemma 4 E4B as DEEP-lane runtime (replacing ornith/Bonsai plan)

**Date:** 2026-09-21 · **Gate:** experimental-runtime-gate (isolated runtime candidate)
**Status:** Investigation complete through gate step 5. **Awaiting user approval for weights download.**

## What was verified (all evidence-first, no model download)

### Provenance pin
- TensorSharp HEAD `75e427b2345f4c21ec4c47cd60e46e7b676b49d8` (2026-09-18, PR #220 merge); release **v2026.09.01** (2026-09-17) — active upstream, not abandonware.
- GGUF inventory pinned via HF API: `unsloth/gemma-4-E4B-it-GGUF` lastModified 2026-07-17, sha `bfc15c382204`; `ggml-org/gemma-4-E4B-it-GGUF` recommended default Q8_0 8.031 GB.

### GGUF header ground truth (ranged HTTP reads 64 KB → 16 MB, no download)
Pulled the actual metadata from `ggml-org/gemma-4-E4B-it-Q8_0.gguf` (GGUF v3, 720 tensors, 49 KV pairs):

| Key | Value | Consequence |
|---|---|---|
| `gemma4.context_length` | **131072** | Native 128K — resolves the 128K-vs-64K open question |
| `gemma4.attention.sliding_window_pattern` | 42 vals, 35 true | **35 SWA layers + 7 global** |
| `gemma4.attention.sliding_window` | 512 | SWA ring capacity = 512 tokens |
| `gemma4.attention.shared_kv_layers` | 18 | KV-donor aliasing L24+ (TensorSharp batched path) |
| `gemma4.attention.head_count_kv` | 2 | Global KV is tiny: 2 heads × (512+512) |
| `key_length_swa`/`value_length_swa` | 256/256 | SWA dims |
| `key_length`/`value_length` | 512/512 (global) | Dual head-dim design confirmed |
| `rope.freq_base` / `freq_base_swa` | 1M / 10K | Dual RoPE |
| `embedding_length_per_layer_input` | 256 | Per-layer input (PLE) present |
| tokenizer | gemma4, ~262K vocab | Header bloats past 8 MB → 16 MB range for full parse |

### KV-cache math @ 64K context (from header values, not estimates)
- 35 SWA rings: 512 tok × 2 kv-heads × (256+256) × f16 = **1.0 MB/layer → 35 MB total** (negligible; memory bounded regardless of context).
- 7 global layers full-context: worst case (llama.cpp, no aliasing) **1.75 GB**; TensorSharp w/ 4 donor-owning globals **1.00 GB**.
- Gemma 4 **declines quantized KV** (circular SWA cache is float-only) — f16 KV mandatory, no q8_0 KV trick from EXP-019.

### Memory budget @ 64K (16 GB M3, FAST lane down while DEEP up)
| Quant | Weights | +KV(64K) | +mmproj+draft | +1 GB margin | Total |
|---|---|---|---|---|---|
| Q8_0 (TS rec.) | 8.03 | 1.03–1.78 | 0.66 | 1.0 | **10.7–11.5 GB** |
| Q6_K | 6.59 | 1.03–1.78 | 0.66 | 1.0 | **9.3–10.0 GB** |
| UD-Q4_K_XL | 4.77 | 1.03–1.78 | 0.66 | 1.0 | **7.5–8.2 GB** |
- Q8_0 @ native 128K: KV 2.03 GB → ~11.7 GB (feasible but tight on 16 GB).

### Product-build gate (PASSED)
- Fetched release asset `tensorsharp-server-osx-arm64.tar.gz` (v2026.09.01, 127 MB) into `runtime/server/`; sha256 **verified** `c03fe053…cafad93` against release manifest.
- `TensorSharp.Server.Host` executes; full `--help` captured (`server-help-rest.txt`). Backends: ggml_metal (Apple Silicon recommended), ggml_cuda, ggml_vulkan, cpu. OpenAI + Ollama APIs.

### Integration findings (deep-lane critical)
1. **Context sizing**: no `--ctx-size` flag and no `MAX_CONTEXT` env var in the server binary — the context window **defaults to the model's native 131072**. `--max-tokens` is only the per-request generation cap (default 20000, `MAX_TOKENS` env override). Natively satisfies Hermes' 64K server-reported floor; no context knob needed.
2. **`--sampling-precedence request` REQUIRED** — default pins server sampling over request values, which would silently break Hermes' per-request temperature/top-p.
3. **Two distinct caches, both opt-in**: per-process prefix cache (`--no-prefix-cache` disables) plus **cross-session paged KV cache (`--paged-kv`, default OFF)** with optional RAM/SSD/Redis tiers and TurboQuant 2-bit spill. For Hermes: `--paged-kv --paged-kv-ram-mb 2048` is the strong fit for the 10K+ system/tool prefix (restart persistence claimed in docs; must be re-verified locally per gate step 7).
4. **MTP draft works on Metal** for gemma-4 family (12B agent config runs it auto-window 7); E4B draft `gemma-4-E4B-it-assistant.Q8_0.gguf` is ~99 MB. Lossless (verify-guaranteed).
5. **Vision mmproj optional** — skip initially (text-first DEEP lane; saves 0.56 GB).
6. Thinking mode `<|channel>thought`; tool calls `<|tool_call>call:name{...}` — server parses natively.
7. Ready-made config recipe: `config/gemma-4-e4b.json` (repo), but backend `ggml_cuda` → **change to `ggml_metal`**.

### Baseline engine evidence (inherited, not local)
- TensorSharp ggml_metal vs llama.cpp on identical GGUFs (M5 Pro 48 GB): tg128 0.951×, tg128@4096 0.964×, pp512 0.985× — **2–6% behind** on decode; wins on some models (Qwen3.6 +8–10%). Peer-class engine now.
- CUDA engine-comparison (RTX 3080): Gemma 4 26B-A4B QAT decode 78.7/78.4/79.1 tok/s, prefill ~1832–1941 tok/s.

### Fallback de-risk
- Local llama.cpp **0.4.1 already supports the `gemma4` arch** (confirmed in `libllama.0.4.1.dylib` arch table) → same-GGUF A/B baseline available with installed toolchain if TensorSharp misbehaves.

## Machine state (untouched)
FAST down, DEEP down, swap 0.00M, 62% memory free, 116 Gi disk free. No lanes switched, no defaults changed, no weights acquired.

## PROMOTED to DEEP lane — 2026-09-21 (gate complete)
- Gate suite on the experiment server: factual / tool-call / strict JSON 3/3 PASS + populated needle correct + Hermes-shape radix reuse 89–91% (turn 2: 172/151→cached, turn 3: 223/245).
- Native tool loop PASS (canonical `tool_calls`, executor echo continued correctly).
- Cross-restart checkpoint restore: **negative** (file found at startup, 22,791,536 B, but identical 15K prompt after restart prefilled 72.2 s with cached=0).
- Promotion wiring (backups in `~/.hermes/backup/20260921-exp020-promotion/`): launcher `~/.hermes/bin/local-gemma4` (contract mirror of local-ornith: --server/--stop/--status, port 8919, MAX_CONTEXT=65536, MTP draft, paged KV, loopback); manager `hermes-local-model` DEEP_* → DEEP_LAUNCHER; 8 profile configs ornith-q6→gemma-4-E4B-it-Q6_K (8919 kept); root config 7 touchpoints; repo .gitignore += runtime/ models/ for EXP-020.
- Verified live: manager `status` → `DEEP: up (Gemma4-E4B Q6_K + MTP / TensorSharp, port 8919)`; real completion through 8919 correct (34.6 s first = weight page-in; warm 1.5–7 s).
- vs Ornith-1.5-9B Q6_K (EXP-019 measured): prefill @15-16K 184 vs 158.7 tok/s (+16%); short decode 11.1 (MTP) vs 12.58; populated decode — Ornith 10.1→6.8 tok/s (16K→56K), Gemma4 MTP ~2× effective under pressure (200.5→108.1 ms/tok measured); tool-loop only verified for Gemma4; context 128K native vs Ornith 64K ceiling; Ornith Q6 RSS @64K 9.54 GB vs Gemma4 4.75 GB dirty + 6.6 GB mmap'd weights (prefill swap growth +1.7 GB observed).
- Rollback: `cp backup/local-gemma4→…` restore manager + launcher, profiles re-point to ornith-q6, `local-ornith --server`.
1. ~~Download~~ **DONE** — approved 2026-09-21: `unsloth/gemma-4-E4B-it-Q6_K.gguf` (7,074,929,792 B, sha256 `fd83f3ef44d22e00…` = LFS oid ✓) + `mtp-gemma-4-E4B-it.gguf` (98,653,248 B, sha256 `b6a723115efa510d…` ✓) → `EXP-020/models/`.
2. ~~Launch isolated~~ **DONE** — port 8921, `--host 127.0.0.1` (loopback; default binding is **0.0.0.0** — must pin!), ggml_metal, `--sampling-precedence request`, `--paged-kv --paged-kv-ram-mb 2048`, `MAX_CONTEXT=65536`.

## LIVE MEASUREMENTS (this Mac, M3 16 GB, background QoS, single-resident)

### Load + engine graph
- Cold model load: **30.6 s** (7.07 GB GGUF); warm restart after prefix-cache write: **9.9 s**.
- Engine graph verified: `gemma4|L=42|H=8|KV=2|gKV=2|gD=512|lD=256|swa=512|f16`, all attention paths available, MTP spec decoding armed (`per-token, maxDraft=7, pMin=0.15`).
- `MAX_CONTEXT` env var **verified working**: `kvCapacityTokens` 131072 → 65536 (halves KV reservation).

### Performance (direct /v1/chat/completions)
| Measure | Result |
|---|---|
| Small-prompt decode (21-tok prompt) | **11.1 tok/s** (80 tok, 7.2 s; TTFT 0.39 s); warm repeat 7.1 tok/s under memory pressure |
| Prefill 15,036-token populated prompt | **TTFT 81.5 s ≈ 184 tok/s** prefill rate; answer correct (391, clean 1–10) |
| Identical repeat, same server | TTFT 70.2–81.6 s, **`kvReused=0`** — radix cache did NOT hit on identical re-prompt |
| Native tool call (134-tok prompt, 1 tool, tool_choice=auto) | **PASS**: `finish_reason=tool_calls`, canonical OpenAI tool_calls array, `{"command":"date"}`, 12 completion tokens |
| Full loop (tool result echoed, ID matched) | **PASS**: content quotes real `date` output, normal `stop` |

### Memory envelope (16 GB, the decisive caveat)
- Footprint (footprint PID): **2.9 GB @128K KV** → **4.75 GB @64K KV** (dirty Malloc Large = KV + workspace; weights are mmap'd file-backed).
- System: 62% free pre-test → **10% free with swap growing ~+1.7 GB during 15K prefill** — real pressure even at modest context. Budget estimate was optimistic: with mmap'd weights the *dirty* KV+workspace+paged-KV tier is what the 16 GB machine feels.
- Clean stop: port closed, no processes, memory back to 67–74% free.

### Cache behavior (honest)
- In-process prefix cache: no hit on identical repeat (`kvReused=0`) — likely the fused per-sequence path bypasses the radix tree for solo sequences (engine log: `rejected: SpeculativePerSequence`).
- Cross-session checkpoint: **22.8 MB .ckpt written to `prefix-cache/<model>-<hash>/` on shutdown** — restart-persistence mechanism exists; its restore path untested (next rung).
- Paged-KV cross-session tier: enabled (2048 MB), evicted blocks unseen at this scale.
- **MTP stats (tool-loop turn, from full server log)**: drafted=42 accepted=27 (**64% acceptance**), verifySteps=6, rollbacks=4; but governor shows spec=82.7 ms/tok vs plain ≈ 0 wins on that turn — at 11 tok/s trunk speed the draft+verify overhead roughly breaks even on short outputs (resolved by the populated-turn stat below — no `--no-spec` lane needed).
- **MTP stats (15K-populated turn, first arm)**: drafted=63 accepted=37 (59%); governor `plain=200.5 ms/tok` vs `spec=108.1 ms/tok`, wins=1 — **spec decoding nearly halved effective token cost under memory pressure**. MTP pays off in the populated/slow-trunk regime (the DEEP lane's regime); keep `--draft-model` engaged.
- **Global-KV cache growth mechanism**: server log shows `Expanded Gemma4 global attention cache to 4096 → 8192 → 16384 tokens` during the 15K prefill — the global cache doubles incrementally with actual context, so memory ramps during long prefills (the +1.7 GB swap event) rather than dirtying the full `kvCapacityTokens` reservation at launch. `MAX_CONTEXT` still bounds the ceiling.

### Verdict vs Bonsai-27B (current DEEP lane)
Gemma 4 E4B + TensorSharp: 11.1 tok/s decode, 184 tok/s prefill, **correct native tool calls**, native 64K–128K window. Bonsai: ~2–4 tok/s, ~140–190 tok/s prefill, no agentic benchmarks. This is a **strict upgrade on every measured axis** — candidate for DEEP-lane promotion after the real Hermes turn.

### Remaining gate steps
- Real Hermes turn at full-scale schema (the promotion gate), then llama.cpp same-GGUF A/B (0.4.1 supports gemma4 arch) if warranted.
- Prefix-cache restart restore test (second launch should read the 22.8 MB checkpoint).
- Populated-context decode ladder (35K/50K) under the 64K reservation.

## Machine state (final)
FAST down, DEEP down, swap 4.2 GB (pre-existing pressure; model exited cleanly), 74% memory free. No lanes switched, no defaults changed. Models + runtime live only in `EXP-020/`.