#!/usr/bin/env bash
# untargeted_fetch.sh -- pull the 24 shard out dirs of a fused-pair UNTARGETED
# run home from the farm PC.  RUNS ON THE MAC.
#
#   bash analysis/farm/untargeted_fetch.sh <tag>          # -> out/s52/untargeted_farm/<tag>/
#   bash analysis/farm/untargeted_fetch.sh <tag> --list   # what is there, no transfer
#
# Tars on the PC first (many small TSVs over Tailscale) and never touches
# anything outside the run dir.  Products (.txt candidate classes) are listed
# loudly on arrival -- NOTHING is believed until it passes both gates:
#   cargo run --release -- validate -n 7 --file <f> --complete
#   python3 analysis/counting/m3_check.py -n 7 <f>        (exit 2 = novel)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
TAG="${1:-}"
MODE="${2:-}"
[ -n "$TAG" ] || { echo "usage: $0 <tag> [--list]" >&2; exit 1; }

RUN_WIN="F:\\superpermFarm\\untargeted\\runs\\${TAG}"
RUN_SCP="F:/superpermFarm/untargeted/runs/${TAG}"
DEST="${REPO}/out/s52/untargeted_farm/${TAG}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

echo "== remote inventory =="
sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"\$r='${RUN_WIN}'; if (-not (Test-Path \$r)) { 'NO SUCH RUN: ' + \$r; exit 1 }; \$f=@(Get-ChildItem \$r -Recurse -File); '{0} files, {1:N1} MB' -f \$f.Count, ((\$f | Measure-Object Length -Sum).Sum/1MB); 'shard out dirs: ' + @(Get-ChildItem \$r\out -Directory -EA SilentlyContinue).Count; 'product .txt : ' + @(Get-ChildItem \$r\out -Recurse -Filter *.txt -EA SilentlyContinue).Count; if (Test-Path \$r\STATUS.txt) { '--- STATUS ---'; Get-Content \$r\STATUS.txt }\""

[ "$MODE" = "--list" ] && exit 0

echo "== packing on the PC =="
sshq "cmd /c \"cd /d F:\\superpermFarm\\untargeted\\runs && tar -czf ${TAG}.tar.gz ${TAG} && echo PACK_OK\""

echo "== transferring =="
mkdir -p "$DEST"
scp -q "${HOST}:${RUN_SCP}.tar.gz" "${DEST}/../${TAG}.tar.gz"
sshq "cmd /c del ${RUN_WIN}.tar.gz" >/dev/null

echo "== unpacking =="
tar -xzf "${DEST}/../${TAG}.tar.gz" -C "${DEST}/.." --strip-components=0
rm -f "${DEST}/../${TAG}.tar.gz"

echo ""
echo "landed: ${DEST}"
du -sh "$DEST" 2>/dev/null || true
echo ""
echo "shard out dirs: $(find "${DEST}/out" -maxdepth 1 -type d -name 's*' 2>/dev/null | wc -l | tr -d ' ')"
echo "stats/edges TSVs: $(find "${DEST}/out" -name '*.tsv' 2>/dev/null | wc -l | tr -d ' ')"

PRODUCTS=$(find "${DEST}/out" -name '*.txt' 2>/dev/null | wc -l | tr -d ' ')
echo "product .txt files: $PRODUCTS"
if [ "$PRODUCTS" -gt 0 ]; then
  cat <<EOF

*** $PRODUCTS PRODUCT FILE(S) -- ESCAPE CANDIDATES. Gate every one before believing anything: ***
  for f in ${DEST}/out/*/*.txt; do
    cargo run --release -- validate -n 7 --file "\$f" --complete
    python3 analysis/counting/m3_check.py -n 7 "\$f"     # exit 2 = novel vs the 220-class shell
  done
EOF
fi
[ -f "${DEST}/STATUS.txt" ] && { echo ""; echo "--- STATUS.txt ---"; cat "${DEST}/STATUS.txt"; }
[ -f "${DEST}/ALARM.txt" ]  && { echo ""; echo "--- ALARM.txt ---";  cat "${DEST}/ALARM.txt"; }
exit 0
