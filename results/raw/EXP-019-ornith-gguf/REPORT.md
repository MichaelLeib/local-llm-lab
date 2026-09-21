# EXP-019 — Ornith-1.5-9B resident GGUF / Hermes runtime campaign

**Date:** 2026-09-19  
**Host:** MacBook Air M3, 16 GiB unified memory, macOS 27.0  
**Scope:** runtime, context, API, and native Hermes tool operation only. No autonomous coding or research tournament was run.

## Executive result

**Yes, Ornith-1.5-9B runs well enough on this M3/16 GB machine to advance to the next autonomy evaluation — with a qualified configuration choice.**

The direct quality-preserving Q6_K representation is fast and retrieval-correct through a 61,943-token populated request, but its 64K server combined with a real 11K-token Hermes/tool prefix reduced free memory to **8%** and grew swap from **2,357 MB to 2,862 MB** during a 102-second tool turn. That is not a comfortable interactive resident lane under the current desktop workload.

The **winning practical configuration is Q5_K_M at a 64K llama.cpp server context**:

- It used **8.75 GB RSS** loaded at 64K versus Q6's **9.54 GB**.
- Its real 11,089-token cold Hermes tool turn completed in **86.7 s**, nearly identical to Q6's **87.6 s**, but began at 15% free memory and ended at 12% free memory with a smaller **+248 MB** swap delta.
- It made correctly parsed native terminal calls, consumed results, and completed normally.
- It is still ordinary fully-resident Metal inference — no SSD expert streaming or live SSD backing is used.

**Practical context:** configure 64K to satisfy Hermes and allow medium/long tasks, but treat **32K as the comfortable populated-context operating target**. Q6 demonstrated correct retrieval at 61,943 input tokens, but its 514.8-second cold fill and 6.81 tok/s post-fill decode make 64K a technical envelope, not an interactive default. Q5 has the healthier 64K Hermes headroom but was not put through an additional 40K+ needle after the safety decision; do not claim that unmeasured result.

**Decision:** proceed to the next direct Ornith-vs-Bonsai autonomy evaluation, using the saved Q5 lane and keeping Q6 available as a quality arm. The full tournament remains explicitly unrun.

---

## Exact reproducible final lane

| Field | Final value |
|---|---|
| Model repository | `ornith-ai/Ornith-1.5-9B-GGUF` |
| Winning artifact | `Ornith-1.5-9B-Q5_K_M.gguf` |
| Artifact size / SHA-256 | 6,642,544,576 bytes / `e4d9634a3b6546a5c00a8680568fe1125f6c98c704ee51ae52ba07650fb4247d` |
| Runtime | Homebrew llama.cpp `0.4.1`, build `10964`, commit `b29c606e2` |
| Endpoint | loopback-only `http://127.0.0.1:8919/v1` |
| Runtime context | `-c 65536`; unified KV; default server slots=4; normal Metal offload |
| Hermes profile | `local-ornith` (isolated clone of `local-minimal`) |
| Hermes transport | custom provider, `api_mode: chat_completions`, local/no-op key, reported context 65536 |
| Coding sampler used in direct probes | temperature 0.6, top-p 0.95; model defaults for unspecified values |
| One-command launcher | `~/.hermes/bin/local-ornith` |
| Launch | `~/.hermes/bin/local-ornith chat` |
| Resident server only | `~/.hermes/bin/local-ornith --server` |
| Stop/status | `~/.hermes/bin/local-ornith --stop` / `--status` |

The wrapper was syntax-tested and exercised: it launched the Q5 artifact, verified `/v1/models` reported **Q5_K_M / 65536**, and stopped the server. It refuses to kill a different process holding port 8919 and never touches FAST (8901) or DEEP (8902). The server was intentionally left **stopped** after the campaign; post-stop free memory was 75%, and port 8919 was closed.

### Retained Q6 comparison arm

| Field | Value |
|---|---|
| Artifact | `Ornith-1.5-9B-Q6_K.gguf` |
| Size / SHA-256 | 7,558,901,696 bytes / `b6f76e74f86245b3caee014b797c10dca931c4dfdaabfb134eab655f81e4154a` |
| Rationale | Retained because it is the higher-precision arm and was functionally sound; not final because 64K Hermes headroom was materially worse. |

---

## Runtime and context measurements — Q6_K

All direct rows are fresh-server, cold populated needle requests. `prompt_tps` and `decode_tps` are llama.cpp server timings; elapsed includes prompt evaluation and generated reasoning/final output. Needle was `LAGUNA_ORNITH_QUARTZ_7391`; every listed completed row returned it exactly.

