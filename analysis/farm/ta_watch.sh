#!/bin/sh
# ta_watch.sh -- session-level heartbeat watch over a farm tail-atsp sweep.
# Polls the PC's tabrief.ps1 every $INTERVAL s and prints ONLY events worth
# acting on: the 871-candidate alarm, decile milestones, stage changes, worker
# deaths, a stalled heartbeat, and farm unreachability. Silence = healthy.
# usage: ta_watch.sh <tag> [interval_seconds]
TAG="${1:?usage: ta_watch.sh <tag> [interval]}"
INTERVAL="${2:-150}"
PS="powershell -NoProfile -ExecutionPolicy Bypass -File F:\\superpermFarm\\tailatsp\\tabrief.ps1 -Tag $TAG"

prev_stage=""; prev_dec=-1; prev_fin=-1; prev_alive=-1
fails=0; stall_warned=0; alarmed=0; eq_noted=0

echo "watch armed: tag=$TAG interval=${INTERVAL}s"
while true; do
  line=$(ssh -o ConnectTimeout=25 -o BatchMode=yes transcribe "$PS" 2>/dev/null | tr -d '\r' | grep -E '^(TAG|ERR)' | head -1)
  if [ -z "$line" ]; then
    fails=$((fails + 1))
    # one bad poll is noise; three in a row means the box or sshd is in trouble
    [ "$fails" -eq 3 ] && echo "FARM UNREACHABLE: 3 consecutive failed polls for $TAG (check the PC: memory pressure wedges F: while 'cmd /c echo alive' still answers)"
    sleep "$INTERVAL"; continue
  fi
  fails=0

  stage=$(echo "$line" | sed -n 's/.*STAGE=\([^ ]*\).*/\1/p')
  pct=$(echo "$line"   | sed -n 's/.*PCT=\([^ ]*\).*/\1/p')
  imp=$(echo "$line"   | sed -n 's/.*IMP=\([^ ]*\).*/\1/p')
  alive=$(echo "$line" | sed -n 's/.*ALIVE=\([^ ]*\).*/\1/p')
  fin=$(echo "$line"   | sed -n 's/.*FIN=\([^ ]*\).*/\1/p')
  age=$(echo "$line"   | sed -n 's/.*AGE=\([^ ]*\).*/\1/p')
  alarm=$(echo "$line" | sed -n 's/.*ALARM=\([^ ]*\).*/\1/p')
  mimp=$(echo "$line"  | sed -n 's/.*MIMP=\([^ ]*\).*/\1/p')
  meq=$(echo "$line"   | sed -n 's/.*MEQ=\([^ ]*\).*/\1/p')

  # 1. the alarm path: an improvement is an 871 candidate
  if [ "$alarmed" -eq 0 ] && { [ "$alarm" = "1" ] || { [ -n "$imp" ] && [ "$imp" -gt 0 ] 2>/dev/null; } \
       || { [ -n "$mimp" ] && [ "$mimp" -gt 0 ] 2>/dev/null; }; }; then
    alarmed=1
    echo "*** ALARM: 871 CANDIDATE -- $line  (do not overwrite finds/; gate with validate --complete + m3_check.py) ***"
  fi

  # 1b. first equal-cost 872 at S-1: not an alarm, but every one needs m3_check
  #     (a novel class would itself be an M3-class result), so say it once.
  if [ "$eq_noted" -eq 0 ] && [ -n "$meq" ] && [ "$meq" -gt 0 ] 2>/dev/null; then
    eq_noted=1
    echo "merge pipeline producing equal-cost 872s at S-1 (MEQ=$meq) -- gate them with ta_fetch.sh when the run ends: $line"
  fi

  # 2. stage transitions (RUNNING -> ALLDONE, or an ERR line)
  if [ "$stage" != "$prev_stage" ]; then
    [ -n "$prev_stage" ] && echo "stage: $prev_stage -> $stage | $line"
    prev_stage="$stage"
  fi

  # 3. decile progress
  dec=$(echo "$pct" | awk '{printf "%d", $1/10}' 2>/dev/null)
  if [ -n "$dec" ] && [ "$dec" -gt "$prev_dec" ] 2>/dev/null; then
    prev_dec="$dec"
    [ "$dec" -gt 0 ] && echo "progress: $line"
  fi

  # 4. a worker vanishing WITHOUT the finished count rising = a crash, not a finish
  if [ "$prev_alive" -ge 0 ] && [ "$alive" -lt "$prev_alive" ] 2>/dev/null && [ "$fin" -le "$prev_fin" ] 2>/dev/null; then
    echo "WORKER LOST without a ledger row (crash?): $line"
  fi
  prev_alive="$alive"; prev_fin="$fin"

  # 5. stalled heartbeat: supervisor not writing STATUS.txt while workers live
  if [ -n "$age" ] && [ "$age" -gt 300 ] 2>/dev/null && [ "$stage" = "RUNNING" ]; then
    if [ "$stall_warned" -eq 0 ]; then
      stall_warned=1
      echo "STALL WARNING: STATUS.txt ${age}s stale while stage=RUNNING -- supervisor may be dead: $line"
    fi
  else
    stall_warned=0
  fi

  if [ "$stage" = "ALLDONE" ]; then
    echo "COMPLETE: $line"
    exit 0
  fi
  sleep "$INTERVAL"
done
