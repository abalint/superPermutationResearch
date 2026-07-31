#!/usr/bin/env python3
"""s49 item1 PART B — exact admissible-frame entry/door diffs from every
blind-spot class to every other class of the 198.

For an ordered pair (source walk-orientation W, target walk-orientation T)
the rigidity theorem forces rho: start(rho.T) = start(W).  Any 9-column
rule carrying W to T then has EXACTLY
    ents_out = flat(W) \\ flat(rho.T),  ents_in = flat(rho.T) \\ flat(W),
    doors_out = doors(W) \\ doors(rho.T), doors_in = doors(rho.T) \\ doors(W).
So |ents_out| is not a bound but an identity -- which is what makes the
6-divisibility test decisive.
"""
import csv
import os
import re
import sys
from itertools import permutations

R = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))
from i4a_apply import structure                          # noqa: E402
from loop_ledger_probe import first_visit_path           # noqa: E402

N = 7
perms = sorted(permutations(range(1, N + 1)))
pid = {p: i for i, p in enumerate(perms)}
DIRS = ['data/upstream5906', 'data/novel5906',
        'data/novel5906b', 'data/novel5906c']

files = {}
for d in DIRS:
    for f in sorted(os.listdir(os.path.join(R, d))):
        if f.endswith('.txt'):
            files[f] = os.path.join(R, d, f)
names = sorted(files)
assert len(names) == 198

W = {}      # (name, orient) -> (start, flatset, doorset, nloops, ndoors)
for f in names:
    src = open(files[f]).read().strip()
    for o, txt in (('F', src), ('R', src[::-1])):
        E, D, st = structure(first_visit_path(txt, N))
        flat = frozenset(pid[p] for c in E for p in E[c])
        doors = frozenset((pid[a], pid[b]) for a, b in D.items())
        W[(f, o)] = (st, flat, doors, len(E), len(D))
print(f"{len(names)} classes, {len(W)} walk-orientations", flush=True)

starts = sorted({v[0] for v in W.values()})
print("distinct start perms:", ["".join(map(str, s)) for s in starts])

rho_tab = {}
for a in starts:            # target start
    for b in starts:        # source start
        rho = [0] * N
        for x, y in zip(a, b):
            rho[x - 1] = y
        rho = tuple(rho)
        rho_tab[(a, b)] = (rho, [pid[tuple(rho[x - 1] for x in p)]
                                 for p in perms])

# per (target-orientation, source-start) cached relabeled flat/door sets
cache = {}
for f in names:
    for ot in ('F', 'R'):
        tst, tflat, tdoors, _, _ = W[(f, ot)]
        for sst in starts:
            rho, tab = rho_tab[(tst, sst)]
            cache[(f, ot, sst)] = (rho,
                                   frozenset(tab[i] for i in tflat),
                                   frozenset((tab[a], tab[b])
                                             for a, b in tdoors))
print("relabeled caches built", flush=True)


def h12(x):
    return re.findall(r'([0-9a-f]{12})', x)[-1]


blind = [l.strip() for l in
         open(os.path.join(R, 'out/s49/item1/blindspot12.txt')) if l.strip()]
blindset = set(blind)
touched = set(names) - blindset

alloc = {f: (W[(f, 'F')][3], W[(f, 'F')][4]) for f in names}

rows = []
for B in blind:
    for C in names:
        if C == B:
            continue
        best = None
        for ob in ('F', 'R'):
            sst, sflat, sdoors, _, _ = W[(B, ob)]
            for ot in ('F', 'R'):
                rho, tflat, tdoors = cache[(C, ot, sst)]
                eo = len(sflat - tflat)
                ei = len(tflat - sflat)
                do = len(sdoors - tdoors)
                di = len(tdoors - sdoors)
                key = (eo + ei, do + di)
                if best is None or key < best[0]:
                    best = (key, ob, ot, eo, ei, do, di, rho)
        (sd, dd), ob, ot, eo, ei, do, di, rho = best
        rows.append((B, C, alloc[B], alloc[C], C in touched,
                     sd, eo, ei, do, di, ob, ot,
                     "".join(map(str, rho))))
    print("done", B, flush=True)

out = os.path.join(R, 'out/s49/item1/admdiff_blind12.tsv')
with open(out, 'w') as o:
    o.write("blind\tother\talloc_blind\talloc_other\tother_touched\t"
            "symdiff\tents_out\tents_in\tdoors_out\tdoors_in\t"
            "o_src\to_tgt\trho\n")
    for r in rows:
        o.write("\t".join([r[0], r[1], f"{r[2][0]},{r[2][1]}",
                           f"{r[3][0]},{r[3][1]}", 'T' if r[4] else 'B',
                           str(r[5]), str(r[6]), str(r[7]), str(r[8]),
                           str(r[9]), r[10], r[11], r[12]]) + "\n")
print("wrote", out)
