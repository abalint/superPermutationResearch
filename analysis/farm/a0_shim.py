#!/usr/bin/env python3
"""a0_shim.py -- run the s62 A0 gate sweep under the farm supervisor's
contract, WITHOUT modifying a0gate.py.

WHY A SHIM EXISTS AT ALL (see paircuts_shim.py / promote_shim.py headers for
the full story).  pysweep_run.ps1 launches every shard as

    upyw.exe -u <TARGET> [<Mode>] --shard i/N --out <dir> [--limit K] [--dry-run] <ExtraArgs>

and TARGET must live under $ROOT (F:\\superpermFarm\\untargeted), NOT in the
repo mirror.  a0gate.py, like every instrument here, derives its repo root from
its own __file__ (dirnames up), so a copy sitting at $ROOT would resolve
out/s56/p1a, analysis/cover7 and data/upstream5906 to the wrong place and
import-fail instantly.  The shim is the one file that lives at $ROOT; it
locates the real instrument inside the repo mirror and execs it in place.

a0gate.py already speaks --shard/--out/--limit/--dry-run/--time-limit and
already writes the STATUS heartbeat, so -- as with paircuts_shim -- nothing is
rewritten here beyond dropping pysweep_run's optional bare -Mode token.

THE -Mode TOKEN.  a0gate.py has NO bare subcommand (contract: flags only), so
the launcher is invoked with -Mode "".  PowerShell interpolates that into the
command line as nothing at all, but a future launcher tweak or a hand-typed
-Mode would inject a leading positional and argparse would die with
"unrecognized arguments" on all 18 shards at once.  paircuts_shim.py drops such
a token defensively; so does this.  Cheap insurance against a whole-sweep loss.

SUPERVISOR COMPATIBILITY, checked against untargeted_super.ps1 as-built:
  * progress: the supervisor takes shard progress from `STATUS*` lines matching
    the tab-delimited `\\t<i>/<n>\\t` field, and the instrument's own declared
    <n> always beats the -Total fallback.  A0 has ONE cell per shard, so a
    shard reports 0/1 then 1/1 -- and is legitimately SILENT in between for the
    whole --time-limit.  Launch with -StallMinutes > time-limit/60 (a0_ship.sh
    recommends 20 for TL 600) or every healthy shard gets flagged STALL.
  * alarm scan regex is
      (?i)Traceback|MemoryError|^\\s*!!|\\*\\*\\*|ESCAPES\\s+[1-9]|NOVEL[^:\\r\\n]*:\\s*[1-9]
    A0's normal per-run output is a verdict line (SAT/UNSAT/UNKNOWN + seconds),
    which matches none of those -- so a healthy shard never self-banners.  That
    is the s52b bug (a normal "novel-candidate classes: 0" summary bannered all
    24 healthy shards) this note exists to avoid repeating.  RULE: if a0gate.py
    ever prints a summary containing the word NOVEL followed by a colon and a
    nonzero count, or a line starting with `!!`, re-check it against that regex
    BEFORE the next launch.
  * a SAT must print a `*** ` banner: that IS the alarm path, and a SAT here is
    a cover from the chain alone (on a 5906 control, a 5905 candidate).
  * `*_stats_*.tsv` in --out is picked up by the supervisor's `(?i)stat` TSV
    row counter; anything the instrument wants NOT line-counted every tick must
    not be a .tsv whose name contains "stat" or "edge".

usage: upyw.exe -u a0_shim.py --shard 0/18 --out F:\\...\\s00 --time-limit 600
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 1st candidate = the normal farm layout ($ROOT\repo\...); 2nd = a checkout
# where this shim sits in analysis/farm/ (lets the shim be smoke-tested on the
# Mac without a farm).  Same two-candidate pattern as paircuts_shim.py.
for cand in (os.path.join(HERE, "repo", "analysis", "counting", "s62"),
             os.path.join(HERE, "..", "counting", "s62")):
    if os.path.isdir(cand):
        TARGET = os.path.join(os.path.abspath(cand), "a0gate.py")
        break
else:
    print("a0_shim: cannot locate analysis/counting/s62", file=sys.stderr)
    sys.exit(2)

if not os.path.isfile(TARGET):
    print(f"a0_shim: instrument not found: {TARGET}", file=sys.stderr)
    sys.exit(2)

# a leading bare token would be pysweep_run.ps1's -Mode; this instrument has no
# subcommand, so drop one if present rather than letting argparse choke on it
if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    del sys.argv[1]
sys.argv[0] = TARGET
runpy.run_path(TARGET, run_name="__main__")
