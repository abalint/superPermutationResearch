#!/usr/bin/env python3
"""Chain cover via kissat (DIMACS shell-out) with lazy rootless-cycle cuts.

usage: python3 kissat_chain.py <chains.jsonl> <index> [--time-limit S] [--seed N]
exit: 0 validated word; 2 UNSAT (no exact cover / no rooted cover given cuts);
1 undecided.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict

import gain1
import chain7
from chain7 import build_instance_from_chain, compile_chain_cover

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chains")
    ap.add_argument("index", type=int)
    ap.add_argument("--time-limit", type=float, default=900)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    with open(args.chains) as fh:
        rec = json.loads([l for l in fh][args.index])
    sol = [tuple(x) for x in rec["chain"]]
    inst = build_instance_from_chain(sol)
    m = inst["meta"]
    rows = inst["rows"]
    tag = f"kissat:{os.path.basename(args.chains)}:{args.index}"
    print(f"[{tag}] K={m['K']} Sigma={m['Sigma']} R={m['R']} "
          f"cols={len(inst['columns'])} rows={len(rows)}", flush=True)

    clauses = []
    by_col = defaultdict(list)
    for i, r in enumerate(rows):
        for c in r["children"]:
            by_col[c].append(i + 1)
    for c, lits in by_col.items():
        clauses.append(lits)
        for a in range(len(lits)):
            for b in range(a + 1, len(lits)):
                clauses.append([-lits[a], -lits[b]])
    by_loop = defaultdict(list)
    for i, r in enumerate(rows):
        by_loop[r["loop"]].append(i + 1)
    for lp, lits in by_loop.items():
        for a in range(len(lits)):
            for b in range(a + 1, len(lits)):
                clauses.append([-lits[a], -lits[b]])

    cuts = []
    t_start = time.time()
    it = 0
    while True:
        remain = args.time_limit - (time.time() - t_start)
        if remain <= 5:
            print(f"[{tag}] time limit -> UNDECIDED ({it} cuts)", flush=True)
            return 1
        cnf = os.path.join(HERE, f"tmp_{os.getpid()}.cnf")
        with open(cnf, "w") as fh:
            fh.write(f"p cnf {len(rows)} {len(clauses) + len(cuts)}\n")
            for cl in clauses:
                fh.write(" ".join(map(str, cl)) + " 0\n")
            for cut in cuts:
                fh.write(" ".join(str(-v) for v in cut) + " 0\n")
        try:
            proc = subprocess.run(
                ["kissat", f"--time={int(remain)}", "-q",
                 f"--seed={args.seed}", cnf],
                capture_output=True, text=True)
        finally:
            os.unlink(cnf)
        out = proc.stdout
        it += 1
        if "s UNSATISFIABLE" in out:
            print(f"[{tag}] UNSAT after {len(cuts)} cuts "
                  f"({time.time()-t_start:.0f}s)", flush=True)
            return 2
        if "s SATISFIABLE" not in out:
            print(f"[{tag}] time limit mid-solve -> UNDECIDED "
                  f"({len(cuts)} cuts)", flush=True)
            return 1
        model = set()
        for line in out.splitlines():
            if line.startswith("v "):
                for x in line[2:].split():
                    v = int(x)
                    if v > 0:
                        model.add(v)
        ids = sorted(v - 1 for v in model if 1 <= v <= len(rows))
        chosen = [rows[i] for i in ids]
        rep = gain1.check_cover(inst, chosen)
        print(f"[{tag}] iter {it}: SAT {len(ids)} rows "
              f"cycles={[len(x) for x in rep['rootless_cycles']]} "
              f"rooted={rep['rooted']} ({time.time()-t_start:.0f}s)",
              flush=True)
        assert rep["exact_cover"] and rep["distinct_loops"]
        if rep["valid"]:
            try:
                word, cert, costs = compile_chain_cover(inst, chosen)
            except Exception as exc:
                print(f"[{tag}] compile FAILED: {exc!r}; banning model",
                      flush=True)
                cuts.append([i + 1 for i in ids])
                continue
            L = len(word)
            assert gain1.verify_word(word, 7)
            base = (f"candidate_{L}_kissat_"
                    f"{os.path.basename(args.chains).replace('.jsonl','')}"
                    f"_{args.index}")
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
        loop_to_var = {rows[i]["loop"]: i + 1 for i in ids}
        for cyc in rep["rootless_cycles"]:
            cuts.append([loop_to_var[lp] for lp in cyc])


if __name__ == "__main__":
    sys.exit(main())
