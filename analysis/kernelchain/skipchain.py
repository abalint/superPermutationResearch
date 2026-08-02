#!/usr/bin/env python3
"""skipchain.py -- waste-ledger (skip-priced) kernel-chain search.
Follow-up to chain.py (same core model).

Definitions (corrected ledger):
  A chain loop arrived at entry index k with outgoing hop replacing splice j
  (hop source = s_j) rides e_k -> ... -> e_j, covering ((j-k)%5)+1 entries.
  skip = 4 - ((j-k)%5).  Full ride (skip 0) <=> j = (k-1)%5 (standard relation).
  Last loop: no outgoing hop, full ride, skip 0.
  First loop L_0: contains the identity orbit (orbit of 123456); arrival
  entry = that orbit's entry in L_0.

  waste = 148 - K/4 + Sigma_skip/4   (needs Sigma_skip == K mod 4)
  roots (ridden kernel orbits) = 5K - Sigma_skip
  rows needed R = (120 - 5K + Sigma_skip)/4;  for K-Sigma=8: R = 28 - K.
  TARGET waste 146  <=>  K - Sigma_skip = 8.
"""
from itertools import permutations
from collections import Counter
import sys, time

ALPHA = "123456"
# s64 P1: ONE copy of the rotation-frame quartet, in pylib/canonical.py.
# `canon` here is the least-ROTATION canon -- NOT m3_check's relabel+reversal
# canon.  pylib keeps the two apart by name (canon_rotation vs
# canon_relabel_rev); the local alias preserves every call site below.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
from pylib.canonical import canon_rotation as canon, door, loop_of, tv  # noqa: E402,F401

# ---------------------------------------------------------------- loops
loops = []
for pivot in ALPHA:
    rest = [c for c in ALPHA if c != pivot]
    seen = set()
    for p in permutations(rest):
        nk = canon("".join(p))
        if nk not in seen:
            seen.add(nk)
            loops.append((pivot, nk))
assert len(loops) == 144
loop_index = {lp: i for i, lp in enumerate(loops)}

entries, sources, orbitsets = [], [], []
for (a, C) in loops:
    e = C + a
    es, ss, os_ = [], [], set()
    for _ in range(5):
        es.append(e)
        ss.append(e[-1] + e[:-1])
        os_.add(canon(e))
        assert door(ss[-1], 2) == tv(e)
        e = tv(e)
    assert len(os_) == 5
    entries.append(es); sources.append(ss); orbitsets.append(frozenset(os_))

def fmt(i): return f"m{loops[i][0]};{loops[i][1]}"

# ------------------------------- cost-3 hop edges, arrival-entry indexed
# E3k[L] = list of (exit_splice j, src, tgt, M, arrival_entry k_of_M)
E3k = [[] for _ in range(144)]
for L in range(144):
    for j, s in enumerate(sources[L]):
        t = door(s, 3)
        M = loop_index[loop_of(t)]
        if M != L:
            E3k[L].append((j, s, t, M, entries[M].index(t)))

# ------------------------------------------------------------ pivot facts
print("== PIVOT FACTS ==")
pp = all(loops[M][0] == loops[L][0] for L in range(144) for (_,_,_,M,_) in E3k[L])
print(" all cost-3 hops preserve pivot:", pp)
part_ok = True
for a in ALPHA:
    cls = [L for L in range(144) if loops[L][0] == a]
    u = set(); dis = True
    for L in cls:
        if orbitsets[L] & u: dis = False
        u |= orbitsets[L]
    if not (dis and len(u) == 120 and len(cls) == 24): part_ok = False
print(" each pivot class (24 loops) partitions all 120 orbits:", part_ok)

ID = canon("123456")
id_loops = {}
for a in ALPHA:
    ls = [L for L in range(144) if loops[L][0] == a and ID in orbitsets[L]]
    assert len(ls) == 1, (a, ls)
    L = ls[0]
    k = [canon(e) for e in entries[L]].index(ID)
    id_loops[a] = (L, k)
    print(f" pivot {a}: identity-orbit loop {fmt(L)}, identity entry index {k}"
          f" (entry word {entries[L][k]})")

# --------------------------------------------- forced (skip-0) structure
print("\n== FORCED (skip-0) STRUCTURE ==")
def forced_step(L, k):
    j = (k + 4) % 5
    for (jj, s, t, M, ka) in E3k[L]:
        if jj == j:
            return (M, ka)
    return None

