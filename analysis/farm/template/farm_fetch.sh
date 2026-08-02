#!/usr/bin/env bash
# farm_fetch.sh -- THE fetch script: pull a run home AND adjudicate it (s64 P5).
# RUNS ON THE MAC.  One, parameterized by the same config the ship used.
#
#   bash analysis/farm/template/farm_fetch.sh <config> <tag>          # fetch+adjudicate
#   bash analysis/farm/template/farm_fetch.sh <config> <tag> --list   # inventory only
#
# THE PRODUCT OF MOST OF OUR SWEEPS IS A NEGATIVE, so the fetch's real job is
# to REFUSE to call it one unless the run earned it.  A negative is valid only
# if every shard exited rc 0, every shard's STATUS ends in a DONE row, no shard
# printed a PARTIAL banner, the per-shard unit counts SUM to the declared total
# (the shard partition is exact, so a short sum means a shard died mid-tree),
# and there is no ALARM.txt.  Anything missing -> INCONCLUSIVE, exit nonzero.
#
# THE bash 3.2 TRAP, 4th recurrence, kept fixed here ONCE.  macOS ships bash
# 3.2: `mapfile`/`readarray` DO NOT EXIST, and the shell's error goes to stderr
# while the array is left EMPTY.  In s63's mc28_fetch that meant a run which
# DID produce a first-of-species walk would have been reported as "no
# products".  Every list below is built with a portable `find | sort` into a
# newline-separated string and consumed with `while IFS= read -r`.
#
# ALSO KEPT: `set -e` must not abort the adjudication -- a nonzero exit from
# the verdict block is a VERDICT, not a crash, so it is captured into $RC.
set -euo pipefail

TPL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${TPL}/../../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"

CFG_NAME="${1:-}"
TAG="${2:-}"
MODE="${3:-}"
[ -n "$CFG_NAME" ] && [ -n "$TAG" ] || {
  echo "usage: $0 <config> <tag> [--list]" >&2; exit 64; }

CONF="$CFG_NAME"
[ -f "$CONF" ] || CONF="${TPL}/configs/${CFG_NAME}.conf"
[ -f "$CONF" ] || { echo "no such config: $CFG_NAME" >&2; exit 64; }

TAG_CFG=""; WHAT=""; ADAPTER=""; INSTRUMENT=""
FILES=(); EXTRA=(); PROVENANCE=(); SIDEFILES=(); SCRIPTS_EXTRA=()
SHARDS=24; WORKERS=24; STALL_MINUTES=10; MB_PER_SHARD=400; TOTAL=0
EXTRA_ARGS=""; DRYRUN_ARGS=""; MODE_TOKEN=""
FETCH_DEST="out/farm"; PRODUCT_GLOB=""; STATS_GLOB="stats_s*.tsv"
REQUIRE_IDLE=1; SELF_TEST=1; ENV_ARGS=""
GATE_TEXT=""; LAUNCH_NOTES=""; SCOPE_NOTE=""; ALARM_NOTES=""
PARTIAL_MARKERS=""; GATE_CMDS=(); PRODUCT_NOTE=""
# shellcheck source=/dev/null
. "$CONF"

RUN_WIN="F:\\superpermFarm\\untargeted\\runs\\${TAG}"
RUN_SCP="F:/superpermFarm/untargeted/runs/${TAG}"
DEST="${REPO}/${FETCH_DEST}/${TAG}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

echo "== remote inventory =="
sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"\$r='${RUN_WIN}'; if (-not (Test-Path \$r)) { 'NO SUCH RUN: ' + \$r; exit 1 }; \$f=@(Get-ChildItem \$r -Recurse -File); '{0} files, {1:N1} MB' -f \$f.Count, ((\$f | Measure-Object Length -Sum).Sum/1MB); if (Test-Path \$r\\STATUS.txt) { '--- STATUS ---'; Get-Content \$r\\STATUS.txt }\""

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

# ------------------------------------------------------------------ verdict --
echo ""
echo "== adjudication =="
BAD=0

if [ -f "${DEST}/ALARM.txt" ]; then
  echo "*** ALARM.txt PRESENT -- read it before trusting anything ***"
  sed -n '1,60p' "${DEST}/ALARM.txt"
  BAD=1
fi

RC=0
STATS_GLOB="$STATS_GLOB" PARTIAL_MARKERS="$PARTIAL_MARKERS" \
python3 - "$DEST" <<'PY' || RC=$?
"""Generic shard adjudicator.

Reads the CANONICAL stats schema written by pylib/farmstatus.py
(shard, shards, units_done, units_declared, finds, secs, rc), so this block
is instrument-independent: adding an instrument adds a config, not another
copy of this logic.
"""
import glob
import os
import sys

