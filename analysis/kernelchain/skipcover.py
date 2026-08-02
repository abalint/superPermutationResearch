#!/usr/bin/env python3
"""skipcover.py -- row exact-cover + rooted-forest check for the
(K=20, Sigma_skip=8, f4=1) V=8 chains found by skipchain.py.

A valid row set: R=7 oriented rows (row loop + designated parent orbit),
covering each of the 28 non-root orbits exactly once (4 per row), such that
parent pointers form a forest grounded in root (ridden) orbits.
"""
from itertools import permutations
from collections import Counter
import time

ALPHA = "123456"
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
loop_index = {lp: i for i, lp in enumerate(loops)}
entries, sources, orbitsets = [], [], []
for (a, C) in loops:
    e = C + a
    es, ss, os_ = [], [], set()
    for _ in range(5):
        es.append(e); ss.append(e[-1] + e[:-1]); os_.add(canon(e)); e = tv(e)
    entries.append(es); sources.append(ss); orbitsets.append(frozenset(os_))
def fmt(i): return f"m{loops[i][0]};{loops[i][1]}"
ID = canon("123456")

E = [[] for _ in range(144)]   # (j, s, t, M, ka, cost)
for L in range(144):
    for j, s in enumerate(sources[L]):
        for c in (3, 4):
            t = door(s, c)
            M = loop_index[loop_of(t)]
            if M != L:
                E[L].append((j, s, t, M, entries[M].index(t), c))
PEN = {3: 0, 4: 4}

# ------------------------- re-find all V=8, f4=1 (K=20,Sigma=8) chains
chains = []
def dfs(cur, k, used, pen, path):
    V = len(used) - pen
    if V >= 8:
        chains.append(list(path) + [(cur, k, None, 0, None, None, None)])
    if 24 - pen < 8:
        return
    for (j, s, t, M, ka, c) in E[cur]:
        if M in used: continue
        sk = 4 - ((j - k) % 5)
        dfs(M, ka, used | {M}, pen + sk + PEN[c],
            path + [(cur, k, j, sk, s, t, c)])
for a in ALPHA:
    ls = [L for L in range(144) if loops[L][0] == a and ID in orbitsets[L]]
    L0 = ls[0]
    k0 = [canon(e) for e in entries[L0]].index(ID)
    dfs(L0, k0, frozenset({L0}), 0, [])
sel = [ch for ch in chains
       if sum(1 for x in ch if x[6] == 4) == 1 and len(ch) == 20]
print(f"V=8 chains re-found: {len(chains)} total; (K=20,f4=1): {len(sel)}")

def chain_roots(sol):
    roots = set()
    for (L, k, j, sk, s, t, c) in sol:
        if j is None:
            roots |= orbitsets[L]
        else:
            for d in range(((j - k) % 5) + 1):
                roots.add(canon(entries[L][(k + d) % 5]))
    return roots

# --------------------------------- exact cover + forest check per chain
def cover_and_forest(sol, verbose=False):
    chainL = set(x[0] for x in sol)
    roots = chain_roots(sol)
    K = len(sol); ssum = sum(x[3] for x in sol)
    nonroot = sorted(set().union(*orbitsets) - roots)
    R = len(nonroot) // 4
    cand = []   # (loopidx, parent_orbit, frozenset covered)
    for L in range(144):
        if L in chainL: continue
        rs = orbitsets[L] & roots
        if len(rs) == 0:
            for p in orbitsets[L]:
                cand.append((L, p, orbitsets[L] - {p}))
        elif len(rs) == 1:
            p = next(iter(rs))
            cand.append((L, p, orbitsets[L] - {p}))
    col = {o: [] for o in nonroot}
    for ci, (L, p, cov) in enumerate(cand):
        for o in cov: col[o].append(ci)
    covers = []
    chosen = []
    def solve(rem):
        if len(covers) >= 100000: return
        if not rem:
            covers.append(list(chosen)); return
        o = min(rem, key=lambda x: len([ci for ci in col[x]
                 if not (cand[ci][2] - rem)]))
        for ci in col[o]:
            L, p, cov = cand[ci]
            if cov - rem: continue
            chosen.append(ci)
            solve(rem - cov)
            chosen.pop()
    solve(frozenset(nonroot))
    # forest check on each cover
    good = []
    for cv in covers:
        owner = {}
        for ci in cv:
            for o in cand[ci][2]: owner[o] = ci
        ok = True
        for ci in cv:
            seen = set()
            cur = ci
            while True:
                if cur in seen: ok = False; break
                seen.add(cur)
                p = cand[cur][1]
                if p in roots: break
                cur = owner[p]
            if not ok: break
        if ok: good.append(cv)
    print(f" chain pivot {loops[sol[0][0]][0]}: K={K} Sigma={ssum} "
          f"nonroot={len(nonroot)} R={R} candidates={len(cand)} "
          f"exact covers={len(covers)} forest-valid covers={len(good)}")
    if good and verbose:
        cv = good[0]
        print("  witness rows (loop | parent orbit -> covered orbits):")
        for ci in cv:
            L, p, cov = cand[ci]
            print(f"   {fmt(L):11s} parent {p} "
                  f"({'root' if p in roots else 'row-covered'}) -> "
                  f"{sorted(cov)}")
    return len(covers), len(good)

tot = Counter()
for i, sol in enumerate(sel):
    nc, ng = cover_and_forest(sol, verbose=(i == 0))
    tot["covers"] += nc; tot["good"] += ng
print(f"\nTOTAL over {len(sel)} chains: exact covers={tot['covers']},"
      f" forest-valid={tot['good']}")

# also check the K=22 all-cost-3 chains for completeness (expect infeasible)
sel22 = [ch for ch in chains
         if sum(1 for x in ch if x[6] == 4) == 0 and len(ch) == 22]
print(f"\nK=22 (f4=0) chains: {len(sel22)} (loop-count already infeasible, "
      "cover check for completeness)")
for sol in sel22[:1]:
    cover_and_forest(sol)
