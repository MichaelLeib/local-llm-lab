# EXP-016 — Small-active MoE feasibility tournament

Date: 2026-09-19
Host: Mac15,13 / Apple M3 / 16 GiB unified memory / macOS 27.0 (26A428)
Scope: runtime feasibility only. Coding and research-quality evaluations were deliberately not run.
Raw evidence root: `results/raw/EXP-016-small-moe-feasibility/`
Machine-readable comparison: `comparison.json`
Storage receipt: `storage-receipt.json`

## Executive summary

North Mini Code is the only primary candidate that survived the runtime feasibility tournament, and only in an experimental CPU-only configuration. The best measured configuration was the pinned unsloth UD-Q3_K_M GGUF served by the isolated llama.cpp ExpertCache build on loopback with `--n-gpu-layers 0 --cpu-moe`. It loaded with HTTP health 200, completed deterministic standalone generation, completed a 2,740-token context needle retrieval after prefix caching, and completed a direct native terminal-tool call followed by a normal `finish_reason=stop` continuation.

This is not a production Hermes promotion. Cold context prefill was very slow (179.8 seconds for 2,740 prompt tokens), the Metal path failed with Insufficient Memory, and the tool test used a compact direct API schema rather than the full rendered Hermes prompt. The next intelligence test is a full realistic Hermes native-tool turn plus the campaign's later quality tests; neither was run here.

ERNIE failed both tested runtime paths: rapid-mlx correctly stopped before inference after projecting a 17.2 GB working set on this 16 GB host, and the GGUF Q4_K_M path reached Metal compute but repeatedly failed with Insufficient Memory. Instella Q4_K_M reached a short four-token standalone output on the publisher's llama.cpp branch, but a longer arm drove free memory to 9% and swap to 9.44 GiB; it was safety-stopped and not escalated to Q3.

## Required candidate decisions

| Candidate | Primary representation tested | Runtime decision | Survivor |
|---|---|---|---|
| ERNIE-4.5-21B-A3B-Thinking | community MLX 4-bit, then GGUF Q4_K_M fallback | projected working-set safety failure; GGUF Metal OOM | No |
| Instella-MoE-16B-A3B-Think | GGUF Q4_K_M on publisher instella-moe branch | short token possible, but practical memory gate failed | No |
| North-Mini-Code-1.0 | 4-bit options gated out by size; UD-Q3_K_M fallback | CPU-only runtime survivor; Metal path failed | Yes, experimental only |

No additional candidate was added. All three required primary candidates were processed in order.

## ERNIE

Source: `baidu/ERNIE-4.5-21B-A3B-Thinking`, revision `4341bb42644d5422859509fa25d41544c57181f8`.
Architecture recorded in `ernie/dossier.md`: `ernie4_5_moe`, 28 layers, hidden 2560, 20 Q / 4 KV heads, 64 routed plus 2 shared experts, top-6.

### MLX 4-bit arm

Artifact: `qurk41/ERNIE-4.5-21B-A3B-Thinking-mlx-4Bit`, revision `b59122f1fbe19df1fe939ad4de46763265fc297`; selected local files total 12,288,141,742 bytes, with 12,277,133,662 bytes of model weights. Acquisition hashes are in `ernie/acquisition/` and `ernie/acquisition.json`.

Runtime: rapid-mlx 0.14.1. The server reached health HTTP 200 in standby, but its startup gate recorded:

- Model on disk: 11.4 GB.
- Estimated short-chat working set: 17.2 GB.
- Current OS use: 8.7 GB.
- Projected utilization: 162% of 16 GB.
- Runtime warning: continued inference could trigger a macOS kernel panic.

Decision: stop before inference. This is a measured runtime safety rejection, not a quality result. Evidence: `ernie/rapid-mlx-arm/startup-gate.json` and `server.log`.

### GGUF Q4_K_M fallback

Artifact: `unsloth/ERNIE-4.5-21B-A3B-Thinking-GGUF`, revision `b1fa62d9e5864da596c78a0fb5cc02e5ffba336c`; file size 13,331,018,624 bytes; SHA-256 `9cd7c60d3c30f46e7f539043ec19c7ec8953153f65dd9a2a2748b8e3f589d015`.

Runtime source: isolated llama.cpp ExpertCache build at commit `7e1e28cae36d41fe7bbe9dae7c9625de6565c063`.

The first standalone probe used an interactive CLI mode accidentally and was terminated after more than ten minutes without a visible model-load or completion marker; its 1.06 GB log and telemetry are retained in `ernie/gguf/first-probe/`, classified as `interactive-standalone-probe-did-not-reach-visible-model-response`.

