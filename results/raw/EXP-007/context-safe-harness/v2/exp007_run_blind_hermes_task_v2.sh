#!/usr/bin/env bash
# Execute one blinded, fresh-worktree Hermes task arm for EXP-007 context-safe-v2.
set -euo pipefail

ROOT=/Users/<user>/HermesProjects/Local-LLM-Lab
SOURCE_BENCH="$ROOT/results/raw/EXP-007/real-repo-ab"
BENCH="$ROOT/results/raw/EXP-007/real-repo-ab-v2"
ASSIGNMENT="$SOURCE_BENCH/private/assignment.json"
PROFILE="$HOME/.local/bin/exp007benchv2"
POLICY="$ROOT/results/raw/EXP-007/context-safe-harness/v2/POLICY.md"
FREEZE_MANIFEST="$ROOT/results/raw/EXP-007/context-safe-harness/v2/freeze-manifest.json"
FREEZE_VERIFY="$ROOT/results/raw/EXP-007/context-safe-harness/v2/verify_v2_freeze.py"
SERVER="$ROOT/results/raw/EXP-007/source/slipstream-hermes-compat/.build/release/slipstream-server"


if [ "$#" -ne 2 ]; then
  echo "usage: $0 <blind-candidate-id> <task-id>" >&2
  exit 64
fi
CID=$1
TASK=$2
[ "$TASK" = T01 ] || { echo "only T01 is ready for scored execution" >&2; exit 64; }
[ -f "$ASSIGNMENT" ] || { echo "missing sealed assignment" >&2; exit 65; }
[ -x "$PROFILE" ] || { echo "missing benchmark profile wrapper" >&2; exit 65; }
[ -x "$SERVER" ] || { echo "missing Slipstream server" >&2; exit 65; }
[ -f "$FREEZE_MANIFEST" ] || { echo "missing v2 freeze manifest" >&2; exit 65; }
python3 "$FREEZE_VERIFY" "$FREEZE_MANIFEST" || { echo "v2 freeze receipt verification failed" >&2; exit 65; }

CANDIDATE_RECORD=$(python3 - "$ASSIGNMENT" "$CID" <<'PY'
import json, sys
x=json.load(open(sys.argv[1], encoding='utf-8'))['assignment'][sys.argv[2]]
print(x['engine'] + '|' + (x['artifact'] or ''))
PY
)
ENGINE=${CANDIDATE_RECORD%%|*}
ARTIFACT=${CANDIDATE_RECORD#*|}

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
RUN="$BENCH/results/$CID/hermes/$TASK/$STAMP"
WORKTREES="$BENCH/worktrees"
FIXTURE="$SOURCE_BENCH/fixtures/T01-ios-layout"
PROMPT="$SOURCE_BENCH/prompts/T01/task.md"
ORACLE="$SOURCE_BENCH/oracles/T01/check.py"
HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
mkdir -p "$RUN" "$WORKTREES"
WT="$WORKTREES/${CID}-hermes-${TASK}-${STAMP}"

cleanup() {
  local rc=$?

  if [ "${SERVER_PID:-}" != "" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill -TERM "$SERVER_PID" || true
    wait "$SERVER_PID" || true
  fi
  if [ "${MANAGED_FAST:-0}" = 1 ]; then
    "$HOME/.hermes/bin/hermes-local-model" stop fast >>"$RUN/cleanup.log" 2>&1 || true
  fi
  for p in 8901 8997; do lsof -nP -iTCP:"$p" -sTCP:LISTEN >>"$RUN/cleanup.log" 2>&1 || true; done
  sysctl vm.swapusage >>"$RUN/postflight.txt" 2>&1 || true
  memory_pressure >>"$RUN/postflight.txt" 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT INT TERM

# Preserve candidate-independent controls before launch. This output intentionally never contains model identity.
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  printf 'blind_candidate=%s\nharness=hermes\ntask=%s\n' "$CID" "$TASK"
  shasum -a 256 "$PROMPT"
  shasum -a 256 "$POLICY"
  git -C "$FIXTURE" rev-parse HEAD
  sysctl vm.swapusage
  memory_pressure
  df -h /
} >"$RUN/preflight.txt"

# Reject cross-residency rather than killing a possible competing task.
for port in 8901 8902 8997 8998; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >"$RUN/unexpected-listener-$port.txt" 2>&1; then
    echo "benchmark precondition failed: listener already active on $port" >&2
    exit 66
  fi
done

COMMIT=$(git -C "$FIXTURE" rev-parse HEAD)
git -C "$FIXTURE" worktree add --detach "$WT" "$COMMIT" >"$RUN/worktree-create.txt" 2>&1
# Dependencies are fixture infrastructure, never candidate output; every T01 arm gets this same read-only target.
ln -s "$FIXTURE/node_modules" "$WT/node_modules"
printf '%s\n' "$WT" >"$RUN/worktree-path.txt"

# A scored arm must fail closed if its profile-local, hook-only observation layer
# is unavailable. This imports plugins but starts no model and changes no schema.
HERMES_HOME="$HOME/.hermes/profiles/exp007benchv2" "$HERMES_PY" - >"$RUN/context-safe-hook-check.txt" 2>&1 <<'PY'
from hermes_cli import plugins
from hermes_cli.lifecycle import has_hook
plugins.discover_plugins()
if not has_hook("transform_tool_result"):
    raise SystemExit("EXP-007 context-safe-v2 hook is not loaded")
print("EXP-007 context-safe-v2 hook loaded")
PY

SERVER_PID=""
MANAGED_FAST=0
case "$ENGINE" in
  slipstream)
    PORT=8997
    "$SERVER" --model "$ARTIFACT" --port "$PORT" --model-id "$CID" \
      --max-context 16384 --prompt-cache-mode single-prefix --expert-cache-slots 16 --expert-cache-policy lfu-aging \
      >"$RUN/server.log" 2>&1 &
    SERVER_PID=$!
    ;;
  managed-fast)
    PORT=8901
    MANAGED_FAST=1
    "$HOME/.hermes/bin/hermes-local-model" start fast >"$RUN/server.log" 2>&1
    ;;
  *) echo "unsupported sealed candidate engine" >&2; exit 65;;
