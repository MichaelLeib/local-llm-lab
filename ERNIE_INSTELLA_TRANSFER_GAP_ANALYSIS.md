# ERNIE and Instella transfer gap analysis

**Scope.** Static source/report study only; no model was launched. “Proven” below means the local lab has a recorded build or measured run for the named Qwen/ExpertCache experiment. It does **not** make a mechanism compatible with another architecture.

## Decision summary

| Target | Reuse now | Reuse after an adapter | Do not reuse as-is | 16 GiB M3 implication |
|---|---|---|---|---|
| **ERNIE-4.5-21B-A3B-Thinking** | GGUF/llama.cpp architecture loader; generic CPU-MoE switch; generic OpenAI bridge/harness; ExpertCache-style route tracing and residency telemetry | SSD expert residency for ERNIE Q4/GGUF; native compressed container/repacker; tool parser/template; any KV policy | Slipstream/TinyTitan Qwen kernels and `.gturbo` layout; TurboQuant’s Qwen streaming adapter/KV implementation | Not a runtime candidate in its tested Q4 forms: MLX projected 17.2 GB working set; GGUF reached repeated Metal `Insufficient Memory`. A transfer effort must first lower the resident/KV/activation floor, not tune slot count. |
| **Instella-MoE-16B-A3B-Think** | Publisher `instella-moe` llama.cpp branch (including MLA cache/graph support); generic CPU-MoE; generic server/tool harness | Expert-residency staging only after preserving Instella’s custom MLA and FarSkip graph; lower-bit representation; native compressed container | Qwen linear-attention, GDN, PLE/n-gram, Qwen tool parsers, Qwen-specific TurboQuant kernels | Q4 worked for four tokens but longer decode reached 9% free memory and 9.44 GiB swap. CPU-MoE is a safety fallback, not a performance path; Q3 was correctly not escalated. |

The most transferable deliverable is **a model-neutral residency subsystem and qualification harness**, not one of the existing Qwen runtimes. For both targets, model parsing/forward correctness precedes cache policy work; for ERNIE, memory fit is the immediate blocker, while Instella first needs a lower-bit model plus its custom attention/residual graph retained.

## Target contracts

| Contract | ERNIE | Instella |
|---|---|---|
| Pinned local source/model | `baidu/ERNIE-4.5-21B-A3B-Thinking@4341bb4`; `ernie4_5_moe` | `amd/Instella-MoE-16B-A3B-Think@74d28c1`; custom `InstellaMoEForCausalLM`, config declares `deepseek_v3` |
| Main shape | 28 layers; hidden 2560; 20 Q / 4 KV; 64 routed + 2 shared; top-6; 131,072 positions | 27 layers; hidden 2048; 16 heads; 64 routed + 2 shared; top-6; 32,768 positions |
| Nonstandard graph risk | ERNIE family tensor namespace, shared-expert semantics, attention/RoPE/cache and thinking/tool template must be independently validated | **High:** Gated MLA plus FarSkip-Collective are required forward-graph features; the publisher requires its experimental `instella-moe` llama.cpp branch |
| Tested representations | MLX 4-bit (12.28 GB selected files), then GGUF Q4_K_M (13.33 GB) | GGUF Q4_K_M (10.47 GB); Q3_K_M was planned but deliberately not acquired/run |
| Lab result | rapid-mlx safety gate stopped before inference: projected 17.2 GB / 162% utilization; GGUF Q4 failed Metal graph compute/`llama_decode` with no output | Publisher branch/Metal emitted `<think> First` in four-token arm (~0.5 prompt and generation tok/s); 32-token arm safety-stopped under severe pressure |

The official ERNIE card independently confirms 21B total/3B active, 28 layers, 64/6 routed experts, two shared experts, 131K context, and function-call support. The official Instella card confirms 16B total/2.8B active, 27 layers, top-6 of 64 experts plus two shared experts, Gated MLA, and FarSkip-Collective.

## Transferable mechanisms

