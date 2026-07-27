#!/usr/bin/env python3
"""Convert KernelFinder nsk patterns to chain jsonl.

usage: python3 kf2chain.py <Kernels file> <out.jsonl> [skip_patterns_file]
Pattern digits = 1-cycles ridden per loop; '-' before a digit = weight-4 hop
into that loop (we only support all-w3 for now; patterns with '-' skipped).
"""
import json
import sys

import chain7
from chain7 import loops, entries, sources, orbitsets, canonical_rotation, door, li, loop_of

NE = 6
ID = canonical_rotation(chain7.ALPHA)
cls = [L for L in range(840) if loops[L][0] == "7"]
L0 = [L for L in cls if ID in orbitsets[L]][0]
K0 = [canonical_rotation(e) for e in entries[L0]].index(ID)


def pattern_to_chain(pat):
    if "-" in pat or " " in pat:
        return None  # weight-4 edges unsupported here
    rides = [int(c) for c in pat]
    sol = []
    L, k = L0, K0
    used = {L}
    for idx, r in enumerate(rides):
        if idx == len(rides) - 1:
            sol.append((L, k, None, NE - r, None, None, None))
            break
        j = (k + r - 1) % NE
        s = sources[L][j]
        t = door(s, 3)
        M = li[loop_of(t)]
        if M in used:
            return None  # revisits a loop: not a valid chain
        used.add(M)
        sol.append((L, k, j, 5 - ((j - k) % NE), s, t, 3))
        L, k = M, entries[M].index(t)
    return sol


def main():
    src, out = sys.argv[1], sys.argv[2]
    recs, bad = [], 0
    for line in open(src):
        pat = line.strip()
        if not pat:
            continue
        sol = pattern_to_chain(pat)
        if sol is None:
            bad += 1
            continue
        K, S, f4, f5, f6, V = chain7.verify_chain(sol)
        recs.append({"K": K, "Sigma": S, "V": V, "pattern": pat,
                     "chain": sol})
    recs.sort(key=lambda r: (r["K"], r["Sigma"]))
    with open(out, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    from collections import Counter
    sig = Counter((r["K"], r["Sigma"]) for r in recs)
    print(f"{len(recs)} chains -> {out} (skipped {bad}); "
          f"{dict(sorted(sig.items()))}")


if __name__ == "__main__":
    main()
