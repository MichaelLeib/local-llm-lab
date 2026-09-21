# EXP-021 — Nanbeige4.2-3B vs frozen Ornith Q5

**Host:** MacBook Air M3, 16 GiB unified memory, macOS 27.0  
**Campaign result:** complete through the runtime/promotion gate  
**Decision:** **NANBEIGE REJECTED** for both primary and FAST-lane promotion

## Executive conclusion

Nanbeige4.2-3B runs correctly on this Mac, but it is not a better local Hermes agent system than the established Ornith Q5 lane. The official Nanbeige llama.cpp fork loaded the model, direct reasoning-off output was coherent, OpenAI tool parsing worked, and a genuine Hermes session completed a read → independent transform → write → reread workflow with a verified artifact.

That functional result is not enough. The best tested GGUF arm was Q6_K with Q8_0 K/V at a 64K-admitted server context. It decoded at 13.26 tok/s at approximately 1K input and 11.49 tok/s at approximately 8K, but a 32K populated retrieval run fell to 10% free memory and was stopped before completion. The 64K FP16-KV arm was materially unsafe during readiness, and the 64K Q8-KV arm was still not a healthy long-context working envelope. The full Hermes tool turn took **229.48 s**, compared with the frozen Ornith Q5 control's inherited **86.7 s** cold ~11K tool turn and **8.9 s** warm continuation.

Nanbeige therefore failed the campaign's central test: its small model file did not translate into a faster, healthier, or more capable end-to-end Hermes lane. Published agent/coding claims were not scored locally because the candidate failed the mandatory runtime gate; spending coding/research budget after that failure would confound capability with an unhealthy serving envelope.

The exact final role decision is **NANBEIGE REJECTED**, not “Nanbeige FAST + Ornith QUALITY.” It did not demonstrate a reliable class of ordinary Hermes tasks that completed faster overall.

## Answers to the required questions

| Question | Measured answer |
|---|---|
| Does Nanbeige run correctly? | Yes, with the official Nanbeige llama.cpp fork; MLX OptiQ also passed a bounded direct smoke. |
| Best runtime/quant tested | GGUF Q6_K + llama.cpp fork `nanbeige42` + Q8_0 K/V. Q5 was a lower-memory comparator, not a win. |
| How fast? | GGUF Q6: 13.26 tok/s at ~1K, 12.45 at ~4K, 11.49 at ~8K, 7.81 at ~16K. |
| Memory | GGUF Q6 Q8-KV ~9.52 GB RSS at 64K idle; Q5 ~9.10 GB. MLX direct smoke process RSS ~3.3 GB, but it was not qualified as a server/Hermes lane. |
| Practical context | 8K completes quickly enough for a smoke; 16K completes but takes ~223 s cold; 32K was stopped for pressure for both Q6 and Q5. No useful 32K+ envelope was established. |
| Native tools | Yes, direct parsed tool call and full isolated Hermes tool execution passed. |
| Coding comparison | Not run: candidate failed runtime promotion gate first. |
| Research comparison | Not run: candidate failed runtime promotion gate first. |
| Primary model | **Ornith Q5 remains primary.** |

## Exact Nanbeige configurations

### Official model and architecture

- Official repository: `Nanbeige/Nanbeige4.2-3B`
- Official revision verified before testing: `b82e54bd609793562a75cbf9337970a93369eab5`
- Architecture: `NanbeigeForCausalLM`, model type `nanbeige`
- BF16 parameter bytes reported by Hub: 4,169,800,704; publisher describes approximately 3B non-embedding parameters / 4B total
- Physical decoder layers: 22
- Looped structure: `num_loops: 2`, shared transformer stack; the MLX card states that each loop keeps its own KV cache
- Hidden size: 3,072
- Intermediate size: 10,752
- Attention: 48 query heads, 8 key/value heads (GQA), head/KV dimension 128, no attention bias
- Vocabulary: 166,144
- RoPE theta: 70,000,000
- Advertised context: 262,144 tokens
- Reasoning format: `<think>...</think>`
- Chat template: official tokenizer template; XML tool calls by default, JSON format selectable
- Tokenizer: official `tokenizer.json` plus `tokenizer.model`
- Model-card architectural additions: LoopSplit, mHC with depth attention, concatenated n-gram embeddings

