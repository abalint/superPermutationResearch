#!/usr/bin/env python3
"""s41: I4-A mode 0 — the rewrite-rule applier (SURGERY-DESIGN §11.6).

M-4a proved the compound tier's vocabulary is three RIGID rules, each
object-for-object identical across all its natural instantiations, and
the s39 theorem makes walks structure-determined: a tight walk is the
deterministic REPLAY of (start perm, per-cycle entry sets, door list) —
w2 successors are forced (exit e → g(rot(e))), arc extents are forced
by the entry sets. So applying a rule = a tiny structure edit + replay.

Rules (literal perms, canonical frame; extracted from the 13
cover-sharing pairs by structure diff — 4 distinct perm-level edits
among the 12 n=6 pairs = 2 rules × 2 orientations, 1 at n=7):

  R-compound  (145,3)→(143,5): remove entries 541236 (cycle 123654)
              and 354126 (cycle 126354); add doors 623541→541326 and
              625413→413526 (both w3). Reverse: (143,5)→(145,3) — and
              on OTHER door-carrying allocations the reverse lands on
              (S+2, D−2): from (142,6) that is (144,4), the
              never-occupied allocation.
  R-unit      (143,5)→(142,6): remove entry 213546 (cycle 135462);
              add door 624135→135426 (w3). Reverse: (S+1, D−1).
  R-K7 (n=7)  (844,17)→(843,18): remove entry 3246157 (cycle 1573246)
              AND its feeding door 7513246→3246157; add doors
              5732461→2461537 and 7513246→3246175 (both w3).

The rule preconditions here are NECESSARY (objects present/absent);
sufficiency is decided by the replay itself — a carrier whose edited
structure does not replay to a valid complete walk is logged with the
failure reason (those reasons ARE the rule's finer precondition, to be
folded back into the docs).

Every valid record-length product is written to --out and must go
through `validate -n <n> --file <f> --complete` and
`python3 analysis/counting/m3_check.py [-n 7] <files>` (exit 2 =
novel class = the M3 event). A product SHORTER than the record would
be an improvement candidate: banner + write, drop everything.

Usage:
  python3 analysis/counting/i4a_apply.py oracle
      # re-derive the partner of all 13 pairs byte-identically (exit 0)
  python3 analysis/counting/i4a_apply.py apply <dir> [<dir>...] --out <outdir>
      # scan every walk, apply every rule direction whose precondition
      # holds, replay, classify, write record-length/shorter products
  python3 analysis/counting/i4a_apply.py apply-sym <dir> [<dir>...] --out <outdir>
      # the SYMMETRY-CONJUGATED sweep: every relabeling of every rule
      # direction (n! instances), on both orientations of every walk
      # (reversal included). Products are canon-gated inline against
      # the committed class index: rediscoveries become EDGES of the
      # natural-move graph (written as a TSV), novel classes are
      # written + bannered. The literal `apply` mode found the corpus
      # closed under the canonical-frame rules but missed 8 edges the
      # cover census couldn't see (relabel-equivalent partners) —
      # this mode is the frame-complete version.
"""
import os
import sys
from collections import Counter
from math import factorial

import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting")
from loop_ledger_probe import first_visit_path, g, rot, rotc, weight

P = lambda t: tuple(int(c) for c in t)  # "541236" -> perm tuple

RULES = [
    # (name, n, entries_removed, doors_removed, doors_added)
    # forward = as listed; reverse = swap removed/added
    ("R-compound", 6,
     [P("541236"), P("354126")],
     [],
     [(P("623541"), P("541326")), (P("625413"), P("413526"))]),
    ("R-unit", 6,
     [P("213546")],
     [],
     [(P("624135"), P("135426"))]),
    ("R-K7", 7,
     [P("3246157")],
     [(P("7513246"), P("3246157"))],
     [(P("5732461"), P("2461537")), (P("7513246"), P("3246175"))]),
]


