#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s61/anatomy/anatlib.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# Divergence from the original: REPO/path block rebased for pylib/
# (see below); logic verbatim.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s61 near-miss residual ANATOMY -- shared helpers.

Everything here sits on top of the VALIDATED s60 machinery
(`out/s60/retrieval/symlib.py`): the G = S7 x {1,rev} action, the instance
structs (byte-identical to s57's committed instances), and the node-capped
exact-cover DFS.  Nothing is re-implemented; symlib is imported.

The one piece of new geometry (derived in REPORT.md sec.2, verified in
geom.py):

    A row of instance(B) is the pair (loop L, parent orbit p) with
    children = orbits(L) \\ {p}; it is a row of B iff L is not a kernel
    loop of B and all five children are columns of B.

    Hence, for any residual column set S (S subset of columns(B)), the
    rows of B that fit entirely inside S are exactly

        { (L,p) : L non-kernel, |orbits(L) cap S| >= 5, orbits(L)\\{p} <= S }

    so with  m_L = |orbits(L) cap S|  over non-kernel loops L,

        #candidate rows(S) = #{L : m_L = 5} + 6 * #{L : m_L = 6}          (*)

    and, since two rows of the same loop share >= 4 orbits and can never be
    disjoint, a residual of |S| = 5t columns can only be exact-covered if

        #{L non-kernel : m_L >= 5} >= t                                   (**)

(*) is the "0 candidates" phenomenon in closed form; (**) is the counting
bound examined in sec.6 of the report.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from fractions import Fraction
from math import comb

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# s64 P1 import-mechanics divergence: pylib/ sits directly under the repo
# root, so REPO is one level up (the out/ original was three levels down).
REPO = os.path.dirname(HERE)
RETR = os.path.join(REPO, "out", "s60", "retrieval")
# s64 P1b: prefixlib is a promoted sibling; PREFIX kept as DATA path only
# (positives.pkl is a regenerable out/ artifact, not code).
PREFIX = os.path.join(REPO, "out", "s59", "prefix")
for _p in (RETR, HERE):   # s64 P1: HERE = promoted symlib/chain7/prefixlib
    sys.path.insert(0, _p)

import symlib as S            # noqa: E402  (the validated s60 machinery)
import prefixlib as L         # noqa: E402
import chain7                 # noqa: E402

NLOOP, NORB = S.NLOOP, S.NORB
LOOP_ORBS = S.LOOP_ORBS       # (840, 6) orbit ids


# ------------------------------------------------------------------ loading
def positives():
    return pickle.load(open(os.path.join(PREFIX, "positives.pkl"), "rb"))


def ctrl_struct(tag, pos=None):
    pos = pos or positives()
    d = S.inst_struct(chain7.build_instance_from_chain(
        [tuple(x) for x in pos[tag]["chain"]]))
    d["tag"] = tag
    d["covers"] = [c["known"] for c in pos[tag]["covers"]]
    d["open"] = False
    _decorate(d)
    return d


def farm_struct(idx, pruned=False):
    f = L.load_farm(idx)
    d = S.inst_struct(f["inst"], alive=f["alive"], fixed=f["fixed"])
    d["tag"] = f"farm{idx}"
    d["covers"] = None
    d["open"] = True
    _decorate(d)
    return d


def census_struct(idx):
    """Any of the 223 census chains, by index in analysis/farm/farm_chains.jsonl."""
    ch = [json.loads(l) for l in
          open(os.path.join(REPO, "analysis", "farm", "farm_chains.jsonl"))][idx]
    d = S.inst_struct(chain7.build_instance_from_chain(
        [tuple(x) for x in ch["chain"]]))
    d["tag"] = f"farm{idx}"
    d["covers"] = None
    d["open"] = True
    _decorate(d)
    return d


def _decorate(d):
    """Add the column/kernel bitmaps and per-row child arrays used below."""
    cols = np.zeros(NORB, dtype=bool)
    for c in d["inst"]["columns"]:
        cols[S.OID[c]] = True
    d["colmask"] = cols
    d["cols"] = np.flatnonzero(cols)
    ker = np.zeros(NLOOP, dtype=bool)
    ker[d["kernel"]] = True
    d["kermask"] = ker
    d["nonkernel"] = np.flatnonzero(~ker)
    # per-row children as orbit ids
    d["children"] = np.array(
        [[S.OID[c] for c in r["children"]] for r in d["rows"]], dtype=np.int32)
    # a_L = |orbits(L) cap columns(B)| for every loop
    d["aL"] = cols[LOOP_ORBS].sum(1).astype(np.int32)
    return d


# -------------------------------------------------------------- the geometry
def mvec(Sset):
    """m_L = |orbits(L) cap S| for all 840 loops.  Sset: iterable of orbit ids."""
    inS = np.zeros(NORB, dtype=bool)
    inS[list(Sset)] = True
    return inS[LOOP_ORBS].sum(1).astype(np.int32)


def shatter(B, Sset):
    """Loop-shatter profile of residual column set S in instance B.

    Returns dict with the m-histogram over NON-KERNEL loops, the number of
    usable loops (m >= 5), the predicted candidate-row count via (*), and the
    same numbers restricted to kernel loops (which can never supply a row).
    """
    m = mvec(Sset)
    nk = ~B["kermask"]
    hist = np.bincount(m[nk], minlength=7)
    khist = np.bincount(m[B["kermask"]], minlength=7)
    usable = int(hist[5] + hist[6])
    cand = int(hist[5] + 6 * hist[6])
    return dict(n=len(set(Sset)), hist=[int(x) for x in hist],
                kernel_hist=[int(x) for x in khist],
                usable_loops=usable, cand_rows=cand,
                maxm=int(m[nk].max()) if nk.any() else 0,
                need=len(set(Sset)) // 5)


def cand_rows_bruteforce(B, Sset, pool=None):
    """Ground truth: rows of B (ids in `pool`, default all) whose 5 children
    all lie in S.  Used to validate (*)."""
    Sarr = np.zeros(NORB, dtype=bool)
    Sarr[list(Sset)] = True
    ok = Sarr[B["children"]].all(1)
    if pool is not None:
        keep = np.zeros(B["nrows"], dtype=bool)
        keep[list(pool)] = True
        ok &= keep
    return np.flatnonzero(ok)


# ------------------------------------------------------- the exact null model
def null_expect(B, k, exact=True):
    """EXACT expectation of the shatter statistics for a UNIFORM RANDOM
    k-subset S of columns(B).

    Distribution: for one loop L with a_L of its six orbits among the C
    columns, |orbits(L) cap S| is hypergeometric(C, a_L, k).  Expectations are
    sums over the 840-|kernel| non-kernel loops, so they are exact (linearity;
    no independence assumed).  Returns E[#loops with m=5], E[m=6],
    E[usable loops], E[#candidate rows], and Markov's exact bound
    P(>=1 candidate row) <= E[#candidate rows].
    """
    C = int(B["colmask"].sum())
    aL = B["aL"][B["nonkernel"]]
    tot = comb(C, k)
    e5 = Fraction(0)
    e6 = Fraction(0)
    for a in range(7):
        cnt = int((aL == a).sum())
        if not cnt:
            continue
        if a >= 5 and k >= 5:
            e5 += Fraction(cnt * comb(a, 5) * comb(C - a, k - 5), tot)
        if a == 6 and k >= 6:
            e6 += Fraction(cnt * comb(a, 6) * comb(C - a, k - 6), tot)
    # C(a,5)*C(C-a,k-5) already counts EXACTLY m=5: the k-5 remaining elements
    # are drawn from the C-a columns outside the loop, so the 6th orbit (when
    # a = 6) is excluded by construction.  Likewise C(C-6,k-6) is exactly m=6.
    e5_exact = e5
    cand = e5_exact + 6 * e6
    return dict(C=C, k=k, E_m5=float(e5_exact), E_m6=float(e6),
                E_usable=float(e5_exact + e6), E_cand=float(cand),
                P_any_le=float(min(Fraction(1), cand)))


def null_mc(B, k, trials, seed):
    """Monte-Carlo companion to null_expect (for the shape of the max-m and
    usable-loop distributions, which have no closed form).  Deterministic."""
    rng = np.random.default_rng(seed)
    cols = B["cols"]
    nk = ~B["kermask"]
    maxm = np.zeros(trials, dtype=np.int32)
    usable = np.zeros(trials, dtype=np.int32)
    cand = np.zeros(trials, dtype=np.int32)
    for t in range(trials):
        Ssub = rng.choice(cols, size=k, replace=False)
        inS = np.zeros(NORB, dtype=bool)
        inS[Ssub] = True
        m = inS[LOOP_ORBS].sum(1)[nk]
        maxm[t] = m.max()
        h = np.bincount(m, minlength=7)
        usable[t] = h[5] + h[6]
        cand[t] = h[5] + 6 * h[6]
    return dict(trials=trials, seed=seed,
                maxm_hist=[int(x) for x in np.bincount(maxm, minlength=7)],
                mean_usable=float(usable.mean()),
                mean_cand=float(cand.mean()),
                p_any_cand=float((cand > 0).mean()))


# --------------------------------------------------- foreign-mapped packings
def source_cover_machinery(A, G):
    """The s60 census apparatus: union of A's known cover rows and the
    10080 x |union| table of mapped row keys."""
    covers_A = A["covers"]
    union_A = sorted(set().union(*[set(c) for c in covers_A]))
    idx_of = {r: k for k, r in enumerate(union_A)}
    lids_u, pids_u = A["lids"][union_A], A["pids"][union_A]
    K = np.empty((G.n, len(union_A)), dtype=np.int64)
    for e in range(G.n):
        K[e] = G.l(e)[lids_u].astype(np.int64) * NORB + G.o(e)[pids_u]
    Mm = np.zeros((len(covers_A), len(union_A)), dtype=np.float32)
    for i, c in enumerate(covers_A):
        for r in c:
            Mm[i, idx_of[r]] = 1.0
    return dict(covers=covers_A, union=union_A, idx_of=idx_of, K=K, M=Mm)


def best_foreign_packing(B, sm, mask=None):
    """The s60 statistic: the (g, coverA) cell maximizing the number of rows of
    a relabeled ctrlgroup0 cover that are legal rows of B.  Returns the winning
    cell and the placed row ids (identical construction to neartop.py)."""
    mask = B["inrows"] if mask is None else mask
    cnt = mask[sm["K"]].astype(np.float32) @ sm["M"].T
    o = int(np.argmax(cnt))
    e, ci = divmod(o, cnt.shape[1])
    return e, ci, int(cnt.flat[o]), cnt


def place(B, sm, e, ci, mask=None):
    """Map cover ci of A by symmetry e; split into rows that land in B and the
    ones that fail, with the reason each failure fails."""
    mask = B["inrows"] if mask is None else mask
    keys = [int(sm["K"][e, sm["idx_of"][r]]) for r in sm["covers"][ci]]
    placed, failed = [], []
    for k in keys:
        lid, pid = divmod(k, NORB)
        if k in B["rowid_of_key"] and mask[k]:
            placed.append(B["rowid_of_key"][k])
        else:
            kids = [int(x) for x in LOOP_ORBS[lid] if x != pid]
            failed.append(dict(key=k, loop=lid, parent=pid, children=kids,
                               kernel=bool(B["kermask"][lid]),
                               root_children=[c for c in kids
                                              if not B["colmask"][c]],
                               pruned=bool(k in B["rowid_of_key"]
                                           and not mask[k])))
    return placed, failed


def residual_cols(B, placed_ids, colset=None):
    cov = set()
    for i in placed_ids:
        cov.update(int(c) for c in B["children"][i])
    allc = set(int(c) for c in B["cols"]) if colset is None else set(colset)
    assert cov <= allc and len(cov) == 5 * len(placed_ids), "not a packing"
    return allc - cov
