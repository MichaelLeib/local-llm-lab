# EXP-010 — Laguna S 2.1 long-context Hermes qualification

**Status:** Complete — Phase-2 short populated-context safety gate stopped for memory pressure; no longer-context or Hermes phase is eligible. See `REPORT.md`.

## Question
Can Poolside Laguna S 2.1 retain useful coding-agent behavior while delivering a genuinely populated 64K context, approximately 4+ tok/s warm decode, safe memory behavior, and real Hermes tool use on this 16 GiB M3 MacBook Air?

## Hypothesis
A ternary-expert, SSD-streamed MLX representation plus compressed KV may make an 118B-A8B Laguna operationally feasible where conventional 2-bit MLX streaming is too memory-constrained; a real 4K–8K guard must pass before any long-context arm.

## Hard safety rule
Each inference arm gets a fresh baseline and is terminated/classified `stopped_for_swap` if incremental swap exceeds 512 MiB, memory-pressure free falls below ~20%, or swap rises rapidly without stabilizing. No larger context arm follows a stop.

## Candidate runtimes under survey
1. **TurboQuant-MLX**, `manjunathshiva/turboquant-mlx`, pinned after local clone; expected model `manjunathshiva/Laguna-S-2.1-tqTe-g64` (TQ 3-bit attention / 1.58-bit ternary routed experts, published as ~27 GB), streamed-expert mode plus K8/V3 KV candidate.
2. **streamlx**, `srcterm/streamlx`; control/reference only until a 16 GiB-safe budget is evidenced. Its published Laguna measurements are on a 32 GiB M4 Air and use a 34.7 GB oQ2e-fast artifact.

## Non-negotiable isolation
- FAST and DEEP must remain down.
- No Hermes default, lane-manager setting, or existing experiment artifact is changed.
- One model process only, loopback only, and every arm uses a new raw subdirectory.

## Evidence initially consulted
- Canonical lab docs: `STATE.md`, `RESULTS.md`, `EXPERIMENTS.md`, `ENVIRONMENT.md`, `DECISIONS.md`.
- EXP-005 Slipstream/Qwen evidence; EXP-006 TinyTitan evidence; EXP-007 harness; EXP-008 FP16 context safety evidence; EXP-009 7K real-prompt safety stop.
- Official Poolside model card/API, runtime repositories, and Hugging Face metadata are recorded in `runtime-survey.md`.
