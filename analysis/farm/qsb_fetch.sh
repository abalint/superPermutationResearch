#!/usr/bin/env bash
# qsb_fetch.sh -- pull an s62 QS-B verdict-mix run home.  RUNS ON THE MAC.
#
#   bash analysis/farm/qsb_fetch.sh <tag>          # -> out/s62/farm/<tag>/
#   bash analysis/farm/qsb_fetch.sh <tag> --list   # inventory only, no transfer
#
# Tars on the PC first (many small files over Tailscale) and never touches
# anything outside the run dir.
#
# THE HEADLINE FOR THIS SWEEP IS THE CURVE, not a scalar: per (chain,
# multiplier) cell, what fraction of uniformly-drawn atom pools of size
# k = round(m x R) the realizer DECIDED inside the time limit, and what
# fraction of those decisions were UNSAT.  The sweep is sharded by UNIT, so a
# cell's 200 samples are spread over every shard and NO single shard's rollup
# is the cell -- the aggregation below, over the per-unit rows of all shards,
# is the authoritative one.  It refuses to present a cell as complete unless
# all 200 of its rows are present.
#
# READING RULES, enforced in the output text because they have been misread
# before:
#   * UNSAT = a theorem about THAT DRAW (no cover uses only those k loops).
#     It is a positive datum and it is most of the product.  It says NOTHING
#     about the chain being closed -- chains #0/#24 are open precisely because
#     a cover may use loops outside the draw.
#   * UNKNOWN = timeout = nothing learned.  Never a negative result.
#   * SAT = a cover of an OPEN n=7 chain.  Both chains have K + R = 141 and
#     length = 5764 + #2-loops (s34), so it compiles to a 5905: a WORLD-RECORD
#     CANDIDATE.  The gate runs HERE -- the farm PC has no Rust toolchain, so
#     confirm_sat cannot finish there.
#   * the `full` cell's 200 draws are ONE atom set (k = |pool| makes
#     rng.sample return the whole pool every time), so its 200 rows carry one
#     solved row per shard and 200-24 reused verdicts.  That is flagged, not
#     hidden: `solved` counts real solver calls, `samples` counts draws.
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

# ---- the curve, aggregated over every shard's per-unit rows ----------------
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


K_V     = pick("verdict", "result", "status")
K_CHAIN = pick("chain")
K_MULT  = pick("mult", "multiplier")
K_MX    = pick("mult_x", "mult_r")
K_K     = pick("k", "atoms")
K_SECS  = pick("seconds", "secs", "solver_seconds", "sec", "time", "elapsed")
K_SOLV  = pick("solved")
K_SAMP  = pick("sample")
K_UNIT  = pick("unit", "idx")
K_N     = pick("nsamp", "samples", "n")

print(f"\nshards reporting: {len(stats)}   unit rows: {len(rows)}")
print(f"columns: {', '.join(keys)}")

if K_UNIT:
    u = [r[K_UNIT] for r in rows]
    dup = len(u) - len(set(u))
    if dup:
        print(f"  *** {dup} DUPLICATE unit ids -- shards overlapped, do not "
              f"aggregate this run without finding out why ***")

if not (K_V and K_CHAIN and K_MULT):
    print("  *** verdict/chain/mult columns not all found -- cannot build the "
          f"curve (verdict={K_V} chain={K_CHAIN} mult={K_MULT}) ***")
    raise SystemExit(0)

cell = defaultdict(lambda: dict(v=Counter(), secs=[], solved=0, mx="", k="",
                                want=0))
for r in rows:
    c = cell[(r[K_CHAIN].strip(), r[K_MULT].strip())]
    c["v"][(r[K_V] or "?").strip().upper()] += 1
    if K_MX:
        c["mx"] = r[K_MX]
    if K_K:
        c["k"] = r[K_K]
    if K_N:
        try:
            c["want"] = int(r[K_N])
        except (TypeError, ValueError):
            pass
    if K_SECS:
        try:
            c["secs"].append(float(r[K_SECS]))
        except (TypeError, ValueError):
            pass
    if K_SOLV:
        try:
            c["solved"] += int(r[K_SOLV] or 0)
        except ValueError:
            pass


def fmt(x, n=4):
    return f"{x:.{n}f}"


print("\n=== QS-B decision curve (refutation lane, epsilon = 0) ===")
print("A cell is 'decided' when the engine returned SAT or UNSAT inside the "
      "budget.\nUNKNOWN is a timeout: nothing learned, NOT a negative result.")
hdr = (f"{'chain':>5} {'mult':>6} {'xR':>7} {'k':>5} {'n':>5} {'solved':>6} "
       f"{'SAT':>4} {'UNSAT':>6} {'UNKN':>5} {'decided':>8} {'unsat_f':>8} "
       f"{'mean_s':>9} {'med_s':>8} {'dec/s':>8}")
