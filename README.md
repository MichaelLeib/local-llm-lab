# Local-LLM-Lab

Benchmark and experiment results for running open-weight LLMs locally on Apple
Silicon (MacBook Air M3, 16 GB unified memory, thermal-hacked with active
water cooling), orchestrated through the
[Hermes Agent](https://github.com/NousResearch/hermes-agent).

Every experiment is a self-contained evidence pack: raw server logs, captured
API payloads, prefill/decode timing series, and the tooling used to run and
score it. The goal is honest, reproducible numbers for day-to-day agent
serving on constrained hardware — not leaderboard chasing.

## Layout

| Path | Contents |
|---|---|
| `README.md` / `PROJECT.md` / `RESULTS.md` / `EXPERIMENTS.md` | project overview, aggregated results, experiment register |
| `results/raw/EXP-*` | raw evidence packs per experiment (logs, JSON metrics, request dumps, patch diffs) |
| `tools/llm-exp` | experiment runner: server control, timed runs, comparison reports |
| `tools/exp007_*.py/.sh` | blind A/B harness scripts for the agent-on-local-model experiment |

## Highlights

- **EXP-019 (Ornith-1.5-9B GGUF):** Q6_K is the promoted DEEP lane —
  12.4–12.7 tok/s decode, 145–172 tok/s prefill, needle retrieval correct
  through **61,943 tokens** (514.8 s cold fill; 64K is a technical envelope,
  32K is the comfortable operating target). Q5_K_M rejected as primary on
  prefill throughput (119 tok/s). Fresh Hermes turn: cold 78.5 s at 11,068
  input tokens, warm 4.7 s at 99% prefix cache.
- **EXP-023 (FAST lane):** MiniCPM5-2B Q4_K_M retained over the faster 1B —
  the 1B failed 3 of 4 real-Hermes end-to-end checks (refuses compression,
  wrong answers) despite ~82–87 tok/s direct decode. Promoted **Q4_0 K/V
  cache at 64K**: idle footprint 857 MB vs 2,787 MB F16 (−69.3%).
- **EXP-022 (auto routing):** Auto FAST/THINK/DEEP routing shipped in
  MyChatty → Hermes. MiniCPM5-2B passed the correctness + native tool-call
  gate (~47–52 tok/s); Spark-X2.5-1.7B rejected (returned `FR` for Paris);
  NeoHorse-1-4B rejected (2.71 GB, slower, no benefit). Both lanes cannot
  stay resident: coexistence drove free memory to 6% and swap to ~2.77 GB.
- **EXP-022b (Ornith MLX4 vs Q6 quality A/B):** MLX 4-bit FAST lane scored
  11/16 (68.75%) vs Q6's 14/16 (87.50%) on a deterministic exact-answer
  suite — a −18.75 pp regression, far past the −5 pp pre-registered ceiling.
  MLX4 stays speed-only; Q6 remains the quality reference.
- **EXP-016 (small-active MoE tournament):** ERNIE 21B-A3B MLX 4-bit stopped
  pre-inference (17.2 GB projected working set); Instella stopped at 9% free
  memory; only North-Mini-Code-1.0 UD-Q3_K_M survived, in CPU-only mode
  (11.2 tok/s standalone, cold prefill 179.8 s at 2,740 tokens) — not
  promoted.
- **EXP-013 (Qwen3.8-Flash-Next 2-bit TurboQuant):** stopped below the 3.5
  tok/s hard gate at 1.475 tok/s decode (1.0 end-to-end) with 21.6 GB
  critical expert reads — memory-safe but unusable.
- **EXP-005 (Slipstream + Qwen3.6-35B-A3B):** the best streamed-MoE arm
  measured — 7.5–8.4 tok/s decode standalone, warm TTFT 3.1–4.5 s at 98–99%
  cache reuse — but cold TTFT 107.9 s at 5K tokens and populated-32K
  prefill safety-stopped; never promoted to a full Hermes lane.

See `EXPERIMENTS.md` for the full experiment catalog and `RESULTS.md` for
cross-experiment findings.

## Model overview

Every model tested or queued on the M3 16 GB, with the decision that
matters. **Future experiment runs: update this table** (add the row, keep
the decision current) as part of writing the result pack — plus a
`## Highlights` bullet when the result is notable.

### Tried

| Model | Size / quant | Key numbers | Decision |
|---|---|---|---|
| **Ornith-1.5-9B GGUF Q6_K** (EXP-019) | 9B, Q6_K + Q8_0 KV | decode 12.4–12.7 tok/s; prefill 145–172 tok/s; needle OK @61.9K; Hermes cold 78.5 s / warm 4.7 s | **DEEP lane — promoted** |
| **Ornith-1.5-9B MLX 4-bit** (EXP-002/022b) | 9B, 4-bit | faster (146.8 tok/s prefill) but 11/16 exact-answer score vs Q6's 14/16 | speed-only lane; **rejected as Q6 replacement** |
| **MiniCPM5-2B Q4_K_M** (EXP-022/023) | 2B, Q4_K_M | 47–52 tok/s; 41 ms tool-call latency; Paris ✓; native tool calls ✓; 64K Q4_0 KV idle 857 MB | **FAST/THINK lane — promoted** |
| **MiniCPM5-1B Q4_K_M** (EXP-023) | 1B, Q4_K_M | 82–87 tok/s direct decode but failed 3/4 real Hermes checks (refuses compression, wrong answers) | **rejected** — too unreliable for the session/tool surface |
| **Spark-X2.5-1.7B Q4_K** (EXP-022) | 1.7B, Q4_K | 55–61 tok/s but answered `FR` to "capital of France" | **rejected** — correctness gate failure |
| **NeoHorse-1-4B Q4_K_M** (EXP-022) | 4B, Q4_K_M | ~23–24 tok/s, Paris ✓, 2.71 GB on disk | **rejected** — larger and slower than MiniCPM5-2B |
| **Qwen3.6-35B-A3B + Slipstream** (EXP-005/012/014/015) | 35B-A3B MoE, .gturbo SSD streaming | 7.5–8.4 tok/s decode; warm TTFT 3.1–4.5 s; cold TTFT 107.9 s @5K; populated-32K prefill safety-stopped | best streamed-MoE arm; **not promoted** (no safe 32K+/64K) |
| **Mference runtime + 32 slots** (EXP-015) | same Qwen3.6 | 7.495 vs 7.312 tok/s (+2.5%), no swap growth | only safe incremental win; retained config |
| **Bonsai-2 27B PTQ1_0 (Prism)** (EXP-020) | 27B ternary 2-bit | healthy direct 32K; 64K FP16 KV idle leaves 9% free; first Hermes tool turn timed out | **rejected as primary** — fails Hermes 64K admission floor |
| **Nanbeige4.2-3B** (EXP-021) | 3B, Q6/Q5 GGUF + MLX smoke | 13.26 tok/s @1K decode but 11.49 @8K; 64K unsafe during load (~10.7 GB RSS); Hermes turn 229 s vs Ornith 86.7 s | **rejected** |
| **TinyTitan + Qwen3.8-Flash-Next** (EXP-006/009) | 125B-A6B MoE streamed | 2.44–2.84 tok/s with 1,493 MiB swap; requal arm stopped at 2,801 MiB swap before first token | **rejected** for interactive use |
| **Qwen3.8-Flash-Next 2-bit TurboQuant** (EXP-013) | 125B-A6B, 2-bit experts | 1.475 tok/s decode, 21.6 GB critical expert reads | **stopped** below 3.5 tok/s hard gate |
| **Qwen3-Coder-Next 80B-A3B + Swiftlet** (EXP-011) | 80B-A3B coding MoE | both ~5K arms blew the +256 MiB swap guard (+316/+376 MiB) before completion | **rejected** at first populated-context gate |
| **Laguna S 2.1 TurboQuant-MLX** (EXP-010) | dense, TurboQuant | stopped at 13% free memory before any emitted generation | **rejected** — host-safety stop (watchdog panic reinforced) |
| **Laguna-XS-2.1-3bit** (EXP-018) | ~3B-class, 3.5 bpw MLX | campaign never got past Phase 0 harness validation (storage/archive gate) | **incomplete** — no inference result claimed |
| **ERNIE-4.5-21B-A3B-Thinking** (EXP-016/017) | 21B-A3B MoE | MLX 4-bit 17.2 GB projected → stopped; GGUF Q4_K_M Metal `Insufficient Memory`; slot ladder 5.0→8.0 prompt tok/s @30 slots (20% free) | **rejected** on 16 GB |
| **Instella small-active MoE** (EXP-016) | MoE 4-bit | 4-token output, longer arm hit 9% free / 9,438 MiB swap | **stopped** before Q3 escalation |
| **North-Mini-Code-1.0 UD-Q3_K_M** (EXP-016) | MoE, Q3 CPU-only | 11.2 tok/s standalone; cold prefill 179.8 s @2.7K; tool smoke passed | only survivor of tournament; **not promoted** |
| **Ornith-1.5-35B-A3B expert-residency** (EXP-003) | 35B-A3B, Q4_K/Q6_K routed | 8/16-slot direct inference + Hermes bridge verified (feasibility probe) | superseded by Qwen3.6/Slipstream track |
| **GPT-OSS-120B MXFP4** (EXP-004) | 120B MoE | Metal MXFP4 op verified `supported=1`; needs 80 GB free disk, had ~20 GiB | **paused** at disk gate |
| **Gemma4 26B-A4B** (EXP-004) | 26B-A4B MoE | build + metadata verified; swap 2.38 GiB > 2 GiB precondition | **deferred** safety gate, probe never started |
| **Ornith-1.5-9B MLX 6-bit / OptiQ 4-bit** (EXP-002) | 9B | inventoried with revisions and sizes; ladder context for the 4-bit lane | inventory only |

### Queued / will-try

| Candidate | Why it's next |
|---|---|
| Ornith-vs-Bonsai direct autonomy tournament (EXP-019 follow-up) | Q5 lane saved for it; the full tournament is explicitly unrun |
| North-Mini-Code-1.0 full Hermes native-tool turn + quality batteries | EXP-016's only survivor earned its intelligence test |
| Larger-context FAST tuning (Q4_0 K/V at 32K operating targets) | promoted KV setting has unmeasured populated-context behavior above 22.8K |
| GPT-OSS-120B resume | only after the documented 80 GB free-disk gate + explicit approval |

> Any agent finishing an experiment: add the model row above, keep numbers
> from the report's own decision section, and note the gate it passed or
> failed. If the result is a lane change or a surprise, also add a
> `## Highlights` bullet.

## Reproducing

Tooling is in `tools/llm-exp/`; each `results/raw/EXP-*` pack documents its
own invocation. Models are pulled from Hugging Face; experiment scripts
reference model IDs rather than bundling weights.

## Sanitization

Personal data (local usernames in recorded paths, Tailnet IPs, live
configuration secrets, private workspace snapshots) was removed before
publication. Vendored third-party source trees and model weights are not
included. Details: `SANITIZATION.md`.

## License

MIT — see `LICENSE`.