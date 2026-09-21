# EXP-022 — Local Auto model routing

## Decision
**FAST/THINK model:** `MiniCPM5-2B-Q4_K_M.gguf` (GGUF, llama.cpp Metal), alias `minicpm5-2b`.

It is the only candidate that passed the direct correctness gate (Paris) and native OpenAI-style function calls while remaining substantially smaller than NeoHorse. Spark was smallest but returned `FR` to a one-word capital-of-France check; NeoHorse was 2.71 GB on disk and materially slower. All raw server responses and timings are retained in `raw/`.

## Architecture

```text
myChatty selection (Auto / Fast / Deep)
   │ POST /h/<profile>/v1/runs
   ▼
HermesMobile Hono proxy — `server/src/auto-router.ts`
   ├─ deterministic structural/semantic policy + 90-minute session stickiness
   ├─ persists route affinity (not prompts) in ~/.hermes/runtime/auto-routing-sessions.json
   ├─ serialises lane changes through ~/.hermes/bin/hermes-local-model
   └─ uses Hermes' supported request-scoped provider/model overrides
          ├─ local-minicpm / minicpm5-2b → 127.0.0.1:8901/v1
          └─ local-ornith / ornith-q6     → 127.0.0.1:8919/v1
                ▼
       existing multiplexed Hermes API server / sessions / tools
```

The frontend default is `local-auto/auto`. The picker explicitly prepends **Auto**, **Fast**, and **Deep**. Existing former implicit `local-fast/hermes-fast` selections migrate to Auto; other deliberate selections remain unchanged.

### Route policy

- **FAST:** direct facts, one command/tool lookup, repository search, status/process/port checks, short explanations, quick retrieval. MiniCPM is invoked with reasoning disabled and a direct-response instruction.
- **THINK:** diagnosis, competing causes, evidence comparison, contained implementation/repair. It uses the same MiniCPM lane with a bounded-investigation instruction and a higher output/tool budget. This model did not reliably classify routes by itself (`FAST` for all three classification probes), so routing is intentionally deterministic/structural rather than pretending an unreliable classifier is safe.
- **DEEP:** architecture, broad/multi-file work, migrations, difficult debugging, serious research, long/big inputs. It starts Ornith directly; the tiny model is not inserted first.
- **Stickiness:** `why?`, `continue`, `do that`, `fix the remaining test`, and similar references remain on the active DEEP/THINK episode for 90 minutes. Clearly new simple questions are permitted to return to FAST. State survives proxy restarts in the 0600 runtime JSON file and expires automatically.
- **Escalation:** the THINK prompt may emit `[[AUTO_ESCALATE]]`; MyChatty also escalates after two failed tool rounds. It restarts the same session on Deep, retaining Hermes-persisted original/tool evidence rather than a lossy summary. One escalation only; explicit Fast/Deep does not auto-escalate.

## Residency and recovery

`~/.hermes/bin/hermes-local-model` is now the only normal lane manager:

```bash
hermes-local-model ensure fast    # MiniCPM; stops Ornith first
hermes-local-model ensure deep    # Ornith Q6; stops MiniCPM first
hermes-local-model ensure         # guard-safe: retains whichever lane is already live
hermes-local-model status
```

Both models **must not** stay resident: measured coexistence drove free memory to 6% and increased swap from ~0.87 GB to ~2.77 GB. The manager verifies the opposing port is down before considering a switch complete. The Auto proxy returns HTTP 503 when its requested lane cannot become healthy; it does not silently substitute a weaker model. Normal resting state after validation is FAST.

The existing `com.hermes.mychatty` launchd agent runs the built proxy at login and restarts it on failure; it was kickstarted successfully after the final server build. The existing Hermes gateway launchd definition was refreshed with `hermes gateway start` and verified to match the installed Hermes build.

The FAST server uses 64K context, not the initial 8K test window: the installed Hermes Agent refuses models reporting less than 64K. This is an implementation constraint, not a claim that 64K populated conversations are an ergonomic FAST workload.

## Auxiliary inventory

Applied uniformly to default plus all nine real profile configs:

| Slot(s) | Choice | Reasoning | Fallback | Why |
|---|---|---:|---|---|
| `auxiliary.title_generation` | MiniCPM | off | Ornith | Tested title output; small, deterministic text |
| `auxiliary.compression` | MiniCPM | off | Ornith | Preservation probe retained paths, ports, command, TODO, constraint, preferences and measurements |
| `auxiliary.session_search` | MiniCPM | off | Ornith | Query rewrite/ranking is small text work |
| `auxiliary.profile_describer` | MiniCPM | off | Ornith | Short structured profile descriptions |
| `auxiliary.mcp` | MiniCPM | off | Ornith | Bounded text/sampling; native tool template passed |
| vision | unchanged (`auto`) | n/a | existing | MiniCPM GGUF is text-only; no fake vision routing |
| approval / smart approval | unchanged (`auto`; approvals mode remains off) | n/a | existing | Not downgraded without a conservative adversarial safety gate |
| `goal_judge`, Kanban decomposition/estimation, MoA, delegation | unchanged/inherit | existing | existing | Completion/agent-quality-sensitive and/or background use; not forced through a 2B model |

If FAST is off because DEEP is active, the configured MiniCPM auxiliary route fails over to Ornith. This was live-tested with `title_generation` and returned `Deep Fallback` from the Ornith Q6 endpoint.

## Candidate measurements (direct 8K compact harness)

| Candidate | GGUF size | Direct answer | native tool call | warm response | decode | Decision |
|---|---:|---|---|---:|---:|---|
| MiniCPM5-2B Q4_K_M | 1.56 GB | `Paris` | valid `get_git_status` | 41 ms | ~47–52 tok/s | **Selected** |
| Spark-X2.5-1.7B Q4_K | 0.97 GB | `FR` (incorrect) | valid | 83 ms | ~55–61 tok/s | Rejected: correctness gate failure |
| NeoHorse-1-4B Q4_K_M | 2.71 GB | `PARIS` | valid | 201 ms | ~23–24 tok/s | Rejected: much larger/slower without need |

MiniCPM extended direct checks: capital correct; 5/5 intended terminal/web tool selections emitted a native call; tool continuation correctly interpreted a clean `main` result; compression preservation probe retained every requested critical item. In a real Hermes session, FAST emitted native terminal, file-search, and web-search calls and completed each run. Raw evidence: `raw/e2e-*.sse`, `raw/minicpm5-2b-q4km/extended.json`.

## Changes and rollback

Backups: `backups/20260920T162848+0200/` (all ten configs plus pre-change frontend and manager files).

Changed:
- `~/.hermes/bin/hermes-local-model`
- `~/.hermes/config.yaml` and each `~/.hermes/profiles/*/config.yaml`
- `HermesMobile/server/src/{auto-router.ts,index.ts,proxy.ts}`
- `HermesMobile/src/app/core/{model-selection.store.ts,run-gateway-impl.ts,run-controller.ts}`
- corresponding frontend tests

Rollback: stop lanes, copy the desired file(s) from the timestamped backup, restart the multiplexed gateway and HermesMobile proxy, then `hermes-local-model ensure fast` to restore the former FAST lane. Models and earlier EXP-019 evidence were not removed.

## Known constraint

A full Hermes run carries ~14K static/system/tool context. That materially dominates fast-lane first response and causes more latency than the direct 40 ms warm MiniCPM response. The dedicated minimal profile route was not substituted because it would fragment the user session/tools. This implementation preserves functionality and records the discrepancy rather than hiding it; the next useful experiment is a supported request-scoped minimal toolset/profile route that retains the same session.
