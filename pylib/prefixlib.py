#!/usr/bin/env python3
# --- PROVENANCE (s64 P1b, 2026-08-02) -------------------------------
# Promoted BY COPY from out/s59/prefix/prefixlib.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# Divergence from the original: REPO/path block rebased for pylib/
# (see below); logic verbatim.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s59 walk-order prefix proposer -- core library.

The object.  A loop-cover DLX instance for one n=7 chain has ~2500-3200 rows
and R ~ 112-138 of them form a cover.  A cover is *walk-ordered*: row t's
`parent_orbit` is either a chain root or a child (covered orbit) of an earlier
row.  s57 measured that fixing the first m ~ 25-30 rows of the walk order
collapses the residual instance to <=3xR and makes it SAT in ~1 s.

This module proposes such prefixes sequentially.  A proposal is a legal
walk-order prefix (grounded + conflict-free at every step); each completed
proposal is handed to dlx7g with a wall cap.

Three-valued discipline (s57 trap f).  Completion runs here use the WITNESS
lane (--epsilon > 0, randomized restarts).  In that lane dlx7g can return a
solution but its exhaustion verdict is meaningless, so:
    rc 0 (SAT)                -> SAT      (a real witness; validate it)
    rc 2 (EXHAUSTED) / rc 3   -> UNKNOWN  (never reported as UNSAT)
Only propagate()'s P1 rule (a column no alive row can cover) is a sound
refutation, and it refutes only the current PREFIX, never the chain.
"""
from __future__ import annotations

import json
import os
import pickle
import random
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
# s64 P1b import-mechanics divergence: pylib/ sits directly under the repo
# root, so REPO is one level up (the out/ original was three levels down).
# chain7/dlxrun/p1a_assume are promoted siblings in pylib/ (HERE inserted
# last so they win); certificate/gain1 stay external in ../extraDocs.
REPO = os.path.dirname(HERE)
# Data artifacts (controls.pkl, prune_all.json) remain in frozen out/ --
# S57 is kept as a DATA path only, no longer on sys.path.
S57 = os.path.join(REPO, "out", "s57", "proposer")
for _p in (os.path.join(REPO, "analysis", "cover7"),
           os.path.join(REPO, "..", "extraDocs",
                        "superpermutation-examples", "scripts"),
           HERE):
    sys.path.insert(0, _p)

import chain7            # noqa: E402
import p1a_assume as P   # noqa: E402
import dlxrun            # noqa: E402

FARM = os.path.join(REPO, "analysis", "farm", "farm_chains.jsonl")
PRUNE_ALL = os.path.join(S57, "prune_all.json")


# --------------------------------------------------------------- instances
def control_groups():
    """The nine control chains, as lists of control dicts, biggest first."""
    data = pickle.load(open(os.path.join(S57, "controls.pkl"), "rb"))
    g = defaultdict(list)
    for d in data:
        g[tuple(sorted(x[0] for x in d["chain"]))].append(d)
    return [v for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))]


def load_control(path):
    ex = P.extract(path)
    inst = ex["inst"]
    return dict(inst=inst, ex=ex, known=ex["known_rows"],
                alive=set(range(len(inst["rows"]))), fixed=[], tag=os.path.basename(path))


def load_farm(idx):
    """Open chain #idx with s57's SOUND pruning applied (prune_all.json)."""
    ch = [json.loads(l) for l in open(FARM)][idx]
    sol = [tuple(x) for x in ch["chain"]]
    inst = chain7.build_instance_from_chain(sol)
    pa = json.load(open(PRUNE_ALL))[f"farm{idx}"]
    return dict(inst=inst, ex=None, known=None,
                alive=set(pa["alive"]), fixed=list(pa["fixed"]), tag=f"farm{idx}")