### GGUF Q6 arm (selected runtime arm)

- Quant repository: `Abiray/Nanbeige4.2-3B-GGUF`
- Quant repository revision: `774a61f8217ad18e7e102107fb7abcfecfae6a99`
- Artifact: `Nanbeige4.2-3B-Q6_K.gguf`
- Artifact size: 3,424,947,120 bytes
- SHA-256: `05c1e5eb316d2a25659d5f2d61be549e789a1d64a053330957bf23ae83bc3713`
- Runtime repository: `https://github.com/Nanbeige/llama.cpp`
- Runtime branch/commit: `nanbeige42` / `c6640a1c0cf7b38df342b67021a3900b04d092e7`
- Runtime build: isolated Apple Metal arm64 build; server identifies as build 1 / commit `c6640a1`
- Endpoint: loopback-only `http://127.0.0.1:8921/v1`
- Runtime context: `-c 65536`
- KV: `-ctk q8_0 -ctv q8_0`
- Batching: `-b 128 -ub 64`, one server slot
- GPU: `-ngl 99`
- Sampling: temperature 0.0 for retrieval probes; temperature 0.6/top-p 0.95 for smoke and Hermes; reasoning disabled for the bounded runtime comparisons
- Launcher: `~/.hermes/bin/local-nanbeige chat`
- Isolated Hermes profile: `local-nanbeige`; existing default, FAST, DEEP, and Ornith profiles were not changed

The launcher is intentionally retained as an isolated stopped experiment entry point. It refuses to interfere with a non-Nanbeige process holding port 8921 and does not touch ports 8901, 8902, or 8919.

### GGUF Q5 comparator

- Artifact: `Nanbeige4.2-3B-Q5_K_M.gguf`
- Size: 2,986,996,658 bytes
- SHA-256: `d3c42b2f07dda05c95cf9bc23d0bdbcb9c10e9b169c074de0b716d6cb468ac68`
- Same fork, server flags, and loopback endpoint
- 64K Q8-KV idle RSS: approximately 9.10 GB; observed 26% free memory
- It saved approximately 0.42 GB versus Q6 but did not create a safe 32K envelope and did not improve prefill.

### MLX bounded comparator

- Repository: `mlx-community/Nanbeige4.2-3B-OptiQ-4bit`
- Revision: `e88d49fdd9cd67629c712fc2b4d845ad403ae9b4`
- Artifact: `model.safetensors`, 3,303,644,285 bytes
- SHA-256: `d80f969f9609ee53e5904f611a875c40ee5785c07594d3926200a66b78effca0`
- Runtime: `mlx-optiq 0.5.12`, MLX 0.32.2, mlx-lm 0.31.3, Python 3.14.7
- Direct smoke: 4.87 s load, 70 prompt tokens, 62 output tokens, 13.85 tok/s decode, 63% system free memory, correct response
- The MLX path was not advanced to a server/native-Hermes gate: the bounded direct result was approximately tied with GGUF's short decode, while the GGUF path had a verified OpenAI-compatible API and native Hermes tool execution. No MLX API/tool win was demonstrated.

## Runtime comparison against frozen Ornith Q5

