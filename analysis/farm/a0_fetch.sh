#!/usr/bin/env bash
# a0_fetch.sh -- pull an s62 A0 gate run home.  RUNS ON THE MAC.
#
#   bash analysis/farm/a0_fetch.sh <tag>          # -> out/s62/farm/<tag>/
#   bash analysis/farm/a0_fetch.sh <tag> --list   # inventory only, no transfer
#
# Tars on the PC first (many small files over Tailscale) and never touches
# anything outside the run dir.  The headline for THIS sweep is the VERDICT MIX
# PER LANE -- how many cells the engine decided at a real budget, split by
# refutation lane (eps=0) and randomized-restart lane (eps=0.15) -- plus total
# solver seconds.  A timeout is UNKNOWN, never a negative result: the whole
# point of the re-run is that the s56 "0/6" was 15 s of UNKNOWN misread as a
# field fact.
#
# A SAT on any control is a cover found from the chain alone -- a FINDABILITY
# event, NOT a new record.  A0 is known-SAT by construction, and the chain pins
# length = 5764 + (K+R), so the cover compiles to a word the SAME length as its
# source (5906, or 5907 on that control).  It is a 5905 candidate only if the
# compiled length actually comes out < 5906, which a0gate.py tests and banners
# separately.  An UNSAT would be a soundness CONTRADICTION, not a result.
# Every SAT is surfaced loudly with the gating ritual regardless, and the gate
# runs HERE -- the farm PC has no Rust toolchain, so confirm_sat cannot finish
# there.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
TAG="${1:-}"
MODE="${2:-}"
[ -n "$TAG" ] || { echo "usage: $0 <tag> [--list]" >&2; exit 1; }

RUN_WIN="F:\\superpermFarm\\untargeted\\runs\\${TAG}"
RUN_SCP="F:/superpermFarm/untargeted/runs/${TAG}"
DEST="${REPO}/out/s62/farm/${TAG}"

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

# ---- headline counters, straight from the shard stats ----------------------
# Column names belong to the instrument, so every field is resolved by trying a
# family of names rather than hard-coding one.  A silently-renamed column then
# degrades to "column not found" instead of to a wrong number.
python3 - "$DEST" <<'EOF'
import csv, glob, os, sys
from collections import Counter, defaultdict

d = sys.argv[1]
stats = sorted(glob.glob(os.path.join(d, "out", "*", "*_stats_*.tsv")))
if not stats:
    print("no *_stats_*.tsv found under out/*/ -- did the shards write anything?")
    raise SystemExit(0)

rows = []
for f in stats:
    rows += list(csv.DictReader(open(f), delimiter="\t"))
if not rows:
    print("stats TSVs present but empty"); raise SystemExit(0)
keys = list(rows[0].keys())


def pick(*names):
    for n in names:
        for k in keys:
            if k.strip().lower() == n:
                return k
    return None


K_VERDICT = pick("verdict", "result", "status")
K_LANE    = pick("lane")                       # as-built: refutation | witness
K_EPS     = pick("epsilon", "eps")
K_SECS    = pick("seconds", "secs", "solver_seconds", "sec", "time", "elapsed")
K_CTRL    = pick("control", "instance", "base", "word", "chain")
K_SEED    = pick("seed")


def lane_of(r):
    """Lane label. The two lanes ARE different questions: eps=0 is the
    deterministic refutation lane (its UNSAT is a theorem about the instance),
    eps=0.15 is the randomized witness-hunting lane (its UNSAT would only be a
    statement about one restart stream), so they must never be pooled."""
    parts = []
    if K_LANE:
        parts.append((r.get(K_LANE) or "?").strip())
    if K_EPS:
        parts.append("eps=" + (r.get(K_EPS) or "?").strip())
    return " ".join(parts) if parts else "all"

print(f"\nshards reporting: {len(stats)}   run rows: {len(rows)}   (grid is 18)")
if len(rows) != 18:
    print(f"  *** {len(rows)} rows, expected 18 (6 controls x 3 runs) -- "
          f"coverage is INCOMPLETE, do not summarise this as the A0 verdict ***")
print(f"columns: {', '.join(keys)}")

if not K_VERDICT:
    print("  *** no verdict column found -- cannot report the verdict mix ***")
