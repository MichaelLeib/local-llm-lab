# ERNIE retirement receipt

**Action:** User-directed removal of ERNIE model payloads after EXP-017 completion.

## Final documented result

- Best measured streamed Q4 configuration: `--moe-stream-cache 30s`, `-ub 2`, 3,982-token populated input, 8,192-token allocation.
- Performance: 8.0 prompt tok/s; 6.0 decode tok/s.
- Safety boundary: 20% minimum free memory at 30 slots. Higher 34/38-slot arms were deliberately not run; sufficient headroom was absent.
- Classification: **expert residency materially helps but ERNIE remains operationally insufficient** on this 16 GB M3.
- Full evidence: `REPORT.md`, `CONTEXT-1K-4K-REPORT.md`, `UBATCH-LADDER-REPORT.md`, and `EXPERT-SLOT-LADDER-REPORT.md` in this directory; EXP-016 compatibility evidence remains under `../EXP-016-small-moe-feasibility/ernie/`.

## Payload deletion scope

- Delete only redownloadable ERNIE model payloads.
- Primary GGUF payload: `results/raw/EXP-016-small-moe-feasibility/ernie/gguf/model/ERNIE-4.5-21B-A3B-Thinking-Q4_K_M.gguf`
- Recorded size before deletion: `13,331,018,624` bytes.
- Preserve reports, raw measurement JSON/CSV/log evidence, scripts, runtime source, checksums, and architecture notes.

This receipt is intentionally written before deletion so the conclusion and artifact provenance survive the storage cleanup.