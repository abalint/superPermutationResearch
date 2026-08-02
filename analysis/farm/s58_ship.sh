#!/usr/bin/env bash
# s58_ship.sh -- ship the two s58 farm instruments (pairwise cut store,
# extended-census sweep) to the Windows farm PC.  RUNS ON THE MAC.
#
# It EXTENDS the existing untargeted harness rather than building a new one:
# pysweep_run.ps1 + untargeted_super.ps1 are already the generic Python farm
# path (--shard/--out + STATUS heartbeat + ledger + stall flagging), so all
# that is missing is the payload, two shims, and a native dlx7g.exe.
#
# Farm layout produced (F: only -- NEVER C:, NEVER F:\audioPrime):
#   F:\superpermFarm\untargeted\
#     paircuts_shim.py  enumext_shim.py  s58_env.ps1     <- this ship
#     repo\analysis\counting\s58\        the two instruments
#     repo\analysis\cover7\chain7.py     + out\s56\p1a, out\s57\{proposer,express}
#     repo\analysis\trackc\dlx7g.{c,exe} the engine, built HERE from repo source
#     extraDocs\superpermutation-examples\scripts\{gain1,certificate}.py
#
# WHY dlx7g IS REBUILT.  The PC already has F:\superpermFarm\trackc2\dlx7g.exe,
# but its dlx7g.c does NOT match the repo's (sha 99E791E3.. vs B25EBE9B..,
# and not a line-ending difference).  The cut store's soundness is exactly the
# claim "this engine exhausted the tree", so the engine must be the one the
# Mac-side oracle validated.  It is built into the s58 repo mirror, leaving
# trackc2's copy untouched -- paircuts.py's DEFAULT_DLX already resolves to
# <repo>\analysis\trackc\dlx7g.exe on Windows, so nothing needs a --dlx flag.
#
# The manifest was determined by IMPORTING the instruments and reading
# sys.modules, not by guessing:
#   paircuts.py      -> chain7, p1a_assume, propose, dlxrun, gain1, certificate
#                       + data: prune_all.json, farm_chains.jsonl
#   enumext_sweep.py -> enum_ext, fvnorm, chain7
#   neither needs numpy.
#
# usage:  bash analysis/farm/s58_ship.sh              # ship + build + verify
#         bash analysis/farm/s58_ship.sh --scripts    # shims/env only (fast)
#         bash analysis/farm/s58_ship.sh --manifest   # print manifest, no ship
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
DEST_WIN='F:\superpermFarm\untargeted'
DEST_SCP='F:/superpermFarm/untargeted'
MODE="${1:-all}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

cd "$REPO"

# repo-relative payload (extracted under repo\ on the PC)
FILES=(
  analysis/counting/s58/paircuts.py
  analysis/counting/s58/paircuts_oracle.py
  analysis/counting/s58/enumext_sweep.py
  analysis/cover7/chain7.py
  out/s56/p1a/p1a_assume.py
  out/s57/proposer/propose.py
  out/s57/proposer/dlxrun.py
  out/s57/proposer/prune_all.json
  out/s57/express/enum_ext.py
  out/s57/express/fvnorm.py
  analysis/farm/farm_chains.jsonl
  analysis/trackc/dlx7g.c
)
# lives OUTSIDE the repo; paircuts.py looks for it at <repo>\..\extraDocs\...
EXTRA=(
  ../extraDocs/superpermutation-examples/scripts/gain1.py
  ../extraDocs/superpermutation-examples/scripts/certificate.py
)

if [ "$MODE" = "--manifest" ]; then
  for f in "${FILES[@]}" "${EXTRA[@]}"; do printf '%10d  %s\n' "$(stat -f %z "$f")" "$f"; done
  exit 0
fi

for f in "${FILES[@]}" "${EXTRA[@]}"; do
  [ -f "$f" ] || { echo "MISSING: $f" >&2; exit 1; }
done

