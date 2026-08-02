#!/usr/bin/env python3
"""Soundness/recall oracle for paircuts.py's pair-forcing reduction.

The one property that matters: a pair that DOES occur together in some real
cover must never come back UNSAT.  Getting that wrong silently poisons a store
of "sound" cuts every later run will trust.  So it is checked against known
covers, where the true answer is on disk.

Most of it needs NO SOLVER, which is what makes it decisive rather than
budget-dependent.  Forcing rows i and j here means: hold the column set fixed
and delete exactly the rows conflicting with i or j (same 2-loop, or sharing a
child column).  So:

  T1 RECALL, exact.  For every pair (i, j) drawn from a control's own known
     cover C, every row of C must survive into the reduced instance.  If
     C survives, C is still an exact cover of it, so SAT is preserved -- a
     complete proof of recall for that cover, with no search involved.  (An
     earlier draft of this oracle demanded the SOLVER return SAT at the 2000-
     node cap and scored 60 honest UNKNOWNs as soundness bugs.  UNKNOWN is a
     budget statement, not a refutation; only UNSAT would be the bug.)

  T2 FORCING, exact.  In the reduced instance each of i's and j's child columns
     must be covered by that row ALONE.  That is what makes "delete the
     conflicting rows" equivalent to "assert both rows": every exact cover of
     the reduction contains i and j.

  T3 NO FALSE REFUTATION, with solver.  No pair drawn from a known cover may
     come back UNSAT at the sweep's own cap.  This is T1 again, end to end
     through the real code path, and it is the test that would actually fire if
     the rendering (column ids, loop ids, parent codes) were subtly wrong.

  T4 POSITIVE CONTROL, with solver.  On a PRUNED control pool -- the same shape
     as the real target, where s57's gate panel solves in <= 0.02 s -- forcing a
     true pair must return SAT, a valid cover (gain1.check_cover), and contain
     both rows.  This proves the reduction can still be SOLVED, not merely that
     it is not refuted.

  T5 REFINEMENT.  propose.py forces by deleting child columns, which re-roots
     dependants and RELAXES the ordering constraint; ours decides the exact
     question.  So relaxation-UNSAT must imply ours-UNSAT, never the reverse.

usage: paircuts_oracle.py [--words K] [--pairs K] [--cap N] [--seed S]
"""
from __future__ import annotations

import argparse
import os
import pickle
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (HERE,
          os.path.join(REPO, "out", "s57", "proposer"),
          os.path.join(REPO, "out", "s56", "p1a"),
          os.path.join(REPO, "analysis", "cover7"),
          os.path.join(REPO, "..", "extraDocs",
                       "superpermutation-examples", "scripts")):
    if os.path.isdir(p):
        sys.path.insert(0, os.path.abspath(p))

import gain1  # noqa: E402
import p1a_assume as P  # noqa: E402
import propose as PR  # noqa: E402
import paircuts as PC  # noqa: E402

DLX = os.path.join(REPO, "analysis", "trackc", "dlx7g")
TMP = os.path.join(REPO, "out", "s58", "oracle")


def base_from_inst(inst, rows_all):
    """paircuts.build_base's fixed-column structures for an arbitrary instance
    + row pool (the oracle needs control chains, not in farm_chains.jsonl)."""
    rows = inst["rows"]
    cols = list(inst["columns"])
    ci = {c: k for k, c in enumerate(cols)}
    roots = set(inst["roots"])
    loop_id = {}
    for r in rows_all:
        loop_id.setdefault(rows[r]["loop"], len(loop_id))
    line = {}
    for r in rows_all:
        rr = rows[r]
        po = rr["parent_orbit"]
        pc = -1 if (po in roots or po not in ci) else ci[po]
        line[r] = (f"{loop_id[rr['loop']]} {pc} "
                   + " ".join(str(ci[c]) for c in rr["children"]))
    nchild = len(rows[rows_all[0]]["children"])
    by_col, by_loop = {}, {}
    for r in rows_all:
        for c in rows[r]["children"]:
            by_col.setdefault(c, []).append(r)
        by_loop.setdefault(rows[r]["loop"], []).append(r)
    kill = {r: set() for r in rows_all}
    for grp in list(by_col.values()) + list(by_loop.values()):
        for r in grp:
            kill[r].update(grp)
    for r in rows_all:
        kill[r].discard(r)
    return dict(inst=inst, rows_all=rows_all, line=line, kill=kill,
                header=f"{len(cols)} %d {len(loop_id)} {nchild}")


