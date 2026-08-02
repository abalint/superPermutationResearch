#!/usr/bin/env python3
"""paircuts_shim.py -- run the s58 pairwise cut store under the farm
supervisor's contract, WITHOUT modifying paircuts.py.

pysweep_run.ps1 launches every shard as

    upyw.exe -u <TARGET> [<Mode>] --shard i/N --out <dir> [--limit K] [--dry-run] <ExtraArgs>

and TARGET must live under $ROOT (F:\\superpermFarm\\untargeted), not in the
repo mirror.  paircuts.py already speaks --shard/--out/--limit/--dry-run and
already writes the STATUS heartbeat the supervisor reads, so unlike
promote_shim.py this needs no argument rewriting and no heartbeat wrapper --
the only thing it supplies is the repo-relative import root, which
paircuts.py derives from its own __file__ (three dirnames up) and would
therefore get wrong if it were copied to $ROOT.

Deliberately NOT shimmed, verified against untargeted_super.ps1's scanner:
  * the alarm path already works -- paircuts.py prints `*** JACKPOT ...`,
    `*** RECONFIRM FAIL ...` and `*** SOUNDNESS VIOLATION ...` with
    flush=True, and the supervisor banners on `\\*\\*\\*`.
  * its normal end-of-shard summary is `... NOGOODS <n> unknown=<n> ...`.
    Checked against the supervisor regex
    `Traceback|MemoryError|^\\s*!!|\\*\\*\\*|ESCAPES\\s+[1-9]|NOVEL[^:\\r\\n]*:\\s*[1-9]`
    -- "NOGOODS 54" does NOT match `NOVEL...: [1-9]` (different word, and the
    regex needs a colon), so a healthy shard never self-banners.  That is the
    s52b bug this check exists to avoid repeating.
  * `*_stats_*.tsv` is picked up by the supervisor's `(?i)stat` TSV counter.
    The no-good store is `.jsonl`, deliberately: the supervisor's `(?i)edge`
    and `(?i)stat` counters only read `.tsv`, so the multi-MB store is never
    line-counted on a tick.

usage: upyw.exe -u paircuts_shim.py --shard 0/24 --out F:\\...\\s00 --spec farm0
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(HERE, "repo", "analysis", "counting", "s58"),
             os.path.join(HERE, "..", "counting", "s58")):
    if os.path.isdir(cand):
        TARGET = os.path.join(os.path.abspath(cand), "paircuts.py")
        break
else:
    print("paircuts_shim: cannot locate paircuts.py", file=sys.stderr)
    sys.exit(2)

# a leading bare token would be pysweep_run.ps1's -Mode; this instrument has no
# subcommand, so drop one if present rather than letting argparse choke on it
if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    del sys.argv[1]
sys.argv[0] = TARGET
runpy.run_path(TARGET, run_name="__main__")
