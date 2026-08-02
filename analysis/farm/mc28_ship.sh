#!/usr/bin/env bash
# mc28_ship.sh -- ship the s63 v=28 supply-tight FOREST multi-cover sweep to the
# Windows farm PC.  RUNS ON THE MAC.  Ships and verifies only -- it never
# launches anything.
#
# WHAT THIS SWEEP IS.  docs/SWEEP-QUEUE.md's n=6 midgame j-probe (s62), PART 1,
# as RESHAPED by out/s63/mcover/REPORT.md §9: the four multi-cover branches as
# specced size to >= ~1,240 core-hours, but the branch that actually matters --
# v=28, splits=20, the ONLY j>=1 872 cell in a known allocation, (140,8,0,0,0)
# -- collapses once the phi-cycle law is used.  length <= 872 with j >= 1 forces
# R = 9, and R >= K = #phi-cycles with K even and K >= 8 forces K = 8, which
# holds IFF the loop-cycle incidence graph is a FOREST (REPORT §6).  So the
# whole cell is decided by enumerating FOREST multi-covers only, at a measured
# ~0.17 s/cover.  This ship carries that branch.
#
# Like a0_ship.sh / qsb_ship.sh this EXTENDS the existing untargeted harness
# rather than building a new one: pysweep_run.ps1 + untargeted_super.ps1 already
# ARE the generic Python farm path (--shard/--out + STATUS heartbeat + ledger +
# stall flagging), so all that is missing is the payload, one shim, and an env
# check.
#
# THE COVER FILE.  Since 2026-08-01 this ship also carries the ENUMERATED
# COVER STREAM (out/s63/mcover/covers_v28_forest.txt, produced once on the Mac
# by `--emit-covers`).  Sharding the enumeration instead would make all 24
# shards re-walk the entire forest tree -- 24x the enumeration for 1x the
# search.  The file is shipped gzipped, extracted on the PC, and its body
# sha256 + declared total are verified BY EVERY SHARD before it processes a
# line (engine exits 4 otherwise), so the manifest sha and the in-band sha are
# two independent ends of the same check.
#
# THE PAYLOAD IS THREE FILES AND NOTHING ELSE.  mcover_search.py imports only
# `cover_search.build` and `lib62.weight`, resolves them via
# sys.path.insert(0, dirname(__file__)) -- NOT via a repo root -- and opens no
# data file at all.  So unlike a0/qsb there is no import-chain archaeology and
# no corpus to ship: three stdlib-only Python files reproduce the entire search.
# (Verified by import audit on the Mac: no numpy, no subprocess, no engine.)
#
# NOTHING IS BUILT.  There is no compiled engine in this sweep -- the PC has no
# Rust toolchain and needs none.  That also means the alarm-path GATE cannot run
# on the PC: any find must come home and be gated on the Mac (mc28_fetch.sh).
#
# Farm layout touched (F: ONLY -- never C:, never F:\audioPrime):
#   F:\superpermFarm\untargeted\
#     mc28_shim.py  mc28_env.ps1  MC28_MANIFEST.tsv     <- this ship
#     repo\out\s62\jtax\mcover_search.py                the engine
#     repo\out\s62\jtax\cover_search.py                 build() -- shared tables
#     repo\out\s62\jtax\lib62.py                        weight/rotc/lam
#
# usage:  bash analysis/farm/mc28_ship.sh              # ship + verify
#         bash analysis/farm/mc28_ship.sh --scripts    # shim/env only (fast)
#         bash analysis/farm/mc28_ship.sh --manifest   # print manifest, no ship
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
DEST_WIN='F:\superpermFarm\untargeted'
DEST_SCP='F:/superpermFarm/untargeted'
MODE="${1:-all}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

cd "$REPO"

INSTRUMENT=out/s62/jtax/mcover_search.py

