# EXP-006 thermal/runbook (approval-gated)

Do not execute until the user explicitly authorizes inference and the short probe passes.

- Establish a clean swap/memory-pressure baseline.
- Run a controlled text-only generation long enough to expose performance drift.
- Record timestamped decode rate, process/Metal footprint, swap, memory pressure, CPU/GPU/thermal proxies available on this Mac, and SSD read volume/throughput where observable.
- Do not change voltage, clock limits, or system thermal controls.
- Keep the server loopback-only and stop on severe pressure, rapid swap growth, instability, or user-reported disruption.
- The user's active water cooling is an experimental condition; report it explicitly rather than comparing to passive-Air claims.
