#!/usr/bin/env python3
"""Recomposition census over cross-allocation specimen pairs (s29, I2 design input).

Input: the pairs TSV emitted by surgery_pairs.py (file1 alloc1 file2 alloc2
deepest_shared ...). For every pair, both walks are byte-identical to the
shared depth, so any per-cycle split-composition difference lives strictly in
the tails. This script:

  pass A — per pair: full-walk per-cycle compositions (part lengths, in visit
           order) for both sides; diff; classify each recomposed cycle by its
           unordered composition pair (e.g. 6 <-> 3|3); price the junctions
           (sum of part-entry move weights) around each recomposed cycle.
  pass B — corpus aggregate: recomposition-type histogram, junction-price
           deltas per type, and the per-pair recomposed/total-cycle counts.

Usage: recomp_census.py <pairs.tsv> [--details] [--pair FILE1,FILE2]
"""

import itertools
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "upstream872"
N = 6
RANK = {"".join(p): i for i, p in enumerate(itertools.permutations("123456"))}
PERM = {i: p for p, i in RANK.items()}


def walk_of(name):
    s = (ARCHIVE / name).read_text().strip()
    seen, out = set(), []
    for i in range(len(s) - N + 1):
        r = RANK.get(s[i : i + N])
        if r is None or r in seen:
            continue
        seen.add(r)
        out.append((r, i + N))
    return out


def cyc(r):
    p = PERM[r]
    return min(p[i:] + p[:i] for i in range(N))


def cycle_parts(walk):
    """Per-cycle list of parts in visit order: (len, entry_w, exit_w, depth0).

    A part = maximal run of same-cycle weight-1 moves (w1 never changes
    cycle). entry_w = weight of the move that opened the part (None for the
    walk's first part), exit_w = weight of the move that closed it (None at
    walk end). depth0 = 1-based depth of the part's first perm.
    """
    parts = defaultdict(list)
    cur_c, plen, entry, d0, er = cyc(walk[0][0]), 1, None, 1, walk[0][0]
    for d, ((r1, p1), (r2, p2)) in enumerate(zip(walk, walk[1:]), 1):
        w = p2 - p1
        if w == 1:
            plen += 1
        else:
            parts[cur_c].append((plen, entry, w, d0, er))
            cur_c, plen, entry, d0, er = cyc(r2), 1, w, d + 1, r2
    parts[cur_c].append((plen, entry, None, d0, er))
    return parts


def comp_of(parts_list):
    return tuple(sorted(p[0] for p in parts_list))


def fmt_comp(comp):
    return "|".join(str(x) for x in comp) if comp else "-"


def fmt_parts(parts_list):
    return " ".join(
        f"[{'^' if e is None else 'w%d' % e}>{PERM[er]}:{ln}@{d0}>{'$' if x is None else 'w%d' % x}]"
        for ln, e, x, d0, er in parts_list
    )


