# EXP-006 Hermes runbook (approval-gated)

Do not execute this runbook until the user explicitly says to begin inference.

1. Run `preflight.py`; do not proceed unless the native receipt is verified.
2. Create an isolated `exp006` Hermes profile cloned from the current profile, with no default-profile changes.
3. Launch TinyTitanServer on `127.0.0.1:8092` with the verified model and an 8,192-token initial context.
4. Check `/health` and `/v1/models` before Hermes.
5. Test Chat Completions non-streaming, SSE streaming, and a constrained terminal function call.
6. Run the same `date` terminal-tool task used for EXP-005.
7. Capture first-turn TTFT, prompt tokens, tool-call decode, execution, final answer, total wall time, then a cached follow-up.
8. Stop only the server started by this experiment and verify port/process closure.

The server must remain loopback-only. Do not change the global Hermes profile or promote the model automatically.
