#!/usr/bin/env python3
"""Streaming (O(1)-memory) equivalent of `mine_subtrees.py --pairs`.

`mine_subtrees.py` builds the whole {(inst, shash): {col: record}} map in RAM.
At the local generation volumes (a 600 s probed run emits ~5 M records) that is
~10 GB, so this variant does the same grouping on disk: it tags every record
with its shash, sorts by shash with coreutils `sort`, and then walks the sorted
stream one state-group at a time.  The pair semantics are IDENTICAL to
mine_subtrees.compare/emit_pairs (docs/TRACKC2-DESIGN.md section 3b):

  * per (inst, shash, col) keep the SMALLEST finished subtree, else the LARGEST
    capped count;
  * exhaust vs exhaust -> smaller subtree wins, exact ties dropped;
  * exhaust vs capped  -> the finished side wins only if it is strictly smaller
    than the capped count, else indeterminate;
  * capped vs capped   -> indeterminate;
  * src = "probe" if either side carries the probe marker, else "transpo".

Verified equal to mine_subtrees.py --pairs on the same inputs (see --verify).

usage: mine_stream.py --pairs OUT.jsonl [--tmp DIR] LOG[=tag] ...
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_subtrees import compare, split_spec, validate, file_tag  # noqa: E402


def keep_better(cur: dict, new: dict) -> dict:
    """mine_subtrees' per-(inst,shash,col) reduction."""
    cfin, nfin = cur["outcome"] == "exhaust", new["outcome"] == "exhaust"
    if nfin and not cfin:
        return new
    if cfin and not nfin:
        return cur
    if nfin and cfin:
        return new if new["subtree"] < cur["subtree"] else cur
    return new if new["subtree"] > cur["subtree"] else cur


def emit_group(recs: dict, inst: str, shash: str, fh, stats) -> None:
    if len(recs) < 2:
        return
    stats["groups_multi"] += 1
    ordered = [recs[k] for k in sorted(recs)]
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            verdict = compare(ordered[i], ordered[j])
            if verdict is None:
                stats["dropped"] += 1
                continue
            win, lose = verdict
            src = "probe" if (win.get("probe") or lose.get("probe")) else "transpo"
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
            stats["pairs"] += 1
            stats["by_src"][src] = stats["by_src"].get(src, 0) + 1
            stats["by_inst"].setdefault(inst, {})
            stats["by_inst"][inst][src] = stats["by_inst"][inst].get(src, 0) + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--inst")
    ap.add_argument("--tmp", default=None)
    args = ap.parse_args()

    tmpdir = args.tmp or tempfile.gettempdir()
    os.makedirs(tmpdir, exist_ok=True)
    tagged = os.path.join(tmpdir, f"mine_stream_{os.getpid()}.tsv")

    n_ok = n_bad = n_noshash = 0
    with open(tagged, "w") as out:
        for spec in args.logs:
            path, tag = split_spec(spec)
            if not os.path.exists(path):
                raise SystemExit(f"no such log file: {path}")
            fallback = tag or args.inst
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        n_bad += 1
                        continue
                    if validate(rec):
                        n_bad += 1
                        continue
                    sh = rec.get("shash")
                    if sh is None:
                        n_noshash += 1
                        continue
                    rec["inst"] = fallback or rec.get("inst") or file_tag(path)
                    n_ok += 1
                    out.write(f"{rec['inst']}\t{sh}\t"
                              f"{json.dumps(rec, separators=(',', ':'))}\n")

    sortd = tagged + ".sorted"
    env = dict(os.environ, LC_ALL="C")
    # -s (stable) is load-bearing: the per-(inst,shash,col) reduction in
    # mine_subtrees._better keeps the FIRST of two tied records, so input order
    # inside a state group must survive the sort or tied pairs get a different
    # `src` label than the reference miner produces.
    subprocess.run(["sort", "-s", "-t", "\t", "-k1,1", "-k2,2", "-T", tmpdir,
                    "-o", sortd, tagged], check=True, env=env)
    os.unlink(tagged)

    stats = {"pairs": 0, "groups_multi": 0, "dropped": 0,
             "by_src": {}, "by_inst": {}}
    with open(args.pairs, "w") as fh, open(sortd) as src:
        cur_key = None
        cur: dict = {}
        for line in src:
            inst, sh, js = line.rstrip("\n").split("\t", 2)
            if (inst, sh) != cur_key:
                if cur_key is not None:
                    emit_group(cur, cur_key[0], cur_key[1], fh, stats)
                cur_key, cur = (inst, sh), {}
            rec = json.loads(js)
            col = rec["col"]
            cur[col] = keep_better(cur[col], rec) if col in cur else rec
        if cur_key is not None:
            emit_group(cur, cur_key[0], cur_key[1], fh, stats)
    os.unlink(sortd)

    print(f"[mine_stream] records ok={n_ok} bad={n_bad} noshash={n_noshash}")
    print(f"[mine_stream] pairs={stats['pairs']} "
          f"multi-col states={stats['groups_multi']} "
          f"indeterminate={stats['dropped']} by_src={stats['by_src']}")
    for inst in sorted(stats["by_inst"]):
        print(f"[mine_stream]   {inst}: {stats['by_inst'][inst]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
