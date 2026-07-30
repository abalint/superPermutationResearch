#!/bin/sh
# ta_fetch.sh -- pull a farm tail-atsp run's finds back to the Mac and gate them.
#
# Improvements (871 candidates) and, with --ties, new-allocation tie walks land
# in F:\superpermFarm\tailatsp\runs\<tag>\finds\wNN\. This copies them into
# data/farm_finds/<tag>/ and runs BOTH gates on every file, because a farm
# banner is not evidence: the Rust validator must say complete, and
# m3_check.py must exit 2 (novel vs all 22,062 known classes) before anything
# is called a result.
#
# usage: analysis/farm/ta_fetch.sh <tag>          (from the repo root)
set -u
TAG="${1:?usage: ta_fetch.sh <tag>}"
DEST="data/farm_finds/$TAG"
REMOTE="F:/superpermFarm/tailatsp/runs/$TAG/finds"

mkdir -p "$DEST"
scp -q -r "transcribe:/$REMOTE/*" "$DEST/" 2>/dev/null
files=$(find "$DEST" -type f -name '*.txt' | sort)
if [ -z "$files" ]; then
  echo "no find files for run $TAG (expected if the sweep found nothing — that IS the result)"
  exit 0
fi

echo "fetched $(echo "$files" | wc -l | tr -d ' ') file(s) into $DEST"
# The validator lives in the release binary; build it from a CLEAN tree only —
# a candidate validated by a half-edited working copy proves nothing.
if [ -n "$(git status --porcelain -- src/ 2>/dev/null)" ]; then
  echo "WARNING: src/ is dirty — validate with a binary built from committed source, not this tree."
fi

rc_all=0
for f in $files; do
  echo "=== $f ==="
  cargo run --release --quiet -- validate -n 6 --file "$f" --complete || rc_all=1
  python3 analysis/counting/m3_check.py "$f"
  m3=$?
  case "$m3" in
    2) echo "  M3: *** NOVEL *** (exit 2) — this is the real thing; notify Andrew before anything else" ;;
    0) echo "  M3: equivalent to a known class (exit 0) — a rediscovery, not a result" ;;
    *) echo "  M3: gate returned $m3 — investigate before believing anything" ; rc_all=1 ;;
  esac
done
exit $rc_all