periods = Counter()
for L in range(144):
    for k in range(5):
        st = (L, k); seen = {st: 0}; n = 0; cur = st
        while True:
            cur = forced_step(*cur)
            n += 1
            if cur is None:
                periods["undef"] += 1; break
            if cur in seen:
                periods[n - seen[cur]] += 1; break
            seen[cur] = n
print(" forced-map cycle periods over 720 (loop,arrival) states:", dict(periods))

def forced_run(L, k):
    seen = {L}; cur = (L, k)
    while True:
        nxt = forced_step(*cur)
        if nxt is None or nxt[0] in seen:
            return len(seen)
        seen.add(nxt[0]); cur = nxt

rl = Counter(forced_run(L, k) for L in range(144) for k in range(5))
print(" forced-run length (distinct loops) distribution:", dict(sorted(rl.items())))
runcap = max(rl)
print(f" => forced-run cap = {runcap} loops (K=12 needs >= 2 deviating hops)")

# ------------------------------------------------------ skip availability
print("\n== SKIP AVAILABILITY per (loop, arrival k) state ==")
valid = [set(j for (j, *_ ) in E3k[L]) for L in range(144)]
print(" valid-exit-splice count per loop:",
      dict(sorted(Counter(len(v) for v in valid).items())))
setdist = Counter(); percount = Counter(); skip0avail = 0
for L in range(144):
    for k in range(5):
        ss = frozenset(4 - ((j - k) % 5) for j in valid[L])
        dev = tuple(sorted(s for s in ss if s > 0))
        setdist[dev] += 1
        for s in dev: percount[s] += 1
        if 0 in ss: skip0avail += 1
print(" deviating-skip-set distribution over 720 states:", dict(setdist))
print(" availability of each deviating skip s (states/720):",
      {s: percount[s] for s in (1, 2, 3, 4)})
print(" states with skip-0 (forced) exit available:", skip0avail, "/720")

# --------------------------------------------- standard kernel sanity K=4
print("\n== STANDARD KERNEL SANITY (K=4, Sigma_skip must be 0) ==")
gate = [("6","12345"), ("6","15234"), ("6","12534"), ("6","12354")]
hops = [("651234","234156"), ("652341","341256"), ("653412","412356")]
gl = [loop_index[g] for g in gate]
k = entries[gl[0]].index("123456")
assert canon(entries[gl[0]][k]) == ID
tot = 0; ok = True
for h, (src, tgt) in enumerate(hops):
    L = gl[h]
    j = sources[L].index(src)
    sk = 4 - ((j - k) % 5)
    tot += sk
    print(f" loop {fmt(L)}: arrival k={k}, exit splice j={j}, skip={sk}")
    if sk != 0: ok = False
    t = door(src, 3)
    M = loop_index[loop_of(t)]
    assert M == gl[h+1] and t == tgt
    k = entries[M].index(t)
print(f" loop {fmt(gl[3])}: arrival k={k}, last loop (full ride, skip 0)")
print(f" Sigma_skip = {tot}; waste = 148 - 4/4 + {tot}/4 = {147 + tot/4}"
      f"   {'OK' if ok and tot == 0 else 'FAIL'}")

# ------------------------------------------------------------- chain DFS
def search_chains(a, K, budget, cap_count=1000, keep=1000, deadline=None):
    """chains of K distinct loops in pivot class a, starting at the
    identity-orbit loop at its identity entry, Sigma_skip == budget exactly.
    Element: (loop, arrival k, exit j, skip, hopsrc, hoptgt); last has j None.
    Returns (count, sols, skip-pattern counter, complete_flag)."""
    L0, k0 = id_loops[a]
    sols, cnt, patt = [], [0], Counter()
    complete = [True]
    def dfs(cur, k, used, ssum, path):
        if deadline and time.time() > deadline:
            complete[0] = False; return
        if len(used) == K:
            if ssum == budget:
                cnt[0] += 1
                patt[tuple(x[3] for x in path if x[3] > 0)] += 1
                if len(sols) < keep:
                    sols.append(path + [(cur, k, None, 0, None, None)])
            return
        if cnt[0] >= cap_count:
            complete[0] = False; return
        for (j, s, t, M, ka) in E3k[cur]:
            if M in used:
                continue
            sk = 4 - ((j - k) % 5)
            if ssum + sk > budget:
                continue
            dfs(M, ka, used | {M}, ssum + sk, path + [(cur, k, j, sk, s, t)])
    dfs(L0, k0, frozenset({L0}), 0, [])
    return cnt[0], sols, patt, complete[0]

