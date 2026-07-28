#!/usr/bin/env python3
"""Track C v2 corpus assembly: merge `dlx7g --log-subtrees` logs.

docs/TRACKC2-DESIGN.md §3.  Each engine run writes one JSONL record per
qualifying node at frame pop:

    {"inst": tag, "depth": d, "cand": |C*_Dgen|, "col": chosen_id,
     "feats": [10 floats], "subtree": nodes_in_subtree, "outcome": "exhaust"}

v2.1 (§3b) adds `"shash"` (state key) and, on probe records, `"probe": 1`.
`--pairs OUT.jsonl` turns the corpus into WITHIN-STATE comparisons: group by
(inst, shash), emit one line per ordered pair of distinct columns observed at
the same state, winner = smaller subtree.  This is the confound-free training
signal — state hardness cancels when both sides share the state.

This merges any number of such logs into `data/trackc/coleffort_<tag>.jsonl`.
Nothing is deduped (repeated states across epsilon runs are *signal* — they are
different policy rollouts of the same decision, §8 risk 1); every record is
schema-validated, stamped with an instance tag, and counted.

Instance tag resolution, highest priority first:
  1. an explicit `path=tag` on the command line
  2. `--inst TAG` (applies to every file that has no `path=tag`)
  3. the record's own "inst" field
  4. the file's basename with a trailing `_subtrees`/`.jsonl`/`.log` stripped

usage:
  python3 mine_subtrees.py --out-tag s19 runs/gen/*.jsonl
  python3 mine_subtrees.py --out-tag n6 runs/a.jsonl=n6std runs/b.jsonl=n6std
  python3 mine_subtrees.py --out-tag t --out /tmp/x.jsonl runs/fixture.jsonl
  python3 mine_subtrees.py --dry-run --pairs data/trackc/pairs_s19.jsonl runs/*.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from instances import DATA, REPO  # noqa: E402

NFEAT = 10
INT_FIELDS = ("depth", "cand", "col", "subtree")
REQUIRED = ("depth", "cand", "col", "feats", "subtree", "outcome")
QUALIFY = 500  # §3 unconditional logging threshold (below it: 1/1024 sample)
OUTCOMES = ("exhaust", "capped")  # §3b: `capped` = probe hit --probe-cap


# ------------------------------------------------------------- validation


def validate(rec) -> str | None:
    """-> None if the record matches §3, else a short reason string."""
    if not isinstance(rec, dict):
        return "not an object"
    for k in REQUIRED:
        if k not in rec:
            return f"missing {k!r}"
    for k in INT_FIELDS:
        v = rec[k]
        if isinstance(v, bool) or not isinstance(v, int):
            return f"{k} is not an int"
    if rec["depth"] < 0:
        return "depth < 0"
    if rec["cand"] < 1:
        return "cand < 1"
    if rec["col"] < 0:
        return "col < 0"
    if rec["subtree"] < 1:
        return "subtree < 1"
    f = rec["feats"]
    if not isinstance(f, list) or len(f) != NFEAT:
        return f"feats is not a list of {NFEAT}"
    for v in f:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return "feats holds a non-number"
        if not math.isfinite(float(v)):
            return "feats holds a non-finite value"
    if not isinstance(rec["outcome"], str) or not rec["outcome"]:
        return "outcome is not a non-empty string"
    if rec["outcome"] not in OUTCOMES:
        return f"unknown outcome {rec['outcome']!r}"
    sh = rec.get("shash")
    if sh is not None:
        if not isinstance(sh, str) or len(sh) != 16:
            return "shash is not a 16-char hex string"
        try:
            int(sh, 16)
        except ValueError:
            return "shash is not hexadecimal"
    return None


def file_tag(path: str) -> str:
    base = os.path.basename(path)
    for suf in (".jsonl", ".json", ".log", ".txt"):
        if base.endswith(suf):
            base = base[: -len(suf)]
    for suf in ("_subtrees", "-subtrees"):
        if base.endswith(suf):
            base = base[: -len(suf)]
    return base


def split_spec(spec: str) -> tuple[str, str | None]:
    """`path=tag` -> (path, tag); a bare path -> (path, None)."""
    if "=" in spec:
        path, tag = spec.rsplit("=", 1)
        if path and tag:
            return path, tag
    return spec, None


# ------------------------------------------------------- within-state pairs
#
# docs/TRACKC2-DESIGN.md §3b.  Two records are comparable iff they share
# (inst, shash) — the same instance in the same state (same placed-row set) —
# and name different columns.  The subtree sizes then differ only because the
# CHOICE differed, which is the whole point: state hardness cancels.


def _better(a, b):
    """Which of two records for the SAME (inst, shash, col) to keep.

    Several runs (different seeds / policies) can log the same state+column
    with different subtree sizes, because the size also depends on the run's
    own downstream choices.  We keep the smallest *finished* subtree (the
    achievable effort for that column) and, failing that, the largest capped
    count (the strongest lower bound, which makes `capped` comparisons as
    informative as they can soundly be).
    """
    if a is None:
        return b
    afin, bfin = a["outcome"] == "exhaust", b["outcome"] == "exhaust"
    if afin != bfin:
        return a if afin else b
    if afin:
        return a if a["subtree"] <= b["subtree"] else b
    return a if a["subtree"] >= b["subtree"] else b


def compare(a, b):
    """-> (winner, loser) or None if the comparison is unsound (§3b).

    exhaust vs exhaust : smaller subtree wins; exact ties carry no order.
    exhaust vs capped  : the finished side wins ONLY if its subtree is smaller
                         than the capped side's node count — then the capped
                         column provably cost more.  Otherwise indeterminate.
    capped  vs capped  : always indeterminate.
    """
    afin, bfin = a["outcome"] == "exhaust", b["outcome"] == "exhaust"
    if afin and bfin:
        if a["subtree"] == b["subtree"]:
            return None
        return (a, b) if a["subtree"] < b["subtree"] else (b, a)
    if afin and not bfin:
        return (a, b) if a["subtree"] < b["subtree"] else None
    if bfin and not afin:
        return (b, a) if b["subtree"] < a["subtree"] else None
    return None


def emit_pairs(groups, out_path):
    """groups: {(inst, shash): {col: record}} -> write pair JSONL, -> report."""
    by_src: dict = {}
    by_inst: dict = {}
    n_pairs = 0
    n_groups_multi = 0
    n_drop = 0
    with open(out_path, "w") as fh:
        for (inst, shash), cols in groups.items():
            if len(cols) < 2:
                continue
            n_groups_multi += 1
            recs = [cols[k] for k in sorted(cols)]
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    verdict = compare(recs[i], recs[j])
                    if verdict is None:
                        n_drop += 1
                        continue
                    win, lose = verdict
                    src = "probe" if (win.get("probe") or lose.get("probe")) \
                        else "transpo"
                    fh.write(json.dumps({
                        "inst": inst,
                        "shash": shash,
                        "depth": win["depth"],
                        "fw": win["feats"],
                        "fl": lose["feats"],
                        "yw": win["subtree"],
                        "yl": lose["subtree"],
                        "src": src,
                    }, separators=(",", ":")) + "\n")
                    n_pairs += 1
                    by_src[src] = by_src.get(src, 0) + 1
                    by_inst.setdefault(inst, {})
                    by_inst[inst][src] = by_inst[inst].get(src, 0) + 1
    return {
        "path": out_path,
        "n_pairs": n_pairs,
        "n_groups_multi": n_groups_multi,
        "n_dropped": n_drop,
        "by_src": by_src,
        "by_inst": by_inst,
    }


# ----------------------------------------------------------------- merge


def merge(specs, default_tag=None, out_path=None, pairs=False):
    """Read every spec, validate, stamp tags, write the corpus.  -> report."""
    per_inst: dict = {}
    per_file = []
    bad_examples = []
    n_bad = 0
    n_ok = 0
    n_noshash = 0
    groups: dict = {}
    fh_out = open(out_path, "w") if out_path else None
    try:
        for spec in specs:
            path, tag = split_spec(spec)
            if not os.path.exists(path):
                raise SystemExit(f"no such log file: {path}")
            fallback = tag or default_tag
            fbad = fok = 0
            with open(path) as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError as exc:
                        n_bad += 1
                        fbad += 1
                        if len(bad_examples) < 5:
                            bad_examples.append(f"{path}:{lineno} {exc}")
                        continue
                    why = validate(rec)
                    if why:
                        n_bad += 1
                        fbad += 1
                        if len(bad_examples) < 5:
                            bad_examples.append(f"{path}:{lineno} {why}")
                        continue
                    inst = fallback or rec.get("inst") or file_tag(path)
                    rec["inst"] = inst
                    rec["src"] = os.path.basename(path)
                    n_ok += 1
                    fok += 1
                    st = per_inst.setdefault(
                        inst, {"n": 0, "subtree": [], "depth": []}
                    )
                    st["n"] += 1
                    st["subtree"].append(rec["subtree"])
                    st["depth"].append(rec["depth"])
                    if fh_out:
                        fh_out.write(json.dumps(rec, separators=(",", ":")) + "\n")
                    if pairs:
                        sh = rec.get("shash")
                        if sh is None:
                            n_noshash += 1
                            continue
                        g = groups.setdefault((inst, sh), {})
                        col = rec["col"]
                        g[col] = _better(g.get(col), rec)
            per_file.append((path, fok, fbad))
    finally:
        if fh_out:
            fh_out.close()
    return {
        "per_inst": per_inst,
        "per_file": per_file,
        "n_ok": n_ok,
        "n_bad": n_bad,
        "n_noshash": n_noshash,
        "bad_examples": bad_examples,
        "out": out_path,
        "groups": groups,
    }


# --------------------------------------------------------------- summary


def quantile(sorted_vals, q: float) -> float:
    """Linear-interpolated quantile (numpy is not imported here on purpose)."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def summarize(vals) -> dict:
    s = sorted(vals)
    return {
        "n": len(s),
        "min": s[0],
        "p25": quantile(s, 0.25),
        "median": quantile(s, 0.50),
        "p75": quantile(s, 0.75),
        "p90": quantile(s, 0.90),
        "p99": quantile(s, 0.99),
        "max": s[-1],
        "mean": sum(s) / len(s),
        "ge_qualify": sum(1 for v in s if v >= QUALIFY),
    }


