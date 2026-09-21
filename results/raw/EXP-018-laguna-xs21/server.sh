#!/bin/bash
# Isolated Laguna endpoint manager; never touches FAST/DEEP or production config.
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
model="$root/model-mlx3"
port="${LAGUNA_PORT:-8918}"
log="$root/server.log"
pidfile="$root/server.pid"
case "${1:-}" in
 start)
  ~/.hermes/bin/hermes-local-model stop all >/dev/null 2>&1 || true
  if pgrep -f "rapid-mlx serve.*$port" >/dev/null; then echo "server already exists on $port" >&2; exit 1; fi
  RAPID_MLX_TELEMETRY=0 rapid-mlx --no-banner serve "$model" --host 127.0.0.1 --port "$port" --served-model-name laguna-xs21 --max-num-seqs 1 --max-concurrent-requests 1 --prefill-step-size "${PREFILL_STEP_SIZE:-512}" --cache-memory-percent 0.12 --enable-prefix-cache --idle-cache-clear-seconds 0 --no-thinking --no-spec-decode --log-level INFO >"$log" 2>&1 &
  echo $! > "$pidfile"; echo "pid=$(cat "$pidfile") log=$log";;
 stop)
  if [ -f "$pidfile" ]; then kill "$(cat "$pidfile")" 2>/dev/null || true; rm -f "$pidfile"; fi
  pgrep -f "rapid-mlx serve.*$port" | xargs -n1 kill 2>/dev/null || true;;
 status)
  if [ -f "$pidfile" ]; then ps -p "$(cat "$pidfile")" -o pid=,rss=,%cpu=,etime=; fi
  curl -fsS "http://127.0.0.1:$port/v1/models" || true;;
 *) echo "usage: $0 start|stop|status" >&2; exit 64;;
esac
