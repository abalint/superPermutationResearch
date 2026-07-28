#!/usr/bin/env python3
"""Merge all n=7 census verdict sources into one canonical CSV.

Sources, in precedence order for the `verdict` column:
  1. STRUCTURAL — the chain's exact-cover instance (chain7.build_instance_from_chain,
     the canonical formulation used by every ledger/census claim in this repo) has a
     zero-candidate column: no cover exists, unconditionally. Recomputed here, not read
     from disk.
  2. UNSAT — CaDiCaL pass-1 (analysis/cover7/results_n7_pass1.csv) and/or the local
     dlx7g sweep (analysis/trackc/runs/census/results.csv). Both engines recorded.
  3. OPEN — no source refutes it (includes per-engine timeouts).

Any SAT anywhere would be a world-record candidate and is surfaced loudly, never merged
silently. Output: analysis/cover7/results_n7_merged.csv with per-source columns.

Run from analysis/trackc/:  PYTHONPATH=../cover7:../../../extraDocs/superpermutation-examples/scripts python3 census_merge.py
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cover7"))
import chain7  # noqa: E402

FARM = os.path.join(HERE, "..", "farm", "farm_chains.jsonl")
CAD = os.path.join(HERE, "..", "cover7", "results_n7_pass1.csv")
DLX = os.path.join(HERE, "runs", "census", "results.csv")
OUT = os.path.join(HERE, "..", "cover7", "results_n7_merged.csv")


def main():
    chains = [json.loads(l) for l in open(FARM)]

    cad = {}
    for r in csv.DictReader(open(CAD)):
        cad[int(r["index"])] = r["outcome"]

    dlx = {}
    if os.path.exists(DLX):
        for r in csv.DictReader(open(DLX)):
            if not (r["index"] or "").isdigit():  # trailing SWEEP COMPLETE marker
                continue
            dlx[int(r["index"])] = r["verdict"]

    sat_alerts = []
    rows = []
    n_struct = n_unsat = n_open = 0
    for idx, rec in enumerate(chains):
        inst = chain7.build_instance_from_chain([tuple(t) for t in rec["chain"]])
        cnt = {c: 0 for c in inst["columns"]}
        for row in inst["rows"]:
            for ch in row["children"]:
                if ch in cnt:
                    cnt[ch] += 1
        structural = sum(1 for v in cnt.values() if v == 0)

        c, d = cad.get(idx, ""), dlx.get(idx, "")
        for src, v in (("cadical", c), ("dlx", d)):
            if "SAT" in v.upper() and "UNSAT" not in v.upper():
                sat_alerts.append((idx, src, v))

        if structural:
            verdict, n_struct = "STRUCTURAL", n_struct + 1
        elif "UNSAT" in c.upper() or d == "UNSAT":
            verdict, n_unsat = "UNSAT", n_unsat + 1
        else:
            verdict, n_open = "OPEN", n_open + 1
        rows.append([idx, rec["pattern"], rec["K"], rec["Sigma"], verdict,
                     structural, c, d])

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "pattern", "K", "Sigma", "verdict",
                    "zero_candidate_columns", "cadical_pass1", "dlx_sweep"])
        w.writerows(rows)

    closed = n_struct + n_unsat
    print(f"{OUT}: {len(rows)} chains — STRUCTURAL {n_struct}, UNSAT {n_unsat}, "
          f"OPEN {n_open} (closed {closed}/{len(rows)})")
    if sat_alerts:
        print("!!! SAT CANDIDATES (validate before believing):", sat_alerts)


if __name__ == "__main__":
    main()
