#!/usr/bin/env python3
"""Kernel-chain existence search for n=6 gain-one construction.

Hop relation (extracted from sources, see report):
  - marked loop L = (pivot a, canonical necklace C), entries e_0..e_4,
    e_0 = C+a, e_{i+1} = tv(e_i);  splice i: source s_i = e_i[-1]+e_i[:-1],
    target = door(s_i,2) = tv(e_i) = e_{i+1}   [certificate.py:111-123]
  - cost-3 hop from L replaces splice i of L: hop source = s_i,
    hop target t = door(s_i,3); it must OPEN the next loop:
    loop_of(t) == M                              [certificate.py:475-488,594]
  - t is automatically an entry e_k of M; the splice of M whose cost-2
    target is t is splice k-1 (mod 5).  Standard-kernel defining relation
    T3(p_j) = T2(p_{j+1})  [lift/README.md:73] == the next hop source is
    forced to be the source of that splice ("forced" mode / full ride).
"""
from itertools import permutations
from collections import Counter
import sys, time

N = 6
ALPHA = "123456"

def door(w, c): return w[c:] + w[:c][::-1]
def tv(w): return w[1:-1] + w[0] + w[-1]
def itv(w): return w[-2] + w[:-2] + w[-1]
def canon(w): return min(w[i:] + w[:i] for i in range(len(w)))
def loop_of(e): return (e[-1], canon(e[:-1]))

# ---------------------------------------------------------------- loops
loops = []                      # list of (pivot, necklace)
for pivot in ALPHA:
    rest = [c for c in ALPHA if c != pivot]
    seen = set()
    for p in permutations(rest):
        neck = canon("".join(p))
        if neck not in seen:
            seen.add(neck)
            loops.append((pivot, neck))
assert len(loops) == 144, len(loops)
loop_index = {lp: i for i, lp in enumerate(loops)}

entries = []    # entries[i] = [e_0..e_4]
sources = []    # sources[i] = [s_0..s_4]
orbitsets = []  # orbitsets[i] = frozenset of 5 cyclic classes
for (a, C) in loops:
    e = C + a
    es, ss, os_ = [], [], set()
    for _ in range(5):
        es.append(e)
        ss.append(e[-1] + e[:-1])
        os_.add(canon(e))
        assert door(ss[-1], 2) == tv(e)          # splice identity
        e = tv(e)
    assert len(os_) == 5
    entries.append(es)
    sources.append(ss)
    orbitsets.append(frozenset(os_))
all_orbits = set().union(*orbitsets)
assert len(all_orbits) == 120

def fmt(i): return f"m{loops[i][0]};{loops[i][1]}"

# ------------------------------------------------- hop edges at cost c
def hop_edges(cost):
    """edges[L] = list of (splice_i_of_L, source, target, M, in_splice_of_M).
    in_splice_of_M = index of the splice of M whose cost-2 target is the
    landing entry t (the splice consumed by arrival; in forced mode it is
    also the next hop source)."""
    edges = [[] for _ in range(144)]
    for L in range(144):
        for i, s in enumerate(sources[L]):
            t = door(s, cost)
            M = loop_index[loop_of(t)]
            k = entries[M].index(t)              # t is entry e_k of M
            j = (k - 1) % 5                      # splice with target t
            if M != L:
                edges[L].append((i, s, t, M, j))
    return edges

E3 = hop_edges(3)

