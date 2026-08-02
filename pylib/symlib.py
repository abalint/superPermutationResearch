#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s60/retrieval/symlib.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# Divergence from the original: REPO/path block rebased for pylib/
# (see below); logic verbatim.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s60 prefix-RETRIEVAL probe -- symmetry library.

Frame (chain7 / certificate.py, n=7):
  orbit  = cyclic-rotation class of a 7-perm string  (720 of them; the
           canonical representative is the lexicographically minimal
           rotation, hence always starts with '1')
  loop   = (pivot symbol a, canonical rotation of the other 6 symbols)
           (840 of them); its six entries are e, tv(e), ... with
           tv(w) = w[1:-1] + w[0] + w[-1]; loop_orbits(loop) = the six
           orbits of those entries.
  row    = an oriented ride of a non-kernel loop that covers five of its
           six orbits; equivalently the PAIR (loop, parent_orbit) where
           parent_orbit is the one orbit of the loop the row does NOT
           cover (children = loop_orbits(loop) \\ {parent_orbit}).
           There are exactly 840*6 = 5040 such pairs.

Symmetry group  G = S7 x {1, rev}  (order 10080):
  sigma in S7 acts by renaming symbols.  Renaming is positional-op-blind,
  so it commutes with tv and with canonical_rotation: it maps orbits to
  orbits and loops to loops.
  rev acts by reversing the string.  rev(X + a) = a + rev(X) ~ rev(X) + a
  as a cyclic class, and rev(rot^i(X)) = rot^-i(rev(X)), so rev maps the
  orbit set of loop (a, C) onto the orbit set of loop (a, canon(rev(C))):
  rev too maps orbits to orbits and loops to loops.
  sigma and rev commute, so G = S7 x {1,rev} as a direct product and any
  g in G is (sigma, eps) acting on orbits/loops by composed lookup maps.

Because rows are the pairs (loop, orbit-of-that-loop), G acts on the 5040
rows.  |G| = 5040 = number of rows; the action turns out to be SIMPLY
TRANSITIVE (verified in check_group.py) -- i.e. for ANY two rows there is
exactly one g carrying one to the other.  Row-level conjugacy alone is
therefore vacuous; all content is in the CHAIN-relative condition.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# s64 P1 import-mechanics divergence: pylib/ sits directly under the repo
# root, so REPO is one level up (the out/ original was three levels down).
REPO = os.path.dirname(HERE)
for _p in (HERE,                            # promoted chain7/dlxrun copies
           os.path.join(REPO, "out", "s59", "prefix"),
           os.path.join(REPO, "out", "s57", "proposer"),
           os.path.join(REPO, "out", "s56", "p1a"),
           os.path.join(REPO, "analysis", "cover7"),
           os.path.join(REPO, "..", "extraDocs",
                        "superpermutation-examples", "scripts")):
    sys.path.insert(0, _p)

import chain7                        # noqa: E402
from certificate import canonical_rotation  # noqa: E402
from itertools import permutations   # noqa: E402

ALPHA = "1234567"
CACHE = os.path.join(HERE, "maps.npz")

# ---------------------------------------------------------------- universes
ORBITS = sorted(chain7.ALL_ORBITS)                 # 720 canonical strings
OID = {o: i for i, o in enumerate(ORBITS)}
LOOPS = chain7.loops                               # 840 (pivot, necklace)
LID = chain7.li
NORB, NLOOP = len(ORBITS), len(LOOPS)
assert (NORB, NLOOP) == (720, 840)

# loop id -> its 6 orbit ids
LOOP_ORBS = np.array([[OID[o] for o in sorted(chain7.orbitsets[L])]
                      for L in range(NLOOP)], dtype=np.int32)

SIGMAS = ["".join(p) for p in permutations(ALPHA)]  # 5040 relabelings


def rowkey(loop_id, orbit_id):
    """Canonical integer id of the row (loop, parent_orbit)."""
    return loop_id * NORB + orbit_id


NKEY = NLOOP * NORB