# repo-relative payload; extracted under repo\ on the PC, so paths stay
# repo-relative on both ends and the engine's own dirname(__file__) import
# still resolves.
FILES=(
  "$INSTRUMENT"
  out/s62/jtax/cover_search.py
  out/s62/jtax/lib62.py
)
# the enumerated cover stream (large; shipped separately, gzipped)
COVERS=out/s63/mcover/covers_v28_forest.txt
COVERS_WIN='F:\superpermFarm\untargeted\covers_v28_forest.txt'

# farm-side path of a payload file, RELATIVE TO $ROOT, backslashed -- the
# manifest carries this so mc28_env.ps1 can re-hash on the PC without having to
# re-derive the layout (manifest on BOTH ends, not just shipped).
farmpath() { printf 'repo\\%s' "$(printf '%s' "$1" | tr '/' '\\')"; }

emit_manifest() {
  printf 'sha256\tbytes\tmac_path\tfarm_relpath\n'
  for f in "${FILES[@]}"; do
    printf '%s\t%s\t%s\t%s\n' \
      "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(stat -f %z "$f")" "$f" "$(farmpath "$f")"
  done
  # the shim ships to $ROOT itself, not under repo\ -- manifest it too
  printf '%s\t%s\t%s\t%s\n' \
    "$(shasum -a 256 analysis/farm/mc28_shim.py | cut -d' ' -f1)" \
    "$(stat -f %z analysis/farm/mc28_shim.py)" \
    "analysis/farm/mc28_shim.py" "mc28_shim.py"
  if [ -f "$COVERS" ]; then
    printf '%s\t%s\t%s\t%s\n' \
      "$(shasum -a 256 "$COVERS" | cut -d' ' -f1)" \
      "$(stat -f %z "$COVERS")" "$COVERS" "covers_v28_forest.txt"
  fi
}

if [ "$MODE" = "--manifest" ]; then
  emit_manifest
  exit 0
fi

for f in "${FILES[@]}" analysis/farm/mc28_shim.py analysis/farm/mc28_env.ps1; do
  [ -f "$f" ] || { echo "MISSING: $f" >&2; exit 1; }
done

echo "== local self-test (never ship a shim that fails on the Mac) =="
python3 analysis/farm/mc28_shim.py --self-test | tail -2

echo "== shipping harness scripts (shim + env) =="
# COPYFILE_DISABLE=1 on EVERY tar/scp -- docs/OPERATIONS.md s29 AppleDouble
# lesson: an untreated bsdtar ships a hidden ._x twin per file AND hides it
# from `tar -t`.  scp of a resource-forked file is the same hazard.
COPYFILE_DISABLE=1 scp -q \
  analysis/farm/mc28_shim.py \
  analysis/farm/mc28_env.ps1 \
  "${HOST}:${DEST_SCP}/"

if [ "$MODE" = "--scripts" ]; then
  echo "scripts-only ship done (no payload, no verify)."
  exit 0
fi

echo "== confirming the box is idle BEFORE staging =="
idle=$(sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"'UPYW {0}' -f @(Get-Process -Name upyw -EA SilentlyContinue).Count\"")
echo "   $idle"
case "$idle" in
  *"UPYW 0"*) ;;
  *) echo "FATAL: upyw.exe is alive on the farm -- a sweep is running. untargeted_status.ps1 first." >&2; exit 1 ;;
esac

echo "== staging farm dirs =="
# No path here contains a space, so nothing is quoted -- OPERATIONS/SWEEP-QUEUE
# trap: `cmd /c "exe" args > "log"` silently strips the OUTER quotes and the
# redirect never fires.  Quote only when a path actually needs it.
sshq "cmd /c mkdir ${DEST_WIN}\\repo\\out\\s62\\jtax" >/dev/null

TAR=$(mktemp -t mc28_payload).tar.gz
MAN=$(mktemp -t mc28_manifest).tsv
echo "== building manifest + tarball =="
emit_manifest > "$MAN"
cp "$MAN" /tmp/MC28_MANIFEST.tsv

