#!/usr/bin/env python3
"""Check the two s26 hybrids against ALL upstream n=6 872s
(superpermutators/superperm), up to relabeling + reversal."""
import os, gzip, sys

BASE = os.path.join(os.path.dirname(__file__), "upstream/superpermutations/6")
HYB = "/Users/andrew/Documents/code/math/superperms/superPermutationResearch/data/hybrids872"

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
            sources.append((f"{d}/{f}", open(p).read()))
for f in ("872-nonstandard.txt", "872-treelike-slack2.txt"):
    sources.append((f, open(os.path.join(BASE, f)).read()))
for f in ("872-treelike.txt.gz", "872-treelike-slack1.txt.gz", "872-treelike-2cycles.txt.gz"):
    sources.append((f, gzip.open(os.path.join(BASE, f), "rt").read()))

canons = {}
total = 0
for name, text in sources:
    for s in strings_from_text(text):
        total += 1
        canons.setdefault(canon(s), name)

print(f"upstream 872 strings scanned: {total}")
print(f"upstream equivalence classes: {len(canons)}")

for f in sorted(os.listdir(HYB)):
    if not f.endswith(".txt"):
        continue
    s = open(os.path.join(HYB, f)).read().strip()
    c = canon(s)
    hit = canons.get(c)
    print(f"hybrid {f}: {'EQUIVALENT to upstream ' + hit if hit else 'NEW vs ALL upstream (relabel+reversal)'}")

# --- addendum: byte-identity, sample coverage, weight multisets ---
print("\n-- byte identity of hybrids --")
allstrings = set()
for name, text in sources:
    for s in strings_from_text(text):
        allstrings.add(s)
for f in sorted(os.listdir(HYB)):
    if f.endswith(".txt"):
        s = open(os.path.join(HYB, f)).read().strip()
        print(f"hybrid {f}: byte-identical in upstream = {s in allstrings}")

print("\n-- our local 296 vs upstream --")
LOCAL = "/Users/andrew/Documents/code/math/superperms/superPermutationResearch/data"
local = {}
for d in ("records872", "gain1_872s"):
    dd = os.path.join(LOCAL, d)
    for f in sorted(os.listdir(dd)):
        s = open(os.path.join(dd, f)).read().strip()
        if s and all(c in "123456" for c in s):
            local[f"{d}/{f}"] = s
lc = {canon(s) for s in local.values()}
print(f"local classes: {len(lc)}; in upstream: {len(lc & set(canons))}; NOT upstream: {len(lc - set(canons))}")
for name, s in local.items():
    if canon(s) not in canons:
        print(f"  local-only: {name}")

print("\n-- upstream weight multisets (the 575/141/3 'universal' claim) --")
from collections import Counter, defaultdict
def multiset(s):
    # weights via overlap of consecutive windows: simpler proxy — count
    # by first-visit reconstruction is heavy; use canonical char method:
    # weight sum = 866 fixed; derive w-histogram from window advances.
    # Sliding: each new perm window at offset i means overlap n-(i-j)...
    # Do it properly but vectorized-ish.
    n = 6
    seen = set()
    lastpos = None
    hist = Counter()
    for i in range(len(s) - n + 1):
        w = s[i:i+n]
        if len(set(w)) == n:
            if w not in seen:
                seen.add(w)
                if lastpos is not None:
                    hist[i - lastpos] += 1
                lastpos = i
    return tuple(hist[k] for k in (1, 2, 3, 4, 5))

ms_count = Counter()
example = {}
for c in canons:          # one representative per class (canonical string itself is a valid superperm? renumbered/reversed still a superperm - yes)
    m = multiset(c)
    ms_count[m] += 1
    example.setdefault(m, c[:30])
print(f"distinct weight multisets across {len(canons)} upstream classes: {len(ms_count)}")
for m, cnt in ms_count.most_common(10):
    print(f"  w1..w5={m}: {cnt} classes")

print("\n-- upstream splice hybrids: new up to equivalence? --")
UH = os.path.join(os.path.dirname(__file__), "upstream_hybrids")
if os.path.isdir(UH):
    for f in sorted(os.listdir(UH)):
        if f.endswith(".txt") and f.startswith("872.h-"):
            s = open(os.path.join(UH, f)).read().strip()
            c = canon(s)
            hit = canons.get(c)
            print(f"{f}: {'equivalent to known (' + hit + ')' if hit else 'NEW TO COMMUNITY (up to relabel+reversal)'}")
    # and pairwise among the five
    hs = {f: open(os.path.join(UH, f)).read().strip() for f in sorted(os.listdir(UH)) if f.startswith('872.h-')}
    ks = list(hs)
    for i in range(len(ks)):
        for j in range(i+1, len(ks)):
            if canon(hs[ks[i]]) == canon(hs[ks[j]]):
                print(f"  {ks[i]} ~ {ks[j]} (mutually equivalent)")
