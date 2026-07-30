#!/usr/bin/env python3
"""Surgery-design feasibility measurements (s28, HANDOFF-S28 item 1).

Question 1 (braid-diff viability): do walks from DIFFERENT L0 allocations
share braid states at all — and if so, down to what depth?  Braid state =
(visited set, current perm), exactly src/recomb.rs::Braid's node key.

Question 2 (free-improvement check, cross-allocation): is any shared state
reached at DIFFERENT prefix lengths by walks from different allocations?
s26 measured equal-prefix-length sharing within the 296-record sample; a
cross-allocation unequal-length reconvergence would splice directly to an
871.  This re-proves (or refutes) it on all 22,062 classes.

Question 3 (door-band context): depth histogram of cross-allocation shared
states vs the midgame door band (~60–450) where the non-records
allocations spend their extra doors.

Input: data/upstream872/ (forward-renumbered class representatives) +
analysis/counting/upstream872_structure.tsv (file -> allocation).
Output: TSV summary to stdout; run from the repo root.
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
NFACT = len(PERMS)
MASK_BYTES = (NFACT + 7) // 8


def alloc_of_rows():
    rows = {}
    with open(STRUCTURE) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        fi = {c: i for i, c in enumerate(header)}
        for line in fh:
            f = line.rstrip("\n").split("\t")
            key = (f[fi["S"]], f[fi["d3"]], f[fi["d4"]], f[fi["d5"]], f[fi["ip"]])
            rows[f[fi["file"]]] = ",".join(key)
    return rows


def first_visit_states(s):
    """Yield (depth, rank, prefix_len_chars) along the first-visit path."""
    seen = set()
    d = 0
    for i in range(len(s) - N + 1):
        w = s[i : i + N]
        r = RANK.get(w)
        if r is None or r in seen:
            continue
        seen.add(r)
        d += 1
        yield d, r, i + N


def main():
    alloc_of = alloc_of_rows()
    allocs = sorted(set(alloc_of.values()))
    abit = {a: 1 << i for i, a in enumerate(allocs)}
    print(f"# allocations: {allocs}", file=sys.stderr)

    # digest -> [alloc_flags, min_len, max_len]  (depth recomputed via first hit)
    states = {}
    depth_of = {}  # digest -> depth (same for all visits: |visited| determines it)

    files = sorted(ARCHIVE.glob("*.txt"))
    if len(files) != len(alloc_of):
        print(f"WARNING: {len(files)} files vs {len(alloc_of)} structure rows", file=sys.stderr)

    for k, path in enumerate(files):
        a = abit[alloc_of[path.name]]
        s = path.read_text().strip()
        mask = bytearray(MASK_BYTES)
        for d, r, plen in first_visit_states(s):
            mask[r >> 3] |= 1 << (r & 7)
            h = hashlib.blake2b(bytes(mask) + r.to_bytes(2, "little"), digest_size=12).digest()
            rec = states.get(h)
            if rec is None:
                states[h] = [a, plen, plen]
                depth_of[h] = d
            else:
                rec[0] |= a
                if plen < rec[1]:
                    rec[1] = plen
                if plen > rec[2]:
                    rec[2] = plen
        if (k + 1) % 2000 == 0:
            print(f"  {k + 1}/{len(files)} walks, {len(states)} states", file=sys.stderr)

    total = len(states)
    multi_alloc = {h: v for h, v in states.items() if bin(v[0]).count("1") >= 2}
    unequal = {h: v for h, v in states.items() if v[1] != v[2]}
    unequal_cross = {h: v for h, v in unequal.items() if bin(v[0]).count("1") >= 2}

    print(f"total braid states\t{total}")
    print(f"states shared by >=2 allocations\t{len(multi_alloc)}")
    print(f"states with unequal prefix lengths (ANY)\t{len(unequal)}")
    print(f"states with unequal prefix lengths (cross-allocation)\t{len(unequal_cross)}")

    # Pairwise sharing counts + max shared depth per pair.
    pair_count = defaultdict(int)
    pair_maxdepth = defaultdict(int)
    for h, v in multi_alloc.items():
        members = [a for a in allocs if v[0] & abit[a]]
        d = depth_of[h]
        for x, y in itertools.combinations(members, 2):
            pair_count[(x, y)] += 1
            if d > pair_maxdepth[(x, y)]:
                pair_maxdepth[(x, y)] = d
    print("\npair\tshared_states\tmax_shared_depth")
    for (x, y), c in sorted(pair_count.items(), key=lambda kv: -kv[1]):
        print(f"{x} x {y}\t{c}\t{pair_maxdepth[(x, y)]}")

    # Depth histogram (deciles of 720) for cross-allocation shared states.
    hist = defaultdict(int)
    for h in multi_alloc:
        hist[min(depth_of[h] * 10 // 720, 9)] += 1
    print("\ndepth_decile\tcross_alloc_shared_states")
    for dec in range(10):
        print(f"{dec}\t{hist.get(dec, 0)}")

    # The interesting anomalies, in full.
    if unequal_cross:
        print("\nUNEQUAL-LENGTH CROSS-ALLOCATION STATES (splice candidates!):")
        for h, v in sorted(unequal_cross.items(), key=lambda kv: kv[1][1]):
            members = [a for a in allocs if v[0] & abit[a]]
            print(f"  depth={depth_of[h]} len={v[1]}..{v[2]} allocs={members}")


if __name__ == "__main__":
    main()