# ------------------------------------------------------ validation gate
gate_loops = [("6","12345"), ("6","15234"), ("6","12534"), ("6","12354")]
gate_hops = [("651234","234156"), ("652341","341256"), ("653412","412356")]
gate_idx = [loop_index[lp] for lp in gate_loops]
print("== VALIDATION GATE ==")
ok = True
for h, (src, tgt) in enumerate(gate_hops):
    L, M = gate_idx[h], gate_idx[h + 1]
    found = [(i, s, t, MM, j) for (i, s, t, MM, j) in E3[L] if MM == M]
    hit = [(i, s, t, MM, j) for (i, s, t, MM, j) in found if s == src and t == tgt]
    print(f" hop {h}: {fmt(L)} -> {fmt(M)} options={[(s,t) for (_,s,t,_,_) in found]}"
          f" expected=({src},{tgt}) {'OK' if hit else 'FAIL'}")
    if not hit: ok = False
    # forced-mode consistency: in-splice of arrival == next hop's splice
    if hit and h + 1 < len(gate_hops):
        j = hit[0][4]
        nxt = gate_hops[h + 1][0]
        forced_src = sources[M][j]
        print(f"   forced next source from landing = {forced_src} "
              f"(actual next hop source {nxt}) "
              f"{'OK' if forced_src == nxt else 'FAIL'}")
        if forced_src != nxt: ok = False
# orbit disjointness of the 4 kernel loops
u = set()
for L in gate_idx:
    assert not (orbitsets[L] & u)
    u |= orbitsets[L]
print(f" 4 gate loops orbit-disjoint: OK ({len(u)} orbits)")
print(" GATE:", "PASS" if ok else "FAIL")
if not ok:
    sys.exit("gate failed")

# ------------------------------------------------------ pair graph stats
outdeg = [len(set(M for (_,_,_,M,_) in E3[L])) for L in range(144)]
print("\n== PAIR GRAPH (cost 3) ==")
print(" distinct-target out-degree distribution:", dict(sorted(Counter(outdeg).items())))
print(" edge multiset size (splice-level, M!=L):", sum(len(E3[L]) for L in range(144)))
selfhops = sum(1 for L in range(144)
               for s in sources[L]
               if loop_index[loop_of(door(s,3))] == L)
print(" splice hops landing back in same loop:", selfhops)

# ------------------------------------------ strict (forced) deterministic walk
def strict_chain(L, i):
    """Standard defining relation: next hop source forced by landing."""
    seq = [L]
    used = set(orbitsets[L])
    cur, spl = L, i
    while True:
        s = sources[cur][spl]
        t = door(s, 3)
        M = loop_index[loop_of(t)]
        if orbitsets[M] & used:
            return seq
        seq.append(M)
        used |= orbitsets[M]
        k = entries[M].index(t)
        cur, spl = M, (k - 1) % 5

best_strict = 0; best_example = None
strict_lengths = Counter()
for L in range(144):
    for i in range(5):
        c = strict_chain(L, i)
        strict_lengths[len(c)] += 1
        if len(c) > best_strict:
            best_strict, best_example = len(c), c
print("\n== STRICT (forced / standard-relation) chains ==")
print(" chain-length distribution over 720 (loop,splice) starts:",
      dict(sorted(strict_lengths.items())))
print(f" max K = {best_strict}, example: {' -> '.join(fmt(x) for x in best_example)}")

# ------------------------------------------ liberal DFS (any / distinct modes)
def search(mode, targetK=None, cap=1000, time_limit=120.0):
    """mode: 'any'  = outgoing splice unrestricted
             'distinct' = outgoing splice != in-splice consumed by arrival
             'forced'   = outgoing splice == in-splice (standard relation)
    Returns (maxK, example_paths_at_targetK, count_at_targetK_capped)."""
    t0 = time.time()
    maxK = [1]
    found = set()
    example = []
    def dfs(cur, in_spl, used, path):
        if time.time() - t0 > time_limit:
            return
        if len(path) > maxK[0]:
            maxK[0] = len(path)
        if targetK and len(path) == targetK:
            if len(found) < cap:
                found.add(tuple(path))
                if len(example) < 3:
                    example.append(list(path))
            return
        for (i, s, t, M, j) in E3[cur]:
            if mode == 'distinct' and in_spl is not None and i == in_spl:
                continue
            if mode == 'forced' and in_spl is not None and i != in_spl:
                continue
            if orbitsets[M] & used:
                continue
            dfs(M, j, used | orbitsets[M], path + [M])
    for L in range(144):
        dfs(L, None, set(orbitsets[L]), [L])
        if targetK and len(found) >= cap:
            break
    return maxK[0], example, len(found)

