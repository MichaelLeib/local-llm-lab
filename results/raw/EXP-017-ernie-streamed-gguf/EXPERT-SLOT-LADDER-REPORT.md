# EXP-017 — ERNIE streamed-MoE expert-slot residency ladder

**Status:** complete through the safety/headroom boundary. Slots 22, 26, and 30 were measured sequentially; 34 and 38 were not run because the 30-slot arm reached only 20% free memory, so it was not healthy enough to justify a larger resident cache.

## Fixed configuration and evidence

- Model: `ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf`; runtime `freedomljc/llama.cpp` `1248fd8fa8cfebaece5ea992e4d951c1e18bb9d5` with the pre-existing local ERNIE graph-reservation patch only.
- Prompt: exact existing `context-retrieval-1k-4k-rerun1/4k-populated/prompt.txt`, SHA-256 `ac681dfdc6759f6d3a30d7ba77dbe52ffc1cae4e28b05ce356893966c04eab08`, 19,377 bytes, verified as **3,982 tokenizer token lines**.
- Held fixed: `-ngl 99 -c 8192 -b 512 -ub 2 -n 128 --temp 0 --seed 1234 --single-turn --simple-io`, `--moe-stream-io-threads 2 --moe-stream-direct --no-mmap --no-warmup --fit off`. The only experimental variable was `--moe-stream-cache <N>s`.
- The exact prior 18-slot `-ub 2` baseline was reused: 5.0 prompt tok/s, 4.0 decode tok/s, 38% minimum free memory, 0 swapouts. No fresh baseline was needed because the established runner and fixed command were reused.
- New arms used the pre-existing `--log-verbosity 3` diagnostic only to seek fork statistics. The normal CLI still did not emit cache hit/miss/load/evict counters; values are explicitly N/A. No runtime/source change was made.
- Per-process disk reads are Darwin `proc_pid_rusage` observations. They are process disk-I/O counters, not fork-attributed expert-byte counters. Metal allocation had no non-intrusive per-process counter and is N/A.

| Expert slots | Prompt tok/s | Decode tok/s | Speedup vs 18s | Min free | Swap Δ | Swapouts | Cache hit/miss | Expert I/O | Result |
|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| 18 baseline | 5.0 | 4.0 | 1.00× | 38% | -32 MiB | 0 | N/A; normal prior CLI output exposed none | N/A; no per-process baseline capture | completed prior baseline |
| 22 | 6.1 | 4.6 | 1.22× | 32% | 0 MiB | 0 | N/A; not emitted despite supported diagnostic inspection | `1,249,139,679,232` B process reads; 1.799 GB/s wall-average | completed, exit 0 |
| 26 | 6.9 | 5.6 | 1.38× | 26% | 0 MiB | 0 | N/A; not emitted despite supported diagnostic inspection | `1,014,028,951,552` B process reads; 1.666 GB/s wall-average | completed, exit 0 |
| 30 | 8.0 | 6.0 | 1.60× | **20%** | 0 MiB | 0 | N/A; not emitted despite supported diagnostic inspection | `772,389,642,240` B process reads; 1.462 GB/s wall-average | completed, exit 0; no headroom for larger arm |

## Findings

- Residency materially improved prefill monotonically: 5.0 → 6.1 → 6.9 → **8.0 prompt tok/s** from 18 → 22 → 26 → 30 slots. Decode also rose from 4.0 to 6.0 tok/s.
- Every attempted arm completed with exit 0, zero incremental swap consumption, zero swapouts, and visible reasoning that included `CEDAR-914`; output still reached the fixed 128-token cap, so this is an inspection note rather than a quality score.
- Higher residency traded directly for host headroom: minimum free memory fell 38% → 32% → 26% → **20%**; peak RSS rose 5,000,080 KiB at baseline to 5,721,584 / 6,443,552 / 7,163,872 KiB at 22 / 26 / 30 slots. The 30-slot arm was clean but too close to the previous dangerous 22%-free reference to advance safely.
- 34 and optional 38 were deliberately not attempted. This is a documented safety/headroom stop, not an inferred performance plateau.

## Bottleneck diagnosis

**Insufficient evidence to assign a sole bottleneck.** The strong residency/throughput relationship and decreasing process-read volume are consistent with expert I/O/locality being important, but the fork did not expose cache hit/miss, expert loads/evictions, or expert byte counters through the existing CLI diagnostic path. The observed process disk I/O is supportive OS-level evidence, not a direct expert-I/O attribution.

## Best configuration

The fastest measured configuration was `--moe-stream-cache 30s` with fixed `-ub 2`: **8.0 prompt tok/s**, 6.0 decode tok/s, 0 MiB swap increase, and 0 swapouts. It is a benchmark best, not an operational recommendation, because it left only 20% minimum free memory.

## Decision

**materially helps but insufficient**

Resident expert slots reached the 8 tok/s prefill threshold at 30 slots, but did so without adequate host-memory safety margin to justify 34 or 38 slots or a Hermes promotion.

## Project implication

**Deprioritize further low-level Q4 ERNIE optimization on this 16 GB Mac.** The Q4 streamed path can be improved materially by residency, but the required cache size consumes the stability margin; more slot tuning is unlikely to turn this into a safely promotable local Hermes configuration.

## Exactly one recommended next experiment (not run)

Run one separately authorized **lower-footprint ERNIE Q3 streamed-MoE 4K populated-context feasibility arm at fixed `-ub 2` and 30 resident slots**, using the same guard and telemetry, to test whether comparable residency can retain safe headroom. Do not run it as part of this experiment.

## Raw evidence

- `expert-slot-ladder-4k/slots-22/`, `slots-26/`, and `slots-30/`: command, before/after/cleanup telemetry, five-second samples, raw log, and result for each attempted slot count.
- `expert-slot-ladder-4k/summary.json`: machine-readable arm summary.
- `expert-slot-help.txt`, `expert-slot-tokenization.txt`, and `run_expert_slot_ladder.py`: diagnostic inspection, 3,982-token verification evidence, and guarded runner.
