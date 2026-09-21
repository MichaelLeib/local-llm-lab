#!/usr/bin/env bash
# EXP-019: Ornith-1.5-9B GGUF (llama.cpp) campaign — isolated server manager.
# Loopback-only, isolated port 8919. Never touches FAST/DEEP lanes (8901/8902).
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
model="${ORNITH_GGUF:-$root/models/Ornith-1.5-9B-Q6_K.gguf}"
port="${ORNITH_PORT:-8919}"
ctx="${ORNITH_CTX:-8192}"
log="$root/server-q6.log"
pidfile="$root/server.pid"

case "${1:-}" in
  start)
    if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
      echo "server already running pid=$(cat "$pidfile")"; exit 0
    fi
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "port $port already in use"; exit 1
    fi
    /opt/homebrew/bin/llama-server \
      -m "$model" \
      --host 127.0.0.1 --port "$port" \
      -c "$ctx" \
      ${ORNITH_EXTRA:-} \
      >"$log" 2>&1 &
    echo $! > "$pidfile"
    echo "pid=$(cat "$pidfile") ctx=$ctx log=$log"
    ;;
  stop)
    if [ -f "$pidfile" ]; then
      pid="$(cat "$pidfile")"
      kill "$pid" 2>/dev/null || true
      for i in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
      kill -9 "$pid" 2>/dev/null || true
      rm -f "$pidfile"
    fi
    echo "stopped"
    ;;
  status)
    if [ -f "$pidfile" ]; then ps -p "$(cat "$pidfile")" -o pid=,rss=,%cpu=,etime= || true; fi
    curl -fsS "http://127.0.0.1:$port/health" 2>/dev/null && echo || echo "down"
    ;;
  *)
    echo "usage: $0 start|stop|status" >&2; exit 64
    ;;
esac