def _build():
    """OMAP[s] : orbit id -> orbit id under sigma s ; LMAP[s] likewise.
    REV_O / REV_L : the reversal maps."""
    omap = np.zeros((len(SIGMAS), NORB), dtype=np.int32)
    lmap = np.zeros((len(SIGMAS), NLOOP), dtype=np.int32)
    for si, s in enumerate(SIGMAS):
        tr = str.maketrans(ALPHA, s)
        for oi, o in enumerate(ORBITS):
            omap[si, oi] = OID[canonical_rotation(o.translate(tr))]
        for li_, (a, C) in enumerate(LOOPS):
            lmap[si, li_] = LID[(a.translate(tr),
                                 canonical_rotation(C.translate(tr)))]
    rev_o = np.zeros(NORB, dtype=np.int32)
    for oi, o in enumerate(ORBITS):
        rev_o[oi] = OID[canonical_rotation(o[::-1])]
    rev_l = np.zeros(NLOOP, dtype=np.int32)
    for li_, (a, C) in enumerate(LOOPS):
        rev_l[li_] = LID[(a, canonical_rotation(C[::-1]))]
    return omap, lmap, rev_o, rev_l


def maps():
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        return z["omap"], z["lmap"], z["rev_o"], z["rev_l"]
    omap, lmap, rev_o, rev_l = _build()
    np.savez_compressed(CACHE, omap=omap, lmap=lmap, rev_o=rev_o, rev_l=rev_l)
    return omap, lmap, rev_o, rev_l


class Group:
    """The 10080 elements of G, as orbit/loop lookup tables.

    Element index e = si (identity part) for e < 5040, and
    e = 5040 + si (sigma o rev) for e >= 5040.
    """

    def __init__(self):
        self.omap, self.lmap, self.rev_o, self.rev_l = maps()
        self.n = 2 * len(SIGMAS)

    def label(self, e):
        si = e % len(SIGMAS)
        return ("rev*" if e >= len(SIGMAS) else "") + SIGMAS[si]

    def o(self, e):
        si = e % len(SIGMAS)
        m = self.omap[si]
        return m if e < len(SIGMAS) else m[self.rev_o]

    def l(self, e):
        si = e % len(SIGMAS)
        m = self.lmap[si]
        return m if e < len(SIGMAS) else m[self.rev_l]


# ---------------------------------------------------------------- instances
def inst_struct(inst, alive=None, fixed=None):
    """Everything the retrieval needs about one chain instance."""
    rows = inst["rows"]
    lids = np.array([LID[r["loop"]] for r in rows], dtype=np.int32)
    pids = np.array([OID[r["parent_orbit"]] for r in rows], dtype=np.int32)
    keys = lids * NORB + pids
    assert len(set(keys.tolist())) == len(rows), "row <-> (loop,parent) not 1-1"
    d = dict(inst=inst, rows=rows, lids=lids, pids=pids, keys=keys,
             roots=np.array(sorted(OID[o] for o in inst["roots"]), np.int32),
             kernel=np.array(sorted(LID[lp] for lp in inst["kernel"]), np.int32),
             R=inst["meta"]["R"], nrows=len(rows))
    d["rowid_of_key"] = {int(k): i for i, k in enumerate(keys)}
    inrows = np.zeros(NKEY, dtype=bool)
    inrows[keys] = True
    d["inrows"] = inrows
    if alive is not None:
        al = np.zeros(NKEY, dtype=bool)
        al[keys[sorted(alive)]] = True
        d["inalive"] = al
        d["alive"] = sorted(alive)
    else:
        d["inalive"] = inrows
        d["alive"] = list(range(len(rows)))
    d["fixed"] = list(fixed or [])
    return d


# ----------------------------------------------------- exact completion
NODE_CAP = 2_000_000


def exact_cover(cols, rows):
    """rows = list of frozensets of column ids; exact cover of `cols`.
    Returns (status, solution, nodes), status 'SAT' | 'UNSAT' | 'CAP'."""
    colrows = {c: [] for c in cols}
    for i, r in enumerate(rows):
        for c in r:
            colrows[c].append(i)
    nodes = [0]
    sol = []

    def rec(rem):
        nodes[0] += 1
        if nodes[0] > NODE_CAP:
            return "CAP"
        if not rem:
            return "SAT"
        c = min(rem, key=lambda c: sum(1 for i in colrows[c]
                                       if rows[i] <= rem))
        cands = [i for i in colrows[c] if rows[i] <= rem]
        if not cands:
            return "UNSAT"
        capped = False
        for i in cands:
            sol.append(i)
            st = rec(rem - rows[i])
            if st == "SAT":
                return "SAT"
            if st == "CAP":
                capped = True
            sol.pop()
        return "CAP" if capped else "UNSAT"

    st = rec(frozenset(cols))
    return st, (list(sol) if st == "SAT" else None), nodes[0]


