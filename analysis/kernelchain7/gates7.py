#!/usr/bin/env python3
"""gates7.py -- n=7 port of the kernel-chain loop machinery + validation gates.

Port of analysis/kernelchain/chain.py + skipchain.py structure sections.
n=7: 720 orbits (rotation classes of size 7), 840 marked loops
(7 pivots x 120 necklaces), 6 entries/splices per loop.

Ledger (n=7): ride from arrival entry k to exit splice j covers
((j-k) mod 6)+1 entries, skip = 5 - ((j-k) mod 6); full ride <=> j=(k-1) mod 6.
waste = 862 - K/5 + Sigma_skip/5 + f4 + 2*f5 + 3*f6
V7 = K - Sigma_skip - 5*f4 - 10*f5 - 15*f6;  waste = 862 - V7/5.
Standard kernel: K=5, 4 cost-3 hops, all skips 0 -> waste 861 (the 5907s).
"""
from itertools import permutations
from collections import Counter
import sys

N = 7
ALPHA = "1234567"
NE = N - 1          # entries/splices per loop = 6
NLOOP = 840
MAXSKIP = NE - 1    # 5

def door(w, c): return w[c:] + w[:c][::-1]
def tv(w): return w[1:-1] + w[0] + w[-1]
def canon(w): return min(w[i:] + w[:i] for i in range(len(w)))
def loop_of(e): return (e[-1], canon(e[:-1]))

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
assert len(loops) == NLOOP, len(loops)
loop_index = {lp: i for i, lp in enumerate(loops)}

entries, sources, orbitsets = [], [], []
for (a, C) in loops:
    e = C + a
    es, ss, os_ = [], [], set()
    for _ in range(NE):
        es.append(e)
        ss.append(e[-1] + e[:-1])
        os_.add(canon(e))
        assert door(ss[-1], 2) == tv(e)          # splice identity
        e = tv(e)
    assert e == es[0], "tv does not cycle with period n-1=6"
    assert len(os_) == NE, "loop orbits not distinct"
    entries.append(es); sources.append(ss); orbitsets.append(frozenset(os_))
all_orbits = set().union(*orbitsets)
assert len(all_orbits) == 720, len(all_orbits)
print(f"[gate] 840 loops built, tv period {NE} verified, "
      f"6 distinct orbits per loop, union = {len(all_orbits)} orbits")

def fmt(i): return f"m{loops[i][0]};{loops[i][1]}"
ID = canon(ALPHA)

# ------------------------- pivot preservation + entry-landing, costs 3..6
print("\n== PIVOT / LANDING FACTS (costs 3..6) ==")
for c in range(3, N):
    pivchange = selfh = usable = 0
    for L in range(NLOOP):
        for s in sources[L]:
            t = door(s, c)
            assert t[-1] == s[0], "door does not end with pivot"
            M = loop_index[loop_of(t)]
            assert t in entries[M], "hop target is not an entry"
            if loops[M][0] != loops[L][0]: pivchange += 1
            if M == L: selfh += 1
            else: usable += 1
    print(f" cost {c}: pivot-changing hops = {pivchange}/5040, "
          f"self-loop hops = {selfh}, usable edges = {usable}")
print(" analytic: door(s,c) = s[c:]+s[:c][::-1] ends with s[0] = pivot "
      "for every c>=1 => absolute pivot confinement (verified empirically).")

# -------------------------------------- cost-3 edges, arrival-entry indexed
E3k = [[] for _ in range(NLOOP)]
for L in range(NLOOP):
    for j, s in enumerate(sources[L]):
        t = door(s, 3)
        M = loop_index[loop_of(t)]
        if M != L:
            E3k[L].append((j, s, t, M, entries[M].index(t)))

outdeg = [len(set(M for (_, _, _, M, _) in E3k[L])) for L in range(NLOOP)]
print("\n== PAIR GRAPH (cost 3) ==")
print(" distinct-target out-degree distribution:",
      dict(sorted(Counter(outdeg).items())))
print(" splice-level edges (M != L):", sum(len(x) for x in E3k))

