#!/usr/bin/env bash
# untargeted_ship.sh -- ship the s49 fused-pair UNTARGETED instrument, its
# caches and its corpora to the Windows farm PC.  RUNS ON THE MAC.
#
# Why a tarball and not scp -r: ~1,900 small files over Tailscale; and
# COPYFILE_DISABLE=1 is MANDATORY on macOS (docs/OPERATIONS.md, s29 lesson --
# bsdtar silently ships an AppleDouble `._x` twin per file and hides them from
# `tar -t`, which would be parsed as corpus records).
#
# Farm layout produced (F: only -- NEVER C:, NEVER F:\audioPrime):
#   F:\superpermFarm\untargeted\
#     pyenv\                     venv over C:\Program Files\Python311 + numpy
#       Scripts\upyw.exe         renamed copy of the venv python (see below)
#     repo\                      repo-root MIRROR == the required working dir
#       analysis\counting\...    fuse.py, its sibling modules, the canon indexes
#       data\...                 rule tables + the 220-class corpora
#       out\s49\item1\...        the PREBUILT caches (no `fuse.py index` needed)
#     *.ps1 *.bat *.py           this harness
#     runs\<tag>\                one run dir per launch
#
# WORKING DIRECTORY: every farm-side invocation runs with cwd =
#   F:\superpermFarm\untargeted\repo
# fuse.py derives its own root from __file__ (4 dirnames up) so it is
# cwd-independent, but sizing_untargeted.py does `sys.path.insert(0,
# 'analysis/counting')` -- a RELATIVE path -- so anything in that family needs
# the repo mirror as cwd.  untargeted_run.ps1 sets it; do the same by hand.
#
# WHY upyw.exe: our 24 shards would otherwise be 24 processes named `python`,
# indistinguishable from the user's transcription service
# (I:\transcribe\.venv\Scripts\python.exe and C:\Program Files\Python311\
# python.exe).  REMOTE-FARM.md forbids killing python indiscriminately.  A
# renamed copy of the venv interpreter (CPython finds pyvenv.cfg by directory,
# not by exe name) makes `Get-Process -Name upyw` exact and makes it impossible
# for the abort script to touch the transcription service.
#
# usage:  bash analysis/farm/untargeted_ship.sh            # ship everything
#         bash analysis/farm/untargeted_ship.sh --scripts  # harness only (fast)
#         bash analysis/farm/untargeted_ship.sh --manifest # print manifest, no ship
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${FARM_HOST:-transcribe}"
DEST_WIN='F:\superpermFarm\untargeted'
DEST_SCP='F:/superpermFarm/untargeted'
MODE="${1:-all}"

