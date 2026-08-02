#!/usr/bin/env python3
"""beam7.py -- segment-level beam search for max-V7 chains (cost-3 hops).

Node = (entry state x, used bitmask, K, pen, path). One beam level = one
segment: ride t forced hops (t = 0..free), then one skip-s deviation
(s = 1..5). Priority = upper bound V + m - ceil((m - fr)/5).
"""
from itertools import permutations
import sys, time

N = 7; ALPHA = "1234567"; NE = 6
WIDTH = int(sys.argv[1]) if len(sys.argv) > 1 else 3000

# s64 P1: ONE copy of the rotation-frame quartet, in pylib/canonical.py.
# `canon` here is the least-ROTATION canon -- NOT m3_check's relabel+reversal
# canon.  pylib keeps the two apart by name (canon_rotation vs
# canon_relabel_rev); the local alias preserves every call site below.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
from pylib.canonical import canon_rotation as canon, door, loop_of, tv  # noqa: E402,F401

loops = []
for pivot in ALPHA:
    rest = [c for c in ALPHA if c != pivot]
    seen = set()
    for p in permutations(rest):
        nk = canon("".join(p))
        if nk not in seen:
            seen.add(nk); loops.append((pivot, nk))
li = {lp: i for i, lp in enumerate(loops)}
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
        t = door(s, 3); M = li[loop_of(t)]
        E3[i][j] = (lidx[M], entries[M].index(t))
ID = canon(ALPHA)
L0g = [L for L in cls if ID in set(canon(e) for e in entries[L])][0]
L0 = lidx[L0g]; K0 = [canon(e) for e in entries[L0g]].index(ID)

def free_run(i, k, used):
    cnt = 0
    for _ in range(4):
        M, ka = E3[i][(k - 1) % NE]
        if used >> M & 1: break
        cnt += 1; i, k = M, ka
    return cnt

t0 = time.time()
best = (5, None)
# beam node: (i, k, used, K, pen, path)  path = list of (i,k,j,s)
beam = [(L0, K0, 1 << L0, 1, 0, ())]
level = 0
while beam:
    level += 1
    nxt = []
    for (i, k, used, K, pen, path) in beam:
        # enumerate: ride t forced (extending path/used), then deviate s
        ci, ck, cu, cK, cpath = i, k, used, K, path
        for t in range(5):
            if t > 0:
                j = (ck - 1) % NE
                M, ka = E3[ci][j]
                if cu >> M & 1: break
                cpath = cpath + ((ci, ck, j, 0),)
                cu |= 1 << M; cK += 1; ci, ck = M, ka
            V_end = cK - pen
            if V_end > best[0]:
                best = (V_end, cpath + ((ci, ck, None, 0),))
            for s in range(1, NE):
                j = (ck - 1 - s) % NE
                M, ka = E3[ci][j]
                if cu >> M & 1: continue
                u2 = cu | (1 << M)
                K2, p2 = cK + 1, pen + s
                fr = free_run(M, ka, u2)
                m = 120 - K2
                ub = (K2 - p2) + m - max(0, -((fr - m) // 5))
                if ub <= best[0]: continue
                nxt.append((ub, K2 - p2 + fr, M, ka, u2, K2, p2,
                            cpath + ((ci, ck, j, s),)))
    if not nxt: break
    nxt.sort(key=lambda x: (-x[0], -x[1]))
    beam = [(M, ka, u2, K2, p2, path)
            for (_, _, M, ka, u2, K2, p2, path) in nxt[:WIDTH]]
    if level % 5 == 0 or not beam:
        print(f" level {level}: beam={len(beam)} bestV={best[0]} "
              f"t+{time.time()-t0:.1f}s", flush=True)

V, path = best
segs = sum(1 for x in path if x[3] and x[3] > 0) + 1
K = len(path); pen = sum(x[3] for x in path if x[3])
print(f"\nBEAM BEST: V={V} (K={K}, Sigma={pen}, segments={segs}) "
      f"width={WIDTH} ({time.time()-t0:.1f}s)")

# verify against raw strings
sol = []
for (i, k, j, s) in path:
    Lg = cls[i]
    if j is None:
        sol.append((Lg, k, None, 0, None, None, None))
    else:
        sol.append((Lg, k, j, s, sources[Lg][j], door(sources[Lg][j], 3), 3))
orbs = set(); seenL = set(); ssum = 0
assert canon(entries[sol[0][0]][sol[0][1]]) == ID
for idx, (L, k, j, sk, s, t, c) in enumerate(sol):
    assert L not in seenL; seenL.add(L)
    os_ = set(canon(e) for e in entries[L])
    assert not (os_ & orbs); orbs |= os_
    if j is None:
        assert idx == len(sol) - 1; continue
    assert s == sources[L][j] and t == door(s, 3)
    assert sk == 5 - ((j - k) % NE); ssum += sk
    Ln, kn = sol[idx + 1][0], sol[idx + 1][1]
    assert loop_of(t) == loops[Ln] and entries[Ln][kn] == t
print(f"VERIFIED: K={len(sol)}, Sigma={ssum}, V={len(sol)-ssum}, "
      f"waste=862-{(len(sol)-ssum)}/5={862-(len(sol)-ssum)/5}")
with open(f"beam_best_w{WIDTH}.txt", "w") as f:
    for x in sol: f.write(repr(x) + "\n")
