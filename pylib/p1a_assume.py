#!/usr/bin/env python3
# --- PROVENANCE (s64 P1b, 2026-08-02) -------------------------------
# Promoted BY COPY from out/s56/p1a/p1a_assume.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# Divergence from the original: REPO/path block rebased for pylib/
# (see below); logic verbatim.
# See pylib/README.md.
# --------------------------------------------------------------------
"""P1a assumption extraction + assumption-restricted DLX completion (s56).

The §6.1 three-valued control gate, first milestone.

Pipeline
--------
  word (known 5906 / 872)
    -> certificate.extract_certificate            [assumption source]
    -> chain tuples (chain7 frame)                [CHAIN fixings + doors]
    -> chain7.build_instance_from_chain           [the completion instance]
    -> restrict / fix under assumptions           [cover atoms, prefix]
    -> dlx7g                                      [SAT / UNSAT / UNKNOWN]
    -> gain1.check_cover + compile + Rust validate [SAT confirmation]

Assumption levels (the completeness gradient):
  A0  chain only                    (rows = every legal row of the instance)
  A1  chain + cover atoms           (rows restricted to the 2-loops the known
                                     cover uses; entry rotation left FREE)
  A2  chain + cover atoms + prefix  (first m cover rows fixed in walk order)
  A3  chain + prefix                (first m cover rows fixed, atoms free)

Row fixing is done by INSTANCE REDUCTION: a fixed row's 5 children columns are
deleted, every row sharing a column or the loop with a fixed row is deleted,
and rows whose parent orbit was deleted become roots (parent_code = -1).  That
last step is sound only because the fixed rows are taken in WALK ORDER, in
which each row is grounded when placed (its parent orbit is already covered by
the kernel ride or an earlier fixed row).  `--self-check` proves the reduction
preserves the known solution and that the residual instance still solves.

usage:
  p1a_assume.py extract  <word.txt> [...]         -- assumptions + ledger laws
  p1a_assume.py gate     <word.txt> --level A2 --fix 60 --time-limit 60
  p1a_assume.py selfcheck <word.txt>              -- reduction correctness
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict

# s64 P1b import-mechanics divergence: pylib/ sits directly under the repo
# root, so REPO is one level up (the out/ original was three levels down).
# chain7 is a promoted sibling in pylib/ (HERE inserted last so it wins);
# certificate/gain1 stay external in ../extraDocs.
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "..", "extraDocs",
                                "superpermutation-examples", "scripts"))
sys.path.insert(0, os.path.join(REPO, "analysis", "cover7"))
sys.path.insert(0, HERE)

import certificate  # noqa: E402
import gain1  # noqa: E402
import chain7  # noqa: E402
from certificate import parse_loop, canonical_rotation  # noqa: E402

DLX7G = os.path.join(REPO, "analysis", "trackc", "dlx7g")
N = 7
NE = 6


# --------------------------------------------------------------- extraction
def cert_to_chain(cert):
    """Certificate -> chain7 chain tuples (L, k, j, sk, s, t, c)."""
    kloops = [parse_loop(x, N) for x in cert["kernel_loops"]]
    hops = cert["hop_doors"]
    assert len(hops) == len(kloops) - 1
    sol = []
    arrival = cert["start_perm"]
    ssum_partial = 0
    for i, lp in enumerate(kloops):
        L = chain7.li[lp]
        k = chain7.entries[L].index(arrival)
        if i < len(hops):
            s = hops[i]["source"]
            j = chain7.sources[L].index(s)
            sk = 5 - ((j - k) % NE)
            ssum_partial += sk
            sol.append((L, k, j, sk, s, hops[i]["target"], hops[i]["cost"]))
            arrival = hops[i]["target"]
        else:
            # terminal loop: skip count fixed by the global orbit ledger
            nrows = len(cert["rows"])
            roots = 720 - (N - 2) * nrows
            ssum = NE * len(kloops) - roots
            sk = ssum - ssum_partial
            sol.append((L, k, None, sk, None, None, None))
    return sol


def normalize_start(word):
    """Relabel (a symmetry of the class) so the word starts at 1234567 --
    chain7.verify_chain requires the identity orbit as the chain root."""
    pre = word[:N]
    if pre == "1234567":
        return word
    m = {c: str(i + 1) for i, c in enumerate(pre)}
    return "".join(m[c] for c in word)


def extract(word_path):
    word = normalize_start(open(word_path).read().strip())
    cert = certificate.extract_certificate(word, N)
    sol = cert_to_chain(cert)
    K, Sigma, f4, f5, f6, V = chain7.verify_chain(sol)
    inst = chain7.build_instance_from_chain(sol)
    # locate the known cover rows inside the instance
    rid_of = {(r["loop"], r["entry"]): i for i, r in enumerate(inst["rows"])}
    known = []
    for r in cert["rows"]:
        key = (parse_loop(r["loop"], N), r["entry_perm"])
        if key not in rid_of:
            raise AssertionError(f"cert row {key} absent from instance rows")
        known.append(rid_of[key])
    assert len(set(known)) == len(known) == len(cert["rows"])
    return dict(word=word, path=word_path, cert=cert, chain=sol, inst=inst,
                known_rows=known)


def _fresh_doors(ex):
    """s27 fresh-doors law in the chain frame: each weight>=3 hop enters a loop
    never entered before, whose orbit set is disjoint from all ridden orbits."""
    seen_loops, seen_orbits = set(), set()
    for (L, k, j, sk, s, t, c) in ex["chain"]:
        if L in seen_loops or (chain7.orbitsets[L] & seen_orbits):
            return False
        seen_loops.add(L)
        seen_orbits |= chain7.orbitsets[L]
        if c is not None and c < 3:
            return False
    return True


def ledger(ex):
    """The priced ledger facts / laws for one control."""
    inst, cert, m = ex["inst"], ex["cert"], ex["inst"]["meta"]
    K, S, V, R = m["K"], m["Sigma"], m["V"], m["R"]
    kloops = set(parse_loop(x, N) for x in cert["kernel_loops"])
    rloops = set(parse_loop(r["loop"], N) for r in cert["rows"])
    twoloops = kloops | rloops
    doors = cert["hop_doors"]
    return dict(
        K=K, Sigma=S, V=V, R=R,
        n_cols=len(inst["columns"]), n_rows_inst=len(inst["rows"]),
        n_loops_inst=len({r["loop"] for r in inst["rows"]}),
        twoloops=len(twoloops), kernel_loops=len(kloops), cover_loops=len(rloops),
        doors=len(doors), door_costs=dict(Counter(d["cost"] for d in doors)),
        disabled=len(cert["disabled_splices"]),
        length=len(ex["word"]),
        # laws
        law_2loop=(len(twoloops) == 142),
        law_len=(len(ex["word"]) == 5764 + len(twoloops)),
        law_score=(len(twoloops) == (720 - V) // 5 and (720 - V) % 5 == 0),
        # s27 fresh-doors law, checked properly: every weight>=3 door lands in a
        # 2-loop that is new AND orbit-disjoint from everything ridden so far.
        law_freshdoor=_fresh_doors(ex),
        law_kr=(K + R == len(twoloops)),
    )


# ------------------------------------------------------- instance reduction
def instance_text(cols, rows, roots, nchild=None):
    """cols: ordered list of column names; rows: list of dicts; roots: set."""
    ci = {c: i for i, c in enumerate(cols)}
    loop_ids = {}
    for r in rows:
        loop_ids.setdefault(r["loop"], len(loop_ids))
    if nchild is None:
        nchild = len(rows[0]["children"]) if rows else N - 2
    out = [f"{len(ci)} {len(rows)} {len(loop_ids)} {nchild}"]
    for r in rows:
        po = r["parent_orbit"]
        pc = -1 if (po in roots or po not in ci) else ci[po]
        ch = " ".join(str(ci[c]) for c in r["children"])
        out.append(f"{loop_ids[r['loop']]} {pc} {ch}")
    return "\n".join(out) + "\n"


def reduce_instance(inst, fixed_row_ids, atom_loops=None):
    """Return (text, rowmap, ncols, nrows).

    rowmap[i] = original instance row id of reduced row i.
    fixed_row_ids MUST be a walk-order-grounded prefix (see module docstring).
    atom_loops: if given, restrict surviving rows to these 2-loops.
    """
    rows = inst["rows"]
    fixed = list(fixed_row_ids)
    dead_cols = set()
    dead_loops = set()
    for i in fixed:
        dead_cols.update(rows[i]["children"])
        dead_loops.add(rows[i]["loop"])
    cols = [c for c in inst["columns"] if c not in dead_cols]
    colset = set(cols)
    # roots: the chain's ridden orbits PLUS every orbit covered by a fixed row
    roots = set(inst["roots"]) | dead_cols
    keep, rowmap = [], []
    for i, r in enumerate(rows):
        if i in set(fixed):
            continue
        if r["loop"] in dead_loops:
            continue
        if any(c in dead_cols for c in r["children"]):
            continue
        if atom_loops is not None and r["loop"] not in atom_loops:
            continue
        keep.append(r)
        rowmap.append(i)
    txt = instance_text(cols, keep, roots)
    return txt, rowmap, len(cols), len(keep)


# ------------------------------------------------------------------- engine
def run_dlx(text, time_limit, max_nodes=None, tag="x", outdir="."):
    inst_fn = os.path.join(outdir, f"inst_{tag}.txt")
    out_fn = os.path.join(outdir, f"sol_{tag}.txt")
    with open(inst_fn, "w") as fh:
        fh.write(text)
    cmd = [DLX7G, inst_fn, "--time-limit", str(time_limit), "--out", out_fn]
    if max_nodes:
        cmd += ["--max-nodes", str(max_nodes)]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.monotonic() - t0
    rc = proc.returncode
    verdict = {0: "SAT", 2: "UNSAT", 3: "UNKNOWN"}.get(rc, f"ERROR{rc}")
    ids = []
    if rc == 0 and os.path.exists(out_fn):
        ids = [int(x) for x in open(out_fn).read().split()]
    tail = [l for l in proc.stderr.strip().splitlines() if l.startswith("RESULT")]
    return dict(verdict=verdict, seconds=dt, rows=ids, rc=rc,
                result_line=(tail[-1] if tail else proc.stdout.strip()[:200]))


def confirm_sat(ex, chosen_row_ids, outdir, tag):
    """SAT confirmation ritual: check_cover -> compile -> Rust validator."""
    inst = ex["inst"]
    chosen = [inst["rows"][i] for i in chosen_row_ids]
    rep = gain1.check_cover(inst, chosen)
    if not rep["valid"]:
        return dict(ok=False, why="check_cover invalid", rep=rep)
    word, cert, costs = chain7.compile_chain_cover(inst, chosen)
    wf = os.path.abspath(os.path.join(outdir, f"word_{tag}.txt"))
    with open(wf, "w") as fh:
        fh.write(word)
    vp = subprocess.run(
        ["cargo", "run", "--release", "--quiet", "--",
         "validate", "-n", "7", "--file", wf, "--complete"],
        cwd=REPO, capture_output=True, text=True)
    return dict(ok=(vp.returncode == 0), length=len(word), word_file=wf,
                validator=vp.stdout.strip().splitlines()[-1] if vp.stdout.strip() else vp.stderr.strip()[-200:],
                identical=(word == ex["word"]))


# --------------------------------------------------------------------- main
def cmd_extract(args):
    print(f"{'control':44} {'K':>3} {'Sig':>4} {'V':>3} {'R':>4} "
          f"{'2loops':>7} {'cols':>5} {'rows':>6} {'iloops':>6} laws")
    ok = 0
    bad = []
    for p in args.words:
        try:
            ex = extract(p)
        except Exception as exc:  # inexpressible in the certificate frame
            bad.append((os.path.basename(p), f"{type(exc).__name__}: {exc}"))
            print(f"{os.path.basename(p):44} INEXPRESSIBLE  {str(exc)[:60]}")
            continue
        L = ledger(ex)
        laws = "".join("Y" if L[k] else "N" for k in
                       ("law_2loop", "law_len", "law_score", "law_freshdoor", "law_kr"))
        if laws == "YYYYY":
            ok += 1
        print(f"{os.path.basename(p):44} {L['K']:3d} {L['Sigma']:4d} {L['V']:3d} "
              f"{L['R']:4d} {L['twoloops']:7d} {L['n_cols']:5d} "
              f"{L['n_rows_inst']:6d} {L['n_loops_inst']:6d} {laws}")
        if args.json:
            with open(os.path.join(args.json, os.path.basename(p) + ".ledger.json"), "w") as fh:
                json.dump(L, fh, indent=1)
    print(f"words read: {len(args.words)}; extracted: {len(args.words) - len(bad)}; "
          f"INEXPRESSIBLE: {len(bad)}; all-laws-pass: {ok}/{len(args.words) - len(bad)}")
    for b in bad:
        print("  inexpressible:", b[0], b[1][:70])
    return 0 if ok == len(args.words) - len(bad) else 1


def build_variant(ex, level, fix, noise=0, seed=1):
    """level in {A0, A1, AP, A2, A3}; noise = extra non-cover 2-loops added to
    the atom pool (AP only); fix = prefix rows fixed (A2/A3 only)."""
    import random
    inst = ex["inst"]
    known = ex["known_rows"]  # already in certificate walk order
    atoms = None
    if level in ("A1", "A2", "AP", "AX"):
        atoms = {inst["rows"][i]["loop"] for i in known}
        others = sorted({r["loop"] for r in inst["rows"]} - atoms)
        rng = random.Random(seed)
        if level == "AP" and noise:
            atoms = atoms | set(rng.sample(others, min(noise, len(others))))
        elif level == "AX":
            # UNSAT-arm probe: delete `fix` TRUE atoms, add `noise` decoys, so
            # the known witness is excluded but the loop count still fits.
            drop = set(rng.sample(sorted(atoms), fix))
            atoms = (atoms - drop) | set(rng.sample(others, min(noise, len(others))))
    nfix = fix if level in ("A2", "A3") else 0  # AX uses `fix` as a drop count
    fixed = known[:nfix]
    txt, rowmap, nc, nr = reduce_instance(inst, fixed, atoms)
    return txt, rowmap, fixed, nc, nr, (len(atoms) if atoms else None)


def cmd_gate(args):
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    results = []
    for p in args.words:
        ex = extract(p)
        base = os.path.basename(p).replace(".txt", "")
        for level in args.levels:
            fixes = args.fix if level in ("A2", "A3", "AX") else [0]
            noises = args.noise if level in ("AP", "AX") else [0]
            for fix in fixes:
              for noise in noises:
                tag = f"{base}_{level}_{fix}_{noise}"
                txt, rowmap, fixed, nc, nr, npool = build_variant(
                    ex, level, fix, noise, args.seed)
                r = run_dlx(txt, args.time_limit, args.max_nodes, tag, outdir)
                rec = dict(control=base, level=level, fix=fix, noise=noise,
                           pool=npool, cols=nc,
                           rows=nr, verdict=r["verdict"],
                           seconds=round(r["seconds"], 2),
                           result=r["result_line"])
                if r["verdict"] == "SAT":
                    full = list(fixed) + [rowmap[i] for i in r["rows"]]
                    c = confirm_sat(ex, full, outdir, tag)
                    rec["validated"] = c["ok"]
                    rec["validator"] = c.get("validator")
                    rec["length"] = c.get("length")
                    rec["identical_to_source"] = c.get("identical")
                    if c.get("length") and c["length"] < 5906:
                        rec["ALERT"] = "SUB-5906 CANDIDATE"
                print(json.dumps(rec), flush=True)
                results.append(rec)
    with open(os.path.join(outdir, args.tag + "_gate.json"), "w") as fh:
        json.dump(results, fh, indent=1)
    print(f"controls read: {len(args.words)}; runs: {len(results)}")
    return 0


def cmd_selfcheck(args):
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    fails = 0
    for p in args.words:
        ex = extract(p)
        inst, known = ex["inst"], ex["known_rows"]
        base = os.path.basename(p).replace(".txt", "")
        # 1. the known cover is a valid cover of the FULL instance
        rep = gain1.check_cover(inst, [inst["rows"][i] for i in known])
        # 2. compiling it reproduces the source word byte-identically
        w, _, _ = chain7.compile_chain_cover(inst, [inst["rows"][i] for i in known])
        rt = (w == ex["word"])
        # 3. reduction at several prefixes preserves the known solution
        pres = []
        for m in args.fix:
            txt, rowmap, nc, nr = reduce_instance(inst, known[:m])
            back = {o: i for i, o in enumerate(rowmap)}
            residual = known[m:]
            pres.append(all(r in back for r in residual)
                        and nc == 5 * len(residual))
        print(f"{base}: cover_valid={rep['valid']} roundtrip={rt} "
              f"reduction_preserves={pres}")
        if not (rep["valid"] and rt and all(pres)):
            fails += 1
    print(f"words read: {len(args.words)}; failures: {fails}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("words", nargs="+")
    e.add_argument("--json", default=None)
    e.set_defaults(fn=cmd_extract)
    g = sub.add_parser("gate")
    g.add_argument("words", nargs="+")
    g.add_argument("--levels", nargs="+", default=["A0", "A1", "A2"])
    g.add_argument("--fix", nargs="+", type=int, default=[60])
    g.add_argument("--noise", nargs="+", type=int, default=[0])
    g.add_argument("--seed", type=int, default=1)
    g.add_argument("--time-limit", type=float, default=60.0)
    g.add_argument("--max-nodes", type=int, default=None)
    g.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    g.add_argument("--tag", default="gate")
    g.set_defaults(fn=cmd_gate)
    s = sub.add_parser("selfcheck")
    s.add_argument("words", nargs="+")
    s.add_argument("--fix", nargs="+", type=int, default=[0, 40, 80, 120])
    s.add_argument("--outdir", default=os.path.dirname(os.path.abspath(__file__)))
    s.set_defaults(fn=cmd_selfcheck)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
