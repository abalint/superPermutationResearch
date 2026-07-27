#!/usr/bin/env python3
"""Complete enumeration of V7=15 chains with total skip Sigma <= SMAX
(cost-3 hops, pivot class '7').  Emission whenever V==15 with the current
loop as full-ride terminus.  K = 15 + Sigma at emission.

usage: python3 enum_budget.py [SMAX] [cap] [tl] [out]
"""
import json
import sys
import time

import chain7
from chain7 import loops, entries, sources, orbitsets, canonical_rotation, door

NE = 6
ID = canonical_rotation(chain7.ALPHA)
cls = [L for L in range(840) if loops[L][0] == "7"]
lidx = {L: i for i, L in enumerate(cls)}
li = chain7.li
E3 = [[None] * NE for _ in range(120)]
for i, L in enumerate(cls):
    for j, s in enumerate(sources[L]):
        t = door(s, 3)
        M = li[chain7.loop_of(t)]
        E3[i][j] = (lidx[M], entries[M].index(t))
L0g = [L for L in cls if ID in orbitsets[L]][0]
L0 = lidx[L0g]
K0 = [canonical_rotation(e) for e in entries[L0g]].index(ID)

SMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 17
cap = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
tl = float(sys.argv[3]) if len(sys.argv) > 3 else 600.0
out_fn = sys.argv[4] if len(sys.argv) > 4 else "chains_V15_budget.jsonl"

TARGET = 15
found = []
t0 = time.time()
timeout = False
nodes = 0


def dfs(i, k, used, K, pen, path):
    global nodes, timeout
    nodes += 1
    if timeout or len(found) >= cap:
        return
    if nodes % 100000 == 0 and time.time() - t0 > tl:
        timeout = True
        return
    V = K - pen
    # terminal skip t: last loop rides 6-t orbits, no hop needed
    for t in range(0, min(5, SMAX - pen) + 1):
        if K - (pen + t) == TARGET:
            found.append((list(path), i, k, t))
            if len(found) >= cap:
                return
    # each hop changes V by 1-s (s = skip, costing s budget):
    # future V-reduction is bounded by remaining budget, future V-gain by
    # remaining unused loops.
    if V - (SMAX - pen) > TARGET:
        return
    if V + (120 - K) < TARGET:
        return
    for s in range(NE):
        if pen + s > SMAX:
            break
        j = (k - 1 - s) % NE
        M, ka = E3[i][j]
        if used >> M & 1:
            continue
        dfs(M, ka, used | (1 << M), K + 1, pen + s, path + [(i, k, j, s)])


def expand(path, li_, lk, t):
    sol = []
    for (i, k, j, s) in path:
        Lg = cls[i]
        sol.append((Lg, k, j, s, sources[Lg][j], door(sources[Lg][j], 3), 3))
    sol.append((cls[li_], lk, None, t, None, None, None))
    return sol


dfs(L0, K0, 1 << L0, 1, 0, [])
print(f"nodes={nodes} timeout={timeout} raw={len(found)}")

recs = []
seen = set()
for (path, li_, lk, t) in found:
    sol = expand(path, li_, lk, t)
    key = (tuple(x[0] for x in sol), t)
    if key in seen:
        continue
    seen.add(key)
    K, S, f4, f5, f6, V = chain7.verify_chain(sol)
    assert V == TARGET
    recs.append({"K": K, "Sigma": S, "V": V, "chain": sol})
recs.sort(key=lambda r: (r["K"], r["Sigma"]))
with open(out_fn, "w") as fh:
    for r in recs:
        fh.write(json.dumps(r) + "\n")
from collections import Counter

sig = Counter((r["K"], r["Sigma"]) for r in recs)
print(f"V=15 Sigma<={SMAX}: {len(recs)} chains -> {out_fn}; "
      f"sig counts: {dict(sorted(sig.items()))}")
