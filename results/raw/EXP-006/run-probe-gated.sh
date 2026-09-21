#!/usr/bin/env bash
# Approval-gated standalone probe. Do not remove the gate.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/source/tinytitan"
MODEL="$ROOT/model/qwen3.8-flash-next_125B_A6B_4Bit"
CLI="$SRC/.build/release/TinyTitanCLI"
RUN="$ROOT/first-probe-approved"

if [[ "${EXP006_ALLOW_INFERENCE:-}" != "I_APPROVE_EXP006_INFERENCE" ]]; then
  echo "Refusing inference: explicit user approval marker is absent." >&2
  exit 3
fi
[[ -x "$CLI" ]] || { echo "TinyTitanCLI is not built: $CLI" >&2; exit 2; }
[[ -f "$MODEL/manifest.json" && -f "$MODEL/verified-install.json" ]] || {
  echo "Refusing inference: verified model receipt is not present." >&2
  exit 2
}
if pgrep -af 'TinyTitanCLI|TinyTitanServer|TinyTitanRepack|slipstream|mlx_lm|llama-server' | grep -v "$$"; then
  echo "Refusing inference: another local model process is present." >&2
  exit 4
fi
mkdir -p "$RUN"
{
  date -u
  sw_vers
  xcrun swift --version
  sysctl -n hw.model hw.memsize hw.ncpu
  sysctl vm.swapusage
  memory_pressure -Q
  df -h /
  "$CLI" \
    --model "$MODEL" \
    --prompt 'Reply with exactly READY.' \
    --max-new 8 \
    --max-context 4096 \
    --temperature 0 \
    --seed 12345
  status=$?
  printf 'probe_exit=%s\n' "$status"
  sysctl vm.swapusage
  df -h /
  exit "$status"
} 2>&1 | tee "$RUN/run.log"