| Metric | Nanbeige Q6 GGUF | Ornith Q5 frozen control |
|---|---:|---:|
| Model file | 3.42 GB | 6.64 GB |
| Runtime | Nanbeige fork `c6640a1` | llama.cpp 0.4.1 / build 10964 / `b29c606e2` |
| Server context | 64K | 64K |
| KV | Q8_0 K/V | inherited Q5 control measurements used FP16 KV in the original report |
| Loaded RSS at 64K | ~9.52 GB with Q8 KV | 8.75 GB at 64K |
| ~1K direct prefill | 171.0 tok/s | not reproduced in this campaign |
| ~4K direct prefill | 147.7 tok/s (cache accounting included) | 149.1 tok/s at ~4.5K inherited |
| ~8K direct prefill | 117.4 tok/s | not reproduced in this campaign |
| Direct decode at short input | 13.26 tok/s at ~1K | 11.94 tok/s inherited |
| Decode at ~8K | 11.49 tok/s | not reproduced in this campaign |
| Cold Hermes tool turn | 229.48 s, 7 tool calls | 86.7 s at ~11K input |
| Warm Hermes continuation | not separately scored after the candidate's long cold turn | 8.9 s inherited |
| 32K populated | stopped at 10% free before completion | practical normal target |
| 64K | allocatable with Q8 KV, not a comfortable populated envelope | valid reserve context |
| Native tool calls | parsed and real executor activity | parsed and real executor activity |

The small candidate file therefore delivered only a modest short-decode advantage and lost badly on cold Hermes wall time and long-context health.

## Context envelope

All input counts below are actual server prompt counts (`cache_n + prompt_n`), not word estimates. Needle retrieval was exact whenever the arm completed.

| Arm | Actual input tokens | Prefill | Post-fill decode | Retrieval | Memory/health classification |
|---|---:|---:|---:|---|---|
| Q6 8K server / 1K target | 972 | 171.0 tok/s | 13.26 tok/s | correct | completes; smoke-practical |
| Q6 8K server / 4K target | 3,962 | 147.7 tok/s | 12.45 tok/s | correct | completes |
| Q6 8K server / 8K target | 7,966 | 117.4 tok/s | 11.49 tok/s | correct | completes; cold latency rising |
| Q6 64K Q8-KV / 16K target | 15,974 | 72.5 tok/s | 7.81 tok/s | correct | completes in 222.9 s; not interactive |
| Q6 64K Q8-KV / 32K target | in-progress actual count not completed | — | — | — | **stopped_for_pressure at 10% free** |
| Q6 64K FP16-KV load | no populated request | — | — | — | **unsafe load; ~10.7 GB RSS and ~1.1 GB swap growth observed** |
| Q6 64K Q8-KV idle | no populated request | — | — | — | allocatable; ~9.52 GB RSS and 23% free observed |
| Q5 64K Q8-KV / 16K target | 15,966 | 72.4 tok/s | 8.87 tok/s | correct | completes in 223.0 s; not interactive |
| Q5 64K Q8-KV / 32K target | in-progress actual count not completed | — | — | — | **stopped_for_pressure at 13% free** |
| Q5 64K Q8-KV idle | no populated request | — | — | — | allocatable; ~9.10 GB RSS and 26% free observed |

The correct classifications are deliberately separate:

- **Maximum admitted context:** 64K server context with Q8 K/V.
- **Maximum completed candidate context:** 16K in this campaign's clean progressive long-context ladder; 32K was safety-stopped.
- **Maximum practically interactive context:** approximately 8K for cold direct work; 16K completes but takes about 3.7 minutes to prefill.
- **Recommended everyday Hermes context:** no Nanbeige recommendation; keep Ornith as the primary lane.

## Hermes integration and native multi-step tool test

The isolated launcher exposed `/v1/models` with `n_ctx: 65536`, `/v1/chat/completions`, streaming-compatible llama.cpp API behavior, reasoning fields, and OpenAI-style `tool_calls`. The first reasoning-enabled smoke was intentionally capped at 256 completion tokens and ended with `finish_reason=length`, empty final content, and 878 characters of `reasoning_content`; the campaign's scored runtime arms therefore used `--reasoning off`, which produced a clean final answer. This is recorded as a reasoning-mode operational caveat, not hidden as a quality pass.

A direct API probe with a terminal-like function schema returned:

```json
{
  "finish_reason": "tool_calls",
  "name": "run_shell",
  "arguments": "{\"command\":\"date\"}"
}
```

