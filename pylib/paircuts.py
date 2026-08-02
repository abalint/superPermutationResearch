#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from analysis/counting/s58/paircuts.py.
# This pylib/ copy is CANONICAL as of s64; the original stays in place
# for the frozen out/ scripts that import it; new/tracked code must use
# this copy.
# Divergence from the original: REPO/path block rebased for pylib/
# (see below); logic verbatim.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s58 PAIRWISE CUT STORE -- sound no-goods over row PAIRS of an open chain.

docs/SWEEP-QUEUE.md "## pairwise cut store, chain #0"; s57 REPORT.md §8.3.

WHAT IT PROVES.  s57 saturated the SINGLETON layer: force one row, refute it at
a node cap, delete it.  On chain #0 that bought 4 forced rows and -11.9% rows
(2662 -> 2346), and a second pass refuted nothing more.  The next layer is
PAIRS: for rows (i, j), assert BOTH and refute.  A refuted pair is a reusable
sound no-good -- "no cover of this chain contains both i and j" -- which any
later witness or refutation run can load as a cut.

REFUTATION LANE ONLY.  epsilon = 0, no randomized restarts.  A no-good must be
unconditional; the witness lane (--epsilon 0.15) can never produce one, because
restarts make an honest UNSAT impossible (s57 §9, s56 6.1 three-valued
contract).  The three-valued reading is unchanged:

    force i and j  ->  dlx7g with --max-nodes CAP, --epsilon 0
        exit 2 (EXHAUSTED) -> no cover contains both  -> NO-GOOD   (sound cut)
        exit 3 (TIMEOUT)   -> UNKNOWN                 -> nothing learned
        exit 0 (SOLVED)    -> a full cover of an OPEN chain exists -> 5905
                              CANDIDATE.  Alarm, stop, run the M3 ritual.

HOW A PAIR IS FORCED (this differs from propose.py, deliberately).
propose.py's `render` forces a row by DELETING its child columns, which
re-roots any row parented on one of them; that RELAXES the first-visit
ordering, so its UNSAT is sound but weaker than the real question.  Here the
column set is held FIXED and a pair is forced by deleting only the rows that
CONFLICT with i or j (same 2-loop, or sharing a child column).  Rows i and j
then remain the unique cover of their own 15 columns, so every exact cover of
the reduced instance contains both -- forcing achieved with the ordering
constraint fully intact.  Consequences:

  * soundness: unchanged.  UNSAT on this instance is UNSAT of "a cover
    containing i and j" exactly, not of a relaxation of it -- so it is sound
    AND refutes at least as many pairs as the relaxation would.
  * speed: the column index, each row's rendered line, and the loop ids are all
    invariant across the 2.7M probes, so they are computed ONCE.  Per probe the
    work is a set-difference and a join, not a re-render.

A pair that is STRUCTURALLY incompatible (shared loop or shared column) is NOT
a no-good: it is already implied by the exact-cover constraints themselves and
carries no information.  Those are counted and skipped, never stored.

SHARDING.  Work unit = one row i; the shard probes every pair (i, j), j > i.
Shards are round-robin (i % N == shard), which balances the linearly-shrinking
pair count per i across workers.  Subtrees do not interact, so the union of the
shard stores is exactly the single-process store.

usage:
  paircuts.py [--spec farm0] --shard i/N --out DIR [--cap 2000] [--tl 30]
              [--limit K] [--dry-run] [--dlx PATH]

Farm contract (analysis/farm/pysweep_run.ps1 + untargeted_super.ps1): honours
--shard/--out, appends a STATUS heartbeat line per completed row, prints a
`***`-bannered line on a jackpot, and writes *stats*.tsv / *nogood*.tsv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# s64 P1 import-mechanics divergence: pylib/ sits directly under the repo
# root, so REPO is one level up (the out/ original was three levels down).
REPO = os.path.dirname(HERE)

