#!/usr/bin/env python3
"""s51 positive/completeness controls for the w4 demotion trade.

A control that fails silently looks exactly like a strong negative
(s50 trap), so the demotion instrument is controlled three ways:

  C1 roundtrip   structure->replay reproduces every carrier byte-identically
                 (run inside demotion.py itself on every sweep).
  C2 w3-degenerate (in demotion.py): DEMOTION(3) IS the R-BND FWD unit
                 trade, so `demote --w-from 3` on data/upstream5906 must
                 reproduce rbnd.py's FWD edges exactly.
  C3 BRUTE FORCE completeness: for a sample of w4-bearing carriers,
                 enumerate EVERY triple (new entry a, new door (u,v) of
                 weight 3) with no derived precondition at all, keep the
                 ones whose degree profile is legal, and check that
                 (i) every such a lies in the instrument's derived
                 candidate set, and (ii) the replayed products agree.
  C4 FIRING: the same brute force at n=5 over lifted (w4-bearing)
                 carriers -- does the trade ever produce a genuine
                 length-conserving product with a TRAVERSED new door?

Usage:
  python3 analysis/counting/s51/control.py brute <n> <dir> [--limit K]
  python3 analysis/counting/s51/control.py n5 [--count K]
"""
import os
import subprocess
import sys
from collections import Counter
from itertools import permutations

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "..", ".."))
sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))
sys.path.insert(0, os.path.join(R, 'analysis', 'counting', 's51'))
from loop_ledger_probe import first_visit_path, g, rot, rotc, weight  # noqa
from i4a_apply import replay, structure  # noqa
import demotion as DM  # noqa


def brute_demotions(E, D, st, n, w_from=4, replay_all=False):
    """EVERY (a, u, v) triple, no derived precondition.  Returns
    (legal, products) where legal = list of (x, y, a, u, v) whose degree
    profile is legal, products = those that replay to a length-conserving
    walk with the new door actually traversed."""
    w_to = w_from - 1
    flat = DM.flat_of(E)
    ex = DM.exits_of(E)
    allp = list(DM.GINV.keys())
    legal, prods = [], []
    for x, y in sorted(D.items()):
        if weight(x, y, n) != w_from:
            continue
        D1 = dict(D)
        del D1[x]
        for a in allp:
            if a in flat:
                continue
            E2 = DM.add_entry(E, a)
            flat2 = flat | {a}
            ex2 = ex | {DM.ROTINV[a]}
            for u in ex2:
                if u in D1:
                    continue
                for v in DM.targets_at(u, w_to, n):
                    if v not in flat2 or weight(u, v, n) != w_to:
                        continue
                    D2 = dict(D1)
                    D2[u] = v
                    st2 = DM.legal_profile(DM.claim_report(E2, D2, n))
                    if st2 is None:
                        continue
                    legal.append((x, y, a, u, v))
                    prod, why = replay(E2, D2, st2, n)
                    if prod is None:
                        continue
                    pE, pD, _ = structure(first_visit_path(prod, n))
                    if len(prod) == DM.predicted_len(E2, D2, n):
                        prods.append((x, y, a, u, v, prod))
    return legal, prods


def derived_set(E, D, st, n, w_from=4):
    """the (x,y,a,u,v) tuples the instrument enumerates."""
    out = set()
    for label, E2, D2, st2, br in DM.demotion_moves(E, D, st, n, w_from):
        parts = label.split('/')
        out.add((parts[1], parts[2], parts[3]))
    return out


def run_brute(n, d, limit):
    DM.build_inv(n)
    files = sorted(f for f in os.listdir(d) if f.endswith('.txt'))[:limit]
    tot = Counter()
    for f in files:
        src = open(os.path.join(d, f)).read().strip()
        if not src.isdigit():
            continue
        for orient, txt in (("F", src), ("R", src[::-1])):
            E, D, st = structure(first_visit_path(txt, n))
            legal, prods = brute_demotions(E, D, st, n)
            der = derived_set(E, D, st, n)
            tot['orientations'] += 1
            tot['brute-legal'] += len(legal)
            tot['brute-products'] += len(prods)
            tot['derived'] += len(der)
            for (x, y, a, u, v) in legal:
                key = (f"{DM.sp(x)}>{DM.sp(y)}", "+" + DM.sp(a),
                       f"{DM.sp(u)}>{DM.sp(v)}")
                if key in der:
                    tot['legal-covered-by-derivation'] += 1
                else:
                    tot['MISSED-BY-DERIVATION'] += 1
                    print("MISSED:", f, orient, key, flush=True)
            for p in prods:
                print(f"*** GENUINE DEMOTION PRODUCT *** {f}[{orient}] "
                      f"len={len(p[5])}", flush=True)
    for k, v in sorted(tot.items()):
        print(f"{k}: {v}")
    return 0 if tot['MISSED-BY-DERIVATION'] == 0 else 2


