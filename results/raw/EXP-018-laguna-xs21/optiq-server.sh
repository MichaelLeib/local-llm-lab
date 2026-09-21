#!/bin/bash
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"; port="${LAGUNA_PORT:-8918}"; pidfile="$root/optiq-server.pid"; log="$root/optiq-server.log"
case "${1:-}" in
start)
  ~/.hermes/bin/hermes-local-model stop all >/dev/null 2>&1 || true
  "$root/server.sh" stop || true
  "$root/venv/bin/optiq" serve --model "$root/model-mlx3" --host 127.0.0.1 --port "$port" --max-tokens 256 --max-concurrent 1 --max-context 8192 --kv-bits 4 --stream-experts --stream-experts-cache 0 --idle-timeout 0 --on-generation-death exit >"$log" 2>&1 & echo $! > "$pidfile"; echo "pid=$(cat "$pidfile") log=$log";;
stop) [ -f "$pidfile" ] && kill "$(cat "$pidfile")" 2>/dev/null || true; rm -f "$pidfile";;
status) [ -f "$pidfile" ] && ps -p "$(cat "$pidfile")" -o pid=,rss=,%cpu=,etime=; curl -fsS "http://127.0.0.1:$port/v1/models" || true;;
*) echo 'usage: optiq-server.sh start|stop|status' >&2; exit 64;;
esac
