#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HUB_DISABLE_PROGRESS_BARS=1
# Revision and target are frozen in runtime-survey.md. --local-dir avoids a
# second project-level copy; no existing hub snapshot or experiment is removed.
hf download manjunathshiva/Laguna-S-2.1-tqTe-g64 \
  --revision 5c08cd7e895257df166dece30405219af66034de \
  --local-dir model/laguna-s21-tqTe-g64 \
  2>&1 | tee logs/laguna-tqte-download.log
