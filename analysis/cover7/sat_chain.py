#!/usr/bin/env python3
"""Chain cover search via CDCL SAT (CaDiCaL) with lazy rootless-cycle cuts.

usage: satenv/bin/python sat_chain.py <chains.jsonl> <index> [--iters N]
         [--no-forest]
exit: 0 validated word; 2 UNSAT (refuted); 1 stalled/limit.
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict

from pysat.solvers import Cadical195

import gain1
import chain7
from chain7 import build_instance_from_chain, compile_chain_cover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chains")
    ap.add_argument("index", type=int)
    ap.add_argument("--iters", type=int, default=100000)
    ap.add_argument("--no-forest", action="store_true")
    ap.add_argument("--time-limit", type=float, default=100000.0)
    ap.add_argument("--phase-cert", default=None,
                    help="bias CDCL phases toward this certificate's rows")
    args = ap.parse_args()

    with open(args.chains) as fh:
        rec = json.loads([l for l in fh][args.index])
    sol = [tuple(x) for x in rec["chain"]]
    inst = build_instance_from_chain(sol)
    m = inst["meta"]
    rows = inst["rows"]
    tag = f"{args.chains}:{args.index}"
    print(f"[{tag}] K={m['K']} Sigma={m['Sigma']} V={m['V']} R={m['R']} "
          f"cols={len(inst['columns'])} rows={len(rows)}", flush=True)

    by_col = defaultdict(list)
    for i, r in enumerate(rows):
        for c in r["children"]:
            by_col[c].append(i + 1)  # SAT vars 1-based
    by_loop = defaultdict(list)
    for i, r in enumerate(rows):
        by_loop[r["loop"]].append(i + 1)

    solver = Cadical195()
    ncl = 0
    for c, lits in by_col.items():
        solver.add_clause(lits)
        ncl += 1
        for a in range(len(lits)):
            for b in range(a + 1, len(lits)):
                solver.add_clause([-lits[a], -lits[b]])
                ncl += 1
    for lp, lits in by_loop.items():
        if len(lits) > 1:
            for a in range(len(lits)):
                for b in range(a + 1, len(lits)):
                    solver.add_clause([-lits[a], -lits[b]])
                    ncl += 1
    print(f"[{tag}] clauses: {ncl}", flush=True)

    if args.phase_cert:
        from certificate import parse_loop
        cert = json.load(open(args.phase_cert))
        rid_of = {(r["loop"], r["entry"]): i for i, r in enumerate(rows)}
        pos = set()
        for r in cert["rows"]:
            rid = rid_of.get((parse_loop(r["loop"], 7), r["entry_perm"]))
            if rid is not None:
                pos.add(rid + 1)
        phases = [v if v in pos else -v for v in range(1, len(rows) + 1)]
        solver.set_phases(phases)
        print(f"[{tag}] phase bias: {len(pos)} seed rows", flush=True)

    t_start = time.time()
    for it in range(args.iters):
        if time.time() - t_start > args.time_limit:
            print(f"[{tag}] time limit", flush=True)
            return 1
        t0 = time.time()
        sat = solver.solve()
        dt = time.time() - t0
        if not sat:
            print(f"[{tag}] UNSAT after {it} cuts ({dt:.1f}s) -> "
                  f"{'no rooted cover' if not args.no_forest else 'no exact cover'}"
                  f" exists (given accumulated cuts sound)", flush=True)
            return 2
        model = set(l for l in solver.get_model() if l > 0)
        ids = [v - 1 for v in sorted(model) if v <= len(rows)]
        chosen = [rows[i] for i in ids]
        rep = gain1.check_cover(inst, chosen)
        cyc_lens = [len(x) for x in rep["rootless_cycles"]]
        print(f"[{tag}] iter {it}: SAT {len(ids)} rows ({dt:.1f}s) "
              f"exact={rep['exact_cover']} cycles={cyc_lens} "
              f"rooted={rep['rooted']}", flush=True)
        assert rep["exact_cover"] and rep["distinct_loops"]
        if args.no_forest:
            print(f"[{tag}] exact cover EXISTS (forest unchecked)", flush=True)
            return 0
        if rep["valid"]:
            try:
                word, cert, costs = compile_chain_cover(inst, chosen)
            except Exception as exc:
                print(f"[{tag}] compile FAILED: {exc!r}; blocking this cover",
                      flush=True)
                solver.add_clause([-(i + 1) for i in ids])
                continue
            L = len(word)
            assert gain1.verify_word(word, 7)
            base = (f"candidate_{L}_sat_"
                    f"{args.chains.replace('.jsonl','').replace('/','_')}"
                    f"_{args.index}")
            with open(base + ".txt", "w") as fh:
                fh.write(word)
            with open(base + ".cert.json", "w") as fh:
                json.dump(cert, fh)
            with open(base + ".cover.json", "w") as fh:
                json.dump({"chain": sol, "meta": m,
                           "entries": [r["entry"] for r in chosen]}, fh)
            hist = Counter(costs)
            print(f"[{tag}] SUCCESS length={L} -> {base}.txt "
                  f"costs={dict(sorted(hist.items()))}", flush=True)
            return 0
        # lazy cuts: ban each rootless cycle's row conjunction
        loop_to_var = {rows[i]["loop"]: i + 1 for i in ids}
        for cyc in rep["rootless_cycles"]:
            solver.add_clause([-loop_to_var[lp] for lp in cyc])
    print(f"[{tag}] iteration limit", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
