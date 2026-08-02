#!/usr/bin/env python3
"""s49 item1 step 1 — recompute the 198 index and the blind spot from
committed artifacts, hash12-normalizing every node name across tiers."""
import csv
import os
import re
import sys

R = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
DIRS = ['data/upstream5906', 'data/novel5906',
        'data/novel5906b', 'data/novel5906c']

files = {}
for d in DIRS:
    for f in sorted(os.listdir(os.path.join(R, d))):
        if f.endswith('.txt'):
            files[f] = os.path.join(R, d, f)
print(f"corpus files: {len(files)}")


# s64 P1: one body, in pylib/canonical.py (this was the superset of the two
# tracked spellings -- admdiff.py's let the empty match raise IndexError).
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
from pylib.canonical import h12  # noqa: E402,F401


byhash = {}
for f in files:
    byhash.setdefault(h12(f), []).append(f)
dupes = {k: v for k, v in byhash.items() if len(v) > 1}
print(f"distinct hash12 in corpus: {len(byhash)}  (collisions: {dupes})")

EDGEFILES = [
    ('lswap', 'data/loopswap/lswap_sym_edges_n7_ALL_union.tsv',
     'source_class', 'target_class'),
    ('rbnd', 'data/loopswap/rbnd_edges_n7.tsv',
     'source_class', 'target_class'),
    ('i4a', 'data/i4a_products_sym_rev/i4a_sym_edges_n7.tsv',
     'source_class', 'target_class'),
    ('i4a_s42', 'out/i4a_s42_n7_edges.tsv',
     'source_class', 'target_class'),
    ('i4a_198', 'out/s48/item2/i4a198/i4a_sym_edges.tsv',
     'source_class', 'target_class'),
    ('rbnd_198', 'out/s48/item2/rbnd198/rbnd_edges.tsv',
     'source_class', 'target_class'),
    ('rbnd_198relax', 'out/s48/item2/rbnd198_relaxed/rbnd_edges.tsv',
     'source_class', 'target_class'),
]

touched = set()
alledges = set()
per_tier = {}
for tag, path, cs, ct in EDGEFILES:
    p = os.path.join(R, path)
    if not os.path.exists(p):
        print(f"  MISSING {path}")
        continue
    ee = set()
    with open(p) as fh:
        for row in csv.DictReader(fh, delimiter='\t'):
            a, b = h12(row[cs]), h12(row[ct])
            ee.add(frozenset((a, b)))
            touched.add(a)
            touched.add(b)
    per_tier[tag] = ee
    alledges |= ee
    print(f"  {tag:14s} {len(ee):5d} undirected (hash12-normalized) "
          f"from {path}")

unknown = touched - set(byhash)
print(f"\nedge endpoints not in the 198 corpus: {len(unknown)} {sorted(unknown)}")
touched &= set(byhash)
blind = sorted(set(byhash) - touched)
print(f"touched: {len(touched)}   BLIND SPOT: {len(blind)}")
with open(os.path.join(R, 'out/s49/item1/blindspot12.txt'), 'w') as o:
    for h in blind:
        o.write(byhash[h][0] + "\n")
for h in blind:
    print("  ", byhash[h][0])
print(f"\nunion undirected edges over all tiers: {len(alledges)}")
