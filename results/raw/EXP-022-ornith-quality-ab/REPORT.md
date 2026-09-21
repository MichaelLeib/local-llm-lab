# EXP-022 — Ornith MLX-4bit vs GGUF-Q6_K quality/performance A/B

**Date:** 2026-09-20  
**Host:** MacBook Air M3, 16 GiB unified memory, macOS 27.0  
**Final classification:** **MLX4_REJECTED_FOR_Q6_REPLACEMENT_UNDER_5PP_GATE**

## Decision

The official MLX 4-bit FAST lane did not meet the pre-registered quality-loss ceiling when compared with the higher-precision Q6 GGUF arm. On a deterministic 16-item exact-answer suite, MLX4 scored **11/16 (68.75%)** versus Q6's **14/16 (87.50%)**: **−18.75 percentage points**, exceeding the permitted −5 point regression by **13.75 points**.

This does **not** invalidate MLX4 as the faster existing lane for speed-first work. It means that its promotion as a no-more-than-5%-quality-loss replacement for Q6 is not supported.

## Fixed direct test

- **Q6:** `Ornith-1.5-9B-Q6_K.gguf`; Homebrew llama.cpp Metal; Q8_0 K/V; loopback `:8919`; 65,536 server context.
- **MLX4:** official `ornith-ai/Ornith-1.5-9B-MLX-4bit`; rapid-mlx; loopback `:8901`.
- Only one model was resident at a time.
- Common request parameters: `temperature=0`, `top_p=1`, `max_tokens=256`, `enable_thinking=false`.
- Every question required a final `FINAL: <answer>` line and used an objective exact answer key.

The suite deliberately measures a narrow quantization-regression envelope: arithmetic/logic, data or code tracing, and strict output following. It is not a substitute for autonomous coding or research evaluation.

## Direct quality result

| Group | Q6 | MLX4 | Delta (MLX4 − Q6) |
|---|---:|---:|---:|
| Arithmetic / logic (9) | 9/9 — 100.00% | 7/9 — 77.78% | −22.22 pp |
| Data / code tracing (5) | 3/5 — 60.00% | 3/5 — 60.00% | 0 pp |
| Instruction following (2) | 2/2 — 100.00% | 1/2 — 50.00% | −50.00 pp |
| **Overall (16)** | **14/16 — 87.50%** | **11/16 — 68.75%** | **−18.75 pp** |

Notable observed MLX4 failures included a wrong exact string reversal (`s21-HsemerH`) and an incorrect XOR construction before output truncation. Several failures were `finish_reason=length` without the required final line; these count as reliability failures because a caller cannot safely infer the intended answer. Q6 also failed one short code-trace item and one strict-format JSON item, so this is not a claim that Q6 is flawless.

## Direct response latency

| Arm | Mean wall time | Median wall time | Mean completion tokens |
|---|---:|---:|---:|
| Q6 | 13.480 s | 14.095 s | 140.62 |
| MLX4 | 11.115 s | 9.949 s | 146.81 |

These values are small-prompt direct-request observations, not a Hermes cold-start metric. MLX4's lower mean latency does not compensate for the failed quality threshold.

## Native Hermes tool scenario

Scenario: read a three-line file; write the lines in reverse order with exactly one trailing newline; reread the created file; only then report success.

### MLX4: PASS

An isolated temporary Hermes profile bound to `:8901` completed the real native file/terminal workflow:

- Session: `20260920_092058_689643`
- Duration: **1m 47s**
- Tool calls: **8**
- Independent output verification: `native-output-mlx4.txt` contains exactly `gamma\nbeta\nalpha\n`.
- The first response hit its output cap after initial tool work, but the model recovered, reread the file, and reached a normal final response.

### Q6: fresh rerun inconclusive; prior native evidence retained

The Q6 rerun first created the correct output and used the reread tool, but the foreground experiment wrapper interrupted the API call before a normal final response. A separate background retry stalled at initialization while the 64K Q6 server reached **8% free memory**; the server was stopped rather than risk host pressure.

This fresh rerun is therefore **not scored as a Q6 native-loop pass**. Its baseline agent evidence is the previous EXP-019 validation: real executor completion through `local-ornith`, **78.5 s cold** at 11,068 input tokens and **4.7 s warm** at 99% cache. The experiment does not overwrite that validated evidence.

## Resource caveat

The two direct-suite arms did not begin from matched host-memory states, so their memory telemetry is preserved but **not compared as a winner metric**:

- Q6 started at 15% free memory and ended at 7%, with significant swap/pageout growth.
- MLX4 started at 70% free and ended at 36%, with no swapout increase in that arm.

All model servers were stopped after the test. FAST and DEEP are down; no listener remains on 8901, 8902, or 8919. The temporary `ornithabfast` profile was deleted after the native MLX4 validation.

## Implication

Keep the existing split:

1. **MLX4 FAST** remains the speed-first, tool-validated lane.
2. **Q6 GGUF + Q8_0 K/V** remains the quality/headroom reference lane.

A future broader evaluation should use a larger coding/research battery with blind human or independent-judge scoring, but it is not necessary to resolve the specific ≤5% replacement claim: this controlled gate already rejected it.

## Artifacts

- `README.md` — preregistered scenario and threshold
- `direct_quality.py` — deterministic stdlib test driver
- `direct-q6.json`, `direct-mlx4.json` — raw responses, scoring, and telemetry
- `native-mlx4.out`, `native-output-mlx4.txt` — full real-Hermes evidence
- `native-q6.out`, `native-q6-rerun.out`, `native-output-q6.txt` — retained incomplete Q6 rerun evidence
- `summary.json` — machine-readable conclusion
