# EXP-010 — Laguna S 2.1 long-context Hermes qualification

**Date:** 2026-09-18  
**Outcome:** **stopped_for_memory_pressure at the Phase-2 short-context safety gate**  
**Decision class:** **D — not viable as a primary local Hermes coder on this 16 GiB Mac under the currently tested TurboQuant-MLX / tqTe-g64 configuration.**

## Question

Can Poolside Laguna S 2.1 deliver a genuinely populated 64K context, approximately 4+ tok/s warm decode, safe memory behavior, useful prefix reuse, and real Hermes tool operation on the actively cooled 16 GiB M3 MacBook Air?

## Phase 0: runtime/model decision

`runtime-survey.md` preserves the source/config/model-host evidence and pinned commits.

- **Selected first runtime:** TurboQuant-MLX, local checkout `manjunathshiva/turboquant-mlx` commit recorded in `provenance/turboquant-git.txt`.
- **Selected model:** `manjunathshiva/Laguna-S-2.1-tqTe-g64`, downloaded once into `model/laguna-s21-tqTe-g64/`; exact file hashes are in `provenance/laguna-sha256.txt`.
- **Format:** TQ 3-bit attention / 1.58-bit ternary routed experts (`tqTe`); the downloaded tree measured `28,034,372 KiB` by `du`.
- **Why TurboQuant first:** it is the only surveyed candidate with a directly supported Laguna tqTe checkpoint, packaged MLX server, streaming routed experts, and compressed-KV controls suitable for a conservative 16 GiB gate. `streamlx` remains an implementation comparator, but its documented Laguna run uses a separate ~34.7 GB artifact and a 32 GiB M4 Air; with only 4.1 GiB immediately free after the single tqTe acquisition, a non-duplicating local streamlx run was not possible.
- **No local model lanes or Hermes defaults were changed.** FAST and DEEP were down before and after the arm.

## Safety rule

A short populated-context arm must stay below **+512 MiB incremental swap** and at or above **20% system-wide memory free**. Either limit stops the process; no larger context, prefix-cache, Hermes, coding, or DFlash phase may follow a stop.

This deliberately adopts the EXP-009 lesson: configured context is not evidence of a safe usable context.

## Phase 2: 4 GiB native-routing ~6K populated-context gate

### Fixed configuration

| Item | Value |
|---|---|
| Arm | `arms/phase2-short-4g-native-6k-tokenizer-fix/` |
| Cache budget | 4.0 GiB |
| Routing | native top-10; `max_active_experts=0` |
| KV | server default FP16; no DFlash |
| Server | TurboQuant OpenAI-compatible server, loopback `127.0.0.1:8910` |
| Prompt | deterministic Hermes-shaped static corpus; **6,159 rendered tokenizer tokens** |
| Requested completion | 256 tokens |
| Prefix reuse | none on this first request (6,158 fresh server prefill tokens) |
| Guard | +512 MiB incremental swap or memory-free <20% |

The original same-config arm is retained separately as `phase2-short-4g-native-6k/`. It never launched inference because the environment's Transformers 5.17 tokenizer path rejected Laguna's nested RoPE configuration. That is a harness/configuration failure, **not** an inference result. The final arm directly used the checkpoint's `tokenizer.json` for deterministic token counting; it compiled and produced the 6,159-token prompt before server launch.

### Observed result

| Measurement | Result |
|---|---:|
| Baseline system swap | 3,437.06 MiB |
| Peak system swap | 3,470.94 MiB |
| Incremental swap | **+33.88 MiB** |
| System-wide free memory | **74% → minimum 13%** |
| Stop condition | `memory_free<20% (13%)` |
| Server exit | SIGTERM from the experiment guard (`-15`) |
| Request HTTP status | 200, but guard stopped the process during the request |
| Prompt processed | 6,158 fresh prefill tokens; 0 reused |
| Generated tokens / TTFT / decode | **not established** |

The server’s own startup line described an estimated 11.8 GiB working set and 0.0 GiB then-resident model cache. That is runtime-reported metadata, not a measured physical-footprint result. The guard’s per-process footprint/RSS extraction was not valid on this macOS invocation, so neither is claimed. The retained raw telemetry, server log, and `iostat` samples are the evidence source.

The guard stopped approximately during the first real prefill/generation transition. `response.sse` contains no emitted completion events. Therefore the HTTP 200 response **does not establish successful generation**, and this experiment deliberately claims **no prefill rate, TTFT, warm decode, cache-hit rate, miss count, expert bytes/token, Metal-memory value, or thermal result**.

The internal-SSD `iostat` samples show active `disk0` traffic during the arm (recorded sample rates range roughly 15–397 MB/s), but without a no-run matched baseline or runtime byte counters they cannot be attributed precisely to routed-expert reads. No SSD-throughput conclusion is promoted.

## Interpretation

The safety objective was not exceeded through swap; it failed through the independent memory-pressure stop at only the required 4K–8K-stage populated prompt. This is still a hard failure for the requested primary-model envelope because a safe short Hermes-shaped prompt is a prerequisite for 32K, 64K, and 128K—not an optional optimization target.

The absence of generated tokens is important: there is no decode score to compare with the 4 tok/s target, and no evidence of Laguna coding quality, tool-call correctness, prefix reuse, or long-context retrieval in this configuration. Cooling is not the diagnosis: this failure occurred before a sustained decode or thermal characterization.

## Decision

**Do not advance EXP-010 to prefix reuse, 32K, 64K, 128K, Hermes tool qualification, coding evaluation, cache-budget sweeps, or DFlash.** The exact requested primary-model qualification is negative on the first safe gate.

This is a current-configuration decision, not a claim that every possible future Laguna runtime is impossible. Reopening Laguna on this Mac requires a materially different, independently justified representation/runtime whose *actual* short 4K–8K populated-context run can remain above the memory-pressure guard. At the original EXP-010 post-download gate, immediate root free space was only 4.1 GiB, so a second large representation was correctly excluded; any future acquisition requires a fresh storage gate rather than reusing that historical value.

## Post-experiment host-failure evidence

On 2026-09-19, macOS restarted after a watchdog panic during an associated agent-launched Python workload. The panic snapshot had only 904 free 16 KiB pages, its compressor was at 100% of segments limit with 44 swapfiles, and its largest task was `python3.11` PID 45987 at 56,261,951,536 recorded resident bytes. The artifact does not retain that task's command line, so it cannot prove the exact command, but it is consistent with the observed unsafe memory-allocation regime. The full forensic record is `POSTMORTEM-2026-09-19.md`.

This makes the current runtime path a host-safety rejection, not merely a conservative short-arm stop. A 2-second user-space polling guard cannot be relied upon once the allocation/VM path has made the host unresponsive.

## Artifacts

- Runtime/model survey: `runtime-survey.md`
- Acquisition command/log, config, revision, and hashes: `scripts/download-laguna-tqte.sh`, `logs/laguna-tqte-download.log`, `provenance/`
- Failed pre-tokenizer arm: `arms/phase2-short-4g-native-6k/RESULT.md`
- Guarded inference arm: `arms/phase2-short-4g-native-6k-tokenizer-fix/summary.json`, `telemetry.json`, `server.log`, `prefill-stats.jsonl`, `iostat.txt`, `response.sse`
- Exact guarded launcher: `scripts/run_guarded_server.py`
