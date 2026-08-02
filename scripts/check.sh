#!/usr/bin/env bash
# scripts/check.sh — the one command that gates a commit (s64 P2).
#
#   cargo test --release   (139 pass / 6 ignored; the count must not decrease)
# + python3 -m pytest tests_py/   (the fast control tier)
#
# Exits non-zero if EITHER fails, and prints a one-line verdict per stage
# so a failure is attributable at a glance.  The heavy Python tier is NOT
# run here: `python3 -m pytest tests_py/ -m slow` is a separate, deliberate
# invocation (it re-derives the s63 singleton fixpoint and restores frozen
# state around itself).
#
# Usage:  scripts/check.sh            # both stages
#         scripts/check.sh --py       # Python tier only (skip cargo)
#         scripts/check.sh --rust     # cargo only
#
# bash 3.2 compatible on purpose: the Mac ships 3.2 and the s63 farm lost a
# pre-flight to a bash-4 builtin (`mapfile`).  No arrays, no `readarray`.
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1

run_rust=1
run_py=1
case "${1:-}" in
  --py)   run_rust=0 ;;
  --rust) run_py=0 ;;
  "")     ;;
  *)      echo "usage: $0 [--py|--rust]" >&2; exit 64 ;;
esac

rust_status="skipped"
py_status="skipped"
rc=0

if [ "$run_rust" -eq 1 ]; then
  echo "=== cargo test --release ==="
  if cargo test --release; then
    rust_status="PASS"
  else
    rust_status="FAIL"
    rc=1
  fi
fi

if [ "$run_py" -eq 1 ]; then
  echo "=== python3 -m pytest tests_py/ (fast tier) ==="
  if python3 -m pytest tests_py/; then
    py_status="PASS"
  else
    py_status="FAIL"
    rc=1
  fi
fi

echo
echo "=== check.sh verdict ==="
echo "cargo test --release : $rust_status"
echo "pytest tests_py/     : $py_status"
if [ "$rc" -ne 0 ]; then
  echo "RESULT: FAIL"
else
  echo "RESULT: PASS"
fi
exit "$rc"
