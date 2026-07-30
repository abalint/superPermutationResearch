#!/usr/bin/env python3
"""I3 (--recomp2) pair sizing from `tail-atsp --measure` TSVs.

SURGERY-DESIGN §10.5 staging step 2: count, per walk, the unordered
CROSS-CYCLE pairs of recomp-1 moves surviving each static prune tier,
BEFORE any solver work:

  T1   combined net-split ds_a + ds_b ∈ {−1, 0}       (M-R2 budget)
  T2   both moves in vocabulary — every arc length ≥ 2 (the n-generic
       form of {n, 2|4, 3|3, 2|2|2}; a 1-arc is the out-of-vocabulary
       tell, M-R1: 1|5 never naturally recomposed)
  T4   Λ-reducibility: ds_pair = −1 passes outright (S−1 ⇒ L−1);
       ds_pair = 0 needs a door delta, and M-R3 says junction-price
       deviations are doors entering the RECOMPOSED cycle ⇒ at least
       one paired cycle must be door-adjacent in the source walk.
       CALIBRATED operationalization, not a theorem — every verdict
       that uses it must say so.

Pair counts are exact but never enumerate pairs: moves are aggregated
into per-cycle class vectors keyed (ds, vocab, door); ordered-pair
totals are global-vector products minus same-cycle products, halved.

Usage: recomp2_sizing.py out/measure/*.tsv [--threshold 5000]
Exit 0 always (a sizing report, not a gate).
"""

import argparse
import collections
import statistics
import sys


def load(path):
    """-> {walk name: (tail_perms, blocks, {cycle: (door, {(ds,vocab): count})})}"""
    walks = {}
    with open(path) as f:
        header = f.readline().rstrip("\n").split("\t")
        assert header[:4] == ["name", "anchor_depth", "tail_perms", "blocks"], path
        for line in f:
            name, _ad, tp, blocks, cyc, door, ds, vocab, count = line.rstrip("\n").split("\t")
            tp, blocks = int(tp), int(blocks)
            _, _, cycles = walks.setdefault(name, (tp, blocks, {}))
            d, nc = cycles.setdefault(cyc, (door == "1", collections.Counter()))
            assert d == (door == "1")
            nc[(int(ds), vocab == "1")] += int(count)
    return walks


def pair_counts(cycles):
    """Exact unordered cross-cycle pair counts per tier."""
    # global class vector and same-cycle ordered-product correction
    A = collections.Counter()
    C = collections.Counter()  # (k1, k2) -> sum over cycles of N_c[k1]*N_c[k2]
    total = 0
    for door, nc in cycles.values():
        keys = [((ds, vocab, door), k) for (ds, vocab), k in nc.items()]
        for key, k in keys:
            A[key] += k
            total += k
        for k1, a in keys:
            for k2, b in keys:
                C[(k1, k2)] += a * b

    tiers = {"raw": 0, "t1": 0, "t12": 0, "t124": 0}
    keys = list(A)
    for k1 in keys:
        for k2 in keys:
            ordered = A[k1] * A[k2] - C.get((k1, k2), 0)
            if ordered == 0:
                continue
            (ds1, v1, d1), (ds2, v2, d2) = k1, k2
            tiers["raw"] += ordered
            if ds1 + ds2 not in (-1, 0):
                continue
            tiers["t1"] += ordered
            if not (v1 and v2):
                continue
            tiers["t12"] += ordered
            if ds1 + ds2 == -1 or d1 or d2:
                tiers["t124"] += ordered
    assert all(v % 2 == 0 for v in tiers.values())
    return total, {t: v // 2 for t, v in tiers.items()}


def selftest(path):
    """Brute-force cross-check of the aggregation identity on the
    smallest walk of `path`; exit 1 on any mismatch."""
    import itertools
    walks = load(path)
    name = min(walks, key=lambda w: sum(k for _, nc in walks[w][2].values() for k in nc.values()))
    _, _, cycles = walks[name]
    moves, tiers = pair_counts(cycles)
    expanded = []
    for cyc, (door, nc) in cycles.items():
        for (ds, vocab), k in nc.items():
            expanded.extend([(cyc, ds, vocab, door)] * k)
    assert len(expanded) == moves
    bf = dict(raw=0, t1=0, t12=0, t124=0)
    for (c1, ds1, v1, d1), (c2, ds2, v2, d2) in itertools.combinations(expanded, 2):
        if c1 == c2:
            continue
        bf["raw"] += 1
        if ds1 + ds2 not in (-1, 0):
            continue
        bf["t1"] += 1
        if not (v1 and v2):
            continue
        bf["t12"] += 1
        if ds1 + ds2 == -1 or d1 or d2:
            bf["t124"] += 1
    if bf != tiers:
        print(f"SELFTEST FAIL {name}: aggregated {tiers} != brute-force {bf}")
        return 1
    print(f"selftest OK: {name} ({moves} moves) aggregated == brute-force {tiers}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tsvs", nargs="+")
    ap.add_argument("--threshold", type=int, default=5000,
                    help="exact-solves-per-walk feasibility bar (§10.5)")
    ap.add_argument("--per-walk", action="store_true", help="print every walk, not just extremes")
    ap.add_argument("--selftest", action="store_true",
                    help="brute-force cross-check the pair aggregation on the first TSV's smallest walk")
    args = ap.parse_args()

    if args.selftest:
        return selftest(args.tsvs[0])

    for path in args.tsvs:
        walks = load(path)
        rows = []
        for name, (tp, blocks, cycles) in sorted(walks.items()):
            moves, tiers = pair_counts(cycles)
            rows.append((name, tp, blocks, len(cycles), moves, tiers))
        print(f"\n== {path} ({len(rows)} walks) ==")
        if args.per_walk:
            for name, tp, blocks, ncyc, moves, t in rows:
                print(f"  {name}: tail={tp} blocks={blocks} cycles={ncyc} moves={moves} "
                      f"raw={t['raw']} T1={t['t1']} T1∩T2={t['t12']} T1∩T2∩T4={t['t124']}")
        for tier in ("raw", "t1", "t12", "t124"):
            vals = [t[tier] for *_, t in rows]
            print(f"  {tier:>5}: median {statistics.median(vals):>12,.0f}   "
                  f"min {min(vals):>12,}   max {max(vals):>12,}")
        surv = [t["t124"] for *_, t in rows]
        ok = sum(1 for v in surv if v <= args.threshold)
        print(f"  verdict: {ok}/{len(surv)} walks at ≤ {args.threshold:,} T1∩T2∩T4 survivors "
              f"(median {statistics.median(surv):,.0f}; T4's ds=0 arm is the M-R3 "
              f"door-adjacency calibration, not a theorem)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
