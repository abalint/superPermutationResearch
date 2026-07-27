#!/usr/bin/env python3
"""Complete enumeration of V7=15 chains with hop costs 3/4/5 and total
penalty (Sigma + 5*f4 + 10*f5) <= PMAX.  V = K - pen; emission at V==15.

usage: python3 enum_mixed.py [PMAX] [cap] [tl] [out]
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
# E[c][i][j] = (M, ka) for cost-c hop out of splice j of class-loop i
COSTS = (3, 4, 5)
PEN = {3: 0, 4: 5, 5: 10}
E = {c: [[None] * NE for _ in range(120)] for c in COSTS}
for i, L in enumerate(cls):
    for j, s in enumerate(sources[L]):
        for c in COSTS:
            t = door(s, c)
            M = li[chain7.loop_of(t)]
            if M == L:
                E[c][i][j] = None
            else:
                E[c][i][j] = (lidx[M], entries[M].index(t))
L0g = [L for L in cls if ID in orbitsets[L]][0]
L0 = lidx[L0g]
K0 = [canonical_rotation(e) for e in entries[L0g]].index(ID)

PMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 10
cap = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
tl = float(sys.argv[3]) if len(sys.argv) > 3 else 1200.0
out_fn = sys.argv[4] if len(sys.argv) > 4 else "chains_V15_mixed.jsonl"

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
    if V == TARGET:
        found.append((list(path), i, k))
        if len(found) >= cap:
            return
    if V - (PMAX - pen) > TARGET:
        return
    if V + (120 - K) < TARGET:
        return
    for s in range(NE):
        j = (k - 1 - s) % NE
        for c in COSTS:
            p = s + PEN[c]
            if pen + p > PMAX:
                continue
            e = E[c][i][j]
            if e is None:
                continue
            M, ka = e
            if used >> M & 1:
                continue
            dfs(M, ka, used | (1 << M), K + 1, pen + s + PEN[c],
                path + [(i, k, j, s, c)])


def expand(path, li_, lk):
    sol = []
    for (i, k, j, s, c) in path:
        Lg = cls[i]
        sol.append((Lg, k, j, s, sources[Lg][j], door(sources[Lg][j], c), c))
    sol.append((cls[li_], lk, None, 0, None, None, None))
    return sol


dfs(L0, K0, 1 << L0, 1, 0, [])
print(f"nodes={nodes} timeout={timeout} raw={len(found)}")

recs = []
seen = set()
for (path, li_, lk) in found:
    sol = expand(path, li_, lk)
    key = tuple((x[0], x[6]) for x in sol)
    if key in seen:
        continue
    seen.add(key)
    K, S, f4, f5, f6, V = chain7.verify_chain(sol)
    assert V == TARGET, (K, S, f4, f5, f6, V)
    recs.append({"K": K, "Sigma": S, "f4": f4, "f5": f5, "V": V, "chain": sol})
recs.sort(key=lambda r: (r["K"], r["Sigma"]))
with open(out_fn, "w") as fh:
    for r in recs:
        fh.write(json.dumps(r) + "\n")
from collections import Counter

sig = Counter((r["K"], r["Sigma"], r["f4"], r["f5"]) for r in recs)
print(f"V=15 pen<={PMAX}: {len(recs)} chains -> {out_fn}; "
      f"(K,Sigma,f4,f5) counts: {dict(sorted(sig.items()))}")