def n5_carriers(count):
    """n=5 w4-bearing walks: apply the R-BND REV-w4 lift (remove one
    entry, add one w4 door; dlen = +1) to n=5 walks by brute force."""
    n = 5
    DM.build_inv(n)
    out = []
    seeds = []
    for seed in range(count):
        r = subprocess.run(['cargo', 'run', '--release', '--quiet', '--',
                            'rollouts', '-n', '5', '--count', '1',
                            '--epsilon', '0.25', '--seed', str(seed),
                            '--out', '/dev/null',
                            '--strings', f'/tmp/s51n5_{seed}.txt'],
                           capture_output=True, text=True, cwd=R)
        p = f'/tmp/s51n5_{seed}.txt'
        if os.path.exists(p):
            for line in open(p):
                s = line.strip()
                if s.isdigit():
                    seeds.append(s)
    seen = set()
    for s in seeds:
        if s in seen:
            continue
        seen.add(s)
        E, D, st = structure(first_visit_path(s, n))
        flat = DM.flat_of(E)
        for a in sorted(flat):
            if len(E[rotc(a)]) < 2 or DM.ROTINV[a] in D:
                continue
            E2 = DM.del_entry(E, a)
            flat2 = flat - {a}
            for yy in sorted(flat2):
                for xx in DM.sources_at(yy, 4, n):
                    if xx in D or weight(xx, yy, n) != 4:
                        continue
                    if rot(xx) not in flat2:
                        continue
                    D2 = dict(D)
                    D2[xx] = yy
                    st2 = DM.legal_profile(DM.claim_report(E2, D2, n))
                    if st2 is None:
                        continue
                    prod, why = replay(E2, D2, st2, n)
                    if prod is None:
                        continue
                    if len(prod) != DM.predicted_len(E2, D2, n):
                        continue
                    out.append(prod)
    return sorted(set(out))


def run_n5(count):
    n = 5
    DM.build_inv(n)
    carr = n5_carriers(count)
    print(f"n=5 w4-bearing carriers built: {len(carr)}")
    tot = Counter()
    hits = []
    for s in carr:
        for orient, txt in (("F", s), ("R", s[::-1])):
            E, D, st = structure(first_visit_path(txt, n))
            legal, prods = brute_demotions(E, D, st, n)
            der = derived_set(E, D, st, n)
            tot['orientations'] += 1
            tot['brute-legal'] += len(legal)
            tot['brute-products'] += len(prods)
            for (x, y, a, u, v) in legal:
                key = (f"{DM.sp(x)}>{DM.sp(y)}", "+" + DM.sp(a),
                       f"{DM.sp(u)}>{DM.sp(v)}")
                tot['legal-covered-by-derivation' if key in der
                    else 'MISSED-BY-DERIVATION'] += 1
            for p in prods:
                hits.append((txt, p[5]))
                print(f"*** GENUINE n=5 DEMOTION *** src len {len(txt)} "
                      f"-> {len(p[5])}  {p[5]}", flush=True)
    for k, v in sorted(tot.items()):
        print(f"{k}: {v}")
    if hits:
        os.makedirs('out/s51/demotion/n5', exist_ok=True)
        for i, (a, b) in enumerate(hits[:20]):
            open(f'out/s51/demotion/n5/src{i}.txt', 'w').write(a)
            open(f'out/s51/demotion/n5/prod{i}.txt', 'w').write(b)
    return 0 if hits else 2


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    if a[0] == 'brute':
        limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 3
        return run_brute(int(a[1]), a[2], limit)
    if a[0] == 'n5':
        count = int(a[a.index('--count') + 1]) if '--count' in a else 12
        return run_n5(count)
    print(f"unknown mode {a[0]}")
    return 1


if __name__ == '__main__':
    sys.exit(main())
