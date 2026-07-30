#!/usr/bin/env python3
"""Find natural cross-allocation surgery specimens (s28).

surgery_feasibility.py found that walks from different L0 allocations share
braid states — and one pair, (142,6,0,0,0) x (143,5,0,0,0), shares states to
depth 584.  A cross-allocation pair sharing MOST of its path is a walk pair
where nature already performed an allocation-changing edit: diffing them
shows exactly what a legal door-demotion / sojourn-merge surgery looks like.

For each cross-allocation pair of walks that share at least one state deeper
than --min-depth, report: shared-state count, first divergence depth, last
shared depth, and the visited-set symmetric difference at the deepest shared
state's depth... more usefully, for the TOP pairs, a full edit-region map:
maximal shared prefix (in states), the divergence window(s), and the partial
ledger (S, d3, d4, w-hist) of each walk inside each window.

Usage: python3 analysis/trackb/surgery_specimens.py [--pair 142,6,0,0,0 143,5,0,0,0]
"""

import argparse
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
    """First-visit path: list of (rank, prefix_len). Also the weight sequence."""
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


def state_keys(walk):
    """Sequence of hashable states (frozen visited via running tuple-hash is
    wrong; use incremental frozenset surrogate: cumulative sorted tuple is
    O(n^2) — instead pair (cur, depth, prefix_len) is NOT unique enough, so
    hash the growing bitmask)."""
    import hashlib

    mask = bytearray(90)
    keys = []
    for r, plen in walk:
        mask[r >> 3] |= 1 << (r & 7)
        h = hashlib.blake2b(bytes(mask) + r.to_bytes(2, "little"), digest_size=12).digest()
        keys.append((h, plen))
    return keys


def weight_seq(walk):
    """Weight of each transition between consecutive first visits."""
    w = []
    for (r1, p1), (r2, p2) in zip(walk, walk[1:]):
        w.append(p2 - p1)
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, default=["142,6,0,0,0", "143,5,0,0,0"])
    ap.add_argument("--min-depth", type=int, default=400)
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()

    alloc_of = load_allocs()
    a1, a2 = args.pair
    files1 = sorted(f for f, a in alloc_of.items() if a == a1)
    files2 = sorted(f for f, a in alloc_of.items() if a == a2)
    print(f"# {a1}: {len(files1)} classes; {a2}: {len(files2)} classes", file=sys.stderr)

    # Index deep states of side 1: digest -> list of (file_idx, depth)
    idx = defaultdict(list)
    walks1 = {}
    for i, f in enumerate(files1):
        w = walk_of(ARCHIVE / f)
        walks1[f] = w
        for d, (h, plen) in enumerate(state_keys(w), 1):
            if d >= args.min_depth:
                idx[h].append((f, d))
        if (i + 1) % 100 == 0:
            print(f"  indexed {i + 1}/{len(files1)}", file=sys.stderr)

    # Scan side 2, score pairs by number of shared deep states.
    pair_shared = defaultdict(list)  # (f1, f2) -> [depth,...]
    for j, f2 in enumerate(files2):
        w = walk_of(ARCHIVE / f2)
        for d, (h, plen) in enumerate(state_keys(w), 1):
            if d >= args.min_depth and h in idx:
                for f1, d1 in idx[h]:
                    assert d1 == d, "equal visited-set size forces equal depth"
                    pair_shared[(f1, f2)].append(d)
        if (j + 1) % 200 == 0:
            print(f"  scanned {j + 1}/{len(files2)}", file=sys.stderr)

    ranked = sorted(pair_shared.items(), key=lambda kv: -len(kv[1]))
    print(f"pairs sharing a state at depth >= {args.min_depth}: {len(ranked)}")
    for (f1, f2), depths in ranked[: args.top]:
        w1, w2 = walks1[f1], walk_of(ARCHIVE / f2)
        k1, k2 = state_keys(w1), state_keys(w2)
        shared = [d for d in range(1, 721) if k1[d - 1][0] == k2[d - 1][0]]
        sset = set(shared)
        # divergence windows = maximal runs of depths NOT shared
        windows = []
        d = 1
        while d <= 720:
            if d not in sset:
                start = d
                while d <= 720 and d not in sset:
                    d += 1
                windows.append((start, d - 1))
            else:
                d += 1
        ws1, ws2 = weight_seq(w1), weight_seq(w2)
        print(f"\n=== {f1} ({a1})  x  {f2} ({a2})")
        print(f"  shared states: {len(shared)}/720; windows of divergence: {windows}")
        for lo, hi in windows:
            # weights spent inside the window (transitions from depth lo-1..hi)
            seg1 = ws1[max(lo - 2, 0) : hi]
            seg2 = ws2[max(lo - 2, 0) : hi]
            print(f"  window {lo}-{hi}: len={hi - lo + 1}")
            print(f"    {a1} weights: {seg1}")
            print(f"    {a2} weights: {seg2}")


if __name__ == "__main__":
    main()
