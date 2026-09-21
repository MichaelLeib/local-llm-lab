# EXP-004 compatibility and disk gate

Date: 2026-09-17

## Result

**Blocked before model download.** ExpertCache's pinned source and patch are compatible with the Mac's software toolchain, but the internal SSD has only approximately 20 GiB free. The documented 16 GiB runbook requires at least 80 GB free; the exact GPT-OSS-120B MXFP4 checkpoint is 63,387,346,208 bytes (~59.0 GiB binary) before temporary download/build headroom.

## Verified prerequisites

- Host: MacBook Air Mac15,13, Apple M3, 16 GiB, macOS 27.0 (26A428).
- Node.js v26.8.1 (requirement >=22).
- Python 3.11.16 available; project-local `.venv` uses NumPy 1.26.4 as documented.
- CMake 4.4.3, AppleClang 21, and `/Library/Developer/CommandLineTools` present.
- ExpertCache checkout: `e6a3b940a8cd8465be0cd8cdf0f39829ebfa6ade`.
- Pinned llama.cpp checkout: `7e1e28cae36d41fe7bbe9dae7c9625de6565c063`.
- ExpertCache patch applied cleanly; SHA-256 matches `6bb978ab189ded46b131edea81fbe0740d7d527797be553f91312e4704f76a63`.
- `npm run check`: pass.
- `npm test`: 29/29 pass after installing only project-local `numpy==1.26.4`.

## Target model verified from manifest and official config

- Repository: `ggml-org/gpt-oss-120b-GGUF`.
- Revision: `238abdd290bb874b90a5da1b4549881b7d05c091`.
- File: `gpt-oss-120b-MXFP4.gguf`.
- Expected bytes: `63387346208`.
- Expected SHA-256: `582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d`.
- Architecture: `gpt_oss`, 36 layers, 128 experts, 4 experts/token, hidden size 2880, MXFP4, 131072 context.

## Download decision

Do not download yet. No GPT-OSS-120B artifact is present in the local HF cache. The remaining free space is insufficient for the checkpoint, temporary download behavior, source/build artifacts, logs, and safe operating reserve. A later download requires explicit approval after freeing enough internal SSD space; the target should be at least the runbook's 80 GB free, not merely the 59 GiB model size.

## Preserved EXP-003 baseline

The verified Ornith baseline and Hermes bridge result are frozen in `phase1-freeze.json` and `results/raw/EXP-003/bridge-fix/summary.json`. EXP-003 source and defaults were not modified.

## Source-layout note

The pinned llama.cpp checkout is kept as the sibling directory `results/raw/EXP-004/source/llama.cpp-expertcache/`, separate from the ExpertCache Node package. This is intentional: placing llama.cpp inside the Node package makes `node --test` recurse into llama.cpp UI tests that require an unrelated `vitest` dependency.
