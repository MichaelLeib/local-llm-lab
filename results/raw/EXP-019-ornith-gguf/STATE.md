# EXP-019 — Ornith-1.5-9B GGUF (llama.cpp) Runtime Campaign — FINAL STATE

Updated: 2026-09-19 21:45 CEST

## Frozen configuration (final winner: Q6_K, 32K runtime context, Q8_0 KV optional)

- Host: MacBook Air M3 (A3114, 15-inch), 16 GiB unified memory, macOS 27.0
- Runtime: Homebrew llama.cpp `0.4.1`, build `10964`, commit `b29c606e2`, Metal
- Model repo: `ornith-ai/Ornith-1.5-9B-GGUF`, rev `bec5e5f3` (tree oid `e57927bbb97bb13881d0d0b9312d4db518788639`)
- Q6 artifact: `Ornith-1.5-9B-Q6_K.gguf`, 7,558,901,696 bytes, SHA-256 `b6f76e74f86245b3caee014b797c10dca931c4dfdaabfb134eab655f81e4154a`
- Q5 artifact (tested): `Ornith-1.5-9B-Q5_K_M.gguf`, 6,642,544,576 bytes, SHA-256 `e4d9634a3b6546a5c00a8680568fe1125f6c98c704ee51ae52ba07650fb4247d`
- Endpoint: `http://127.0.0.1:8919/v1`, loopback-only
- Launch: `~/.hermes/bin/local-ornith` (starts Q6 server @32K, health-waits, runs Hermes `-p local-ornith`, stops only a server it started)
- Server manager: `scripts/ornith-server.sh` (`ORNITH_CTX`, `ORNITH_EXTRA` env overrides)
- Hermes profile: `local-ornith` (cloned from local-minimal; chat_completions api_mode; context_length 65536; model default + alias `ornith-q6`)
- Sampling (coding): temp 0.6, top_p 0.95, top_k 20, min_p 0, rep_pen 1.0 (per official card)
- Note: GGUF contains an ignored MTP/nextn draft head (blk.32); llama.cpp loads the dense base (9.197B params reported by server meta)

## Headline measurements (llama.cpp server-side timings, idle baseline where noted)

- Cold model load: ~12 s (weights file-backed; phys_footprint grows with touched pages)
- Decode (small prompt): 12.4–12.7 tok/s steady (tg_3s 12.6–12.9), both Q6 and Q5
- Prefill: 152–172 tok/s up to ~6K; 159 tok/s @17.7K; 153 @26.6K; 145 @35.4K; 138 @44.2K; 123 @61.9K populated
- Decode vs populated context (same session, growing cache): 12.7 (0) → 12.3 (4.4K) → 9.8–10.1 (17.7–26.6K) → 8.0 (44K) → 6.8–7.8 (62K) tok/s
- Hermes real-prompt cold: 87.6 s TTFT at 11,095 input tokens (system+tools+user); Q5: 86.7 s
- Hermes warm tool-loop continuations: 9.2–14.3 s latency at 98–99% cached input, decode 7.8–10.4 tok/s
- Qwen3.6/Slipstream reference: cold ~5K Hermes TTFT 108–127 s; warm 3.1–4.5 s

## Context envelope (Q6, needle retrieval, all retrieval CORRECT)

| Populated tokens | Alloc ctx | Prefill t/s | Decode t/s | Memory state | Verdict |
|---|---|---|---|---|---|
| ≤6.7K | 8K | 152–172 | 9.6–12.7 | comfortable | practically usable |
| 17.7K | 32K | 159 | 10.1 | ~24% free | usable |
| 26.6K | 32K | 153 | 9.8 | ~17–24% free | usable |
| 35.4K | 48K | 145 | 9.0 | 15–18% free, swap grows | completes, marginal |
| 44.2K | 48K | 138 | 7.8–8.0 | 15% free, swap +1.1G | completes, not comfortable |
| 61.9K | 64K | 123 | 6.8–7.8 | 9–11% free, swap grew to 5.3G | allocatable/completes/correct, NOT comfortable |
| 21.1K (Q8_0 KV @64K server) | 64K | 144.7 | 10.1 | idle footprint 1.47 GB, 21% free | preferred KV config |
| 21.1K (FP16 KV @32K) | 32K | 157.1 | 7.7 | more KV memory | prefill faster, decode slower, more memory |

KV decision: `--cache-type-k q8_0 --cache-type-v q8_0` for ≥24K-class sessions (43% KV memory cut, ~24% better populated decode; prefill only ~8% slower). FP16 KV fine below 16K.

## Hermes real-loop results (native terminal tool, profile local-ornith)

- Q6 @32K: date+pwd loop, 2 API calls; cold 87.6 s, warm 11.3 s (99% cache); exact outputs quoted, no fabrication
- Q6 @32K: multi-turn file pipeline (list→read→write→read) resumed session, 4 API calls: 10.2 s, 14.3 s, 9.2 s, 10.0 s; all 98–99% cache; result.txt correct (ALPHA/BETA/GAMMA)
- Q6 @64K: full Hermes session ran; system free memory fell to 8% during loop → 64K classified NOT comfortable under concurrent desktop load
- Q5 @64K: full Hermes session (86.7 s cold, 8.9 s warm); swap after 2.1G vs Q6-32K 2.96G
- Reasoning splits cleanly into reasoning_content; tool calls surface as finish_reason=tool_calls with valid JSON args

## Quant comparison (same 21,055-token needle @32K)

| Metric | Q6_K | Q5_K_M |
|---|---|---|
| Prefill | 144.7–172 t/s | 119.5 t/s |
| Decode (populated) | 0.48 t/s (session-contaminated) | 0.40 t/s |
| Decode (small) | 12.4–12.7 | 12.37 |
| Weights | 7.56 GB | 6.64 GB |
| Hermes @64K | 8% free | ~10% free, swap 2.1G |

Decision: Q6_K wins. Q5 prefill is ~20% slower with no meaningful headroom gain in the arm that matters. Q6 decode/prefill at small context identical. Keep Q6.

## Safety notes

- Memory pressure at ≥35K populated context reaches 15% free with swap growth; do not run >48K-class prompts while the user is actively working.
- 64K allocates and completes with correct retrieval, but is not a comfortable interactive configuration on 16 GiB with desktop apps resident.
- All servers stopped cleanly; port 8919 verified closed after each arm.

## Known-good launcher

`~/.hermes/bin/local-ornith` → starts Q6 GGUF llama-server on 8919 @64K with Q8_0 KV, waits health, runs `hermes -p local-ornith "$@"`, stops only its own server.
Validated end-to-end 2026-09-19 22:12: fresh Q6 Hermes session, cold 78.5 s @ 11,068 input tokens, warm follow-up 4.7 s at 99% cache, exact `sw_vers` output quoted.

## Environment note (parallel-controller interference)

A parallel desktop Hermes session (gpt-5.6-terra, session 20260919_211454_a3074d) worked the same campaign concurrently and repeatedly stopped the 8919 server mid-prefill; a concurrent EXP-020 Bonsai-2 campaign briefly held a second model resident (8.2 GB RSS), which caused one Metal compute failure. Numbers in this report were taken with a single resident model unless noted; the 21K Q5/Q8KV/FP16 arms were re-run cleanly after the interference.

## Not yet run (next campaign)

Full autonomous coding/research benchmark (Ornith GGUF vs Bonsai) — runtime lane is ready.