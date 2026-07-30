#!/usr/bin/env python3
"""Door pricing across the 8 specimen-backed allocations (s27, queued s26c).

For every class representative in data/upstream872/: where in the walk the
weight>=3 doors sit (visited-perm depth), what they exit from and land on,
and how the non-records allocations "pay" for their extra doors relative to
the records class. Cheap positional/contextual statistics — the input data
for cross-class surgery design (which door edits real 872s tolerate, where).

Per door event: normalized depth (perms visited / 720), exit-part length
(members covered in the sojourn being left), target-cycle freshness
(members of the landing cycle already visited when the door is taken).

Usage: python3 analysis/counting/upstream872_door_pricing.py data/upstream872
           [--out analysis/counting/upstream872_door_pricing.tsv]
"""
import os
import sys
from collections import Counter, defaultdict
from itertools import permutations

N = 6

PERMS = ["".join(map(str, p)) for p in permutations(range(1, N + 1))]
CYCLE = {}
for p in PERMS:
    rots = [p[i:] + p[:i] for i in range(N)]
    CYCLE[p] = min(rots)


def trace(s):
    seen = set()
    path = []
    for i in range(len(s) - N + 1):
        w = s[i:i + N]
        if len(set(w)) == N and w not in seen:
            seen.add(w)
            path.append(w)
    weights = []
    for a, b in zip(path, path[1:]):
        for k in range(N, 0, -1):
            if a[N - k:] == b[:k]:
                weights.append(N - k)
                break
    return path, weights


def doors(s):
    """Door events: (weight, depth, exit_part_len, target_fresh) for w>=3."""
    path, weights = trace(s)
    inter = Counter()
    cyc_seen = Counter()  # cycle -> members visited
    cur_cycle = CYCLE[path[0]]
    cyc_seen[cur_cycle] = 1
    run_len = 1
    events = []
    for i, w in enumerate(weights):
        q = path[i + 1]
        qc = CYCLE[q]
        if qc != cur_cycle:
            inter[w] += 1
            if w >= 3:
                events.append((w, i + 1, run_len, cyc_seen[qc]))
            cur_cycle = qc
            run_len = 1
        else:
            run_len += 1
        cyc_seen[qc] += 1
    S = 1 + sum(inter.values())
    d3, d4, d5 = inter[3], inter[4], inter[5]
    return (S, d3, d4, d5, 0), events


def main():
    d = sys.argv[1]
    out_path = "analysis/counting/upstream872_door_pricing.tsv"
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    per_alloc = defaultdict(list)  # alloc -> [(w, depth, exit_len, fresh)]
    n_classes = Counter()
    files = sorted(f for f in os.listdir(d) if f.endswith(".txt"))
    for f in files:
        s = open(os.path.join(d, f)).read().strip()
        alloc, events = doors(s)
        n_classes[alloc] += 1
        per_alloc[alloc].extend(events)
    print(f"classes: {len(files)}")
    with open(out_path, "w") as out:
        out.write("S\td3\td4\td5\tip\tweight\tdepth\texit_part\ttarget_fresh\n")
        for alloc in sorted(per_alloc, key=lambda a: -n_classes[a]):
            for w, dep, ex, fr in per_alloc[alloc]:
                out.write("\t".join(map(str, alloc)) + f"\t{w}\t{dep}\t{ex}\t{fr}\n")
    print(f"wrote {out_path}")

    for alloc in sorted(per_alloc, key=lambda a: -n_classes[a]):
        ev = per_alloc[alloc]
        nc = n_classes[alloc]
        print(f"\n=== S={alloc[0]} d3={alloc[1]} d4={alloc[2]} d5={alloc[3]} "
              f"({nc} classes, {len(ev)} door events, {len(ev)/nc:.1f}/walk)")
        for w in (3, 4, 5):
            evw = [e for e in ev if e[0] == w]
            if not evw:
                continue
            deps = sorted(e[1] for e in evw)
            deciles = Counter(min(9, e[1] * 10 // 720) for e in evw)
            dec = " ".join(f"{deciles.get(i, 0)*100//len(evw):2d}" for i in range(10))
            exit_h = Counter(e[2] for e in evw)
            fresh_h = Counter(min(e[3], 3) for e in evw)
            print(f"  w{w} x{len(evw)}: depth min/med/max = "
                  f"{deps[0]}/{deps[len(deps)//2]}/{deps[-1]}"
                  f"   decile% [{dec}]")
            print(f"      exit-part lens: "
                  + " ".join(f"{k}:{v*100//len(evw)}%" for k, v in sorted(exit_h.items())))
            print(f"      target fresh (visited members of landing cycle, 3=3+): "
                  + " ".join(f"{k}:{v*100//len(evw)}%" for k, v in sorted(fresh_h.items())))


if __name__ == "__main__":
    main()
