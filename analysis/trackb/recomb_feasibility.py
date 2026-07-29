#!/usr/bin/env python3
"""Feasibility measurements for the s26 recombination design.

R1 feasibility: across all 872 records, how often do two byte-distinct
records occupy the SAME search state (visited-set, current-perm) — and
with what prefix-length differences? Exact-state collisions are free
splice points: prefix(A)+suffix(B) is a legal walk, length
lenA(i) + 872 - lenB(j).

R3 feasibility: size/out-degree of the union graph of first-visit edges
used by any record — determines whether an exhaustive capped DFS
restricted to corpus edges is tractable.
"""
import os, sys
from itertools import permutations
from collections import defaultdict

N = 6
PERMS = list(permutations(range(1, N + 1)))
RANK = {p: i for i, p in enumerate(PERMS)}

def overlap(a, b):
    for k in range(N, 0, -1):
        if a[N - k:] == b[:k]:
            return k
    return 0

def first_visit(s):
    seen = set()
    path = []
    vals = [int(c) for c in s.strip()]
    for i in range(len(vals) - N + 1):
        w = tuple(vals[i:i + N])
        if len(set(w)) == N and all(1 <= v <= N for v in w):
            r = RANK[w]
            if r not in seen:
                seen.add(r)
                path.append(r)
    return path

def load_corpus():
    recs = {}
    for d in ("data/records872", "data/gain1_872s"):
        for f in sorted(os.listdir(d)):
            s = open(os.path.join(d, f)).read().strip()
            if not s or not all(c in "123456" for c in s):
                print(f"  skipping non-record file: {d}/{f} ({s[:40]!r}...)")
                continue
            recs[f] = s
    return recs

recs = load_corpus()
print(f"corpus: {len(recs)} strings, {len(set(recs.values()))} byte-distinct")

# Trace every record: path, per-step (visited_mask, cur, len_chars)
traces = {}
for name, s in recs.items():
    path = first_visit(s)
    assert path[0] == 0, name
    lens = [N]
    for i in range(1, len(path)):
        w = N - overlap(PERMS[path[i - 1]], PERMS[path[i]])
        lens.append(lens[-1] + w)
    traces[name] = (path, lens)
    assert lens[-1] == len(s.strip()), (name, lens[-1], len(s))
    assert len(path) == 720, (name, len(path))

names = sorted(traces)
# distinct-by-bytes representative set
by_str = {}
for name in names:
    by_str.setdefault(recs[name], name)
distinct = sorted(by_str.values())
print(f"tracing {len(distinct)} byte-distinct records")

# R1: state collisions. state = (frozen visited mask as int, cur rank)
states = defaultdict(list)  # (mask, cur) -> [(rec, step_idx, len)]
for name in distinct:
    path, lens = traces[name]
    mask = 0
    for i, r in enumerate(path):
        mask |= 1 << r
        states[(mask, r)].append((name, i, lens[i]))

cross = 0
len_diffs = defaultdict(int)
improving = 0
pair_examples = []
for (mask, cur), occ in states.items():
    if len(occ) < 2:
        continue
    # cross-record pairs only
    recs_here = {o[0] for o in occ}
    if len(recs_here) < 2:
        continue
    cross += 1
    ls = sorted(set(o[2] for o in occ))
    d = ls[-1] - ls[0]
    len_diffs[d] += 1
    if d > 0:
        improving += 1
        if len(pair_examples) < 5:
            pair_examples.append((bin(mask).count('1'), cur, occ[:4]))

print(f"\nR1: states shared by >=2 byte-distinct records: {cross}")
print(f"    with differing prefix length (=> strict improvement on splice!): {improving}")
print(f"    len-diff histogram: {dict(sorted(len_diffs.items()))}")
for ex in pair_examples:
    print(f"    example: depth={ex[0]} cur={ex[1]} occ={ex[2]}")

# depth distribution of collisions
depth_hist = defaultdict(int)
for (mask, cur), occ in states.items():
    if len({o[0] for o in occ}) >= 2:
        depth_hist[bin(mask).count('1') // 100] += 1
print(f"    collision depth histogram (per 100 perms): {dict(sorted(depth_hist.items()))}")

# R2 relaxation: cur matches, visited masks differ by small Hamming distance.
# Too expensive all-pairs at every step; sample: same cur, same depth (+-0), count min symdiff
# Bucket by (cur, popcount) then compare within buckets.
buck = defaultdict(list)
for name in distinct:
    path, lens = traces[name]
    mask = 0
    for i, r in enumerate(path):
        mask |= 1 << r
        if 100 <= i <= 620:
            buck[(r, i)].append((name, mask, lens[i]))
sym_hist = defaultdict(int)
checked = 0
for key, occ in buck.items():
    if len(occ) < 2:
        continue
    for a in range(len(occ)):
        for b in range(a + 1, len(occ)):
            if occ[a][0] == occ[b][0]:
                continue
            d = bin(occ[a][1] ^ occ[b][1]).count('1')
            sym_hist[min(d, 20)] += 1
            checked += 1
            if checked > 2_000_000:
                break
print(f"\nR2: same (cur, depth) cross-record pairs: {checked}")
print(f"    symdiff histogram (capped at 20): {dict(sorted(sym_hist.items()))}")

# R3: union edge graph
edges = set()
w_hist = defaultdict(int)
for name in distinct:
    path, _ = traces[name]
    for i in range(1, len(path)):
        p, q = path[i - 1], path[i]
        if (p, q) not in edges:
            edges.add((p, q))
            w = N - overlap(PERMS[p], PERMS[q])
            w_hist[w] += 1
outdeg = defaultdict(int)
for p, q in edges:
    outdeg[p] += 1
od_hist = defaultdict(int)
for p in range(720):
    od_hist[outdeg[p]] += 1
print(f"\nR3: union graph: {len(edges)} distinct edges over 720 nodes")
print(f"    edge weight histogram: {dict(sorted(w_hist.items()))}")
print(f"    out-degree histogram: {dict(sorted(od_hist.items()))}")
import math
logsum = sum(math.log10(max(outdeg[p], 1)) for p in range(720))
print(f"    naive product-of-outdegrees log10: {logsum:.1f}")

# Splice-closure count: DAG over states (mask,cur), edges = record steps.
# Depth (=popcount) strictly increases, so it's layered; count root->terminal paths.
sedges = defaultdict(set)   # state -> set(next state)
root = None
terminals = set()
allstates = set()
for name in distinct:
    path, lens = traces[name]
    mask = 1 << path[0]
    st = (mask, path[0])
    root = st
    allstates.add(st)
    for i in range(1, len(path)):
        mask |= 1 << path[i]
        nst = (mask, path[i])
        sedges[st].add(nst)
        st = nst
        allstates.add(st)
    terminals.add(st)
print(f"\nsplice-closure DAG: {len(allstates)} states, "
      f"{sum(len(v) for v in sedges.values())} edges, {len(terminals)} terminal states")
# count paths by memoized DFS (DAG)
from functools import lru_cache
import sys as _sys
_sys.setrecursionlimit(500000)
memo = {}
def npaths(st):
    if st in terminals:
        return 1
    if st in memo:
        return memo[st]
    r = sum(npaths(t) for t in sedges.get(st, ()))
    memo[st] = r
    return r
total = npaths(root)
print(f"splice-closure walk count (all length-872, all valid): {total}")
print(f"  vs corpus size {len(distinct)} -> {total - len(distinct)} NEW hybrid 872s available by splicing alone")
