#!/usr/bin/env python3
"""s49 item1 PART C — POSITIVE CONTROL for the LIBERAL SUMSET test.

`control.py` controls the DEPTH-1 lookup (recorded edges must be found).
This controls the sumset code path itself, end to end.

Construction (the "synthetic 2-step path" control of JOURNAL s49): take a
path A -> B -> C in the recorded loop-swap edge graph.  Rigidity aligns
every target's start to the SOURCE's start, so in A's frame

    delta_req(A -> C)  =  delta(A -> rho.B) + delta(rho.B -> rho'.C)

with both summands genuine vocabulary instances (Delta is closed under
relabeling).  Hence key_req MUST lie in K + K.  A miss here means the
2SUM / linear-hash machinery is broken and every 0 it reports is void.

Each path is verified step-by-step first (both single steps must be
depth-1 hits in the chained orientation) so that a sumset miss can only
be blamed on the sumset code.

Usage: python3 analysis/counting/s49/sumset_control.py [n_paths]
"""
import csv
import os
import random
import sys
import time
from itertools import permutations

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fuse                                                # noqa: E402
import sumset                                              # noqa: E402

R, OUT, NP = fuse.R, fuse.OUT, fuse.NP
NPATHS = int(sys.argv[1]) if len(sys.argv) > 1 else 12


def main():
    t0 = time.time()
    relab = fuse.relab_table()
    keys, ridx, sidx, ruleids = fuse.load_index()
    K = np.load(os.path.join(OUT, 'lin_keys.npy'))
    names, W = fuse.load_corpus()
    sig = list(permutations(range(1, 8)))
    sidx_of = {s: i for i, s in enumerate(sig)}
    starts = sorted({v[0] for v in W.values()})
    print(f"corpus {len(names)} classes, {len(starts)} distinct starts, "
          f"{time.time()-t0:.1f}s", flush=True)

    cache = {}

    def get(C, ot, sst):
        k = (C, ot, sst)
        if k not in cache:
            tst, tflat, tdr = W[(C, ot)]
            tab = relab[sidx_of[fuse.rho_of(tst, sst)]]
            nf = np.zeros(NP, dtype=bool)
            nf[tab[np.flatnonzero(tflat)]] = True
            nd = np.full(NP, -1, dtype=np.int32)
            de = np.flatnonzero(tdr >= 0)
            nd[tab[de]] = tab[tdr[de]]
            cache[k] = (nf, nd)
        return cache[k]

    def diff(sf, sd, tf, td):
        eo = np.flatnonzero(sf & ~tf)
        ei = np.flatnonzero(tf & ~sf)
        se = np.flatnonzero(sd >= 0)
        te = np.flatnonzero(td >= 0)
        dom = se[td[se] != sd[se]]
        dim = te[sd[te] != td[te]]
        return eo, ei, dom, sd[dom], dim, td[dim]

    # recorded loop-swap edges -> adjacency over corpus files
    adj = {}
    with open(os.path.join(
            R, 'data/loopswap/lswap_sym_edges_n7_ALL_union.tsv')) as fh:
        for row in csv.DictReader(fh, delimiter='\t'):
            a, b = row['source_class'], row['target_class']
            if (a, 'F') in W and (b, 'F') in W:
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    paths = []
    for B in sorted(adj):
        nb = sorted(adj[B])
        for i, A in enumerate(nb):
            for C in nb[i + 1:]:
                if A != C:
                    paths.append((A, B, C))
    random.seed(11)
    random.shuffle(paths)
    print(f"{len(paths)} candidate 2-step paths", flush=True)

    ok = 0
    tried = 0
    fails = []
    for (A, B, C) in paths:
        if ok >= NPATHS:
            break
        found = None
        for ob in ('F', 'R'):
            sst, sf, sd = W[(A, ob)]
            for ot1 in ('F', 'R'):
                bf, bd = get(B, ot1, sst)
                d1 = diff(sf, sd, bf, bd)
                if fuse.lookup(keys, fuse.setkey(*d1)) < 0:
                    continue
                for ot2 in ('F', 'R'):
                    cf, cd = get(C, ot2, sst)
                    d2 = diff(bf, bd, cf, cd)
                    if fuse.lookup(keys, fuse.setkey(*d2)) < 0:
                        continue
                    found = (ob, ot1, ot2, sst, sf, sd, cf, cd)
                    break
                if found:
                    break
            if found:
                break
        if not found:
            continue
        tried += 1
        ob, ot1, ot2, sst, sf, sd, cf, cd = found
        eo, ei, dom, domv, dim, dimv = diff(sf, sd, cf, cd)
        kreq = sumset.linkey(eo, ei, dom, domv, dim, dimv)
        want = kreq - K
        pos = np.searchsorted(K, want)
        pos[pos >= len(K)] = 0
        m = np.flatnonzero(K[pos] == want)
        verdict = "HIT" if len(m) else "MISS"
        if len(m):
            ok += 1
        else:
            fails.append((A, B, C, ob, ot1, ot2))
        print(f"  {verdict} {A[5:22]} -> {B[5:22]} -> {C[5:22]} "
              f"[{ob}{ot1}{ot2}] |eo|={len(eo)} sumset_pairs={len(m)}",
              flush=True)

    print(f"\nSUMSET 2-step-path control: {ok}/{tried} paths hit "
          f"({time.time()-t0:.1f}s)")
    for f in fails:
        print("   FAIL", f)
    return 0 if (ok == tried and ok >= NPATHS) else 1


if __name__ == '__main__':
    sys.exit(main())
