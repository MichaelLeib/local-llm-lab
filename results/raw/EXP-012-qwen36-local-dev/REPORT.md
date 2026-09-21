# EXP-012 — Qwen3.6/Slipstream against existing `local-dev`

**Date:** 2026-09-18
**Status:** integration protocol root cause identified; slim native Hermes tool-loop passed. Not promoted as the default local-dev configuration.

## Objective

Use the existing `local-dev` coding profile rather than create a second local coder profile. Determine why Qwen3.6/Slipstream failed under its current payload and prove or reject a minimal coding shape through a real Hermes tool loop.

## Preconditions and build

- Qwen3-Coder-Next `EXP-011` was deleted at the user’s request; 43 GiB reclaimed (10 GiB -> 52 GiB available).
- FAST and DEEP were down before launch; no other custom runtime process was live.
- Existing Qwen artifact: `EXP-005/model/qwen36.gturbo`.
- Existing pinned Slipstream source was rebuilt with:
  `swift build -c release --product slipstream-server`
- Build completed in 112.54 seconds. It had existing Command Line Tools path and Swift Sendable warnings but completed successfully.
- Test server: port 8901, 8192 context, 16 expert-cache slots, single-prefix cache.

## Protocol root cause

`local-dev` normally uses Codex Responses transport, while Slipstream exposes only `/v1/chat/completions`; `/v1/responses` returned HTTP 404.

After temporarily switching only the test transport to chat completions, captured request replay showed the decisive failure:

| Request shape | Rendered prompt | Result |
| --- | ---: | --- |
| Existing EXP-005 four-tool request | 4,998 tokens | Pass: `terminal(date)` tool call; 115.94 s TTFT |
| Current local-dev system + terminal only | 4,588 tokens | Pass: `terminal(date)` tool call; 103.39 s TTFT |
| Current local-dev system + coding file/terminal tools (`patch`, `read_file`, `search_files`, `terminal`, `write_file`) | 5,763 tokens | Pass: `terminal(date)` tool call; 143.30 s TTFT |
| Current local-dev full 13-tool request | exceeds 8,192-token runtime context | Correct direct-server rejection: HTTP 400 `context_length_exceeded` before prefill |

The earlier Hermes `RemoteProtocolError` was therefore a client-side symptom of an over-context rendered request, not a model/tool-call failure. The server’s direct structured error identifies the root cause.

## Real Hermes validation

For the native test, `local-dev` was **temporarily** set to its Qwen-compatible shape:

- chat-completions transport;
- 8192 context ceiling;
- `terminal` and `file` toolsets only;
- no model reasoning-effort field;
- streaming disabled for the test.

### Cold native terminal loop

Prompt: `Use the terminal tool to run: date. Then return the exact command output and nothing else.`

- Hermes executed the real terminal command: `date`.
- Output returned to the user: `Fri Sep 18 21:55:47 CEST 2026`.
- Server request 1: 5,302 prompt tokens, 46 completion tokens, **126.53 s TTFT**, 41.9 prefill tok/s, 6.9 decode tok/s, `stop=tool_calls`.
- Tool-result follow-up: 5,401 total / 5,347 cached / 54 new prompt tokens, **4.34 s TTFT**, 6.9 decode tok/s, final normal `stop`.

### Warm resumed native terminal loop

Prompt: `Now use the terminal tool to run: pwd. Return only the exact output.`

- Hermes executed the real terminal command: `pwd`.
- Output returned: `/Users/<user>`.
- Tool-call request: 5,465 total / 5,437 cached / 28 new prompt tokens, **3.12 s TTFT**, 6.3 decode tok/s, `stop=tool_calls`.
- Tool-result follow-up: 5,547 total / 5,509 cached / 38 new prompt tokens, **3.77 s TTFT**, 6.1 decode tok/s, final normal `stop`.

The auxiliary Hermes title generator still tried an unsupported `reasoning_effort` request and logged a non-fatal HTTP 400. It did not affect the actual native tool loops.

## Decision

Qwen3.6 now has a validated, slim `local-dev` integration arm: terminal/file coding operations remain below the 8192 context limit and execute real native Hermes tools. The first turn remains non-interactive at 126.53 seconds, but the persistent follow-up loop has 3.12–4.34 second TTFT.

Do not make this the default `local-dev` configuration yet. The existing FAST lane uses a different transport/context configuration, and the profile cannot safely become a dual-runtime default without a per-model transport/context selection mechanism. Restore the current proven FAST configuration after this experiment; any durable Qwen entry point must preserve that fallback and use the slim toolset from the start.

## Persistent entry point

Installed `~/.hermes/bin/local-qwen-coder`. It creates a persistent, isolated
runtime overlay derived from `local-dev` at
`~/.hermes/runtime/local-qwen-coder/home`; the normal `local-dev` profile is
never edited. The overlay declares the 64K window Hermes requires while the
Slipstream server itself remains capped at the measured 8192-token safe
runtime ceiling.

- `local-qwen-coder` — starts Qwen explicitly, opens an interactive slim coding session, and unloads Qwen on exit.
- `local-qwen-coder --oneshot --query '…'` — bounded single query.
- `local-qwen-coder --resume <session-id>` — resumes a Qwen coding session.
- `local-qwen-coder --prepare-only` — verifies/prepares the overlay without loading a model.

It refuses to evict FAST/DEEP; a managed lane must be stopped explicitly first.
It also owns and cleans up only its own Slipstream PID. End-to-end wrapper
validation completed a real Hermes `terminal(date)` call and returned
`Fri Sep 18 22:04:07 CEST 2026`; it then verified that port 8901 was closed,
no Slipstream process remained, and `local-dev` stayed on its original
Codex Responses/64K/full-toolset configuration.

## Artifacts

- `protocol_matrix.py` / `protocol-matrix-result.json` — captured payload minimization.
- `coding_five_tools_probe.py` / `coding-five-tools-result.json` — coding-tool request replay.
- `slipstream-server-protocol.log` — server timings and cache evidence.
