#!/usr/bin/env python3
"""s49 item1 — SIZING ONLY for the UNTARGETED fused-pair sweep.

Measures, on a sample of intermediates F' = flat(B) - EO1 + EI1, how many
r2 instances are edit-preconditioned on F', and how long one replay costs.
No products are produced; this exists to write an honest SWEEP-QUEUE
projection.
"""
import os
import sys
import time
from itertools import permutations

import numpy as np

# s64 P1: the second insert used to be the cwd-relative string
# 'analysis/counting' -- this script only worked when launched from the
# repo root.  The bootstrap is __file__-based and cwd-independent.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting/s49", "analysis/counting")
import fuse                                               # noqa: E402
from i4a_apply import replay, structure                   # noqa: E402
from loop_ledger_probe import first_visit_path            # noqa: E402

NP = fuse.NP
relab = fuse.relab_table()
rules = fuse.load_rules()
ids = sorted(rules)
names, W = fuse.load_corpus()
blind = [l.strip() for l in
         open(os.path.join(fuse.OUT, 'blindspot12.txt')) if l.strip()]
B = blind[0]
sst, sf, sd = W[(B, 'F')]


def preconditioned(flat, doors):
    inst = []
    for j, rid in enumerate(ids):
        eo, ei, (doe, dov), (die, div) = rules[rid]
        ok = np.ones(NP, dtype=bool)
        if len(eo):
            ok &= flat[relab[:, eo]].all(axis=1)
        if not ok.any():
            continue
        if len(ei):
            ok &= ~flat[relab[:, ei]].any(axis=1)
        if not ok.any():
            continue
        if len(doe):
            ok &= (doors[relab[:, doe]] == relab[:, dov]).all(axis=1)
        if not ok.any():
            continue
        if len(die):
            ok &= (doors[relab[:, die]] == -1).all(axis=1)
        for k in np.flatnonzero(ok):
            inst.append((j, int(k)))
    return inst


t0 = time.time()
base = preconditioned(sf, sd)
t_scan = time.time() - t0
print(f"{B}[F]: {len(base)} preconditioned r1 instances, "
      f"scan {t_scan:.1f}s")

rng = np.random.default_rng(5)
sample = [base[i] for i in rng.choice(len(base), 8, replace=False)]
tot = 0
for (j, k) in sample:
    eo, ei, (doe, dov), (die, div) = rules[ids[j]]
    tab = relab[k]
    fp = sf.copy()
    if len(eo):
        fp[tab[eo]] = False
    if len(ei):
        fp[tab[ei]] = True
    dp = sd.copy()
    if len(doe):
        dp[tab[doe]] = -1
    if len(die):
        dp[tab[die]] = tab[div]
    t1 = time.time()
    inst2 = preconditioned(fp, dp)
    tot += len(inst2)
    print(f"  r1={ids[j]}[sigma {k}] |eo|={len(eo)} -> intermediate has "
          f"{len(inst2)} preconditioned r2 instances ({time.time()-t1:.1f}s)")
print(f"mean r2 instances per intermediate: {tot/len(sample):.1f}")

# replay cost
src = open([os.path.join(fuse.R, d, B) for d in
            ['data/upstream5906'] if os.path.exists(
                os.path.join(fuse.R, d, B))][0]).read().strip()
E, D, st = structure(first_visit_path(src, 7))
t1 = time.time()
for _ in range(5):
    replay(E, D, st, 7)
print(f"replay cost: {(time.time()-t1)/5*1000:.0f} ms")
