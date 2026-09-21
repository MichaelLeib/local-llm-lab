#!/bin/zsh
# EXP-013: wait for the verified model transfer, then run the authorized Stage 1 smoke gate.
set -euo pipefail

ROOT="/Users/<user>/HermesProjects/Local-LLM-Lab"
MODEL="$ROOT/models/Qwen3.8-Flash-Next-tq4a-tq2e-g64-9e5c434"
VENV="$ROOT/results/raw/EXP-013-qwen38-flash-2bit-streaming/venv"
RAW="$ROOT/results/raw/EXP-013-qwen38-flash-2bit-streaming"
DOWNLOAD_PID=5331
RUN="$RAW/stage1-smoke-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN"

# The download is resumable. Do not begin inference until its process leaves and
# the exact 11-shard text model passes index-size validation.
# A completed background downloader can remain as a zombie until its launcher
# reaps it. Treat Z as completed rather than waiting forever.
while kill -0 "$DOWNLOAD_PID" 2>/dev/null; do
  state="$(ps -o state= -p "$DOWNLOAD_PID" 2>/dev/null | tr -d ' ' || true)"
  [[ "$state" == Z* ]] && break
  sleep 20
done

"$VENV/bin/python" - "$MODEL" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1])
idx=json.loads((p/'model.safetensors.index.json').read_text())
files=sorted(set(idx['weight_map'].values()))
assert len(files)==11, files
for name in files:
    f=p/name
    assert f.is_file(), f'missing {f}'
    assert f.stat().st_size > 1_000_000, f'truncated {f}: {f.stat().st_size}'
for name in ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja'):
    assert (p/name).is_file(), f'missing {name}'
print('download validation: PASS (11 indexed text shards + tokenizer/config)')
PY

~/.hermes/bin/hermes-local-model status > "$RUN/local-lane-before.txt" 2>&1 || true
if ! grep -q 'FAST: down' "$RUN/local-lane-before.txt" || ! grep -q 'DEEP: down' "$RUN/local-lane-before.txt"; then
  echo 'Refusing Stage 1: an existing local-model lane is not down.' >&2
  exit 20
fi

{
  date -Iseconds
  vm_stat
  sysctl vm.swapusage
  memory_pressure -Q
  df -k /
} > "$RUN/system-before.txt"
iostat -w 1 > "$RUN/iostat.txt" 2>&1 &
IOSTAT_PID=$!
trap 'kill "$IOSTAT_PID" 2>/dev/null || true' EXIT

"$VENV/bin/python" -m turboquant_mlx.stream.stream_generate \
  --model "$MODEL" \
  --prompt 'State the capital of France, then give one sentence explaining why the answer is unambiguous.' \
  --max-tokens 48 \
  --temp 0 \
  --cache-budget-gb 1 \
  --max-active-experts 0 \
  --ngram-offload \
  --no-think \
  --no-learn-experts \
  > "$RUN/generation.log" 2>&1

{
  date -Iseconds
  vm_stat
  sysctl vm.swapusage
  memory_pressure -Q
  df -k /
} > "$RUN/system-after.txt"
kill "$IOSTAT_PID" 2>/dev/null || true
wait "$IOSTAT_PID" 2>/dev/null || true
trap - EXIT
printf '%s\n' "$RUN" > "$RAW/stage1-current-run.txt"
printf 'stage1 smoke: PASS; evidence directory: %s\n' "$RUN"
