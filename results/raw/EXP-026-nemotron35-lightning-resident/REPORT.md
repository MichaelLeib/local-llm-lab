# EXP-026 — Resident Nemotron 3.5 Lightning 30B-A3B on 16 GiB M3 Air

**Branch:** 1 — resident aggressively compressed weights only. SSD/expert streaming is explicitly out of scope.

## Candidate decision before acquisition

First candidate: `vcruz305/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF` / `Nemotron-3.5-Lightning-30B-A3B-MIXED-Q2_0-Q4_0-2.47BPW.gguf`.

- HF LFS size: 9,759,494,016 bytes (9.09 GiB)
- Published LFS SHA-256/OID: `5128d93446d9bf416a1d22eb466caea193a2c6537c96a841398959b45aaa280a`
- It is the only currently discovered resident artifact below 10 GiB. The same source's 2.97-BPW mixed artifact is 11.735 GB; conventional / IQ4 artifacts discovered were 16.8–18.1+ GiB, and APEX / UD candidates 14.7+ GiB.
- This is an admission candidate, not an intelligence claim. No controlled quality/perplexity data for the publisher's bespoke mixed allocation was supplied. Higher-quality formats will be investigated only after it proves a healthy populated ≥64K envelope.

## Architecture-derived lower bounds

Vendor/NVIDIA Nano documentation and this Lightning family's config describe 30B total / 3B active hybrid MoE, 6 attention layers, two KV heads, 128-dim KV heads, and Mamba/SSM layers. FP16 attention-KV lower bound is 6,144 bytes/token: 48 MiB (8K), 96 MiB (16K), 192 MiB (32K), 288 MiB (48K), 384 MiB (64K), 576 MiB (96K), and 768 MiB (128K). Q8 K/V halves those values; Q4 quarters them. These omit recurrent state, weights actually faulted/resident in Metal, graph/workspace, macOS, and Hermes.

## Safety contract

- FAST was stopped and port 8901 verified closed before this experiment.
- Baseline after stopping FAST: 63% free, 1,506.06 MiB swap used, pageouts 407,637.
- Every **llama.cpp** server arm uses exactly one sequence, loopback only, Q8 KV, flash attention, batch 128 / ubatch 64, no vision, no mlock, and the independent `safety_guard.py`.
- Hard llama.cpp first-arm guard: terminate candidate process below 15% free, >384 MiB incremental swap, or >2,000 incremental pageouts. The later TensorSharp compatibility-only arm used a more conservative 25% free floor and never reached weight allocation.

## Initial ladder

1. 8K direct correctness/load gate
2. 16K populated retrieval
3. 32K populated retrieval
4. 48K populated retrieval
5. 64K populated retrieval only if preceding arms remain clearly healthy

96K/128K, API/tool, and isolated Hermes admission are contingent on a healthy ≥64K result.

## Reproduced first-load / 8K direct gate

- Download was verified byte-for-byte against the published LFS OID: SHA-256 `5128d93446d9bf416a1d22eb466caea193a2c6537c96a841398959b45aaa280a`.
- Runtime: isolated upstream `ggml-org/llama.cpp` commit `96550613656e7f024df65f91cf8b2d80a83cf09e`, `llama-server` `0.4.1-dev (build 1, commit 9655061)`, AppleClang 21 / Darwin arm64. This is the current upstream Metal path.
- Exact server flags: `--host 127.0.0.1 --port 8926 -ngl 999 -c 8192 -np 1 -b 128 -ub 32 -fa on -ctk q8_0 -ctv q8_0 --metrics --alias nemotron35-exp026`. There was one sequence; no vision, draft, mlock, external listener, or other local model lane.
- The model loaded and produced a finite response. A raw 16-token completion probe took 303.96 ms prompt time (52.64 prompt tok/s) and 32 output tokens in 923.40 ms (33.57 tok/s); wall time was 1.239 s. It surfaced `chat_format: Content-only`, emitted a multiple-choice list containing `42` rather than the requested one-sentence answer, so it is only a finite-output/tokenizer smoke—not a template or intelligence pass.

