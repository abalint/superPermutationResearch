#!/usr/bin/env python3
"""s47 item1: R-BND -- the boundary/door unit trade, as an instrument.

THE MOVE (derived from the three (842,19)<->(844,17) conjugated cover
twins; see out/s47/item1/RULE.md).  In the s39 tight-cover frame a walk
has D doors + the walk END terminating D+1 partial-loop chains, and D
door TARGETS + the walk START beginning them.  R-BND trades one door
against one walk boundary:

  FWD-END  (S+1, D-1), START PRESERVED
     l2 := loop(rot(end)); its chain is terminated by the walk end.
     d2 := the unique door (x2->y2) with y2 in l2 (y2 begins l2's chain).
     delete d2; add entry a2 = g(rot(end)); l2 closes; new end = x2.
  FWD-START (S+1, D-1), END PRESERVED  [= FWD-END under reversal]
     l1 := the loop whose chain BEGINS at the walk start.
     d1 := the unique door (x1->y1) with start in loop(rot(x1)).
     delete d1; add entry a1 = g(rot(x1)); l1 closes; new start = y1.
  REV-END  (S-1, D+1), START PRESERVED
     pick an entry a (on a full loop); remove it; add door
     (end -> g(a)) -- must have weight exactly 3 to stay at 5906;
     new end = rot^-1(g^-1(a)).
  REV-START (S-1, D+1), END PRESERVED
     pick an entry a; remove it; add door (rot^-1(g^-1(a)) -> start);
     new start = g(a).

The composite FWD-START . FWD-END is the (842,19)->(844,17) twin move
(oracle: 3/3 byte-identical).

Usage:
  python3 rbnd.py oracle
  python3 rbnd.py sweep <dir>[,<dir>...] --out <outdir> [--gens N]
"""
import hashlib
import os
import sys
from collections import Counter

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting")
from loop_ledger_probe import first_visit_path, g, rot, rotc, weight  # noqa: E402
from i4a_apply import replay, structure  # noqa: E402
from m3_check import SUPPLEMENTARY, canon, load_index  # noqa: E402

n = 7
RECORD = 5906
HERE = os.path.join(R, 'analysis', 'counting')

GINV = {}
ROTINV = {}


def build_inv():
    from itertools import permutations
    for p in permutations(range(1, n + 1)):
        GINV[g(p)] = p
        ROTINV[rot(p)] = p


def s(p):
    return "".join(map(str, p))


def loop_list(p):
    o, q = [], p
    for _ in range(n - 1):
        o.append(q)
        q = g(q)
    return o


def moves(E, D, st, end, relaxed=False):
    """All R-BND applications of a structure. Yields
    (label, E2, D2, newstart).  relaxed=True drops the boundary clause
    on the FWD side (try EVERY door, both re-origination choices)."""
    out = []
    # ---- FWD-END: delete the door that begins loop(rot(end))'s chain
    l2 = set(loop_list(rot(end)))
    a2 = g(rot(end))
    for x2, y2 in D.items():
        if y2 in l2 or relaxed:
            aa = a2 if y2 in l2 else g(rot(x2))
            E2 = {c: set(v) for c, v in E.items()}
            E2.setdefault(rotc(aa), set()).add(aa)
            D2 = dict(D)
            del D2[x2]
            out.append((f"FWD-END/{s(x2)}>{s(y2)}", E2, D2, st))
    # ---- FWD-START: delete the door whose loop chain begins at start
    for x1, y1 in D.items():
        if st in loop_list(rot(x1)) or relaxed:
            a1 = g(rot(x1))
            E2 = {c: set(v) for c, v in E.items()}
            E2.setdefault(rotc(a1), set()).add(a1)
            D2 = dict(D)
            del D2[x1]
            out.append((f"FWD-START/{s(x1)}>{s(y1)}", E2, D2, y1))
    flat = set().union(*E.values())
    # ---- REV-END: remove an entry a, add door (end -> g(a)) of weight 3
    for a in flat:
        ga = g(a)
        if weight(end, ga, n) != 3 or end in D:
            continue
        if a == st:
            continue
        E2 = {c: set(v) for c, v in E.items()}
        E2[rotc(a)].discard(a)
        D2 = dict(D)
        D2[end] = ga
        out.append((f"REV-END/{s(a)}", E2, D2, st))
    # ---- REV-START: remove an entry a, add door (rot^-1(g^-1(a)) -> start)
    for a in flat:
        x1 = ROTINV[GINV[a]]
        if weight(x1, st, n) != 3 or x1 in D:
            continue
        ga = g(a)
        if a == st:
            continue
        E2 = {c: set(v) for c, v in E.items()}
        E2[rotc(a)].discard(a)
        D2 = dict(D)
        D2[x1] = st
        out.append((f"REV-START/{s(a)}", E2, D2, ga))
    return out


