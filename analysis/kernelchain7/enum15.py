#!/usr/bin/env python3
"""enum15.py -- enumerate certificate-valid V7=15 (5905-class) and V7=20
(5904-class) chains (cap 100 each), annotate examples, eligible-row counts.
Also row-stats for the saved best beam chains (V=35, V=36).

Note (proven structural fact): skip-1 deviations require run length r=1
(landing = loop of f^-1(state), the previous loop of the own forced cycle),
so every deviating segment nets r - s <= 3; V ranges here use skip>=2 runs.
"""
from itertools import permutations
from collections import Counter
import time, ast

N = 7; ALPHA = "1234567"; NE = 6; MAXSKIP = 5
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
entries, sources, orbitsets = [], [], []
for (a, C) in loops:
    e = C + a
    es, ss, os_ = [], [], set()
    for _ in range(NE):
        es.append(e); ss.append(e[-1] + e[:-1]); os_.add(canon(e)); e = tv(e)
    entries.append(es); sources.append(ss); orbitsets.append(frozenset(os_))
def fmt(i): return f"m{loops[i][0]};{loops[i][1]}"
ID = canon(ALPHA)
cls = [L for L in range(840) if loops[L][0] == '7']
lidx = {L: i for i, L in enumerate(cls)}
E3 = [[None] * NE for _ in range(120)]
for i, L in enumerate(cls):
    for j, s in enumerate(sources[L]):
        t = door(s, 3); M = li[loop_of(t)]
        E3[i][j] = (lidx[M], entries[M].index(t))
L0g = [L for L in cls if ID in orbitsets[L]][0]
L0 = lidx[L0g]; K0 = [canon(e) for e in entries[L0g]].index(ID)

def free_run(i, k, used):
    cnt = 0
    for _ in range(4):
        M, ka = E3[i][(k - 1) % NE]
        if used >> M & 1: break
        cnt += 1; i, k = M, ka
    return cnt

# ---------- verification / reporting on global-index sols ----------
def verify_mixed(sol):
    assert canon(entries[sol[0][0]][sol[0][1]]) == ID
    piv = loops[sol[0][0]][0]
    seenL, orbs, ssum, f = set(), set(), 0, Counter()
    for idx, (L, k, j, sk, s, t, c) in enumerate(sol):
        assert loops[L][0] == piv
        assert L not in seenL; seenL.add(L)
        assert not (orbitsets[L] & orbs); orbs |= orbitsets[L]
        if j is None:
            assert idx == len(sol) - 1 and sk == 0; continue
        assert s == sources[L][j] and t == door(s, c)
        assert sk == MAXSKIP - ((j - k) % NE)
        ssum += sk; f[c] += 1
        Ln, kn = sol[idx + 1][0], sol[idx + 1][1]
        assert loop_of(t) == loops[Ln] and entries[Ln][kn] == t
    K = len(sol)
    V = K - ssum - 5 * f[4] - 10 * f[5] - 15 * f[6]
    return K, ssum, f[4], f[5], f[6], V

def chain_roots(sol):
    roots = set()
    for (L, k, j, sk, s, t, c) in sol:
        if j is None: roots |= orbitsets[L]
        else:
            for d in range(((j - k) % NE) + 1):
                roots.add(canon(entries[L][(k + d) % NE]))
    return roots

def eligible_rows(chainL, roots):
    tot = c0 = c1 = 0
    for L in range(840):
        if L in chainL: continue
        r = len(orbitsets[L] & roots)
        if r == 0: tot += NE; c0 += 1
        elif r == 1: tot += 1; c1 += 1
    return tot, c0, c1

def report(sol, tag, annotate=True):
    K, ssum, f4, f5, f6, V = verify_mixed(sol)
    roots = chain_roots(sol)
    assert len(roots) == NE * K - ssum
    er, c0, c1 = eligible_rows(set(x[0] for x in sol), roots)
    R = (720 - NE * K + ssum) / 5
    print(f"\n--- {tag}: VERIFIED K={K} Sigma={ssum} f4={f4} f5={f5} f6={f6} "
          f"V={V} waste={862 - V / 5:g} roots={len(roots)} ---")
    print(f"    R = (720-6K+Sigma)/5 = {R:g} (integral: {R == int(R)}); "
          f"eligible rows = {er} oriented from {c0 + c1} loops "
          f"({c0} zero-root x6 + {c1} one-root x1); "
          f"loop-count feasible (c0+c1 >= R): {c0 + c1 >= R}")
    if annotate:
        for (L, k, j, sk, s, t, c) in sol:
            if j is None:
                print(f"  {fmt(L):11s} arrival k={k}  LAST (full ride, skip 0)")
            else:
                d = "" if sk == 0 and c == 3 else f"  <-- DEV cost={c} skip={sk}"
                print(f"  {fmt(L):11s} arrival k={k} exit j={j} skip={sk} "
                      f"cost{c} hop {s}->{t}{d}")
    return K, ssum, f4, er, c0, c1, R

def expand(path, li_, lk):
    sol = []
    for (i, k, j, s) in path:
        Lg = cls[i]
        sol.append((Lg, k, j, s, sources[Lg][j], door(sources[Lg][j], 3), 3))
    sol.append((cls[li_], lk, None, 0, None, None, None))
    return sol

# ---------- enumeration: chains with exact V target, cost-3 only ----------
def enum_V(target, cap=100, tl=90.0):
    out = []; t0 = time.time()
    def dfs(i, k, used, K, pen, path):
        if len(out) >= cap or time.time() - t0 > tl: return
        V = K - pen
        if V == target and pen % 5 == (K % 5 if False else pen % 5) and \
           (pen - K) % 5 == 0:
            out.append((list(path), i, k))
            if len(out) >= cap: return
        m = 120 - K
        fr = free_run(i, k, used)
        if V + m - max(0, -((fr - m) // 5)) < target: return
        for s in range(NE):
            j = (k - 1 - s) % NE
            M, ka = E3[i][j]
            if used >> M & 1: continue
            if K + 1 - pen - s > target:  # overshoot risk fine; prune V>target+slack?
                pass
            dfs(M, ka, used | (1 << M), K + 1, pen + s, path + [(i, k, j, s)])
    dfs(L0, K0, 1 << L0, 1, 0, [])
    return out

for TV in (15, 20):
    sols = enum_V(TV, cap=100)
    sig = Counter()
    er_stats = []
    for (path, li_, lk) in sols:
        sol = expand(path, li_, lk)
        K, ssum, f4, f5, f6, V = verify_mixed(sol)
        assert V == TV and (ssum - K) % 5 == 0
        sig[(K, ssum)] += 1
    print(f"\n== V7 = {TV} (waste {862 - TV // 5}, length "
          f"{5046 + 862 - TV // 5}): enumerated {len(sols)} chains (cap 100, "
          f"pivot class '7' only; x7 by isomorphism) ==")
    print(f"   signature (K, Sigma) -> count: {dict(sorted(sig.items()))}")
    if sols:
        path, li_, lk = sols[0]
        report(expand(path, li_, lk), f"V={TV} example (first found)")

# ---------- row stats for the saved best chains ----------
for fn, tag in (("best_chain.txt", "segment7 best"),
                ("beam_best_w3000.txt", "beam w=3000 best"),
                ("beam_best_w20000.txt", "beam w=20000 best")):
    try:
        sol = [ast.literal_eval(l) for l in open(fn)]
    except FileNotFoundError:
        continue
    report(sol, f"{tag} ({fn})", annotate=False)
