# EXP-014 — Qwen3.6 / Slipstream optimization campaign closeout

**Completed:** 2026-09-19  
**Machine:** 15-inch M3 MacBook Air (2024), 16 GiB unified memory, macOS 27.0  
**Status:** **no promotion**. The existing Qwen3.6/Slipstream configuration remains the best measured streamed-MoE arm, but is not yet a practical full Hermes/autonomous-coding lane on this 16 GiB host.

## 1. Executive conclusion

The defensible configuration is still the already-pinned Qwen3.6 setup, not a newly faster build:

- **Decode:** 7.5–8.4 tok/s in clean short standalone controls; 6.1–6.9 tok/s in realistic slim-Hermes tool turns.
- **Cold Hermes:** 107.87 s TTFT at 5,003 tokens in EXP-005; a later current-local-dev slim coding arm was 126.53 s at 5,302 tokens.
- **Warm Hermes:** verified 3.12–4.50 s TTFT with 98–99% exact-prefix reuse.
- **Context:** 16K short control completed, but populated 32K FP16 prefill was safety-stopped twice (+436.87 MiB at 16 slots; +310.44 MiB with an isolated 8-slot/zero-lookahead variant). **64K is technically supported by the server, but is not practically demonstrated and must not be claimed.**
- **Current revalidation:** 2026-09-19 16-slot server load started from 27.74% measured free pages and reduced this metric to 0.41% before the 2K-request sweep could run. The guard terminated the client after 3.56 s with **0 MiB swap growth**, and the server was cleanly stopped. This is a resource-state safety stop, not a performance score.

The model is materially more usable than the 2.4–2.8 tok/s Qwen3.8 Flash-Next streamed arm, but it does **not** meet the requested 32K+/64K autonomous-agent criterion. Do not proceed to a serious autonomous coding/research benchmark yet.

## 2. Winning (retained) configuration

```text
Runtime source: https://github.com/dwijenpatel/slipstream.git
Runtime commit: 3a892465729406944778a24064664d817617f558
Model source: mlx-community/Qwen3.6-35B-A3B-4bit
Model revision: 38740b847e4cb78f352aba30aa41c76e08e6eb46
Installed artifact: results/raw/EXP-005/model/qwen36.gturbo
Quantization: native MLX 4-bit input, Slipstream .gturbo repack
Expert cache: 16 slots
Policy: lfu-aging
Prefill chunk: auto
KV: FP16/default
Server context used for Hermes: 8192
Prompt cache: single-prefix
Transport: OpenAI Chat Completions only (/v1/chat/completions)
```

Reference isolated launch:

```bash
/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/source/slipstream/.build/out/Products/Release/slipstream-server \
  --model /Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-005/model/qwen36.gturbo \
  --port 8901 --max-context 8192 --prompt-cache-mode single-prefix \
  --expert-cache-slots 16 --expert-cache-policy lfu-aging
```

For Hermes, use only the approved `local-qwen-coder` wrapper; it creates an isolated overlay, uses Chat Completions and the slim terminal/file tool shape, refuses to evict FAST/DEEP, and unloads only its own server. The normal `local-dev` profile remains unchanged.

## 3. Before vs. after / evidence table

| Measure | Best evidence | Interpretation |
|---|---:|---|
| Short standalone decode | 8.417 tok/s (273 prompt tokens); 8.219 (546); 7.531 (1,105); 5.903 (2,210) | Clean EXP-005 controls; no post-reboot swap growth |
| Representative decode | 8.4 tok/s | EXP-012 direct API server timing, short request |
| 1K prefill | 15.14 s / 1,105 tokens | Effective rate includes fixed load/start effects |
| 2K prefill | 37.99 s / 2,210 tokens | This is the useful cold standalone reference |
| 4K / 8K prefill | not cleanly completed as standalone sweep | Full Hermes evidence below is more relevant |
| Cold Hermes TTFT | 107.87 s / 5,003 tokens | EXP-005 constrained terminal tool loop |
| Later cold coding TTFT | 126.53 s / 5,302 tokens | EXP-012 five-tool coding arm |
| Cached Hermes TTFT | 4.50 s, then 4.34 s | First post-tool continuations |
| Resumed cached Hermes TTFT | 3.12 s tool call; 3.77 s final continuation | Native `pwd` tool loop |
| 16K | Completed short 2,157-token control | 35.52 s prefill, 5.519 tok/s decode; non-clean inherited swap baseline |
| 32K | safety-stopped | populated ~25.6K prefill: +436.87 MiB swap, 929.56 s; no completion |
| 32K 8-slot variant | safety-stopped | required prefill scheduler lookahead change; +310.44 MiB swap, 102.58 s |
| 48K / 64K | not run | scientifically and operationally unjustified after 32K failures |
| Persistent disk KV | functional but slower decode | 1,196-token snapshot restored in 0.04 s but decoded 1.546 tok/s |
| Current 2026-09-19 recheck | guard stop | 16 slots/server load made measured free pages 27.74% → 0.41%; no swap growth; no response produced |

## 4. Major branches, including negative results

### Phase 0 — recovered state

- Existing Slipstream and model are preserved; no default Hermes, FAST, or DEEP change was made.
- Initial live state for EXP-014: FAST down, DEEP down, no Slipstream/llama/MLX inference process, 1,811.25 MiB existing macOS swap, 27.74% free pages, and 17 GiB immediately available root storage.
- The 19.55 GB Qwen `.gturbo` is intact. Disk space is not sufficient for a duplicate Qwen representation plus safe system reserve.

