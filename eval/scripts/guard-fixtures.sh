#!/usr/bin/env bash
# guard-fixtures.sh — add a DO-NOT-EDIT guard header to every mutable eval fixture,
# so a "helpful" agent or linter can't silently fix a planted bug (see LESSONS.md #7).
#
# Run this ONLY when no grid is in flight (in-flight arms read these files live).
# Idempotent: skips a file that already has the guard.
#
# Usage: eval/scripts/guard-fixtures.sh

set -euo pipefail
shopt -s nullglob

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# Neutral wording on purpose: the arm agents READ these files, so the guard must not
# reveal what (if anything) is planted — it only forbids editing. No spoilers.
GUARD_PY='# READ-ONLY eval fixture — do not modify this file. Provide any solution in your
# response, not by editing here. (Editing corrupts the shared fixture for other runs.)'

added=0 skipped=0
for f in "$ROOT"/eval/tasks/*/context/*.py; do
  first="$(head -1 "$f")"
  if [[ "$first" == *"DO NOT EDIT — eval fixture"* ]]; then
    skipped=$((skipped+1)); continue
  fi
  # Prepend the guard, preserving the rest of the file
  tmp="$(mktemp)"
  printf '%s\n' "$GUARD_PY" > "$tmp"
  cat "$f" >> "$tmp"
  mv "$tmp" "$f"
  added=$((added+1))
  echo "guarded: ${f#$ROOT/}"
done

echo "Done: $added guarded, $skipped already had the header."
echo "Verify fixtures are otherwise pristine: git status --short eval/tasks/*/context/"