def run(B, lo, hi, cap, tl, tag="o"):
    txt, keep = PC.render_pair(B, lo, hi)
    v, dt, ids, nodes, err = PC.probe(
        DLX, txt, os.path.join(TMP, f"_{tag}_inst.txt"),
        os.path.join(TMP, f"_{tag}_sol.txt"), cap, tl)
    return v, dt, [keep[x] for x in ids], keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", type=int, default=4)
    ap.add_argument("--pairs", type=int, default=25)
    ap.add_argument("--cap", type=int, default=2000)
    ap.add_argument("--tl", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--t5", type=int, default=40)
    ap.add_argument("--prefix", type=int, default=30,
                    help="T4: true walk-order rows fixed before the pair")
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    os.makedirs(TMP, exist_ok=True)

    data = pickle.load(open(os.path.join(REPO, "out", "s57", "proposer",
                                         "controls.pkl"), "rb"))
    paths = sorted({d["path"] for d in data})
    rnd.shuffle(paths)
    paths = paths[:a.words]

    fails = 0
    t1_pairs = t2_pairs = t3_n = t3_unsat = t4_n = t4_ok = 0

    for wp in paths:
        ex = P.extract(wp)
        inst, known = ex["inst"], ex["known_rows"]
        B = base_from_inst(inst, list(range(len(inst["rows"]))))
        rows = inst["rows"]
        name = os.path.basename(wp)
        print(f"\n== {name}: {len(rows)} rows, {len(inst['columns'])} cols, "
              f"cover = {len(known)} rows")

        # ---- T1 recall: every row of C survives every pair drawn from C -----
        allpairs = [(min(i, j), max(i, j))
                    for x, i in enumerate(known) for j in known[x + 1:]]
        Cset = set(known)
        lost = [(i, j) for (i, j) in allpairs if (B["kill"][i] | B["kill"][j]) & Cset]
        t1_pairs += len(allpairs)
        if lost:
            fails += 1
            print(f"  T1 FAIL: {len(lost)} of {len(allpairs)} true pairs "
                  f"delete a row of their own cover, e.g. {lost[:3]}")
        else:
            print(f"  T1 ok  : all {len(allpairs)} true pairs keep all "
                  f"{len(known)} cover rows -> SAT provably preserved")

        # ---- T2 forcing: i and j uniquely cover their own columns -----------
        t2bad = 0
        for (i, j) in allpairs[:200]:
            dead = B["kill"][i] | B["kill"][j]
            keep = [r for r in B["rows_all"] if r not in dead]
            for r in (i, j):
                for c in rows[r]["children"]:
                    if any(c in rows[q]["children"] for q in keep if q != r):
                        t2bad += 1
                        break
        t2_pairs += min(len(allpairs), 200)
        if t2bad:
            fails += 1
            print(f"  T2 FAIL: {t2bad} pairs where a forced row's column is "
                  f"also covered by a survivor -- forcing is NOT implied")
        else:
            print(f"  T2 ok  : {min(len(allpairs), 200)} pairs, every forced "
                  f"row uniquely covers its 5 columns")

        # ---- T3 no false refutation through the real code path --------------
        rnd.shuffle(allpairs)
        bad3 = []
        for (lo, hi) in allpairs[:a.pairs]:
            v, dt, full, keep = run(B, lo, hi, a.cap, a.tl)
            t3_n += 1
            if v == "UNSAT":
                t3_unsat += 1
                bad3.append((lo, hi))
        if bad3:
            fails += 1
            print(f"  T3 FAIL: {len(bad3)} true pairs REFUTED -- soundness "
                  f"bug, e.g. {bad3[:3]}")
        else:
            print(f"  T3 ok  : {min(len(allpairs), a.pairs)} true pairs "
                  f"probed at cap={a.cap}, 0 refuted")

    # ---- T4 positive control: SOLVE a forced instance, not merely fail to
    # refute it.  A 2-row-forced control pool is not solvable at epsilon=0 in
    # seconds (s57 §7: the full pool is UNKNOWN; ~30 walk-order rows are what
    # buy decidability, SAT in 1.18 s).  So the control forces a true
    # walk-order PREFIX plus the pair -- which is the honest positive test:
    # given a solvable instance, does pair-forcing preserve the solution?
    print(f"\n== T4 positive control: {a.prefix}-row true prefix + a true pair")
    wp = paths[0]
    ex = P.extract(wp)
    inst, known = ex["inst"], ex["known_rows"]
    Bp = base_from_inst(inst, list(range(len(inst["rows"]))))
    pre = list(known[:a.prefix])
    rest = [r for r in known[a.prefix:]]
    print(f"  {os.path.basename(wp)}: prefix {len(pre)} rows, "
          f"{len(rest)} cover rows left to find")
    tp = [(min(i, j), max(i, j))
          for x, i in enumerate(rest) for j in rest[x + 1:]]
    rnd.shuffle(tp)
    for (lo, hi) in tp[:a.pairs]:
        txt, keep = PC.render_forced(Bp, pre + [lo, hi])
        v, dt, ids, nodes, err = PC.probe(
            DLX, txt, os.path.join(TMP, "_p_inst.txt"),
            os.path.join(TMP, "_p_sol.txt"), 0, a.tl)
        full = [keep[x] for x in ids]
        t4_n += 1
        if v != "SAT":
            fails += 1
            print(f"  T4 FAIL: prefix + true pair ({lo},{hi}) -> {v} "
                  f"({dt:.2f}s, {len(keep)} rows)")
            continue
        rep = gain1.check_cover(inst, [inst["rows"][r] for r in full])
        missing = [r for r in pre + [lo, hi] if r not in full]
        if not rep["valid"] or missing:
            fails += 1
            print(f"  T4 FAIL: ({lo},{hi}) SAT but valid={rep['valid']} "
                  f"missing_forced={missing[:5]}")
            continue
        t4_ok += 1
    print(f"  T4 ok  : {t4_ok}/{t4_n} (prefix + true pair) -> SAT + valid "
          f"cover + every forced row present")

    # ---- T5 refinement vs the s57 relaxation, on the real target ------------
    print(f"\n== T5 refinement check on the pruned chain #0 base")
    B0 = PC.build_base("farm0")
    rows0 = B0["rows_all"]
    alive0 = set(rows0) - set(B0["fixed"])
    rel_unsat = mine_unsat = disagree = 0
    for i in rnd.sample(rows0, min(a.t5, len(rows0))):
        j = rnd.choice([r for r in rows0 if r != i and r not in B0["kill"][i]])
        lo, hi = min(i, j), max(i, j)
        txt_r, rmap, nc, nr = PR.render(B0["inst"], alive0 - {lo, hi},
                                        list(B0["fixed"]) + [lo, hi])
        vr, _, _, _, _ = PC.probe(DLX, txt_r, os.path.join(TMP, "_r_inst.txt"),
                                  os.path.join(TMP, "_r_sol.txt"), a.cap, a.tl)
        vm, _, _, _ = run(B0, lo, hi, a.cap, a.tl, tag="m")
        rel_unsat += (vr == "UNSAT")
        mine_unsat += (vm == "UNSAT")
        if vr == "UNSAT" and vm != "UNSAT":
            disagree += 1
            fails += 1
            print(f"  T5 FAIL: ({lo},{hi}) relaxation UNSAT but ours {vm}")
    print(f"  T5 ok  : {min(a.t5, len(rows0))} random compatible pairs; "
          f"relaxation refuted {rel_unsat}, ours refuted {mine_unsat}, "
          f"violations {disagree}")

    print(f"\nT1 {t1_pairs} true pairs recall-checked | T2 {t2_pairs} "
          f"forcing-checked | T3 {t3_n} probed, {t3_unsat} refuted | "
          f"T4 {t4_ok}/{t4_n} solved")
    print("ORACLE PASS -- 0 failures" if fails == 0
          else f"ORACLE FAIL -- {fails} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
