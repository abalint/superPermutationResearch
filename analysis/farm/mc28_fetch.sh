#!/usr/bin/env bash
# mc28_fetch.sh -- pull an s63 mc28 forest-branch run home AND adjudicate it.
# RUNS ON THE MAC.
#
#   bash analysis/farm/mc28_fetch.sh <tag>          # -> out/s63/mcover/farm/<tag>/
#   bash analysis/farm/mc28_fetch.sh <tag> --list   # inventory only, no transfer
#
# Tars on the PC first (many small files over Tailscale) and never touches
# anything outside the run dir.
#
# THE PRODUCT OF THIS SWEEP IS A NEGATIVE, so the fetch's real job is to refuse
# to call it one unless it earned it.  A negative is valid ONLY if:
#   * every shard exited rc 0,
#   * every shard's STATUS ends in a DONE row,
#   * NO shard printed "*** PARTIAL" (a capped shard's "NO walk" is not a
#     negative -- the engine says so itself and exits 3),
#   * the shard cover counts SUM to the enumeration's own total (the stride
#     partition is exact, so a short sum means a shard died mid-tree), and
#   * no ALARM.txt.
# Anything missing and this script prints INCONCLUSIVE and exits nonzero.
#
# ANY FIND IS A FIRST-OF-SPECIES EVENT -- a materialized j >= 1 n=6 walk of
# length <= 872, which has never existed.  The PC cannot gate it (no Rust
# toolchain), so the gate runs HERE, all three, in order:
#   cargo run --release -- validate -n 6 --file <f> --complete
#   python3 analysis/counting/m3_check.py <f>        (exit 2 = novel)
#   python3 pylib/verify_master.py 6 <f>             (exit 1 = THEORY ALARM)
# This script runs all three automatically on every product it finds and
# refuses to summarise anything until it has.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
TAG="${1:-}"
MODE="${2:-}"
[ -n "$TAG" ] || { echo "usage: $0 <tag> [--list]" >&2; exit 1; }

RUN_WIN="F:\\superpermFarm\\untargeted\\runs\\${TAG}"
RUN_SCP="F:/superpermFarm/untargeted/runs/${TAG}"
DEST="${REPO}/out/s63/mcover/farm/${TAG}"

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

# every shard: rc, DONE row, covers, PARTIAL banner.
# `set -e` must not abort here -- a nonzero exit is a VERDICT, not a crash.
RC=0
python3 - "$DEST" <<'PY' || RC=$?
import os, sys, glob, re
dest = sys.argv[1]
outs = sorted(glob.glob(os.path.join(dest, "out", "s*")))
logs = sorted(glob.glob(os.path.join(dest, "logs", "w*.log")))
tot_cov = tot_secs = 0
rows, bad = [], []
for d in outs:
    nn = os.path.basename(d)
    stats = glob.glob(os.path.join(d, "mc28_stats_*.tsv"))
    status = os.path.join(d, "STATUS")
    rc = cov = secs = finds = None
    if stats:
        with open(stats[0]) as fh:
            hdr = fh.readline().rstrip("\n").split("\t")
            val = fh.readline().rstrip("\n").split("\t")
        rec = dict(zip(hdr, val))
        rc = rec.get("rc"); cov = rec.get("covers_done")
        secs = rec.get("secs"); finds = rec.get("finds")
    else:
        bad.append(f"{nn}: no stats TSV (shard never finished)")
    done = os.path.isfile(status) and "\tDONE\t" in open(status).read()
    if not done:
        bad.append(f"{nn}: STATUS has no DONE row")
    if rc not in (None, "0"):
        bad.append(f"{nn}: rc={rc}")
    if cov:
        tot_cov += int(cov)
    if secs:
        tot_secs += float(secs)
    rows.append((nn, rc, cov, secs, finds))
# the engine's own PARTIAL banner in any shard log kills the negative
part = []
for lg in logs:
    try:
        t = open(lg, errors="replace").read()
    except OSError:
        continue
    if "PARTIAL (cap hit)" in t:
        part.append(os.path.basename(lg))
    if "NOT SUPPLY-TIGHT" in t:
        bad.append(f"{os.path.basename(lg)}: NOT SUPPLY-TIGHT (misconfigured launch)")
print(f"shards: {len(outs)}   covers processed: {tot_cov:,}   "
      f"cpu: {tot_secs/3600:.2f} core-h")
for nn, rc, cov, secs, finds in rows:
    print(f"  {nn}  rc={rc}  covers={cov}  secs={secs}  finds={finds}")
