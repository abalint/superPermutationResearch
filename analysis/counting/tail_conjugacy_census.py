#!/usr/bin/env python3
"""s43: tail-conjugacy census — the non-census detector the s42 verdict
asked for.

s42 closed the loop-cover front as instrumented: the cover census is
provably blind to R-K7 products (the rule is exactly cover-preserving),
and rule closure is a fixed point. But s42 also left one dangling
signal: the recomp2 funnel counts pair up BYTE-IDENTICALLY across three
pairs of inequivalent novel walks — suggesting relabel-conjugate TAIL
structure between walks whose full classes are inequivalent.

This instrument tests that directly, at string level. For a walk s and
a depth d, the d-tail is the substring of s from the first character of
its (d+1)-th first-visit permutation to the end (so it realizes the
last N−d perm visits, N = n!). Two walks share a d-tail iff their
d-tails are equal after first-occurrence renumbering (m3_check's
relabel convention, per orientation — a walk and its reversal each
contribute their own tail). Sharing is MONOTONE in d: a relabel
bijection matching the d-tails restricts to every suffix, so each
colliding pair has a well-defined DEEPEST shared tail, found by binary
search.

Why this is a genuinely different detector from the cover census:
  - the cover census compares unordered used-loop SETS of whole walks;
  - this compares ordered, literal traversal SUFFIXES up to relabeling,
    localized by depth — exactly the coordinates the recomp2 funnel
    lives in, and a place where cover-preserving rules can leave a
    visible boundary (the diff objects sit at depths 2520–4137; below
    them the traversals may coincide).

Usage:
  python3 analysis/counting/tail_conjugacy_census.py -n 7 \
      data/upstream5906 data/novel5906 [--anchor 4840] [--deep]
  python3 analysis/counting/tail_conjugacy_census.py -n 6 \
      data/upstream872 [--anchor 520] [--deep]

--anchor d : census collisions of d-tails (default: the recomp2 band,
             4840 at n=7 / 520 at n=6).
--deep     : for every colliding pair, binary-search the deepest shared
             tail (min d) and report its length in perms.
--pairs f  : summary mode — one TSV row per unordered CLASS pair that
             collides at the anchor: deepest shared tail over all four
             orientation combos, annotated KNOWN-EDGE if the pair is an
             edge of the natural-move graph (i4a_sym_edges_n7.tsv /
             i4a_sym_edges.tsv), else NEW. Writes the TSV to f.
--edges f  : (s49) add an edge table to the KNOWN-EDGE reference set;
             repeatable.  WITHOUT it the reference set is the two BASE
             tables above — only 41 undirected n=7 edges, 1,973 short of
             the 2,014 the known tiers actually carry (s48 called this
             "~340 short"; measured s49).  Pass the full union, e.g.
               --edges data/loopswap/lswap_sym_edges_n7_ALL_union.tsv \
               --edges data/loopswap/rbnd_edges_n7.tsv \
               --edges data/i4a_products_sym_rev/i4a_sym_edges_n7.tsv
             Tables may be 4-column (n, source, target, rule) or
             3-column (source, target, move); node names are matched by
             their 12-hex class hash, so the three spellings of an R-BND
             node (NEW-<h>, rbnd-NOVEL-5906-<h>.txt, 5906.rbnd-<h>.txt)
             all resolve to the same vertex.
--all f    : null-model mode — exact longest shared tail for EVERY
             unordered class pair (every pair trivially matches at the
             final perm, so the binary search is always anchored).
             Writes the full TSV to f and prints the distribution —
             the check that anchored collisions are a discrete relation
             and not the tail of a continuum.
Exit 0 always (a measurement, not a gate); collisions are the product.
"""
import hashlib
import os
import re
import sys
from collections import defaultdict
from math import factorial


def renumber(s):
    m, nxt, out = {}, 0, []
    for c in s:
        if c not in m:
            nxt += 1
            m[c] = str(nxt)
        out.append(m[c])
    return "".join(out)


def first_visit_starts(s, n):
    """Start index of each first-visit permutation window, in order."""
    want = set("123456789"[:n])
    seen, starts = set(), []
    for i in range(len(s) - n + 1):
        w = s[i : i + n]
        if len(set(w)) == n and set(w) <= want and w not in seen:
            seen.add(w)
            starts.append(i)
    return starts


class Walk:
    __slots__ = ("name", "fwd", "rev", "fwd_starts", "rev_starts")

    def __init__(self, name, s, n):
        self.name = name
        self.fwd = s
        self.rev = s[::-1]
        self.fwd_starts = first_visit_starts(self.fwd, n)
        self.rev_starts = first_visit_starts(self.rev, n)

    def tail(self, orient, d):
        s, starts = (
            (self.fwd, self.fwd_starts) if orient == "f" else (self.rev, self.rev_starts)
        )
        return s[starts[d] :]


