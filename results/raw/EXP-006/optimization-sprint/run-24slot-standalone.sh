#!/usr/bin/env bash
# EXP-006 optimization sprint: first numerics-preserving 24-slot arm.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(cd "$(dirname "$0")" && pwd)/bundle-24slot-standalone"
SRC="$ROOT/source/tinytitan"
MODEL="$ROOT/model/qwen3.8-flash-next_125B_A6B_4Bit"
CLI="$SRC/.build/release/TinyTitanCLI"
MESSAGES="$ROOT/throughput-messages.json"
mkdir -p "$OUT"
[[ -x "$CLI" && -f "$MODEL/manifest.json" && -f "$MODEL/verified-install.json" && -f "$MESSAGES" ]] || { echo 'Refusing: verified inputs missing.' >&2; exit 2; }
if pgrep -af 'TinyTitanCLI|TinyTitanServer|TinyTitanRepack|slipstream|mlx_lm|llama-server|rapid-mlx' | grep -v "$$"; then
  echo 'Refusing: competing local model process.' >&2
  exit 4
fi
{
  date -u
  printf 'bundle=24-slot-standalone\n'
  printf 'command=TinyTitanCLI --messages-file throughput-messages.json --max-new 64 --max-context 4096 --temperature 0 --seed 12345 --thinking off --concise --expert-cache-slots 24\n'
  sysctl vm.swapusage
  memory_pressure -Q
  df -h /
  TINYTITAN_DECODE_IO_TRACE=1 "$CLI" --model "$MODEL" --messages-file "$MESSAGES" --max-new 64 --max-context 4096 --temperature 0 --seed 12345 --thinking off --concise --expert-cache-slots 24
  status=$?
  printf 'probe_exit=%s\n' "$status"
  sysctl vm.swapusage
  memory_pressure -Q
  df -h /
  exit "$status"
} 2>&1 | tee "$OUT/run.log"