## Safety stop — no populated-context admission

The independent guard began while the resident model was loaded. Its first sample was already **13% system-wide free memory**, **1,924 MiB swap used**, and **151,765 compressor pages**. The pre-experiment quiet baseline was 63% free, 1,506.06 MiB swap, and 407,637 pageouts. The configured guard terminated the server immediately because free memory was below its 15% hard floor; it never allowed the 8K populated retrieval request to reach the runtime.

Against the quiet pre-arm observation, the first loaded sample also had **+417.94 MiB swap used** and **+77,036 pageouts** (about 1,203.69 MiB at the 16-KiB page size). Those counters were observed across the model arm rather than atomically sampled immediately before allocation, so they are recorded as associated pressure rather than a clean causal delta. After termination and recovery, the Mac returned to 76% free with 1,827.56 MiB swap and 484,682 pageouts. Comparing the live loaded and recovered observations, the candidate consumed roughly 63 percentage points of immediately free unified memory and coincided with about 584 MiB of compressor growth; macOS reclaimed some swap after termination. The observations reinforce—not soften—the hard free-memory stop.

This is a resident-weight/Metal unified-memory admission failure before context state becomes material. Q8 KV would have been only 24/48/96/144/192/288/384 MiB for 8K/16K/32K/48K/64K/96K/128K respectively, but there was no safe headroom to populate even 8K. Reducing `-b`/`-ub`, applying lower KV precision, or prefix caching cannot recover the multi-GiB resident-memory deficit shown before prefill. No 8K populated retrieval, 16–128K ladder, API/tool-call, Hermes, warm-cache, or quality qualification is claimed.

## TensorSharp ggml_metal compatibility check

The installed isolated TensorSharp `ggml_metal` server was also arm-tested, with no other model resident, `MAX_CONTEXT=8192`, `--max-tokens 256`, loopback port 8927, and a stricter external guard (25% free floor). It correctly parsed the architecture as `nemotron_h_moe`: 52 layers, hidden 2688, six attention + 23 Mamba2 + 23 MoE FFN layers, 128 experts/top-6, KV heads=2/head dimension=128, and SSM state details (`dInner=4096`, `dState=128`). It then refused the file after **584.1 ms**, before loading weights or moving system memory: `Unknown GGML tensor type: 42`.

Thus TensorSharp is not an available lower-memory alternate runtime for this published 2.47-bpw artifact as installed. A future TensorSharp GGML reader upgrade that supports tensor type 42 would merit a *new* guarded first-load comparison, but does not negate the measured current llama.cpp resident failure.

## Decision

**REJECTED — Branch 1 resident Nemotron 3.5 Lightning on this 16 GiB Mac.** The highest-quality available <10-GiB resident GGUF (the 9.09-GiB 2.47-bpw mixed Q2/Q4) is already unsafe at first load. A smaller quantization would need to remove several GiB of actual unified-memory pressure while preserving a model whose raw completion smoke already needs template/quality validation; that is outside a credible quality-preserving next step. The 11.735-GB 2.97-bpw candidate and all higher-quality options are excluded by stronger weight residency pressure.

Reopen Branch 1 only with a materially different bounded-working-set Metal/runtime implementation that demonstrably avoids duplicate/resident weight pressure, a much larger unified-memory Mac (at least 24–32 GiB should be re-profiled), or a separately approved non-resident/SSD expert-streaming branch. Do not repurpose this result into that separate branch.

## Artifacts

Published evidence includes `guard-8k.jsonl`, `server-8k.log`, `small-gate.json`, `model.sha256`, and `make_retrieval_corpus.py`. The pinned `source/llama.cpp/` checkout, compiled `build/` tree, and GGUF weights are retained locally but deliberately excluded from Git history. The corpus generator remains unexecuted at long context because the guard correctly stopped before a populated admission.