def tail_key(w, orient, d):
    return hashlib.sha256(renumber(w.tail(orient, d)).encode()).hexdigest()


def collisions_at(walks, d):
    """fp -> [(walk, orient)] with >1 distinct walk, at depth d."""
    groups = defaultdict(list)
    for w in walks:
        for o in ("f", "r"):
            groups[tail_key(w, o, d)].append((w, o))
    out = []
    for fp, members in groups.items():
        if len({m[0].name for m in members}) > 1:
            out.append(members)
    return out


def deepest_shared(wa, oa, wb, ob, d_hi):
    """Smallest d in [0, d_hi] where the d-tails still match (monotone)."""
    lo, hi = 0, d_hi  # invariant: match at hi, unknown below
    while lo < hi:
        mid = (lo + hi) // 2
        if tail_key(wa, oa, mid) == tail_key(wb, ob, mid):
            hi = mid
        else:
            lo = mid + 1
    return hi


HASH12 = re.compile(r"([0-9a-f]{12})")


def class_key(name):
    """Vertex identity of a class node: its 12-hex hash if it has one.

    The tiers spell the same class three ways (`NEW-<h>`,
    `rbnd-NOVEL-5906-<h>.txt`, `5906.rbnd-<h>.txt`) — normalizing here is
    what keeps a cross-tier union from double-counting (s48 trap).  On the
    base tables the map is injective, so default behaviour is unchanged.
    """
    m = HASH12.search(name)
    return m.group(1) if m else name


def load_known_edges(n, extra=()):
    """Undirected natural-move edges from the committed censuses:
    i4a (cover-preserving rules, s41) + loop-swap (s44), plus any tables
    named by --edges.  Keys are hash12-normalized (see class_key)."""
    here = os.path.dirname(os.path.abspath(__file__))
    fn = "i4a_sym_edges_n7.tsv" if n == 7 else "i4a_sym_edges.tsv"
    paths = [
        os.path.join(here, "..", "..", "data", "i4a_products_sym_rev", fn),
        os.path.join(here, "..", "..", "data", "loopswap",
                     f"lswap_sym_edges_n{n}.tsv"),
    ] + list(extra)
    edges = set()
    for path in paths:
        if os.path.exists(path):
            with open(path) as f:
                # 4-column (n, source, target, rule) or 3-column
                # (source, target, move) — decide from the header.
                off = 1 if f.readline().split("\t")[0].strip() == "n" else 0
                for line in f:
                    fld = line.rstrip("\n").split("\t")
                    if len(fld) < off + 2:
                        continue
                    a, b = fld[off], fld[off + 1]
                    edges.add(frozenset((class_key(a), class_key(b))))
    return edges


def edge_key(a, b):
    return frozenset((class_key(a), class_key(b)))


