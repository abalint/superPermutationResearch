#!/usr/bin/env python3
"""s49 item1 — POSITIVE CONTROL for the fused instrument.

Every edge in lswap_sym_edges_n7_ALL_union.tsv was produced by an actual
rule firing, so depth-1 lookup MUST hit on it (and return the recorded
rule id, up to the rule's own reversal/frame images).  If the control
fails, every negative from fuse.py is void.
"""
import csv
import os
import random
import sys

import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting/s49")
import numpy as np                                        # noqa: E402
import fuse                                               # noqa: E402

R = fuse.R
OUT = fuse.OUT
relab = fuse.relab_table()
rules = fuse.load_rules()
keys, ridx, sidx, ruleids = fuse.load_index()
names, W = fuse.load_corpus()
starts = sorted({v[0] for v in W.values()})
from itertools import permutations                        # noqa: E402
sig = list(permutations(range(1, 8)))
sidx_of = {s: i for i, s in enumerate(sig)}
NP = fuse.NP

cache = {}


def get(C, ot, sst):
    k = (C, ot, sst)
    if k in cache:
        return cache[k]
    tst, tflat, tdr = W[(C, ot)]
    tab = relab[sidx_of[fuse.rho_of(tst, sst)]]
    nf = np.zeros(NP, dtype=bool)
    nf[tab[np.flatnonzero(tflat)]] = True
    nd = np.full(NP, -1, dtype=np.int32)
    de = np.flatnonzero(tdr >= 0)
    nd[tab[de]] = tab[tdr[de]]
    cache[k] = (nf, nd)
    return cache[k]


edges = []
with open(os.path.join(R, 'data/loopswap/lswap_sym_edges_n7_ALL_union.tsv')) \
        as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        edges.append((row['source_class'], row['target_class'], row['rule']))
print(f"{len(edges)} recorded loop-swap edges")
random.seed(7)
sample = random.sample(edges, min(200, len(edges)))

ok = 0
same_rule = 0
miss = []
for a, b, rule in sample:
    if (a, 'F') not in W or (b, 'F') not in W:
        print("   SKIP (not in corpus)", a, b)
        continue
    hit = None
    for ob in ('F', 'R'):
        sst, sf, sd = W[(a, ob)]
        for ot in ('F', 'R'):
            tf, td = get(b, ot, sst)
            eo = np.flatnonzero(sf & ~tf)
            ei = np.flatnonzero(tf & ~sf)
            se = np.flatnonzero(sd >= 0)
            te = np.flatnonzero(td >= 0)
            dom = np.array([e for e in se if td[e] != sd[e]], dtype=np.int64)
            dim = np.array([e for e in te if sd[e] != td[e]], dtype=np.int64)
            k = fuse.setkey(eo, ei, dom, sd[dom] if len(dom) else dom,
                            dim, td[dim] if len(dim) else dim)
            i = fuse.lookup(keys, k)
            if i >= 0:
                hit = (ruleids[ridx[i]], int(sidx[i]), len(eo), ob, ot)
                break
        if hit:
            break
    if hit:
        ok += 1
        if hit[0] == rule:
            same_rule += 1
    else:
        miss.append((a, b, rule))
print(f"depth-1 lookup HITS on recorded edges: {ok}/{len(sample)}  "
      f"(recorded rule id recovered exactly: {same_rule})")
for m in miss[:10]:
    print("   MISS", m)
