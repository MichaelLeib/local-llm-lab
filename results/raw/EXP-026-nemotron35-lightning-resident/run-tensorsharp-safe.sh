#!/bin/bash
# EXP-026 isolated TensorSharp support/memory gate. Loopback-only; one model.
set -euo pipefail
EXP="/Users/<user>/HermesProjects/Local-LLM-Lab/results/raw/EXP-026-nemotron35-lightning-resident"
TS="/Users/<user>/Local-LLM-Lab/results/raw/EXP-020-tensorsharp-gemma4-e4b/runtime/server/TensorSharp.Server.Host"
MODEL="$EXP/models/Nemotron-3.5-Lightning-30B-A3B-MIXED-Q2_0-Q4_0-2.47BPW.gguf"
export TENSORSHARP_LOG_LEVEL=Information
export TENSORSHARP_LOG_DIR="$EXP/tensorsharp-logs"
export MAX_CONTEXT=8192
mkdir -p "$TENSORSHARP_LOG_DIR"
exec taskpolicy -c background "$TS" --model "$MODEL" --backend ggml_metal --host 127.0.0.1 --port 8927 --sampling-precedence request --max-tokens 256 --no-webui
