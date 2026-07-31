#!/usr/bin/env python3
"""s49 item1 PARTS B/C — the FUSED-composite instrument.

A 9-column rule instance is a signed edit
    delta = (ents_out EO, ents_in EI, doors_out DO, doors_in DI)
in ABSOLUTE (perm-id) coordinates: rule r conjugated by relabeling sigma.
The vocabulary has 864 directed rules x 5040 relabelings = 4,354,560
instances.

Rigidity: for an ordered pair of walk-orientations (B source, C target)
the frame rho is FORCED by start(rho.C) = start(B), so the edit that
carries B to C is UNIQUE and explicit:
    EO_req = flat(B) \\ flat(rho.C)      EI_req = flat(rho.C) \\ flat(B)
    DO_req = doors(B) \\ doors(rho.C)    DI_req = doors(rho.C) \\ doors(B)
and, because replay is a deterministic function of (E, D, start), ANY
edit realizing (EO_req, EI_req, DO_req, DI_req) reproduces C exactly --
there is no replay filter on a targeted composite.

DEPTH 1  : is delta_req itself an instance?             (hash lookup)
DEPTH 2  : is delta_req = delta_1 + delta_2 with delta_1 an instance
           whose `edit` precondition holds on B (EO_1 subset flat(B),
           EI_1 disjoint flat(B), doors ok) and delta_2 an instance?
           delta_2 is then DETERMINED by (B, C, delta_1), so this is one
           hash lookup per (preconditioned instance, target) pair.

Usage: python3 fuse.py index        # build+save the instance key index
       python3 fuse.py depth1       # exact single-rule test, all pairs
       python3 fuse.py depth2 [maxinst]
"""
import csv
import os
import re
import sys
import time
from itertools import permutations

import numpy as np

R = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(R, 'out/s49/item1')
sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))
from i4a_apply import structure                          # noqa: E402
from loop_ledger_probe import first_visit_path           # noqa: E402

N = 7
NP = 5040
perms = sorted(permutations(range(1, N + 1)))
pid = {p: i for i, p in enumerate(perms)}
TABLES = ['data/loopswap/rules_n7_a256.tsv',
          'data/loopswap/rules_n7_a4840_gen2.tsv',
          'data/loopswap/rules_n7_a4840_band200.tsv',
          'data/loopswap/rules_n7_s48_covertwin.tsv']
DIRS = ['data/upstream5906', 'data/novel5906',
        'data/novel5906b', 'data/novel5906c']

M1 = np.uint64(0x9E3779B97F4A7C15)
M2 = np.uint64(0xC2B2AE3D27D4EB4F)
M3 = np.uint64(0x165667B19E3779F9)
M4 = np.uint64(0x27D4EB2F165667C5)
KD = np.uint64(0xD6E8FEB86659FD93)


def rng_tables():
    g = np.random.default_rng(20260730)
    return [g.integers(1, 2**63, size=NP, dtype=np.uint64) for _ in range(4)]


hA, hB, hC, hD = rng_tables()


def relab_table():
    p = os.path.join(OUT, 'relab.npy')
    if os.path.exists(p):
        return np.load(p)
    sig = list(permutations(range(1, N + 1)))
    t = np.zeros((NP, NP), dtype=np.int32)
    for k, sg in enumerate(sig):
        m = {i + 1: sg[i] for i in range(N)}
        t[k] = [pid[tuple(m[c] for c in q)] for q in perms]
    np.save(p, t)
    return t


def load_rules():
    rules = {}
    for t in TABLES:
        with open(os.path.join(R, t)) as fh:
            for row in csv.DictReader(fh, delimiter='\t'):
                def ids(x):
                    return np.array(
                        [pid[tuple(int(c) for c in s)]
                         for s in (x.split(',') if x else [])],
                        dtype=np.int64)

                def dids(x):
                    ee, vv = [], []
                    for s in (x.split(',') if x else []):
                        a, b = s.split('>')
                        ee.append(pid[tuple(int(c) for c in a)])
                        vv.append(pid[tuple(int(c) for c in b)])
                    return (np.array(ee, dtype=np.int64),
                            np.array(vv, dtype=np.int64))
                rules[row['rule_id']] = (ids(row['ents_out']),
                                         ids(row['ents_in']),
                                         dids(row['doors_out']),
                                         dids(row['doors_in']))
    return rules


def setkey(eo, ei, do_e, do_v, di_e, di_v):
    """uint64 key of one absolute edit (arrays of perm ids)."""
    sa = hA[eo].sum(dtype=np.uint64) if len(eo) else np.uint64(0)
    sb = hB[ei].sum(dtype=np.uint64) if len(ei) else np.uint64(0)
    sc = ((hC[do_e] ^ (hD[do_v] * KD)).sum(dtype=np.uint64)
          if len(do_e) else np.uint64(0))
    sd = ((hC[di_e] ^ (hD[di_v] * KD)).sum(dtype=np.uint64)
          if len(di_e) else np.uint64(0))
    return sa * M1 + sb * M2 + sc * M3 + sd * M4