dest = sys.argv[1]
stats_glob = os.environ.get("STATS_GLOB") or "stats_s*.tsv"
markers = [m for m in os.environ.get("PARTIAL_MARKERS", "").split("|") if m]

outs = sorted(glob.glob(os.path.join(dest, "out", "s*")))
logs = sorted(glob.glob(os.path.join(dest, "logs", "w*.log")))
tot_units = declared = tot_secs = tot_finds = 0
rows, bad = [], []
for d in outs:
    nn = os.path.basename(d)
    stats = sorted(glob.glob(os.path.join(d, stats_glob)))
    status = os.path.join(d, "STATUS")
    rec = {}
    if stats:
        with open(stats[0]) as fh:
            hdr = fh.readline().rstrip("\n").split("\t")
            val = fh.readline().rstrip("\n").split("\t")
        rec = dict(zip(hdr, val))
    else:
        bad.append(f"{nn}: no stats TSV (shard never finished)")
    done = os.path.isfile(status) and "\tDONE\t" in open(status).read()
    if not done:
        bad.append(f"{nn}: STATUS has no DONE row")
    rc = rec.get("rc")
    if rc not in (None, "0"):
        bad.append(f"{nn}: rc={rc}")
    tot_units += int(rec.get("units_done") or 0)
    declared += int(rec.get("units_declared") or 0)
    tot_secs += float(rec.get("secs") or 0)
    tot_finds += int(rec.get("finds") or 0)
    rows.append((nn, rc, rec.get("units_done"), rec.get("secs"),
                 rec.get("finds")))

for lg in logs:
    try:
        t = open(lg, errors="replace").read()
    except OSError:
        continue
    for m in markers:
        if m in t:
            bad.append(f"{os.path.basename(lg)}: {m!r} -- the run did not "
                       f"earn a negative")

print(f"shards: {len(outs)}   units processed: {tot_units:,}   "
      f"declared: {declared:,}   finds: {tot_finds}   "
      f"cpu: {tot_secs/3600:.2f} core-h")
for nn, rc, units, secs, finds in rows:
    print(f"  {nn}  rc={rc}  units={units}  secs={secs}  finds={finds}")

# The partition closure test: the shard slices are EXACT, so a short sum means
# a shard died mid-tree even though it exited 0.  Skipped when nothing declared
# a total (an instrument that cannot know its size up front).
if declared and tot_units != declared:
    bad.append(f"unit sum {tot_units:,} != declared {declared:,} -- the "
               f"shard partition did not close")
elif declared:
    print("partition CLOSED: sum of shard units == declared total")

if bad:
    print("\n*** INCONCLUSIVE ***")
    for b in bad:
        print("   " + b)
    sys.exit(1)
print("\nall shards complete, uncapped, partition closed")
PY
if [ $RC -ne 0 ]; then BAD=1; fi

# ------------------------------------------------------------- the products --
if [ -n "$PRODUCT_GLOB" ]; then
  # NO `mapfile` (bash 3.2) -- see the header.  Portable list + read loop.
  FINDLIST="$(find "$DEST" -name "$PRODUCT_GLOB" -type f 2>/dev/null | sort)"
  NFIND=0
  if [ -n "$FINDLIST" ]; then NFIND=$(printf '%s\n' "$FINDLIST" | wc -l | tr -d ' '); fi
  if [ "$NFIND" -gt 0 ]; then
    echo ""
    echo "*** ${NFIND} PRODUCT(S). Gating every one. ***"
    cd "$REPO"
    printf '%s\n' "$FINDLIST" | while IFS= read -r f; do
      echo "--- $f"
      for cmd in ${GATE_CMDS[@]+"${GATE_CMDS[@]}"}; do
        gc="${cmd//<f>/$f}"
        gr=0
        # a nonzero exit is a VERDICT here (m3_check 2 = NOVEL), not a crash
        eval "$gc" || gr=$?
        echo "   rc=$gr  <- $gc"
      done
    done
    echo ""
    [ -n "$PRODUCT_NOTE" ] && echo "$PRODUCT_NOTE"
    exit 2
  fi
fi

echo ""
if [ $BAD -eq 0 ]; then
  echo "VERDICT: no products, and the run EARNED that negative (all shards"
  echo "complete, uncapped, partition closed, no alarms)."
  [ -n "$SCOPE_NOTE" ] && { echo ""; echo "$SCOPE_NOTE"; }
else
  echo "VERDICT: INCONCLUSIVE -- see above.  Do not record a negative."
  exit 1
fi