sshq() { ssh "$HOST" "$@" 2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com" || true; }

cd "$REPO"

# ---------------------------------------------------------------- manifest --
# Determined by READING the code, not by guessing:
#   fuse.py            -> numpy; analysis/counting/i4a_apply.py (structure,
#                         replay), analysis/counting/loop_ledger_probe.py
#                         (first_visit_path); TABLES = 4 data/loopswap rule
#                         TSVs; DIRS = the n=7 corpora; OUT = out/s49/item1.
#   i4a_apply.py       -> loop_ledger_probe; m3_check (canon gate) ->
#                         upstream872_canon_index.tsv (n=6, loaded
#                         unconditionally by run_apply_sym) +
#                         upstream5906_canon_index.tsv + the 5 SUPPLEMENTARY
#                         indexes (novel5906{,b,c,d} + kristan5906_web) = the
#                         220-class project shell the s51 re-scope requires.
#   loop_ledger_probe  -> stdlib only.
# Everything under analysis/counting is shipped wholesale (~5 MB) rather than
# cherry-picked, so the as-built `untargeted` mode cannot miss a sibling
# import; likewise all of data/loopswap (rules_n7_s51.tsv included).
MANIFEST_GLOBS=(
  'analysis/counting/*.py'
  'analysis/counting/*.tsv'
  'analysis/counting/s49/*.py'
  'data/loopswap/*.tsv'
  'data/upstream5906/*.txt'
  'data/novel5906/*.txt'
  'data/novel5906b/*.txt'
  'data/novel5906c/*.txt'
  'data/novel5906d/*.txt'
  'data/kristan5906_web/*.txt'
  'data/upstream5907/*.txt'
)
# Prebuilt caches: shipping these means `fuse.py index` (~45 s) is NOT needed
# on the PC.  relab.npy is the 5040x5040 int32 relabel table (101 MB) that
# relab_table() rebuilds (minutes) if absent; inst_* are what build_index()
# writes.  blindspot12.txt / control12.txt are the S49_SOURCES source lists.
CACHE_FILES=(
  out/s49/item1/relab.npy
  out/s49/item1/inst_keys.npy
  out/s49/item1/inst_rule.npy
  out/s49/item1/inst_sigma.npy
  out/s49/item1/inst_ruleids.txt
  out/s49/item1/blindspot12.txt
  out/s49/item1/control12.txt
)

FILES=()
for g in "${MANIFEST_GLOBS[@]}"; do
  while IFS= read -r f; do [ -n "$f" ] && FILES+=("$f"); done < <(compgen -G "$g" || true)
done
for f in "${CACHE_FILES[@]}"; do
  [ -f "$f" ] || { echo "MISSING REQUIRED CACHE: $f (run: python3 analysis/counting/s49/fuse.py index)" >&2; exit 1; }
  FILES+=("$f")
done

if [ "$MODE" = "--manifest" ]; then
  printf '%s\n' "${FILES[@]}" | while read -r f; do
    printf '%10d  %s\n' "$(stat -f %z "$f")" "$f"
  done
  echo "----"
  echo "files: ${#FILES[@]}   total: $(printf '%s\n' "${FILES[@]}" | xargs stat -f %z | awk '{s+=$1} END {print s}') bytes"
  exit 0
fi

# ------------------------------------------------------------- harness ship --
echo "== staging farm dirs =="
sshq "cmd /c mkdir ${DEST_WIN}\\repo ${DEST_WIN}\\runs" >/dev/null

echo "== shipping harness scripts =="
COPYFILE_DISABLE=1 scp -q \
  analysis/farm/untargeted_run.ps1 \
  analysis/farm/untargeted_super.ps1 \
  analysis/farm/untargeted_super.bat \
  analysis/farm/untargeted_status.ps1 \
  analysis/farm/untargeted_abort.ps1 \
  analysis/farm/untargeted_env.ps1 \
  analysis/farm/untargeted_stub.py \
  analysis/farm/meminfo.ps1 \
  "${HOST}:${DEST_SCP}/"
echo "   -> ${DEST_WIN}\\"

if [ "$MODE" = "--scripts" ]; then echo "scripts-only ship done."; exit 0; fi

# ---------------------------------------------------------------- payload ---
TAR=$(mktemp -t untargeted_payload).tar.gz
MAN=$(mktemp -t untargeted_manifest).tsv
echo "== building manifest + tarball =="
{
  printf 'sha256\tbytes\tpath\n'
  for f in "${FILES[@]}"; do
    printf '%s\t%s\t%s\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(stat -f %z "$f")" "$f"
  done
} > "$MAN"
cp "$MAN" /tmp/untargeted_MANIFEST.tsv

# COPYFILE_DISABLE=1 -- non-negotiable (s29 AppleDouble lesson).
COPYFILE_DISABLE=1 tar -czf "$TAR" "${FILES[@]}"
BYTES=$(stat -f %z "$TAR")
NF=${#FILES[@]}
echo "   ${NF} files, tarball $(( BYTES / 1024 / 1024 )) MB"

# paranoia: the AppleDouble twins are hidden from `tar -t` on macOS bsdtar, so
# check with gzip -dc | tar -t (GNU-style listing) for any `/._` entry.
if gzip -dc "$TAR" | tar -tf - | grep -q '/\._'; then
  echo "FATAL: AppleDouble entries in the tarball -- COPYFILE_DISABLE was not honoured" >&2
  exit 1
fi

echo "== transferring =="
COPYFILE_DISABLE=1 scp -q "$TAR" "${HOST}:${DEST_SCP}/payload.tar.gz"
COPYFILE_DISABLE=1 scp -q "$MAN" "${HOST}:${DEST_SCP}/MANIFEST.tsv"
rm -f "$TAR" "$MAN"

echo "== extracting on the PC =="
sshq "cmd /c \"cd /d ${DEST_WIN}\\repo && tar -xzf ..\\payload.tar.gz && echo EXTRACT_OK\""
sshq "cmd /c del ${DEST_WIN}\\payload.tar.gz"

echo "== verifying (env + manifest + import + cache load) =="
sshq "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\untargeted_env.ps1"

cat <<EOF

shipped.  manifest copy: /tmp/untargeted_MANIFEST.tsv
next:
  launch : ssh ${HOST} "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\untargeted_run.ps1 -Tag <tag>"
  status : ssh ${HOST} "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\untargeted_status.ps1"
  abort  : ssh ${HOST} "powershell -NoProfile -ExecutionPolicy Bypass -File ${DEST_WIN}\\untargeted_abort.ps1"
  fetch  : bash analysis/farm/untargeted_fetch.sh <tag>
EOF