else:
    lanes = defaultdict(Counter)
    for r in rows:
        lanes[lane_of(r)][(r[K_VERDICT] or "?").strip().upper()] += 1
    print("\nverdict mix per lane" +
          ("" if (K_LANE or K_EPS) else "  (no lane/epsilon column -- pooled)"))
    order = ["SAT", "UNSAT", "UNKNOWN"]
    for lane in sorted(lanes):
        c = lanes[lane]
        extra = sorted(set(c) - set(order))
        cells = "  ".join(f"{v}={c[v]}" for v in order) + \
                ("  " + "  ".join(f"{v}={c[v]}" for v in extra) if extra else "")
        print(f"  {lane:<22} n={sum(c.values()):<3} {cells}")
        if extra:
            print(f"    ^ non-three-valued verdicts present ({', '.join(extra)}) -- "
                  f"those are ERRORS or DRY-RUN rows, not results")
    tot = Counter()
    for c in lanes.values():
        tot += c
    print(f"  TOTAL     n={sum(tot.values()):<3} " +
          "  ".join(f"{v}={tot[v]}" for v in order))
    # An UNKNOWN is the honest non-result the whole re-run exists to price.
    if tot["UNKNOWN"]:
        print(f"\n  {tot['UNKNOWN']} cell(s) UNKNOWN at the budget -- a timeout is NOT a "
              f"negative result. Report as 'undecided at TL', never as 'no cover exists'.")

if K_SECS:
    tot_s = 0.0
    for r in rows:
        try:
            tot_s += float(r[K_SECS])
        except (TypeError, ValueError):
            pass
    print(f"\ntotal solver seconds: {tot_s:,.1f}  ({tot_s/3600:.2f} core-hours)"
          f"   mean/cell {tot_s/max(len(rows),1):,.1f} s")
else:
    print("\n(no seconds column found -- solver time not summarised)")

if K_VERDICT and K_CTRL:
    print("\nper-control:")
    per = defaultdict(Counter)
    for r in rows:
        per[(r.get(K_CTRL) or "?").strip()][(r[K_VERDICT] or "?").strip().upper()] += 1
    for ctrl in sorted(per):
        c = per[ctrl]
        print(f"  {ctrl:26} " + "  ".join(f"{v}={c[v]}" for v in ["SAT", "UNSAT", "UNKNOWN"]))

sats = [r for r in rows if K_VERDICT and (r[K_VERDICT] or "").strip().upper() == "SAT"]
if sats:
    print("\n" + "=" * 72)
    print(f"*** {len(sats)} SAT ROW(S) -- A COVER FROM THE CHAIN ALONE ***")
    lines = []
    for r in sats:
        bits = {k: r[k] for k in (K_CTRL, K_LANE, K_EPS, K_SEED, K_SECS) if k}
        lines.append("  ".join(f"{k}={v}" for k, v in bits.items()))
        print("   " + lines[-1])
    print("=" * 72)
    # Sentinel for the shell half, so the ritual banner does not depend on
    # grepping tabs out of an instrument-owned TSV format.
    with open(os.path.join(d, "SAT_FOUND.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
EOF

# ---- SAT artifacts + alarms -------------------------------------------------
# Anything that looks like a materialized witness gets the full ritual banner.
found_sat=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  found_sat=1
  echo ""
  echo "*** WITNESS ARTIFACT $f"
done < <(find "$DEST" \( -name 'word_*.txt' -o -name 'JACKPOT_*.json' -o -name '*SAT*.json' \) 2>/dev/null)

if [ "$found_sat" = 1 ] || [ -f "${DEST}/SAT_FOUND.txt" ]; then
  cat <<'RITUAL'

########################################################################
A0 SAT: a cover of a control chain found from the CHAIN ALONE, no atom
assumptions.  This is a FINDABILITY event, not a record: A0 is known-SAT
by construction and the chain pins length = 5764 + (K+R), so the cover
compiles to a word the SAME length as its source.  It is a 5905
candidate ONLY if the compiled length is actually < 5906 -- a0gate.py
tests that and banners it separately.
Believe NOTHING until all three gates pass, and run them HERE (the farm
PC has no Rust toolchain, so confirm_sat cannot finish there):

  1. python3 -c 'import sys; sys.path.insert(0,"out/s56/p1a"); \
       import p1a_assume as P; ...P.confirm_sat(ex, rows, outdir, tag)'
  2. cargo run --release -- validate -n 7 --file <abspath> --complete
  3. python3 analysis/counting/m3_check.py -n 7 <abspath>     (exit 2 = novel)
########################################################################
RITUAL
fi

[ -f "${DEST}/ALARM.txt" ] && { echo ""; echo "--- ALARM.txt ---"; cat "${DEST}/ALARM.txt"; }
exit 0
