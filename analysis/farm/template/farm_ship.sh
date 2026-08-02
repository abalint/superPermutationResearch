#!/usr/bin/env bash
# farm_ship.sh -- THE ship script.  One, parameterized by a config (s64 P5).
# RUNS ON THE MAC.  Ships and verifies only -- it never launches anything.
#
#   bash analysis/farm/template/farm_ship.sh <config> [--scripts|--manifest|--dry]
#
# <config> is a name under analysis/farm/template/configs/ (e.g. `mc28`) or a
# path to a .conf file.  See configs/README or template/README.md for the key
# list; every knob the four per-instrument quartets used to hard-code
# (payload, side files, stall minutes, alarm additions, gate text) is a key.
#
# WHY THIS EXISTS.  a0_ship.sh, qsb_ship.sh, mc28_ship.sh and s58_ship.sh were
# ~54% verbatim-identical (normalized line-set intersection, s63 survey):
# the same COPYFILE_DISABLE tarball, the same AppleDouble scan, the same
# mkdir-the-mirror, the same manifest-on-both-ends, the same idle check.  So a
# fix in one reached none of the others -- and the fixes that mattered
# (bash-3.2 `mapfile`, CRLF sha corruption, the escape-scan .txt trap) each had
# to be found separately per instrument.  There is now one copy of each.
#
# HARD-WON RULES PRESERVED HERE (they are why the boilerplate looked like this)
#   * `COPYFILE_DISABLE=1` on EVERY tar and scp.  An untreated bsdtar ships a
#     hidden `._x` twin per file AND hides it from `tar -t` (OPERATIONS, s29).
#     The tarball is scanned for `/._` anyway -- belt and braces.
#   * bash 3.2 ONLY.  macOS ships 3.2: no `mapfile`, no `readarray`, no
#     associative arrays, no `${x^^}`.  s63 lost a farm pre-flight to `mapfile`
#     silently leaving an array EMPTY -- a run that DID find a first-of-species
#     walk would have been reported as "no products".
#   * Quote nothing that does not need quoting in the remote command.  `cmd /c
#     "exe" args > "log"` silently strips the OUTER quotes and the redirect
#     never fires (OPERATIONS/SWEEP-QUEUE trap).  No farm path has a space.
#   * `F:` only.  Never `C:`, never `F:\audioPrime`.
#   * The manifest lives on BOTH ends: the Mac writes sha256+bytes+farm path,
#     the PC re-hashes every row.  "We copied files" becomes "the PC has the
#     same bytes".
#
# ENV KNOBS
#   FARM_HOST=transcribe      ssh target.
#   FARM_SCRATCH=<subdir>     deploy the WHOLE harness under one throwaway
#                             subdirectory of the farm root -- how a template
#                             change is proven on the PC without touching a
#                             live deployment.
#   FARM_SKIP_SIDEFILES=1     do not ship (or verify) the large side files.
#                             HARNESS WORK ONLY: it also removes farm_env's
#                             presence check for them, so it must never be
#                             used on a pre-launch ship.
set -euo pipefail

TPL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${TPL}/../../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"

usage() {
  echo "usage: $0 <config> [--scripts|--manifest|--dry]" >&2
  echo "  configs: $(ls "${TPL}/configs"/*.conf 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/\.conf$//' | tr '\n' ' ')" >&2
  exit 64
}

CFG_NAME="${1:-}"
[ -n "$CFG_NAME" ] || usage
MODE="${2:-all}"

# ------------------------------------------------------------------ config --
CONF="$CFG_NAME"
[ -f "$CONF" ] || CONF="${TPL}/configs/${CFG_NAME}.conf"
[ -f "$CONF" ] || { echo "no such config: $CFG_NAME" >&2; usage; }

# defaults -- every key a config MAY set, so `set -u` is safe below and the
# config file only carries what is actually instrument-specific.
TAG=""; WHAT=""; ADAPTER=""; INSTRUMENT=""
FILES=(); EXTRA=(); PROVENANCE=(); SIDEFILES=(); SCRIPTS_EXTRA=()
SHARDS=24; WORKERS=24; STALL_MINUTES=10; MB_PER_SHARD=400; TOTAL=0
EXTRA_ARGS=""; DRYRUN_ARGS=""; MODE_TOKEN=""
FETCH_DEST="out/farm"; PRODUCT_GLOB=""; STATS_GLOB="stats_s*.tsv"
REQUIRE_IDLE=1; SELF_TEST=1; ENV_ARGS=""
GATE_TEXT=""; LAUNCH_NOTES=""; SCOPE_NOTE=""; ALARM_NOTES=""
DEST_WIN='F:\superpermFarm\untargeted'
DEST_SCP='F:/superpermFarm/untargeted'

