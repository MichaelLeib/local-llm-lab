#!/usr/bin/env bash
# EXP-020 isolated Bonsai 2 server lifecycle. Loopback-only on 8920.
set -euo pipefail
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
bin="$root/bin/llama-prism-b10709-9a9394a/llama-server"
model="${BONSAI_GGUF:-$root/models/Ternary-Bonsai-2-27B-PTQ1_0.gguf}"
port="${BONSAI_PORT:-8920}"
ctx="${BONSAI_CTX:-8192}"
log="${BONSAI_LOG:-$root/raw/server-$(basename "$model" .gguf)-ctx${ctx}.log}"
pidfile="$root/server.pid"

case "${1:-}" in
  start)
    [[ -x "$bin" && -s "$model" ]] || { echo "missing binary/model" >&2; exit 2; }
    if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then echo "already running"; exit 0; fi
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then echo "port $port already in use" >&2; exit 1; fi
    "$bin" -m "$model" --host 127.0.0.1 --port "$port" \
      -ngl 99 -c "$ctx" -b "${BONSAI_BATCH:-1024}" -ub "${BONSAI_UBATCH:-512}" -np 1 -fa on --jinja \
      --reasoning-budget "${BONSAI_REASONING_BUDGET:-512}" \
      --temp "${BONSAI_TEMP:-0.6}" --top-p "${BONSAI_TOP_P:-0.95}" --top-k "${BONSAI_TOP_K:-20}" \
      --metrics ${BONSAI_EXTRA:-} >"$log" 2>&1 &
    echo $! > "$pidfile"
    echo "pid=$(cat "$pidfile") port=$port ctx=$ctx log=$log"
    ;;
  stop)
    if [[ -f "$pidfile" ]]; then
      pid="$(cat "$pidfile")"; kill -TERM "$pid" 2>/dev/null || true
      for _ in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
      kill -KILL "$pid" 2>/dev/null || true
      rm -f "$pidfile"
    fi
    for pid in $(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true); do kill -TERM "$pid" 2>/dev/null || true; done
    ;;
  status)
    [[ -f "$pidfile" ]] && ps -p "$(cat "$pidfile")" -o pid=,rss=,%cpu=,etime=,command= || true
    curl -fsS "http://127.0.0.1:$port/health" || true
    ;;
  *) echo "usage: $0 start|stop|status" >&2; exit 64 ;;
esac