# ------------------------------------------- independent chain verifier
def verify_chain(sol):
    """Re-derive everything from raw strings; raise on any inconsistency."""
    L0, k0, *_ = sol[0]
    assert canon(entries[L0][k0]) == ID, "L_0 arrival is not the identity entry"
    piv = loops[L0][0]
    seenL = set(); orbs = set(); ssum = 0
    for idx, (L, k, j, sk, s, t) in enumerate(sol):
        assert loops[L][0] == piv
        assert L not in seenL; seenL.add(L)
        assert not (orbitsets[L] & orbs); orbs |= orbitsets[L]
        if j is None:
            assert idx == len(sol) - 1 and sk == 0
            continue
        assert s == sources[L][j] and t == door(s, 3)
        assert sk == 4 - ((j - k) % 5) and 0 <= sk <= 4
        ssum += sk
        Lnxt, knxt, *_ = sol[idx + 1]
        assert loop_of(t) == loops[Lnxt] and entries[Lnxt][knxt] == t
    return len(sol), ssum

def chain_roots(sol):
    roots = set()
    for (L, k, j, sk, s, t) in sol:
        if j is None:
            roots |= orbitsets[L]
        else:
            for d in range(((j - k) % 5) + 1):
                roots.add(canon(entries[L][(k + d) % 5]))
    return roots

def eligible_rows(chain_loops, roots):
    """(oriented_rows, loops_with_0_roots, loops_with_1_root)."""
    tot = c0 = c1 = 0
    for L in range(144):
        if L in chain_loops: continue
        r = len(orbitsets[L] & roots)
        if r == 0: tot += 5; c0 += 1
        elif r == 1: tot += 1; c1 += 1
    return tot, c0, c1

def row_stats(sol):
    K, ssum = verify_chain(sol)
    chainL = set(x[0] for x in sol)
    roots = chain_roots(sol)
    assert len(roots) == 5 * K - ssum
    er, c0, c1 = eligible_rows(chainL, roots)
    R = (120 - 5 * K + ssum) // 4
    return K, ssum, roots, er, c0, c1, R

def report_example(sol, tag):
    K, ssum, roots, er, c0, c1, R = row_stats(sol)
    print(f"\n --- {tag}: K={K}, Sigma_skip={ssum}, roots={len(roots)}, "
          f"waste={148 - K / 4 + ssum / 4} ---")
    for (L, k, j, sk, s, t) in sol:
        if j is None:
            print(f"  {fmt(L):11s} arrival k={k}  LAST (full ride, skip 0)")
        else:
            tag2 = "" if sk == 0 else f"  <-- DEVIATION skip={sk}"
            print(f"  {fmt(L):11s} arrival k={k} exit j={j} skip={sk} "
                  f"hop {s}->{t}{tag2}")
    print(f"  eligible rows: {er} oriented, from {c0 + c1} loops "
          f"({c0} loops 0-root x5, {c1} loops 1-root x1); "
          f"non-root orbits={120 - len(roots)}; R needed={R}; "
          f"loop-count feasible (>=R loops): {c0 + c1 >= R}")

# ------------------------------------------------------- targeted checks
print("\n== K=8 / Sigma_skip=0 (should be impossible) ==")
print(" chains found:", sum(search_chains(a, 8, 0)[0] for a in ALPHA))

print("\n== MAIN: K=12, Sigma_skip=4 (exhaustive per pivot) ==")
g12 = 0
for a in ALPHA:
    c, ex, patt, comp = search_chains(a, 12, 4, cap_count=10**9)
    g12 += c
    print(f" pivot {a}: count={c} complete={comp}")
print(" TOTAL K=12/Sigma=4:", g12)

print("\n== FALLBACK: K=16, Sigma_skip=8 (exhaustive per pivot) ==")
g16 = 0
for a in ALPHA:
    c, ex, patt, comp = search_chains(a, 16, 8, cap_count=10**9)
    g16 += c
    print(f" pivot {a}: count={c} complete={comp}")