if part:
    bad.append(f"PARTIAL (capped) shards: {' '.join(part)} -- 'NO walk' from a "
               f"capped shard is NOT a negative")
# The COVER FILE's declared total, echoed by every shard, must agree across
# shards AND equal the sum of per-shard cover counts.  Every shard also prints
# the body sha256 it verified -- all shards must have read the SAME file.
tots, shas, ver = set(), set(), set()
for lg in logs:
    t = open(lg, errors="replace").read()
    for m in re.finditer(r"lines=(\d+) declared_total=(\d+)", t):
        tots.add(int(m.group(2)))
    for m in re.finditer(r"sha256 body=([0-9a-f]{64})", t):
        shas.add(m.group(1))
    for m in re.finditer(r"VERIFIED=(\w+)", t):
        ver.add(m.group(1))
    for m in re.finditer(r"multi-covers containing lam\(id\): total=(\d+)", t):
        tots.add(int(m.group(1)))
if ver and ver != {"True"}:
    bad.append(f"a shard did NOT verify the covers file: VERIFIED={sorted(ver)}")
if len(shas) > 1:
    bad.append(f"shards read DIFFERENT cover files: {sorted(shas)}")
elif shas:
    print(f"covers-file body sha256 (all shards agree): {shas.copy().pop()}")
if len(tots) == 1:
    T = tots.pop()
    print(f"covers-file total (agreed by all shards): {T:,}")
    if T != tot_cov:
        bad.append(f"cover sum {tot_cov:,} != covers-file total {T:,} -- "
                   f"the stride partition did not close")
    else:
        print("stride partition CLOSED: sum of shard covers == file total")
elif tots:
    bad.append(f"shards disagree on the covers-file total: {sorted(tots)}")
else:
    bad.append("no shard reported a covers-file total")
if bad:
    print("\n*** INCONCLUSIVE ***")
    for b in bad:
        print("   " + b)
    sys.exit(1)
print("\nall shards complete, uncapped, partition closed")
PY
if [ $RC -ne 0 ]; then BAD=1; fi

# ------------------------------------------------------------- the products --
# NO `mapfile` here: macOS ships bash 3.2, where `mapfile` does not exist and
# would leave the array EMPTY -- i.e. a run that DID find a first-of-species
# walk would be reported as "no products".  Portable read loop instead.
FINDLIST="$(find "$DEST" -name 'mc28-s*-j*.txt' -type f 2>/dev/null | sort)"
NFIND=0
if [ -n "$FINDLIST" ]; then NFIND=$(printf '%s\n' "$FINDLIST" | wc -l | tr -d ' '); fi
if [ "$NFIND" -gt 0 ]; then
  echo ""
  echo "*** ${NFIND} PRODUCT(S) -- FIRST-OF-SPECIES CANDIDATES. Gating all three. ***"
  cd "$REPO"
  printf '%s\n' "$FINDLIST" | while IFS= read -r f; do
    echo "--- $f"
    vr=0; cargo run --release -q -- validate -n 6 --file "$f" --complete || vr=$?
    echo "   validate rc=$vr"
    m3=0; python3 analysis/counting/m3_check.py "$f" || m3=$?
    echo "   m3_check rc=$m3 (2 = NOVEL)"
    vm=0; python3 pylib/verify_master.py 6 "$f" || vm=$?
    echo "   verify_master rc=$vm"
    if [ $vm -eq 1 ]; then
      echo "   *** THEORY ALARM: verify_master exit 1 -- STOP EVERYTHING ***"
    fi
  done
  echo ""
  echo "A gated product here is a materialized j >= 1 n=6 walk of length <= 872"
  echo "in the (140,8,0,0,0) cell.  Nothing like it exists.  Stop and report."
  exit 2
fi

echo ""
if [ $BAD -eq 0 ]; then
  cat <<EOF
VERDICT: NO WALK, and the run earned the negative (all shards complete,
uncapped, partition closed, no alarms).

  => the (140,8,0,0,0) cell -- splits=20, D=8, v=28, supply-tight, the ONLY
     j>=1 872 cell in a known allocation -- contains NO pure complete
     first-visit walk of length <= 872 with j >= 1.

Scope, state it with the claim: PURE walks (no intra-cycle edge of weight >= 2),
supply-TIGHT only (S = 5v), and sound GIVEN the phi-cycle law of
out/s63/mcover/REPORT.md §6 (K = v-splits iff the loop-cycle incidence graph is
a forest), which is what licenses --forest.  Supply-SLACK cells are untouched.
EOF
else
  echo "VERDICT: INCONCLUSIVE -- see above.  Do not record a negative."
  exit 1
fi
