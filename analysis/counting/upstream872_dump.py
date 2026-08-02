#!/usr/bin/env python3
"""Dump one forward-renumbered representative per upstream equivalence
class as individual files for the Rust corpus loader (identity-start
required by trace_string; count exclusions)."""
import os, gzip, hashlib

BASE = os.path.join(os.path.dirname(__file__), "upstream/superpermutations/6")
OUT = "/Users/andrew/Documents/code/math/superperms/superPermutationResearch/data/upstream872"
os.makedirs(OUT, exist_ok=True)

# s64 P1: one body each, in pylib/walkio.py + pylib/canonical.py.  `canon`
# here is the RELABEL+REVERSAL class representative (m3_check semantics) --
# pylib keeps it apart from the kernelchain least-rotation `canon` by name.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
from pylib.canonical import canon_relabel_rev as canon  # noqa: E402,F401
from pylib.walkio import renumber  # noqa: E402,F401

def strings_from_text(text):
    for line in text.splitlines():
        line = line.strip()
        if len(line) == 872 and all(c in "123456" for c in line):
            yield line

sources = []
for d in ("872", "872-tahg"):
    dd = os.path.join(BASE, d)
    for f in sorted(os.listdir(dd)):
        p = os.path.join(dd, f)
        if os.path.isfile(p):
            sources.append(open(p).read())
for f in ("872-nonstandard.txt", "872-treelike-slack2.txt"):
    sources.append(open(os.path.join(BASE, f)).read())
for f in ("872-treelike.txt.gz", "872-treelike-slack1.txt.gz", "872-treelike-2cycles.txt.gz"):
    sources.append(gzip.open(os.path.join(BASE, f), "rt").read())

reps = {}
for text in sources:
    for s in strings_from_text(text):
        c = canon(s)
        if c not in reps:
            reps[c] = renumber(s)  # forward orientation, starts at identity if first 6 distinct

skipped = 0
written = 0
for c, fwd in reps.items():
    if len(set(fwd[:6])) != 6:
        skipped += 1
        continue
    h = hashlib.sha1(fwd.encode()).hexdigest()[:12]
    with open(os.path.join(OUT, f"872.up-{h}.txt"), "w") as f:
        f.write(fwd)
    written += 1
print(f"classes: {len(reps)}, written: {written}, skipped(non-identity-start): {skipped}")