def index():
    idx = load_index(os.path.join(HERE, "upstream5906_canon_index.tsv"))
    for supp in SUPPLEMENTARY.get(7, []):
        p = os.path.join(HERE, supp)
        if os.path.exists(p):
            idx.update(load_index(p))
    return idx


def file_map(dirs):
    files = {}
    for d in dirs:
        for f in sorted(os.listdir(d)):
            if f.endswith(".txt"):
                files[f] = os.path.join(d, f)
    return files


def run_sweep(dirs, outdir, gens=1, relaxed=False):
    build_inv()
    os.makedirs(outdir, exist_ok=True)
    idx = index()
    print(f"index: {len(idx)} known 5906 classes")
    files = file_map(dirs)
    print(f"{len(files)} source walks")
    stats = Counter()
    edges = set()
    novel = {}         # sha -> (string, [provenance])
    frontier = [(f, open(p).read().strip()) for f, p in files.items()]
    seen_src = set()
    for gen in range(1, gens + 1):
        nxt = []
        print(f"\n--- generation {gen}: {len(frontier)} sources", flush=True)
        for name, src in frontier:
            if not src.isdigit():
                continue
            for orient, txt in (("F", src), ("R", src[::-1])):
                path = first_visit_path(txt, n)
                E, D, st = structure(path)
                end = path[-1]
                for label, E2, D2, st2 in moves(E, D, st, end, relaxed):
                    kind = label.split("/")[0]
                    stats[f"{kind}:tried"] += 1
                    prod, why = replay(E2, D2, st2, n)
                    if prod is None:
                        stats[f"{kind}:replay-killed"] += 1
                        continue
                    L = len(prod)
                    if L > RECORD:
                        stats[f"{kind}:longer"] += 1
                        continue
                    sha = hashlib.sha256(canon(prod).encode()).hexdigest()
                    if L == RECORD and sha in idx:
                        tgt = idx[sha]
                        if tgt == name:
                            stats[f"{kind}:self-edge"] += 1
                        else:
                            edges.add((name, tgt, kind))
                            stats[f"{kind}:edge"] += 1
                    elif L == RECORD and sha in novel:
                        novel[sha][1].append((name, orient, label))
                        edges.add((name, f"NEW-{sha[:12]}", kind))
                        stats[f"{kind}:edge-to-new"] += 1
                    else:
                        tag = "SHORTER" if L < RECORD else "NOVEL"
                        stats[f"{kind}:{tag}"] += 1
                        novel[sha] = (prod, [(name, orient, label)])
                        nm = f"rbnd-{tag}-{L}-{sha[:12]}.txt"
                        open(os.path.join(outdir, nm), "w").write(prod)
                        print(f"*** {tag} {L} *** {kind} on {name}[{orient}] "
                              f"-> {nm}", flush=True)
                        nxt.append((nm, prod))
            seen_src.add(name)
        frontier = [x for x in nxt if x[0] not in seen_src]
        if not frontier:
            print("fixed point reached")
            break
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    ep = os.path.join(outdir, "rbnd_edges.tsv")
    with open(ep, "w") as out:
        out.write("source_class\ttarget_class\tmove\n")
        for a, b, r in sorted(edges):
            out.write(f"{a}\t{b}\t{r}\n")
    und = {frozenset((a, b)) for a, b, _ in edges}
    pp = os.path.join(outdir, "rbnd_provenance.tsv")
    with open(pp, "w") as out:
        out.write("product_sha256\tsource\torientation\tmove\n")
        for sha, (_, prov) in sorted(novel.items()):
            for nm, orient, label in prov:
                out.write(f"{sha}\t{nm}\t{orient}\t{label}\n")
    print(f"\n{len(edges)} directed edges ({len(und)} undirected) -> {ep}")
    print(f"{len(novel)} distinct NOVEL/SHORTER products in {outdir}")
    return 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "sweep":
        dirs = sys.argv[2].split(",")
        outdir = "out/s47/item1/sweep"
        gens = 1
        a = sys.argv[3:]
        if "--out" in a:
            outdir = a[a.index("--out") + 1]
        if "--gens" in a:
            gens = int(a[a.index("--gens") + 1])
        return run_sweep(dirs, outdir, gens, "--relaxed" in a)
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
