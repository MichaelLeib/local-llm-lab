#!/usr/bin/env bash
# Approval-gated throughput probe: same model, 16 expert slots, 64-token cap.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/source/tinytitan"
MODEL="$ROOT/model/qwen3.8-flash-next_125B_A6B_4Bit"
CLI="$SRC/.build/release/TinyTitanCLI"
MESSAGES="$ROOT/throughput-messages.json"
RUN="$ROOT/throughput-16slots-approved"

if [[ "${EXP006_ALLOW_INFERENCE:-}" != "I_APPROVE_EXP006_INFERENCE" ]]; then echo 'Refusing inference: explicit approval marker absent.' >&2; exit 3; fi
[[ -x "$CLI" && -f "$MODEL/manifest.json" && -f "$MODEL/verified-install.json" && -f "$MESSAGES" ]] || { echo 'Refusing inference: verified inputs missing.' >&2; exit 2; }
if pgrep -af 'TinyTitanCLI|TinyTitanServer|TinyTitanRepack|slipstream|mlx_lm|llama-server' | grep -v "$$"; then echo 'Refusing inference: competing model process.' >&2; exit 4; fi
mkdir -p "$RUN"
{
  date -u
  printf 'expert_cache_slots=16 max_new=64\n'
  sysctl vm.swapusage
  memory_pressure -Q
  df -h /
  "$CLI" --model "$MODEL" --messages-file "$MESSAGES" --max-new 64 --max-context 4096 --temperature 0 --seed 12345 --thinking off --concise --expert-cache-slots 16
  status=$?
  printf 'probe_exit=%s\n' "$status"
  sysctl vm.swapusage
  memory_pressure -Q
  df -h /
  exit "$status"
} 2>&1 | tee "$RUN/run.log"