def main():
    args = sys.argv[1:]
    n = 6
    if args[:1] == ["-n"]:
        n = int(args[1])
        args = args[2:]
    anchor = None
    deep = False
    pairs_out = None
    all_out = None
    extra_edges = []
    dirs = []
    i = 0
    while i < len(args):
        if args[i] == "--anchor":
            anchor = int(args[i + 1])
            i += 2
        elif args[i] == "--deep":
            deep = True
            i += 1
        elif args[i] == "--pairs":
            pairs_out = args[i + 1]
            i += 2
        elif args[i] == "--all":
            all_out = args[i + 1]
            i += 2
        elif args[i] == "--edges":
            extra_edges.append(args[i + 1])
            i += 2
        else:
            dirs.append(args[i])
            i += 1
    if anchor is None:
        anchor = 4840 if n == 7 else 520
    nfact = factorial(n)

    walks = []
    for d in dirs:
        for f in sorted(os.listdir(d)):
            if not f.endswith(".txt"):
                continue
            s = open(os.path.join(d, f)).read().strip()
            if not s.isdigit():
                continue
            w = Walk(f, s, n)
            if len(w.fwd_starts) != nfact:
                print(f"SKIP {f}: {len(w.fwd_starts)} first visits", file=sys.stderr)
                continue
            walks.append(w)
    print(f"n={n}: {len(walks)} walks, anchor {anchor} "
          f"(tails of {nfact - anchor} perm visits), both orientations")

    if all_out:
        from collections import Counter

        known = load_known_edges(n, extra_edges)
        last = nfact - 1  # every pair's tails match at the final perm
        rows = []
        for i in range(len(walks)):
            for j in range(i + 1, len(walks)):
                best_d, best_o = None, None
                for oa in ("f", "r"):
                    for ob in ("f", "r"):
                        d = deepest_shared(walks[i], oa, walks[j], ob, last)
                        if best_d is None or d < best_d:
                            best_d, best_o = d, f"{oa}{ob}"
                rows.append((walks[i].name, walks[j].name, best_d, best_o))
        rows.sort(key=lambda r: r[2])
        with open(all_out, "w") as out:
            out.write("class_a\tclass_b\tdeepest_d\tshared_perms\torient\tstatus\n")
            for a, b, d, o in rows:
                status = "KNOWN-EDGE" if edge_key(a, b) in known else ""
                out.write(f"{a}\t{b}\t{d}\t{nfact - d}\t{o}\t{status}\n")
        hist = Counter()
        for _, _, d, _ in rows:
            sp = nfact - d
            # log-ish bins
            for lo, hi, tag in [(1, 8, "1-7"), (8, 16, "8-15"), (16, 32, "16-31"),
                                (32, 64, "32-63"), (64, 128, "64-127"),
                                (128, 256, "128-255"), (256, 512, "256-511"),
                                (512, 1024, "512-1023"), (1024, 2048, "1024-2047"),
                                (2048, 1 << 30, ">=2048")]:
                if lo <= sp < hi:
                    hist[tag] += 1
                    break
        print(f"{len(rows)} pairs; shared-tail-length histogram (perms):")
        for lo, hi, tag in [(1, 8, "1-7"), (8, 16, "8-15"), (16, 32, "16-31"),
                            (32, 64, "32-63"), (64, 128, "64-127"),
                            (128, 256, "128-255"), (256, 512, "256-511"),
                            (512, 1024, "512-1023"), (1024, 2048, "1024-2047"),
                            (2048, 1 << 30, ">=2048")]:
            if hist[tag]:
                print(f"  {tag:>10}: {hist[tag]}")
        print(f"-> {all_out}")
        return 0

    colls = collisions_at(walks, anchor)
    if not colls:
        print(f"0 cross-walk tail collisions at anchor {anchor}")
        return 0

    if pairs_out:
        known = load_known_edges(n, extra_edges)
        best = {}  # frozenset(names) -> (dmin, orient tag)
        for members in colls:
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    (wa, oa), (wb, ob) = members[i], members[j]
                    if wa.name == wb.name:
                        continue
                    key = frozenset((wa.name, wb.name))
                    dmin = deepest_shared(wa, oa, wb, ob, anchor)
                    if key not in best or dmin < best[key][0]:
                        best[key] = (dmin, f"{oa}{ob}")
        rows = sorted(best.items(), key=lambda kv: kv[1][0])
        with open(pairs_out, "w") as out:
            out.write("class_a\tclass_b\tdeepest_d\tshared_perms\torient\tstatus\n")
            for key, (dmin, orient) in rows:
                a, b = sorted(key)
                status = ("KNOWN-EDGE" if edge_key(a, b) in known
                          else "NEW")
                out.write(f"{a}\t{b}\t{dmin}\t{nfact - dmin}\t{orient}\t{status}\n")
        n_new = sum(1 for k, _ in rows
                    if edge_key(*sorted(k)) not in known)
        print(f"{len(rows)} colliding class pairs at anchor {anchor} "
              f"({n_new} NEW vs the natural-move graph, "
              f"{len(rows) - n_new} known edges) -> {pairs_out}")
        for key, (dmin, orient) in rows:
            a, b = sorted(key)
            status = "KNOWN-EDGE" if edge_key(a, b) in known else "NEW"
            print(f"  {a} ~ {b}: shared {nfact - dmin} perms "
                  f"(d={dmin}, {orient}) {status}")
        return 0

    print(f"{len(colls)} shared-tail groups at anchor {anchor}:")
    for members in sorted(colls, key=lambda ms: sorted(m[0].name for m in ms)):
        names = [f"{w.name}[{o}]" for w, o in members]
        print(f"  group: {names}")
        if deep:
            # deepest shared tail for each pair inside the group
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    (wa, oa), (wb, ob) = members[i], members[j]
                    if wa.name == wb.name:
                        continue
                    dmin = deepest_shared(wa, oa, wb, ob, anchor)
                    print(f"    {wa.name}[{oa}] ~ {wb.name}[{ob}]: "
                          f"deepest shared tail d={dmin} "
                          f"({nfact - dmin}/{nfact} perms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
