#!/usr/bin/env python3
"""s49 item2 Part B: the w4 LIFT-AND-DROP composite.

REV-w4  : remove an entry, add a WEIGHT-4 door.  dlen = -1 -2 +4 = +1.
          (record -> record+1, e.g. 872 -> 873, with one EXTRA w4 door)
FWD-w4  : delete a weight-4 door, add the loop-closing entry.  dlen = 3-4 = -1.
          (record+1 -> record)

FWD-w4 applied to the door REV-w4 just created is the exact inverse.  The
composite is interesting only when FWD-w4 fires on a DIFFERENT w4 door -
i.e. a w4-door RELOCATION through an off-shell intermediate.  This script
runs the 2-step composite over every w4-bearing source and reports every
product of record length, gating it against the canonical index.

Usage: rbnd_w4_composite.py <n> <dir> <files.txt> <outdir>
"""
import hashlib
import os
import sys
from collections import Counter
from itertools import permutations

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "..", ".."))
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting")
from loop_ledger_probe import first_visit_path, g, rot, rotc, weight  # noqa
from i4a_apply import replay, structure  # noqa
from m3_check import SUPPLEMENTARY, canon, load_index  # noqa

n = int(sys.argv[1])
srcdir = sys.argv[2]
flist = sys.argv[3]
outdir = sys.argv[4]
RECORD = 872 if n == 6 else 5906
HERE = os.path.join(R, 'analysis', 'counting')
os.makedirs(outdir, exist_ok=True)

GINV, ROTINV = {}, {}
for p in permutations(range(1, n + 1)):
    GINV[g(p)] = p
    ROTINV[rot(p)] = p


def sp(p):
    return "".join(map(str, p))


def loop_list(p):
    o, q = [], p
    for _ in range(n - 1):
        o.append(q)
        q = g(q)
    return o


idx = load_index(os.path.join(HERE, f"upstream{RECORD}_canon_index.tsv"))
for supp in SUPPLEMENTARY.get(n, []):
    p = os.path.join(HERE, supp)
    if os.path.exists(p):
        idx.update(load_index(p))
sys.stderr.write(f"index: {len(idx)} known {RECORD} classes\n")

SRC = {}
for d in srcdir.split(','):
    for f in sorted(os.listdir(d)):
        if f.endswith('.txt'):
            SRC[f] = os.path.join(d, f)
names = sorted(SRC) if flist == 'ALL' else open(flist).read().split()
tot = Counter()
inter_seen = set()
prods = {}
edges = set()

for fname in names:
    src = open(SRC[fname]).read().strip()
    for orient, txt in (("F", src), ("R", src[::-1])):
        path = first_visit_path(txt, n)
        E, D, st = structure(path)
        end = path[-1]
        flat = set().union(*E.values())
        # ---- step 1: REV-w4 (both END and START forms)
        step1 = []
        for a in flat:
            ga = g(a)
            if weight(end, ga, n) == 4 and end not in D and a != st:
                E2 = {c: set(v) for c, v in E.items()}
                E2[rotc(a)].discard(a)
                D2 = dict(D)
                D2[end] = ga
                step1.append((f"REVEND-w4/{sp(a)}", E2, D2, st))
        for a in flat:
            x1 = ROTINV[GINV[a]]
            if weight(x1, st, n) == 4 and x1 not in D and a != st:
                E2 = {c: set(v) for c, v in E.items()}
                E2[rotc(a)].discard(a)
                D2 = dict(D)
                D2[x1] = st
                step1.append((f"REVSTART-w4/{sp(a)}", E2, D2, g(a)))
        for lab1, E2, D2, st2 in step1:
            tot['step1:fired'] += 1
            mid, _ = replay(E2, D2, st2, n)
            if mid is None or len(mid) != RECORD + 1:
                tot['step1:dead'] += 1
                continue
            tot['step1:ok'] += 1
            h = hashlib.sha256(canon(mid).encode()).hexdigest()
            inter_seen.add(h)
            # ---- step 2: FWD-w4 on the intermediate, from its own structure
            p2 = first_visit_path(mid, n)
            Em, Dm, stm = structure(p2)
            endm = p2[-1]
            l2 = set(loop_list(rot(endm)))
            a2 = g(rot(endm))
            step2 = []
            for x, y in Dm.items():
                if weight(x, y, n) < 4:
                    continue
                D3 = dict(Dm)
                del D3[x]
                strict = y in l2
                E3 = {c: set(v) for c, v in Em.items()}
                aa = a2 if strict else g(rot(x))
                E3.setdefault(rotc(aa), set()).add(aa)
                step2.append((f"FWDEND-w4{'S' if strict else 'R'}/{sp(x)}>{sp(y)}",
                              E3, D3, stm))
                strict2 = stm in loop_list(rot(x))
                E4 = {c: set(v) for c, v in Em.items()}
                a1 = g(rot(x))
                E4.setdefault(rotc(a1), set()).add(a1)
                D4 = dict(Dm)
                del D4[x]
                step2.append((f"FWDSTART-w4{'S' if strict2 else 'R'}/{sp(x)}>{sp(y)}",
                              E4, D4, y))
            for lab2, E3, D3, st3 in step2:
                tot['step2:fired'] += 1
                tot['step2:strict' if lab2.split('/')[0].endswith('S')
                    else 'step2:relaxed'] += 1
                prod, _ = replay(E3, D3, st3, n)
                if prod is None:
                    tot['step2:killed'] += 1
                    continue
                L = len(prod)
                tot[f'step2:len{L}'] += 1
                if L > RECORD:
                    continue
                sha = hashlib.sha256(canon(prod).encode()).hexdigest()
                tgt = idx.get(sha)
                if tgt is None:
                    tot['step2:NOVEL' if L == RECORD else 'step2:SHORTER'] += 1
                    nm = f"w4comp-{L}-{sha[:12]}.txt"
                    open(os.path.join(outdir, nm), 'w').write(prod)
                    prods[sha] = nm
                    print(f"*** {'SHORTER' if L < RECORD else 'NOVEL'} {L} *** "
                          f"{fname}[{orient}] {lab1} + {lab2} -> {nm}", flush=True)
                elif tgt == fname:
                    tot['step2:self-edge'] += 1
                else:
                    tot['step2:edge'] += 1
                    edges.add((fname, tgt))

print(f"\ndistinct {RECORD+1} intermediates: {len(inter_seen)}")
for k, v in sorted(tot.items()):
    print(f"{k}: {v}")
print(f"non-trivial edges (source != target): {len(edges)}")
with open(os.path.join(outdir, 'w4_composite_edges.tsv'), 'w') as o:
    o.write("source_class\ttarget_class\n")
    for a, b in sorted(edges):
        o.write(f"{a}\t{b}\n")
