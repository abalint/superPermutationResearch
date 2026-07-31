#!/usr/bin/env bash
# promote_ship.sh -- ship the n=6 PROMOTION hunt payload to the farm PC.
# RUNS ON THE MAC.  Incremental on top of untargeted_ship.sh: the pyenv, the
# repo mirror, detach.exe and every shared analysis/counting module are already
# there, so this adds only what the promotion hunt needs on top.
#
# Ships:
#   -> F:\superpermFarm\untargeted\           promote_shim.py, promote_run.ps1,
#                                             untargeted_super.ps1 (s52b Target)
#   -> ...\untargeted\repo\analysis\counting\s51\demotion.py
#   -> ...\untargeted\repo\data\upstream872\  22,062 walks (86 MB) -- the big one
#
# COPYFILE_DISABLE=1 is MANDATORY (docs/OPERATIONS.md s29 lesson): macOS bsdtar
# otherwise ships an AppleDouble `._x` twin per file AND hides them from
# `tar -t`, and every one of those would be read as a corpus record.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
DEST_WIN='F:\superpermFarm\untargeted'
DEST_SCP='F:/superpermFarm/untargeted'
TAR="$(mktemp -d)/promote_payload.tar.gz"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

cd "$REPO"

# --- what goes in the repo-mirror tarball (paths are repo-relative) ----------
FILES=(
  "analysis/counting/s51/demotion.py"
  "data/upstream872"
)
for f in "${FILES[@]}"; do
  [ -e "$f" ] || { echo "FATAL: missing $f" >&2; exit 1; }
done

NWALK=$(find data/upstream872 -name '*.txt' | wc -l | tr -d ' ')
echo "== payload: demotion.py + ${NWALK} corpus walks =="
[ "$NWALK" -eq 22062 ] || echo "WARNING: expected 22062 walks, found ${NWALK}"

echo "== packing (COPYFILE_DISABLE=1) =="
COPYFILE_DISABLE=1 tar -czf "$TAR" "${FILES[@]}"
if gzip -dc "$TAR" | tar -tf - | grep -q '/\._'; then
  echo "FATAL: AppleDouble entries in the tarball -- COPYFILE_DISABLE not honoured" >&2
  exit 1
fi
echo "   $(du -h "$TAR" | cut -f1) packed, no AppleDouble entries"

echo "== shipping harness files =="
COPYFILE_DISABLE=1 scp -q \
  analysis/farm/promote_shim.py \
  analysis/farm/promote_run.ps1 \
  analysis/farm/untargeted_super.ps1 \
  "${HOST}:${DEST_SCP}/"

echo "== shipping repo payload =="
COPYFILE_DISABLE=1 scp -q "$TAR" "${HOST}:${DEST_SCP}/promote_payload.tar.gz"

echo "== unpacking on the PC =="
sshq "cmd /c \"cd /d ${DEST_WIN}\\repo && tar -xzf ..\\promote_payload.tar.gz && echo EXTRACT_OK\""

echo "== verifying =="
sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"
  \\\$r='${DEST_WIN}\\repo';
  'demotion.py   : ' + (Test-Path \\\$r\\analysis\\counting\\s51\\demotion.py);
  'corpus walks  : ' + @(Get-ChildItem \\\$r\\data\\upstream872 -Filter *.txt -File -EA SilentlyContinue).Count;
  'AppleDouble   : ' + @(Get-ChildItem \\\$r\\data\\upstream872 -Filter '._*' -File -EA SilentlyContinue).Count;
  'promote_shim  : ' + (Test-Path '${DEST_WIN}\\promote_shim.py');
  'promote_run   : ' + (Test-Path '${DEST_WIN}\\promote_run.ps1');
  'canon index   : ' + (Test-Path \\\$r\\analysis\\counting\\upstream872_canon_index.tsv)
\""

rm -f "$TAR"
cat <<EOF

shipped.
  dry-run: ssh ${HOST} "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\promote_run.ps1 -Tag pdry -DryRun"
  smoke  : ssh ${HOST} "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\promote_run.ps1 -Tag psmoke -Limit 4"
  launch : ssh ${HOST} "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\promote_run.ps1 -Tag p1"
  status : ssh ${HOST} "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\untargeted_status.ps1"
  fetch  : bash analysis/farm/untargeted_fetch.sh <tag>
EOF