# ------------------------------------------------------------------- state
class State:
    """A partial walk-order prefix over one instance."""

    def __init__(self, inst, alive, fixed):
        self.inst = inst
        self.rows = inst["rows"]
        self.alive = set(alive)
        self.fixed = []
        self.covered = set(inst["roots"])
        self.usedloops = set()
        self.tcover = {c: -1 for c in self.covered}
        self.step = 0
        self.forced = 0
        for i in fixed:                      # s57's provably-in-every-cover rows
            self.take(i, forced=True)

    def clone(self):
        s = State.__new__(State)
        s.inst, s.rows = self.inst, self.rows
        s.alive = set(self.alive)
        s.fixed = list(self.fixed)
        s.covered = set(self.covered)
        s.usedloops = set(self.usedloops)
        s.tcover = dict(self.tcover)
        s.step, s.forced = self.step, self.forced
        return s

    def take(self, i, forced=False):
        r = self.rows[i]
        self.fixed.append(i)
        self.alive.discard(i)
        for c in r["children"]:
            self.covered.add(c)
            self.tcover[c] = self.step
        self.usedloops.add(r["loop"])
        self.step += 1
        if forced:
            self.forced += 1
        # kill everything now in conflict
        dead = [j for j in self.alive
                if self.rows[j]["loop"] in self.usedloops
                or any(c in self.covered for c in self.rows[j]["children"])]
        self.alive.difference_update(dead)

    def frontier(self):
        """Alive rows that are grounded now (parent orbit already covered)."""
        return [i for i in self.alive
                if self.rows[i]["parent_orbit"] in self.covered]

    def open_cols(self):
        return [c for c in self.inst["columns"] if c not in self.covered]

    def col_index(self):
        """uncovered column -> alive rows covering it (grounding ignored:
        a row may become grounded later, so this is a RELAXATION and its
        emptiness verdict is sound)."""
        ci = defaultdict(list)
        for i in self.alive:
            for c in self.rows[i]["children"]:
                if c not in self.covered:
                    ci[c].append(i)
        return ci

    def propagate(self, max_units=64):
        """P1 (zero column -> prefix is dead) + P2 (unit column -> forced row).

        Returns 'ok' | 'DEAD'.  DEAD refutes THIS PREFIX only (sound: the
        column relaxation ignores grounding, so no cover extending this
        prefix exists).
        """
        for _ in range(max_units):
            ci = self.col_index()
            for c in self.open_cols():
                if not ci.get(c):
                    return "DEAD"
            units = [ci[c][0] for c in self.open_cols() if len(ci[c]) == 1]
            units = sorted(set(units))
            if not units:
                return "ok"
            i = units[0]
            if self.rows[i]["parent_orbit"] not in self.covered:
                # forced but not yet grounded -- it will be, later; taking it
                # out of walk order would break the reduction, so stop here.
                return "ok"
            self.take(i, forced=True)
        return "ok"


# ------------------------------------------------------------------ scoring
def score_candidates(st, cands, w):
    """Instance-intrinsic scores.  Higher = proposed earlier.

    f_recency  how recently the candidate's parent orbit was covered
               (corpus law: real walks are strongly DFS-local, see REPORT S3)
    f_scarce   -min over the row's children of that column's alive-row count
               (MRV: prefer rows that consume scarce columns)
    f_loopdeg  -number of alive rows sharing the candidate's loop
    f_damage   -number of alive rows the candidate would kill
    """
    ci = st.col_index()
    loopdeg = defaultdict(int)
    for i in st.alive:
        loopdeg[st.rows[i]["loop"]] += 1
    colrows = {c: len(v) for c, v in ci.items()}
    out = []
    for i in cands:
        r = st.rows[i]
        rec = st.tcover.get(r["parent_orbit"], -1)
        scarce = min(colrows.get(c, 0) for c in r["children"])
        dmg = 0
        for c in r["children"]:
            dmg += colrows.get(c, 0)
        s = (w["recency"] * (rec + 1) / max(st.step, 1)
             - w["scarce"] * scarce / 20.0
             - w["loopdeg"] * loopdeg[r["loop"]] / 6.0
             - w["damage"] * dmg / 100.0)
        out.append((s, i))
    return out


