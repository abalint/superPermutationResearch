#!/usr/bin/env python3
"""qsb_shim.py -- run the s62 QS-B verdict-mix sweep under the farm
supervisor's contract, WITHOUT modifying analysis/counting/s62/qsbsweep.py.

WHY A SHIM EXISTS AT ALL (paircuts_shim.py / promote_shim.py / a0_shim.py carry
the longer version).  pysweep_run.ps1 launches every shard as

    upyw.exe -u <TARGET> [<Mode>] --shard i/N --out <dir> [--limit K] [--dry-run] <ExtraArgs>

and TARGET must live under $ROOT (F:\\superpermFarm\\untargeted), NOT inside the
repo mirror.  qsbsweep.py, like every instrument here, derives its repo root
from its own __file__ (dirnames up), so a copy sitting at $ROOT would resolve
out/s56/p1a, out/s57/proposer, analysis/cover7 and analysis/farm/
farm_chains.jsonl to the wrong place and import-fail instantly.  The shim is
the one file that lives at $ROOT; it locates the real instrument inside the
repo mirror and execs it in place.

This is the paircuts_shim / a0_shim case, not the promote_shim case:
qsbsweep.py already speaks --shard/--out/--limit/--dry-run and already writes
the STATUS heartbeat itself, so NOTHING is rewritten here beyond dropping
pysweep_run's optional bare -Mode token.

THE -Mode TOKEN.  qsbsweep.py has no bare subcommand (contract: flags only), so
the launcher is invoked with -Mode "".  PowerShell interpolates that as nothing
at all, but a hand-typed -Mode or a future launcher tweak would inject a
leading positional and argparse would die with "unrecognized arguments" on all
shards at once.  Cheap insurance against a whole-sweep loss.

SUPERVISOR COMPATIBILITY, checked against untargeted_super.ps1 as-built:
  * progress: the supervisor takes shard progress from `STATUS*` lines matching
    the tab-delimited `\\t<i>/<n>\\t` field, and the instrument's own declared
    <n> beats the -Total fallback.  qsbsweep emits ONE progress row per UNIT
    (one solver call), so with 3600 units over N shards a shard is silent for
    at most one solver call -- i.e. at most --time-limit seconds (30 s at the
    queue's budget) plus instance build (~0.01 s).  The default
    -StallMinutes 10 is therefore ~20x the true worst-case gap; qsb_ship.sh
    still prints 10 explicitly so the number is a decision, not a default.
    (Contrast a0_shim: one CELL per shard meant one 600 s silence and needed
    -StallMinutes 20.)
  * alarm scan regex is
      (?i)Traceback|MemoryError|^\\s*!!|\\*\\*\\*|ESCAPES\\s+[1-9]|NOVEL[^:\\r\\n]*:\\s*[1-9]
    qsbsweep's normal output is one per-cell rollup line and one terminal
    summary, neither of which contains `***`, a leading `!!`, "Traceback",
    "MemoryError", "ESCAPES <nonzero>" or "NOVEL...: <nonzero>" -- and every
    print goes through its say() guard, which rewrites any healthy line that
    would match.  A healthy shard is structurally incapable of self-bannering.
    NOTE the specific hazard for THIS instrument: an UNSAT is a NORMAL,
    EXPECTED result here (it is most of the product -- the sweep measures the
    UNSAT FRACTION), so UNSAT must never banner.  Only a SAT does.
  * a SAT prints `*** ` on purpose: that IS the alarm path, and a SAT here is a
    cover of an OPEN n=7 chain, i.e. a 5905 world-record candidate.
  * `qsb_stats_s<NN>.tsv` in --out is picked up by the supervisor's `(?i)stat`
    TSV row counter (live progress).  `qsb_cells_s<NN>.tsv` deliberately
    matches neither `(?i)stat` nor `(?i)edge`, so the rollup rows are not
    double-counted into the same number.

usage: upyw.exe -u qsb_shim.py --shard 0/24 --out F:\\...\\s00 --time-limit 30
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 1st candidate = the normal farm layout ($ROOT\repo\...); 2nd = a checkout
# where this shim sits in analysis/farm/ (lets the shim be smoke-tested on the
# Mac without a farm).  Same two-candidate pattern as a0_shim.py.
for cand in (os.path.join(HERE, "repo", "analysis", "counting", "s62"),
             os.path.join(HERE, "..", "counting", "s62")):
    if os.path.isdir(cand):
        TARGET = os.path.join(os.path.abspath(cand), "qsbsweep.py")
        break
else:
    print("qsb_shim: cannot locate analysis/counting/s62", file=sys.stderr)
    sys.exit(2)

if not os.path.isfile(TARGET):
    print(f"qsb_shim: instrument not found: {TARGET}", file=sys.stderr)
    sys.exit(2)

# a leading bare token would be pysweep_run.ps1's -Mode; this instrument has no
# subcommand, so drop one if present rather than letting argparse choke on it
if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    del sys.argv[1]
sys.argv[0] = TARGET
runpy.run_path(TARGET, run_name="__main__")
