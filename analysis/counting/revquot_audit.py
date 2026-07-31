#!/usr/bin/env python3
"""s47 item3 — the reversal-quotient audit of the loop-swap rule vocabulary.

The tables' `rule_id` is min over S_n relabelings of the DIRECTED rule.
Two further symmetries act on rules and are NOT quotiented by that id:

  iota (direction inverse)  : (eo, ei, do, di) -> (ei, eo, di, do)
  tau  (reversal frame)     : the same underlying move seen on the
                              reversed walk strings.  In replay
                              coordinates (i4a_apply.structure) an entry
                              e of W corresponds to entry rho(e) of
                              rev(W), rho(p) = rot(rev(p)) = rev(p[:-1])+p[-1],
                              and a door (exit a -> entry b) of W
                              corresponds to the door (rev(b) -> rev(a))
                              of rev(W).  Hence
                              tau(eo, ei, do, di) =
                                (rho eo, rho ei,
                                 {(rev b, rev a)} do, {(rev b, rev a)} di).
                              (validated walk-wise by revmap_check.py and
                               move-wise by revoracle.py)

Both commute with relabeling and with each other, and both are
involutions, so the full symmetry group of a rule object is
S_n x {1,iota} x {1,tau} and every directed canonical id has at most
4 images.  This script computes all four ids for every rule in the
committed tables and reports the three quotients.

Output: <outdir>/rule_annotation_n<N>.tsv + summary on stdout.
"""
import hashlib
import os
import sys
import time
from itertools import permutations

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "analysis", "counting"))
from loopswap_apply import parse_rule, relab_rule, rule_id, serialize_rule  # noqa: E402

TABLES = {
    7: ["data/loopswap/rules_n7.tsv",
        "data/loopswap/rules_n7_a256.tsv",
        "data/loopswap/rules_n7_a4840_gen2.tsv",
        "data/loopswap/rules_n7_a4840_band200.tsv"],
    6: ["data/loopswap/rules_n6.tsv",
        "data/loopswap/rules_n6_a360.tsv"],
}


# ---------------------------------------------------------------- symmetries
def rev(p):
    return p[::-1]


def rho(p):
    return p[-2::-1] + (p[-1],)


def iota(rule):
    eo, ei, do, di = rule
    return (ei, eo, di, do)


def tau(rule):
    eo, ei, do, di = rule
    dm = lambda ds: tuple(sorted((rev(b), rev(a)) for a, b in ds))
    return (tuple(sorted(rho(p) for p in eo)),
            tuple(sorted(rho(p) for p in ei)), dm(do), dm(di))


# ---------------------------------------------------------------- canon (fast)
class Canon:
    """min over all n! relabelings of a directed rule, numpy-accelerated."""

    def __init__(self, n):
        self.n = n
        self.perms = sorted(permutations(range(1, n + 1)))
        self.pid = {p: i for i, p in enumerate(self.perms)}
        N = len(self.perms)
        P = np.array(self.perms, dtype=np.int64)                # (N, n)
        pw = np.array([8 ** i for i in range(n)], dtype=np.int64)
        code = np.zeros(8 ** n, dtype=np.int32)
        code[(P * pw).sum(1)] = np.arange(N)
        self.RL = np.empty((N, N), dtype=np.int16)              # sigma x perm
        self.sigmas = list(permutations(range(1, n + 1)))
        for si, sg in enumerate(self.sigmas):
            sa = np.array((0,) + sg, dtype=np.int64)
            self.RL[si] = code[(sa[P] * pw).sum(1)]
        self.cache = {}

    def _blocks(self, rule):
        eo, ei, do, di = rule
        N = len(self.perms)
        cols = []
        for ents in (eo, ei):
            if ents:
                ids = np.array([self.pid[p] for p in ents])
                cols.append(np.sort(self.RL[:, ids].astype(np.int32), axis=1))
        for ds in (do, di):
            if ds:
                a = np.array([self.pid[x] for x, _ in ds])
                b = np.array([self.pid[y] for _, y in ds])
                packed = (self.RL[:, a].astype(np.int32) * N
                          + self.RL[:, b].astype(np.int32))
                cols.append(np.sort(packed, axis=1))
        if not cols:
            return np.zeros((N, 0), dtype=np.int32)
        return np.concatenate(cols, axis=1)

    def best_sigma(self, rule):
        M = self._blocks(rule)
        cand = np.arange(M.shape[0])
        for j in range(M.shape[1]):
            col = M[cand, j]
            cand = cand[col == col.min()]
            if len(cand) == 1:
                break
        return self.sigmas[cand[0]]

    def canon(self, rule):
        key = rule
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        c = relab_rule(rule, self.best_sigma(rule))
        res = (c, rule_id(c))
        self.cache[key] = res
        return res


