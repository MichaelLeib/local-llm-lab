# EXP-010 host-failure postmortem — 2026-09-19

## What happened

The Mac restarted after becoming unresponsive during an agent-launched Python workload associated in time with the Laguna qualification. The new boot began at **2026-09-19 17:20:23 CEST**. macOS wrote:

`/Library/Logs/DiagnosticReports/panic-full-2026-09-19-172941.0002.panic`

The panic occurred at **17:29:41 CEST**.

## Kernel evidence

The panic string is a **watchdog timeout**:

> `watchdog timeout: no checkins from watchdogd in 92 seconds`

It is not a literal userspace “out of memory” report. However, the panic snapshot shows an exhausted VM/compression state consistent with the reported severe memory-pressure event:

- only **904 free 16 KiB pages** (`14,811,136` bytes) remained;
- compressor: **100% of segments limit (BAD)**, with **44 swapfiles**;
- **311,840,887** compression events and **270,313,152** decompression events;
- the largest recorded task was `python3.11`, PID **45987**, with `56,261,951,536` bytes recorded as resident memory and process uptime **144.96 s**;
- PID 45987 was spawned by a `bash` child of an agent Python process. The panic artifact has no command line, so it cannot by itself prove which exact Python command owned PID 45987.

The model/runtime process was gone after restart. On post-boot inspection: FAST/DEEP were down, swap was 0 MiB, memory-free was 85%, and the experimental port had no listener.

## Interpretation

This materially strengthens the earlier guarded-arm result. The 6,159-token TurboQuant/tqTe arm had already reached 13% free memory and was stopped before any completion. The new panic evidence shows that an agent-launched Python allocation became sufficiently unresponsive under memory pressure that macOS’s watchdog did not receive a check-in for 92 seconds.

The existing 2-second user-space polling guard is **not a sufficient safety mechanism** for this failure mode: once the allocation/VM path wedges host responsiveness, the supervisor may not get a timely opportunity to kill its child. The original result should therefore be treated as a host-safety failure, not merely a conservative early stop.

## Updated decision

Do not rerun the current Laguna TurboQuant/tqTe configuration on this 16 GiB Mac—not even at a smaller prompt or cache setting—as a normal iterative experiment. No 32K/64K/128K, prefix, Hermes, coding, or DFlash arm is permitted.

This does **not** prove that Laguna’s architecture can never work on any 16 GiB machine. It proves that the currently tested runtime/representation lacks a demonstrably safe resident-memory envelope here. A reopening proposal must first be non-inference work: source-level accounting of the 56 GB allocation path and a static proof of a bounded working set. Only then could an explicitly approved, externally monitored micro-probe be considered.
