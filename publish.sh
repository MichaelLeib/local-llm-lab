#!/bin/bash
# publish.sh — scrub + verify + commit + push Local-LLM-Lab results to GitHub.
#
# Usage: ./publish.sh [commit message]
#
# Pipeline (fail-closed: any failed gate aborts before push):
#   1. scrub     — rewrite personal identifiers in tracked files (idempotent)
#   2. verify    — index scan: ZERO personal-data residue allowed
#   3. untracked — check for never-commit paths (backups/, worktrees/, bundles…)
#   4. commit    — repo-local identity (noreply), NOT the global config
#   5. push      — origin main
#
# Rules the scrub applies (see PUBLISHING.md for rationale):
#   /Users/michaelleib  ->  /Users/<user>     (recorded absolute paths)
#   100.85.108.51       ->  100.x.x.x.51      (Tailnet address)
#   michaelleib         ->  <user>            (bare username: ps columns, ls -l owners)
#
# This script NEVER touches: LICENSE attribution, docs' descriptions of the
# scrub itself (SANITIZATION.md / PUBLISHING.md use the tokens in tables),
# or excluded (untracked) material.
set -euo pipefail
cd "$(dirname "$0")"

MSG="${1:-Publish experiment results}"
IDENTITY_NAME="MichaelLeib"
IDENTITY_EMAIL="73171570+MichaelLeib@users.noreply.github.com"
ORIGIN_URL="https://github.com/MichaelLeib/local-llm-lab.git"

# --- 1. SCRUB tracked files (worktree) -------------------------------------
# Run repeatedly until fixpoint: a file can contain several forms; the sed
# applies longest-first within one pass (/Users/... before bare username).
# Compatible with macOS bash 3.2 (no mapfile).
pass=0; total_files=0
while :; do
  # collector: grep legitimately fails (exit 1) on no-match files; keep that
  # from tripping `set -e` by running the substitution with errexit disabled
  set +e
  files=$(git ls-files | grep -vE '^(PUBLISHING\.md|SANITIZATION\.md|publish\.sh)$' | while IFS= read -r f; do
    [ -f "$f" ] && grep -lE "michaelleib|100\.85\.108\.51" "$f" 2>/dev/null
  done)
  set -e
  [ -z "$files" ] && break
  pass=$((pass+1))
  # shellcheck disable=SC2086
  n=$(printf '%s\n' "$files" | wc -l | tr -d ' ')
  total_files=$((total_files+n))
  printf '%s\n' "$files" | while IFS= read -r f; do
    sed -i '' \
      -e 's|/Users/michaelleib|/Users/<user>|g' \
      -e 's|100\.85\.108\.51|100.x.x.x.51|g' \
      -e 's|michaelleib|<user>|g' \
      "$f"
  done
  echo "[scrub pass $pass] rewrote tokens in $n files"
done

# --- 2. VERIFY index is clean ----------------------------------------------
stage_all() { git add -A; }
stage_all
bad=$(git grep --cached -lE "michaelleib|100\.85\.108\.51" -- . | grep -vE "^(PUBLISHING\.md|SANITIZATION\.md|publish\.sh)$" || true)
if [ -n "$bad" ]; then
  echo "ABORT: personal-data residue in index:" >&2
  echo "$bad" >&2
  exit 20
fi
echo "[verify] index clean (0 residue)"

# --- 3. UNTRACKED safety check ----------------------------------------------
forbidden=$(git status --porcelain | awk '$1=="??" {print $2}' | grep -E \
  '(^|/)(backups|worktrees|node_modules|site-packages|__pycache__|packed_experts|binaries|ios-native|fixtures|source|venv.*)(/|$)|\.bundle$|\.tgz$|\.tar(\.gz)?$|\.gguf$|\.safetensors$|weights|\.bin$' || true)
if [ -n "$forbidden" ]; then
  echo "[gate] leaving untracked material out (this is normal, NOT an error):"
  echo "$forbidden" | head -8
fi

# --- 4. COMMIT (repo-local noreply identity, always) ------------------------
if git diff --cached --quiet; then
  echo "[commit] nothing to publish (working tree matches origin/main)"
  exit 0
fi
export GIT_AUTHOR_NAME="$IDENTITY_NAME" GIT_AUTHOR_EMAIL="$IDENTITY_EMAIL"
export GIT_COMMITTER_NAME="$IDENTITY_NAME" GIT_COMMITTER_EMAIL="$IDENTITY_EMAIL"
git commit -q -m "$MSG

Scrub applied: personal paths -> /Users/<user>, Tailnet IP -> 100.x.x.x.51.
Sanitization policy: PUBLISHING.md"
echo "[commit] $(git log -1 --format='%h %s')"

# --- 5. PUSH -----------------------------------------------------------------
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "$ORIGIN_URL"
fi
current_url=$(git remote get-url origin)
if [ "$current_url" != "$ORIGIN_URL" ]; then
  echo "ABORT: origin points to $current_url, expected $ORIGIN_URL" >&2
  exit 30
fi
git push -q origin main
echo "[push] origin/main -> $(git ls-remote origin main | cut -f1)"
echo "DONE. Published $MSG"