# shellcheck source=/dev/null
. "$CONF"
[ -n "$TAG" ] || { echo "config sets no TAG: $CONF" >&2; exit 1; }
[ -n "$ADAPTER" ] || { echo "config sets no ADAPTER: $CONF" >&2; exit 1; }

# SCRATCH lets the whole deployment land under one throwaway subdirectory --
# how a template change is proven on the PC without touching a live harness.
SCRATCH="${FARM_SCRATCH:-}"
if [ -n "$SCRATCH" ]; then
  DEST_WIN="${DEST_WIN}\\${SCRATCH}"
  DEST_SCP="${DEST_SCP}/${SCRATCH}"
fi

MAN_WIN="${TAG}_MANIFEST.tsv"
CFG_WIN="${TAG}_CONFIG.tsv"

cd "$REPO"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

# The harness scripts that live at the farm ROOT (never inside repo\): the
# adapter, the shared bootstrap, the generic env check.  Everything else is
# repo-relative payload.
SCRIPTS="${TPL}/${ADAPTER} ${TPL}/farmlayout.py ${TPL}/farm_env.ps1"
for s in ${SCRIPTS_EXTRA[@]+"${SCRIPTS_EXTRA[@]}"}; do SCRIPTS="$SCRIPTS $s"; done
PARITY="${TPL}/configs/${TAG}.parity.tsv"

