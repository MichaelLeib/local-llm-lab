# EXP-016 — Small-active MoE feasibility tournament

## Mission
Determine which next-generation, small-active MoEs run well enough on the 16 GB M3 MacBook Air to deserve later autonomous coding and research-quality testing. This is runtime feasibility only: **do not run coding or research-quality benchmarks**.

## Explicit user authorization
The user has explicitly authorized the entire campaign, including normal dependency installation, large candidate downloads, local model launches/lane switching, build/conversion work, safe storage cleanup, and model tests. The standing constraints still apply: only one resident local model at a time; preserve proven FAST/DEEP defaults; loopback-only endpoints; preserve raw evidence; do not alter unrelated projects or secrets. Do not ask routine configuration questions.

## Starting state / Phase 0 receipt
- `FAST`: down; `DEEP`: down.
- Initial swap: 1,723.44 MiB used. Record deltas rather than resetting swap.
- Qwen3.6/Slipstream remains the comparison baseline, not the campaign target.
- Existing Local-LLM-Lab is the experiment root; use a new `EXP-016-*` directory per candidate/run.
- External archive `/Volumes/EXT/Local-LLM-Archive` is mounted, writable, and has approximately 117 GiB free. Use it only for older non-Flash model artifacts if internal storage becomes constrained; do not move files required by an active run.
- Authorized cleanup completed: deleted only redownloadable Qwen3.8 Flash payloads (the 162 GiB EXP-006 native model and the 52 GiB Qwen Flash SafeTensors); retained experiment docs, source, logs, manifests, tokenizer/config metadata, and all results. Data-volume free space increased from 13 GiB to 227 GiB. Record this as 214 GiB reclaimed.

## Required candidates, in order
1. `baidu/ERNIE-4.5-21B-A3B-Thinking` — very high priority.
2. `amd/Instella-MoE-16B-A3B-Think` — very high priority.
3. `CohereLabs/North-Mini-Code-1.0` — medium/high priority.

Candidate discovery may add only a genuinely competitive current small-active MoE (preferred <=25B total, <=30B total, <=7B active) and must not derail the three primary candidates.

## Initial feasibility facts (must independently pin exact revisions and file sizes)
- ERNIE: 21B total / 3B activated, 28 layers, 20 Q heads / 4 KV heads, 64 routed + 2 shared experts, 6 routed experts activated, advertised 131,072 context; GGUF and MLX quantizations exist. Official FastDeploy claim is 80 GB GPU, so desktop-runtime feasibility must be proven, not assumed.
- Instella: 16B total / 2.8B activated, 27 layers, hidden 2048, 16 attention heads, 64 routed + 2 shared experts, 6 routed experts activated, Gated MLA + FarSkip-Collective. Find the strongest viable Apple Silicon representation; do not assume a standard MLX converter supports it.
- North: 30B total / 3B active, 128 experts / top-8, 3:1 sliding-window RoPE and global no-position attention. Native MLX-VLM main and a special llama.cpp cohere2-moe branch are plausible; establish current support before acquiring weights.

## Execution requirements
Follow the user-supplied campaign specification in the original attached message. First inspect `PROJECT.md`, `STATE.md`, `ENVIRONMENT.md`, `EXPERIMENTS.md`, `BENCHMARKS.md`, and the local-llm-lanes skill. Use a candidate dossier before large downloads. Reuse existing collector tooling where reliable. Capture exact revisions, architecture/config, download and disk size, runtime commit, commands, system telemetry (vm_stat/memory pressure/swap/SSD I/O/process footprint), cold vs warm, prefill, decode, context retrieval, and API/tool smoke for qualified survivors.

Use a 4-bit representation first where sensible; evaluate a strong 3-bit form only when 4-bit cannot meet the practical memory envelope. Stop escalating an individual candidate with a documented reason if it clearly cannot meet runtime/health gates; continue to the next candidate. Do not falsely call configured context "usable": populate it, retrieve a deterministic needle, and distinguish allocatable / completable / correct / practically usable.

Do not promote on a toy tool call. Any Hermes compatibility claim requires direct endpoint probing and a real native terminal/file tool loop at a realistic rendered Hermes prompt size. Do not modify production Hermes configuration; use isolated overlays/profiles and restore/verify lane state after every candidate.

## Milestone delivery
Post concise messages at actual milestones, failures, and final completion using:
`HERMES_HOME="$HOME/.hermes" hermes send --to 'matrix:development' --subject '[EXP-016 Small MoE tournament]' '<message>' --json`
The initial milestone was sent successfully with Matrix event `$EUfIy9MqIk2s3IO53chxbLgGeeCWQcvmXL_L18gzEJ0`. Include measured facts, candidate, gate decision, and next action; never claim measurements not yet recorded. If Matrix send fails, write the failure and message payload in the campaign raw directory and continue.

## Final deliverable
Write `REPORT.md` and a machine-readable comparison table under `results/raw/EXP-016-small-moe-feasibility/`, then update `EXPERIMENTS.md` and `RESULTS.md` append-only. The report must contain the executive summary, per-candidate best configuration and launch commands, comparison measurements, context classifications, system-health evidence, Hermes compatibility, storage receipt, 1–3 survivor set, and the next intelligence test for each survivor—without running those intelligence tests.
