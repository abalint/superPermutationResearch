#!/usr/bin/env python3
"""All-pairs cross-allocation specimen census (s28, follows surgery_specimens.py).

Two passes over data/upstream872:
  pass 1 — digest every braid state at depth >= --min-depth, keep digests
           seen by >= 2 allocations;
  pass 2 — for those digests, collect the (file, depth) hits and emit, for
           every cross-allocation FILE pair, the deepest shared state.

Then for each reported pair: tail ledger delta (sojourn boundaries = #w>=2,
doors = #w>=3 by weight) of the two re-covers of the same residual set.

Output: TSV to stdout, ranked by shared depth.
"""

import hashlib
import itertools
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "upstream872"
STRUCTURE = ROOT / "analysis" / "counting" / "upstream872_structure.tsv"

N = 6
PERMS = ["".join(p) for p in itertools.permutations("123456")]
RANK = {p: i for i, p in enumerate(PERMS)}
MIN_DEPTH = int(sys.argv[1]) if len(sys.argv) > 1 else 250


def load_allocs():
    rows = {}
    with open(STRUCTURE) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        fi = {c: i for i, c in enumerate(header)}
        for line in fh:
            f = line.rstrip("\n").split("\t")
            rows[f[fi["file"]]] = ",".join(
                (f[fi["S"]], f[fi["d3"]], f[fi["d4"]], f[fi["d5"]], f[fi["ip"]])
            )
    return rows


def walk_of(path):
    s = path.read_text().strip()
    seen = set()
    out = []
    for i in range(len(s) - N + 1):
        r = RANK.get(s[i : i + N])
        if r is None or r in seen:
            continue
        seen.add(r)
        out.append((r, i + N))
    return out


def digests(walk, min_depth):
    mask = bytearray(90)
    for d, (r, plen) in enumerate(walk, 1):
        mask[r >> 3] |= 1 << (r & 7)
        if d >= min_depth:
            yield d, hashlib.blake2b(
                bytes(mask) + r.to_bytes(2, "little"), digest_size=12
            ).digest()


def main():
    alloc_of = load_allocs()
    files = sorted(ARCHIVE.glob("*.txt"))

    # pass 1: digest -> set of allocs (only keep digests, cheaply)
    seen_alloc = {}
    cross = set()
    for k, p in enumerate(files):
        a = alloc_of[p.name]
        for d, h in digests(walk_of(p), MIN_DEPTH):
            prev = seen_alloc.get(h)
            if prev is None:
                seen_alloc[h] = a
            elif prev != a:
                cross.add(h)
        if (k + 1) % 2000 == 0:
            print(f"pass1 {k + 1}/{len(files)} cross={len(cross)}", file=sys.stderr)
    del seen_alloc
    print(f"# cross-allocation states at depth >= {MIN_DEPTH}: {len(cross)}", file=sys.stderr)

    # pass 2: collect files touching those states
    hits = defaultdict(list)  # digest -> [(file, depth)]
    for k, p in enumerate(files):
        w = walk_of(p)
        for d, h in digests(w, MIN_DEPTH):
            if h in cross:
                hits[h].append((p.name, d))
        if (k + 1) % 2000 == 0:
            print(f"pass2 {k + 1}/{len(files)}", file=sys.stderr)

    # deepest shared state per cross-allocation file pair
    best = {}
    for h, lst in hits.items():
        d = lst[0][1]
        for (f1, _), (f2, _) in itertools.combinations(lst, 2):
            if alloc_of[f1] == alloc_of[f2]:
                continue
            key = (f1, f2) if f1 < f2 else (f2, f1)
            if best.get(key, 0) < d:
                best[key] = d

    print("file1\talloc1\tfile2\talloc2\tdeepest_shared\ttail1_w2\ttail1_w3+\ttail2_w2\ttail2_w3+")
    for (f1, f2), d in sorted(best.items(), key=lambda kv: -kv[1]):
        w1, w2 = walk_of(ARCHIVE / f1), walk_of(ARCHIVE / f2)
        ws1 = [b - a for (_, a), (_, b) in zip(w1[d - 1 :], w1[d:])]
        ws2 = [b - a for (_, a), (_, b) in zip(w2[d - 1 :], w2[d:])]
        t1w2 = sum(1 for w in ws1 if w == 2)
        t1w3 = sum(1 for w in ws1 if w >= 3)
        t2w2 = sum(1 for w in ws2 if w == 2)
        t2w3 = sum(1 for w in ws2 if w >= 3)
        print(
            f"{f1}\t{alloc_of[f1]}\t{f2}\t{alloc_of[f2]}\t{d}\t{t1w2}\t{t1w3}\t{t2w2}\t{t2w3}"
        )


if __name__ == "__main__":
    main()