| Mechanism and evidence | What it actually does | Qwen architecture coupling | ERNIE work | Instella work |
|---|---|---|---|---|
| **SSD expert residency — EXP-003 fork** | `llama.cpp` Metal/SSD PoC leaves expert tensors in GGUF, reads selected contiguous expert ranges with `pread`, stages them into compact per-layer Metal slots, and maps expert IDs to slots with LRU. Controls include `--moe-n-slots`, `--moe-n-layers`, `--no-mmap`, `--no-warmup`. | Selection is relatively generic: expert count and stride come from tensor shape/stride, and it does not hard-code Qwen’s 40 layers/256 experts/top-8. But it expects routed tensors named with `_exps.`, contiguous GGUF expert-major storage, a shared per-layer slot map, and enough slots for all unique experts in a microbatch. Its Qwen graph hook is around Qwen3.5 `MUL_MAT_ID`. | **Moderate adapter.** Validate ERNIE GGUF tensor triplets/layout, hook its routed-MoE graph, correctly stage both 64 routed and preserve two resident shared experts. Six selected experts mean a first slot count cannot be below unique top-6 demand (plus any batch union). The existing ERNIE loader proves parsing, not this paging path. | **Large adapter.** Use the publisher branch as base, not the Qwen fork. Keep its separate MLA KV/cache and FarSkip graph intact; add staging only at its routed expert projections after validating GGUF layouts/names. Top-6 reduces selected-expert bandwidth versus Qwen top-8/top-10, but does not solve the observed full-model memory pressure. |
| **SSD expert residency — Slipstream / TinyTitan native containers** | Qwen common tensors are resident; routed experts are repacked as page-aligned per-layer blobs. A bounded per-layer cache reads misses from SSD (Slipstream default 64 slots, LFU-aging). TinyTitan's larger native cache reduces traffic but costs unified memory. | **Hard-coded implementation.** Slipstream’s `ModelFamily` has only `gemma4` and `qwen36`; the runtime validates its manifest against compile-time Qwen geometry and Qwen’s 30 GDN + 10 full-attention mask. TinyTitan adds Qwen Flash but remains Qwen-specific (48 layers/512 experts/top-10, GDN/QSA, hyper-connections, PLE table). | **Rebuild required.** Add an ERNIE family, tensor mapper, 28-layer forward graph, attention/cache, MoE router/shared experts, kernels, tokenizer/template, and repacker source entry. Reusing its cache class/receipt/repack transaction logic is practical; reusing the runtime binary/container is not. | **Rebuild required and larger than ERNIE.** Add a full Instella graph: Gated MLA, its cache layout, FarSkip-Collective, 27-layer tensor mapper, MoE/shared experts, tokenizer/template. The native container should be designed from Instella tensors; `.gturbo` is not a general MLX format. |
| **Native compressed formats — `.gturbo` / QPACK / TurboQuant** | `.gturbo` is a runtime-owned layout: resident `model_weights.bin`, per-layer page-aligned `packed_experts/`, manifest, receipt and source fingerprint. It enables range-repack/install and verification without a full raw duplicate. TurboQuant packs rotated/codebook dense weights, quantized/ternary experts, and offers streaming readers. Swiftlet’s QPACK is another runtime-specific container. | `.gturbo` is schema- and graph-coupled, not a portable quantization standard. Slipstream source exposes only `gemma4` and `qwen36`; its Qwen expert blob/manifest assumptions include Qwen stride/quantization and Qwen kernel shapes. TurboQuant has per-architecture rotation configs and swaps only particular `switch_mlp.{gate,up,down}_proj` tensors. | **New converter and proof chain.** Preserve official ERNIE tensor names/quant scales, choose a target quantizer, pack all three routed projections and identify shared-expert tensors as resident, create an ERNIE manifest plus loader equivalence tests against a reference. Do not reinterpret Qwen `.gturbo`, qpack, or TQ weights as ERNIE weights. | **New converter plus custom-op support.** Same routing projection work, but additionally retain/quantize Gated MLA and FarSkip tensors without changing semantics. Existing Instella GGUF is a better starting point than an MLX container because its publisher runtime already supports its graph. |
| **KV compression / prefix persistence — EXP-005, EXP-010, EXP-015, TurboQuant** | Slipstream exact-prompt snapshots serialize full runtime state; Qwen linear-attention state must be included and cannot be token-sliced. Its server cache is one in-process verified prefix. TurboQuant has compressed KV layers and optional disk prompt cache; compressed KV trades memory/quality/speed and must be measured. | **Very architecture-specific.** Qwen3.6’s 30 GDN layers make its state fixed-size and leave only 10 full-attention KV layers growing with context. TurboQuant/Laguna’s hybrid sliding/global cache has different bytes/token and a K8 tradeoff. | **Build and benchmark separately.** Do not use Qwen snapshot serialization. Define ERNIE’s attention KV layout, RoPE/scaling, cache quantizer, snapshot version/domain, exact prefix/hash rules, and equivalence tests. Since ERNIE’s 131K advertised context does not imply a 16 GiB usable cache, first measure short FP16 prefill; then compare a low-risk K/V quantization arm against exact output/quality. | **Use the publisher MLA path first.** The branch already contains MLA-specific KV cache/context machinery; preserve its latent cache format. A compressed/persistent cache needs an Instella-specific serialization and correctness test. Do not apply GDN/hybrid sliding-cache assumptions to MLA. |
| **CPU-MoE — EXP-016 North and llama.cpp** | `--cpu-moe`/CPU-only execution leaves MoE or all layers on CPU to avoid Metal allocation failures. The North Q3 CPU-only fallback completed endpoint/tool smoke, demonstrating a safety/compatibility escape hatch. | Generic llama.cpp feature, but performance depends on graph/backends and model format. It does not make a GPU graph fit, nor provide SSD staging automatically. | **Possible diagnostic fallback only.** Test only after a short model-load gate; ERNIE’s Q4 Metal failure and MLX projection make CPU-MoE useful to isolate Metal versus model-memory failure, not a route to interactive 131K Hermes use. | **Possible diagnostic fallback only.** The recorded Instella arm already used `--cpu-moe --n-gpu-layers 99` and was ~0.5 tok/s before longer-arm pressure. A fully CPU model may be safer but should be expected to be noninteractive; run only as a correctness/endpoint diagnostic. |
| **Metal kernels — Slipstream/TinyTitan/ExpertCache/TurboQuant** | Existing code includes fused int4 GEMV/QKV, GDN/attention, MoE grouping and SSD staging (Swift/Metal), TurboQuant polar quant/dequant/gather kernels (MLX Metal), and ExpertCache MXFP4 direct selected-expert views. | Nearly all are shape/quant/layout/operator coupled. Slipstream specializes Qwen decode GEMV shapes and GDN; TinyTitan specializes Qwen Flash’s GDN/QSA/PLE; TurboQuant kernels require its rotated/packed representation; ExpertCache patch targets MXFP4 staging. | **Reuse only low-level patterns.** Reuse buffer/event/slot lifecycle, page alignment, read coalescing, telemetry and test methodology. Write/adapt Metal kernels for ERNIE quant layout and its attention/MoE projections only after reference correctness. MXFP4 ExpertCache kernels do not apply to Q4_K_M without a corresponding quant path. | **Least reusable.** Existing publisher Metal graph is the first correctness base. Gated MLA and FarSkip must remain correct before optimizing. Start with generic or existing llama.cpp Metal ops; only fuse after a profiler identifies a stable bottleneck. |

