# EXP-023 — FAST-lane optimization: MiniCPM5-1B vs 2B

**Date:** 2026-09-20  
**Host:** M3 MacBook Air, 16 GB unified memory  
**Runtime:** `/opt/homebrew/bin/llama-server` (Metal), managed by `~/.hermes/bin/hermes-local-model`  
**Decision:** **retain MiniCPM5-2B Q4_K_M for FAST and THINK; promote Q4_0 K/V cache at 64K.**

## Final live architecture

```text
Auto FAST/THINK → MiniCPM5-2B Q4_K_M, llama.cpp Metal, 64K, Q4_0 K/V KV cache
Auto DEEP       → existing Ornith Q6 / Q8 KV, single-resident managed lane
```

The manager is currently verified running FAST on `127.0.0.1:8901` with:

```text
-c 65536 --cache-type-k q4_0 --cache-type-v q4_0
```

No Hermes profile model/provider/auxiliary assignment was changed in EXP-023.  The existing Auto router remains the MyChatty implementation from HermesMobile commit `8e8062b`.

## Result: 1B vs 2B

### Direct 64K / F16 control

| Model | GGUF bytes | load | direct factual | direct native tool call | compression | 22,849-token retrieval | outcome |
|---|---:|---:|---|---|---|---:|---|
| MiniCPM5-1B Q4_K_M | 682,930,176 | 2.097 s | pass | pass | **fail** — refuses/does not compress | 40.517 s, correct | reject |
| MiniCPM5-2B Q4_K_M | 1,556,172,800 | 3.132 s | pass | pass | pass, all required facts preserved | 85.876 s, correct | control/winner |

The 1B model is materially faster on direct probes (about 82–87 decode tok/s versus about 39–43 for 2B), and MiniCPM5's `enable_thinking` chat-template option was verified: no-think returned just `56`, while think produced a reasoned answer.  This is a real template/runtime mode, not an instruction-only approximation.

It is nevertheless not a safe Hermes FAST/THINK lane.  At the real MyChatty → Hermes 14K-token prefix, 1B failed 3 of 4 end-to-end checks:

- simple factual question: replied `C` instead of `Paris`;
- terminal request: narrated intent; emitted **no** native `tool.started` event;
- web URL request: passed;
- THINK diagnostic: repetition detector stopped the response after **438.221 s**.

2B passed all direct checks and each real Hermes lane check.  Both F16 and Q4 KV variants produced native `tool.started`/`tool.completed` events for the terminal task and completed factual, terminal, web, and diagnostic requests.

**Conclusion:** MiniCPM5-1B is fast enough for a toy endpoint, but is not reliable enough for the existing full Hermes session/tool surface. It is also not promoted for compression or latency-sensitive auxiliaries.

## Context and KV ladder

All context arms were single-resident, freshly restarted, and contain a correct retrieval query after the populated prompt. `RSS` is process RSS; `footprint` is macOS physical footprint, the more useful unified-memory signal. The result files retain `vm_stat`, `memory_pressure`, swap, `footprint`, `ps`, and llama.cpp metrics before and after work.

| Arm | Loaded idle footprint | Post-work footprint | RSS at idle | populated tokens | populated wall |
|---|---:|---:|---:|---:|---:|
| 1B, 8K F16 | 289 MB | 349 MB | 988 MB | 2,629 | 2.533 s |
| 1B, 16K F16 |  — | — | 1,185 MB | 5,233 | 4.463 s |
| 1B, 32K F16 | — | — | 1,578 MB | 10,937 | 12.369 s |
| 1B, 64K F16 | 1,633 MB | 1,736 MB | 2,366 MB | 22,849 | 40.517 s |
| 1B, 64K Q8 | 914 MB | 1,001 MB | 1,630 MB | 22,849 | 39.725 s |
| 1B, 64K Q4 | 532 MB | 619 MB | 1,236 MB | 22,849 | 40.699 s |
| 2B, 8K F16 | 432 MB | 477 MB | 1,988 MB | 2,629 | 5.409 s |
| 2B, 16K F16 | — | — | 2,332 MB | 5,233 | 11.416 s |
| 2B, 32K F16 | — | — | 3,022 MB | 10,937 | 27.715 s |
| 2B, 64K F16 | 2,787 MB | 2,875 MB | 4,400 MB | 22,849 | 85.876 s |
| 2B, 64K Q8 | 1,527 MB | 1,603 MB | 3,112 MB | 22,849 | 86.319 s |
| **2B, 64K Q4** | **857 MB** | **922 MB** | **2,423 MB** | **22,849** | **86.484 s** |

