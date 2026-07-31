#!/usr/bin/env python3
"""untargeted_stub.py -- a trivial stand-in for `fuse.py untargeted`, used to
exercise the farm supervisor's MECHANICS without the instrument.

It honours the same CLI contract the harness assumes
    --shard i/N   --out <dir>   [--limit K]   [--dry-run]
and produces the same three artefacts in <dir>:
    STATUS        one appended line per "intermediate" (the heartbeat)
    *_stats.tsv   a stats TSV
    *_edges.tsv   an edges TSV

Test hooks.  They are SHARD-INDEXED so one global -ExtraArgs string drives the
whole 24-way mechanics test (the supervisor passes -ExtraArgs to every shard):
    --stall-shard I   shard I stops appending to STATUS after 2 intermediates
                      but keeps running -- must be caught by the supervisor's
                      stall detector and FLAGGED in the ledger, not ignored
    --fail-shard I    shard I exits 3 after 2 intermediates -- must land in the
                      ledger with rc=3 (proves exit codes survive detach.exe,
                      which cannot report them itself)
    --banner-shard I  shard I prints '*** NOVEL ***' -- must raise ALARM.txt
    --sleep S         seconds per intermediate (default 1.0)

usage: upyw.exe -u untargeted_stub.py --shard 0/24 --out F:\\...\\out\\s00
"""
import argparse
import os
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stall-shard", type=int, default=-1)
    ap.add_argument("--fail-shard", type=int, default=-1)
    ap.add_argument("--banner-shard", type=int, default=-1)
    ap.add_argument("--sleep", type=float, default=1.0)
    a = ap.parse_args()

    i, n = (int(x) for x in a.shard.split("/"))
    stall_after = 2 if i == a.stall_shard else 0
    fail_after = 2 if i == a.fail_shard else 0
    banner = (i == a.banner_shard)
    os.makedirs(a.out, exist_ok=True)
    total = a.limit if a.limit > 0 else 10

    # numpy is imported on purpose: the stub must fail farm-side for the same
    # reason the instrument would if the venv were wrong.
    import numpy as np
    _ = np.arange(4).sum()

    print(f"stub shard {i}/{n} -> {a.out}  total={total}  numpy={np.__version__}",
          flush=True)
    if a.dry_run:
        print(f"DRY RUN: shard {i}/{n} would process {total} intermediates",
              flush=True)
        return 0

    st = os.path.join(a.out, "STATUS")
    stats = os.path.join(a.out, f"untargeted_stats_s{i:02d}.tsv")
    edges = os.path.join(a.out, f"untargeted_edges_s{i:02d}.tsv")
    with open(stats, "w") as fh:
        fh.write("shard\tintermediate\tr2_instances\treplays\thits\tsec\n")
    with open(edges, "w") as fh:
        fh.write("source\tproduct_sha256\trule1\tsigma1\trule2\tsigma2\n")

    # The heartbeat's first line declares the shard total -- the supervisor
    # parses it and prefers it over the corpus-wide projection.
    with open(st, "a") as fh:
        fh.write(f"shard {i}/{n} start total={total} "
                 f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    t0 = time.time()
    for k in range(total):
        time.sleep(a.sleep)
        if fail_after and k + 1 >= fail_after:
            print(f"stub shard {i}: deliberate failure at intermediate {k+1}",
                  file=sys.stderr, flush=True)
            return 3
        if stall_after and k + 1 > stall_after:
            # alive, burning time, heartbeat frozen: the stall case.  Deliberately
            # much slower than a healthy shard so the supervisor's stall window
            # actually elapses while the process is still running.
            time.sleep(a.sleep * 8)
            continue
        with open(st, "a") as fh:
            fh.write(f"intermediate {k+1}/{total} r2=448 "
                     f"{time.strftime('%H:%M:%S')}\n")
        with open(stats, "a") as fh:
            fh.write(f"{i}\t{k+1}\t448\t448\t0\t{a.sleep:.2f}\n")
        if k % 3 == 0:
            with open(edges, "a") as fh:
                fh.write(f"stub{i}\t{'0'*64}\tR-K7\t{k}\tS51A\t{k}\n")
        print(f"  shard {i} intermediate {k+1}/{total}", flush=True)

    if banner:
        print("*** NOVEL 5906 CLASS (stub banner) ***", flush=True)

    print(f"stub shard {i}/{n} DONE {total} intermediates "
          f"in {time.time()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