The genuine Hermes test used a fresh disposable sandbox containing `source.txt` with `ALPHA`, `BETA`, `GAMMA`. The agent outcome was intentionally behavioral rather than a prescribed sequence: read the source, independently reverse line order, write `output.txt`, reread it, and report the verified result.

Observed result:

- Wall time: **229.48 s**
- Hermes session: `20260920_074310_7ecb0a`
- Tool calls: **7**
- Actual tool executor activity: yes
- Artifact: `hermes-sandbox/output.txt`
- Verified content: `GAMMA`, `BETA`, `ALPHA`
- Independent SHA-256 of output: `8b7b971402609638772fa5e06f05c724e4a3ee6955909099b835b0af2ef858d3`
- Completion: normal final response, not a fabricated tool result

The auxiliary title generation emitted an HTTP 400 warning because an auxiliary path attempted to initialize samplers; the main Hermes task still completed normally through the local endpoint. This is retained as an operational blemish, not hidden.

## Coding and research phases

No direct coding challenge or research challenge was run. This is a deliberate gate result, not missing work:

1. A healthy 64K-admitted runtime and real Hermes tools were required before intelligence testing.
2. The Q6 and Q5 long-context arms were both safety-stopped at 32K before completion.
3. The candidate's full Hermes read/write/reread task took 229.48 s, already 2.6× the frozen Ornith Q5 cold tool turn for a comparable class of interaction.
4. Running coding or research after that point would measure an unhealthy runtime and would not answer whether Nanbeige is a practical replacement.

Published claims (for example, the model card's SWE-Bench Verified 63.6 and Terminal-Bench 2.0 44.1) are recorded as external claims only. They are not local A/B results and do not override the observed runtime gate.

## Operational cleanup and preserved state

- Nanbeige server: stopped; port 8921 closed at final cleanup.
- FAST and DEEP lanes: not started or modified.
- Ornith Q5/Q6 artifacts and launcher: not modified.
- Existing project reports and unique experiment evidence: preserved.
- Isolated profile: `~/.hermes/profiles/local-nanbeige/`; not selected as a default.
- Isolated launcher: `~/.hermes/bin/local-nanbeige`; retained but stopped.
- Raw experiment tree: `results/raw/EXP-021-nanbeige42/`
- The machine had non-zero swap before the experiment; all safety conclusions use arm-local observations and record the evolving baseline rather than claiming a clean reboot baseline.

## Final lane decision

**NANBEIGE REJECTED.**

Nanbeige is a technically interesting small model and its direct quality is not disproven by this campaign. It is rejected as a Hermes lane because the end-to-end evidence is unfavorable: only a small short-context decode edge, no healthy completed 32K envelope, unsafe FP16 64K behavior, long cold prefills, and a native Hermes task much slower than Ornith. Keep Ornith Q5 as the primary local model. Revisit Nanbeige only if a materially different Apple-Silicon runtime demonstrates both a healthy completed 32K+ populated context and a native Hermes wall-time advantage; do not retune Ornith as part of that future test.

## Evidence inventory

- `phase1-freeze.json` — official revision, architecture, runtime, and source freeze
- `summary.json` — structured result summary
- `source/llama.cpp/` — pinned Nanbeige fork and build logs
- `models/q6/` and `models/q5/` — verified GGUF artifacts and hashes
- `models/mlx-optiq/` — verified MLX OptiQ artifact
- `raw/context-8k/` — 1K/4K/8K direct retrieval probes
- `raw/context64-q8/` — Q6 Q8-KV 16K completion and 32K safety stop
- `raw/context64-q5/` — Q5 16K completion and 32K safety stop
- `raw/hermes-native-read-transform-write.txt` — full Hermes transcript
- `raw/hermes-sysmon.txt` — native Hermes resource observations
- `raw/mlx-smoke.json` — MLX bounded comparator
- `raw/final-hashes-verified.txt` — final Q6/Q5/output SHA-256 verification
- `~/.hermes/bin/local-nanbeige` — isolated reversible launcher
