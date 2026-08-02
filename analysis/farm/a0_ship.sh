#!/usr/bin/env bash
# a0_ship.sh -- ship the s62 A0 gate sweep to the Windows farm PC.  RUNS ON THE MAC.
#
# WHAT THIS SWEEP IS.  It re-runs the s56 "A0 gate" -- can dlx7g find a cover
# from the CHAIN ALONE, with no atom assumptions -- at a real time budget.
# s56's "0/6" was measured at a 15 s cap and is the last uncorrected budget
# artifact in the repo (out/s59/cliff/REPORT.md §7 flags it), so the claim "no
# engine finds a cover from the chain alone" is currently not citable.  Grid:
# 6 control instances x 3 runs (1 seed at eps=0, 2 seeds at eps=0.15) = 18
# cells, sharded 18 ways, one cell per shard.
#
# Like s58_ship.sh this EXTENDS the existing untargeted harness rather than
# building a new one: pysweep_run.ps1 + untargeted_super.ps1 already are the
# generic Python farm path (--shard/--out + STATUS heartbeat + ledger + stall
# flagging), so all that is missing is the payload, one shim, and an env check.
#
# Farm layout touched (F: ONLY -- never C:, never F:\audioPrime):
#   F:\superpermFarm\untargeted\
#     a0_shim.py  a0_env.ps1  A0_MANIFEST.tsv          <- this ship
#     repo\analysis\counting\s62\a0gate.py             the instrument
#     repo\out\s56\p1a\p1a_assume.py                   the A0 instance builder
#     repo\out\s57\proposer\dlxrun.py                  the eps-lane runner
#     repo\analysis\cover7\chain7.py
#     repo\data\{upstream5906,novel5906c,upstream5907}\  the SIX control words
#     extraDocs\superpermutation-examples\scripts\{gain1,certificate}.py
#
# THE ENGINE IS NOT REBUILT.  s58_ship.sh already built dlx7g.exe from the
# repo's own analysis/trackc/dlx7g.c into the s62-shared repo mirror
# (repo\analysis\trackc\dlx7g.exe), and A0's verdicts are exactly that engine's
# verdicts.  This script CONFIRMS it is present and refuses to ship without it,
# rather than rebuilding and risking a different binary under the same claim.
#
# ---------------------------------------------------------------- MANIFEST --
# Derived the s58 way -- by IMPORTING the instrument chain and reading
# sys.modules, plus an audit hook on `open` to catch data files, NOT by
# guessing.  (analysis/farm/ has no home for throwaway probes; the probe lived
# in the session scratchpad.)  Result:
#
#   a0gate.py -> p1a_assume -> {certificate, gain1, chain7}
#             -> dlxrun     -> (subprocess only: dlx7g.exe)
#   data actually opened: exactly the six PANEL words of out/s59/cliff/geninst.py
#   nothing else; no numpy; propose.py / prune_all.json are s58's paircuts
#   chain and are NOT in A0's.
#
# THE PAYLOAD GAP this ship exists to close: s58_ship.sh ships every MODULE
# above but no data/ WORD file, because paircuts.py reads its chains from
# analysis/farm/farm_chains.jsonl instead.  A0 starts from the words, so the
# six control words are shipped here.  (They happen to be on the box already,
# left by untargeted_ship.sh's corpus ship for the loop-swap sweeps, and were
# spot-checked byte-identical -- but a deployment that depends on another
# sweep's leftovers surviving is not a deployment.  They are in the tarball and
# in the manifest.)
#
# usage:  bash analysis/farm/a0_ship.sh              # ship + verify
#         bash analysis/farm/a0_ship.sh --scripts    # shim/env only (fast, safe
#                                                    # before the instrument exists)
#         bash analysis/farm/a0_ship.sh --manifest   # print manifest, no ship
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
DEST_WIN='F:\superpermFarm\untargeted'
DEST_SCP='F:/superpermFarm/untargeted'
MODE="${1:-all}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

cd "$REPO"

INSTRUMENT=analysis/counting/s62/a0gate.py

# repo-relative payload; extracted under repo\ on the PC, so paths stay
# repo-relative on both ends and every __file__-derived REPO root still works.
FILES=(
  "$INSTRUMENT"
  out/s56/p1a/p1a_assume.py
  out/s57/proposer/dlxrun.py
  analysis/cover7/chain7.py
  data/upstream5906/5906.up-02d771908307.txt
  data/novel5906c/5906.rbnd-2641d60c9d5c.txt
  data/upstream5906/5906.up-331228e22360.txt
  data/upstream5906/5906.up-6f42b3603dac.txt
  data/upstream5906/5906.up-0a065898a821.txt
  data/upstream5907/5907.up-6f2e8d9df51c.txt
)
# Provenance only.  geninst.py is the authoritative source of the PANEL list
# and of the "regenerate the s56 instances exactly" conventions, so it belongs
# on the box for a human to diff -- but it must NEVER be imported: it builds
# instances and calls sys.exit() at MODULE level, which would kill a shard.
PROVENANCE=(
  out/s59/cliff/geninst.py
)
# Lives OUTSIDE the repo; p1a_assume.py puts <repo>\..\extraDocs\... on sys.path.
EXTRA=(
  ../extraDocs/superpermutation-examples/scripts/gain1.py
  ../extraDocs/superpermutation-examples/scripts/certificate.py
)

