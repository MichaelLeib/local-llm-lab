# EXP-017 — ERNIE streamed-GGUF populated-context test

**Scope:** staged 1K then 4K populated retrieval probes after the successful 512-token smoke gate. No API, Hermes, tool-call, coding, or research-quality testing.

## Configuration held constant

- ERNIE-4.5-21B-A3B-Thinking Q4_K_M GGUF
- Local arm64/Metal streamed-MoE runtime built from `1248fd8fa8cfebaece5ea992e4d951c1e18bb9d5`, with the isolated ERNIE graph-reservation compatibility patch from the smoke gate
- `--moe-stream-cache 18s --moe-stream-io-threads 2 --moe-stream-direct --no-mmap --no-warmup --fit off -ngl 99 -b 512 -ub 1`
- `temp=0`, `seed=1234`, generated-token cap 128
- Objective host abort guard: free memory below 6%

## Results

| Arm | Populated input | Allocated context | Elapsed | Prompt rate | Decode rate | Minimum free memory | Swap delta | Swapouts | Retrieval result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1K | 1,023 tokens | 2,048 | 267.88 s | 4.5 tok/s | 4.3 tok/s | 42% | -16 MiB | 0 | Model explicitly reasoned that the code was `ORBIT-271`; its final visible answer was truncated at `ORBIT-27` by the 128-token thinking/output budget. **Not formally correct.** |
| 4K | 3,982 tokens | 8,192 | 943.29 s | 4.4 tok/s | 4.2 tok/s | 38% | -24 MiB | 0 | Model explicitly identified `cedar-914` in its reasoning, then continued reasoning when the 128-token cap ended. **No final structured answer; not formally correct.** |

Additional OS counters:

| Arm | Pageouts | Swapins |
|---|---:|---:|
| 1K | +1,615 | +1,032 |
| 4K | +4,951 | +1,027 |

The system never crossed the protective threshold, never produced a swapout, and returned to **73% free memory** after the process exited. FAST and DEEP remained down; no residual `llama-cli`, `llama-server`, or rapid-mlx process remained.

## Interpretation

1. **Allocatable and completable:** PASS through approximately 4K populated input on the streamed-expert path.
2. **System health:** tight but not pathological in this small-context range. Minimum observed free-memory percentage was 38%; no incremental swap consumption or swapout occurred. The high page-in/page-out activity and slow 4K wall time demonstrate substantial SSD-backed traffic and make this unsuitable for promotion yet.
3. **Retrieval correctness:** not proven. Both arms semantically located the needle, but neither returned the requested final exact answer before the fixed 128-token cap. This is a generation-budget/output-contract limitation in this probe, not evidence of successful formal retrieval.
4. **Speed:** generation stayed near 4.2 tok/s, meeting the campaign's experimental floor but only barely. The 3,982-token prefill took about 15.7 minutes, so the present `18s` streamed-cache/`-ub 1` configuration is **not operationally acceptable** for a primary Hermes agent even though it is memory-safe at this range.

## Raw evidence

- `context-retrieval-1k-4k-rerun1/1k-populated/`
- `context-retrieval-1k-4k-rerun1/4k-populated/`
- `context-retrieval-1k-4k-rerun1/summary.json`

The earlier `context-retrieval-1k-4k/` directory is retained as a harness-preflight artifact: tokenizer output was parsed with the wrong wording, so no inference was launched in that directory.
