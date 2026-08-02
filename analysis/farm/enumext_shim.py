#!/usr/bin/env python3
"""enumext_shim.py -- run the s58 extended-census sweep under the farm
supervisor's contract, WITHOUT modifying enumext_sweep.py.

Same story as paircuts_shim.py: pysweep_run.ps1's TARGET must live under $ROOT
(F:\\superpermFarm\\untargeted), while enumext_sweep.py derives its repo root
from its own __file__ and so must stay in the repo mirror.  This supplies the
bridge and nothing else -- the instrument already speaks
--shard/--out/--limit/--dry-run and already writes the STATUS heartbeat.

Deliberately NOT shimmed, verified against untargeted_super.ps1's scanner:
  * alarms already work -- the instrument prints, with flush=True,
      `*** SHARD n CAPPED at N nodes -- coverage is INCOMPLETE ...`
      `*** SHARD n: k chain(s) using a generalized door ... OUTSIDE the census frame ***`
    and the supervisor banners on `\\*\\*\\*`.  The CAPPED banner matters most:
    a capped shard is not a negative result, and silence there would read as
    "swept clean".
  * its healthy summary is
      `shard i/N: subtrees=... nodes=... EXHAUSTED chains=5 pivbreak=0 gen=0 ...`
    Checked against the supervisor regex
    `Traceback|MemoryError|^\\s*!!|\\*\\*\\*|ESCAPES\\s+[1-9]|NOVEL[^:\\r\\n]*:\\s*[1-9]`
    -- no substring matches, so a healthy shard never self-banners (the s52b
    trap, where demotion.py's ordinary "novel-candidate classes: 0" bannered
    all 24 healthy shards).
  * `enumext_stats_*.tsv` is picked up by the supervisor's `(?i)stat` counter;
    `enumext_chains_*.tsv` is small by construction (one row per chain found).

usage: upyw.exe -u enumext_shim.py --shard 0/24 --out F:\\...\\s00 --pmax 16
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(HERE, "repo", "analysis", "counting", "s58"),
             os.path.join(HERE, "..", "counting", "s58")):
    if os.path.isdir(cand):
        TARGET = os.path.join(os.path.abspath(cand), "enumext_sweep.py")
        break
else:
    print("enumext_shim: cannot locate enumext_sweep.py", file=sys.stderr)
    sys.exit(2)

# a leading bare token would be pysweep_run.ps1's -Mode; this instrument has no
# subcommand, so drop one if present rather than letting argparse choke on it
if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    del sys.argv[1]
sys.argv[0] = TARGET
runpy.run_path(TARGET, run_name="__main__")