### Phase 1 — baseline

EXP-005 already supplies the clean controlled baseline: clean first probe exact `READY.`, 8.404 tok/s, 14.22 s 5-token cold prefill, 1.46 GB sampled footprint, and zero swap growth. Its four-arm clean prefill/decode sweep and real Hermes tool loop are retained above.

### Phase 2 — upstream

A fresh remote inspection was performed in `EXP-014/source/upstream`.

- `origin/main` resolves exactly to **`3a892465729406944778a24064664d817617f558`**, the previously pinned EXP-005/008 runtime.
- Therefore no newer upstream Qwen3.6 implementation exists to build/test against this baseline. The pinned runtime already contains current features relevant here: LFU-aging default, configurable `lfu-aging|lfu|lru`, GPUClockHold, expert-I/O telemetry, route/cache-policy analysis, single-prefix server reuse, and Qwen prefill path.

### Phases 3–5 — expert cache, policies, GPU/I/O

- Previous 16-slot configuration is the only fully supported and safety-qualified populated-context condition.
- A pure 8-slot 32K request is invalid in this runtime: Qwen prefill depth 1 needs two 8-expert routed tiles (16 slots). It failed at configuration admission without a performance or memory result.
- The isolated zero-lookahead modification enabled 8 slots, but it still safety-stopped at +310.44 MiB swap during the same populated 32K prefill.
- EXP-014 intended a fresh 16/24/32-slot + LRU/LFU-aging short-prompt server sweep. It was stopped immediately at the 16-slot control because free-page percentage dropped to 0.41% while no response had yet completed. Escalating to 24/32/48/64 slots would be unsafe and would not isolate cache policy.
- No new GPU-clock setting was enabled. `GPUClockHold` exists in the pinned upstream but has no local end-to-end win measurement on this host; applying it now would add a variable to a resource-unsafe system state.

### Phases 6–9 — prefill, prefix, context, KV

- Cold prefill remains the dominant latency: 41.9 tok/s reported in the 5,302-token Hermes request, yielding 126.53 s TTFT.
- In-memory exact-prefix reuse works and is the real operational win: 5,347 of 5,401 input tokens cached in EXP-012, followed by 4.34 s TTFT. Further turns cached 5,437/5,465 and 5,509/5,547 tokens, with 3.12/3.77 s TTFT.
- Disk snapshot restores are fast but have unacceptable 1.546 tok/s subsequent decode in the only clean measurement. Do not use disk KV as an interactive default.
- FP16 KV is only 20 KiB/token because this hybrid has 10 full-attention layers; theoretical allocation is 1.25 GiB at 64K. The observed 32K failure is nevertheless a whole-host prefill envelope failure (temporary prefill work + expert/cache/file-cache interaction + host state), not proof that KV alone is the cause.
- KV quantization is not justified: there is no completed FP16 32K baseline against which to measure quality/memory benefit. It cannot be promoted as a remedy for the current failed populated-context prefill.

### Phases 10 and 13 — Hermes and autonomy

- Real native Hermes tool use is verified in the slim coding overlay: `terminal(date)` and later `terminal(pwd)` both executed, results returned with the correct IDs, and each loop completed with normal stop behavior.
- The normal full 13-tool `local-dev` shape is incompatible with the 8,192-token server ceiling before prefill; direct server returned correct `context_length_exceeded` rather than a model failure.
- A full safe autonomous coding/research smoke test was not run. The required practical 32K envelope is absent, and the current short control is resource-unsafe. Running a disposable autonomous benchmark would produce a misleading one-off short-context score and risk host usability.

## 5. Context conclusion

| Category | Result |
|---|---|
| Technically allocatable | Server supports 4K, 8K, 16K, 32K, and 64K; source audit finds no 64K position/index blocker. |
| Technically completable | Short 16K-context control completed. A populated ~25.6K request did not complete before safety termination. |
| Practically usable | **8K server / ~5K full Hermes slim-prefix only**, with in-memory prefix reuse. No practical 32K result exists; 48K/64K are rejected for this machine/configuration. |

## 6. Remaining bottleneck and decision

The limiting factor is **cold prefill plus whole-system unified-memory pressure**, not sustained short decode and not a missing upstream revision. In-memory prefix caching converts repeated turns into useful 3–5 s TTFT, but cannot repair first-turn latency or provide autonomous-session context growth on 16 GiB.

**Next recommendation: do not spend more time on Qwen3.6 micro-optimizations.** Keep the isolated `local-qwen-coder` wrapper as a narrow, warm-session coding option. The rational next experiment is a model/runtime whose real populated 4K–8K safety gate passes with material free-memory headroom, before attempting any full autonomous coding/research evaluation. Qwen3.6 itself should only be reopened after an evidence-backed source-level reduction in long-prefill working memory, not after a larger cache, an aggressive KV quant, or another speculative knob.

## 7. Reproducibility artifacts

- Prior raw controls: `results/raw/EXP-005/`, `results/raw/EXP-008/`, and `results/raw/EXP-012-qwen36-local-dev/`
- Current upstream inspection: `results/raw/EXP-014-qwen36-slipstream-campaign/source/upstream/`
- Current guarded revalidation: `results/raw/EXP-014-qwen36-slipstream-campaign/raw/cache-sweep-20260919T071850Z/`
- Guarded sweep script: `results/raw/EXP-014-qwen36-slipstream-campaign/run_cache_sweep.py`
