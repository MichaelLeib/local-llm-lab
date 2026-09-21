# EXP-022 — Auto routing: compact local fast-lane selection

## Objective
Select the smallest candidate that reliably performs Hermes-oriented FAST and auxiliary tasks on the M3/16 GB Mac, then integrate a reversible Auto/Fast/Deep route in the existing MyChatty → Hermes `/v1/runs` path.

## Safety controls
- One resident local model only. The existing `hermes-local-model` FAST Ornith lane is stopped before an isolated test server is launched and restored afterward.
- Every candidate binds `127.0.0.1` on a dedicated test port.
- Existing configs are copied to `backups/<timestamp>/` before any edit; no production model file or prior evidence is overwritten.
- Candidate context is 8192 tokens: sufficient for compact direct validation and avoids claiming a long-context performance result.
- Resource snapshots record swap/pageout deltas and process footprint. Any unsafe memory condition is terminal for that arm.

## Candidate arms
1. MiniCPM5-2B GGUF Q4_K_M — `openbmb/MiniCPM5-2B-GGUF`
2. Spark-X2.5-1.7B GGUF Q4_K — `eaddario/Spark-X2.5-1.7B-GGUF`
3. NeoHorse-1-4B GGUF Q4_K_M — `TokenRhythm/NeoHorse-1-4B-GGUF`

All arms use Homebrew llama.cpp 0.4.1 (`b10964-b29c606e2`), `--jinja`, Metal offload (`-ngl 99`), loopback-only HTTP, and the embedded model chat template. Spark requires llama.cpp build >= b10828, which this build satisfies.

## Gates
- Direct text correctness / no-think behavior
- Tool-call emission and continuation on an OpenAI-compatible request
- Warm TTFT, server timings/prefill, decode throughput
- Hermes tool loop in an isolated profile only after direct tool calls pass
- Loaded idle/active RSS/footprint, swap and pageout deltas

A model that emits prose instead of a native tool call is rejected for a Hermes primary/auxiliary lane regardless of direct-answer quality.
