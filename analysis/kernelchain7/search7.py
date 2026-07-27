#!/usr/bin/env python3
"""search7.py -- n=7 max-V7 kernel-chain branch & bound.

V7 = K - Sigma_skip - 5*f4 - 10*f5 - 15*f6;  waste = 862 - V7/5.
Chains: distinct loops of ONE pivot class (pivot confinement is analytic;
within-class loop-distinct <=> orbit-disjoint by the partition gate),
starting at the identity-orbit loop at its identity entry.
Pivot classes are isomorphic (relabeling): search pivot '7' only, x7.

Analytic bound: forced (skip-0 cost-3) map has pure period 5, so any run of
consecutive forced hops spans <= 5 distinct loops.  With D deviating hops
(each penalty >= 1): K <= min(120, 5(D+1)), V <= K - D <= 97 (K=120, D=23).

B&B upper bound at a node: V + m - ceil(max(0, m - free)/5), where
m = 120 - |used| and free = fresh loops reachable by pure forced steps now.
"""
from itertools import permutations
from collections import Counter
import sys, time

N = 7; ALPHA = "1234567"; NE = 6; MAXSKIP = 5
TIME_BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 900.0

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
entries, sources, orbitsets = [], [], []
for (a, C) in loops:
    e = C + a
    es, ss, os_ = [], [], set()
    for _ in range(NE):
        es.append(e); ss.append(e[-1] + e[:-1]); os_.add(canon(e)); e = tv(e)
    entries.append(es); sources.append(ss); orbitsets.append(frozenset(os_))
def fmt(i): return f"m{loops[i][0]};{loops[i][1]}"
ID = canon(ALPHA)

# ---------------- pivot-'7' class local tables ----------------
cls = [L for L in range(840) if loops[L][0] == '7']
assert len(cls) == 120
glo = cls                      # local -> global
lidx = {L: i for i, L in enumerate(cls)}
# edge[c-3][i][j] = (m_local, ka);  t = door(sources[glo[i]][j], c)
EDGE = [[[None] * NE for _ in range(120)] for _ in range(4)]
for i, L in enumerate(cls):
    for j, s in enumerate(sources[L]):
        for c in (3, 4, 5, 6):
            t = door(s, c)
            M = loop_index[loop_of(t)]
            assert loops[M][0] == '7' and M != L
            EDGE[c - 3][i][j] = (lidx[M], entries[M].index(t))
E3 = EDGE[0]
L0g = [L for L in cls if ID in orbitsets[L]][0]
L0, K0 = lidx[L0g], [canon(e) for e in entries[L0g]].index(ID)
print(f"root: {fmt(L0g)} local {L0}, identity arrival k={K0}")

# ---------------- forced-cycle loop-sets + partition check ----------------
fsets = set()
for i in range(120):
    for k in range(NE):
        st = (i, k); seq = [i]; cur = st
        for _ in range(4):
            M, ka = E3[cur[0]][(cur[1] - 1) % NE]
            seq.append(M); cur = (M, ka)
        nxt = E3[cur[0]][(cur[1] - 1) % NE]
        assert nxt[0] == i, "period-5 loop-set assumption broken"
        fsets.add(frozenset(seq))
fsets = sorted(fsets, key=sorted)
cover_cnt = Counter()
for s in fsets:
    for x in s: cover_cnt[x] += 1
print(f"forced 5-cycles per class: 144 states-cycles, distinct loop-sets = "
      f"{len(fsets)}; loop membership multiplicity dist = "
      f"{dict(sorted(Counter(cover_cnt.values()).items()))}")
# exact cover: partition 120 loops into 24 disjoint forced loop-sets?
bysym = [[] for _ in range(120)]
for si, s in enumerate(fsets):
    for x in s: bysym[x].append(si)
sol_part = []
def cover(remmask, chosen):
    if remmask == 0:
        sol_part.append(list(chosen)); return True
    x = (remmask & -remmask).bit_length() - 1
    for si in bysym[x]:
        m = 0
        for y in fsets[si]: m |= 1 << y
        if m & ~remmask: continue
        chosen.append(si)
        if cover(remmask & ~m, chosen): return True
        chosen.pop()
    return False
t0 = time.time()
has_part = cover((1 << 120) - 1, [])
print(f"partition of 120 loops into 24 disjoint forced loop-sets exists: "
      f"{has_part}  ({time.time()-t0:.2f}s)")

# ---------------- B&B ----------------
# move list per (k): (pen, c, j) sorted by pen; j = (k-1-s) % 6
MOVES = []
for k in range(NE):
    mv = []
    for c in (3, 4, 5, 6):
        for s in range(NE):
            j = (k - 1 - s) % NE
            mv.append((s + 5 * (c - 3), c, s, j))
    mv.sort()
    MOVES.append(mv)

def free_run(i, k, used):
    cnt = 0
    for _ in range(4):
        M, ka = E3[i][(k - 1) % NE]
        if used >> M & 1: break
        cnt += 1; i, k = M, ka
    return cnt

best = [5, None]           # standard kernel gives V=5 as seed floor
witnesses = []             # chains achieving current best
nodes = [0]; t_start = time.time(); complete = [True]
next_report = [t_start + 15.0]

