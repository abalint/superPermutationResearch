#!/usr/bin/env python3
"""M-2 (s36, SURGERY-DESIGN §10.3): recomposition CO-OCCURRENCE census —
the pre-build measurement for the I3 pair enumerator.

Input: the controlled-pair TSV from surgery_pairs.py (both walks
byte-identical to the shared depth, so composition diffs live in the
tails). Questions, per §10.3:

  M-2a  Joint locality: for every unordered pair of recomposed cycles
        inside one controlled pair — do they share a USED 2-loop (a
        2-loop some w2 edge of either walk lies on, containing parts of
        both)? a STATIC 2-loop (any of the 144)? are they directly
        adjacent (consecutive parts in either walk)? door-linked (a
        w>=3 transition between them)? how far apart in first-part
        depth? Null model: the same measures over all tail-cycle pairs
        of the same controlled pairs.
  M-2b  Minimal-flux pairs: controlled pairs with the fewest recomposed
        cycles — the closest nature gets to a minimal compound; their
        full type multisets and locality flags.
  M-2c  The natural (142,6)x(143,5) unit pairs: full joint autopsy.

Usage: recomp_cooccur.py <pairs.tsv> [--min-flux K]
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/trackb")
from recomp_census import PERM, censor_pair, cyc, cycle_parts, walk_of  # noqa: E402

N = 6


def rot(p):
    return p[1:] + p[0]


def g(p):  # jump-composed map (string perms), n-generic form
    return p[1 : N - 1] + p[0] + p[N - 1]


def loop_id(p):
    orb = [p]
    for _ in range(N - 2):
        orb.append(g(orb[-1]))
    return min(orb)


def static_loop_cycles():
    """loop_id -> frozenset of the (n-1) 1-cycles it covers."""
    out = defaultdict(set)
    for r, p in PERM.items():
        lid = loop_id(p)
        out[lid].add(cyc(r))
    return out


def walk_structure(name, cache={}):
    """Per walk: parts (from recomp_census), plus
    adjacency (cycle pairs with consecutive parts, by transition weight),
    used-loop -> cycles map, per-cycle first-part depth."""
    if name in cache:
        return cache[name]
    walk = walk_of(name)
    parts = cycle_parts(walk)
    adj_w2, adj_door = set(), set()
    used = defaultdict(set)
    for (r1, p1), (r2, p2) in zip(walk, walk[1:]):
        w = p2 - p1
        c1, c2 = cyc(r1), cyc(r2)
        if c1 == c2:
            continue
        key = frozenset((c1, c2))
        if w == 2:
            adj_w2.add(key)
            lid = loop_id(rot(PERM[r1]))
            used[lid].update((c1, c2))
        elif w >= 3:
            adj_door.add(key)
    depth0 = {c: min(d0 for _, _, _, d0, _ in lst) for c, lst in parts.items()}
    cache[name] = (parts, adj_w2, adj_door, used, depth0)
    return cache[name]


def pair_measures(cycles, structs, static_pairs):
    """For every unordered pair from `cycles`, locality flags against the
    union of both walks' structures."""
    rows = []
    cl = sorted(cycles)
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            a, b = cl[i], cl[j]
            key = frozenset((a, b))
            shared_used = any(
                a in cs and b in cs
                for _, _, _, used, _ in structs
                for cs in used.values()
            )
            adj2 = any(key in s[1] for s in structs)
            adjd = any(key in s[2] for s in structs)
            ddist = min(
                abs(s[4][a] - s[4][b]) for s in structs if a in s[4] and b in s[4]
            )
            rows.append(
                (key in static_pairs, shared_used, adj2, adjd, ddist)
            )
    return rows


def summarize(rows, label):
    n = len(rows)
    if not n:
        print(f"  {label}: no pairs")
        return
    st = sum(r[0] for r in rows)
    us = sum(r[1] for r in rows)
    a2 = sum(r[2] for r in rows)
    ad = sum(r[3] for r in rows)
    dd = sorted(r[4] for r in rows)
    q = lambda f: dd[min(n - 1, int(f * n))]  # noqa: E731
    print(
        f"  {label}: {n} cycle-pairs | static-loop {100*st/n:.1f}% | "
        f"used-loop {100*us/n:.1f}% | w2-adjacent {100*a2/n:.1f}% | "
        f"door-linked {100*ad/n:.1f}% | depth-dist q25/q50/q75 = "
        f"{q(.25)}/{q(.5)}/{q(.75)}"
    )


def main():
    pairs_tsv = sys.argv[1]
    min_flux = 6
    if "--min-flux" in sys.argv:
        min_flux = int(sys.argv[sys.argv.index("--min-flux") + 1])

    sl = static_loop_cycles()
    static_pairs = set()
    for cs in sl.values():
        cl = sorted(cs)
        for i in range(len(cl)):
            for j in range(i + 1, len(cl)):
                static_pairs.add(frozenset((cl[i], cl[j])))

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

    rec_rows, null_rows = [], []
    flux = []  # (n_recomps, net, dS, files, types, cycles)
    unit_pairs = []
    for f1, a1, f2, a2, anchor in rows:
        recomps, _, net, _, _ = censor_pair(f1, f2, anchor)
        s1, s2 = walk_structure(f1), walk_structure(f2)
        structs = (s1, s2)
        rc = [c for c, *_ in recomps]
        rec_rows += pair_measures(rc, structs, static_pairs)
        # null: tail cycles (first part at/after anchor) NOT recomposed
        tail = {
            c
            for s in structs
            for c, d in s[4].items()
            if d >= anchor and c not in rc
        }
        null_rows += pair_measures(sorted(tail)[:12], structs, static_pairs)
        ds = int(a2.split(",")[0]) - int(a1.split(",")[0])
        types = Counter(
            tuple(sorted((tuple(c1), tuple(c2)))) for _, c1, c2, *_ in recomps
        )
        flux.append((len(recomps), net, ds, f1, f2, types, rc, anchor))
        if {a1, a2} == {"142,6,0,0,0", "143,5,0,0,0"}:
            unit_pairs.append((f1, f2, anchor))

    print(f"# M-2a joint locality ({len(rows)} controlled pairs)")
    summarize(rec_rows, "recomposed-cycle pairs")
    summarize(null_rows, "null (non-recomposed tail-cycle pairs)")

    print(f"\n# M-2b minimal-flux controlled pairs (recomposed <= {min_flux})")
    for k, net, ds, f1, f2, types, rc, anchor in sorted(flux)[:40]:
        if k > min_flux:
            break
        tstr = " ".join(
            "|".join(map(str, t[0])) + "<->" + "|".join(map(str, t[1])) + f"x{m}"
            for t, m in sorted(types.items())
        )
        loc = pair_measures(rc, (walk_structure(f1), walk_structure(f2)), static_pairs)
        nloc = sum(1 for r in loc if r[1] or r[2] or r[3])
        print(
            f"  {f1[7:19]} x {f2[7:19]} anchor={anchor} recomps={k} "
            f"net={net:+d} dS={ds:+d} local-pairs={nloc}/{len(loc)} {tstr}"
        )

    print(f"\n# M-2c natural (142,6)x(143,5) unit pairs: {len(unit_pairs)}")
    for f1, f2, anchor in unit_pairs:
        print(f"  -- {f1} x {f2} (anchor {anchor})")
        censor_pair(f1, f2, anchor, details=True)


if __name__ == "__main__":
    main()
