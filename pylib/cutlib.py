#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s60/nogood/cutlib.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# Divergence from the original: REPO/path block rebased for pylib/
# (see below); logic verbatim.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s60 no-good (cut) harvest -- shared library.

A CUT is a set S of instance row ids such that NO cover of the instance
contains all of S.  It is produced by the s59 refutation lane:

    render(S)   -> the residual DLX instance after fixing S
                   (S's children columns deleted, rows conflicting with S
                    deleted, rows whose parent orbit S covered re-rooted)
    dlx7g rc 2  -> that residual tree was EXHAUSTED

Soundness of the direction we use.  If a cover C of the instance had C >= S,
then C\\S covers exactly the residual columns, uses only rows alive after S
(no shared loop, no shared column), and every row of C\\S has its parent
orbit covered either by S (=> a root in the residual) or by another row of
C\\S (=> a residual column).  So C\\S would be a solution of the residual
instance.  rc 2 = the residual has no solution => no such C.  QED.

The reverse direction (residual SAT => a cover exists) is NOT claimed and is
not used: S itself need not be walk-order groundable.  That asymmetry is why
rc 2 is sound here even for row sets that are not legal walk prefixes.

LANE (HANDOFF-S59 trap): every check run by this module goes through
dlxrun.run(..., epsilon=0.0), and dlxrun only appends `--epsilon/--seed`
when epsilon is truthy -- so dlx7g runs with NO randomization flags at all:
deterministic, no restarts, plain rc 2 = exhaustion.  Nothing here is ever
recorded as a cut from an epsilon>0 run.

rc 3 (timeout) and rc 0 (SAT) are NEVER cuts.  A timeout is not a cut.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# s64 P1 import-mechanics divergence: pylib/ sits directly under the repo
# root, so REPO is one level up (the out/ original was three levels down).
REPO = os.path.dirname(HERE)
S59 = os.path.join(REPO, "out", "s59", "prefix")
sys.path.insert(0, S59)
sys.path.insert(0, HERE)     # s64 P1: promoted chain7/dlxrun copies

import prefixlib as L      # noqa: E402  (also fixes sys.path for the rest)
import chain7              # noqa: E402
import dlxrun              # noqa: E402

SCRATCH = os.environ.get(
    "S60_SCRATCH",
    "/private/tmp/claude-501/-Users-andrew-Documents-code-math-superperms/"
    "a499da61-89c9-40cc-a9d2-9b4410a75ea3/scratchpad")
os.makedirs(SCRATCH, exist_ok=True)

_POS = None


def positives():
    global _POS
    if _POS is None:
        _POS = pickle.load(open(os.path.join(S59, "positives.pkl"), "rb"))
    return _POS


def load(spec):
    """Same instance objects the s59 proposer used.

    farm*      : s57's SOUND pruning applied (alive/fixed from prune_all.json)
    ctrlgroup* : the RAW instance, no pruning (alive = all rows, fixed = [])
    """
    if spec.startswith("ctrlgroup"):
        P = positives()[spec]
        inst = chain7.build_instance_from_chain([tuple(x) for x in P["chain"]])
        return dict(spec=spec, inst=inst, alive=set(range(len(inst["rows"]))),
                    fixed=[], covers=[c["known"] for c in P["covers"]])
    d = L.load_farm(int(spec[4:]))
    return dict(spec=spec, inst=d["inst"], alive=set(d["alive"]),
                fixed=list(d["fixed"]), covers=None)


def base_state(D):
    return L.State(D["inst"], D["alive"], D["fixed"])


def state_for(D, rows):
    """State after fixing exactly `rows` on top of the base.  take() is
    order-independent for (covered, usedloops, alive), so this reproduces the
    DFS state that generated a refutation bit-for-bit."""
    st = base_state(D)
    for i in rows:
        st.take(i)
    return st


def base_fingerprint(D):
    st = base_state(D)
    txt, _, nc, nr = L.render(D["inst"], st)
    return dict(sha256=hashlib.sha256(txt.encode()).hexdigest(), cols=nc,
                rows=nr, n_fixed=len(D["fixed"]), n_alive=len(D["alive"]))


def check(D, rows, cap, tag):
    """The one and only refutation check.  Deterministic (epsilon=0).

    Returns dict(verdict in SAT/UNSAT/UNKNOWN/ERROR*, seconds, cols, rows,
                 sol_rows).  UNSAT == rc 2 == EXHAUSTED == a sound refutation
    of `rows`.  Anything else is NOT a refutation.
    """
    st = state_for(D, rows)
    txt, rowmap, nc, nr = L.render(D["inst"], st)
    r = dlxrun.run(txt, cap, None, tag, SCRATCH, epsilon=0.0)
    sol = None
    if r["verdict"] == "SAT":
        sol = list(rows) + [rowmap[k] for k in r["rows"]]
    return dict(verdict=r["verdict"], seconds=r["seconds"], cols=nc, rows=nr,
                rc=r["rc"], sol_rows=sol)


def minimize(D, rows0, cap, tag, time_budget=15.0):
    """One deletion pass -> a set that is 1-minimal w.r.t. the capped check.

    Contract (NOVELTY-DESIGN 6.1): a drop is kept ONLY on rc 2 within the
    cap.  rc 3 (timeout) or rc 0 keeps the row.  A timeout is never a cut.
    """
    cur = list(rows0)
    steps = kept = 0
    solver_s = 0.0
    trunc = False
    t0 = time.monotonic()
    for e in list(rows0):
        if len(cur) <= 1:
            break
        if time.monotonic() - t0 > time_budget:
            trunc = True
            break
        trial = [x for x in cur if x != e]
        r = check(D, trial, cap, tag)
        steps += 1
        solver_s += r["seconds"]
        if r["verdict"] == "UNSAT":
            cur = trial
            kept += 1
    return dict(cut=sorted(cur), steps=steps, drops=kept,
                solver_s=round(solver_s, 3), truncated=trunc,
                minim_s=round(time.monotonic() - t0, 3))


class Store:
    """Exact-dedup cut store with a min-element index for subset queries."""

    def __init__(self):
        self.cuts = []          # list of frozenset
        self.exact = set()      # the same, for O(1) exact dedup
        self.byminel = {}       # min row id -> [cut index]

    def __len__(self):
        return len(self.cuts)

    def has(self, s):
        return frozenset(s) in self.exact

    def add(self, s):
        f = frozenset(s)
        if f in self.exact:
            return False
        self.exact.add(f)
        self.cuts.append(f)
        self.byminel.setdefault(min(f), []).append(len(self.cuts) - 1)
        return True

    def hit(self, rowset):
        """Return the index of a stored cut that is a SUBSET of rowset, else
        None.  Sound pruning: rowset extends a refuted set => refuted."""
        rs = set(rowset)
        for r in rs:
            for k in self.byminel.get(r, ()):
                if self.cuts[k] <= rs:
                    return k
        return None


def load_cuts(path):
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("kind") == "cut":
            out.append(rec)
    return out
