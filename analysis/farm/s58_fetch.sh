#!/usr/bin/env bash
# s58_fetch.sh -- pull an s58 farm run home (pairwise cut store or extended
# census).  RUNS ON THE MAC.
#
#   bash analysis/farm/s58_fetch.sh <tag>          # -> out/s58/farm/<tag>/
#   bash analysis/farm/s58_fetch.sh <tag> --list   # inventory only, no transfer
#
# Tars on the PC first (many small files over Tailscale) and never touches
# anything outside the run dir.  Alarms and the two headline soundness
# counters are surfaced loudly on arrival:
#   * a JACKPOT_*.json on chain #0 would be a 5905 CANDIDATE -> M3 ritual
#   * violations > 0 or recheck_fail > 0 means the cut store is NOT sound
#     and must not be used
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
TAG="${1:-}"
MODE="${2:-}"
[ -n "$TAG" ] || { echo "usage: $0 <tag> [--list]" >&2; exit 1; }

RUN_WIN="F:\\superpermFarm\\untargeted\\runs\\${TAG}"
RUN_SCP="F:/superpermFarm/untargeted/runs/${TAG}"
DEST="${REPO}/out/s58/farm/${TAG}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

echo "== remote inventory =="
sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"\$r='${RUN_WIN}'; if (-not (Test-Path \$r)) { 'NO SUCH RUN: ' + \$r; exit 1 }; \$f=@(Get-ChildItem \$r -Recurse -File); '{0} files, {1:N1} MB' -f \$f.Count, ((\$f | Measure-Object Length -Sum).Sum/1MB); if (Test-Path \$r\STATUS.txt) { '--- STATUS ---'; Get-Content \$r\STATUS.txt }\""

[ "$MODE" = "--list" ] && exit 0

echo "== packing on the PC =="
sshq "cmd /c \"cd /d F:\\superpermFarm\\untargeted\\runs && tar -czf ${TAG}.tar.gz ${TAG} && echo PACK_OK\""

echo "== transferring =="
mkdir -p "$(dirname "$DEST")"
scp -q "${HOST}:${RUN_SCP}.tar.gz" "$(dirname "$DEST")/${TAG}.tar.gz"
sshq "cmd /c del ${RUN_WIN}.tar.gz" >/dev/null
tar -xzf "$(dirname "$DEST")/${TAG}.tar.gz" -C "$(dirname "$DEST")"
rm -f "$(dirname "$DEST")/${TAG}.tar.gz"

echo ""
echo "landed: ${DEST}"
du -sh "$DEST" 2>/dev/null || true

# ---- headline counters, summed straight from the shard stats ---------------
python3 - "$DEST" <<'EOF'
import csv, glob, json, os, sys
d = sys.argv[1]
stats = sorted(glob.glob(os.path.join(d, "out", "*", "*_stats_*.tsv")))
if not stats:
    print("no stats TSVs found"); raise SystemExit(0)
rows = []
for f in stats:
    rows += list(csv.DictReader(open(f), delimiter="\t"))
keys = rows[0].keys()
def total(k):
    return sum(int(r[k]) for r in rows if r.get(k, "").lstrip("-").isdigit())
print(f"\nshards reporting: {len(rows)}")
if "nogoods" in keys:
    print(f"  probed        {total('probed'):,}")
    print(f"  NO-GOODS      {total('nogoods'):,}")
    print(f"  unknown       {total('unknown'):,}")
    print(f"  structural    {total('structural'):,}")
    print(f"  errors        {total('errors')}   recheck_fail {total('recheck_fail')}"
          f"   violations {total('violations')}")
    if total("violations") or total("recheck_fail"):
        print("  *** STORE IS NOT SOUND -- do not use it ***")
if "nodes" in keys:
    print(f"  subtrees      {total('subtrees'):,}")
    print(f"  nodes         {total('nodes'):,}")
    print(f"  chains        {total('chains'):,}   pivbreak {total('pivbreak')}"
          f"   gen {total('gen')}")
    bad = [r for r in rows if r.get("status") != "EXHAUSTED"]
    if bad:
        print(f"  *** {len(bad)} SHARD(S) NOT EXHAUSTED -- coverage incomplete ***")
    else:
        print("  every shard EXHAUSTED -- coverage complete")
EOF

for f in $(find "$DEST" -name 'JACKPOT_*.json' 2>/dev/null); do
  echo ""
  echo "*** JACKPOT $f -- a cover of an OPEN chain. Gate it before believing anything:"
  echo "    p1a_assume.confirm_sat -> cargo run --release -- validate -n 7 --file <f> --complete"
  echo "    AND python3 analysis/counting/m3_check.py -n 7 <f>"
done
[ -f "${DEST}/ALARM.txt" ] && { echo ""; echo "--- ALARM.txt ---"; cat "${DEST}/ALARM.txt"; }
exit 0