def build_index(relab, rules):
    ids = sorted(rules)
    keys = np.zeros(len(ids) * NP, dtype=np.uint64)
    ridx = np.zeros(len(ids) * NP, dtype=np.int16)
    sidx = np.zeros(len(ids) * NP, dtype=np.int16)
    t0 = time.time()
    for j, rid in enumerate(ids):
        eo, ei, (doe, dov), (die, div) = rules[rid]
        z = np.zeros(NP, dtype=np.uint64)
        sa = hA[relab[:, eo]].sum(axis=1, dtype=np.uint64) if len(eo) else z
        sb = hB[relab[:, ei]].sum(axis=1, dtype=np.uint64) if len(ei) else z
        sc = ((hC[relab[:, doe]] ^ (hD[relab[:, dov]] * KD))
              .sum(axis=1, dtype=np.uint64) if len(doe) else z)
        sd = ((hC[relab[:, die]] ^ (hD[relab[:, div]] * KD))
              .sum(axis=1, dtype=np.uint64) if len(die) else z)
        keys[j * NP:(j + 1) * NP] = sa * M1 + sb * M2 + sc * M3 + sd * M4
        ridx[j * NP:(j + 1) * NP] = j
        sidx[j * NP:(j + 1) * NP] = np.arange(NP, dtype=np.int16)
        if j % 100 == 0:
            print(f"  rule {j}/{len(ids)}  {time.time()-t0:.1f}s", flush=True)
    o = np.argsort(keys, kind='stable')
    np.save(os.path.join(OUT, 'inst_keys.npy'), keys[o])
    np.save(os.path.join(OUT, 'inst_rule.npy'), ridx[o])
    np.save(os.path.join(OUT, 'inst_sigma.npy'), sidx[o])
    with open(os.path.join(OUT, 'inst_ruleids.txt'), 'w') as fh:
        fh.write("\n".join(ids))
    u = len(np.unique(keys))
    print(f"instances {len(keys)}  distinct keys {u}  "
          f"({len(keys)-u} collisions/duplicates)  {time.time()-t0:.1f}s")


def load_index():
    return (np.load(os.path.join(OUT, 'inst_keys.npy')),
            np.load(os.path.join(OUT, 'inst_rule.npy')),
            np.load(os.path.join(OUT, 'inst_sigma.npy')),
            open(os.path.join(OUT, 'inst_ruleids.txt')).read().split())


def lookup(keys, k):
    i = np.searchsorted(keys, k)
    return i if (i < len(keys) and keys[i] == k) else -1


def load_corpus():
    files = {}
    for d in DIRS:
        for f in sorted(os.listdir(os.path.join(R, d))):
            if f.endswith('.txt'):
                files[f] = os.path.join(R, d, f)
    W = {}
    for f in sorted(files):
        src = open(files[f]).read().strip()
        for o, txt in (('F', src), ('R', src[::-1])):
            E, D, st = structure(first_visit_path(txt, N))
            flat = np.zeros(NP, dtype=bool)
            for c in E:
                for p in E[c]:
                    flat[pid[p]] = True
            dr = np.full(NP, -1, dtype=np.int32)
            for a, b in D.items():
                dr[pid[a]] = pid[b]
            W[(f, o)] = (st, flat, dr)
    return sorted(files), W


def frames(W, names):
    starts = sorted({v[0] for v in W.values()})
    return starts


def rho_of(a, b):
    """relabeling sending target-start a to source-start b, as a tuple."""
    rho = [0] * N
    for x, y in zip(a, b):
        rho[x - 1] = y
    return tuple(rho)


def sigma_index(rho):
    sig = list(permutations(range(1, N + 1)))
    return sig.index(tuple(rho))