def structure(path):
    arcs, start = [], 0
    for i in range(len(path)):
        if i + 1 == len(path) or rotc(path[i + 1]) != rotc(path[i]):
            arcs.append((rotc(path[start]), path[start], path[i]))
            start = i + 1
    entries = {}
    for c, e, _ in arcs:
        entries.setdefault(c, set()).add(e)
    doors = {}
    n = len(path[0])
    for i in range(len(arcs) - 1):
        if weight(arcs[i][2], arcs[i + 1][1], n) >= 3:
            doors[arcs[i][2]] = arcs[i + 1][1]
    return entries, doors, path[0]


def edit(entries, doors, ents_out, ents_in, doors_out, doors_in):
    """Apply the edit if the necessary precondition holds; None if not."""
    # removals validate against the original structure, additions
    # against the post-removal structure (a rule may reuse a door exit)
    for p in ents_out:
        if p not in entries.get(rotc(p), set()):
            return None
    for e, v in doors_out:
        if doors.get(e) != v:
            return None
    E = {c: set(s) for c, s in entries.items()}
    D = dict(doors)
    for p in ents_out:
        E[rotc(p)].discard(p)
    for e, _ in doors_out:
        del D[e]
    for p in ents_in:
        if p in E.get(rotc(p), set()):
            return None
        E.setdefault(rotc(p), set()).add(p)
    for e, v in doors_in:
        if e in D:
            return None
        D[e] = v
    return E, D


def replay(E, D, start, n):
    """Deterministic replay of a structure. Returns (string, reason)."""
    total_perms = factorial(n)
    out = list(start)
    cur = cur0 = start
    seen_entries = set()
    covered = 0
    for _ in range(total_perms + 1):  # at most one iteration per arc
        c = rotc(cur)
        ec = E.get(c, set())
        if cur not in ec:
            return None, f"landed on non-entry {cur}"
        if cur in seen_entries:
            return None, f"entry revisited {cur}"
        seen_entries.add(cur)
        p = cur
        alen = 1
        while rot(p) not in ec:
            p = rot(p)
            out.append(p[-1])
            alen += 1
        covered += alen
        if covered == total_perms:
            s = "".join(map(str, out))
            fv = first_visit_path(s, n)
            if len(fv) != total_perms:
                return None, f"coverage check failed ({len(fv)})"
            return s, None
        if p in D:
            nxt = D[p]
        else:
            nxt = g(rot(p))
            if nxt not in E.get(rotc(nxt), set()):
                return None, f"w2 target {nxt} not an entry (from exit {p})"
        w = weight(p, nxt, n)
        out.extend(nxt[n - w:])
        cur = nxt
    return None, "replay did not terminate"


def rule_dirs(n):
    for name, rn, ents, d_out, d_in in RULES:
        if rn != n:
            continue
        yield f"{name}-fwd", ents, [], d_out, d_in
        yield f"{name}-rev", [], ents, d_in, d_out


def alloc_of(E, D):
    S = sum(len(s) for s in E.values())
    return S, len(D)


def run_apply(dirs, outdir):
    os.makedirs(outdir, exist_ok=True)
    stats = Counter()
    products = []
    for d in dirs:
        files = sorted(f for f in os.listdir(d) if f.endswith(".txt"))
        for f in files:
            s = open(os.path.join(d, f)).read().strip()
            if not s.isdigit():
                continue
            n = 6 if len(s) < 3000 else 7
            record = 872 if n == 6 else 5906
            path = first_visit_path(s, n)
            entries, doors, start = structure(path)
            for rname, eo, ei, do, di in rule_dirs(n):
                ed = edit(entries, doors, eo, ei, do, di)
                if ed is None:
                    continue
                stats[f"{rname}:carrier"] += 1
                E2, D2 = ed
                prod, reason = replay(E2, D2, start, n)
                if prod is None:
                    kind = reason.split("(")[0].strip()
                    # drop the specific perm from the key so reasons bucket
                    kind = " ".join(t for t in kind.split() if not t.isdigit())
                    stats[f"{rname}:fail:{kind[:48]}"] += 1
                    continue
                L = len(prod)
                al = alloc_of(E2, D2)
                if L < record:
                    stats[f"{rname}:SHORTER-{L}"] += 1
                    name = f"i4a-CANDIDATE-{L}-{rname}-{f}"
                    open(os.path.join(outdir, name), "w").write(prod)
                    products.append(name)
                    print(f"*** {L} < {record} CANDIDATE *** {rname} on {d}/{f} -> {name}")
                elif L == record:
                    stats[f"{rname}:product-{al}"] += 1
                    name = f"i4a-{rname}-S{al[0]}D{al[1]}-{f}"
                    open(os.path.join(outdir, name), "w").write(prod)
                    products.append(name)
                else:
                    stats[f"{rname}:longer-{L}"] += 1
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"\n{len(products)} record-length-or-better products in {outdir}")
    if products:
        print("gate them: python3 analysis/counting/m3_check.py "
              f"[-n 7] {outdir}/*.txt")
    return 0


