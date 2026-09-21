#!/bin/bash
set -eu
d=~/HermesProjects/Local-LLM-Lab/results/raw/EXP-019-ornith-gguf/models
export HF_HUB_ENABLE_HF_TRANSFER=0
"$HOME/.hermes/hermes-agent/venv/bin/hf" download ornith-ai/Ornith-1.5-9B-GGUF Ornith-1.5-9B-Q6_K.gguf --local-dir "$d" --local-dir-use-symlinks False 2>&1 | tail -5
