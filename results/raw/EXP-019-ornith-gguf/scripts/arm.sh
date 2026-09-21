#!/bin/bash
# EXP-019: run one benchmark arm with sysmon sampling + server restart between context changes.
# usage: arm.sh LABEL CTX [EXTRA_FLAGS]
# Env: ORNITH_PORT, ORNITH_EXTRA
set -u
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
label="$1"; ctx="$2"; extra="${3:-}"
export ORNITH_CTX="$ctx"
export ORNITH_EXTRA="$extra"
scripts_dir="$root/scripts"

"$scripts_dir/ornith-server.sh" stop >/dev/null 2>&1
t0=$(date +%s)
"$scripts_dir/ornith-server.sh" start >/dev/null
for i in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8919/health >/dev/null 2>&1; then break; fi
  if ! kill -0 "$(cat "$root/server.pid" 2>/dev/null)" 2>/dev/null; then
    echo "{\"label\":\"$label\",\"status\":\"SERVER_DIED\"}"; exit 1
  fi
  sleep 1
done
load_s=$(( $(date +%s) - t0 ))

LLM_EXP_ROOT="$root" "$HOME/HermesProjects/Local-LLM-Lab/tools/llm-exp/sysmon" "$root/raw/$label-sysmon.jsonl" 600 2>/dev/null &
SYS=$!
sleep 0.3

echo "ARM $label ctx=$ctx load_s=$load_s"
echo "{\"label\":\"$label\",\"ctx\":$ctx,\"load_s\":$load_s}" > "$root/raw/$label-arm.json"
wait $SYS 2>/dev/null
echo "sysmon done"