print(" TOTAL K=16/Sigma=8:", g16)

# ---------------------- enumeration of all K with K - Sigma_skip = 8
print("\n== ENUMERATION: chains with K - Sigma_skip = 8, by K "
      "(cap 1000/pivot, 60s/K) ==")
best_row = None          # maximize eligible row-loop count minus R
sols_by_K = {}
for K in range(9, 25):
    budget = K - 8
    dl = time.time() + 60
    tot = 0; allsols = []; pats = Counter(); compK = True
    for a in ALPHA:
        c, ex, p, comp = search_chains(a, K, budget, cap_count=1000,
                                       keep=200, deadline=dl)
        tot += c; pats += p; compK = compK and comp
        allsols += ex
    sols_by_K[K] = allsols
    if tot:
        # row feasibility scan over collected solutions
        bestloc = None
        for sol in allsols:
            Kv, sv, roots, er, c0, c1, R = row_stats(sol)
            score = (c0 + c1) - R
            if bestloc is None or score > bestloc[0]:
                bestloc = (score, er, c0 + c1, R, sol)
            if best_row is None or score > best_row[0]:
                best_row = (score, er, c0 + c1, R, sol)
        print(f" K={K:2d} Sigma={budget:2d}: count={tot}"
              f"{'' if compK else '+ (capped/timeout)'} patterns(top5)="
              f"{dict(sorted(pats.items(), key=lambda x: -x[1])[:5])}")
        print(f"      row-scan over {len(allsols)} sols: best (eligible loops - R)"
              f" = {bestloc[0]}  (eligible loops={bestloc[2]}, oriented={bestloc[1]},"
              f" R={bestloc[3]})")
    else:
        print(f" K={K:2d} Sigma={budget:2d}: count=0"
              f"{'' if compK else ' (INCOMPLETE: timeout)'}")

# ------------------- absolute max K - Sigma_skip, instrumented for proof
print("\n== ABSOLUTE MAX K - Sigma_skip (branch & bound, 240s) ==")
best = [0, None]; deadline = time.time() + 240; completed = [True]
def dfs2(cur, k, used, ssum, path, a):
    if time.time() > deadline:
        completed[0] = False; return
    val = len(used) - ssum
    if val > best[0]:
        best[0] = val
        best[1] = (a, list(path) + [(cur, k, None, 0, None, None)])
    if 24 - ssum <= best[0]:
        return
    for (j, s, t, M, ka) in E3k[cur]:
        if M in used: continue
        sk = 4 - ((j - k) % 5)
        dfs2(M, ka, used | {M}, ssum + sk, path + [(cur, k, j, sk, s, t)], a)
t0 = time.time()
for a in ALPHA:
    L0, k0 = id_loops[a]
    dfs2(L0, k0, frozenset({L0}), 0, [], a)
print(f" max K - Sigma_skip = {best[0]}; search completed (proof): {completed[0]}"
      f"  ({time.time() - t0:.1f}s)")
a, solmax = best[1]
Kb = len(solmax); sb = sum(x[3] for x in solmax)
print(f" achieved at K={Kb}, Sigma={sb} (pivot {a}); "
      f"waste = 148 - {best[0]}/4 = {148 - best[0] / 4}; "
      f"K==Sigma mod 4: {(Kb - sb) % 4 == 0}")

# --------------------------------------------------------- example reports
print("\n== EXAMPLES (independently verified) ==")
shown = 0
for K in sorted(sols_by_K):
    if sols_by_K[K] and shown < 2:
        report_example(sols_by_K[K][0], f"smallest-K example, K={K}")
        shown += 1
if best_row is not None:
    report_example(best_row[4], "best row-feasibility chain found")

# ======================================================================
# COST-4 / COST-5 EXTENSION (cross-cost ledger)
#   ledger: cost-3 hop = baseline; cost-4 wastes +1 vs cost-3, cost-5 +2.
#   waste = 148 - K/4 + Sigma_skip/4 + f4 + 2*f5
#   target waste 146  <=>  V := K - Sigma_skip - 4*f4 - 8*f5 >= 8
#   (R = (120-5K+Sigma)/4 unchanged; V=8 => K-Sigma = 8+4*f4+8*f5 == 0 mod 4,
#    so R integrality is automatic on V=8.)
# ======================================================================
print("\n" + "=" * 70)
print("== COST-4 / COST-5 HOP CHARACTERIZATION ==")