print("\n== LIBERAL search: mode=any (any splice may be the outgoing cut) ==")
mk, ex, cnt = search('any', targetK=8)
print(f" max K reached = {mk};  K=8 paths found = {cnt}{'+ (capped)' if cnt>=1000 else ''}")
for p in ex:
    print("  K=8 example:", " -> ".join(fmt(x) for x in p))
K8_any = ex

print("\n== LIBERAL search: mode=distinct (outgoing splice != arrival splice) ==")
mkd, exd, cntd = search('distinct', targetK=8)
print(f" max K reached = {mkd};  K=8 paths found = {cntd}{'+ (capped)' if cntd>=1000 else ''}")
for p in exd:
    print("  K=8 example:", " -> ".join(fmt(x) for x in p))

if mk >= 8:
    for K in (10, 12):
        mk2, ex2, cnt2 = search('any', targetK=K, time_limit=120)
        print(f"\n mode=any targetK={K}: paths found = {cnt2}"
              f"{'+ (capped)' if cnt2>=1000 else ''}, max depth seen = {mk2}")
        for p in ex2[:1]:
            print(f"  K={K} example:", " -> ".join(fmt(x) for x in p))
    # absolute max K within time
    mkmax, exmax, _ = search('any', targetK=None, time_limit=150)
    print(f"\n mode=any absolute max K within time limit: {mkmax}")

# ------------------------------- cost-4 extension if K=8 fails at cost 3
def extend_with_cost4(chain):
    E4 = hop_edges(4)
    used = set()
    for L in chain: used |= orbitsets[L]
    exts = []
    last = chain[-1]
    for (i, s, t, M, j) in E4[last]:
        if not (orbitsets[M] & used):
            exts.append((fmt(M), s, t))
    front = []
    for L in range(144):
        if orbitsets[L] & used: continue
        for (i, s, t, M, j) in E4[L]:
            if M == chain[0]:
                front.append((fmt(L), s, t))
    return exts, front

# --------------------------------- eligible-row feasibility side condition
def eligible_rows(chain):
    roots = set()
    for L in chain: roots |= orbitsets[L]
    total = 0
    for L in range(144):
        if L in chain: continue
        r = len(orbitsets[L] & roots)
        if r == 0: total += 5      # any of 5 orbits may be parent
        elif r == 1: total += 1    # parent forced to the root orbit
    return total, len(roots)

print("\n== ELIGIBLE ORIENTED ROWS ==")
base, nb = eligible_rows(gate_idx)
print(f" baseline standard K=4 kernel: eligible oriented rows = {base} "
      f"(roots={nb})  [expected 464]")
if K8_any:
    for p in K8_any:
        er, nr = eligible_rows(p)
        print(f" K=8 chain {'->'.join(fmt(x) for x in p)}: "
              f"eligible rows = {er} (roots={nr})")
else:
    # report on best available chains, and cost-4 extension options
    print(" no K=8 at cost 3; extension check with cost-4 hops on max chains:")
    # regenerate a few max-length chains in 'any' mode
    mkx, exx, cntx = search('any', targetK=mk)
    print(f"  chains of max K={mk}: {cntx}{'+' if cntx>=1000 else ''} found")
    for p in exx[:3]:
        exts, front = extend_with_cost4(p)
        er, nr = eligible_rows(p)
        print(f"  chain {'->'.join(fmt(x) for x in p)}")
        print(f"   eligible rows={er}; cost-4 tail extensions={len(exts)}, "
              f"head extensions={len(front)}")
        if exts[:3]: print("   tail ext examples:", exts[:3])
        if front[:3]: print("   head ext examples:", front[:3])
