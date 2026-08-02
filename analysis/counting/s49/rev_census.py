#!/usr/bin/env python3
"""s48 item2: census of R-BND variant firings (esp. the REV variants,
whose preconditions are NOT universal) over a corpus of tight walks.

Per walk-orientation records: allocation (S,D), per-variant precondition
firing count, replay survivors, and the product's allocation/class.

Usage: rev_census.py <n> <dir>[,<dir>...] <out.tsv> [--limit N]
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
dirs = sys.argv[2].split(',')
outp = sys.argv[3]
limit = None
if '--limit' in sys.argv:
    limit = int(sys.argv[sys.argv.index('--limit') + 1])
RECORD = 872 if n == 6 else 5906
HERE = os.path.join(R, 'analysis', 'counting')

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


def moves(E, D, st, end):
    """Same enumeration as analysis/counting/rbnd.py:moves (relaxed=False)."""
    out = []
    l2 = set(loop_list(rot(end)))
    a2 = g(rot(end))
    for x2, y2 in D.items():
        if y2 in l2:
            E2 = {c: set(v) for c, v in E.items()}
            E2.setdefault(rotc(a2), set()).add(a2)
            D2 = dict(D)
            del D2[x2]
            out.append((f"FWD-END/{sp(x2)}>{sp(y2)}", E2, D2, st))
    for x1, y1 in D.items():
        if st in loop_list(rot(x1)):
            a1 = g(rot(x1))
            E2 = {c: set(v) for c, v in E.items()}
            E2.setdefault(rotc(a1), set()).add(a1)
            D2 = dict(D)
            del D2[x1]
            out.append((f"FWD-START/{sp(x1)}>{sp(y1)}", E2, D2, y1))
    flat = set().union(*E.values())
    for a in flat:
        ga = g(a)
        if weight(end, ga, n) == 3 and end not in D and a != st:
            E2 = {c: set(v) for c, v in E.items()}
            E2[rotc(a)].discard(a)
            D2 = dict(D)
            D2[end] = ga
            out.append((f"REV-END/{sp(a)}", E2, D2, st))
    for a in flat:
        x1 = ROTINV[GINV[a]]
        if weight(x1, st, n) == 3 and x1 not in D and a != st:
            E2 = {c: set(v) for c, v in E.items()}
            E2[rotc(a)].discard(a)
            D2 = dict(D)
            D2[x1] = st
            out.append((f"REV-START/{sp(a)}", E2, D2, g(a)))
    return out


idx = load_index(os.path.join(HERE, f"upstream{RECORD}_canon_index.tsv"))
for supp in SUPPLEMENTARY.get(n, []):
    p = os.path.join(HERE, supp)
    if os.path.exists(p):
        idx.update(load_index(p))
sys.stderr.write(f"index: {len(idx)} known {RECORD} classes\n")

files = []
for d in dirs:
    for f in sorted(os.listdir(d)):
        if f.endswith('.txt'):
            files.append((f, os.path.join(d, f)))
if limit:
    files = files[:limit]
if '--shard' in sys.argv:
    _i = int(sys.argv[sys.argv.index('--shard') + 1])
    _k = int(sys.argv[sys.argv.index('--shard') + 2])
    files = files[_i::_k]
sys.stderr.write(f"{len(files)} source walks\n")

VAR = ("FWD-END", "FWD-START", "REV-END", "REV-START")
rows = []
tot = Counter()
prodalloc = Counter()
survivors = []
for fname, path_ in files:
    src = open(path_).read().strip()
    if not src.isdigit():
        continue
    for orient, txt in (("F", src), ("R", src[::-1])):
        path = first_visit_path(txt, n)
        E, D, st = structure(path)
        end = path[-1]
        S = sum(len(v) for v in E.values())
        Dn = len(D)
        fire = Counter()
        surv = Counter()
        for label, E2, D2, st2 in moves(E, D, st, end):
            k = label.split('/')[0]
            fire[k] += 1
            tot[k + ':fired'] += 1
            prod, why = replay(E2, D2, st2, n)
            if prod is None:
                tot[k + ':killed'] += 1
                continue
            L = len(prod)
            if L != RECORD:
                tot[k + f':len{L}'] += 1
                continue
            surv[k] += 1
            tot[k + ':survived'] += 1
            p2 = first_visit_path(prod, n)
            E3, D3, _ = structure(p2)
            S2 = sum(len(v) for v in E3.values())
            D2n = len(D3)
            sha = hashlib.sha256(canon(prod).encode()).hexdigest()
            tgt = idx.get(sha, "NOVEL-" + sha[:12])
            prodalloc[(S2, D2n)] += 1
            survivors.append((fname, orient, label, S, Dn, S2, D2n, tgt))
        rows.append((fname, orient, S, Dn,
                     fire["FWD-END"], fire["FWD-START"],
                     fire["REV-END"], fire["REV-START"],
                     surv["FWD-END"], surv["FWD-START"],
                     surv["REV-END"], surv["REV-START"]))

with open(outp, 'w') as o:
    o.write("file\torient\tS\tD\tfFWDEND\tfFWDSTART\tfREVEND\tfREVSTART"
            "\tsFWDEND\tsFWDSTART\tsREVEND\tsREVSTART\n")
    for r in rows:
        o.write("\t".join(map(str, r)) + "\n")
with open(outp.replace('.tsv', '_survivors.tsv'), 'w') as o:
    o.write("file\torient\tmove\tS\tD\tS2\tD2\ttarget\n")
    for r in survivors:
        o.write("\t".join(map(str, r)) + "\n")

print(f"walk-orientations: {len(rows)}")
for k in VAR:
    print(f"{k}: fired={tot[k+':fired']} killed={tot[k+':killed']} "
          f"survived={tot[k+':survived']}")
for k, v in sorted(tot.items()):
    if ':len' in k:
        print(f"  {k}: {v}")
print("product allocations (S,D):", dict(sorted(prodalloc.items())))
# firing-count distributions
for k, i in (("REV-END", 6), ("REV-START", 7)):
    c = Counter(r[i] for r in rows)
    print(f"{k} firings-per-orientation distribution: {dict(sorted(c.items()))}"
          f"  nonzero-orientations={sum(1 for r in rows if r[i])}/{len(rows)}")
for k, i in (("FWD-END", 4), ("FWD-START", 5)):
    c = Counter(r[i] for r in rows)
    print(f"{k} firings-per-orientation distribution: {dict(sorted(c.items()))}")