### What consumes memory

A GGUF file size is not the runtime footprint.  In particular, the 2B model's 64K allocation is dominated by KV/cache reservation and runtime buffers:

- 2B F16: physical footprint grows from **432 MB at 8K** to **2,787 MB at 64K**.
- 2B Q4: 64K idle physical footprint is **857 MB**, a **1,930 MB / 69.3%** reduction versus 2B F16 at the same advertised context.
- Process RSS likewise falls from **4,400 MB** to **2,423 MB** (a **2,024,685,568-byte / 44.9%** reduction).
- The F16 2B-vs-1B RSS difference at 64K is **2,082,881,536 bytes**, but this is not pure model weight: the architectures have different KV shapes and runtime allocations. macOS does not expose a trustworthy isolated "Metal model weight" counter; raw `footprint`/IOAccelerator sections are preserved rather than inventing one.

Q4 had no material prompt-speed penalty in the 22.8K populated check and passed the real Hermes tool loop. It is therefore the promoted FAST cache setting. Q8 is a conservative middle rung but has no user-visible advantage here.

## 64K admission policy

The active installed Hermes source implements a 64K local-runtime guarantee in:

```text
~/.hermes/hermes-agent/hermes_cli/local_runtime/context_policy.py
FLOOR = 64 * 1024
```

`initial_window()` calls its physics check at this floor and the source explains the policy: it is the smallest window at which compression is exceptional rather than routine, based on 161 real agentic sessions.  The running server must also report the same window; an alias/config value cannot make a 32K llama.cpp server safely appear as 64K.

No bypass was implemented.  A smaller real FAST window is not safe for the current surface: the first ordinary MyChatty/Hermes request is **14,397 input tokens** before useful history.  An 8K server would truncate/reject it; 16K leaves no durable space for tool results, history, or a normal session. Separating advertised from allocated context would violate both the installed policy and the endpoint's capability contract.

## Prompt composition

Measured fresh real FAST request: **14,397 input tokens** (factual request; Q4 or F16 did not change this).

Static inventory:

- stored Hermes system prompts: **21,580–33,748 characters** depending on active variant;
- enabled toolsets: 15; rendered schemas: **23 schemas / 36,953 characters**;
- largest individual schemas: `delegate_task` 4,383 chars, `browser_exec` 3,495, `terminal` 3,341, `memory` 3,222, `execute_code` 3,002, `skill_manage` 2,334, `search_files` 2,248;
- profile/system instructions, skills, memory, routing instruction, and user text are embedded in the stored system content; the complete provider-reported input value above is authoritative.

The schema payload is the dominant controllable part of the 14K prefix. I inspected the active `/v1/runs` path and its `prepareAutoRoute()` transformation. It has a supported request-scoped seam for provider/model/reasoning/instructions, but **no supported request-scoped toolset/schema override**. `platform_toolsets` is profile-wide. Creating a slim profile would make a disconnected session, which violates the same-session requirement, and patching Hermes would invalidate prompt caching/unsupported session behavior. Therefore no unsafe tool reduction was made.

## End-to-end timings

All numbers are client-wall clock from MyChatty request to completed event. First request is cold prefix; following requests reuse the static prefix cache and are labeled warm.

| Model/route | simple cold | terminal warm | web warm | THINK warm | native tools |
|---|---:|---:|---:|---:|---|
| 2B F16 | 45.182 s | 4.144 s | 1.367 s | 4.708 s | pass |
| 2B Q4 | **43.024 s** | 5.633 s | 1.279 s | 8.167 s | pass |
| 1B F16 | 19.211 s but wrong | 1.339 s but no call | 0.675 s | 438.221 s repetition stop | fail |

