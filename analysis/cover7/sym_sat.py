#!/usr/bin/env python3
"""2-fold symmetric cover search for palindromic chains (Egan 2SYMM style).

The reversal involution sigma (word reversal + relabeling tau) maps the
instance to itself when the chain's ride pattern is palindromic.  We impose
x_r = x_sigma(r) in the SAT encoding — a heuristic restriction: any model is
a genuine cover (checked + compiled as usual), found in ~half the space.

usage: satenv/bin/python sym_sat.py <chains.jsonl> <index> [--time-limit S]
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict

from pysat.solvers import Cadical195

import gain1
import chain7
from chain7 import (
    build_instance_from_chain, compile_chain_cover, canonical_rotation,
    loops, entries, orbitsets, li, ridden_orbits_of, ALPHA,
)


def build_sigma(sol, inst):
    """Return (sigma_orbit, sigma_row_index) or raise if not symmetric."""
    # final walk perm = splice source of the last ridden orbit of the last loop
    L, lk = sol[-1][0], sol[-1][1]
    last_entry = entries[L][(lk + 5 - sol[-1][3]) % 6]
    final = last_entry[-1] + last_entry[:-1]  # rot-right-1 = exit source
    rev = final[::-1]
    tau = str.maketrans(rev, ALPHA)

    def sig_perm(p):
        return p[::-1].translate(tau)

    def sig_orbit(o):
        return canonical_rotation(sig_perm(o))

    roots = inst["roots"]
    assert {sig_orbit(o) for o in roots} == roots, "sigma does not fix roots"
    # loops map: orbit-set -> loop id (assert unique)
    byset = {}
    for i in range(len(loops)):
        key = frozenset(orbitsets[i])
        assert key not in byset, "loop not determined by orbit set"
        byset[key] = i
    def sig_loop(i):
        return byset[frozenset(sig_orbit(o) for o in orbitsets[i])]
    # kernel check: loop i -> loop K-1-i with ridden sets exchanged
    K = len(sol)
    for i, (Li, k, j, sk, s, t, c) in enumerate(sol):
        Lj = sol[K - 1 - i][0]
        assert sig_loop(li[loops[Li]] if False else Li) == Lj, \
            f"kernel not sigma-symmetric at {i}"
        r1 = {sig_orbit(o) for o in ridden_orbits_of(Li, k, j, sk)}
        (Lj_, kj, jj, skj, *_ ) = sol[K - 1 - i]
        assert r1 == ridden_orbits_of(Lj_, kj, jj, skj), \
            f"ridden mismatch at {i}"
    # row map
    rows = inst["rows"]
    idx = {}
    for i, r in enumerate(rows):
        idx[(r["loop"], r["parent_orbit"])] = i
    smap = []
    for r in rows:
        X = li[r["loop"]]
        img = idx.get((loops[sig_loop(X)], sig_orbit(r["parent_orbit"])))
        smap.append(img)  # may be None if image ineligible (shouldn't happen)
    return sig_orbit, smap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chains")
    ap.add_argument("index", type=int)
    ap.add_argument("--time-limit", type=float, default=100000.0)
    ap.add_argument("--iters", type=int, default=100000)
    args = ap.parse_args()

    with open(args.chains) as fh:
        rec = json.loads([l for l in fh][args.index])
    sol = [tuple(x) for x in rec["chain"]]
    inst = build_instance_from_chain(sol)
    m = inst["meta"]
    rows = inst["rows"]
    tag = f"sym:{args.chains}:{args.index}"
    print(f"[{tag}] K={m['K']} Sigma={m['Sigma']} R={m['R']} "
          f"cols={len(inst['columns'])} rows={len(rows)}", flush=True)

    sig_orbit, smap = build_sigma(sol, inst)
    none_img = sum(1 for x in smap if x is None)
    print(f"[{tag}] sigma OK; rows without image: {none_img}", flush=True)

    # variable classes {r, sigma(r)}; rows with no image are excluded
    cls = {}
    nvar = 0
    nforb = 0
    for i, img in enumerate(smap):
        if i in cls:
            continue
        if img is None:
            cls[i] = 0  # forbidden
            nforb += 1
            continue
        if img != i:
            r, q = rows[i], rows[img]
            if r["loop"] == q["loop"] or \
               set(r["children"]) & set(q["children"]):
                cls[i] = 0
                cls[img] = 0
                nforb += 2
                continue
        nvar += 1
        cls[i] = nvar
        cls[img] = nvar
    print(f"[{tag}] {nvar} symmetric row classes ({nforb} rows forbidden)",
          flush=True)

    by_col = defaultdict(set)
    for i, r in enumerate(rows):
        v = cls[i]
        if v:
            by_col[r["children"][0]].add(v)
            for c in r["children"][1:]:
                by_col[c].add(v)
    by_loop = defaultdict(set)
    for i, r in enumerate(rows):
        if cls[i]:
            by_loop[r["loop"]].add(cls[i])

    solver = Cadical195()
    ncl = 0
    for c, lits in by_col.items():
        lits = sorted(lits)
        solver.add_clause(lits)
        ncl += 1
        for a in range(len(lits)):
            for b in range(a + 1, len(lits)):
                solver.add_clause([-lits[a], -lits[b]])
                ncl += 1
    for lp, lits in by_loop.items():
        lits = sorted(lits)
        if len(lits) > 1:
            for a in range(len(lits)):
                for b in range(a + 1, len(lits)):
                    solver.add_clause([-lits[a], -lits[b]])
                    ncl += 1
    print(f"[{tag}] clauses: {ncl}", flush=True)

    var_rows = defaultdict(list)
    for i, v in cls.items():
        if v:
            var_rows[v].append(i)

    t0 = time.time()
    for it in range(args.iters):
        if time.time() - t0 > args.time_limit:
            print(f"[{tag}] time limit", flush=True)
            return 1
        sat = solver.solve()
        if not sat:
            print(f"[{tag}] UNSAT after {it} cuts -> no SYMMETRIC cover "
                  f"(asymmetric may still exist)", flush=True)
            return 2
        model = set(l for l in solver.get_model() if l > 0)
        ids = sorted({i for v in model if v in var_rows for i in var_rows[v]})
        chosen = [rows[i] for i in ids]
        rep = gain1.check_cover(inst, chosen)
        print(f"[{tag}] iter {it}: SAT {len(ids)} rows "
              f"exact={rep['exact_cover']} distinct={rep['distinct_loops']} "
              f"cycles={[len(x) for x in rep['rootless_cycles']]} "
              f"rooted={rep['rooted']} ({time.time()-t0:.1f}s)", flush=True)
        if not (rep["exact_cover"] and rep["distinct_loops"]):
            # duplicate coverage from identified pairs sharing a column:
            # ban this model
            solver.add_clause([-v for v in sorted(model) if v <= nvar])
            continue
        if rep["valid"]:
            try:
                word, cert, costs = compile_chain_cover(inst, chosen)
            except Exception as exc:
                print(f"[{tag}] compile FAILED: {exc!r}; banning model",
                      flush=True)
                solver.add_clause([-v for v in sorted(model) if v <= nvar])
                continue
            L = len(word)
            assert gain1.verify_word(word, 7)
            base = f"candidate_{L}_sym_{args.index}"
            with open(base + ".txt", "w") as fh:
                fh.write(word)
            with open(base + ".cert.json", "w") as fh:
                json.dump(cert, fh)
            with open(base + ".cover.json", "w") as fh:
                json.dump({"chain": sol, "meta": m,
                           "entries": [r["entry"] for r in chosen]}, fh)
            print(f"[{tag}] SUCCESS length={L} -> {base}.txt "
                  f"costs={dict(sorted(Counter(costs).items()))}", flush=True)
            return 0
        loop_to_var = {rows[i]["loop"]: cls[i] for i in ids}
        for cyc in rep["rootless_cycles"]:
            solver.add_clause([-loop_to_var[lp] for lp in cyc])
    return 1


if __name__ == "__main__":
    sys.exit(main())
