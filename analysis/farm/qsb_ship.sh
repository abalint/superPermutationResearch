#!/usr/bin/env bash
# qsb_ship.sh -- ship the s62 QS-B verdict-mix sweep to the Windows farm PC.
# RUNS ON THE MAC.  Ships and verifies only -- it never launches anything.
#
# WHAT THIS SWEEP IS.  docs/SWEEP-QUEUE.md "## QS-B full realizer verdict-mix
# map, chains #0/#24 (s59 item 4 follow-on)".  For each of Houston's two still-
# open n=7 chains it models "a proposer of precision m" as a uniform draw of
# k = round(m x R) 2-loops from the chain's pool, and measures what fraction of
# such draws the realizer (dlx7g, REFUTATION LANE, epsilon = 0) can DECIDE
# inside 30 s.  Grid: 2 chains x 9 multipliers (3.00 .. 4.75 in 0.25 steps,
# plus `full`) x 200 samples = 3,600 solver calls.  The product is the
# decision-rate / UNSAT-fraction curve NOVELTY-DESIGN Sec 6.0/6.4 needs, which
# replaces the single "~100 decisions/s" scalar s56 measured on three cells.
#
# Like a0_ship.sh and s58_ship.sh this EXTENDS the existing untargeted harness
# rather than building a new one: pysweep_run.ps1 + untargeted_super.ps1
# already ARE the generic Python farm path (--shard/--out + STATUS heartbeat +
# ledger + stall flagging), so all that is missing is the payload, one shim,
# and an env check.
#
# Farm layout touched (F: ONLY -- never C:, never F:\audioPrime):
#   F:\superpermFarm\untargeted\
#     qsb_shim.py  qsb_env.ps1  QSB_MANIFEST.tsv       <- this ship
#     repo\analysis\counting\s62\qsbsweep.py            the instrument
#     repo\out\s56\p1a\p1a_assume.py                    instance_text/confirm_sat
#     repo\out\s57\proposer\dlxrun.py                   the engine runner
#     repo\analysis\cover7\chain7.py                    chain -> instance
#     repo\analysis\farm\farm_chains.jsonl              the 223 chains (#0, #24)
#     repo\out\s59\cliff\qsb.py                         PROVENANCE ONLY
#     extraDocs\superpermutation-examples\scripts\{gain1,certificate}.py
#
# THE ENGINE IS NOT REBUILT.  s58_ship.sh built dlx7g.exe from the repo's own
# analysis/trackc/dlx7g.c into this shared repo mirror, and a0g1 ran on it
# today.  Every verdict in this sweep is that binary's verdict, so this script
# CONFIRMS it is present and refuses to ship without it rather than rebuilding
# and risking a different binary under the same claim.
#
# ---------------------------------------------------------------- MANIFEST --
# Derived by IMPORTING the instrument and reading sys.modules, not by guessing
# (the s58 method; the probe lived in the session scratchpad, since
# analysis/farm/ has no home for throwaways).  Result:
#
#   qsbsweep.py -> p1a_assume -> {certificate, gain1, chain7}
#               -> chain7
#               -> dlxrun      -> (subprocess only: dlx7g.exe)
#   data actually opened: analysis/farm/farm_chains.jsonl and nothing else.
#   No numpy.  NOT needed (they belong to s58's paircuts chain, not this one):
#   propose.py, prune_all.json, enum_ext.py, fvnorm.py.  NOT needed (they
#   belong to a0's chain): any data/upstream5906 word file -- this instrument
#   starts from a CHAIN, not from a word.
#
# Most of the payload is already on the box from s58_ship.sh and a0_ship.sh.
# It is re-shipped and re-hashed anyway: a deployment that depends on another
# sweep's leftovers still being there, and still being the same bytes, is not a
# deployment.  The manifest is the second end of that claim (qsb_env.ps1
# re-hashes every row PC-side).
#
# usage:  bash analysis/farm/qsb_ship.sh              # ship + verify
#         bash analysis/farm/qsb_ship.sh --scripts    # shim/env only (fast)
#         bash analysis/farm/qsb_ship.sh --manifest   # print manifest, no ship
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
DEST_WIN='F:\superpermFarm\untargeted'
DEST_SCP='F:/superpermFarm/untargeted'
MODE="${1:-all}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