DEFAULT_W = dict(recency=3.0, scarce=1.0, loopdeg=0.5, damage=0.3)


def propose_prefix(inst, alive0, fixed0, m, rng, w=None, mode="score",
                   temp=1.0, max_backtrack=200):
    """Build ONE legal walk-order prefix of length m (counting from fixed0).

    mode 'score'  : softmax sampling over the feature score (the proposer)
    mode 'random' : uniform over the legal frontier (the chance baseline)
    Returns (State, status) with status 'ok' | 'DEAD' | 'STUCK'.
    """
    w = w or DEFAULT_W
    st = State(inst, alive0, fixed0)
    if st.propagate() == "DEAD":
        return st, "DEAD"
    bt = 0
    trail = []          # (state_clone, remaining candidate ids)
    while len(st.fixed) < m + len(fixed0):
        cands = st.frontier()
        if not cands:
            status = "STUCK"
        else:
            if mode == "random":
                order = list(cands)
                rng.shuffle(order)
            else:
                sc = score_candidates(st, cands, w)
                mx = max(s for s, _ in sc)
                weights = [pow(2.718281828, (s - mx) / max(temp, 1e-6)) for s, _ in sc]
                order = []
                pool = list(zip(weights, [i for _, i in sc]))
                while pool:
                    tot = sum(x[0] for x in pool)
                    if tot <= 0:
                        rng.shuffle(pool)
                        order += [i for _, i in pool]
                        break
                    x = rng.random() * tot
                    acc = 0.0
                    for k, (wt, i) in enumerate(pool):
                        acc += wt
                        if acc >= x:
                            order.append(i)
                            pool.pop(k)
                            break
                    else:
                        order.append(pool[-1][1])
                        pool.pop()
            status = "ok"
        if status == "ok":
            trail.append((st.clone(), order))
            st2 = st.clone()
            st2.take(order[0])
            trail[-1] = (trail[-1][0], order[1:])
            if st2.propagate() == "DEAD":
                status = "DEAD"
            else:
                st = st2
                continue
        # backtrack
        while trail and not trail[-1][1]:
            trail.pop()
        if not trail or bt >= max_backtrack:
            return st, ("DEAD" if status == "DEAD" else "STUCK")
        bt += 1
        base, rest = trail[-1]
        st2 = base.clone()
        st2.take(rest[0])
        trail[-1] = (base, rest[1:])
        if st2.propagate() != "DEAD":
            st = st2
    return st, "ok"


# --------------------------------------------------------------- completion
def render(inst, st):
    """dlx7g instance text for the residual after this prefix."""
    rows = inst["rows"]
    dead_cols = set()
    for i in st.fixed:
        dead_cols.update(rows[i]["children"])
    cols = [c for c in inst["columns"] if c not in dead_cols]
    roots = set(inst["roots"]) | dead_cols
    keep, rowmap = [], []
    for i in sorted(st.alive):
        keep.append(rows[i])
        rowmap.append(i)
    return P.instance_text(cols, keep, roots), rowmap, len(cols), len(keep)


def complete(inst, st, cap_s, tag, outdir, epsilon=0.15, seed=0):
    """Capped completion in the WITNESS lane.  Returns dict with a
    three-valued verdict where the only non-UNKNOWN outcome is SAT."""
    txt, rowmap, nc, nr = render(inst, st)
    r = dlxrun.run(txt, cap_s, None, tag, outdir, epsilon=epsilon, seed=seed)
    v = "SAT" if r["verdict"] == "SAT" else "UNKNOWN"
    full = list(st.fixed) + [rowmap[k] for k in r["rows"]] if r["rows"] else None
    return dict(verdict=v, raw=r["verdict"], seconds=r["seconds"],
                cols=nc, rows=nr, full_rows=full)
