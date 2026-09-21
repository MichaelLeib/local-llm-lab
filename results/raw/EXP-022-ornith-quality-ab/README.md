# EXP-022 — Ornith MLX-4bit vs GGUF-Q6_K quality/performance A/B

## Decision question
Can the already tool-validated official `ornith-ai/Ornith-1.5-9B-MLX-4bit` FAST lane replace the higher-precision Ornith Q6 GGUF lane while remaining within a pre-registered **5 percentage-point** quality-loss tolerance?

## Fixed arms

| Arm | Model/runtime | Endpoint | Context |
|---|---|---|---|
| `mlx4` | `ornith-ai/Ornith-1.5-9B-MLX-4bit`, rapid-mlx | `127.0.0.1:8901/v1` | runtime default; server reports its own ceiling |
| `q6` | `Ornith-1.5-9B-Q6_K.gguf`, Homebrew llama.cpp Metal, Q8_0 K/V | `127.0.0.1:8919/v1` | 65,536 |

Only one arm may be resident at any point. FAST/DEEP and port ownership are checked before every arm.

## Quality suite

The direct suite is deterministic (`temperature=0`, `top_p=1`) and contains 16 objectively scoreable items: arithmetic, exact date logic, unit conversion, boolean logic, string transformations, sorting, JSON extraction, and short code tracing. Each asks for an exact `FINAL: <answer>` line. Scoring is exact normalized answer matching; errors, missing `FINAL`, and malformed output score zero. The same suite runs independently against both endpoints.

This does **not** claim to represent all coding/research quality. It is a narrow quantization-regression gate. A separate native Hermes scenario then tests the agent-critical behavior: a fresh session must read an input file, create a transformed output file, reread it, and reach a normal final response. The artifact is independently verified.

## Acceptance rule

MLX4 is an everyday-lane candidate only if all are true:

1. Direct exact-score is no more than **5 percentage points below Q6**;
2. It does not score lower on any of arithmetic/logic, data/code tracing, or instruction-following subgroups by more than 10 percentage points;
3. The native Hermes file-tool loop succeeds with a verified output artifact and normal completion;
4. Performance, resource telemetry, and cleanup are recorded; no safety guard is tripped.

A tie or MLX4 win does not automatically change production defaults; the experiment reports the measured decision and preserves both lane configurations.
