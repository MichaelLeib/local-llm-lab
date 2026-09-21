# Local LLM Lab

> A long-running engineering workspace for making local language models more capable, efficient, reliable, and practical on Apple Silicon and other machines we may add later.

Updated: 2026-09-17

## Objective

Find local-model configurations that are genuinely useful in real Hermes work—coding, research, reasoning, tool use, and agentic workflows—while preserving responsiveness, memory headroom, stability, and reproducibility. The project is broader than any one model, runtime, architecture, or optimization technique.

A candidate is a win only when it improves the end-to-end trade-off, not merely a leaderboard score or isolated tokens/second number.

## Priorities

1. Real-world capability: coding, research, reasoning, tool selection, and agentic Hermes work.
2. Practical usability: time to first token, sustained generation, prompt/prefill latency, responsiveness, and stability.
3. Memory efficiency: coexist with normal work; quantify RAM, unified-memory pressure, and swap.
4. Quality preservation: do not trade away useful behavior for attractive speed numbers without making the trade explicit.
5. Reproducibility: record exact weights/builds, runtime versions, configuration, commands, and raw measurements.
6. Evidence over assumptions: measure when practical and preserve failures.

## Scope

We may investigate model selection, quantization and mixed quantization, KV-cache/context strategies, sampling and reasoning configuration, prompt/scaffold/agent design, MLX, llama.cpp, Ollama and other runtimes, thermal behavior, dense versus MoE models, selective/offloaded execution, SSD-backed expert streaming, caching/prefetching, and making models larger than active RAM practical.

The immediate research direction is **strong capability under a small active-RAM footprint**, including MoE expert offloading/streaming. It is a hypothesis, not a presumed solution; dense models, quantization, context policy, and agent scaffolding remain equally eligible.

## Success criteria

A promoted configuration must have:

- measured capability on representative Hermes tasks;
- verified native tool calls in a real Hermes turn, not just text that resembles a tool call;
- measured prefill/TTFT, decode speed, memory pressure, swap, and sustained behavior;
- a documented quality and reliability comparison against a named baseline;
- a reversible deployment path and an honest account of limitations.

## Operating principles and guardrails

- Change one meaningful variable at a time whenever possible.
- Keep a known-good configuration recoverable; do not promote from a single number.
- Only one local model may be resident on the primary 16 GB machine.
- Local inference, large downloads, installs, system changes, and expensive experiments require explicit approval before execution.
- A timeout, OOM, swap-thrash event, or fabricated-looking tool result is a result to diagnose—not evidence of success.
- Keep private/proprietary evaluation material on-machine.
- Separate measured facts, inherited measurements, hypotheses, and interpretations in the record.

## Relationship to other work

`~/HermesProjects/QwenLoop` is a separate research project on latent/recurrent computation in small models. Its measurements may be cited as cross-project evidence, but its experiment IDs and conclusions are not silently merged into this lab's register.

## Canonical documents

- `PROJECT.md` — scope, goals, principles, and promotion criteria.
- `ENVIRONMENT.md` — observed machines, runtimes, lanes, and unknowns.
- `EXPERIMENTS.md` — backlog, experiment register, and preregistration template.
- `BENCHMARKS.md` — task sets, metrics, procedure, and comparison rules.
- `RESULTS.md` — concise measured findings and provenance.
- `DECISIONS.md` — durable decisions, rejected paths, and revisit triggers.
- `STATE.md` — short current handoff: active direction, next steps, and blockers.