A corrected fresh probe used `--no-conversation --single-turn --simple-io`, context 512, physical ubatch 1, and `GGML_METAL_LAZY_TENSOR_MAP=1`. The log records repeated Metal status 5 / `Insufficient Memory`, graph-compute failure, `llama_decode` failure, and `Error: Compute error`; no response was produced. Evidence: `ernie/gguf/first-probe-clean/`.

Decision: GGUF Q4_K_M is a runtime-gate failure. No API/tool smoke was attempted.

## Instella

Source: `amd/Instella-MoE-16B-A3B-Think`, revision `74d28c1a8425583d7805b58e2caa9c13d6b62929`.
Architecture: custom `InstellaMoEForCausalLM`, `deepseek_v3` model type, 27 layers, hidden 2048, Gated MLA, FarSkip-Collective, 64 routed plus 2 shared experts, top-6. The source config and remote discovery are retained in `instella/discovery/`.

Representation: `DevQuasar/amd.Instella-MoE-16B-A3B-Think-GGUF`, revision `987ee1648d7e4bcb33ab98dfbf4e910b2230c30a`, Q4_K_M file size 10,470,249,600 bytes, SHA-256 `f776ddfee5dc6c808265c3f0a9c1b384c98058bfa551fe5df656fe712eb4c7f3`.

Runtime: publisher branch `instella-moe`, commit `7a3c74eb0b5e58bc8cc3949f416fbc2b3959774c`, built with Metal successfully.

- Conservative short probe: `--cpu-moe --n-gpu-layers 99 --ctx-size 512 --ubatch-size 1`, four-token cap. It emitted `<think> First`; footer measured approximately 0.5 prompt tok/s and 0.5 generation tok/s.
- Longer 32-token arm: process RSS reached 7,402,672 KB, system-wide free memory reached 9%, and swap reached 9,438.19 MiB used. The arm was safety-stopped before output completion.
- No coding or research-quality evaluation was run.

Decision: Q4 is not practically feasible on this host. Q3 escalation was not justified after the measured severe-pressure result. Evidence: `instella/first-probe/` and `instella/decode-32/`.

## North Mini Code

Source: `CohereLabs/North-Mini-Code-1.0`, revision `d11e61a842617a22dc328552fa5bb86231ee4f37`.
Architecture: `Cohere2MoeForCausalLM` / `cohere2_moe`, 49 layers, hidden 2048, 32 Q / 4 KV heads, 128 experts, top-8, sliding-window layers, source maximum position 500000. The source config and model-card discovery are retained in `north/discovery/`.

### Representation and 4-bit gate

The pinned GGUF repository is `unsloth/North-Mini-Code-1.0-GGUF`, revision `e306bb4bf0df610f5471d97a01de2b6e0b24d356`. Its 4-bit options were:

- `MXFP4_MOE.gguf`: 18,662,121,568 bytes.
- `UD-Q4_K_M.gguf`: 19,203,186,784 bytes.

These exceed the practical 16 GiB envelope already rejected by the ERNIE MLX projection and the Instella Q4 measured pressure arm. They were not downloaded. The strongest available lower-bit fallback was selected:

- `North-Mini-Code-1.0-UD-Q3_K_M.gguf`: 14,213,013,600 bytes.
- SHA-256: `145e185430e31c43221995ac52aed7efbd91f043dbfcdcf297a986f06f7dcee7`.

Runtime source: isolated ExpertCache llama.cpp build at commit `7e1e28cae36d41fe7bbe9dae7c9625de6565c063`, which contains the `cohere2moe` architecture and parser support.

### Metal and CPU runtime arms

The Q3 Metal path was attempted with context 512, ubatch 1, `--cpu-moe`, and `GGML_METAL_LAZY_TENSOR_MAP=1`. It loaded far enough to begin serving but failed with repeated Metal status 5 / `Insufficient Memory`, graph-compute failure, and no response token. A non-lazy attempt also produced a macOS `SIGBUS` diagnostic during `cli_server::wait_ready`; the copied crash report is preserved at `north/first-probe/llama-cli-crash.ips` and the run is classified separately in `north/first-probe/`.

The CPU-only fallback (`--n-gpu-layers 0 --cpu-moe`) completed:

- Context 256, deterministic prompt, 8-token cap.
- Prompt: 6.7 tok/s.
- Generation: 11.2 tok/s.
- Post-run pressure remained healthy.