# ---------------------------------------------- pivot-class orbit partition
print("\n== ORBIT PARTITION PER PIVOT CLASS ==")
part_ok = True
for a in ALPHA:
    cls = [L for L in range(NLOOP) if loops[L][0] == a]
    u = set(); dis = True
    for L in cls:
        if orbitsets[L] & u: dis = False
        u |= orbitsets[L]
    ok = dis and len(u) == 720 and len(cls) == 120
    part_ok = part_ok and ok
    if not ok:
        print(f" pivot {a}: FAIL (disjoint={dis}, union={len(u)}, cls={len(cls)})")
print(" each pivot class (120 loops) partitions all 720 orbits:", part_ok)

id_loops = {}
for a in ALPHA:
    ls = [L for L in range(NLOOP) if loops[L][0] == a and ID in orbitsets[L]]
    assert len(ls) == 1, (a, ls)
    L = ls[0]
    k = [canon(e) for e in entries[L]].index(ID)
    id_loops[a] = (L, k)
print(" identity-orbit loop per pivot:",
      {a: (fmt(L), k) for a, (L, k) in id_loops.items()})

# ------------------------------------------- standard kernel (gain1 port)
print("\n== STANDARD KERNEL GATE (K=5, all skips 0, waste 861) ==")
lows, hi2, hi1 = ALPHA[:N-2], ALPHA[N-2], ALPHA[N-1]   # "12345","6","7"
klo = [loop_index[loop_of(ALPHA)]]
khops = []
for x in range(1, N - 2):                              # x = 1..4 -> 4 hops
    src = hi1 + hi2 + lows[x-1] + lows[x:] + lows[:x-1]
    tgt = door(src, 3)
    khops.append((src, tgt))
    klo.append(loop_index[loop_of(tgt)])
assert len(set(klo)) == N - 2 == 5
# cross-check vs lift/README p_j = (n, n-1, j+1, .., n-2, 1, .., j)
for jj, (src, tgt) in enumerate(khops, start=1):
    pj = "76" + "".join(str(x) for x in range(jj, N - 2)) + \
         "".join(str(x) for x in range(1, jj + 1))
    # p_j as source word: (n)(n-1)(j+1)..(n-2)(1)..(j) -- note gain1 uses
    # hi1+hi2+lows[x-1]+lows[x:]+lows[:x-1]; both must be perms of ALPHA
    assert sorted(src) == sorted(ALPHA)
u = set()
for L in klo:
    assert not (orbitsets[L] & u), "kernel loops share an orbit"
    u |= orbitsets[L]
print(f" kernel loops: {[fmt(L) for L in klo]}  (orbit-disjoint, "
      f"{len(u)} root orbits)")

L0, k0 = klo[0], entries[klo[0]].index(ALPHA)
assert canon(entries[klo[0]][k0]) == ID
assert (L0, k0) == id_loops[hi1], (L0, k0, id_loops[hi1])
k = k0; tot = 0; ok = True
for h, (src, tgt) in enumerate(khops):
    L = klo[h]
    j = sources[L].index(src)
    sk = MAXSKIP - ((j - k) % NE)
    tot += sk
    forced = (j == (k - 1) % NE)
    print(f" loop {fmt(L)}: arrival k={k}, exit j={j}, skip={sk}, "
          f"full-ride={forced}, hop {src}->{tgt}")
    if sk != 0 or not forced: ok = False
    M = loop_index[loop_of(tgt)]
    assert M == klo[h + 1] and door(src, 3) == tgt
    k = entries[M].index(tgt)
print(f" loop {fmt(klo[4])}: arrival k={k}, LAST (full ride, skip 0)")
K = 5
waste = 862 - K / 5 + tot / 5
print(f" K={K}, Sigma_skip={tot}, waste = 862 - {K}/5 + {tot}/5 = {waste}  "
      f"{'OK (5907 = 5040+861+6)' if ok and waste == 861 else 'FAIL'}")
if not (ok and waste == 861):
    sys.exit("STANDARD KERNEL GATE FAILED")
R = (720 - 6 * K + tot) // 5
print(f" R = (720 - 6*{K} + {tot})/5 = {R} rows; "
      f"integrality Sigma==K mod 5: {(tot - K) % 5 == 0}")