def dfs(i, k, used, ucount, pen, path):
    nodes[0] += 1
    if not nodes[0] & 0xFFFF:
        now = time.time()
        if now > t_start + TIME_BUDGET:
            complete[0] = False
            raise TimeoutError
        if now > next_report[0]:
            next_report[0] = now + 15.0
            print(f"  [t+{now-t_start:6.0f}s] nodes={nodes[0]:,} bestV={best[0]} "
                  f"depth={ucount} pen={pen}", flush=True)
    V = ucount - pen
    if V > best[0]:
        best[0] = V; best[1] = (list(path), i, k)
        witnesses.clear()
        print(f"  new bestV = {V} (K={ucount}, pen={pen}) "
              f"t+{time.time()-t_start:.1f}s", flush=True)
    if V == best[0] and len(witnesses) < 100:
        witnesses.append((list(path), i, k))
    m = 120 - ucount
    fr = free_run(i, k, used)
    ub = V + m - max(0, -((fr - m) // 5))
    if ub <= best[0]:
        return
    for (pa, c, s, j) in MOVES[k]:
        if V + m - pa <= best[0]:  # child ub <= V+1-pa + (m-1) = V+m-pa
            break                  # moves sorted by pen ascending
        M, ka = EDGE[c - 3][i][j]
        if used >> M & 1:
            continue
        dfs(M, ka, used | (1 << M), ucount + 1, pen + pa,
            path + [(i, k, j, s, c)])

print(f"\n== B&B max V7 (budget {TIME_BUDGET:.0f}s) ==", flush=True)
try:
    dfs(L0, K0, 1 << L0, 1, 0, [])
except TimeoutError:
    pass
el = time.time() - t_start
print(f"max V7 found = {best[0]}; complete (PROOF): {complete[0]}; "
      f"nodes={nodes[0]:,} ({el:.1f}s)")
print(f"analytic bound: V7 <= 97 (K<=120, runs<=5 => D>=ceil(K/5)-1, "
      f"V<=K-D; max at K=120,D=23)")
print(f"witnesses at V={best[0]} collected: {len(witnesses)}")

# ---------------- verification + reporting ----------------
def expand(sol):
    """(path, last_i, last_k) -> list of (Lglobal, k, j, skip, src, tgt, c),
    last element j=None."""
    path, li, lk = sol
    out = []
    for (i, k, j, s, c) in path:
        Lg = glo[i]
        out.append((Lg, k, j, s, sources[Lg][j], door(sources[Lg][j], c), c))
    out.append((glo[li], lk, None, 0, None, None, None))
    return out

def verify_mixed(sol):
    L0_, k0_ = sol[0][0], sol[0][1]
    assert canon(entries[L0_][k0_]) == ID
    piv = loops[L0_][0]
    seenL, orbs, ssum = set(), set(), 0
    f = Counter()
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
    return K, ssum, f[3], f[4], f[5], f[6], V

def chain_roots(sol):
    roots = set()
    for (L, k, j, sk, s, t, c) in sol:
        if j is None:
            roots |= orbitsets[L]
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
    K, ssum, f3, f4, f5, f6, V = verify_mixed(sol)
    roots = chain_roots(sol)
    assert len(roots) == NE * K - ssum
    er, c0, c1 = eligible_rows(set(x[0] for x in sol), roots)
    R = (720 - NE * K + ssum) / 5
    print(f"\n--- {tag}: VERIFIED  K={K} Sigma={ssum} f4={f4} f5={f5} f6={f6} "
          f"V={V} waste={862 - V/5} roots={len(roots)} ---")
    print(f"  R needed = (720-6K+Sigma)/5 = {R}; integral: {R == int(R)}; "
          f"eligible rows = {er} oriented from {c0+c1} loops "
          f"({c0} zero-root x6, {c1} one-root x1); "
          f"loop-count feasible (c0+c1 >= R): {c0 + c1 >= R}")
    if annotate:
        for (L, k, j, sk, s, t, c) in sol:
            if j is None:
                print(f"  {fmt(L):11s} arrival k={k}  LAST (full ride, skip 0)")
            else:
                d = "" if sk == 0 and c == 3 else f"  <-- DEV cost={c} skip={sk}"
                print(f"  {fmt(L):11s} arrival k={k} exit j={j} skip={sk} "
                      f"cost{c} hop {s}->{t}{d}")

if best[1]:
    report(expand(best[1]), f"best chain, V={best[0]}")
sig = Counter()
for wsol in witnesses:
    K, ssum, f3, f4, f5, f6, V = verify_mixed(expand(wsol))
    sig[(K, ssum, f4, f5, f6)] += 1
print(f"\nwitness census at V={best[0]} (K,Sigma,f4,f5,f6) -> count: "
      f"{dict(sig)}  [not exhaustive unless proof complete]")

# ---------------- targeted small chains: V=15 and V=20 examples ----------------
def find_exact(K_t, S_t, cap=100, tl=60.0):
    """cost-3-only chains, K=K_t loops, Sigma=S_t exactly; cap solutions."""
    out = []; t0 = time.time()
    def d2(i, k, used, ucount, ssum, path):
        if len(out) >= cap or time.time() - t0 > tl: return
        if ucount == K_t:
            if ssum == S_t: out.append((list(path), i, k))
            return
        rem = K_t - ucount
        fr = free_run(i, k, used)
        # need at least ceil((rem - fr)/5) more skip; prune on budget
        if ssum + max(0, -((fr - rem) // 5)) > S_t: return
        for s in range(NE):
            if ssum + s > S_t: break
            j = (k - 1 - s) % NE
            M, ka = E3[i][j]
            if used >> M & 1: continue
            d2(M, ka, used | (1 << M), ucount + 1, ssum + s,
               path + [(i, k, j, s, 3)])
    d2(L0, K0, 1 << L0, 1, 0, [])
    return out

for (Kt, St, tag) in [(18, 3, "V=15 (5905-class)"), (24, 4, "V=20 (5904-class)")]:
    if best[0] < Kt - St: continue
    sols = find_exact(Kt, St)
    print(f"\n== {tag}: K={Kt} Sigma={St} cost-3 only: found {len(sols)} "
          f"(cap 100) in this class (x7 pivots by isomorphism) ==")
    if sols:
        report(expand(sols[0]), f"{tag} example")