# farm-side path of a payload file, RELATIVE TO $ROOT, backslashed -- the
# manifest carries this so a0_env.ps1 can re-hash on the PC without having to
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
  [ -f "$INSTRUMENT" ] || echo "NOTE: $INSTRUMENT does not exist yet (second agent owns it)" >&2
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
  analysis/farm/a0_shim.py \
  analysis/farm/a0_env.ps1 \
  "${HOST}:${DEST_SCP}/"

if [ "$MODE" = "--scripts" ]; then
  echo "scripts-only ship done (no payload, no verify -- the instrument may not exist yet)."
  exit 0
fi

# ------------------------------------------------------------- payload ship --
for f in "${FILES[@]}" "${PROVENANCE[@]}" "${EXTRA[@]}"; do
  [ -f "$f" ] || {
    echo "MISSING: $f" >&2
    [ "$f" = "$INSTRUMENT" ] && echo "  (that is the s62 instrument -- it has not landed yet; use --scripts)" >&2
    exit 1
  }
done

# The engine must already be there.  s58_ship.sh built it from repo source into
# this same mirror; A0's soundness claim is "THAT binary said UNSAT/UNKNOWN".
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
sshq "cmd /c mkdir ${DEST_WIN}\\repo\\analysis\\counting\\s62 ${DEST_WIN}\\repo\\analysis\\cover7 ${DEST_WIN}\\repo\\out\\s56\\p1a ${DEST_WIN}\\repo\\out\\s57\\proposer ${DEST_WIN}\\repo\\out\\s59\\cliff ${DEST_WIN}\\repo\\data\\upstream5906 ${DEST_WIN}\\repo\\data\\novel5906c ${DEST_WIN}\\repo\\data\\upstream5907 ${DEST_WIN}\\extraDocs\\superpermutation-examples\\scripts" >/dev/null

TAR=$(mktemp -t a0_payload).tar.gz
MAN=$(mktemp -t a0_manifest).tsv
echo "== building manifest + tarball =="
emit_manifest > "$MAN"
cp "$MAN" /tmp/a0_MANIFEST.tsv

COPYFILE_DISABLE=1 tar -czf "$TAR" "${FILES[@]}" "${PROVENANCE[@]}"
if gzip -dc "$TAR" | tar -tf - | grep -q '/\._'; then
  echo "FATAL: AppleDouble entries in the tarball" >&2; exit 1
fi
echo "   $(( ${#FILES[@]} + ${#PROVENANCE[@]} )) files, $(( $(stat -f %z "$TAR") / 1024 )) KB"

echo "== transferring =="
COPYFILE_DISABLE=1 scp -q "$TAR" "${HOST}:${DEST_SCP}/a0_payload.tar.gz"
COPYFILE_DISABLE=1 scp -q "$MAN" "${HOST}:${DEST_SCP}/A0_MANIFEST.tsv"
COPYFILE_DISABLE=1 scp -q "${EXTRA[@]}" \
  "${HOST}:${DEST_SCP}/extraDocs/superpermutation-examples/scripts/"
rm -f "$TAR" "$MAN"

echo "== extracting on the PC =="
sshq "cmd /c \"cd /d ${DEST_WIN}\\repo && tar -xzf ..\\a0_payload.tar.gz && echo EXTRACT_OK\""
sshq "cmd /c del ${DEST_WIN}\\a0_payload.tar.gz"

echo "== verifying (manifest re-hash + engine + PARITY) =="
# a0_env.ps1 re-hashes every manifest row PC-side: that is the second end of
# the sha256 manifest, and it is what turns "we copied files" into "the PC has
# the same bytes".  Its exit code is the failure count.
sshq "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\a0_env.ps1"

cat <<EOF

shipped.  manifest copy: /tmp/a0_MANIFEST.tsv
next (powershell -NoProfile -ExecutionPolicy Bypass -File ...):
  launch  : ${DEST_WIN}\\pysweep_run.ps1 -Tag a0g1 -Target a0_shim.py -Mode "" \\
            -Shards 18 -Workers 18 -Total 18 -MBPerShard 300 -StallMinutes 20 \\
            -What "s62 A0 gate: 6 controls x 3 runs (eps 0 / 0.15), TL 600s" \\
            -ExtraArgs "--time-limit 600"
            ^ -StallMinutes 20, NOT the default 10: one shard = ONE cell, so a
              shard is legitimately silent for the whole 600 s solver call plus
              instance build.  At the default every shard would be flagged STALL.
            ^ 18 shards on 28 cores leaves 10 for the transcription service.
  status  : ${DEST_WIN}\\untargeted_status.ps1 -Tag a0g1
  ABORT   : ${DEST_WIN}\\untargeted_abort.ps1 -Tag a0g1
  fetch   : bash analysis/farm/a0_fetch.sh a0g1              (on the Mac)

A SAT on any control is a cover found from the chain alone -- a FINDABILITY
event, NOT a new record.  A0 is known-SAT by construction (reduce_instance with
no fixed rows and no atom filter is the identity, and p1a_assume.extract ASSERTS
every row of the source word's cover is present), and the chain pins
length = 5764 + (K+R), so the cover compiles to a word the SAME length as its
source -- 5906, or 5907 on that control.  It is a 5905 candidate only if the
compiled length actually comes out < 5906, which a0gate.py tests explicitly and
banners separately.  An UNSAT would be a soundness CONTRADICTION, not a result.
Gate every SAT on the MAC anyway (the PC has no Rust toolchain, so
p1a_assume.confirm_sat cannot finish there):
confirm_sat -> validate -n 7 --complete -> m3_check.py -n 7.
EOF
