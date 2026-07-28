#!/usr/bin/env python3
"""PC-side driver for Track C v2.1 within-state pair mining (stdlib only).

Runs `mine_subtrees.py --pairs` (design §3b) over the GEN2 logs and merges the
result into one gzipped pair corpus.

Why per-chain and not one global invocation: the miner holds a
`{(inst, shash): {col: rec}}` dict over every record it reads, and the gen2
sweep is ~10^8 records -- that will not fit in RAM.  Pairs require a shared
`inst`, so grouping the logs by chain and mining each chain separately yields
EXACTLY the same pair set as one global run (states from different chains can
never be compared), at 1/55 of the peak memory.

If the merged corpus exceeds --max-pairs, it is uniformly subsampled to that
size with a two-pass bitmap selection (no 6M-line list ever in memory).

usage (Windows):
  "C:\\Program Files\\Python311\\python.exe" tc2pairs.py ^
     --gen2 F:\\superpermFarm\\trackc2\\gen2 ^
     --miner F:\\superpermFarm\\trackc2\\mine_subtrees_pc.py ^
     --tmp F:\\superpermFarm\\trackc2\\pairtmp ^
     --out F:\\superpermFarm\\trackc2\\colpairs_gen2.jsonl.gz
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import random
import subprocess
import sys


def chain_of(path):
    """`wl_082_e15s3.jsonl` -> `wl_082`."""
    base = os.path.basename(path)
    if base.endswith(".jsonl"):
        base = base[: -len(".jsonl")]
    i = base.find("_e15s")
    return base[:i] if i > 0 else base


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gen2", required=True)
    ap.add_argument("--miner", required=True)
    ap.add_argument("--tmp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--max-pairs", type=int, default=6000000)
    ap.add_argument("--seed", type=int, default=20260728)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.gen2, "*.jsonl")))
    if not files:
        print("no gen2 logs matched", file=sys.stderr)
        return 1
    by_chain = {}
    for f in files:
        by_chain.setdefault(chain_of(f), []).append(f)
    os.makedirs(args.tmp, exist_ok=True)
    print("chains=%d logs=%d" % (len(by_chain), len(files)))

    shards = []
    total = 0
    by_src = {}
    by_chain_n = {}
    failed = []
    for ci, chain in enumerate(sorted(by_chain), 1):
        shard = os.path.join(args.tmp, "pairs_%s.jsonl" % chain)
        cmd = [args.python, args.miner, "--pairs", shard] + sorted(by_chain[chain])
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if r.returncode != 0 or not os.path.exists(shard):
            failed.append((chain, r.returncode, r.stdout.decode("utf8", "replace")[-400:]))
            print("  [%2d/%d] %-10s MINER FAILED rc=%d" % (ci, len(by_chain), chain, r.returncode))
            sys.stdout.flush()
            continue
        n = 0
        with open(shard) as fh:
            for line in fh:
                if not line.strip():
                    continue
                n += 1
                k = line.find('"src":"')
                src = line[k + 7: line.find('"', k + 7)] if k > 0 else "?"
                by_src[src] = by_src.get(src, 0) + 1
        shards.append(shard)
        total += n
        by_chain_n[chain] = n
        print("  [%2d/%d] %-10s logs=%d pairs=%d (running total %d)"
              % (ci, len(by_chain), chain, len(by_chain[chain]), n, total))
        sys.stdout.flush()

    print("TOTAL PAIRS MINED = %d" % total)
    print("by_src: " + json.dumps(by_src, sort_keys=True))
    if failed:
        print("MINER FAILURES: %d" % len(failed))
        for c, rc, tail in failed:
            print("  %s rc=%d :: %s" % (c, rc, tail.replace("\n", " | ")))

    # ---- uniform subsample to --max-pairs (two passes, bitmap selection) ----
    keep = None
    if total > args.max_pairs:
        rng = random.Random(args.seed)
        k = args.max_pairs
        invert = k > total // 2
        want = total - k if invert else k
        bits = bytearray((total + 7) // 8)
        got = 0
        while got < want:
            i = rng.randrange(total)
            if not (bits[i >> 3] >> (i & 7)) & 1:
                bits[i >> 3] |= 1 << (i & 7)
                got += 1
        keep = (bits, invert)
        print("subsampling %d -> %d (invert=%s)" % (total, k, invert))

    idx = 0
    written = 0
    out_src = {}
    tmpout = args.out + ".part"
    with gzip.open(tmpout, "wt", compresslevel=6) as out:
        for shard in shards:
            with open(shard) as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    if keep is not None:
                        bits, invert = keep
                        sel = bool((bits[idx >> 3] >> (idx & 7)) & 1)
                        if invert:
                            sel = not sel
                        idx += 1
                        if not sel:
                            continue
                    else:
                        idx += 1
                    out.write(line if line.endswith("\n") else line + "\n")
                    written += 1
                    k2 = line.find('"src":"')
                    s = line[k2 + 7: line.find('"', k2 + 7)] if k2 > 0 else "?"
                    out_src[s] = out_src.get(s, 0) + 1
    if os.path.exists(args.out):
        os.remove(args.out)
    os.rename(tmpout, args.out)

    print("pairs_written=%d" % written)
    print("written_by_src: " + json.dumps(out_src, sort_keys=True))
    print("by_chain: " + json.dumps(by_chain_n, sort_keys=True))
    print("wrote %s  %.1f MB" % (args.out, os.path.getsize(args.out) / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