# The s57 proposer supplies the pruned state; chain7 rebuilds the instance.
for p in (HERE,                            # s64 P1: promoted chain7/dlxrun
          os.path.join(REPO, "out", "s57", "proposer"),
          os.path.join(REPO, "out", "s56", "p1a"),
          os.path.join(REPO, "analysis", "cover7"),
          os.path.join(REPO, "..", "extraDocs",
                       "superpermutation-examples", "scripts")):
    if os.path.isdir(p):
        sys.path.insert(0, os.path.abspath(p))

import chain7  # noqa: E402
import p1a_assume as P  # noqa: E402

PRUNE_JSON = os.path.join(REPO, "out", "s57", "proposer", "prune_all.json")
FARM = os.path.join(REPO, "analysis", "farm", "farm_chains.jsonl")
DEFAULT_DLX = os.path.join(REPO, "analysis", "trackc", "dlx7g")


# --------------------------------------------------------------- the base --
def load_spec(spec):
    """-> (inst, rows_all, fixed, covers).  Mirrors s60 cutlib.load's split.

    farm*      : s57's SOUND pruning applied (alive + fixed from prune_all.json)
    ctrlgroup* : the RAW instance, unpruned, plus its known covers -- the
                 control lane, where every produced cut can be cross-checked
                 against real solutions (s60 REPORT §4c, the headline test).
    """
    if spec.startswith("ctrlgroup"):
        import pickle
        pk = os.path.join(REPO, "out", "s57", "proposer", "controls.pkl")
        data = pickle.load(open(pk, "rb"))
        from collections import defaultdict
        g = defaultdict(list)
        for d in data:
            g[tuple(sorted(x[0] for x in d["chain"]))].append(d)

        groups = sorted(g.items(), key=lambda kv: -len(kv[1]))
        idx = int(spec[len("ctrlgroup"):])
        members = groups[idx][1]
        sol = [tuple(x) for x in members[0]["chain"]]
        inst = chain7.build_instance_from_chain(sol)
        covers = []
        for m in members:
            ex = P.extract(m["path"])
            covers.append(sorted(ex["known_rows"]))
        return inst, list(range(len(inst["rows"]))), [], covers
    if not spec.startswith("farm"):
        raise SystemExit(f"unknown spec: {spec}")
    idx = int(spec[4:])
    ch = [json.loads(l) for l in open(FARM)][idx]
    inst = chain7.build_instance_from_chain([tuple(x) for x in ch["chain"]])
    pr = json.load(open(PRUNE_JSON))[spec]
    return inst, sorted(set(pr["alive"]) | set(pr["fixed"])), list(pr["fixed"]), None


def build_base(spec="farm0"):
    """-> dict with the fixed-column base instance and the conflict sets.

    `rows_all` is the row pool in ascending ORIGINAL row id, which is what the
    no-good store records, so the store stays meaningful against a re-derived
    instance.
    """
    inst, rows_all, fixed_rows, covers = load_spec(spec)
    rows = inst["rows"]

    # Fixed, probe-invariant column index and loop index over the WHOLE
    # instance (not just survivors): ids must not renumber between probes.
    cols = list(inst["columns"])
    ci = {c: k for k, c in enumerate(cols)}
    roots = set(inst["roots"])
    loop_id = {}
    for r in rows_all:
        loop_id.setdefault(rows[r]["loop"], len(loop_id))

    # Each row's rendered line, once.  Format: loop_id parent_code c0..c{nchild-1}
    line = {}
    for r in rows_all:
        rr = rows[r]
        po = rr["parent_orbit"]
        pc = -1 if (po in roots or po not in ci) else ci[po]
        line[r] = (f"{loop_id[rr['loop']]} {pc} "
                   + " ".join(str(ci[c]) for c in rr["children"]))
    nchild = len(rows[rows_all[0]]["children"])

    # conflict sets: same 2-loop (ridden once) or sharing a child column
    by_col = {}
    for r in rows_all:
        for c in rows[r]["children"]:
            by_col.setdefault(c, []).append(r)
    by_loop = {}
    for r in rows_all:
        by_loop.setdefault(rows[r]["loop"], []).append(r)
    kill = {r: set() for r in rows_all}
    for grp in list(by_col.values()) + list(by_loop.values()):
        for r in grp:
            kill[r].update(grp)
    for r in rows_all:
        kill[r].discard(r)

    header = f"{len(cols)} %d {len(loop_id)} {nchild}"
    return dict(inst=inst, spec=spec, rows_all=rows_all, line=line, kill=kill,
                header=header, ncols=len(cols), nloops=len(loop_id),
                nchild=nchild, R=inst["meta"]["R"], K=inst["meta"]["K"],
                V=inst["meta"]["V"], fixed=list(fixed_rows), covers=covers)


