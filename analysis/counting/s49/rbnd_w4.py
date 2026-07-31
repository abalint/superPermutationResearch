#!/usr/bin/env python3
"""s49 item2 Part B: w>=4 boundary trades.

LENGTH ALGEBRA (T0 / THEORY s7).  For a walk with S sojourns (= S entries),
D = #heavy inter-sojourn doors with weights w_j (the other S-1-D
inter-sojourn steps are w2), and 720-S intra steps of weight 1:

    len = n + (n!-S)*1 + 2*(S-1-D) + sum_j w_j
        = (n! + n - 2) + S - 2D + sum_j w_j

An R-BND FWD unit trade deletes ONE door of weight w and adds ONE entry:
    dS=+1, dD=-1, d(sum w) = -w   =>   dlen = 1 + 2 - w = 3 - w.
So R-BND is length-conserving EXACTLY at w=3.  At w=4 the same edit is
length-DECREASING by 1 (an 871 at n=6, a 5905 at n=7) - i.e. a record
break, if it replays.  The REV direction at w=4 is +1 (873 / 5907).

This script measures, per w4-bearing walk-orientation:
  * the weight of the door the strict FWD-END / FWD-START precondition
    selects (does the boundary trade ever SELECT a w4 door?),
  * a w4-forced FWD probe: delete EVERY w4 door, add the loop-closing
    entry, replay (the dlen = -1 probe),
  * REV at w4: remove an entry, add a weight-4 door (dlen = +1),
  * the REV-END(F) vs REV-START(R) candidate sets, to explain the
    reversal-identity violation that the Part A census localises on
    exactly the 415 w4-bearing n=6 classes.

Usage: rbnd_w4.py <n> <dir>[,<dir>...] <out.tsv> [--files list.txt]
"""
import hashlib
import os
import sys
from collections import Counter
from itertools import permutations

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "..", ".."))
sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))
from loop_ledger_probe import first_visit_path, g, rot, rotc, weight  # noqa
from i4a_apply import replay, structure  # noqa
from m3_check import SUPPLEMENTARY, canon, load_index  # noqa

n = int(sys.argv[1])
dirs = sys.argv[2].split(',')
outp = sys.argv[3]
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


def add_entry(E, a):
    E2 = {c: set(v) for c, v in E.items()}
    E2.setdefault(rotc(a), set()).add(a)
    return E2


def del_entry(E, a):
    E2 = {c: set(v) for c, v in E.items()}
    E2[rotc(a)].discard(a)
    return E2


idx = load_index(os.path.join(HERE, f"upstream{RECORD}_canon_index.tsv"))
for supp in SUPPLEMENTARY.get(n, []):
    p = os.path.join(HERE, supp)
    if os.path.exists(p):
        idx.update(load_index(p))
sys.stderr.write(f"index: {len(idx)} known {RECORD} classes\n")

sel = None
if '--files' in sys.argv:
    sel = set(open(sys.argv[sys.argv.index('--files') + 1]).read().split())
files = []
for d in dirs:
    for f in sorted(os.listdir(d)):
        if f.endswith('.txt') and (sel is None or f in sel):
            files.append((f, os.path.join(d, f)))
sys.stderr.write(f"{len(files)} source walks\n")

rows = []
tot = Counter()
lens = Counter()
finds = []
os.makedirs(os.path.dirname(outp) or '.', exist_ok=True)
FIND = os.path.join(os.path.dirname(outp) or '.', 'w4_finds')
os.makedirs(FIND, exist_ok=True)

