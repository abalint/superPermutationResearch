#!/usr/bin/env python3
"""Recompute the a6-872 package's confinement coordinates (e, l, s, j, B, x, kappa, beta)
on OUR corpus of 296 distinct 872-symbol superpermutations.

Definitions taken from CLAIM.md / the package's own clean-room script
(audits/fable_review_20260728/scripts/indep_verify.py) -- marked loop =
(last symbol, rotation class of the first n-1); arcs = maximal weight-1 runs;
blocks split at weight >= 3; D(P) = bipartite (rotation classes x entered loops),
one edge per arc.

Tests, per word:
  T1  length identity   867 + e + r + l == L
  T2  r == 0 (claimed unconditional)
  T3  split tax         s <= 5l   (equivalently Delta = 5l - s >= 0)
  T4  block identity    B + x == v - s + e
  T5  confinement       B >= kappa,  kappa == v - s + beta
  T6  j = B - (v - s),  0 <= j <= e,  x == e - j
  T7  beta <= s - 1 (s > 0);  beta == 0 (s == 0)
  T8  block confinement: every maximal weight-2 block lies in ONE component of D(P)
  T9  the cell (e, l, s, j) lies in the 209-cell universe at delta = e + l
"""
import glob
import itertools
import sys
from collections import defaultdict

N = 6
NCLASSES = 120   # (n-1)!
BASELOOPS = 24   # (n-2)!
HPV = 867


def rotclass(w):
    return min(w[i:] + w[:i] for i in range(len(w)))


def genloop(sigma):
    return (sigma[-1], rotclass(sigma[:-1]))


PERMS = set("".join(p) for p in itertools.permutations("123456"))


def analyze(word):
    L = len(word)
    seen, path = {}, []
    for i in range(L - N + 1):
        w = word[i:i + N]
        if w in PERMS and w not in seen:
            seen[w] = i
            path.append((i, w))
    assert len(seen) == 720, "not a superpermutation"
    wts = [path[k + 1][0] - path[k][0] for k in range(len(path) - 1)]
    verts = [p for _, p in path]

    arc_start = [0] + [k + 1 for k, w in enumerate(wts) if w >= 2]
    R = len(arc_start)
    s = R - NCLASSES
    bounds = arc_start + [len(verts)]
    arcs = []
    for a in range(R):
        seg = verts[bounds[a]:bounds[a + 1]]
        cls = {rotclass(x) for x in seg}
        assert len(cls) == 1, "arc crosses rotation classes"
        arcs.append((cls.pop(), genloop(seg[0])))
    assert len({c for c, _ in arcs}) == NCLASSES
    entered = []
    for _, lp in arcs:
        if lp not in entered:
            entered.append(lp)
    v = len(entered)
    l = v - BASELOOPS

    cls_of = [rotclass(x) for x in verts]
    cnt = defaultdict(int)
    complete_at = {}
    for k, c in enumerate(cls_of):
        cnt[c] += 1
        if cnt[c] == N:
            complete_at[c] = k
    final_cls = cls_of[-1]
    r = sum(1 for c, k in complete_at.items()
            if c != final_cls and k >= len(verts) - 1)

    running = {genloop(verts[0])}
    e = 0
    for k, w in enumerate(wts):
        if w == 1:
            continue
        dc = 1 if complete_at[cls_of[k]] <= k else 0
        lt = genloop(verts[k + 1])
        dv = 1 if lt not in running else 0
        running.add(lt)
        d = (w - 1) - dc - dv
        assert d >= 0, "negative per-edge defect"
        e += d

    bnd = [k for k, w in enumerate(wts) if w >= 3]
    B = len(bnd) + 1
    x = sum(wts[k] - 3 for k in bnd)

    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    pairs = [(('C', c), ('L', lp)) for c, lp in arcs]
    assert len(set(pairs)) == R, "multi-edge in D(P)"
    for a, b in pairs:
        union(a, b)
    kappa = len({find(('C', c)) for c, _ in arcs})
    beta = R - (NCLASSES + v) + kappa
    j = B - (v - s)
    Delta = 5 * l - s

    blk_arcs = defaultdict(list)
    for a in range(R):
        blk_arcs[sum(1 for k in bnd if k < bounds[a])].append(a)
    conf_ok = all(len({find(('C', arcs[a][0])) for a in aa}) == 1
                  for aa in blk_arcs.values())

    return dict(L=L, e=e, r=r, l=l, v=v, s=s, B=B, x=x, j=j,
                kappa=kappa, beta=beta, Delta=Delta, conf=conf_ok)


def cell_universe(delta):
    """(e,l,s,j) cells at this delta, per CLAIM.md section 5."""
    out = set()
    for e in range(delta + 1):
        l = delta - e
        for s in range(5 * l + 1):
            for j in range(e + 1):
                out.add((e, l, s, j))
    return out


UNIV = {d: cell_universe(d) for d in range(0, 9)}

files = sorted(glob.glob(sys.argv[1] + "/*.txt")) if len(sys.argv) > 1 else []
for extra in sys.argv[2:]:
    files += sorted(glob.glob(extra + "/*.txt"))
files = [f for f in files if "_filelist" not in f]

fails = defaultdict(list)
cells = defaultdict(int)
words = set()
for f in files:
    word = open(f).read().strip().replace("\n", "")
    if not word or set(word) - set("123456"):
        continue
    words.add(word)
    c = analyze(word)
    tag = f.split("/")[-1]
    T = {
        "T1 len=867+e+r+l": HPV + c['e'] + c['r'] + c['l'] == c['L'],
        "T2 r==0": c['r'] == 0,
        "T3 s<=5l": c['s'] <= 5 * c['l'],
        "T4 B+x==v-s+e": c['B'] + c['x'] == c['v'] - c['s'] + c['e'],
        "T5a B>=kappa": c['B'] >= c['kappa'],
        "T5b kappa==v-s+beta": c['kappa'] == c['v'] - c['s'] + c['beta'],
        "T6a 0<=j<=e": 0 <= c['j'] <= c['e'],
        "T6b x==e-j": c['x'] == c['e'] - c['j'],
        "T7 beta<=s-1": (c['beta'] <= c['s'] - 1) if c['s'] > 0 else (c['beta'] == 0),
        "T8 block confinement": c['conf'],
        "T9 cell in universe": (c['e'], c['l'], c['s'], c['j']) in UNIV[c['e'] + c['l']],
    }
    for k, ok in T.items():
        if not ok:
            fails[k].append((tag, c))
    cells[(c['e'], c['l'], c['s'], c['j'])] += 1

print(f"words read: {len(files)}, distinct: {len(words)}")
print(f"\nTEST RESULTS ({len(words)} distinct 872s)")
for k in ["T1 len=867+e+r+l", "T2 r==0", "T3 s<=5l", "T4 B+x==v-s+e",
          "T5a B>=kappa", "T5b kappa==v-s+beta", "T6a 0<=j<=e", "T6b x==e-j",
          "T7 beta<=s-1", "T8 block confinement", "T9 cell in universe"]:
    n = len(fails[k])
    print(f"  [{'ok  ' if n == 0 else 'FAIL'}] {k:24s} {'all pass' if n == 0 else str(n) + ' failures'}")
    for tag, c in fails[k][:3]:
        print(f"          {tag}: {c}")

print(f"\ncell (e,l,s,j) distribution over the corpus  [delta = e+l must be 5]:")
for cell, n in sorted(cells.items(), key=lambda kv: -kv[1]):
    e, l, s, j = cell
    print(f"  (e={e}, l={l}, s={s}, j={j})  delta={e+l:2d}   {n:4d} words")