COPYFILE_DISABLE=1 tar -czf "$TAR" "${FILES[@]}"
if gzip -dc "$TAR" | tar -tf - | grep -q '/\._'; then
  echo "FATAL: AppleDouble entries in the tarball" >&2; exit 1
fi
echo "   ${#FILES[@]} files, $(( $(stat -f %z "$TAR") / 1024 )) KB"

echo "== transferring =="
COPYFILE_DISABLE=1 scp -q "$TAR" "${HOST}:${DEST_SCP}/mc28_payload.tar.gz"
COPYFILE_DISABLE=1 scp -q "$MAN" "${HOST}:${DEST_SCP}/MC28_MANIFEST.tsv"
rm -f "$TAR" "$MAN"

echo "== extracting on the PC =="
sshq "cmd /c \"cd /d ${DEST_WIN}\\repo && tar -xzf ..\\mc28_payload.tar.gz && echo EXTRACT_OK\""
sshq "cmd /c del ${DEST_WIN}\\mc28_payload.tar.gz"

# ---- the cover stream (large; gzip for the wire, verify sha on arrival) -----
if [ -f "$COVERS" ]; then
  echo "== shipping the cover stream ($(( $(stat -f %z "$COVERS") / 1048576 )) MB raw) =="
  CT=$(mktemp -t mc28_covers).tar.gz
  COPYFILE_DISABLE=1 tar -czf "$CT" -C "$(dirname "$COVERS")" "$(basename "$COVERS")"
  echo "   gzipped to $(( $(stat -f %z "$CT") / 1048576 )) MB"
  COPYFILE_DISABLE=1 scp -q "$CT" "${HOST}:${DEST_SCP}/mc28_covers.tar.gz"
  rm -f "$CT"
  sshq "cmd /c \"cd /d ${DEST_WIN} && tar -xzf mc28_covers.tar.gz && echo COVERS_EXTRACT_OK\""
  sshq "cmd /c del ${DEST_WIN}\\mc28_covers.tar.gz"
  echo "   Mac sha256: $(shasum -a 256 "$COVERS" | cut -d' ' -f1)"
  sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"'   PC  sha256: ' + (Get-FileHash '${COVERS_WIN}' -Algorithm SHA256).Hash.ToLower()\""
else
  echo "== NO cover stream at $COVERS -- run --emit-covers first =="
  echo "   (the shards REQUIRE it; mc28_shim.py refuses to enumerate-shard)"
fi

echo "== verifying (manifest re-hash + PARITY P1/P2 + shim self-test) =="
# mc28_env.ps1 re-hashes every manifest row PC-side (the second end of the
# sha256 manifest) and then makes the PC RE-DERIVE the brute-force-verified
# n=4 census and the designed-SAT n=5 census.  Its exit code is the failure
# count.  -Full adds the 200-cover real-branch node-count parity (~35 s).
sshq "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\mc28_env.ps1 -Full"

cat <<EOF

shipped.  manifest copy: /tmp/MC28_MANIFEST.tsv

LAUNCH GATE (2026-08-01, Andrew, recorded in SWEEP-QUEUE):  N_forest(28) must
be EXACT (the emit run finished, trailer present) and <= 3,000,000.  Above that
-> STOP, no launch.  A PARTIAL count is a lower bound and sizes nothing.

THE GATE IS IN *MAC* CORE-HOURS.  Measured at ship time by mc28_env.ps1 -Full:
the 200-cover real-branch parity ran 63 s on the farm vs 33 s on the Mac, so
this box is 1.91x SLOWER PER CORE.  Per-cover cost is therefore ~0.17 s on the
Mac and ~0.325 s here, and the two numbers the operator actually needs are

    farm core-hours = N_forest x 0.325 s / 3600
    wall (24 shards) = N_forest x 0.325 s / 24

      N_forest      Mac core-h    farm core-h    wall @24 shards
      206,043           9.7           18.6           47 min
    1,000,000          47.2           90.3          3.8 h
    1,500,000          70.8          135.4          5.6 h
    2,000,000          94.4          180.6          7.5 h
    3,000,000 (gate)  141.7          270.8         11.3 h

