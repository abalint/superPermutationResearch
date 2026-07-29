#!/usr/bin/env python3
"""Structural census of the full community 872 corpus (s26b).

Per equivalence-class representative (data/upstream872/, one
forward-renumbered identity-start string per class): first-visit trace,
L0 allocation (S, d3, d4, d5, ip), waste-identity check, and the
per-cycle split profile — the quantities every Track B scoping decision
was calibrated to on the biased 296-sample.

Usage: python3 analysis/counting/upstream872_structure.py data/upstream872 [out.tsv]
"""
import os
import sys
from collections import Counter, defaultdict
from itertools import permutations

N = 6
WASTE = 147  # 872 - 725

PERMS = ["".join(map(str, p)) for p in permutations(range(1, N + 1))]
CYCLE = {}
for p in PERMS:
    rots = [p[i:] + p[:i] for i in range(N)]
    CYCLE[p] = min(rots)

def trace(s):
    """First-visit path (as perm strings) + maximal-overlap weights."""
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

def census(s):
    path, weights = trace(s)
    assert len(path) == 720, len(path)
    inter = Counter()   # weight -> count of cycle-changing moves
    intra = Counter()   # weight -> count of same-cycle moves (w >= 2)
    # split profile: per cycle, the sequence of sojourn run lengths
    runs = defaultdict(list)
    cur_cycle = CYCLE[path[0]]
    run_len = 1
    for i, w in enumerate(weights):
        q = path[i + 1]
        qc = CYCLE[q]
        if qc != cur_cycle:
            inter[w] += 1
            runs[cur_cycle].append(run_len)
            cur_cycle = qc
            run_len = 1
        else:
            if w >= 2:
                intra[w] += 1
            run_len += 1
    runs[cur_cycle].append(run_len)
    S = 1 + sum(inter.values())
    d3, d4, d5 = inter[3], inter[4], inter[5]
    ip = intra[2]
    waste = (S - 1) + sum((w - 2) * c for w, c in inter.items()) + sum(
        (w - 1) * c for w, c in intra.items()
    )
    # profile: multiset of per-cycle run-length tuples
    profile = Counter(tuple(v) for v in runs.values())
    mult = Counter(weights)
    return {
        "S": S, "d3": d3, "d4": d4, "d5": d5, "ip": ip,
        "waste_ok": waste == WASTE,
        "mult": tuple(mult[w] for w in range(1, N)),
        "profile": frozenset(profile.items()),
        "profile_c": profile,
        "intra_hi": sum(c for w, c in intra.items() if w >= 3),
    }

def main():
    d = sys.argv[1]
    out = open(sys.argv[2], "w") if len(sys.argv) > 2 else None
    if out:
        out.write("file\tS\td3\td4\td5\tip\tmult\twaste_ok\n")
    alloc = Counter()
    mults = Counter()
    profiles = Counter()
    bad_waste = []
    intra_hi = 0
    alloc_example = {}
    files = sorted(f for f in os.listdir(d) if f.endswith(".txt"))
    for f in files:
        s = open(os.path.join(d, f)).read().strip()
        c = census(s)
        key = (c["S"], c["d3"], c["d4"], c["d5"], c["ip"])
        alloc[key] += 1
        alloc_example.setdefault(key, f)
        mults[c["mult"]] += 1
        profiles[c["profile"]] += 1
        intra_hi += c["intra_hi"]
        if not c["waste_ok"]:
            bad_waste.append(f)
        if out:
            out.write(f"{f}\t{c['S']}\t{c['d3']}\t{c['d4']}\t{c['d5']}\t{c['ip']}\t"
                      f"{c['mult']}\t{c['waste_ok']}\n")
    print(f"classes: {len(files)}")
    print(f"waste identity holds: {len(files) - len(bad_waste)}/{len(files)}"
          + (f"  FAILURES: {bad_waste[:5]}" if bad_waste else ""))
    print(f"intra moves of weight>=3 anywhere: {intra_hi}")
    print(f"\nL0 allocations (S,d3,d4,d5,ip) with specimens: {len(alloc)}")
    for k, n in alloc.most_common():
        print(f"  S={k[0]} d3={k[1]} d4={k[2]} d5={k[3]} ip={k[4]}: {n} classes"
              f"   e.g. {alloc_example[k]}")
    print(f"\nweight multisets: {len(mults)}")
    for m, n in mults.most_common():
        print(f"  w1..w5={m}: {n}")
    print(f"\ndistinct split profiles: {len(profiles)}")
    for p, n in profiles.most_common(5):
        pretty = ", ".join(f"{'|'.join(map(str, t))}×{c}" for t, c in sorted(p))
        print(f"  {n} classes: {pretty[:120]}")
    if out:
        out.close()

if __name__ == "__main__":
    main()
