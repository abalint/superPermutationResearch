#!/usr/bin/env python3
"""segment7.py -- stochastic segment-level search for max V7 chains.

Structure exploited: forced (skip-0) map = pure 5-cycles. A high-V chain is
a sequence of forced runs (<=5 fully ridden loops) joined by deviating hops
(prefer skip-1 cost-3). Greedy with 1-step lookahead (next free-run length)
+ randomized restarts; records the best chain found.
V7 = K - Sigma_skip - 5*f4 - ...; here cost-3 only => V = K - Sigma.
Upper bound (analytic): V <= 4C+1 per C segments, max 97 at C=24 (K=120).
"""
from itertools import permutations
from collections import Counter
import sys, time, random

N = 7; ALPHA = "1234567"; NE = 6; MAXSKIP = 5
TIME_BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 1

def door(w, c): return w[c:] + w[:c][::-1]
def tv(w): return w[1:-1] + w[0] + w[-1]
def canon(w): return min(w[i:] + w[:i] for i in range(len(w)))
def loop_of(e): return (e[-1], canon(e[:-1]))

loops = []
for pivot in ALPHA:
    rest = [c for c in ALPHA if c != pivot]
    seen = set()
    for p in permutations(rest):
        nk = canon("".join(p))
        if nk not in seen:
            seen.add(nk); loops.append((pivot, nk))
loop_index = {lp: i for i, lp in enumerate(loops)}
entries, sources = [], []
for (a, C) in loops:
    e = C + a
    es, ss = [], []
    for _ in range(NE):
        es.append(e); ss.append(e[-1] + e[:-1]); e = tv(e)
    entries.append(es); sources.append(ss)

cls = [L for L in range(840) if loops[L][0] == '7']
lidx = {L: i for i, L in enumerate(cls)}
E3 = [[None] * NE for _ in range(120)]
for i, L in enumerate(cls):
    for j, s in enumerate(sources[L]):
        M = loop_index[loop_of(door(s, 3))]
        E3[i][j] = (lidx[M], entries[M].index(door(s, 3)))
ID = canon(ALPHA)
L0g = [L for L in cls if ID in set(canon(e) for e in entries[L])][0]
L0 = lidx[L0g]
K0 = [canon(e) for e in entries[L0g]].index(ID)

def free_run(i, k, used):
    cnt = 0
    for _ in range(4):
        M, ka = E3[i][(k - 1) % NE]
        if used >> M & 1: break
        cnt += 1; i, k = M, ka
    return cnt

rng = random.Random(SEED)
best = (0, None)
t0 = time.time(); it = 0; last_rep = t0
while time.time() - t0 < TIME_BUDGET:
    it += 1
    i, k = L0, K0
    used = 1 << L0
    pen = 0; K = 1
    path = []                       # (i, k, j, s)
    while True:
        # ride forced while fresh
        while True:
            j = (k - 1) % NE
            M, ka = E3[i][j]
            if used >> M & 1: break
            path.append((i, k, j, 0))
            used |= 1 << M; K += 1; i, k = M, ka
        # deviating candidates (cost 3, skip 1..5)
        cand = []
        for s in range(1, NE):
            j = (k - 1 - s) % NE
            M, ka = E3[i][j]
            if used >> M & 1: continue
            fr = free_run(M, ka, used | (1 << M))
            gain_density = (1 + fr) - s        # loops gained minus pen
            cand.append((gain_density, -s, s, j, M, ka, fr))
        if not cand: break
        cand.sort(reverse=True)
        # softmax-ish choice among near-best
        top = [c for c in cand if c[0] >= cand[0][0] - (0 if rng.random() < 0.7 else 1)]
        g, ns, s, j, M, ka, fr = top[rng.randrange(len(top))]
        if K - pen - s + 1 + fr <= 0: break
        path.append((i, k, j, s))
        used |= 1 << M; K += 1; pen += s; i, k = M, ka
    V = K - pen
    if V > best[0]:
        best = (V, (list(path), i, k, K, pen))
        print(f" it={it} new best V={V} (K={K}, Sigma={pen}) "
              f"t+{time.time()-t0:.1f}s", flush=True)
    if time.time() - last_rep > 30:
        last_rep = time.time()
        print(f" [t+{last_rep-t0:.0f}s] restarts={it}, best V={best[0]}", flush=True)

V, (path, li, lk, K, pen) = best
print(f"\nBEST: V={V}  K={K} Sigma={pen} segments={sum(1 for x in path if x[3]>0)+1}")
print(f"restarts={it} in {time.time()-t0:.0f}s")

# ---- verify from raw strings and dump for reuse ----
sol = []
for (i, k, j, s) in path:
    Lg = cls[i]
    sol.append((Lg, k, j, s, sources[Lg][j], door(sources[Lg][j], 3), 3))
sol.append((cls[li], lk, None, 0, None, None, None))
orbs = set(); seenL = set(); ssum = 0
assert canon(entries[sol[0][0]][sol[0][1]]) == ID
for idx, (L, k, j, sk, s, t, c) in enumerate(sol):
    assert L not in seenL; seenL.add(L)
    os_ = set(canon(e) for e in entries[L])
    assert not (os_ & orbs); orbs |= os_
    if j is None: continue
    assert s == sources[L][j] and t == door(s, 3)
    assert sk == MAXSKIP - ((j - k) % NE)
    ssum += sk
    Ln, kn = sol[idx + 1][0], sol[idx + 1][1]
    assert loop_of(t) == loops[Ln] and entries[Ln][kn] == t
assert len(sol) == K and ssum == pen
print(f"VERIFIED against raw strings: K={K}, Sigma={ssum}, V={K-ssum}, "
      f"waste={862 - (K-ssum)/5}")
with open("best_chain.txt", "w") as f:
    for x in sol:
        f.write(repr(x) + "\n")
