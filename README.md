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
| `README.md` / `PROJECT.md` / `RESULTS.md` / `EXP-INDEX.md` | project overview, aggregated results, per-experiment index |
| `results/raw/EXP-*` | raw evidence packs per experiment (logs, JSON metrics, request dumps, patch diffs) |
| `results/clean/` | curated summaries derived from raw packs |
| `tools/llm-exp` | experiment runner: server control, timed runs, comparison reports |
| `tools/exp007_*.py/.sh` | blind A/B harness scripts for the agent-on-local-model experiment |

## Highlights

- **EXP-019 (Ornith GGUF):** Q6_K winner at 12.4–12.7 tok/s decode,
  145–172 tok/s prefill, needle retrieval correct through 61.9K context;
  Q5_K rejected on prefill throughput (119 tok/s).
- **EXP-005 (prefill sweep):** chunked-prefill behavior characterized
  across GGUF quant levels.
- **EXP-007 (agent A/B):** blind task runs comparing local model lanes
  against the production setup, with unblinding score sheets.
- **EXP-022/023 (routing):** automatic fast/deep lane selection.

See `EXP-INDEX.md` for the full experiment catalog and `RESULTS.md` for
cross-experiment findings.

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