| Requested filler rung | Actual input tokens | Prefill time / rate | Post-fill decode | Retrieval | Classification |
|---:|---:|---:|---:|---|---|
| 4K | 4,465 | 25.88 s / 172.08 tok/s | 12.58 tok/s | correct | practical |
| 16K | 17,737 | 111.76 s / 158.71 tok/s | 10.10 tok/s | correct | practical for long focused work |
| 24K | 26,579 | 173.36 s / 153.25 tok/s | 9.82 tok/s | correct | completes; cold latency high |
| 32K | 35,419 | 243.66 s / 145.31 tok/s | 9.04 tok/s | correct | upper practical populated target |
| 40K | 44,261 | 323.01 s / 136.99 tok/s | 8.00 tok/s | correct | allocatable/completes, not interactive cold |
| 56K | 61,943 | 503.98 s / 122.88 tok/s | 6.81 tok/s | correct | technical envelope, not practical cold |

### 64K safety telemetry

The Q6 64K needle arm itself ran for 600 seconds with no incremental swap/pageout counter growth: min free memory was **16% / 75.4 MB free pages**, ending at 21%; swap changed **-160 MB**. This proves the isolated direct arm completed safely in that moment; it does **not** promote 64K as a normal desktop configuration.

The more representative Q6 64K Hermes turn had a different outcome: Q6 RSS **9.50 GB**, free memory declined to **8%**, and swap grew **+505 MB** across the two-call tool interaction. The campaign therefore stops escalation at 64K and classifies it as `allocatable`, `completes`, and `retrieval-correct`, but **not comfortably practical with a full Hermes prefix**.

Raw evidence: `raw/ctx64k-needle-56000.json`, `raw/ctx64k-sysmon.jsonl`, `raw/ctx64k-sysmon.compact.json`, and `raw/hermes-date-pwd-e2e-summary.json`.

---

## Q6 vs Q5_K_M

| Measure | Q6_K | Q5_K_M | Result |
|---|---:|---:|---|
| File bytes | 7.559 GB | 6.643 GB | Q5 saves 916 MB on disk |
| Loaded RSS, 32K server | 8.44 GB | 7.65 GB | Q5 saves ~0.79 GB |
| Loaded RSS, 64K server | 9.54 GB | 8.75 GB | Q5 saves ~0.80 GB |
| Direct 4,465-token prefill | 172.08 tok/s | 149.10 tok/s | Q6 +15% faster |
| Direct 4,465-token decode | 12.58 tok/s | 11.94 tok/s | Q6 +5% faster |
| Cold 11K Hermes tool turn | 87.6 s | 86.7 s | effectively tied |
| Warm tool continuation | 9.2–14.3 s, 98–99% cache | 8.9 s, 99% cache | effectively tied / Q5 slightly faster in this one arm |
| 64K Hermes post-turn free memory | 8% | 12% | Q5 materially healthier |
| 64K Hermes swap growth | +505 MB | +248 MB | Q5 materially healthier |
| Native tool calls | parsed and real executor completions | parsed and real executor completions | tie |

**Quantization decision:** Q6 has the modest raw-speed advantage and remains the quality comparison arm. Q5 is selected because the extra ~0.9 GB moves the real Hermes 64K workload from an 8% free-memory state toward a 12% state with half the observed swap growth, without a latency regression. This is a headroom decision, not a claim that Q5 is intrinsically smarter.

No Q4 or Q8 promotion test was warranted: Q5 solved the observed headroom issue; Q8 was already predicted to be inappropriate for this 16 GB context envelope.

---

## API and Hermes validation

### OpenAI-compatible API

The llama.cpp server correctly exposed `/v1/models` and `/v1/chat/completions`. It returned separate `reasoning_content`, `content`, OpenAI-style `tool_calls`, IDs, usage, cache accounting, and llama.cpp timing fields.

A direct tool-schema call (426 input tokens) returned `finish_reason: tool_calls` and a parsed function call:

```json
{"name":"run_shell","arguments":"{\"command\":\"nproc\"}"}
```

This proves llama.cpp parsed the model's tool syntax into the OpenAI-style response rather than emitting only XML/text. Note that `nproc` is not a macOS command; it was only the direct parser probe, not a claimed executor success.

### Real Hermes tool loop — Q6

The isolated `local-ornith` profile made two terminal calls (`date`, `pwd`) on a 11,095-token cold Hermes request. Hermes logged actual `tool_executor` completions, then a normal cached continuation:

- Cold: **87.6 s**, 11,095 in / 92 out.
- Warm: **11.3 s**, 11,229 in / 75 out, **99% cache**.

In the continued disposable-sandbox task it read `source.txt`, then independently chose terminal commands to transform it and read it back:

```text
ALPHA
BETA
GAMMA
```

The session made three sequential executor calls after the follow-up: read source, write transformed file, read result. Evidence: `raw/hermes-file-e2e.out`, `hermes-sandbox/result.txt`, and profile session `20260919_211926_c88c46`.

### Real Hermes tool loop — Q5

At 64K runtime context, Q5 made the same real `date` and `pwd` terminal calls. Hermes logged:

- Cold: **86.7 s**, 11,089 in / 90 out.
- Warm: **8.9 s**, 11,223 in / 66 out, **99% cache**.