def censor_pair(f1, f2, anchor, details=False):
    w1, w2 = walk_of(f1), walk_of(f2)
    p1, p2 = cycle_parts(w1), cycle_parts(w2)
    assert set(p1) == set(p2), "both are full covers; cycle sets must match"
    recomps = []
    entry_nested = entry_total = 0
    for c in p1:
        c1, c2 = comp_of(p1[c]), comp_of(p2[c])
        if c1 != c2:
            # junction price = sum of entry weights over the cycle's parts
            # (walk-start entries count 0; they are the identity opening)
            j1 = sum(e for _, e, _, _, _ in p1[c] if e)
            j2 = sum(e for _, e, _, _, _ in p2[c] if e)
            # depth of the cycle's first recomposition-relevant part
            dmin = min(d0 for _, _, _, d0, _ in p1[c] + p2[c])
            recomps.append((c, c1, c2, j1, j2, dmin))
            # entry-point nesting: is the coarser side's part-entry perm set
            # a subset of the finer side's? (bounds I2 branching: split points
            # reuse the whole side's entry)
            e1 = {er for _, _, _, _, er in p1[c]}
            e2 = {er for _, _, _, _, er in p2[c]}
            lo, hi = (e1, e2) if len(e1) <= len(e2) else (e2, e1)
            entry_total += 1
            if lo <= hi:
                entry_nested += 1
    tail_cycles = {
        c
        for c, lst in p1.items()
        if any(d0 + ln - 1 >= anchor for ln, _, _, d0, _ in lst)
    } | {
        c
        for c, lst in p2.items()
        if any(d0 + ln - 1 >= anchor for ln, _, _, d0, _ in lst)
    }
    if details:
        for c, c1, c2, j1, j2, dmin in sorted(recomps, key=lambda t: t[5]):
            print(f"    {c}: {fmt_comp(c1)} <-> {fmt_comp(c2)}  junction {j1} vs {j2}")
            print(f"      A: {fmt_parts(p1[c])}")
            print(f"      B: {fmt_parts(p2[c])}")
    # net splits: (parts in side2) - (parts in side1) over recomposed cycles;
    # must equal S2 - S1 if recompositions fully account for the S delta
    net = sum(len(c2) - len(c1) for _, c1, c2, _, _, _ in recomps)
    return recomps, len(tail_cycles), net, entry_nested, entry_total


def main():
    pairs_tsv = sys.argv[1]
    details = "--details" in sys.argv
    only = None
    if "--pair" in sys.argv:
        only = set(sys.argv[sys.argv.index("--pair") + 1].split(","))

    rows = []
    with open(pairs_tsv) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        fi = {c: i for i, c in enumerate(header)}
        for line in fh:
            f = line.rstrip("\n").split("\t")
            rows.append(
                (
                    f[fi["file1"]],
                    f[fi["alloc1"]],
                    f[fi["file2"]],
                    f[fi["alloc2"]],
                    int(f[fi["deepest_shared"]]),
                )
            )

    type_hist = Counter()
    type_jdelta = defaultdict(list)
    print(
        "file1\talloc1\tfile2\talloc2\tanchor\ttail_cycles\trecomposed"
        "\tnet_splits\tdS\tentry_nested\ttypes"
    )
    for f1, a1, f2, a2, anchor in rows:
        if only and {f1, f2} != only:
            continue
        if details:
            print(f"-- {f1} ({a1})  x  {f2} ({a2})  anchor {anchor}")
        recomps, ntail, net, en, et = censor_pair(f1, f2, anchor, details=details)
        ds = int(a2.split(",")[0]) - int(a1.split(",")[0])
        tset = Counter()
        for c, c1, c2, j1, j2, dmin in recomps:
            t = tuple(sorted((c1, c2)))
            tset[t] += 1
            type_hist[t] += 1
            # junction delta oriented low-comp -> high-comp for consistency
            lo, hi = (c1, j1), (c2, j2)
            if tuple(sorted((c1, c2)))[0] != c1:
                lo, hi = hi, lo
            type_jdelta[t].append(hi[1] - lo[1])
        tstr = " ".join(
            f"{fmt_comp(t[0])}<->{fmt_comp(t[1])}x{k}" for t, k in sorted(tset.items())
        )
        print(
            f"{f1}\t{a1}\t{f2}\t{a2}\t{anchor}\t{ntail}\t{len(recomps)}"
            f"\t{net}\t{ds}\t{en}/{et}\t{tstr or '-'}"
        )

    print("\n# recomposition-type vocabulary (all pairs):")
    for t, k in type_hist.most_common():
        hist = Counter(type_jdelta[t])
        hstr = " ".join(f"{d:+d}x{c}" for d, c in sorted(hist.items()))
        print(
            f"#   {fmt_comp(t[0])} <-> {fmt_comp(t[1])}: {k} events, "
            f"junction-delta histogram (first-listed minus other): {hstr}"
        )


if __name__ == "__main__":
    main()
