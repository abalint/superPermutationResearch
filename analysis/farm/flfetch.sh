#!/usr/bin/env bash
# flfetch.sh -- pull an fl1577 study run home from the farm PC.
#   ./analysis/farm/flfetch.sh <tag> [dest]      default dest: out/fl1577_pc_study
# Tars on the PC and ships one file (many small scp's over this link are slow).
set -eu
TAG="${1:-s1}"
DEST="${2:-out/fl1577_pc_study}"
REMOTE="D:/superpermFarm/fl1577"
mkdir -p "$DEST"
ssh transcribe "powershell -NoProfile -Command \"cd $REMOTE\\runs; & \$env:SystemRoot\\System32\\tar.exe -czf $REMOTE\\runs\\$TAG.tgz $TAG\"" >/dev/null
scp "transcribe:/D:/superpermFarm/fl1577/runs/$TAG.tgz" "$DEST/" >/dev/null
tar -xzf "$DEST/$TAG.tgz" -C "$DEST"
rm -f "$DEST/$TAG.tgz"
echo "fetched runs/$TAG -> $DEST/$TAG"