def main():
    relab = relab_table()
    rules = load_rules()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'index'
    if cmd == 'index':
        build_index(relab, rules)
        return
    keys, ridx, sidx, ruleids = load_index()
    names, W = load_corpus()
    srcfile = os.environ.get('S49_SOURCES',
                             os.path.join(OUT, 'blindspot12.txt'))
    blind = [l.strip() for l in open(srcfile) if l.strip()]
    print(f"sources: {len(blind)} from {srcfile}", flush=True)
    starts = sorted({v[0] for v in W.values()})
    sig = list(permutations(range(1, N + 1)))
    sidx_of = {s: i for i, s in enumerate(sig)}

    # relabeled target caches: (C, orient, source-start) -> (flat, doors)
    cache = {}
    for C in names:
        for ot in ('F', 'R'):
            tst, tflat, tdr = W[(C, ot)]
            for sst in starts:
                k = sidx_of[rho_of(tst, sst)]
                tab = relab[k]
                nf = np.zeros(NP, dtype=bool)
                nf[tab[np.flatnonzero(tflat)]] = True
                nd = np.full(NP, -1, dtype=np.int32)
                de = np.flatnonzero(tdr >= 0)
                nd[tab[de]] = tab[tdr[de]]
                cache[(C, ot, sst)] = (nf, nd)
    print("caches built", flush=True)

    def req(B, ob, C, ot):
        sst, sf, sd = W[(B, ob)]
        tf, td = cache[(C, ot, sst)]
        eo = np.flatnonzero(sf & ~tf)
        ei = np.flatnonzero(tf & ~sf)
        se = np.flatnonzero(sd >= 0)
        te = np.flatnonzero(td >= 0)
        dom = np.array([e for e in se if td[e] != sd[e]], dtype=np.int64)
        dim = np.array([e for e in te if sd[e] != td[e]], dtype=np.int64)
        return eo, ei, (dom, sd[dom] if len(dom) else dom), \
            (dim, td[dim] if len(dim) else dim)

    if cmd == 'depth1':
        hits = 0
        rows = []
        for B in blind:
            for C in names:
                if C == B:
                    continue
                for ob in ('F', 'R'):
                    for ot in ('F', 'R'):
                        eo, ei, (doe, dov), (die, div) = req(B, ob, C, ot)
                        k = setkey(eo, ei, doe, dov, die, div)
                        i = lookup(keys, k)
                        if i >= 0:
                            hits += 1
                            rows.append((B, C, ob, ot, len(eo), len(ei),
                                         ruleids[ridx[i]], int(sidx[i])))
            print("  depth1 done", B, flush=True)
        print(f"DEPTH-1 exact single-rule realizations: {hits}")
        with open(os.path.join(OUT, 'depth1_hits.tsv'), 'w') as fh:
            fh.write("blind\tother\to_src\to_tgt\tents_out\tents_in\t"
                     "rule\tsigma\n")
            for r in rows:
                fh.write("\t".join(map(str, r)) + "\n")
        return

    if cmd == 'depth2':
        maxinst = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
        ids = sorted(rules)
        # precompute per-rule arrays
        t0 = time.time()
        tot_pre = 0
        hits = []
        stat = open(os.path.join(OUT, 'depth2_stats.tsv'), 'w')
        stat.write("blind\to_src\tpreconditioned_instances\ttargets\t"
                   "lookups\thits\tsec\n")
        for B in blind:
            for ob in ('F', 'R'):
                t1 = time.time()
                sst, sf, sd = W[(B, ob)]
                inst = []
                for j, rid in enumerate(ids):
                    eo, ei, (doe, dov), (die, div) = rules[rid]
                    ok = np.ones(NP, dtype=bool)
                    if len(eo):
                        ok &= sf[relab[:, eo]].all(axis=1)
                    if not ok.any():
                        continue
                    if len(ei):
                        ok &= ~sf[relab[:, ei]].any(axis=1)
                    if not ok.any():
                        continue
                    if len(doe):
                        ok &= (sd[relab[:, doe]] ==
                               relab[:, dov]).all(axis=1)
                    if not ok.any():
                        continue
                    if len(die):
                        ok &= (sd[relab[:, die]] == -1).all(axis=1)
                    for k in np.flatnonzero(ok):
                        inst.append((j, int(k)))
                tot_pre += len(inst)
                # candidate targets: every other class, both orientations
                nlook = 0
                nh = 0
                for (j, k) in inst[:maxinst]:
                    rid = ids[j]
                    eo, ei, (doe, dov), (die, div) = rules[rid]
                    tab = relab[k]
                    aeo = tab[eo] if len(eo) else eo
                    aei = tab[ei] if len(ei) else ei
                    fp = sf.copy()
                    fp[aeo] = False
                    fp[aei] = True
                    dp = sd.copy()
                    if len(doe):
                        dp[tab[doe]] = -1
                    if len(die):
                        dp[tab[die]] = tab[div]
                    dpe = np.flatnonzero(dp >= 0)
                    for C in names:
                        if C == B:
                            continue
                        for ot in ('F', 'R'):
                            tf, td = cache[(C, ot, sst)]
                            e2 = np.flatnonzero(fp & ~tf)
                            i2 = np.flatnonzero(tf & ~fp)
                            te = np.flatnonzero(td >= 0)
                            d2o = dpe[td[dpe] != dp[dpe]]
                            d2i = te[dp[te] != td[te]]
                            kk = setkey(e2, i2, d2o, dp[d2o],
                                        d2i, td[d2i])
                            nlook += 1
                            ii = lookup(keys, kk)
                            if ii >= 0:
                                nh += 1
                                hits.append((B, ob, C, ot, rid, k,
                                             ruleids[ridx[ii]],
                                             int(sidx[ii]), len(e2)))
                dt = time.time() - t1
                stat.write(f"{B}\t{ob}\t{len(inst)}\t{2*(len(names)-1)}\t"
                           f"{nlook}\t{nh}\t{dt:.1f}\n")
                stat.flush()
                print(f"  {B}[{ob}] pre={len(inst)} lookups={nlook} "
                      f"hits={nh} {dt:.1f}s", flush=True)
        stat.close()
        print(f"TOTAL preconditioned instances {tot_pre}, "
              f"depth-2 hits {len(hits)}, {time.time()-t0:.1f}s")
        with open(os.path.join(OUT, 'depth2_hits.tsv'), 'w') as fh:
            fh.write("blind\to_src\ttarget\to_tgt\trule1\tsigma1\trule2\t"
                     "sigma2\tents_out2\n")
            for r in hits:
                fh.write("\t".join(map(str, r)) + "\n")
        return


if __name__ == '__main__':
    main()