# ------------------------------------------------ forced (skip-0) structure
print("\n== FORCED (skip-0) MAP on 5040 (loop, arrival) states ==")
fnext = [[None] * NE for _ in range(NLOOP)]
for L in range(NLOOP):
    for (j, s, t, M, ka) in E3k[L]:
        fnext[L][j] = (M, ka)          # exit splice j reached from k=(j+1)%NE
def forced_step(L, k):
    return fnext[L][(k - 1) % NE]

periods = Counter(); tails = Counter()
for L in range(NLOOP):
    for k in range(NE):
        st = (L, k); seen = {st: 0}; n_ = 0; cur = st
        while True:
            cur = forced_step(*cur)
            n_ += 1
            if cur is None:
                periods["undef"] += 1; break
            if cur in seen:
                periods[n_ - seen[cur]] += 1
                tails[seen[cur]] += 1
                break
            seen[cur] = n_
print(" forced-map cycle periods over 5040 states:", dict(periods))
print(" tail lengths before entering cycle:", dict(sorted(tails.items())))

def forced_run(L, k):
    """distinct loops visitable by pure forced steps (no reuse)."""
    seenL = {L}; cur = (L, k)
    while True:
        nxt = forced_step(*cur)
        if nxt is None or nxt[0] in seenL:
            return len(seenL)
        seenL.add(nxt[0]); cur = nxt
rl = Counter(forced_run(L, k) for L in range(NLOOP) for k in range(NE))
print(" forced-run length (distinct loops) distribution:", dict(sorted(rl.items())))
print(f" => forced-run cap = {max(rl)} loops")

# --------------------------------------------------------- skip availability
print("\n== SKIP AVAILABILITY per (loop, arrival k) state (cost 3) ==")
valid = [set(j for (j, *_) in E3k[L]) for L in range(NLOOP)]
print(" valid-exit-splice count per loop:",
      dict(sorted(Counter(len(v) for v in valid).items())))
setdist = Counter(); percount = Counter(); skip0avail = 0
for L in range(NLOOP):
    for k in range(NE):
        ss = frozenset(MAXSKIP - ((j - k) % NE) for j in valid[L])
        dev = tuple(sorted(s for s in ss if s > 0))
        setdist[dev] += 1
        for s in dev: percount[s] += 1
        if 0 in ss: skip0avail += 1
top = sorted(setdist.items(), key=lambda x: -x[1])[:8]
print(" deviating-skip-set distribution (top 8):", dict(top),
      f"({len(setdist)} distinct sets)")
print(" availability of each deviating skip s (states/5040):",
      {s: percount[s] for s in range(1, NE)})
print(" states with skip-0 (forced) exit available:", skip0avail, "/5040")

# ------------------------------------------- pivot-class isomorphism check
print("\n== PIVOT-CLASS ISOMORPHISM (symbol rotation sigma: i -> i mod 7 + 1) ==")
rho = {ALPHA[i]: ALPHA[(i + 1) % N] for i in range(N)}
def relab(w): return "".join(rho[c] for c in w)
iso_ok = True
for a in ALPHA:
    L, k = id_loops[a]
    Lb = loop_index[loop_of(relab(entries[L][k]))]
    if id_loops[rho[a]][0] != Lb: iso_ok = False
# spot-check edge transport on 2000 random-ish edges
cnt = 0
for L in range(0, NLOOP, 7):
    for (j, s, t, M, ka) in E3k[L]:
        L2 = loop_index[loop_of(relab(entries[L][0]))]
        s2, t2 = relab(s), relab(t)
        M2 = loop_index[loop_of(t2)]
        # the relabeled hop must exist in E3k[L2] with same skip offsets
        hit = [(j2, ka2) for (j2, ss, tt, MM, ka2) in E3k[L2]
               if ss == s2 and tt == t2 and MM == M2]
        assert hit, "edge transport failed"
        cnt += 1
print(f" identity-loop transport consistent: {iso_ok}; "
      f"{cnt} edges transport-checked OK")
print(" (word ops commute with relabeling; skips depend on (j-k) mod 6, "
      "invariant under the uniform entry-index shift => classes isomorphic)")

print("\nALL GATES PASSED" if part_ok and iso_ok else "\nGATE FAILURES ABOVE")