Evidence: `raw/q5-hermes64-date-pwd-e2e.out` and profile session `20260919_212835_4c6957`.

### MLX comparison

A fresh MLX rerun was intentionally not performed after the GGUF safety arm. The maintained same-machine FAST baseline already has a validated official `ornith-ai/Ornith-1.5-9B-MLX-4bit` route: **15.1 tok/s** decode, roughly **180 tok/s** at a ~21K-token prefill, and a full-scale native Hermes tool-call validation. It is faster than both GGUF quants, but it is uniform 4-bit rather than the quality-oriented Q5/Q6 choice. This campaign therefore selects llama.cpp Q5 for the quality/headroom lane; MLX-4bit remains the separate speed-oriented FAST lane, not an unmeasured substitute.

---

## Reference comparison — Qwen3.6-35B-A3B / Slipstream

The Qwen numbers below are the established project baseline supplied before this campaign, not rerun here.

| Measure | Ornith Q5 final lane | Ornith Q6 arm | Qwen3.6 / Slipstream reference |
|---|---:|---:|---:|
| Model file | 6.64 GB | 7.56 GB | much larger MoE representation |
| Short direct decode | 11.94 tok/s | 12.58 tok/s | 7.5–8.4 tok/s |
| Realistic Hermes decode | 8.7–10.7 tok/s in tool turns | 7.8–10.4 tok/s | 6.1–6.9 tok/s |
| 4K direct prefill | 149.1 tok/s | 172.1 tok/s | no directly comparable published row |
| 16K direct prefill | not rerun | 158.7 tok/s | cold large prefix known poor |
| Cold ~11K Hermes TTFT | 86.7 s | 87.6 s | cold ~5K: 108–127 s |
| Warm Hermes continuation | 8.9 s | 9.2–14.3 s | 3.1–4.5 s prefix-reused |
| 32K populated | unmeasured Q5 needle; 64K Hermes healthy enough for tool loop | correct at 35,419 actual input tokens | desired 32K envelope previously failed |
| 64K populated | allocation + Hermes tool turn only | correct at 61,943 actual input tokens; not practical cold | not a desired safe envelope |
| Stability | normal API/tool completion; server cleanly stopped | normal API/tool completion; 64K desktop headroom weak | useful narrow warm coding only |

Ornith's advantage is dense-model geometry, higher direct decode, and much healthier long-context feasibility. Qwen's established warm-prefix TTFT is still better in the cited narrow session.

---

## Evidence inventory

- `STATE.md` — current campaign state and safety decisions.
- `results.jsonl` — compact structured direct-run rows.
- `raw/` — raw OpenAI responses, telemetry JSONL, system summaries, launcher test logs, and Hermes outputs.
- `scripts/probe.py`, `scripts/arm.sh`, `scripts/ornith-server.sh` — retained experiment tooling.
- `~/.hermes/bin/local-ornith` — final isolated launcher.
- `~/.hermes/profiles/local-ornith/` — isolated Hermes configuration; default/cloud/FAST/DEEP profiles were not edited.

## Final recommendation

**Proceed to the direct Ornith-vs-Bonsai autonomous coding/research evaluation using `local-ornith` (Q5_K_M, llama.cpp, 64K configured context), with a 32K populated-context budget as the normal operating policy.** Keep Q6 as a targeted higher-precision quality arm. Do not schedule long cold 64K Hermes jobs as ordinary interactive work; reserve 64K for explicitly valuable cases and preserve the existing stop-on-memory-pressure rule.

---

## Post-report reconciliation (api-server session, 22:15 CEST)

Two controllers ran parts of this campaign in parallel. The api-server session additionally measured:

| Measure | Q6_K | Q5_K_M |
|---|---:|---:|
| Prefill @21,055 populated tokens @32K server | 144.7 t/s (Q8_0 KV) / 157.1 t/s (FP16 KV) | 119.5 t/s |
| Decode @21,055 populated | 10.1 t/s (Q8_0 KV) / 7.7 t/s (FP16 KV) | 7.1 t/s |
| Q8_0 KV @64K idle footprint | 1.47 GB phys_footprint, 21% free | n/a |
| Fresh Q6 Hermes turn, final wrapper | cold 78.5 s @ 11,068 in; warm 4.7 s @ 99% cache | — |

With Q8_0 KV the Q6 64K headroom gap narrows substantially (21% free during a real Hermes turn vs the 8% measured at FP16 KV earlier). Resolution encoded in the launcher: **default = Q6_K + Q8_0 KV @64K** (quality-preserving, fastest populated prefill, validated headroom); `ORNITH_QUANT=q5` switches to the Q5_K_M headroom lane measured by the desktop session. Both artifacts and both Hermes aliases remain installed. A fresh Q6 session confirmed the final wrapper end-to-end at 22:12 (exact `sw_vers` output quoted, no fabrication).