cd "$REPO"

INSTRUMENT=analysis/counting/s62/qsbsweep.py

# repo-relative payload; extracted under repo\ on the PC, so paths stay
# repo-relative on both ends and every __file__-derived REPO root still works.
FILES=(
  "$INSTRUMENT"
  out/s56/p1a/p1a_assume.py
  out/s57/proposer/dlxrun.py
  analysis/cover7/chain7.py
  analysis/farm/farm_chains.jsonl
)
# Provenance only.  out/s59/cliff/qsb.py is the SOURCE OF TRUTH for the
# sampling stream (`random.Random(12345 + chain)` + `rng.sample(pool, k)`)
# that makes these cells comparable to s56/s59, so it belongs on the box for a
# human to diff against qsbsweep.draw().  It is NEVER imported or run there:
# it is a local-run script with its own hard-coded cell list, both lanes, and
# no farm contract.
PROVENANCE=(
  out/s59/cliff/qsb.py
)
# Lives OUTSIDE the repo; p1a_assume.py puts <repo>\..\extraDocs\... on sys.path.
EXTRA=(
  ../extraDocs/superpermutation-examples/scripts/gain1.py
  ../extraDocs/superpermutation-examples/scripts/certificate.py
)

# farm-side path of a payload file, RELATIVE TO $ROOT, backslashed -- the
# manifest carries this so qsb_env.ps1 can re-hash on the PC without having to
# re-derive the layout (manifest on BOTH ends, not just shipped).
farmpath() {
  case "$1" in
    ../extraDocs/*) printf 'extraDocs\\superpermutation-examples\\scripts\\%s' "$(basename "$1")" ;;
    *)              printf 'repo\\%s' "$(printf '%s' "$1" | tr '/' '\\')" ;;
  esac
}

emit_manifest() {
  printf 'sha256\tbytes\tmac_path\tfarm_relpath\n'
  for f in "${FILES[@]}" "${PROVENANCE[@]}" "${EXTRA[@]}"; do
    printf '%s\t%s\t%s\t%s\n' \
      "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(stat -f %z "$f")" "$f" "$(farmpath "$f")"
  done
}

if [ "$MODE" = "--manifest" ]; then
  for f in "${FILES[@]}" "${PROVENANCE[@]}" "${EXTRA[@]}"; do
    if [ -f "$f" ]; then printf '%10d  %s\n' "$(stat -f %z "$f")" "$f"
    else                 printf '%10s  %s\n' MISSING "$f"; fi
  done
  exit 0
fi

echo "== shipping harness scripts (shim + env) =="
# COPYFILE_DISABLE=1 on EVERY tar/scp -- docs/OPERATIONS.md s29 AppleDouble
# lesson: an untreated bsdtar ships a hidden ._x twin per file AND hides it
# from `tar -t`.  scp of a resource-forked file is the same hazard.
COPYFILE_DISABLE=1 scp -q \
  analysis/farm/qsb_shim.py \
  analysis/farm/qsb_env.ps1 \
  "${HOST}:${DEST_SCP}/"

if [ "$MODE" = "--scripts" ]; then
  echo "scripts-only ship done (no payload, no verify)."
  exit 0
fi

# ------------------------------------------------------------- payload ship --
for f in "${FILES[@]}" "${PROVENANCE[@]}" "${EXTRA[@]}"; do
  [ -f "$f" ] || { echo "MISSING: $f" >&2; exit 1; }
done

echo "== confirming dlx7g.exe (built by s58_ship.sh -- NOT rebuilt here) =="
dlxinfo=$(sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"\$p='${DEST_WIN}\\repo\\analysis\\trackc\\dlx7g.exe'; if (Test-Path \$p) { 'DLX_OK {0} bytes, built {1}' -f (Get-Item \$p).Length, (Get-Item \$p).LastWriteTime } else { 'DLX_MISSING' }\"")
echo "   $dlxinfo"
case "$dlxinfo" in
  *DLX_OK*) ;;
  *) echo "FATAL: dlx7g.exe is not on the farm. Run: bash analysis/farm/s58_ship.sh" >&2; exit 1 ;;
esac

echo "== staging farm dirs =="
# No path here contains a space, so nothing is quoted -- OPERATIONS/SWEEP-QUEUE
# trap: `cmd /c "exe" args > "log"` silently strips the OUTER quotes and the
# redirect never fires.  Quote only when a path actually needs it.
sshq "cmd /c mkdir ${DEST_WIN}\\repo\\analysis\\counting\\s62 ${DEST_WIN}\\repo\\analysis\\cover7 ${DEST_WIN}\\repo\\analysis\\farm ${DEST_WIN}\\repo\\out\\s56\\p1a ${DEST_WIN}\\repo\\out\\s57\\proposer ${DEST_WIN}\\repo\\out\\s59\\cliff ${DEST_WIN}\\extraDocs\\superpermutation-examples\\scripts" >/dev/null

TAR=$(mktemp -t qsb_payload).tar.gz
MAN=$(mktemp -t qsb_manifest).tsv
echo "== building manifest + tarball =="
emit_manifest > "$MAN"
cp "$MAN" /tmp/qsb_MANIFEST.tsv

COPYFILE_DISABLE=1 tar -czf "$TAR" "${FILES[@]}" "${PROVENANCE[@]}"
if gzip -dc "$TAR" | tar -tf - | grep -q '/\._'; then
  echo "FATAL: AppleDouble entries in the tarball" >&2; exit 1
fi
echo "   $(( ${#FILES[@]} + ${#PROVENANCE[@]} )) files, $(( $(stat -f %z "$TAR") / 1024 )) KB"

echo "== transferring =="
COPYFILE_DISABLE=1 scp -q "$TAR" "${HOST}:${DEST_SCP}/qsb_payload.tar.gz"
COPYFILE_DISABLE=1 scp -q "$MAN" "${HOST}:${DEST_SCP}/QSB_MANIFEST.tsv"
COPYFILE_DISABLE=1 scp -q "${EXTRA[@]}" \
  "${HOST}:${DEST_SCP}/extraDocs/superpermutation-examples/scripts/"
rm -f "$TAR" "$MAN"

echo "== extracting on the PC =="
sshq "cmd /c \"cd /d ${DEST_WIN}\\repo && tar -xzf ..\\qsb_payload.tar.gz && echo EXTRACT_OK\""
sshq "cmd /c del ${DEST_WIN}\\qsb_payload.tar.gz"

echo "== verifying (manifest re-hash + engine + PARITY of stream/instance/verdict) =="
# qsb_env.ps1 re-hashes every manifest row PC-side AND re-draws six pinned
# samples, rebuilding their instances and re-solving four of them, comparing
# sha256 + verdict + node count with Mac-computed constants.  Its exit code is
# the failure count.
sshq "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\qsb_env.ps1"

cat <<EOF

shipped.  manifest copy: /tmp/qsb_MANIFEST.tsv

ROUND-ROBIN PROBE FIRST (house rule -- and it is not a formality here: the
measured spread across cells is ~0.006 s at 3.0xR against a 30 s timeout at
4.5xR+, i.e. FOUR ORDERS OF MAGNITUDE, and the queue entry's 2.5 core-hour
projection was extrapolated from TL 5 s data).  --probe 10 runs the first 10
samples of EVERY cell, ~180 units, under 4 min wall, and prices the real thing:

  probe   : ${DEST_WIN}\\pysweep_run.ps1 -Tag qsbp1 -Target qsb_shim.py -Mode "" \\
            -Shards 24 -Workers 24 -Total 180 -MBPerShard 250 -StallMinutes 5 \\
            -What "s62 QS-B pricing probe: 18 cells x 10 samples, TL 30s, eps=0" \\
            -ExtraArgs "--time-limit 30 --probe 10"

Then read out/s62/farm/qsbp1's per-cell timeout fractions and decide whether
the full grid is affordable as specced.  Projection from a 2-sample Mac probe:
~4-10 core-hours, ~11-28 min wall at 24 workers -- NOT the ~7 min the queue
entry projected, because at TL 30 the undecided cells cost 30 s each instead of
the 4.8 s they cost at the s59 TL of 5 s.

  full run: ${DEST_WIN}\\pysweep_run.ps1 -Tag qsb1 -Target qsb_shim.py -Mode "" \\
            -Shards 24 -Workers 24 -Total 3600 -MBPerShard 250 -StallMinutes 5 \\
            -What "s62 QS-B verdict-mix: chains 0/24 x 9 mults x 200, TL 30s, eps=0" \\
            -ExtraArgs "--time-limit 30"
            ^ -StallMinutes 5, not the default 10: one shard emits one STATUS
              progress row per UNIT, so its worst-case silence is ONE solver
              call = 30 s.  5 min is 10x that -- early enough to catch a wedged
              shard, loose enough that a loaded box never false-flags.
              (Contrast a0g1, which needed 20: one cell per shard = one 600 s
              silence by design.)
            ^ 24 shards on 28 cores leaves 4 for the transcription service.
              The conservative alternative is -Shards 18 -Workers 18 (what a0g1
              used, leaving 10 cores), at ~33% more wall time.
            ^ -Total is only the supervisor's fallback; each shard declares its
              own 150 units (3600/24) in its STATUS rows and that always wins.
            ^ -MBPerShard 250 is measured, not guessed: a shard that has drawn
              all 18 cells' 200-sample lists peaks at 148 MB RSS on the Mac
              (both chain instances + 3,600 atom sets).  24 x 250 MB + 2 GB is
              what pysweep_run.ps1 will demand free before it launches.
  status  : ${DEST_WIN}\\untargeted_status.ps1 -Tag qsb1
  ABORT   : ${DEST_WIN}\\untargeted_abort.ps1 -Tag qsb1
            ^ NOT pkill -f dlxrun (that is the local-Mac form).  The farm abort
              uses the pid+name+start-time identity guard so it can never kill
              the transcription service's python.
  fetch   : bash analysis/farm/qsb_fetch.sh qsb1            (on the Mac)

A SAT ON EITHER CHAIN IS A WORLD-RECORD CANDIDATE, not a findability curiosity:
chains #0 and #24 are OPEN, both have K + R = 141, and length = 5764 +
#2-loops with #2-loops pinned at K + R by the chain (s34 law), so any cover
compiles to a 5905.  The shard STOPS on a SAT and banners it.  Gate it on the
MAC -- the PC has no Rust toolchain, so p1a_assume.confirm_sat cannot finish
there and qsbsweep falls back to the Python half (check_cover + compile),
reported as VALIDATOR-UNAVAILABLE, never as validated:
  1. p1a_assume.confirm_sat
  2. cargo run --release -- validate -n 7 --file <abspath> --complete
  3. python3 analysis/counting/m3_check.py -n 7 <abspath>     (exit 2 = novel)
All three green before any claim.

An UNSAT here is a NORMAL RESULT and most of the product (it is a theorem about
one draw: no cover of the chain uses only those k loops).  It says NOTHING
about the chain being closed, and it must never be reported as one.  An UNKNOWN
is a timeout: nothing learned, never a negative result.
EOF