def render_forced(B, forced):
    """Instance text forcing every row in `forced`.  -> (text, rowmap).

    Generalizes the pair case: the rows conflicting with ANY forced row are
    deleted, so each forced row is left as the unique cover of its own child
    columns.  Used with a 2-element list by the sweep, and with a walk-order
    prefix + a pair by the oracle's positive control.
    """
    kill = B["kill"]
    dead = set()
    for r in forced:
        dead |= kill[r]
    dead -= set(forced)
    keep = [r for r in B["rows_all"] if r not in dead]
    line = B["line"]
    return ((B["header"] % len(keep)) + "\n"
            + "\n".join(line[r] for r in keep) + "\n"), keep


def render_pair(B, i, j):
    """Instance text forcing rows i and j.  -> (text, rowmap)."""
    return render_forced(B, (i, j))


# ------------------------------------------------------------------ probe --
def probe(dlx, text, inst_fn, out_fn, cap, tl):
    with open(inst_fn, "w") as fh:
        fh.write(text)
    if os.path.exists(out_fn):
        os.remove(out_fn)
    cmd = [dlx, inst_fn, "--time-limit", str(tl), "--max-nodes", str(cap),
           "--out", out_fn]
    t0 = time.monotonic()
    pr = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.monotonic() - t0
    verdict = {0: "SAT", 2: "UNSAT", 3: "UNKNOWN"}.get(pr.returncode,
                                                       f"ERROR{pr.returncode}")
    ids = []
    if pr.returncode == 0 and os.path.exists(out_fn):
        ids = [int(x) for x in open(out_fn).read().split()]
    nodes = -1
    for tok in pr.stderr.split():
        if tok.startswith("nodes="):
            try:
                nodes = int(tok[6:])
            except ValueError:
                pass
    return verdict, dt, ids, nodes, pr.stderr.strip()[-400:]