def log_hist(vals) -> list:
    """(exponent, count) buckets by floor(log10(subtree))."""
    buckets: dict = {}
    for v in vals:
        e = int(math.floor(math.log10(v))) if v > 0 else 0
        buckets[e] = buckets.get(e, 0) + 1
    return sorted(buckets.items())


def report(rep) -> None:
    print("per-file records (ok / rejected):")
    for path, ok, bad in rep["per_file"]:
        print(f"  {os.path.basename(path):<40} {ok:>9,} / {bad:,}")
    print(f"\nper-instance records ({len(rep['per_inst'])} instances):")
    for inst in sorted(rep["per_inst"]):
        st = rep["per_inst"][inst]
        d = summarize(st["depth"])
        s = summarize(st["subtree"])
        print(f"  {inst:<28} n={st['n']:>9,}  depth "
              f"[{d['min']}..{d['max']}] med {d['median']:.0f}  "
              f"subtree med {s['median']:,.0f} p90 {s['p90']:,.0f} "
              f"max {s['max']:,}")
    allsub = [v for st in rep["per_inst"].values() for v in st["subtree"]]
    if allsub:
        s = summarize(allsub)
        print(f"\nsubtree size distribution (all {s['n']:,} records):")
        for k in ("min", "p25", "median", "p75", "p90", "p99", "max", "mean"):
            print(f"  {k:<7} {s[k]:>15,.1f}")
        print(f"  >= {QUALIFY} nodes: {s['ge_qualify']:,} "
              f"({100.0*s['ge_qualify']/s['n']:.1f}%)")
        print("  log10 buckets:")
        for e, c in log_hist(allsub):
            print(f"    1e{e:<2d} {c:>9,}  {100.0*c/s['n']:5.1f}%")
    print(f"\ntotal: {rep['n_ok']:,} records kept, {rep['n_bad']:,} rejected")
    for ex in rep["bad_examples"]:
        print(f"  REJECT {ex}")
    if rep["n_bad"] > len(rep["bad_examples"]):
        print(f"  ... and {rep['n_bad'] - len(rep['bad_examples']):,} more")
    if rep["out"]:
        rel = os.path.relpath(rep["out"], REPO)
        print(f"wrote {rep['out'] if rel.startswith('..') else rel}")


