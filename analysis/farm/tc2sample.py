#!/usr/bin/env python3
"""PC-side reservoir sampler for Track C v2 subtree logs (stdlib only).

The farm's `gen\\*.jsonl` logs are ~150-250 MB each (~35 GB per sweep) -- far
too big to scp home.  This walks the finished logs, keeps a uniform reservoir
sample of at most --per-file records from each, and writes ONE gzipped JSONL.

"Finished" = a done-marker `<done-dir>\\<jid>.done` exists for `<jid>.jsonl`
(the sweep worker writes the marker only after the engine exited), so a log
still being appended to is never sampled.

Every kept record gets a `"run"` key (the job id) so the combined sample stays
traceable; nothing else about the record is altered.

usage (Windows):
  "C:\\Program Files\\Python311\\python.exe" tc2sample.py ^
      --gen F:\\superpermFarm\\trackc2\\gen ^
      --done F:\\superpermFarm\\trackc2\\done ^
      --out F:\\superpermFarm\\trackc2\\coleffort_sweep1_sample.jsonl.gz
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import random
import sys

REQUIRED = ("depth", "cand", "col", "feats", "subtree", "outcome")


def sample_file(path, k, seed):
    """Reservoir-sample <= k parseable records from `path`. -> (kept, n, bad)."""
    rng = random.Random("%d:%s" % (seed, os.path.basename(path)))
    res = []
    n = 0
    bad = 0
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if not isinstance(rec, dict) or any(f not in rec for f in REQUIRED):
                bad += 1
                continue
            n += 1
            if len(res) < k:
                res.append(rec)
            else:
                j = rng.randrange(n)
                if j < k:
                    res[j] = rec
    return res, n, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gen", required=True, help="directory of *.jsonl engine logs")
    ap.add_argument("--out", required=True, help="output path (.jsonl.gz)")
    ap.add_argument("--done", help="done-marker dir; only finished jobs sampled")
    ap.add_argument("--done-prefix", default="",
                    help="job-id prefix if markers are <prefix><logname>.done "
                         "(gen2 logs are <chain>_e15sN.jsonl but the job ids are "
                         "g2_<chain>_e15sN, so pass --done-prefix g2_)")
    ap.add_argument("--per-file", type=int, default=30000)
    ap.add_argument("--seed", type=int, default=20260728)
    ap.add_argument("--pattern", default="*.jsonl")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.gen, args.pattern)))
    if not files:
        print("no logs matched", file=sys.stderr)
        return 1

    total_in = total_kept = total_bad = 0
    skipped = []
    used = []
    tmp = args.out + ".part"
    with gzip.open(tmp, "wt", compresslevel=6) as out:
        for path in files:
            jid = os.path.basename(path)[: -len(".jsonl")]
            marker = os.path.join(args.done, args.done_prefix + jid + ".done") \
                if args.done else None
            if marker and not os.path.exists(marker):
                skipped.append(jid)
                continue
            recs, n, bad = sample_file(path, args.per_file, args.seed)
            for r in recs:
                r["run"] = jid
                out.write(json.dumps(r, separators=(",", ":")) + "\n")
            total_in += n
            total_kept += len(recs)
            total_bad += bad
            used.append(jid)
            if not args.quiet:
                print("  %-24s records=%-10d kept=%-7d bad=%d"
                      % (jid, n, len(recs), bad))
                sys.stdout.flush()
    if os.path.exists(args.out):
        os.remove(args.out)
    os.rename(tmp, args.out)

    size = os.path.getsize(args.out)
    print("files_sampled=%d files_skipped_unfinished=%d" % (len(used), len(skipped)))
    if skipped:
        print("skipped: " + " ".join(skipped))
    print("records_scanned=%d records_kept=%d records_rejected=%d"
          % (total_in, total_kept, total_bad))
    print("wrote %s  %.1f MB" % (args.out, size / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