for fname, path_ in files:
    src = open(path_).read().strip()
    if not src.isdigit():
        continue
    for orient, txt in (("F", src), ("R", src[::-1])):
        path = first_visit_path(txt, n)
        E, D, st = structure(path)
        end = path[-1]
        S = sum(len(v) for v in E.values())
        dw = Counter(weight(x, y, n) for x, y in D.items())
        flat = set().union(*E.values())
        # --- predicted length from the identity (sanity pin)
        pred = (1 for _ in ()) and 0
        pred = ((len(path) if False else 0))
        sumw = sum(weight(x, y, n) for x, y in D.items())
        predlen = (720 if n == 6 else 5040) + n - 2 + S - 2 * len(D) + sumw
        tot['predlen-ok' if predlen == RECORD else 'predlen-BAD'] += 1

        # --- strict FWD preconditions: which door gets selected, what weight
        l2 = set(loop_list(rot(end)))
        selend = [(x, y) for x, y in D.items() if y in l2]
        selsta = [(x, y) for x, y in D.items() if st in loop_list(rot(x))]
        wend = sorted(weight(x, y, n) for x, y in selend)
        wsta = sorted(weight(x, y, n) for x, y in selsta)
        for w in wend:
            tot[f'FWD-END:selected-w{w}'] += 1
        for w in wsta:
            tot[f'FWD-START:selected-w{w}'] += 1

        # --- probes
        probes = []
        # (a) w4-FORCED FWD-END: delete each w4 door, close loop(rot(end))
        a2 = g(rot(end))
        for x, y in D.items():
            w = weight(x, y, n)
            if w < 4:
                continue
            D2 = dict(D)
            del D2[x]
            strict = y in l2
            probes.append((f"FWDEND-w{w}{'-strict' if strict else '-relax'}",
                           add_entry(E, a2 if strict else g(rot(x))), D2, st))
        # (b) w4-FORCED FWD-START
        for x, y in D.items():
            w = weight(x, y, n)
            if w < 4:
                continue
            D2 = dict(D)
            del D2[x]
            strict = st in loop_list(rot(x))
            probes.append((f"FWDSTART-w{w}{'-strict' if strict else '-relax'}",
                           add_entry(E, g(rot(x))), D2, y))
        # (c) REV at w4: remove entry a, add a WEIGHT-4 door
        for a in flat:
            ga = g(a)
            if weight(end, ga, n) == 4 and end not in D and a != st:
                D2 = dict(D)
                D2[end] = ga
                probes.append((f"REVEND-w4/{sp(a)}", del_entry(E, a), D2, st))
        for a in flat:
            x1 = ROTINV[GINV[a]]
            if weight(x1, st, n) == 4 and x1 not in D and a != st:
                D2 = dict(D)
                D2[x1] = st
                probes.append((f"REVSTART-w4/{sp(a)}", del_entry(E, a), D2, g(a)))

        fired = Counter()
        for label, E2, D2, st2 in probes:
            k = label.split('/')[0]
            fired[k] += 1
            tot[k + ':fired'] += 1
            prod, why = replay(E2, D2, st2, n)
            if prod is None:
                tot[k + ':killed'] += 1
                continue
            L = len(prod)
            tot[k + f':len{L}'] += 1
            lens[(k, L)] += 1
            if L <= RECORD:
                sha = hashlib.sha256(canon(prod).encode()).hexdigest()
                tag = idx.get(sha, 'NOVEL-' + sha[:12])
                nm = f"w4-{L}-{sha[:12]}.txt"
                open(os.path.join(FIND, nm), 'w').write(prod)
                finds.append((fname, orient, label, L, tag, nm))
                print(f"*** SURVIVOR len={L} *** {label} on {fname}[{orient}]"
                      f" -> {nm} ({tag})", flush=True)

        # --- reversal-identity diagnostic: REV-END candidates (w3) on this orientation
        rev3 = sorted(sp(a) for a in flat
                      if weight(end, g(a), n) == 3 and end not in D and a != st)
        rev3s = sorted(sp(a) for a in flat
                       if weight(ROTINV[GINV[a]], st, n) == 3
                       and ROTINV[GINV[a]] not in D and a != st)
        rows.append((fname, orient, S, len(D), dict(sorted(dw.items())),
                     wend, wsta,
                     fired['FWDEND-w4-strict'] + fired['FWDEND-w4-relax'],
                     fired['FWDSTART-w4-strict'] + fired['FWDSTART-w4-relax'],
                     fired['REVEND-w4'], fired['REVSTART-w4'],
                     ",".join(rev3), ",".join(rev3s)))

with open(outp, 'w') as o:
    o.write("file\torient\tS\tD\tdoor_weights\tfwdend_sel_w\tfwdstart_sel_w"
            "\tn_fwdend_w4\tn_fwdstart_w4\tn_revend_w4\tn_revstart_w4"
            "\trevend_w3_cands\trevstart_w3_cands\n")
    for r in rows:
        o.write("\t".join(map(str, r)) + "\n")

print(f"\nwalk-orientations: {len(rows)}")
for k, v in sorted(tot.items()):
    print(f"{k}: {v}")
print("\nproduct lengths by probe:", dict(sorted(lens.items())))
print(f"survivors (len <= {RECORD}): {len(finds)}")
for r in finds:
    print("  ", r)
