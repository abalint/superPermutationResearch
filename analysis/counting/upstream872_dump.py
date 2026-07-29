#!/usr/bin/env python3
"""Dump one forward-renumbered representative per upstream equivalence
class as individual files for the Rust corpus loader (identity-start
required by trace_string; count exclusions)."""
import os, gzip, hashlib

BASE = os.path.join(os.path.dirname(__file__), "upstream/superpermutations/6")
OUT = "/Users/andrew/Documents/code/math/superperms/superPermutationResearch/data/upstream872"
os.makedirs(OUT, exist_ok=True)

def renumber(s):
    m, nxt, out = {}, 0, []
    for c in s:
        if c not in m:
            nxt += 1
            m[c] = str(nxt)
        out.append(m[c])
    return "".join(out)

def canon(s):
    return min(renumber(s), renumber(s[::-1]))

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