# ---------------------------------------------------------------- table load
def load_tables(n):
    """rule_id -> (rule, {table: n_pairs})."""
    rules = {}
    for rel in TABLES[n]:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        tag = os.path.basename(path)
        with open(path) as fh:
            next(fh)
            for line in fh:
                f = line.rstrip("\n").split("\t")
                rid, rn, eo, ei, do, di, npairs = f[0], int(f[1]), f[2], f[3], f[4], f[5], f[6]
                if rn != n:
                    continue
                r = parse_rule(eo, ei, do, di)
                if rid in rules:
                    rules[rid][1][tag] = int(npairs)
                else:
                    rules[rid] = (r, {tag: int(npairs)})
    return rules


def dsu_find(par, x):
    while par[x] != x:
        par[x] = par[par[x]]
        x = par[x]
    return x


def dsu_union(par, a, b):
    ra, rb = dsu_find(par, a), dsu_find(par, b)
    if ra != rb:
        par[max(ra, rb)] = min(ra, rb)


def audit(n, outdir):
    t0 = time.time()
    rules = load_tables(n)
    print(f"n={n}: {len(rules)} distinct directed canonical ids across "
          f"{len(TABLES[n])} tables")
    C = Canon(n)
    print(f"  relabel table built ({time.time() - t0:.1f}s)", flush=True)

    info = {}
    bad = []
    for k, (rid, (rule, tabs)) in enumerate(sorted(rules.items())):
        cfwd, ifwd = C.canon(rule)
        if ifwd != rid:
            bad.append(rid)
        _, iinv = C.canon(iota(rule))
        _, irev = C.canon(tau(rule))
        _, iir = C.canon(iota(tau(rule)))
        _, iri = C.canon(tau(iota(rule)))
        assert iir == iri, (rid, "iota/tau do not commute")
        eo, ei, do, di = rule
        info[rid] = dict(rule=rule, tabs=tabs,
                         shape=(len(eo), len(ei), len(do), len(di)),
                         inv=iinv, rev=irev, invrev=iir)
        if (k + 1) % 50 == 0:
            print(f"  {k + 1}/{len(rules)} canonicalized "
                  f"({time.time() - t0:.1f}s)", flush=True)
    print(f"  id re-derivation: {len(rules) - len(bad)}/{len(rules)} match "
          f"the committed rule_id" + (f" MISMATCH: {bad}" if bad else ""))

    ids = sorted(info)
    pos = {r: i for i, r in enumerate(ids)}
    par_u = list(range(len(ids)))   # S_n x iota
    par_r = list(range(len(ids)))   # S_n x tau
    par_f = list(range(len(ids)))   # S_n x iota x tau
    for r in ids:
        for tag, par in (("inv", par_u), ("rev", par_r)):
            o = info[r][tag]
            if o in pos:
                dsu_union(par, pos[r], pos[o])
        for tag in ("inv", "rev", "invrev"):
            o = info[r][tag]
            if o in pos:
                dsu_union(par_f, pos[r], pos[o])

    def groups(par):
        g = {}
        for r in ids:
            g.setdefault(dsu_find(par, pos[r]), []).append(r)
        return g

    gu, gr, gf = groups(par_u), groups(par_r), groups(par_f)
    print(f"\n  DIRECTED (S_{n} only)              : {len(ids)}")
    print(f"  UNDIRECTED (S_{n} x iota)           : {len(gu)}")
    print(f"  REVERSAL-QUOTIENTED (S_{n} x tau)   : {len(gr)}")
    print(f"  FULL (S_{n} x iota x tau)           : {len(gf)}")

    self_inv = [r for r in ids if info[r]["inv"] == r]
    inv_absent = [r for r in ids if info[r]["inv"] not in pos]
    self_rev = [r for r in ids if info[r]["rev"] == r]
    rev_absent = [r for r in ids if info[r]["rev"] not in pos]
    rev_pairs = sorted({tuple(sorted((r, info[r]["rev"]))) for r in ids
                        if info[r]["rev"] != r and info[r]["rev"] in pos})
    print(f"  self-inverse (iota-fixed) rules      : {len(self_inv)}")
    print(f"  rules whose inverse is NOT in tables : {len(inv_absent)}"
          f" {inv_absent if len(inv_absent) < 25 else ''}")
    print(f"  tau-fixed rules                      : {len(self_rev)}")
    print(f"  rules whose tau-image is NOT present : {len(rev_absent)}")
    print(f"  tau-collision PAIRS inside the vocab : {len(rev_pairs)}")

    os.makedirs(outdir, exist_ok=True)
    ann = os.path.join(outdir, f"rule_annotation_n{n}.tsv")
    urep = {k: min(v) for k, v in gu.items()}
    rrep = {k: min(v) for k, v in gr.items()}
    frep = {k: min(v) for k, v in gf.items()}
    with open(ann, "w") as out:
        out.write("rule_id\tn\tshape_eo_ei_do_di\tsource_tables\tn_pairs\t"
                  "inverse_id\tinverse_present\trev_frame_id\trev_present\t"
                  "invrev_id\tundirected_object\tundirected_mult\t"
                  "reversal_object\treversal_mult\tfull_object\tfull_mult\n")
        for r in ids:
            d = info[r]
            ku, kr, kf = (dsu_find(par_u, pos[r]), dsu_find(par_r, pos[r]),
                          dsu_find(par_f, pos[r]))
            out.write("\t".join([
                r, str(n), ",".join(map(str, d["shape"])),
                ",".join(sorted(d["tabs"])),
                ",".join(f"{t}={c}" for t, c in sorted(d["tabs"].items())),
                d["inv"], "Y" if d["inv"] in pos else "N",
                d["rev"], "Y" if d["rev"] in pos else "N",
                d["invrev"],
                urep[ku], str(len(gu[ku])),
                rrep[kr], str(len(gr[kr])),
                frep[kf], str(len(gf[kf]))]) + "\n")
    print(f"\n-> {ann}")

    # nontrivial reversal-collision classes, with provenance
    print("\nNONTRIVIAL tau-COLLISION CLASSES (|class| > 1):")
    for k, v in sorted(gr.items(), key=lambda kv: (-len(kv[1]), kv[1][0])):
        if len(v) > 1:
            for r in v:
                print(f"  {r}  shape={info[r]['shape']}  "
                      f"tables={','.join(sorted(info[r]['tabs']))}")
            print("  --")
    print("\nFULL-OBJECT CLASSES of size > 2 (iota+tau both act):")
    for k, v in sorted(gf.items(), key=lambda kv: (-len(kv[1]), kv[1][0])):
        if len(v) > 2:
            print("  " + " ".join(v))
    import pickle
    with open(os.path.join(outdir, f"audit_n{n}.pkl"), "wb") as fh:
        pickle.dump({"info": info, "gu": gu, "gr": gr, "gf": gf,
                     "pos": pos, "par_u": par_u, "par_r": par_r,
                     "par_f": par_f}, fh)
    print(f"\nwall clock n={n}: {time.time() - t0:.1f}s")
    return info, gu, gr, gf


if __name__ == "__main__":
    nn = [int(x) for x in sys.argv[1:]] or [7]
    for n in nn:
        audit(n, os.path.join(HERE, "out"))