echo "== staging farm dirs =="
sshq "cmd /c mkdir ${DEST_WIN}\\repo\\analysis\\counting\\s58 ${DEST_WIN}\\repo\\analysis\\trackc ${DEST_WIN}\\repo\\out\\s56\\p1a ${DEST_WIN}\\repo\\out\\s57\\proposer ${DEST_WIN}\\repo\\out\\s57\\express ${DEST_WIN}\\extraDocs\\superpermutation-examples\\scripts" >/dev/null

echo "== shipping harness scripts =="
COPYFILE_DISABLE=1 scp -q \
  analysis/farm/paircuts_shim.py \
  analysis/farm/enumext_shim.py \
  analysis/farm/s58_env.ps1 \
  analysis/farm/build_s58_dlx.bat \
  "${HOST}:${DEST_SCP}/"

if [ "$MODE" = "--scripts" ]; then echo "scripts-only ship done."; exit 0; fi

TAR=$(mktemp -t s58_payload).tar.gz
MAN=$(mktemp -t s58_manifest).tsv
echo "== building manifest + tarball =="
{
  printf 'sha256\tbytes\tpath\n'
  for f in "${FILES[@]}"; do
    printf '%s\t%s\t%s\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(stat -f %z "$f")" "$f"
  done
} > "$MAN"
cp "$MAN" /tmp/s58_MANIFEST.tsv

# COPYFILE_DISABLE=1 -- non-negotiable (docs/OPERATIONS.md s29 AppleDouble
# lesson: bsdtar ships a hidden ._x twin per file and hides it from `tar -t`).
COPYFILE_DISABLE=1 tar -czf "$TAR" "${FILES[@]}"
if gzip -dc "$TAR" | tar -tf - | grep -q '/\._'; then
  echo "FATAL: AppleDouble entries in the tarball" >&2; exit 1
fi
echo "   ${#FILES[@]} files, $(( $(stat -f %z "$TAR") / 1024 )) KB"

echo "== transferring =="
COPYFILE_DISABLE=1 scp -q "$TAR" "${HOST}:${DEST_SCP}/s58_payload.tar.gz"
COPYFILE_DISABLE=1 scp -q "$MAN" "${HOST}:${DEST_SCP}/S58_MANIFEST.tsv"
COPYFILE_DISABLE=1 scp -q "${EXTRA[@]}" \
  "${HOST}:${DEST_SCP}/extraDocs/superpermutation-examples/scripts/"
rm -f "$TAR" "$MAN"

echo "== extracting on the PC =="
sshq "cmd /c \"cd /d ${DEST_WIN}\\repo && tar -xzf ..\\s58_payload.tar.gz && echo EXTRACT_OK\""
sshq "cmd /c del ${DEST_WIN}\\s58_payload.tar.gz"

# The build script is a SHIPPED file, never generated inline: an earlier
# version echoed it through ssh -> cmd and the quotes around the vcvars path
# were eaten ("'\"C:\Program Files\...\"' is not recognized").
echo "== building dlx7g.exe from the repo source (MSVC, native) =="
sshq "cmd /c ${DEST_WIN}\\build_s58_dlx.bat"

echo "== verifying (env + parity) =="
sshq "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\s58_env.ps1"

cat <<EOF

shipped.  manifest copy: /tmp/s58_MANIFEST.tsv
next (all: powershell -NoProfile -ExecutionPolicy Bypass -File ...):
  paircuts  : ${DEST_WIN}\\pysweep_run.ps1 -Tag pc1 -Target paircuts_shim.py -Mode "" \\
              -Shards 24 -Workers 24 -Total 2350 -MBPerShard 300 \\
              -What "s58 pairwise cut store, chain #0" -ExtraArgs "--spec farm0 --cap 2000"
  enumext   : ${DEST_WIN}\\pysweep_run.ps1 -Tag ex1 -Target enumext_shim.py -Mode "" \\
              -Shards 24 -Workers 24 -Total 0 -MBPerShard 300 \\
              -What "s58 extended-census sweep" -ExtraArgs "--target 15 --pmax 16 --max-break 2 --depth 5"
  status    : ${DEST_WIN}\\untargeted_status.ps1 -Tag <tag>
  ABORT     : ${DEST_WIN}\\untargeted_abort.ps1 -Tag <tag>
  fetch     : bash analysis/farm/s58_fetch.sh <tag>
EOF