Re-measure the ratio if the box's load changes; the shard ledger's own secs
column is the authority once the run starts.

launch (powershell -NoProfile -ExecutionPolicy Bypass -File ...), with
SHARDS=24 and NFOREST=<the finished count>:
  ${DEST_WIN}\\pysweep_run.ps1 -Tag mc28f1 -Target mc28_shim.py -Mode "" \\
      -Shards 24 -Workers 24 -Total 24 -MBPerShard 300 -StallMinutes 20 \\
      -What "s63 (140,8,0,0,0) cell: v=28 splits=20 supply-tight FOREST multi-covers, TMAX 872 j>=1" \\
      -ExtraArgs "-n 6 --tmax 872 --v 28 --splits 20 --jmin 1 --forest --covers-file F:\superpermFarm\untargeted\covers_v28_forest.txt --tick 100"
    ^ -StallMinutes 20 with --tick 100.  Sized from measurement, not taste:
      per-cover cost on the FARM is 0.315 s (P3: 200 covers in 63 s), so one
      STATUS tick is 100 x 0.315 = ~32 s -- and that cadence is independent of
      N, so it does not change as the run gets longer.  Shard STARTUP silence
      is negligible: the sha-verify pass streams 107 MB in 0.3 s (355 MB/s) and
      the perm/door/mid tables build in 1.2 s, so the first tick lands ~35-40 s
      in.  20 min is therefore ~37x the healthy gap while still catching a
      genuinely wedged shard inside 20 minutes of an 11-hour run.  At N = 3M a
      shard walks ~125k covers = 1,250 STATUS rows -- comfortable for the
      supervisor's incremental reader.  Do NOT raise --tick without raising
      -StallMinutes with it.
    ^ 24 shards on 28 cores leaves 4 for the transcription service.
    ^ --covers-file is REQUIRED: the shim refuses to enumerate-shard, which
      would make every shard re-walk the whole forest tree.  Each shard
      verifies the file's body sha256 + declared total before processing a
      line (engine exit 4 otherwise), and takes the lines with idx % 24 == i,
      so the shards are EXACTLY balanced and the totals must sum to the file's
      own count -- which mc28_fetch.sh checks.
  smoke first (recommended, ~seconds, proves the whole launch path):
      ... -Tag mc28dry -Shards 24 ... -DryRun -ExtraArgs "<same>"
      then untargeted_abort.ps1 -Tag mc28dry is unnecessary -- dry shards exit.
  status  : ${DEST_WIN}\\untargeted_status.ps1 -Tag mc28f1
  ABORT   : ${DEST_WIN}\\untargeted_abort.ps1 -Tag mc28f1     (NEVER pkill on the PC)
  fetch   : bash analysis/farm/mc28_fetch.sh mc28f1            (on the Mac)

WHAT COUNTS AS A RESULT.  The expected outcome is 24 shards x "NO walk", which
together are a SOUND NEGATIVE: the (140,8,0,0,0) cell -- the only j>=1 872 cell
in a known allocation -- contains no pure complete first-visit walk.  The
negative is only valid if EVERY shard finished with rc 0 and no shard printed
"*** PARTIAL"; mc28_fetch.sh checks exactly that and refuses to summarise a
run with a missing or capped shard.

ANY FIND IS A FIRST-OF-SPECIES EVENT -- a materialized j >= 1 n=6 walk of
length <= 872.  The shim banners it (\`*** MC28 FIND\`), writes a \\tESCAPE\\t
STATUS row so the supervisor raises ALARM.txt, and preserves the walk.  The PC
cannot gate it (no Rust toolchain).  Gate on the Mac, all three, in order:
  cargo run --release -- validate -n 6 --file <f> --complete
  python3 analysis/counting/m3_check.py <f>          (exit 2 = novel)
  python3 out/s62/jtax/verify_master.py 6 <f>        (exit 1 = THEORY ALARM -> stop everything)
EOF