def hop_edges_cost(c):
    E = [[] for _ in range(144)]
    selfh = 0; pivchange = 0
    for L in range(144):
        for j, s in enumerate(sources[L]):
            t = door(s, c)
            M = loop_index[loop_of(t)]
            assert t in entries[M], "hop target is not an entry"
            if loops[M][0] != loops[L][0]: pivchange += 1
            if M == L: selfh += 1
            else: E[L].append((j, s, t, M, entries[M].index(t)))
    return E, selfh, pivchange

E4k, sh4, pc4 = hop_edges_cost(4)
E5k, sh5, pc5 = hop_edges_cost(5)
print(f" cost-4: pivot-changing hops = {pc4}/720, self-loop (M==L) hops = {sh4},"
      f" usable edges = {sum(len(x) for x in E4k)}")
print(f" cost-5: pivot-changing hops = {pc5}/720, self-loop hops = {sh5},"
      f" usable edges = {sum(len(x) for x in E5k)}")
print(" analytic: door(s,c) = s[c:]+s[:c][::-1] ends with s[0] = pivot for every"
      " c>=1,")
print("           so NO hop of ANY cost ever leaves the pivot class.")
print(" every hop target ends in the pivot => always an entry of its loop;"
      " same skip accounting applies (asserted).")

inter = Counter()
for La in range(144):
    for Lb in range(La + 1, 144):
        if loops[La][0] != loops[Lb][0]:
            inter[len(orbitsets[La] & orbitsets[Lb])] += 1
print(" cross-pivot loop-pair orbit-intersection distribution:",
      dict(sorted(inter.items())))

# mixed edge set: (j, s, t, M, ka, cost)
MIX = [[] for _ in range(144)]
for L in range(144):
    for e in E3k[L]: MIX[L].append(e + (3,))
    for e in E4k[L]: MIX[L].append(e + (4,))
    for e in E5k[L]: MIX[L].append(e + (5,))
PEN = {3: 0, 4: 4, 5: 8}

def verify_mixed(sol):
    L0, k0 = sol[0][0], sol[0][1]
    assert canon(entries[L0][k0]) == ID
    piv = loops[L0][0]
    seenL = set(); orbs = set(); ssum = 0; f4 = f5 = 0
    for idx, (L, k, j, sk, s, t, c) in enumerate(sol):
        assert loops[L][0] == piv
        assert L not in seenL; seenL.add(L)
        assert not (orbitsets[L] & orbs); orbs |= orbitsets[L]
        if j is None:
            assert idx == len(sol) - 1 and sk == 0
            continue
        assert s == sources[L][j] and t == door(s, c)
        assert sk == 4 - ((j - k) % 5)
        ssum += sk
        if c == 4: f4 += 1
        elif c == 5: f5 += 1
        Ln, kn = sol[idx + 1][0], sol[idx + 1][1]
        assert loop_of(t) == loops[Ln] and entries[Ln][kn] == t
    return len(sol), ssum, f4, f5

def mixed_roots(sol):
    roots = set()
    for (L, k, j, sk, s, t, c) in sol:
        if j is None:
            roots |= orbitsets[L]
        else:
            for d in range(((j - k) % 5) + 1):
                roots.add(canon(entries[L][(k + d) % 5]))
    return roots

def mixed_rowstats(sol):
    K = len(sol); ssum = sum(x[3] for x in sol)
    f4 = sum(1 for x in sol if x[6] == 4)
    f5 = sum(1 for x in sol if x[6] == 5)
    chainL = set(x[0] for x in sol)
    roots = mixed_roots(sol)
    er, c0, c1 = eligible_rows(chainL, roots)
    R = (120 - 5 * K + ssum) // 4
    return K, ssum, f4, f5, er, c0, c1, R

