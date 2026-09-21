# EXP-008 — 32K FP16 / 8-slot zero-lookahead variant

**Date:** 2026-09-18  
**Base source commit:** `3a892465729406944778a24064664d817617f558`  
**Source state:** isolated EXP-008 worktree only; EXP-005 source/model and Hermes defaults were untouched.

## Hypothesis

Removing the routed-expert prefill pipeline lookahead (`maxPendingDepth: 1 → 0`) permits 8 routed-expert cache slots instead of 16, which may release enough working-set memory to make the same 32K FP16 context workload safe under a 256 MiB incremental-swap guard.

## Changed variables

This is explicitly a **two-part runtime variant**, not a pure slot-count comparison:

1. routed-expert cache slots: `16 → 8`;
2. prefill routed-tile maximum pending depth: `1 → 0`.

The scheduler retains `tileExperts = 8`; a depth of zero drains each issued tile before issuing the next, so one tile can fit in 8 slots. A focused unit test was added for the zero-depth decision and 8-slot budget condition.

## Preserved workload

- FP16 KV;
- max context 32,768;
- fill fraction 0.78 (51,227-byte prompt);
- `--max-new 64`;
- `--prefill-chunk auto`;
- `--expert-cache-policy lfu-aging`;
- temperature 0, seed 12345;
- isolated local CLI, no concurrent model process;
- loopback server/prefix probe would only run after a successful CLI phase;
- stop on system swap growth above 256 MiB.

## Build and test evidence

- `swift build -c release --product slipstream`: passed.
- `swift build -c release --product slipstream-server`: passed.
- `git diff --check`: passed.
- Focused `swift test --filter PrefillRoutedTileSchedulerTests/zeroDepthSchedulerDrainsBeforePrefetching` could not execute because the package test build reaches unrelated macOS UI targets whose Command Line Tools installation lacks the `SwiftUIMacros` / `PreviewsMacros` plugins. The failure occurred in `TurboFieldfareApp/Mac/*`, not the changed core scheduler source. This is a validation limitation, not a passing unit-test result.

Patch and release hashes:

```text
24de9a8a16b101ef393ee46e70a5ff65f474410d8ba6a84e1054385b1bb30b21  slipstream
a4680dc39694a17aa4d7344071999f581e73aa1928319276011d533f23c2d6fa  slipstream-server
eef98d0ca62706a46041e1208db993c58b012c8583876749d87593dac632d319  patches/8-slot-zero-lookahead.patch
```

## 32K result

**Outcome: stopped for swap; not healthy; do not run 64K.**

| Metric | Result |
|---|---:|
| CLI wall time | 102.577 s |
| Completion/footer | none (prefill not completed) |
| Needle correctness | not measured |
| Server/prefix-cache phase | not started |
| Baseline system swap | 1,307.12 MiB |
| Maximum system-swap delta | **+310.44 MiB** |
| Guard | 256 MiB; exceeded and sent SIGTERM |
| Post-run system swap | 1,617.56 MiB |
| Minimum reported free memory | 25% |
| Additional `vm_stat` pageouts | 946 pages |
| Additional `vm_stat` swapouts | 21,404 pages |
| Peak sampled Slipstream RSS | 458.6 MiB |

The arm entered swap at approximately 51 seconds and crossed the guard at the 102.6-second sample. The raw runner result is `status: "stopped_for_swap"`, CLI return code `-15`.

## Comparison caveat

The original 16-slot arm also stopped for swap, but started from a different system-swap baseline (990.25 MiB versus 1,307.12 MiB) and used the original depth-1 scheduler. Its 929.558-second time to termination, +436.87 MiB maximum swap delta, and 534.7 MiB peak sampled RSS are therefore **not an apples-to-apples performance or memory reduction estimate**. The 8-slot variant's RSS sampling was about 76.1 MiB lower, but it does not establish the requested 0.5–1 GiB physical-footprint reduction and must not be interpreted as one.

## Decision

The minimal 8-slot/zero-lookahead variant enables the workload but fails the operational criterion at 32K. It is not eligible for a 64K arm, and this result does not justify a 128K FP16 or Q8-KV implementation yet. The next useful experiment needs a controlled, low-background-load baseline before comparing runtime/cache designs.

## Raw artifacts

- `runs/ctx-32768-slots-8-20260918T144546Z/summary.json`
- `runs/ctx-32768-slots-8-20260918T144546Z/baseline.json`
- `runs/ctx-32768-slots-8-20260918T144546Z/post-run.json`
- `patches/8-slot-zero-lookahead.patch`
