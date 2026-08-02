#!/usr/bin/env python3
"""Track C teacher-forced replay + feature extraction (docs/TRACKC-DESIGN.md).

Replays a *known* cover through a minimal deterministic DLX state (column
sizes under row placement, plus the rooted-forest `grounded`/`pending` maps of
design §2) and emits, per decision node, the §3 JSONL record: the MRV column,
the cover's row (positive), its sibling negatives, and the LOCKED 8-feature
vector for every candidate.

Determinism contract shared with the C engine
---------------------------------------------
* MRV column = smallest `size`, ties broken by lowest column index.
* Candidates are enumerated in ascending row id.
* Features are evaluated at the node state **before** column `c` is covered
  (`c` is still an active column, so `size[c]` is well defined and every
  candidate row is still linked into all of its child columns).  This is the
  only reading of §2 under which feature 1 is not identically log1p(0); the
  post-cover(c) alternative is available via `--post-cover` for diagnosis.

usage:
  python3 replay.py corpus [--out DIR]     # write data/trackc/corpus_*.jsonl
  python3 replay.py parity [--out DIR]     # write data/trackc/parity/*
  python3 replay.py all
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/trackc")

from instances import (  # noqa: E402
    COVER7,
    DATA,
    REPO,
    cert5906_paths,
    cert5907_paths,
    cert_family,
    chain5906_families,
    n6_standard,
    n7_standard,
)

import gain1  # noqa: E402
from certificate import extract_certificate, format_loop, parse_loop  # noqa: E402

NFEAT = 8
FEATURE_ORDER = [
    "min_child_sz_log",
    "mean_child_sz_log",
    "scarce_children",
    "parent_is_root",
    "parent_grounded",
    "parent_depth_log",
    "static_min_child_log",
    "grounds_pending",
]


# ------------------------------------------------------------------ state


class ReplayState:
    """Forward-only DLX + rooted-forest state for teacher-forced replay.

    Teacher forcing never backtracks, so no undo trail is kept; the C engine's
    trailed version must agree with this on every forward state.
    """

    def __init__(self, inst: dict, post_cover: bool = False):
        self.inst = inst
        self.n = inst["n"]
        self.nchild = self.n - 2
        self.post_cover = post_cover
        self.columns = inst["columns"]
        self.col_index = {c: i for i, c in enumerate(self.columns)}
        self.ncols = len(self.columns)
        self.rows = inst["rows"]
        self.nrows = len(self.rows)
        self.roots = set(inst["roots"])

        # integer-id views of the instance (the C engine's vocabulary)
        ci = self.col_index
        self.row_children = [tuple(ci[c] for c in r["children"]) for r in self.rows]
        self.row_parent = [
            -1 if r["parent_orbit"] in self.roots else ci[r["parent_orbit"]]
            for r in self.rows
        ]

        # DLX column state
        self.col_rows = [set() for _ in range(self.ncols)]
        for rid, ch in enumerate(self.row_children):
            for c in ch:
                self.col_rows[c].add(rid)
        self.col_active = [True] * self.ncols
        self.row_active = [True] * self.nrows
        self.static_size = [len(s) for s in self.col_rows]
        self.static_min_child_log = [
            math.log1p(min(self.static_size[c] for c in ch))
            for ch in self.row_children
        ]

        # rooted-forest state: depth of grounded orbits, pending counts
        self.depth = {}  # column id -> #placed-row hops to a root (grounded only)
        self.pending = [0] * self.ncols  # column id -> placed-but-ungrounded count
        self.pending_rows = [[] for _ in range(self.ncols)]
        self.placed = []

    # -- DLX ----------------------------------------------------------
    def size(self, c: int) -> int:
        return len(self.col_rows[c])

    def cover_column(self, c: int) -> None:
        self.col_active[c] = False
        for rid in list(self.col_rows[c]):
            if not self.row_active[rid]:
                continue
            self.row_active[rid] = False
            for x in self.row_children[rid]:
                self.col_rows[x].discard(rid)

    def mrv_column(self) -> int | None:
        """Smallest active column, ties by lowest column index."""
        best, best_sz = None, None
        for c in range(self.ncols):
            if not self.col_active[c]:
                continue
            sz = len(self.col_rows[c])
            if best_sz is None or sz < best_sz:
                best, best_sz = c, sz
        return best

    def candidates(self, c: int) -> list:
        return sorted(self.col_rows[c])

    # -- rooted forest -------------------------------------------------
    def _ground(self, col: int, d: int) -> None:
        """Mark orbit `col` grounded at depth `d`, cascading to waiters."""
        stack = [(col, d)]
        while stack:
            x, dx = stack.pop()
            if x in self.depth:
                continue
            self.depth[x] = dx
            waiting = self.pending_rows[x]
            if waiting:
                self.pending_rows[x] = []
                self.pending[x] = 0
                for w in waiting:
                    for ch in self.row_children[w]:
                        stack.append((ch, dx + 1))

    def parent_grounded(self, rid: int) -> bool:
        p = self.row_parent[rid]
        return p == -1 or p in self.depth

    def parent_depth(self, rid: int) -> int:
        p = self.row_parent[rid]
        return 0 if p == -1 else self.depth[p]

    def place(self, rid: int) -> None:
        """Place row `rid`: cover its child columns, update the forest."""
        p = self.row_parent[rid]
        if p == -1:
            grounded, pd = True, 0
        elif p in self.depth:
            grounded, pd = True, self.depth[p]
        else:
            grounded, pd = False, None
        for c in self.row_children[rid]:
            self.cover_column(c)
        if grounded:
            for c in self.row_children[rid]:
                self._ground(c, pd + 1)
        else:
            self.pending[p] += 1
            self.pending_rows[p].append(rid)
        self.placed.append(rid)

    # -- features ------------------------------------------------------
    def features(self, rid: int) -> list:
        ch = self.row_children[rid]
        k = self.nchild
        sizes = [len(self.col_rows[c]) for c in ch]
        f1 = math.log1p(min(sizes))
        f2 = sum(math.log1p(s) for s in sizes) / k
        f3 = sum(1 for s in sizes if s <= 2) / k
        p = self.row_parent[rid]
        f4 = 1.0 if p == -1 else 0.0
        g = p == -1 or p in self.depth
        f5 = 1.0 if g else 0.0
        f6 = math.log1p(0 if p == -1 else self.depth[p]) if g else 0.0
        f7 = self.static_min_child_log[rid]
        f8 = sum(self.pending[c] for c in ch) / k
        return [f1, f2, f3, f4, f5, f6, f7, f8]


# ------------------------------------------------------------------ replay


class ReplayError(RuntimeError):
    pass


def replay(inst: dict, cover_row_ids, tag: str, post_cover: bool = False) -> list:
    """Teacher-forced replay; returns the list of §3 decision records."""
    st = ReplayState(inst, post_cover=post_cover)
    remaining = set(cover_row_ids)
    if len(remaining) != len(list(cover_row_ids)):
        raise ReplayError("cover contains a duplicate row id")
    covers = {}
    for rid in remaining:
        for c in st.row_children[rid]:
            if c in covers:
                raise ReplayError("cover rows overlap on a column")
            covers[c] = rid

    out = []
    while remaining:
        c = st.mrv_column()
        if c is None:
            raise ReplayError("no active column left but cover rows remain")
        cands = st.candidates(c)
        if not cands:
            raise ReplayError(f"MRV column {c} has zero candidates")
        pos = covers.get(c)
        if pos is None:
            raise ReplayError(f"MRV column {c} is not covered by the cover")
        if pos not in st.col_rows[c]:
            raise ReplayError(
                f"positive row {pos} is not an active candidate of column {c}"
            )
        if post_cover:
            # diagnostic alternative timing: evaluate after cover(c) (this is
            # what a C engine that scores inside its post-cover candidate loop
            # would see).  cover_column is idempotent, so place() still works.
            st.cover_column(c)
        feats = {rid: st.features(rid) for rid in cands}
        out.append(
            {
                "inst": tag,
                "n": st.n,
                "col": c,
                "pos": pos,
                "neg": [r for r in cands if r != pos],
                "feats": feats,
            }
        )
        st.place(pos)
        remaining.discard(pos)
    if any(st.col_active):
        raise ReplayError("cover consumed but active columns remain")
    return out


def dump_features(inst: dict, cover_row_ids, fh, post_cover: bool = False) -> int:
    """Write the parity trace: `NODE k col=c` + one line per candidate."""
    recs = replay(inst, cover_row_ids, "parity", post_cover=post_cover)
    for k, rec in enumerate(recs):
        fh.write(f"NODE {k} col={rec['col']}\n")
        for rid in sorted(rec["feats"]):
            vals = " ".join("%.6f" % v for v in rec["feats"][rid])
            fh.write(f"{rid} {vals}\n")
    return len(recs)


# --------------------------------------------------------- cover sources


def _row_id_map(inst: dict) -> dict:
    return {(r["loop"], r["entry"]): i for i, r in enumerate(inst["rows"])}


def cert_row_ids(inst: dict, cert: dict) -> list:
    """Map certificate rows onto instance row ids (None if a row is absent)."""
    rid = _row_id_map(inst)
    n = inst["n"]
    return [
        rid.get((parse_loop(r["loop"], n), r["entry_perm"])) for r in cert["rows"]
    ]


def n6_word_files() -> list:
    """The n=6 record words, in sorted path order (non-word files filtered)."""
    fs = sorted(
        glob.glob(os.path.join(REPO, "data", "records872", "*.txt"))
        + glob.glob(os.path.join(REPO, "data", "gain1_872s", "*.txt"))
    )
    out = []
    for f in fs:
        s = open(f).read().strip()
        if len(s) == 872 and set(s) <= set("123456"):
            out.append((f, s))
    return out


def n6_covers(inst: dict, verbose: bool = False) -> tuple[list, dict]:
    """(path, sorted row ids) for every record word whose cert covers `inst`."""
    kern = [format_loop(l) for l in inst["kernel"]]
    covers, stats = [], {
        "files": 0,
        "extract_fail": 0,
        "kernel_mismatch": 0,
        "map_fail": 0,
        "check_cover_fail": 0,
    }
    for path, word in n6_word_files():
        stats["files"] += 1
        try:
            cert = extract_certificate(word, 6)
        except Exception:
            stats["extract_fail"] += 1
            continue
        if cert["kernel_loops"] != kern:
            stats["kernel_mismatch"] += 1
            continue
        ids = cert_row_ids(inst, cert)
        if any(i is None for i in ids):
            stats["map_fail"] += 1
            continue
        chosen = [inst["rows"][i] for i in ids]
        if not gain1.check_cover(inst, chosen)["valid"]:
            stats["check_cover_fail"] += 1
            continue
        covers.append((path, sorted(ids)))
    stats["ok"] = len(covers)
    return covers, stats


# --------------------------------------------------------------- corpora


def _write_jsonl(recs, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r, separators=(",", ":")) + "\n")


def _pair_counts(recs) -> tuple[int, int]:
    return len(recs), sum(len(r["neg"]) for r in recs)


def build_corpus_n6(out_dir: str) -> dict:
    inst = n6_standard()
    covers, stats = n6_covers(inst)
    recs, bad = [], 0
    for path, ids in covers:
        tag = "n6std/" + os.path.basename(path)[:-4]
        try:
            recs.extend(replay(inst, ids, tag))
        except ReplayError as exc:
            bad += 1
            print(f"  replay FAIL {tag}: {exc}", file=sys.stderr)
    path = os.path.join(out_dir, "corpus_n6.jsonl")
    _write_jsonl(recs, path)
    d, p = _pair_counts(recs)
    return {
        "file": path, "certs": len(covers), "replay_fail": bad,
        "decisions": d, "pairs": p, "gate": stats,
    }


def build_corpus_5907(out_dir: str) -> dict:
    inst = n7_standard()
    recs, used, bad = [], 0, []
    for cp in cert5907_paths():
        cert = json.load(open(cp))
        ids = cert_row_ids(inst, cert)
        name = os.path.basename(cp)[:-5]
        if any(i is None for i in ids):
            bad.append((name, "row not in instance"))
            continue
        if not gain1.check_cover(inst, [inst["rows"][i] for i in ids])["valid"]:
            bad.append((name, "check_cover invalid"))
            continue
        try:
            recs.extend(replay(inst, sorted(ids), f"n7std/{name}"))
            used += 1
        except ReplayError as exc:
            bad.append((name, str(exc)))
    path = os.path.join(out_dir, "corpus_5907.jsonl")
    _write_jsonl(recs, path)
    d, p = _pair_counts(recs)
    return {"file": path, "certs": used, "failed": bad, "decisions": d, "pairs": p}


def build_corpus_5906(out_dir: str) -> dict:
    fams, fam_fail = chain5906_families()
    recs, used, bad = [], 0, list(fam_fail)
    for cp in cert5906_paths():
        fam = cert_family(cp)
        if fam not in fams:
            bad.append((os.path.basename(cp), "family instance unavailable"))
            continue
        inst = fams[fam][0]
        cert = json.load(open(cp))
        ids = cert_row_ids(inst, cert)
        name = os.path.basename(cp)[:-5]
        if any(i is None for i in ids):
            bad.append((name, "row not in instance"))
            continue
        if not gain1.check_cover(inst, [inst["rows"][i] for i in ids])["valid"]:
            bad.append((name, "check_cover invalid"))
            continue
        try:
            recs.extend(replay(inst, sorted(ids), f"c5906_{fam}/{name}"))
            used += 1
        except ReplayError as exc:
            bad.append((name, str(exc)))
    path = os.path.join(out_dir, "corpus_5906.jsonl")
    _write_jsonl(recs, path)
    d, p = _pair_counts(recs)
    return {"file": path, "certs": used, "failed": bad, "decisions": d, "pairs": p}


def build_parity(out_dir: str, post_cover: bool = False) -> dict:
    inst = n6_standard()
    covers, _ = n6_covers(inst)
    if not covers:
        raise SystemExit("no n=6 cover available for the parity artifact")
    path, ids = covers[0]
    pdir = os.path.join(out_dir, "parity")
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "cover_rows.txt"), "w") as fh:
        fh.write("\n".join(str(i) for i in ids) + "\n")
    trace = os.path.join(pdir, "parity_py.txt")
    with open(trace, "w") as fh:
        nodes = dump_features(inst, ids, fh)
    # diagnostic-only second timing, in case the C engine scores post-cover(c)
    with open(os.path.join(pdir, "parity_py_postcover.txt"), "w") as fh:
        dump_features(inst, ids, fh, post_cover=True)
    with open(os.path.join(pdir, "parity.meta.json"), "w") as fh:
        json.dump(
            {
                "instance": "n6std",
                "source_word": os.path.relpath(path, REPO),
                "rows": len(ids),
                "nodes": nodes,
                "feature_order": FEATURE_ORDER,
                "format": "NODE <k> col=<c> then '<rowid> f1..f8' (%.6f), "
                          "candidates ascending by row id",
                "feature_timing": "before cover(c)",
            },
            fh,
            indent=1,
        )
        fh.write("\n")
    return {"cover": path, "rows": len(ids), "nodes": nodes, "trace": trace}


def build_sample(out_dir: str, lines: int = 200) -> str:
    """A committed 200-line slice of the n=6 corpus."""
    src = os.path.join(out_dir, "corpus_n6.jsonl")
    dst = os.path.join(out_dir, "corpus_sample.jsonl")
    with open(src) as fh, open(dst, "w") as out:
        for i, line in enumerate(fh):
            if i >= lines:
                break
            out.write(line)
    return dst


# ------------------------------------------------------------------ main


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["corpus", "parity", "all"], nargs="?",
                    default="all")
    ap.add_argument("--out", default=DATA)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    if args.cmd in ("corpus", "all"):
        r6 = build_corpus_n6(args.out)
        g = r6["gate"]
        print(f"corpus_n6    certs={r6['certs']}/{g['files']} "
              f"decisions={r6['decisions']} pairs={r6['pairs']}")
        print(f"  GATE(b) extract_fail={g['extract_fail']} "
              f"kernel_mismatch={g['kernel_mismatch']} map_fail={g['map_fail']} "
              f"check_cover_fail={g['check_cover_fail']} "
              f"replay_fail={r6['replay_fail']}")
        r7 = build_corpus_5907(args.out)
        print(f"corpus_5907  certs={r7['certs']}/3 decisions={r7['decisions']} "
              f"pairs={r7['pairs']} failed={r7['failed']}")
        r6b = build_corpus_5906(args.out)
        print(f"corpus_5906  certs={r6b['certs']}/{len(cert5906_paths())} "
              f"decisions={r6b['decisions']} pairs={r6b['pairs']} "
              f"failed={r6b['failed']}")
        print(f"TOTAL decisions={r6['decisions']+r7['decisions']+r6b['decisions']} "
              f"pairs={r6['pairs']+r7['pairs']+r6b['pairs']}")
        print("sample ->", build_sample(args.out))

    if args.cmd in ("parity", "all"):
        rp = build_parity(args.out)
        print(f"parity: {rp['nodes']} nodes, {rp['rows']} rows, "
              f"cover={os.path.relpath(rp['cover'], REPO)}")
        print(f"  GATE(d) {'OK' if rp['nodes'] == 25 else 'FAIL'} "
              f"({rp['nodes']} NODE blocks)")


if __name__ == "__main__":
    main()