esac

for _ in $(seq 1 240); do
  if curl --fail --silent --show-error --max-time 3 "http://127.0.0.1:$PORT/v1/models" >"$RUN/models.json" 2>>"$RUN/server-ready.err"; then break; fi
  sleep 1
done
[ -s "$RUN/models.json" ] || { echo "candidate server never became ready" >&2; exit 67; }

# This profile is isolated; these endpoint changes are intentional per-run configuration, not user defaults.
"$PROFILE" config set model.provider custom >"$RUN/profile-config.txt" 2>&1
"$PROFILE" config set model.base_url "http://127.0.0.1:$PORT/v1" >>"$RUN/profile-config.txt" 2>&1
"$PROFILE" config set model.api_mode chat_completions >>"$RUN/profile-config.txt" 2>&1

# Actual scored fresh Hermes session. 4096 max output is pinned in the benchmark profile config.
START=$(python3 -c 'import time; print(time.time())')
set +e
EXP007_CONTEXT_SAFE_METRICS_PATH="$RUN/context-safe-tool-results.jsonl" \
"$PROFILE" chat --query-file "$PROMPT" --oneshot --in "$WT" --no-restore-cwd \
  --model "$CID" --provider custom --toolsets terminal,file --ignore-rules --yolo \
  --max-turns 120 --run-budget 1800 \
  >"$RUN/final.txt" 2>"$RUN/hermes.stderr"
AGENT_RC=$?
set -e
END=$(python3 -c 'import time; print(time.time())')
python3 - "$START" "$END" "$AGENT_RC" >"$RUN/agent-result.json" <<'PY'
import json, sys
print(json.dumps({'wall_seconds': float(sys.argv[2])-float(sys.argv[1]), 'exit_code': int(sys.argv[3])}, indent=2))
PY
python3 "$ROOT/results/raw/EXP-007/context-safe-harness/v2/exp007_summarize_context_metrics_v2.py" "$RUN" \
  --context-limit 16384 --completion-allowance 4096 >"$RUN/context-efficiency-runner.log" 2>&1
python3 "$ROOT/results/raw/EXP-007/context-safe-harness/v2/exp007_retrieval_refinement.py" \
  "$RUN/context-safe-tool-results.jsonl" --output "$RUN/retrieval-refinement.json" \
  >"$RUN/retrieval-refinement-runner.log" 2>&1

git -C "$WT" status --short >"$RUN/git-status.txt" || true
git -C "$WT" diff --binary >"$RUN/final.diff" || true
set +e
python3 "$ORACLE" "$WT" >"$RUN/acceptance.txt" 2>&1
printf '%s\n' "$?" >"$RUN/acceptance.exit-code"
(
  cd "$WT"
  "$HOME/.local/bin/node" node_modules/@angular/cli/bin/ng.js test --watch=false --include 'src/app/**/*.spec.ts' --exclude src/app/core/live-contract.spec.ts
) >"$RUN/regression.txt" 2>&1
printf '%s\n' "$?" >"$RUN/regression.exit-code"
(
  cd "$WT"
  "$HOME/.local/bin/node" node_modules/@angular/cli/bin/ng.js build --configuration production
) >"$RUN/build.txt" 2>&1
printf '%s\n' "$?" >"$RUN/build.exit-code"
set -e

# Human-facing run state is blind: it never contains candidate identity.
printf 'completed blind_candidate=%s task=%s hermes_exit=%s\n' "$CID" "$TASK" "$AGENT_RC" >"$RUN/summary.txt"
printf '%s\n' "$RUN"
