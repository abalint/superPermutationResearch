#!/usr/bin/env python3
"""Track C v2 column-feature extractor (docs/TRACKC2-DESIGN.md §2).

Teacher-forces a known cover through the same pure-Python DLX + rooted-forest
state `replay.py` uses (this module subclasses `replay.ReplayState`, so the
`size` / `grounded` / `pending` maintenance is literally the v1 code that
already passed the v1 byte-clean parity gate) and, at every node BEFORE the
column is covered, prints the LOCKED 10-vector for **every active column**.

Determinism contract shared with the C engine (`dlx7g --dump-col-features`)
---------------------------------------------------------------------------
* Replay column policy is fixed at **plain MRV**: smallest `size`, ties by
  lowest column index.  (The learned policy is never used in parity mode; the
  point of the gate is the feature arithmetic, not the choice.)
* Features are evaluated on the state **before** `cover(c)` (v1 timing rule).
* Every active column is dumped, in **ascending column id** — the order the C
  engine's header list walk produces, since DLX unlink/relink preserves the
  header ring's ascending order.
* A child orbit that is already covered contributes `log1p(0) = 0.0`
  (v1 convention).  Under a valid cover this case is unreachable: an active
  row's child columns are all active, and every active column keeps its own
  cover row active, so `size >= 1` throughout.  Implemented anyway, together
  with the `size[c] == 0` degenerate (features 7/8 fall back to 0.0).
* Line format, one line per (node, active column):

      <node_idx> <col_id> f1 .. f10        (all values "%.6f")

usage:
  python3 colfeat.py --parity-dump analysis/trackc/runs/parity_col_py.txt
  python3 colfeat.py --instance n6std --cover data/trackc/parity/cover_rows.txt
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from instances import DATA, REPO, n6_standard, n7_standard  # noqa: E402
from replay import ReplayError, ReplayState, n6_covers  # noqa: E402

NFEAT = 10
FEATURE_ORDER = [
    "sz_log",
    "sz_rel",
    "static_sz_log",
    "is_root",
    "grounded_c",
    "pending_log",
    "mean_child_load",
    "min_child_load",
    "frac_parents_grounded",
    "active_cols_log",
]

DEFAULT_DUMP = os.path.join(HERE, "runs", "parity_col_py.txt")
DEFAULT_COVER = os.path.join(DATA, "parity", "cover_rows.txt")

INSTANCES = {
    "n6std": n6_standard,
    "n7std": n7_standard,
}


# ------------------------------------------------------------------ state


class ColReplayState(ReplayState):
    """`ReplayState` + the §2 per-column feature vector.

    Nothing about the DLX / forest maintenance changes; the v2 features are a
    pure read of the same arrays, so a v1-parity-clean state stays parity-clean.
    """

    def __init__(self, inst: dict):
        super().__init__(inst)
        self.static_col_log = [math.log1p(s) for s in self.static_size]
        # Root orbits are *not* columns in any instance we build (the kernel
        # pre-covers them), so feature 4 reads 0.0 everywhere; the membership
        # test is kept literal so the code matches the spec, not the accident.
        self.root_cols = {
            self.col_index[c] for c in self.roots if c in self.col_index
        }

    def active_columns(self) -> list:
        return [c for c in range(self.ncols) if self.col_active[c]]

    def min_size(self, active) -> int:
        return min(len(self.col_rows[c]) for c in active)

    def col_features(self, c: int, min_sz: int, active_cols_log: float) -> list:
        rows = self.candidates(c)
        sz = len(self.col_rows[c])
        k = self.nchild
        if rows:
            mean_load = 0.0
            min_load = None
            for rid in rows:
                tot = 0.0
                for x in self.row_children[rid]:
                    v = math.log1p(len(self.col_rows[x]) if self.col_active[x] else 0)
                    tot += v
                    if min_load is None or v < min_load:
                        min_load = v
                mean_load += tot / k
            f7 = mean_load / len(rows)
            f8 = min_load
            f9 = sum(1 for rid in rows if self.parent_grounded(rid)) / len(rows)
        else:  # unreachable under a valid cover; defined for safety
            f7 = f8 = f9 = 0.0
        return [
            math.log1p(sz),
            float(sz - min_sz),
            self.static_col_log[c],
            1.0 if c in self.root_cols else 0.0,
            1.0 if c in self.depth else 0.0,
            math.log1p(self.pending[c]),
            f7,
            f8,
            f9,
            active_cols_log,
        ]


# ------------------------------------------------------------------ replay


def dump_col_features(inst: dict, cover_row_ids, fh) -> tuple[int, int]:
    """Teacher-forced replay; writes `<node> <col> f1..f10`.  -> (nodes, lines)."""
    st = ColReplayState(inst)
    remaining = set(cover_row_ids)
    if len(remaining) != len(list(cover_row_ids)):
        raise ReplayError("cover contains a duplicate row id")
    covers = {}
    for rid in remaining:
        for c in st.row_children[rid]:
            if c in covers:
                raise ReplayError("cover rows overlap on a column")
            covers[c] = rid

    nodes = lines = 0
    while remaining:
        active = st.active_columns()
        if not active:
            raise ReplayError("no active column left but cover rows remain")
        min_sz = st.min_size(active)
        acl = math.log1p(len(active))
        for c in active:
            f = st.col_features(c, min_sz, acl)
            fh.write(
                "%d %d %s\n" % (nodes, c, " ".join("%.6f" % v for v in f))
            )
            lines += 1

        c = st.mrv_column()  # plain MRV, ties by lowest column index
        if not st.col_rows[c]:
            raise ReplayError(f"MRV column {c} has zero candidates")
        pos = covers.get(c)
        if pos is None:
            raise ReplayError(f"MRV column {c} is not covered by the cover")
        if pos not in st.col_rows[c]:
            raise ReplayError(
                f"positive row {pos} is not an active candidate of column {c}"
            )
        st.place(pos)
        remaining.discard(pos)
        nodes += 1
    if any(st.col_active):
        raise ReplayError("cover consumed but active columns remain")
    return nodes, lines


# ------------------------------------------------------------- cover source


def load_cover(path: str) -> list:
    with open(path) as fh:
        return [int(x) for x in fh.read().split()]


def default_cover(inst: dict) -> tuple[list, str]:
    """The v1 parity trace: the committed row-id list, else re-derive it."""
    if os.path.exists(DEFAULT_COVER):
        return load_cover(DEFAULT_COVER), os.path.relpath(DEFAULT_COVER, REPO)
    covers, _ = n6_covers(inst)
    if not covers:
        raise SystemExit("no n=6 cover available for the parity artifact")
    path, ids = covers[0]
    return ids, os.path.relpath(path, REPO)


# ------------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instance", default="n6std", choices=sorted(INSTANCES),
                    help="instance to replay (default n6std)")
    ap.add_argument("--cover", help="row-id list file (default: the v1 parity "
                                    "cover, data/trackc/parity/cover_rows.txt)")
    ap.add_argument("--parity-dump", default=DEFAULT_DUMP,
                    help="output path for the column-feature dump")
    ap.add_argument("--meta", help="also write a sidecar .meta.json here")
    args = ap.parse_args()

    inst = INSTANCES[args.instance]()
    if args.cover:
        ids, src = load_cover(args.cover), os.path.relpath(args.cover, REPO)
    elif args.instance == "n6std":
        ids, src = default_cover(inst)
    else:
        raise SystemExit(f"--cover is required for instance {args.instance}")
    ids = sorted(ids)

    out = os.path.abspath(args.parity_dump)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        nodes, lines = dump_col_features(inst, ids, fh)

    print(f"colfeat {args.instance}: {nodes} nodes, {lines} column lines "
          f"(cover={src}, rows={len(ids)})")
    print(f"  wrote {os.path.relpath(out, REPO)}")
    if args.instance == "n6std":
        print(f"  GATE {'OK' if nodes == 25 else 'FAIL'} ({nodes} nodes, "
              f"expected 25)")

    if args.meta:
        with open(args.meta, "w") as fh:
            json.dump(
                {
                    "instance": args.instance,
                    "cover_source": src,
                    "rows": len(ids),
                    "nodes": nodes,
                    "lines": lines,
                    "feature_order": FEATURE_ORDER,
                    "format": "'<node_idx> <col_id> f1..f10' (%.6f), one line "
                              "per active column, columns ascending by id",
                    "feature_timing": "before cover(c)",
                    "column_policy": "MRV, ties by lowest column index",
                },
                fh,
                indent=1,
            )
            fh.write("\n")


if __name__ == "__main__":
    main()