# ------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="farm0")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap", type=int, default=2000)
    ap.add_argument("--tl", type=float, default=30.0)
    ap.add_argument("--limit", type=int, default=0,
                    help="probe only the first K rows of THIS shard (probe mode)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dlx", default=None)
    ap.add_argument("--reconfirm-mult", type=int, default=10,
                    help="re-run every refutation at this multiple of --cap in "
                         "a fresh process before storing it (s60 lesson); 0 off")
    a = ap.parse_args()

    si, sn = (int(x) for x in a.shard.split("/"))
    os.makedirs(a.out, exist_ok=True)
    dlx = a.dlx or (DEFAULT_DLX + (".exe" if os.name == "nt" else ""))
    if not a.dry_run and not os.path.exists(dlx):
        raise SystemExit(f"dlx7g not found: {dlx}")

    t0 = time.time()
    B = build_base(a.spec)
    rows_all = B["rows_all"]
    pos = {r: k for k, r in enumerate(rows_all)}
    nrows = len(rows_all)

    # Provenance: the un-forced base instance's hash pins what the store is a
    # store FOR.  A different pruning => a different base => a new store.
    # `relax_sha` is the s57/s60 relaxation render of the SAME pool, recorded so
    # this store can be matched against out/s60/nogood/*.jsonl, whose meta.base
    # carries that hash rather than ours.
    base_txt = ((B["header"] % nrows) + "\n"
                + "\n".join(B["line"][r] for r in rows_all) + "\n")
    base_sha = hashlib.sha256(base_txt.encode()).hexdigest()
    relax_sha = ""
    try:
        import propose as _PR
        _t, _rm, _nc, _nr = _PR.render(B["inst"],
                                       set(rows_all) - set(B["fixed"]),
                                       list(B["fixed"]))
        relax_sha = hashlib.sha256(_t.encode()).hexdigest()
    except Exception:                                          # noqa: BLE001
        pass

    mine = [r for k, r in enumerate(rows_all) if k % sn == si]
    if a.limit:
        mine = mine[:a.limit]

    # pair accounting for THIS shard (j strictly after i in rows_all order)
    tot_pairs = sum(nrows - 1 - pos[r] for r in mine)
    struct = sum(len(B["kill"][r] & set(rows_all[pos[r] + 1:])) for r in mine)
    to_probe = tot_pairs - struct

    tag = f"s{si:02d}"
    status_p = os.path.join(a.out, "STATUS")
    st = open(status_p, "a", buffering=1)

    def stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    if a.dry_run:
        st.write(f"{stamp()}\tDRYRUN\t0/{len(mine)}\tsizing only\n")
        st.write(f"{stamp()}\tDONE\tdry-run: {len(mine)} rows, {tot_pairs} pairs, "
                 f"{struct} structural, {to_probe} to probe\n")
        with open(os.path.join(a.out, f"paircuts_stats_{tag}.tsv"), "w") as fh:
            fh.write("shard\trows\tpairs\tstructural\tto_probe\tbase_sha\n")
            fh.write(f"{si}\t{len(mine)}\t{tot_pairs}\t{struct}\t{to_probe}"
                     f"\t{base_sha[:16]}\n")
        print(f"dry-run shard {si}/{sn}: rows={len(mine)} pairs={tot_pairs} "
              f"structural={struct} to_probe={to_probe} base_sha={base_sha[:16]}")
        st.close()
        return 0

    inst_fn = os.path.join(a.out, f"_inst_{tag}.txt")
    out_fn = os.path.join(a.out, f"_sol_{tag}.txt")
    ng_p = os.path.join(a.out, f"paircuts_nogoods_{tag}.jsonl")
    ng = open(ng_p, "w", buffering=1)
    ng.write(json.dumps(dict(
        kind="meta", spec=a.spec, shard=f"{si}/{sn}", size=2,
        base=dict(sha256=base_sha, relax_sha256=relax_sha, cols=B["ncols"],
                  rows=nrows, n_fixed=len(B["fixed"]), loops=B["nloops"]),
        base_fixed=list(B["fixed"]),
        lane="refutation(epsilon=0, deterministic)",
        cap_nodes=a.cap, reconfirm_cap_nodes=a.cap * a.reconfirm_mult,
        forcing="fixed-column: delete rows conflicting with i or j; columns "
                "and the first-visit ordering constraint are untouched",
        R=B["R"], K=B["K"], V=B["V"], argv=sys.argv[1:],
        started=time.strftime("%Y-%m-%dT%H:%M:%S"))) + "\n")

    covers = [set(c) for c in (B["covers"] or [])]
    n_probe = n_unsat = n_unknown = n_err = n_recheck_fail = n_violation = 0
    jackpot = None
    t_probe = 0.0
    for k, i in enumerate(mine):
        ki = B["kill"][i]
        for j in rows_all[pos[i] + 1:]:
            if j in ki:
                continue
            txt, keep = render_pair(B, i, j)
            verdict, dt, ids, nodes, err = probe(dlx, txt, inst_fn, out_fn,
                                                 a.cap, a.tl)
            n_probe += 1
            t_probe += dt
            if verdict == "UNSAT":
                # s60 lesson: re-confirm in a fresh process at >= 10x the cap
                # before storing.  Their cap was WALL-CLOCK, so cuts sat on the
                # boundary and re-runs were a coin flip; a NODE cap is
                # deterministic, so this should never fail -- which is exactly
                # why a failure here is worth an alarm rather than a shrug.
                rc_nodes, rc_ok = nodes, True
                if a.reconfirm_mult:
                    v2, dt2, _, n2, _ = probe(dlx, txt, inst_fn, out_fn,
                                              a.cap * a.reconfirm_mult, a.tl)
                    rc_nodes, rc_ok = n2, (v2 == "UNSAT")
                if not rc_ok:
                    n_recheck_fail += 1
                    print(f"*** RECONFIRM FAIL ({i},{j}): {verdict} at cap "
                          f"{a.cap} but {v2} at {a.cap * a.reconfirm_mult} "
                          f"-- NOT stored ***", flush=True)
                    continue
                # control lane: a cut inside a KNOWN cover is a soundness bug
                bad = [x for x, c in enumerate(covers) if i in c and j in c]
                if bad:
                    n_violation += 1
                    print(f"*** SOUNDNESS VIOLATION ({i},{j}) refuted but both "
                          f"rows lie in known cover(s) {bad[:3]} ***", flush=True)
                n_unsat += 1
                ng.write(json.dumps(dict(
                    kind="cut", spec=a.spec, cut=[i, j], size=2,
                    nodes=nodes, reconfirm_nodes=rc_nodes,
                    refute_s=round(dt, 5), rows=len(keep),
                    violation=bool(bad))) + "\n")
            elif verdict == "UNKNOWN":
                n_unknown += 1
            elif verdict == "SAT":
                full = [keep[x] for x in ids]
                jackpot = dict(i=i, j=j, rows=full, spec=a.spec,
                               base_sha=base_sha)
                with open(os.path.join(a.out, f"JACKPOT_{tag}.json"), "w") as fh:
                    json.dump(jackpot, fh, indent=1)
                msg = (f"*** JACKPOT: SAT on OPEN chain {a.spec} forcing rows "
                       f"{i},{j} -- {len(full)} rows -- 5905 CANDIDATE ***")
                print(msg, flush=True)
                st.write(f"{stamp()}\tJACKPOT\t{i},{j}\t{len(full)} rows\n")
                break
            else:
                n_err += 1
                if n_err <= 3:
                    print(f"!! probe error {verdict} on ({i},{j}): {err}",
                          flush=True)
        st.write(f"{stamp()}\trow{i}\t{k + 1}/{len(mine)}\t"
                 f"probed={n_probe} unsat={n_unsat} unknown={n_unknown}\n")
        if jackpot:
            break

    secs = time.time() - t0
    rate = (t_probe / n_probe) if n_probe else 0.0
    with open(os.path.join(a.out, f"paircuts_stats_{tag}.tsv"), "w") as fh:
        fh.write("shard\trows\tpairs\tstructural\tprobed\tnogoods\tunknown"
                 "\terrors\trecheck_fail\tviolations\tsecs_per_probe\tsecs"
                 "\tbase_sha\n")
        fh.write(f"{si}\t{len(mine)}\t{tot_pairs}\t{struct}\t{n_probe}"
                 f"\t{n_unsat}\t{n_unknown}\t{n_err}\t{n_recheck_fail}"
                 f"\t{n_violation}\t{rate:.5f}\t{secs:.1f}"
                 f"\t{base_sha[:16]}\n")
    if n_violation:
        print(f"*** {n_violation} SOUNDNESS VIOLATION(S) on {a.spec} -- the "
              f"reduction refuted a pair that occurs in a known cover ***",
              flush=True)
    ng.close()
    for f in (inst_fn, out_fn):
        if os.path.exists(f):
            os.remove(f)
    st.write(f"{stamp()}\tDONE\tshard {si}: {len(mine)} rows, {n_probe} probes, "
             f"{n_unsat} no-goods, {n_unknown} unknown, {n_err} errors, "
             f"{secs:.1f}s\n")
    st.close()
    print(f"shard {si}/{sn}: rows={len(mine)} pairs={tot_pairs} "
          f"structural={struct} probed={n_probe} NOGOODS {n_unsat} "
          f"unknown={n_unknown} errors={n_err} recheck_fail={n_recheck_fail} "
          f"violations={n_violation} {rate * 1000:.2f}ms/probe {secs:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