## Evidence from the measured Qwen arms: why not to copy knobs

* **Qwen3.6 Slipstream was viable because its representation/runtime were co-designed.** On this host it passed a constrained Hermes tool loop with 5,003 prompt tokens / 107.87 s first TTFT and a 5,052/5,106 cached-token follow-up / 4.50 s TTFT; it also recorded clean 16-slot decode around 5.9–8.4 tok/s depending on prompt. This proves its transport/cache harness, not ERNIE or Instella graph compatibility.
* **Cache size is not a universal answer.** Qwen Flash TinyTitan’s 24-slot arm cut I/O to 428.2 MiB/token and raised hit rate to 65.7%, yet reached only 2.839 tok/s and created 1,493 MiB swap. Its aging-LFU variant did not change hit rate (49.5%) or I/O/token at 16 slots. ERNIE/Instella require measured route traces before choosing LRU/LFU, pool size, or prefetch.
* **Compression is only useful after the resident-floor audit.** TurboQuant’s initial Flash analysis was corrected: PLE/n-gram bytes overlap `resident_bytes`, and `--ngram-offload` left a 2.665 GB wired core on paper. That correction reinforces the required method: derive target tensor accounting from headers, subtract only real overlaps, then verify with OS/MLX telemetry. It cannot be transferred to ERNIE/Instella, which lack Flash’s PLE contract.
* **A successful page-streamed model can still fail the product gate.** Qwen Flash 2-bit smoke was memory-safe but 1.475 tok/s, with 23.6% cache hit rate and roughly 0.7 GB critical expert reads per generated token. SSD residency makes a model loadable; it does not guarantee interactive decode.

## Concrete build plan

### Shared substrate (build once, model-neutral)

1. Extract a `ResidencyPlan` interface from the proven patterns: declared routed tensor groups; selected-expert IDs; bytes/stride/alignment; per-layer pool budget; cache policy; async I/O/read coalescing; Metal event synchronization; cache/read/bytes/token telemetry. Keep the backend representation-specific (`GGUF`, native packed, SafeTensors), rather than pretending one expert loader supports all formats.
2. Reuse the **qualification harness**, not the Qwen kernels: pinned source/model/format receipts; header/layout audit; low-slot one-token gate; deterministic route trace; memory pressure/swap/footprint/Metal measurements; cold versus in-process prefix versus restart snapshot classification; direct tool-loop then realistic Hermes profile test.
3. Make route correctness mandatory: compare selected expert IDs and a bounded output trajectory with the reference runtime before introducing prefetch, grouping, slot-policy changes, compressed KV, MTP, or speculative decoding.
4. Support CPU-MoE as an explicit diagnostic backend and label its result separately from GPU/SSD performance.

### ERNIE sequence