### Persistent server and cold/warm measurements

Best configuration:

    llama-server -m North-Mini-Code-1.0-UD-Q3_K_M.gguf --host 127.0.0.1 --port 8926 --no-webui --metrics --jinja -c 4096 -b 64 -ub 1 -np 1 -ngl 0 --cpu-moe --load-mode mmap --no-warmup

The server was loopback-only and bound to `127.0.0.1`. Health returned HTTP 200. Observed loaded-idle RSS was approximately 9,279,536 KB. The first fixed chat request took 19.572 seconds; the warm repeat took 1.102 seconds with 116 of 121 prompt tokens cached. The server metrics capture reported 13.0999 average prompt tok/s and 8.3201 average predicted tok/s across the requests. Raw captures are in `north/server/`.

### Context classification

A deterministic needle test used a 2,740-token prompt and exact needle `NORTH_NEEDLE_7F3C`:

- Allocatable: yes; HTTP 200 and 2,740 prompt tokens accepted.
- Completable: yes; the request returned a completion. The first 8-token cap was intentionally too short and ended with the prefix `NORTH_NEEDLE_7F3`.
- Correct: yes on the warm retry with a 16-token cap; the exact needle appeared.
- Cold practical usability: no; first request wall time was 179.798 seconds.
- Warm cached usability: yes for this narrow repeated-prefix case; second request was 2.327 seconds with 2,735 cached tokens.

This does not establish the advertised 256K context as usable. It is a 2,740-token actual-context classification only. Evidence: `north/server/context-retrieval-*`.

### Direct native tool loop

A compact direct OpenAI-compatible request with one `terminal` function produced a parsed native tool call (`finish_reason=tool_calls`) with command `date -u +%Y-%m-%dT%H:%M:%SZ`. The isolated executor returned `2026-09-19T09:45:55Z`. The continuation containing the matching assistant call and tool result ended with `finish_reason=stop` and reported the exact executor result. Raw request, response, executor result, and final response are in `north/server/tool-*`.

This is an endpoint/native parser compatibility pass. A full rendered Hermes prompt and production Hermes turn were not run, and no production configuration was modified; therefore this is not a promotion claim.

## System-health evidence and residency

- Starting campaign receipt recorded FAST and DEEP down and initial swap 1,723.44 MiB.
- All custom arms were run one at a time. No FAST or DEEP model was started.
- ERNIE rapid-mlx emitted its own projected-working-set safety warning before inference.
- Instella Q4 longer arm reached 9% free memory and 9,438.19 MiB swap; it was safety-stopped.
- North CPU-only server remained operational with healthy sampled pressure and was stopped cleanly.
- After North shutdown, port 8926 was unreachable, no custom llama process remained, FAST/DEEP were down, final observed swap was 2,406.50 MiB, and memory-pressure free was 77%.
- No swap reset, reboot, production lane switch, or persistent Hermes configuration edit was used.

## Best configurations and decisions

| Candidate | Best tested configuration | Decision |
|---|---|---|
| ERNIE | None; rapid-mlx standby safety rejection and GGUF Metal OOM | Reject for this 16 GiB host |
| Instella | Publisher branch Q4, CPU-MoE fallback; short token only | Reject as practical runtime; do not escalate |
| North | UD-Q3_K_M, llama.cpp CPU-only, one server slot, ctx 4096 | One experimental runtime survivor; do not promote yet |

## Survivor set and next intelligence test

Survivor set: North Mini Code UD-Q3_K_M through llama.cpp CPU-only.

Next intelligence test (not run): a fresh full realistic Hermes session using the active target profile's rendered system/tool prefix, one native terminal/file call, matching tool-result continuation, and normal stop; then the separately authorized coding/research-quality test battery. The direct compact tool loop here is insufficient to replace that test.

## Storage receipt

The campaign acquired and hash-verified the ERNIE MLX and GGUF representations, Instella Q4 GGUF, and North Q3 GGUF. North 4-bit artifacts were gated out before acquisition. The evidence tree measured approximately 50G at report time; raw APFS free space was 174GiB in the final snapshot. No campaign model or raw evidence was deleted. Full machine-readable accounting is `storage-receipt.json`.

## Matrix milestone receipts

Messages were sent with the exact campaign command to `matrix:development` at discovery, ERNIE gate, Instella gate, North runtime qualification, and completion milestones. Successful message IDs are recorded in the command outputs and session log; the final completion message was sent after the North server was stopped and verified unreachable.
