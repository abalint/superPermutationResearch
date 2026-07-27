#!/usr/bin/env python3
"""Structural feasibility analysis of a chain instance: per-column candidate
counts and unit propagation (forced selections), before any search.

usage: python3 analyze_chain.py <chains.jsonl> <index> [--quiet]
"""
import json
import sys
from collections import defaultdict

from chain7 import build_instance_from_chain


def analyze(inst, quiet=False):
    rows = inst["rows"]
    columns = set(inst["columns"])
    by_col = defaultdict(set)
    for i, r in enumerate(rows):
        for c in r["children"]:
            by_col[c].add(i)
    # columns with no candidates at all
    zero = [c for c in columns if not by_col[c]]
    hist = defaultdict(int)
    for c in columns:
        hist[len(by_col[c])] += 1
    if not quiet:
        print(f"  column candidate-count histogram (lowest 8): "
              f"{dict(sorted(hist.items())[:8])}")
    if zero:
        print(f"  REFUTED: {len(zero)} columns with zero candidate rows, "
              f"e.g. {zero[:3]}")
        return "zero-column"
    # unit propagation
    alive = set(range(len(rows)))
    colset = {c: set(by_col[c]) for c in columns}
    open_cols = set(columns)
    chosen = []
    loop_used = set()

    def kill_row(i):
        alive.discard(i)
        for c in rows[i]["children"]:
            if c in colset:
                colset[c].discard(i)

    changed = True
    while changed:
        changed = False
        forced = [c for c in open_cols if len(colset[c]) == 1]
        for c in forced:
            if c not in open_cols:
                continue
            if not colset[c]:
                print(f"  CONTRADICTION during propagation at column {c} "
                      f"(after {len(chosen)} forced rows)")
                return "propagation-contradiction"
            i = next(iter(colset[c]))
            r = rows[i]
            chosen.append(i)
            loop_used.add(r["loop"])
            changed = True
            for ch in r["children"]:
                open_cols.discard(ch)
                for j in list(colset[ch]):
                    if j != i:
                        kill_row(j)
                del colset[ch]
            # same-loop exclusion
            for j in list(alive):
                if j != i and rows[j]["loop"] == r["loop"]:
                    kill_row(j)
            alive.discard(i)
        for c in open_cols:
            if not colset[c]:
                print(f"  CONTRADICTION: column {c} emptied after "
                      f"{len(chosen)} forced rows")
                return "propagation-contradiction"
    print(f"  propagation: {len(chosen)} forced rows, "
          f"{len(open_cols)} columns open, no contradiction")
    return "open"


if __name__ == "__main__":
    fn = sys.argv[1]
    idxs = [int(x) for x in sys.argv[2].split(",")]
    for idx in idxs:
        with open(fn) as fh:
            rec = json.loads([l for l in fh][idx])
        sol = [tuple(x) for x in rec["chain"]]
        inst = build_instance_from_chain(sol)
        m = inst["meta"]
        nloops = len({r["loop"] for r in inst["rows"]})
        print(f"[{fn}:{idx}] K={m['K']} Sigma={m['Sigma']} R={m['R']} "
              f"cols={len(inst['columns'])} rows={len(inst['rows'])} "
              f"loops={nloops}")
        if nloops < m["R"]:
            print("  INFEASIBLE by loop count")
            continue
        analyze(inst)
