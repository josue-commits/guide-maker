#!/usr/bin/env bash
# Smoke test: fresh machine, no tokens, no network. Exits non-zero on any failure.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -c "import PIL, yaml" 2>/dev/null || { echo "pip install -r requirements.txt first"; exit 2; }
python3 -m compileall -q skills tests
python3 -m unittest tests/test_smoke.py -v
# Nothing under skills/ may be created by the suite (run-time state lives in .guide-maker/).
if git -C . rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  untracked="$(git status --porcelain -- skills/ | grep -E '^\?\?' || true)"
  if [[ -n "$untracked" ]]; then
    echo "run-time writes under skills/:"; echo "$untracked"; exit 1
  fi
fi
