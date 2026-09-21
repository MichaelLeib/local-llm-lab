#!/usr/bin/env bash
# Approval-gated cache-size probe. Usage: .../run-chat-probe-slots-gated.sh 8
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SLOTS="${1:-}"
[[ "$SLOTS" =~ ^(8|16|24|32|40|48|64|96|112|128|160|192|256)$ ]] || { echo 'usage: script <supported expert-cache-slots>' >&2; exit 2; }
SRC="$ROOT/source/tinytitan"
MODEL="$ROOT/model/qwen3.8-flash-next_125B_A6B_4Bit"
CLI="$SRC/.build/release/TinyTitanCLI"
MESSAGES="$ROOT/chat-probe-messages.json"
RUN="$ROOT/chat-probe-${SLOTS}slots-approved"

if [[ "${EXP006_ALLOW_INFERENCE:-}" != "I_APPROVE_EXP006_INFERENCE" ]]; then
  echo "Refusing inference: explicit user approval marker is absent." >&2
  exit 3
fi
[[ -x "$CLI" && -f "$MODEL/manifest.json" && -f "$MODEL/verified-install.json" && -f "$MESSAGES" ]] || { echo 'Refusing inference: verified inputs missing.' >&2; exit 2; }
if pgrep -af 'TinyTitanCLI|TinyTitanServer|TinyTitanRepack|slipstream|mlx_lm|llama-server' | grep -v "$$"; then
  echo 'Refusing inference: another local model process is present.' >&2; exit 4
fi
mkdir -p "$RUN"
{
  date -u
  printf 'expert_cache_slots=%s\n' "$SLOTS"
  sysctl vm.swapusage
  memory_pressure -Q
  df -h /
  "$CLI" --model "$MODEL" --messages-file "$MESSAGES" --max-new 8 --max-context 4096 --temperature 0 --seed 12345 --thinking off --concise --expert-cache-slots "$SLOTS"
  status=$?
  printf 'probe_exit=%s\n' "$status"
  sysctl vm.swapusage
  memory_pressure -Q
  df -h /
  exit "$status"
} 2>&1 | tee "$RUN/run.log"