1. **Representation and floor gate:** inspect ERNIE Q4 GGUF headers and MLX tensor headers; account for dense/attention/router/shared-expert versus routed projections, KV/state and activation workspace. The existing rapid-mlx estimate and Q4 Metal OOM mean this gate must demonstrate a materially lower safe working set before any paging implementation.
2. **Forward adapter:** begin from the existing `ernie4_5_moe` GGUF loader, add an explicit route hook only after a CPU/reference short-token trajectory passes. Validate all 64 routed expert tensor names, three projection layouts and the two shared experts.
3. **Residency adapter:** stage only routed projections; retain shared experts, router, embeddings and attention resident. Start with exactly enough slots for top-6 on a physical microbatch of one, then measure route-union behavior. No prefetch or larger slot sweep until this is correct.
4. **KV/API:** implement ERNIE cache/snapshot from its actual attention graph; parse its official tool/thinking template and execute a direct OpenAI tool round trip. Only then test a slim Hermes profile; full Hermes requires its real rendered prefix.

### Instella sequence

1. **Do not fork the Qwen runtime.** Start from publisher `instella-moe@7a3c74e`, which already contains Instella graph/MLA support. First identify a lower-bit representation that passes a strict loaded-idle and short-prefill gate; Q4’s 9% free/9.44 GiB swap result makes Q4 unsuitable as the optimization base on this host.
2. **Separate graph from residency:** obtain exact output and route traces for Gated MLA + FarSkip + top-6 MoE before altering storage. Preserve the branch’s MLA-specific KV cache (separate from standard/GDN cache assumptions).
3. **Add resident experts only at supported MoE tensors:** validate names, contiguous GGUF stride and quant format. Since the branch is custom, add a new Instella residency hook rather than transplanting `_exps.` Qwen assumptions. Run one-slot/top-6-union test with `ubatch=1`, then grow only under a memory guard.
4. **KV/API:** retain the native MLA cache first. Add KV compression/disk snapshots only after exact continuation equivalence; use a tool parser matched to Instella’s template, then a direct tool loop and full Hermes gate.

## Acceptance gates and stop rules

| Gate | ERNIE pass condition | Instella pass condition |
|---|---|---|
| Loader/reference | One deterministic short completion matches baseline under target graph | Same, including Gated MLA/FarSkip and router IDs |
| Loaded idle | Safe pressure/swap and a measured physical footprint below the experiment budget | Same; Q4 result means a different/lower-bit representation is required first |
| SSD residency | Exact selected-expert reads and output trajectory; no full expert materialization | Same on publisher graph and MLA cache |
| Short populated context | Actual 4K–8K prompt completes within declared memory guard before any long-context claim | Same |
| Cache | Valid history extension returns cached-token evidence; restart persistence only if proven | Same; cache type must be MLA-aware |
| Product | Direct tool call + continuation `stop`, then a full rendered Hermes tool loop | Same |

Do **not** promote a target because it loads, produces a few tokens, or returns HTTP 200. Do not claim 32K/131K from a configured context value. The existing ERNIE and Instella results have not passed the loaded-idle/short-context gates.

## Sources and local evidence

### Local, pinned evidence

* `results/raw/EXP-003/compatibility-gate.md` — GGUF SSD-slot PoC design, Qwen source assumptions and slot budget.
* `results/raw/EXP-004/phase1/compatibility-gate.md`; `source/expertcache/README.md` — ExpertCache MXFP4/Metal scope and evidence boundary.
* `results/raw/EXP-005/runtime-inspection.md`; `source/slipstream/Sources/TurboFieldfare/Infrastructure/ModelIO/ModelTypes.swift`; `.../SupportedModelSource.swift` — Slipstream features and hard-coded Gemma/Qwen families.
* `results/raw/EXP-006/runtime-inspection.md`; `optimization-sprint/*/summary.md` — Flash/TinyTitan graph and cache measurements.
* `results/raw/EXP-010-laguna-long-context/runtime-survey.md` and `REPORT.md`; `results/raw/EXP-013-qwen38-flash-2bit-streaming/{STAGE1_REPORT,CORRECTION-2026-09-19}.md` — TurboQuant streaming/KV mechanisms and measured caveats.
* `results/raw/EXP-015-github-runtime-dive/REPORT.md` — Qwen Coder Swiftlet/TurboQuant/Mference applicability limits.
* `results/raw/EXP-016-small-moe-feasibility/{REPORT.md,ernie/dossier.md,instella/dossier.md}` — target architecture pins and local feasibility outcomes.

### Upstream primary references

* ERNIE model card: https://huggingface.co/baidu/ERNIE-4.5-21B-A3B-Thinking
* Instella model card: https://huggingface.co/amd/Instella-MoE-16B-A3B-Think
* TinyTitan: https://github.com/Pummelchen/TinyTitan
* TurboQuant-MLX: https://github.com/manjunathshiva/turboquant-mlx
* ExpertCache: https://github.com/amos-labs/expertcache
