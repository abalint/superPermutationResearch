#!/usr/bin/env python3
"""n=7 corpus L0 allocation census (s33; n=6 analog: upstream872_structure.py).

Per walk: sojourn count S, inter-sojourn door histogram, intra-orbit
histogram — the L0 allocation in the T0 waste identity
    waste = (S-1) + sum_{w>=3}(w-2)*inter[w] + sum_{w>=2}(w-1)*intra[w].

Writes upstream5906_structure.tsv (one row per class file) and prints the
allocation histogram. s42 headline (refreshed after PR #50): all 92
PUBLISHED 5906 classes are PURE-w3 (no w4+, no intra) over exactly 8
allocations, S+#w3 = 861 in every case — (844,17)=61, (838,23)=9,
(840,21)=9, (839,22)=6, (842,19)=2, (836,25)=2, (835,26)=2, (843,18)=1.
Kristan's class is the sole occupant of (S=843,#w3=18), one S<->door
unit-trade from the dominant (844,17) shell — the n=7 echo of the n=6
natural pair (143,5)<->(142,6); the two allocations added in s42,
(839,22) and (835,26), are this project's 8 novel classes, each one
R-K7 off-shell from a (840,21)/(836,25) source. The three 5907s sit at
(858,4): treelike, door-sparse, sojourn-heavy.

Usage: python3 upstream5906_structure.py [dir ...]
       The committed TSV covers the WHOLE published n=7 corpus, which
       since s41 spans two dirs — regenerate with all three explicitly:
       python3 upstream5906_structure.py data/upstream5906 \\
           data/novel5906 data/upstream5907
       (bare default: data/upstream5906 data/upstream5907 = the stale 84)
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(ROOT, "analysis", "trackb"))
from verify_identity import first_visit_path, overlap  # noqa: E402

OUT = os.path.join(HERE, "upstream5906_structure.tsv")


def rot_cycle(p):
    n = len(p)
    return min(p[i:] + p[:i] for i in range(n))


def alloc(s):
    n = max(int(c) for c in s)
    path = first_visit_path(s, n)
    weights = [n - overlap(path[i], path[i + 1]) for i in range(len(path) - 1)]
    inter, intra = Counter(), Counter()
    sojourns = 1
    for i, w in enumerate(weights):
        same = rot_cycle(path[i]) == rot_cycle(path[i + 1])
        if same and w > 1:
            intra[w] += 1
        elif not same:
            sojourns += 1
            if w >= 3:
                inter[w] += 1
    return sojourns, inter, intra


def fmt_hist(h):
    return ",".join(f"{w}:{c}" for w, c in sorted(h.items())) or "-"


def main():
    dirs = sys.argv[1:] or [
        os.path.join(ROOT, "data", "upstream5906"),
        os.path.join(ROOT, "data", "upstream5907"),
    ]
    rows = []
    hist = Counter()
    for d in dirs:
        for f in sorted(os.listdir(d)):
            if not f.endswith(".txt"):
                continue
            s = open(os.path.join(d, f)).read().strip()
            sojourns, inter, intra = alloc(s)
            waste = (
                (sojourns - 1)
                + sum((w - 2) * c for w, c in inter.items())
                + sum((w - 1) * c for w, c in intra.items())
            )
            rows.append((f, len(s), sojourns, fmt_hist(inter), fmt_hist(intra), waste))
            hist[(len(s), sojourns, tuple(sorted(inter.items())),
                  tuple(sorted(intra.items())))] += 1
    with open(OUT, "w") as out:
        out.write("file\tlength\tS\tinter\tintra\twaste\n")
        for r in rows:
            out.write("\t".join(str(x) for x in r) + "\n")
    print(f"{len(rows)} walks -> {OUT}")
    for (length, sojourns, inter, intra), c in sorted(hist.items(),
                                                     key=lambda kv: -kv[1]):
        print(f"count={c:3d}  len={length}  S={sojourns}  "
              f"inter={dict(inter)}  intra={dict(intra)}")


if __name__ == "__main__":
    main()