# farm-side path of a payload file, RELATIVE TO the deployment root,
# backslashed.  The manifest carries it so the PC can re-hash without
# re-deriving the layout.
farmpath() {
  case "$1" in
    ../extraDocs/*) printf 'extraDocs\\superpermutation-examples\\scripts\\%s' "$(basename "$1")" ;;
    *)              printf 'repo\\%s' "$(printf '%s' "$1" | tr '/' '\\')" ;;
  esac
}

emit_manifest() {
  printf 'sha256\tbytes\tmac_path\tfarm_relpath\n'
  for f in ${FILES[@]+"${FILES[@]}"} ${PROVENANCE[@]+"${PROVENANCE[@]}"} \
           ${EXTRA[@]+"${EXTRA[@]}"}; do
    printf '%s\t%s\t%s\t%s\n' \
      "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(stat -f %z "$f")" "$f" "$(farmpath "$f")"
  done
  # the adapter + bootstrap ship to the deployment ROOT, not under repo\
  for s in $SCRIPTS; do
    case "$s" in *.ps1) continue ;; esac   # env script is verified by running it
    printf '%s\t%s\t%s\t%s\n' \
      "$(shasum -a 256 "$s" | cut -d' ' -f1)" "$(stat -f %z "$s")" \
      "$s" "$(basename "$s")"
  done
  # side files land at the deployment root under their own names
  for pair in ${SIDEFILES[@]+"${SIDEFILES[@]}"}; do
    src="${pair%%:*}"; dst="${pair##*:}"
    [ "${FARM_SKIP_SIDEFILES:-0}" = "1" ] && continue
    [ -f "$src" ] || continue
    printf '%s\t%s\t%s\t%s\n' \
      "$(shasum -a 256 "$src" | cut -d' ' -f1)" "$(stat -f %z "$src")" "$src" "$dst"
  done
}

# The PC-side projection of the config.  ONE authored source of truth (the
# .conf); this is generated, never hand-edited, so farm_env.ps1 and the launch
# line can never disagree with the ship.
emit_pc_config() {
  printf 'key\tvalue\n'
  printf 'tag\t%s\n'            "$TAG"
  printf 'what\t%s\n'           "$WHAT"
  printf 'adapter\t%s\n'        "$(basename "$ADAPTER")"
  printf 'instrument\t%s\n'     "$INSTRUMENT"
  printf 'shards\t%s\n'         "$SHARDS"
  printf 'workers\t%s\n'        "$WORKERS"
  printf 'stall_minutes\t%s\n'  "$STALL_MINUTES"
  printf 'mb_per_shard\t%s\n'   "$MB_PER_SHARD"
  printf 'total\t%s\n'          "$TOTAL"
  printf 'mode_token\t%s\n'     "$MODE_TOKEN"
  printf 'extra_args\t%s\n'     "$EXTRA_ARGS"
  printf 'dryrun_args\t%s\n'    "$DRYRUN_ARGS"
  printf 'self_test\t%s\n'      "$SELF_TEST"
  for pair in ${SIDEFILES[@]+"${SIDEFILES[@]}"}; do
    [ "${FARM_SKIP_SIDEFILES:-0}" = "1" ] && continue
    printf 'sidefile\t%s\n' "${pair##*:}"
  done
}

if [ "$MODE" = "--manifest" ]; then
  emit_manifest
  exit 0
fi

echo "=== ship ${TAG} -> ${HOST}:${DEST_WIN} ==="
[ -n "$SCRATCH" ] && echo "    SCRATCH deployment (FARM_SCRATCH=${SCRATCH})"

for f in ${FILES[@]+"${FILES[@]}"} ${PROVENANCE[@]+"${PROVENANCE[@]}"} \
         ${EXTRA[@]+"${EXTRA[@]}"} $SCRIPTS; do
  [ -f "$f" ] || { echo "MISSING: $f" >&2; exit 1; }
done
[ -f "$PARITY" ] || { echo "MISSING parity spec: $PARITY" >&2; exit 1; }

# ---------------------------------------------------- local self-test first --
# Never ship an adapter that fails on the Mac.  (Cannot catch the Windows-only
# defects -- see farm_env.ps1's note on the CRLF sha bug, which only the PC
# round trip found -- but it catches everything else for free.)
if [ "$SELF_TEST" = "1" ] && grep -q -- "--self-test" "${TPL}/${ADAPTER}"; then
  echo "== local self-test =="
  python3 "${TPL}/${ADAPTER}" --self-test | tail -3
fi

if [ "$MODE" = "--dry" ]; then
  echo "== dry: would ship =="
  emit_manifest
  echo "== pc config =="
  emit_pc_config
  exit 0
fi

# --------------------------------------------------------------- idle check --
if [ "$REQUIRE_IDLE" = "1" ]; then
  echo "== confirming the box is idle BEFORE staging =="
  # Process NAME, not a command-line match: `pgrep -f`-style matching catches
  # the monitor's own command line (OPERATIONS, s19 PID-recycling section).
  # upyw.exe is the deliberately renamed venv python, so this can never see
  # -- or be confused by -- the transcription service's python.exe.
  idle=$(sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"'UPYW {0}' -f @(Get-Process -Name upyw -EA SilentlyContinue).Count\"")
  echo "   $idle"
  case "$idle" in
    *"UPYW 0"*) ;;
    *) echo "FATAL: upyw.exe is alive on the farm -- a sweep is running. untargeted_status.ps1 first." >&2; exit 1 ;;
  esac
fi

# --------------------------------------------------------- harness scripts --
echo "== staging deployment root =="
sshq "cmd /c mkdir ${DEST_WIN}" >/dev/null
echo "== shipping harness scripts (adapter + bootstrap + env + parity) =="
# shellcheck disable=SC2086
COPYFILE_DISABLE=1 scp -q $SCRIPTS "$PARITY" "${HOST}:${DEST_SCP}/"

if [ "$MODE" = "--scripts" ]; then
  echo "scripts-only ship done (no payload, no verify)."
  exit 0
fi

# --------------------------------------------------------------- the mirror --
echo "== staging farm dirs =="
DIRS=""
for f in ${FILES[@]+"${FILES[@]}"} ${PROVENANCE[@]+"${PROVENANCE[@]}"}; do
  d="$(dirname "$f")"
  case " $DIRS " in *" $d "*) ;; *) DIRS="$DIRS $d" ;; esac
done
MKDIRS=""
for d in $DIRS; do
  MKDIRS="$MKDIRS ${DEST_WIN}\\repo\\$(printf '%s' "$d" | tr '/' '\\')"
done
if [ ${#EXTRA[@]} -gt 0 ]; then
  MKDIRS="$MKDIRS ${DEST_WIN}\\extraDocs\\superpermutation-examples\\scripts"
fi
[ -n "$MKDIRS" ] && sshq "cmd /c mkdir$MKDIRS" >/dev/null

TAR=$(mktemp -t "${TAG}_payload").tar.gz
MAN=$(mktemp -t "${TAG}_manifest").tsv
PCC=$(mktemp -t "${TAG}_config").tsv
echo "== building manifest + tarball =="
emit_manifest > "$MAN"
emit_pc_config > "$PCC"
cp "$MAN" "/tmp/${MAN_WIN}"

COPYFILE_DISABLE=1 tar -czf "$TAR" \
  ${FILES[@]+"${FILES[@]}"} ${PROVENANCE[@]+"${PROVENANCE[@]}"}
if gzip -dc "$TAR" | tar -tf - | grep -q '/\._'; then
  echo "FATAL: AppleDouble entries in the tarball" >&2; exit 1
fi
echo "   $(( ${#FILES[@]} + ${#PROVENANCE[@]} )) files, $(( $(stat -f %z "$TAR") / 1024 )) KB"

echo "== transferring =="
COPYFILE_DISABLE=1 scp -q "$TAR" "${HOST}:${DEST_SCP}/${TAG}_payload.tar.gz"
COPYFILE_DISABLE=1 scp -q "$MAN" "${HOST}:${DEST_SCP}/${MAN_WIN}"
COPYFILE_DISABLE=1 scp -q "$PCC" "${HOST}:${DEST_SCP}/${CFG_WIN}"
if [ ${#EXTRA[@]} -gt 0 ]; then
  COPYFILE_DISABLE=1 scp -q "${EXTRA[@]}" \
    "${HOST}:${DEST_SCP}/extraDocs/superpermutation-examples/scripts/"
fi
rm -f "$TAR" "$MAN" "$PCC"

echo "== extracting on the PC =="
sshq "cmd /c \"cd /d ${DEST_WIN}\\repo && tar -xzf ..\\${TAG}_payload.tar.gz && echo EXTRACT_OK\""
sshq "cmd /c del ${DEST_WIN}\\${TAG}_payload.tar.gz"

# ------------------------------------------------------------- side files ---
# Large inputs (cover streams, corpora): gzipped for the wire, landed at the
# deployment root, sha printed on BOTH ends.  In-band verification (the
# instrument re-hashing the file's own body) is the other end of this check
# where the format supports it.
for pair in ${SIDEFILES[@]+"${SIDEFILES[@]}"}; do
  src="${pair%%:*}"; dst="${pair##*:}"
  if [ "${FARM_SKIP_SIDEFILES:-0}" = "1" ]; then
    echo "== side file $dst SKIPPED (FARM_SKIP_SIDEFILES=1) =="
    continue
  fi
  if [ ! -f "$src" ]; then
    echo "== side file ABSENT: $src -- shards that require it will refuse =="
    continue
  fi
  echo "== shipping side file $dst ($(( $(stat -f %z "$src") / 1048576 )) MB raw) =="
  CT=$(mktemp -t "${TAG}_side").tar.gz
  COPYFILE_DISABLE=1 tar -czf "$CT" -C "$(dirname "$src")" "$(basename "$src")"
  echo "   gzipped to $(( $(stat -f %z "$CT") / 1048576 )) MB"
  COPYFILE_DISABLE=1 scp -q "$CT" "${HOST}:${DEST_SCP}/${TAG}_side.tar.gz"
  rm -f "$CT"
  sshq "cmd /c \"cd /d ${DEST_WIN} && tar -xzf ${TAG}_side.tar.gz && echo SIDE_EXTRACT_OK\""
  sshq "cmd /c del ${DEST_WIN}\\${TAG}_side.tar.gz"
  echo "   Mac sha256: $(shasum -a 256 "$src" | cut -d' ' -f1)"
  sshq "powershell -NoProfile -ExecutionPolicy Bypass -Command \"'   PC  sha256: ' + (Get-FileHash '${DEST_WIN}\\${dst}' -Algorithm SHA256).Hash.ToLower()\""
done

# ---------------------------------------------------------------- verify -----
echo "== verifying (manifest re-hash + parity + adapter self-test) =="
sshq "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\farm_env.ps1 -Tag ${TAG} -Root ${DEST_WIN} ${ENV_ARGS}"

cat <<EOF

shipped.  manifest copy: /tmp/${MAN_WIN}
${LAUNCH_NOTES}

launch (powershell -NoProfile -ExecutionPolicy Bypass -File ...):
  F:\\superpermFarm\\untargeted\\pysweep_run.ps1 -Tag <TAG> -Target ${SCRATCH:+${SCRATCH}\\}$(basename "$ADAPTER") -Mode "${MODE_TOKEN}" \\
      -Shards ${SHARDS} -Workers ${WORKERS} -Total ${TOTAL} -MBPerShard ${MB_PER_SHARD} \\
      -StallMinutes ${STALL_MINUTES} -What "${WHAT}" \\
      -ExtraArgs "${EXTRA_ARGS}"
  smoke first (seconds; proves the whole launch path):
      ... -Tag <TAG>dry -DryRun -ExtraArgs "${DRYRUN_ARGS:-${EXTRA_ARGS}}"
  status  : F:\\superpermFarm\\untargeted\\untargeted_status.ps1 -Tag <TAG>
  ABORT   : F:\\superpermFarm\\untargeted\\untargeted_abort.ps1 -Tag <TAG>   (NEVER pkill on the PC)
  fetch   : bash analysis/farm/template/farm_fetch.sh ${TAG} <TAG>          (on the Mac)
${SCOPE_NOTE}
EOF
