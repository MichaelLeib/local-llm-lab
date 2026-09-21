# EXP-020 — Bonsai 2 27B vs Ornith Q5

## Reconciled predecessor evidence

The prior DEEP lane was **not Bonsai 2**. It was the predecessor `prism-ml/Ternary-Bonsai-27B-mlx-2bit` (Ternary/Bonsai generation 1), previously configured at port 8902. Inherited directional measurements were approximately 2–4 tok/s decode and 140–190 tok/s prefill, with an approximately 8.5 GB payload and an MLX configuration intended to serve about 61K tokens under Hermes's configured 64K floor. It did not complete reproducible Hermes-scale deep-research jobs and was demoted to explicit opt-in. The old 7.94 GiB cache was intentionally deleted on 2026-09-18.

Those predecessor results are historical context only. Bonsai 2 has a rotated/Hadamard ternary representation; PTQ1_0/PQ2_0 require Prism's llama.cpp fork. Stock llama.cpp is invalid for this model because its apparent Q2_0 loading path can emit gibberish.

## Acquired EXP-020 candidate

- Repository: `prism-ml/Ternary-Bonsai-2-27B-gguf`
- Artifact: `Ternary-Bonsai-2-27B-PTQ1_0.gguf`
- Artifact size: `5,946,648,928` bytes
- SHA-256: `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3`
- Runtime: Prism llama.cpp, `0.2.0-dev`, build `10709`, commit `9a9394a89`, Metal arm64 release
- Runtime archive and binary hashes: `raw/prism-runtime-sha256.txt`
- Manifest snapshot: `raw/bonsai2-manifest.json` (PTQ1_0=5,946,648,928 bytes; PQ2_0=7,206,168,928 bytes)

## Bounded PTQ1_0 smoke — 8K runtime context

- Isolated loopback port `8920`, `-ngl 99`, `-np 1`, Flash Attention on, Prism runtime.
- Short 78-token prompt completed coherently, including separately surfaced reasoning content.
- Short-prompt prefill: **23.55 tok/s**.
- Decode: **7.96 tok/s** for a 160-token completion with a 512-token reasoning cap.
- A first populated-prompt attempt failed safely: with `-b 1024 -ub 512`, the Metal backend returned `Insufficient Memory` during a roughly 1,074-token prompt request and HTTP 500. No long-context claim follows from this.
- The server was stopped immediately and the raw log preserves the failure at `raw/server-Ternary-Bonsai-2-27B-PTQ1_0-ctx8192.log`.

## Safety state

- EXP-020 has not run Hermes, tool, autonomy, or long-context tests.
- Root cause of the Q6 restarts: a still-active API-source EXP-019 session (`api_1789839626_dc1a3755`), not a LaunchAgent, cron job, or FAST/DEEP lane manager. Its recorded commands explicitly invoked `scripts/ornith-server.sh start` for the Q6 artifact on port 8919 (both 32K and 64K variants), and orphaned the resulting server after its short shell controller exited.
- The stale session was ended through the profile-scoped local API and its currently resident Q6 server was terminated. It nevertheless continued to issue Q6 starts, so the obsolete Q6 artifact has a temporary mode-`000` safety quarantine. Frozen Q5 remains mode `644` and is unaffected. Restore Q6 only after the stale session is confirmed no longer issuing work.
- No Q6 listener or local inference process remained during a 35-second quarantine check; host free memory recovered to 78%.
- The reduced `-b 128 -ub 64` recovery arm subsequently qualified direct 8K, 16K, and 32K populated contexts without swap growth, including 29,977 populated tokens at 32K. See `REPORT.md` for the full measured table.
- Final runtime decision: Bonsai is not promoted. Hermes requires a 64K admission context; FP16 KV at 64K left 9% memory free idle, and the Q8-KV 64K variant failed the first genuine Hermes read/write/reread terminal loop under severe pageout/memory pressure. Bonsai server was stopped and the report preserves raw evidence.