Q4 reduces memory dramatically but does **not** materially reduce cold first-turn latency. The static prefix/pre-fill remains the dominant cost.

Forced MyChatty lane switch checks:

| Path | admission / lane-ready | request complete | notes |
|---|---:|---:|---|
| FAST → DEEP | 15.223 s | 125.838 s | full 14,423-token cold Ornith request, correct `DEEP_OK` |
| warm DEEP → DEEP | 0.265 s | 5.179 s | correct `DEEP_OK` |
| DEEP → FAST | 2.390 s | 5.005 s | correct `FAST_OK`; use as observed cached/short-output result, not a cold-prefill promise |

The DEEP→FAST result must not be extrapolated to an uncached first ordinary FAST turn; the clean Q4 cold control above is 43.024 s.

## Dual residency

**Not rerun.** The lane policy for this 16 GB Mac is one resident model, and the prior EXP-022 dual-residency run already produced about 6% free RAM and 1.9 GB incremental swap. The controlling runtime policy forbids intentionally loading a second resident model during normal experiments; EXP-023 improved the FAST allocation safely instead. This is a safety restriction, not a claim that Q4 makes coexistence healthy.

## Auxiliary model decision

No auxiliary assignment changed. MiniCPM5-1B is rejected for compression and full Hermes tools; it is not substituted for titles, search, MCP routing, or other helpers. Existing quality/safety-sensitive helpers remain untouched.

## Changes, backup, and rollback

### Persistent change

`~/.hermes/bin/hermes-local-model`

```diff
- FAST_KV_K="${HERMES_FAST_KV_K:-f16}"
- FAST_KV_V="${HERMES_FAST_KV_V:-f16}"
+ FAST_KV_K="${HERMES_FAST_KV_K:-q4_0}"
+ FAST_KV_V="${HERMES_FAST_KV_V:-q4_0}"
```

The launcher now also explicitly passes `--cache-type-k` / `--cache-type-v`; per-run `HERMES_FAST_KV_K` and `HERMES_FAST_KV_V` remain overrides.

Backup root before EXP-023 changes:

```text
backups/20260920T180630+0200/
```

### Immediate rollback

```bash
# One launch only (does not edit the promoted default)
HERMES_FAST_KV_K=f16 HERMES_FAST_KV_V=f16 \
  ~/.hermes/bin/hermes-local-model start fast

# Persistent rollback: restore the backed-up launcher, then restart FAST
cp "<EXP-023>/backups/20260920T180630+0200/hermes-local-model" \
  ~/.hermes/bin/hermes-local-model
~/.hermes/bin/hermes-local-model start fast
```

The normal manager will stop DEEP before starting FAST; no profile configuration or Ornith files need restoration.

## Evidence and version pins

- Experiment root: `results/raw/EXP-023-fast-lane-optimization/`
- Raw direct arms: `raw/arms/<arm>/` (requests/responses, metrics, macOS snapshots)
- Real MyChatty/Hermes streams: `raw/e2e/`
- Official MiniCPM5-1B GGUF: `models/minicpm5-1b/MiniCPM5-1B-Q4_K_M.gguf`
- Existing Auto-router source baseline: HermesMobile `8e8062b` (`feat: add local Auto FAST/THINK/DEEP routing`)
- Installed Hermes source baseline: `cedf4a3d786`
- This experiment tree is not itself a Git repository; no unrelated HermesMobile files were committed or modified.

## Reproduce the selected lane checks

```bash
cd ~/HermesProjects/Local-LLM-Lab/results/raw/EXP-023-fast-lane-optimization
python3 run_direct_arm.py --name scratch-2b-q4 --model \
  ../EXP-022-auto-routing/models/minicpm/MiniCPM5-2B-Q4_K_M.gguf \
  --context 65536 --kv-k q4_0 --kv-v q4_0
python3 run_hono_e2e.py --label scratch-2b-q4 --session exp023-scratch
```

Do not run the arms in parallel: each one controls the single managed FAST lane.
