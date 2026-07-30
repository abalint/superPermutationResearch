#!/usr/bin/env python3
"""Door locality vs recomposed cycles (s29, I2 design input).

For every specimen pair: list each side's door events (w>=3 part entries),
and check whether the door's TARGET cycle is one of the pair's recomposed
cycles. Localized doors mean an I2 edit couples door placement to the
recomposition set; delocalized doors mean the edit is nonlocal (doors move
independently of where compositions change).

Usage: recomp_doors.py <pairs.tsv>
"""

import sys

from recomp_census import cycle_parts, comp_of, walk_of


def doors_of(parts):
    out = []
    for c, lst in parts.items():
        for ln, e, x, d0, er in lst:
            if e and e >= 3:
                out.append((d0, e, c))
    return sorted(out)


def main():
    with open(sys.argv[1]) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        fi = {c: i for i, c in enumerate(header)}
        rows = [line.rstrip("\n").split("\t") for line in fh]

    for f in rows:
        f1, a1, f2, a2 = f[fi["file1"]], f[fi["alloc1"]], f[fi["file2"]], f[fi["alloc2"]]
        anchor = int(f[fi["deepest_shared"]])
        p1, p2 = cycle_parts(walk_of(f1)), cycle_parts(walk_of(f2))
        recomp = {c for c in p1 if comp_of(p1[c]) != comp_of(p2[c])}
        d1, d2 = doors_of(p1), doors_of(p2)
        # doors in the shared prefix are identical; only report tail doors
        t1 = [(d0, w, c) for d0, w, c in d1 if d0 > anchor]
        t2 = [(d0, w, c) for d0, w, c in d2 if d0 > anchor]
        print(f"-- {f1} ({a1})  x  {f2} ({a2})  anchor {anchor}  recomposed {len(recomp)}")
        for tag, td in (("A", t1), ("B", t2)):
            desc = " ".join(
                f"w{w}@{d0}->{c}{'*' if c in recomp else ''}" for d0, w, c in td
            )
            on = sum(1 for _, _, c in td if c in recomp)
            print(f"   {tag} tail doors: {len(td)} ({on} on recomposed cycles*)  {desc}")


if __name__ == "__main__":
    main()