def run_oracle():
    from m4a_pair_anatomy import PAIRS_N6, PAIRS_N7
    ok = True
    cases = [(ha, hb, 6, "data/upstream872", "872.up-") for ha, hb in PAIRS_N6]
    cases += [(ha, hb, 7, "data/upstream5906", "5906.up-") for ha, hb in PAIRS_N7]
    for ha, hb, n, d, pref in cases:
        sa = open(os.path.join(d, f"{pref}{ha}.txt")).read().strip()
        sb = open(os.path.join(d, f"{pref}{hb}.txt")).read().strip()
        derived = {}
        for src, tgt, tag in [(sa, sb, "A->B"), (sb, sa, "B->A")]:
            path = first_visit_path(src, n)
            entries, doors, start = structure(path)
            hits = []
            for rname, eo, ei, do, di in rule_dirs(n):
                ed = edit(entries, doors, eo, ei, do, di)
                if ed is None:
                    continue
                prod, reason = replay(*ed, start, n)
                if prod == tgt:
                    hits.append(rname)
            derived[tag] = hits
        good = bool(derived["A->B"]) and bool(derived["B->A"])
        ok &= good
        print(f"{ha}<->{hb}: A->B via {derived['A->B']}, "
              f"B->A via {derived['B->A']} {'OK' if good else 'FAIL'}")
    print("oracle:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def run_apply_sym(dirs, outdir, only=None):
    from itertools import permutations as _perms

    from m3_check import SUPPLEMENTARY, canon, load_index
    import hashlib

    os.makedirs(outdir, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    idx = {
        6: load_index(os.path.join(here, "upstream872_canon_index.tsv")),
        7: load_index(os.path.join(here, "upstream5906_canon_index.tsv")),
    }
    # s42: the novelty gate must match m3_check's — published index PLUS
    # this project's own discovery indexes, or a re-derivation of one of
    # our archived classes would be bannered as novel (and the edge to it
    # lost). Missing supplementary files are skipped.
    for nn, supps in SUPPLEMENTARY.items():
        for supp in supps:
            p = os.path.join(here, supp)
            if os.path.exists(p):
                idx[nn].update(load_index(p))

    # precompute every relabeled rule instance, with cycles attached
    def relab(p, sig):
        return tuple(sig[x - 1] for x in p)

    instances = {6: [], 7: []}
    for n in (6, 7):
        for rname, eo, ei, do, di in rule_dirs(n):
            if only and not any(t in rname for t in only):
                continue
            for sig in _perms(range(1, n + 1)):
                inst = (
                    rname,
                    [relab(p, sig) for p in eo],
                    [relab(p, sig) for p in ei],
                    [(relab(a, sig), relab(b, sig)) for a, b in do],
                    [(relab(a, sig), relab(b, sig)) for a, b in di],
                )
                instances[n].append(inst)

    stats = Counter()
    edges = set()  # (n, source class file, target class file, rule)
    novel = []
    novel_shas = set()
    novel_src = {}  # sha -> [(source file, rule, orientation, length)]
    for d in dirs:
        files = sorted(f for f in os.listdir(d) if f.endswith(".txt"))
        for fi, f in enumerate(files):
            src = open(os.path.join(d, f)).read().strip()
            if not src.isdigit():
                continue
            n = 6 if len(src) < 3000 else 7
            record = 872 if n == 6 else 5906
            for orient, txt in (("F", src), ("R", src[::-1])):
                path = first_visit_path(txt, n)
                entries, doors, start = structure(path)
                flat = set().union(*entries.values())
                for rname, eo, ei, do, di in instances[n]:
                    # fast precheck before the full edit
                    if any(p not in flat for p in eo):
                        continue
                    if any(p in flat for p in ei):
                        continue
                    if any(doors.get(a) != b for a, b in do):
                        continue
                    ed = edit(entries, doors, eo, ei, do, di)
                    if ed is None:
                        continue
                    stats[f"{rname}:replayed"] += 1
                    prod, reason = replay(*ed, start, n)
                    if prod is None:
                        continue
                    L = len(prod)
                    if L > record:
                        stats[f"{rname}:longer"] += 1
                        continue
                    sha = hashlib.sha256(canon(prod).encode()).hexdigest()
                    if L == record and sha in idx[n]:
                        tgt = idx[n][sha]
                        if tgt == f:
                            stats[f"{rname}:self-edge"] += 1
                        else:
                            edges.add((n, f, tgt, rname.rsplit("-", 1)[0]))
                            stats[f"{rname}:edge"] += 1
                    else:
                        tag = "SHORTER" if L < record else "NOVEL"
                        # s42: dedupe by canonical sha, not by file name —
                        # one (rule, orientation, source) can yield SEVERAL
                        # distinct products across the n! conjugates, and
                        # name-only dedup silently dropped all but the first.
                        name = (f"i4a-sym-{tag}-{L}-{rname}-{orient}-"
                                f"{sha[:12]}-{f}")
                        p = os.path.join(outdir, name)
                        if sha not in novel_shas:
                            novel_shas.add(sha)
                            open(p, "w").write(prod)
                            novel.append(name)
                            print(f"*** {tag} {L} *** {rname} on {d}/{f} -> {name}")
                        novel_src.setdefault(sha, []).append(
                            (f, rname, orient, L))
            if (fi + 1) % 2000 == 0:
                print(f"[{d}] {fi + 1}/{len(files)} walks; "
                      f"{len(edges)} edges, {len(novel)} novel/shorter so far",
                      flush=True)
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    ep = os.path.join(outdir, "i4a_sym_edges.tsv")
    with open(ep, "w") as out:
        out.write("n\tsource_class\ttarget_class\trule\n")
        for n, a, b, r in sorted(edges):
            out.write(f"{n}\t{a}\t{b}\t{r}\n")
    # undirected unique edges for the headline
    und = {(n, frozenset((a, b)), r) for n, a, b, r in edges}
    if novel_src:
        pp = os.path.join(outdir, "i4a_sym_novel_provenance.tsv")
        with open(pp, "w") as out:
            out.write("product_sha256\tsource_class\trule\torientation\tlength\n")
            for sha, rows in sorted(novel_src.items()):
                for f, rname, orient, L in sorted(set(rows)):
                    out.write(f"{sha}\t{f}\t{rname}\t{orient}\t{L}\n")
        print(f"provenance of {len(novel_src)} distinct products -> {pp}")
    print(f"\n{len(edges)} directed edges ({len(und)} undirected) -> {ep}")
    print(f"{len(novel)} NOVEL/SHORTER products in {outdir}" if novel
          else "corpus CLOSED under the conjugated rule vocabulary "
               "(no novel classes)")
    return 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "oracle":
        return run_oracle()
    if len(sys.argv) >= 3 and sys.argv[1] == "apply-sym":
        args = sys.argv[2:]
        out = "data/i4a_products_sym"
        only = None
        if "--only" in args:
            i = args.index("--only")
            only = args[i + 1].split(",")
            args = args[:i] + args[i + 2:]
        if "--out" in args:
            i = args.index("--out")
            out = args[i + 1]
            args = args[:i] + args[i + 2:]
        return run_apply_sym(args, out, only)
    if len(sys.argv) >= 3 and sys.argv[1] == "apply":
        args = sys.argv[2:]
        out = "data/i4a_products"
        if "--out" in args:
            i = args.index("--out")
            out = args[i + 1]
            args = args[:i] + args[i + 2:]
        return run_apply(args, out)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
