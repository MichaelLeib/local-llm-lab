# EXP-017 — ERNIE physical-microbatch ladder at ~4K populated context

**Objective:** isolate the effect of physical microbatch (`-ub`) on ERNIE streamed-MoE prompt throughput. No model, quantization, expert-cache, I/O, context, logical-batch, prompt, seed, generation cap, GPU-placement, or thread setting changed.

## Fixed configuration

- Model: `ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf`
- Runtime: local arm64/Metal streamed-MoE fork at `1248fd8fa8cfebaece5ea992e4d951c1e18bb9d5`, with the existing isolated ERNIE graph-reservation patch
- Prompt: exact reused 3,982-token 4K artifact: `context-retrieval-1k-4k-rerun1/4k-populated/prompt.txt`
- Context: `-c 8192`
- Logical batch: `-b 512`
- Routed-expert cache: `--moe-stream-cache 18s`
- I/O: `--moe-stream-direct --no-mmap`, 2 MoE I/O threads
- GPU: `-ngl 99`
- Generation: `-n 128 --temp 0 --seed 1234 --single-turn --simple-io`

## Comparison

| ubatch | Prompt tok/s | Decode tok/s | Prompt time est. (3,982/prompt rate) | Total wall | TTFT | Min free mem | Peak RSS | Swap Δ | Swapouts | Pageouts | I/O/cache evidence | Result |
|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 baseline | 4.4 | 4.2 | 905.00 s | 943.29 s | not separately emitted by CLI | 38% | not captured in baseline arm | 0 MiB | 0 | +4,951 | Direct I/O requested; fork emitted no cache/read counters | completed |
| 2 | **5.0** | 4.0 | **796.40 s** | 842.07 s | not separately emitted by CLI | 38% | 5,000,080 KiB | -32 MiB | 0 | +4,340 | Direct I/O requested; no fork cache/read counters | completed |
| 4 | 3.8 | 4.0 | 1,047.89 s | 1,103.27 s | not separately emitted by CLI | 38% | 4,863,376 KiB | 0 MiB | 0 | +4,468 | Direct I/O requested; no fork cache/read counters | completed |
| 8 | n/a; did not complete | n/a | n/a | safety-stopped before prompt completion | n/a | **22% observed** | periodic peak not flushed before safety stop | -227.81 MiB | **+6,924** | **+61,979** | Sustained VM activity; no emitted fork cache/read counters | unsafe; stopped |
| 16 | not run | not run | not run | n/a | n/a | n/a | n/a | n/a | n/a | n/a | larger rung prohibited after unsafe `-ub 8` arm | not attempted |
| 32 | not run | not run | not run | n/a | n/a | n/a | n/a | n/a | n/a | n/a | optional rung not eligible | not attempted |

All completed arms requested a 128-token cap; the thinking checkpoint continued visible reasoning until that cap, so output retrieval was preserved only for inspection and not scored as a quality gate.

## Findings

- `-ub 2` was the fastest safe measured setting at **5.0 prompt tok/s**, a **1.136x** speedup over the 4.4 tok/s baseline. It reduced prompt time by roughly 109 seconds, but remains far below the experiment's 8 tok/s no-rescue threshold.
- `-ub 4` regressed to **3.8 prompt tok/s** (0.864x baseline) while decode remained about 4 tok/s.
- `-ub 8` was safety-stopped. During that arm, system free memory fell to 22% and cumulative OS activity versus the arm baseline reached +6,924 swapouts, +21,900 swapins, and +61,979 pageouts without completing the prompt. Although `vm.swapusage` happened to decrease by 227.81 MiB, the sustained swap/pageout counters represented active churn, so it met the protective-stop rule.
- After cleanup, free memory recovered to 59% immediately and 66% on the recorded cleanup snapshot; FAST and DEEP remained down and no `llama-cli`/server process remained.

## Bottleneck diagnosis

The evidence does **not** support a large GPU-starvation effect from `-ub 1`:

1. Doubling microbatch produced only a 13.6% improvement.
2. Increasing to 4 regressed rather than scaling throughput.
3. Increasing to 8 triggered severe VM churn before prefill completed.
4. Decode stayed near 4.0–4.2 tok/s across safe arms, so batching did not reveal an independent high-throughput execution regime.

The most consistent current explanation is **streamed-expert I/O / synchronization and bounded 18-slot residency**, not under-filled GPU kernels. The fork exposed no per-expert hit/miss or byte-read counters in its normal CLI output, so that attribution remains evidence-based but not fully instrumented.

## Best configuration

`-ub 2` is the fastest safe measured arm: 5.0 prompt tok/s, 4.0 decode tok/s, 38% minimum free memory, no incremental swap growth, and zero swapouts. It is a marginal improvement only.

## Decision

**Microbatch scaling does not solve the fundamental bottleneck.** It neither approaches the 8 tok/s minimum-rescue threshold nor remains safe at a substantially larger batch. ERNIE's streamed path remains technically runnable, but not operationally viable for Hermes context prefill in this configuration.

## Exactly one recommended next experiment (not executed)

Run a narrowly controlled **expert-slot scaling sweep at fixed `-ub 2`** (for example, 18s versus one modestly larger cache) on the same 3,982-token prompt. The aim is to distinguish expert-cache locality/SSD traffic from unavoidable model compute, while retaining the only safe microbatch improvement.

## Raw evidence

- `ubatch-ladder-4k/ub2/` — complete arm with command, before/after telemetry, periodic samples, log, and result
- `ubatch-ladder-4k/ub4/` — complete arm with equivalent evidence
- `ubatch-ladder-4k/ub8/` — raw command/log/baseline plus `safety-stop.json`; the outer experiment process was intentionally terminated before in-memory periodic samples could flush