print("\n" + hdr)
print("-" * len(hdr))
incomplete = []
for (ch, mult) in sorted(cell, key=lambda t: (int(t[0]), float(cell[t]["mx"] or 0))):
    c = cell[(ch, mult)]
    n = sum(c["v"].values())
    want = c["want"] or 200          # the instrument's own declared N
    if n != want:
        incomplete.append((ch, mult, n, want))
    dec = c["v"]["SAT"] + c["v"]["UNSAT"]
    ts = c["secs"] or [0.0]
    mean = sum(ts) / len(ts)
    srt = sorted(ts)
    med = srt[len(srt) // 2]
    print(f"{ch:>5} {mult:>6} {c['mx']:>7} {c['k']:>5} {n:>5} {c['solved']:>6} "
          f"{c['v']['SAT']:>4} {c['v']['UNSAT']:>6} {c['v']['UNKNOWN']:>5} "
          f"{fmt(dec / n) if n else '-':>8} "
          f"{fmt(c['v']['UNSAT'] / n) if n else '-':>8} "
          f"{fmt(mean):>9} {fmt(med):>8} "
          f"{(fmt(1.0 / mean, 2) if mean > 0 else '-'):>8}")
    extra = set(c["v"]) - {"SAT", "UNSAT", "UNKNOWN"}
    if extra:
        print(f"        ^ non-three-valued verdicts present "
              f"({', '.join(sorted(extra))}) -- ERRORs or DRY-RUN rows, "
              f"not results")

if incomplete:
    print(f"\n  *** {len(incomplete)} INCOMPLETE CELL(S) -- do not quote these "
          f"as the curve.  (Expected for a --probe pricing run, where every "
          f"cell is short by design; NOT expected for the full sweep, where it "
          f"means shards died or were aborted.)")
    for ch, mult, n, want in incomplete:
        print(f"      chain #{ch} mult {mult}: {n}/{want} rows")

tot = Counter()
for c in cell.values():
    tot += c["v"]
print(f"\nTOTAL  n={sum(tot.values())}  SAT={tot['SAT']}  UNSAT={tot['UNSAT']}  "
      f"UNKNOWN={tot['UNKNOWN']}")
if K_SECS:
    # Per-row seconds; a reused row carries the memoised time of the draw it
    # duplicates, so this is the sample-weighted cost, not the machine cost.
    tot_s = sum(sum(c["secs"]) for c in cell.values())
    print(f"sample-weighted seconds: {tot_s:,.1f}  ({tot_s / 3600:.2f} "
          f"core-hours if every draw had been solved separately)")
if K_SOLV:
    ns = sum(c["solved"] for c in cell.values())
    nd = sum(tot.values())
    msg = f"actual solver calls: {ns} of {nd} draws"
    if nd - ns:
        msg += (f"  ({nd - ns} reused: identical atom sets, which at "
                f"epsilon = 0 give identical runs -- almost all of them are "
                f"the `full` cell, whose draws are all the whole pool)")
    print(msg)
if tot["UNKNOWN"]:
    print(f"\n{tot['UNKNOWN']} draw(s) UNDECIDED at the budget. Report as "
          f"'undecided at TL', never as 'no cover exists'.")

sats = [r for r in rows if (r[K_V] or "").strip().upper() == "SAT"]
if sats:
    print("\n" + "=" * 72)
    print(f"*** {len(sats)} SAT ROW(S) -- A COVER OF AN OPEN n=7 CHAIN ***")
    lines = []
    for r in sats:
        bits = {k: r[k] for k in (K_CHAIN, K_MULT, K_K, K_SAMP, K_SECS) if k}
        lines.append("  ".join(f"{k}={v}" for k, v in bits.items()))
        print("   " + lines[-1])
    print("=" * 72)
    # Sentinel for the shell half, so the ritual banner does not depend on
    # grepping tabs out of an instrument-owned TSV format.
    with open(os.path.join(d, "SAT_FOUND.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
EOF

# ---- SAT artifacts + alarms -------------------------------------------------
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
QS-B SAT: a cover of an OPEN n=7 chain (#0 or #24) was found.  Both
chains have K + R = 141 and length = 5764 + #2-loops (s34 law), so this
compiles to a 5905 -- a WORLD RECORD CANDIDATE.  Believe NOTHING until
all three gates pass, and run them HERE (the farm PC has no Rust
toolchain, so p1a_assume.confirm_sat cannot finish there; the shard's
JACKPOT_*.json carries the atom set and both row-id lists):

  1. p1a_assume.confirm_sat(ex, rows, outdir, tag)   -- check_cover + compile
  2. cargo run --release -- validate -n 7 --file <abspath> --complete
  3. python3 analysis/counting/m3_check.py -n 7 <abspath>     (exit 2 = novel)
########################################################################
RITUAL
fi

[ -f "${DEST}/ALARM.txt" ] && { echo ""; echo "--- ALARM.txt ---"; cat "${DEST}/ALARM.txt"; }
exit 0