# ---------------- PASS 1: prove max V over mixed-cost chains -----------
print("\n== PASS 1: max V = K - Sigma - 4*f4 - 8*f5 (B&B, best-prune) ==")
bestV = [0, None]; deadline1 = [time.time() + 300]; comp1 = [True]
def dfsV(cur, k, used, pen, path):
    if time.time() > deadline1[0]:
        comp1[0] = False; return
    V = len(used) - pen
    if V > bestV[0]:
        bestV[0] = V
        bestV[1] = list(path) + [(cur, k, None, 0, None, None, None)]
    if 24 - pen <= bestV[0]:
        return
    for (j, s, t, M, ka, c) in MIX[cur]:
        if M in used: continue
        d = 4 - ((j - k) % 5) + PEN[c]
        dfsV(M, ka, used | {M}, pen + d, path + [(cur, k, j, 4 - ((j - k) % 5), s, t, c)])
t0 = time.time()
for a in ALPHA:
    L0, k0 = id_loops[a]
    dfsV(L0, k0, frozenset({L0}), 0, [])
print(f" max V = {bestV[0]}; complete (proof): {comp1[0]}  ({time.time()-t0:.1f}s)")

# ---------------- PASS 2: enumerate ALL V=8 chains, row-scan -----------
print("\n== PASS 2: enumerate all V=8 chains (any cost mix), row feasibility ==")
TARGET = 8
sig = Counter()          # (K, Sigma, f4, f5) -> count
cnt8 = [0]; evals = [0]; EVCAP = 500000
best_score = [None]      # (score, stats, sol)
best_by_sig = {}
comp2 = [True]; deadline2 = [time.time() + 480]
def dfs8(cur, k, used, pen, path):
    if time.time() > deadline2[0]:
        comp2[0] = False; return
    V = len(used) - pen
    if V >= TARGET:
        sol = list(path) + [(cur, k, None, 0, None, None, None)]
        cnt8[0] += 1
        if evals[0] < EVCAP:
            evals[0] += 1
            K, ssum, f4, f5, er, c0, c1, R = mixed_rowstats(sol)
            sig[(K, ssum, f4, f5)] += 1
            score = (c0 + c1) - R
            key = (K, ssum, f4, f5)
            if key not in best_by_sig or score > best_by_sig[key][0]:
                best_by_sig[key] = (score, er, c0, c1, R, sol)
            if best_score[0] is None or score > best_score[0][0]:
                best_score[0] = (score, (K, ssum, f4, f5, er, c0, c1, R), sol)
    if 24 - pen < TARGET:
        return
    for (j, s, t, M, ka, c) in MIX[cur]:
        if M in used: continue
        sk = 4 - ((j - k) % 5)
        dfs8(M, ka, used | {M}, pen + sk + PEN[c],
             path + [(cur, k, j, sk, s, t, c)])
t0 = time.time()
for a in ALPHA:
    L0, k0 = id_loops[a]
    dfs8(L0, k0, frozenset({L0}), 0, [])
print(f" V=8 chains found: {cnt8[0]} (row-scanned {evals[0]});"
      f" complete: {comp2[0]}  ({time.time()-t0:.1f}s)")
print(" signature (K, Sigma, f4, f5) -> count:")
for kk in sorted(sig):
    sc = best_by_sig[kk]
    print(f"  K={kk[0]:2d} Sigma={kk[1]:2d} f4={kk[2]} f5={kk[3]}: count={sig[kk]:6d}"
          f"  best (eligible-loops - R) = {sc[0]}"
          f" (elig loops={sc[2]+sc[3]}, oriented={sc[1]}, R={sc[4]})")
if best_score[0] is not None:
    score, stats, sol = best_score[0]
    K, ssum, f4, f5, er, c0, c1, R = stats
    verify_mixed(sol)
    print(f"\n best row-feasibility V=8 chain: score={score} "
          f"(K={K}, Sigma={ssum}, f4={f4}, f5={f5}; eligible loops={c0+c1},"
          f" oriented={er}, R={R}) -- verified")
    for (L, k, j, sk, s, t, c) in sol:
        if j is None:
            print(f"  {fmt(L):11s} arrival k={k}  LAST (full ride, skip 0)")
        else:
            d = "" if sk == 0 and c == 3 else f"  <-- cost={c} skip={sk}"
            print(f"  {fmt(L):11s} arrival k={k} exit j={j} skip={sk} cost{c} "
                  f"hop {s}->{t}{d}")
    print(f" VERDICT input: loop-count feasible (>= R distinct row loops): "
          f"{c0 + c1 >= R}")
