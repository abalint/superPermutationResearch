#!/usr/bin/env python3
"""Chain-cover search as binary MILP (HiGHS) with lazy rootless-cycle cuts.

usage: python3 milp_chain.py <chains.jsonl> <index> [--seed-cert cert.json]
         [--rng N] [--iters N] [--time-per-iter S]
exit: 0 = validated word written; 1 = infeasible/stalled/limit.
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, vstack

import gain1
import chain7
from chain7 import build_instance_from_chain, compile_chain_cover
from certificate import parse_loop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chains")
    ap.add_argument("index", type=int)
    ap.add_argument("--seed-cert", default="cert5907_5907-504778e6.json")
    ap.add_argument("--no-seed", action="store_true")
    ap.add_argument("--feas", action="store_true")
    ap.add_argument("--rng", type=int, default=0)
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--time-per-iter", type=float, default=120.0)
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

    seed = set()
    if not args.no_seed:
        cert = json.load(open(args.seed_cert))
        rid_of = {(r["loop"], r["entry"]): i for i, r in enumerate(rows)}
        for r in cert["rows"]:
            rid = rid_of.get((parse_loop(r["loop"], 7), r["entry_perm"]))
            if rid is not None:
                seed.add(rid)
        print(f"[{tag}] seed rows still eligible: {len(seed)}", flush=True)

    col_index = {c: i for i, c in enumerate(inst["columns"])}
    rr, cc = [], []
    for i, r in enumerate(rows):
        for ch in r["children"]:
            rr.append(col_index[ch])
            cc.append(i)
    nrows = len(rows)
    Aeq = coo_matrix((np.ones(len(rr)), (rr, cc)),
                     shape=(len(col_index), nrows)).tocsr()
    # distinct-loops: at most one row per loop
    by_loop = defaultdict(list)
    for i, r in enumerate(rows):
        by_loop[r["loop"]].append(i)
    lr, lc = [], []
    loops_multi = [ids for ids in by_loop.values() if len(ids) > 1]
    for j, ids in enumerate(loops_multi):
        for i in ids:
            lr.append(j)
            lc.append(i)
    Aloop = coo_matrix((np.ones(len(lr)), (lr, lc)),
                       shape=(len(loops_multi), nrows)).tocsr()

    rng = np.random.default_rng(args.rng)
    if args.feas:
        # pure feasibility: zero objective => HiGHS stops at first incumbent
        cost = np.zeros(nrows)
    else:
        cost = np.where(np.isin(np.arange(nrows), list(seed)), -1000.0, 0.0) \
            - rng.random(nrows) * 1e-3

    cuts = []
    integrality = np.ones(nrows)
    bounds = Bounds(np.zeros(nrows), np.ones(nrows))

    for it in range(args.iters):
        t0 = time.time()
        mats = [Aeq, Aloop]
        lbs = [np.ones(Aeq.shape[0]), np.full(Aloop.shape[0], -np.inf)]
        ubs = [np.ones(Aeq.shape[0]), np.ones(Aloop.shape[0])]
        if cuts:
            cr, ccc, cub = [], [], []
            for j, cut in enumerate(cuts):
                for i in cut:
                    cr.append(j)
                    ccc.append(i)
                cub.append(len(cut) - 1)
            Ac = coo_matrix((np.ones(len(cr)), (cr, ccc)),
                            shape=(len(cuts), nrows)).tocsr()
            mats.append(Ac)
            lbs.append(np.full(len(cuts), -np.inf))
            ubs.append(np.array(cub, dtype=float))
        A = vstack(mats, format="csr")
        lb = np.concatenate(lbs)
        ub = np.concatenate(ubs)
        res = milp(cost, integrality=integrality, bounds=bounds,
                   constraints=LinearConstraint(A, lb, ub),
                   options={"time_limit": args.time_per_iter,
                            "mip_rel_gap": 0})
        if res.x is None:
            print(f"[{tag}] iter {it}: MILP infeasible/timeout "
                  f"(status {res.status}: {res.message})", flush=True)
            return 1
        ids = [i for i, v in enumerate(res.x) if v > 0.5]
        chosen = [rows[i] for i in ids]
        rep = gain1.check_cover(inst, chosen)
        print(f"[{tag}] iter {it}: {len(ids)} rows "
              f"({len(set(ids) & seed)} seed), exact={rep['exact_cover']} "
              f"distinct={rep['distinct_loops']} "
              f"cycles={[len(x) for x in rep['rootless_cycles']]} "
              f"rooted={rep['rooted']} ({time.time() - t0:.1f}s)", flush=True)
        if rep["valid"]:
            try:
                word, cert_out, costs = compile_chain_cover(inst, chosen)
            except Exception as exc:
                print(f"[{tag}] compile FAILED: {exc!r}; cutting this cover",
                      flush=True)
                cuts.append(frozenset(ids))
                continue
            L = len(word)
            assert gain1.verify_word(word, 7)
            base = f"candidate_{L}_milp_{args.chains.replace('.jsonl','')}_{args.index}"
            with open(base + ".txt", "w") as fh:
                fh.write(word)
            with open(base + ".cert.json", "w") as fh:
                json.dump(cert_out, fh)
            with open(base + ".cover.json", "w") as fh:
                json.dump({"chain": sol, "meta": m,
                           "entries": [rows[i]["entry"] for i in ids]}, fh)
            hist = Counter(costs)
            print(f"[{tag}] SUCCESS length={L} -> {base}.txt "
                  f"costs={dict(sorted(hist.items()))}", flush=True)
            return 0
        loop_to_id = {rows[i]["loop"]: i for i in ids}
        new = 0
        for cyc in rep["rootless_cycles"]:
            cut = frozenset(loop_to_id[lp] for lp in cyc)
            if cut not in cuts:
                cuts.append(cut)
                new += 1
        if not new:
            print(f"[{tag}] no new cuts -- stalled", flush=True)
            return 1
    print(f"[{tag}] iteration limit", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