def report_pairs(rep, prep) -> None:
    print(f"\nwithin-state pairs (§3b), {rep['n_ok']:,} records "
          f"({rep['n_noshash']:,} without shash, skipped):")
    ngroups = len(rep["groups"])
    print(f"  distinct states (inst,shash) : {ngroups:,}")
    print(f"  states with >= 2 columns     : {prep['n_groups_multi']:,} "
          f"({100.0*prep['n_groups_multi']/ngroups if ngroups else 0:.3f}%)")
    print(f"  comparisons dropped (capped/tie): {prep['n_dropped']:,}")
    print(f"  PAIRS EMITTED                : {prep['n_pairs']:,}")
    print("  by source:")
    for src in sorted(prep["by_src"]):
        print(f"    {src:<10} {prep['by_src'][src]:>10,}")
    print("  by instance:")
    for inst in sorted(prep["by_inst"]):
        d = prep["by_inst"][inst]
        tot = sum(d.values())
        detail = "  ".join(f"{k}={v:,}" for k, v in sorted(d.items()))
        print(f"    {inst:<24} {tot:>10,}   {detail}")
    if rep["n_ok"]:
        per_m = 1e6 * prep["n_pairs"] / rep["n_ok"]
        print(f"  yield: {per_m:,.1f} pairs per million records")
    rel = os.path.relpath(prep["path"], REPO)
    print(f"wrote {prep['path'] if rel.startswith('..') else rel}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logs", nargs="+", help="engine JSONL logs (`path` or `path=tag`)")
    ap.add_argument("--out-tag", help="corpus tag -> data/trackc/coleffort_<tag>.jsonl")
    ap.add_argument("--out", help="explicit output path (overrides --out-tag)")
    ap.add_argument("--inst", help="default instance tag for untagged files")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    ap.add_argument("--pairs", metavar="OUT.jsonl",
                    help="also mine within-state pairs (§3b) into OUT.jsonl")
    args = ap.parse_args()

    out = None
    if not args.dry_run:
        if args.out:
            out = os.path.abspath(args.out)
        elif args.out_tag:
            out = os.path.join(DATA, f"coleffort_{args.out_tag}.jsonl")
        elif not args.pairs:
            raise SystemExit("need --out-tag, --out, --pairs, or --dry-run")
        if out:
            os.makedirs(os.path.dirname(out), exist_ok=True)

    rep = merge(args.logs, default_tag=args.inst, out_path=out,
                pairs=bool(args.pairs))
    report(rep)
    if args.pairs:
        pout = os.path.abspath(args.pairs)
        d = os.path.dirname(pout)
        if d:
            os.makedirs(d, exist_ok=True)
        report_pairs(rep, emit_pairs(rep["groups"], pout))
    return 0 if rep["n_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
