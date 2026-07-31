#!/usr/bin/env python3
"""s49 item1 PART C — the LIBERAL fused test: is the required edit the
ALGEBRAIC SUM of two vocabulary instances?

A 9-column edit is a signed vector delta over (perm entries) x (door
slots): +1 on ents_in / doors_in, -1 on ents_out / doors_out.  Fusing
r2 after r1 adds the vectors (produced-then-consumed entries cancel).
Use a LINEAR hash  key(delta) = sum_i delta_i * h_i  (mod 2^64), so
key(delta1 + delta2) = key(delta1) + key(delta2) exactly.  Then

    delta_req realizable as a fused pair  <=>  key_req in K + K

with K the 4,354,560 instance keys -- a 2SUM over a sorted uint64 array.
This is STRICTLY WEAKER than requiring r1's own edit precondition to
hold on the source (which fuse.py depth2 tests), so a 0 here is the
stronger negative.

Any hit is a 64-bit hash coincidence candidate and MUST be re-verified
exactly.

Usage: python3 sumset.py build
       python3 sumset.py run [top_targets_per_blind]
"""
import os
import sys
import time
from itertools import permutations

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fuse                                               # noqa: E402

R, OUT, NP = fuse.R, fuse.OUT, fuse.NP
g = np.random.default_rng(4242)
HE = g.integers(1, 2**63, size=NP, dtype=np.uint64)        # entry slots
HDe = g.integers(1, 2**63, size=NP, dtype=np.uint64)       # door exit
HDv = g.integers(1, 2**63, size=NP, dtype=np.uint64)       # door target
KD = np.uint64(0xD6E8FEB86659FD93)


def dkey(e, v):
    return HDe[e] * KD + HDv[v]


def linkey(eo, ei, doe, dov, die, div):
    k = np.uint64(0)
    if len(ei):
        k = k + HE[ei].sum(dtype=np.uint64)
    if len(eo):
        k = k - HE[eo].sum(dtype=np.uint64)
    if len(die):
        k = k + dkey(die, div).sum(dtype=np.uint64)
    if len(doe):
        k = k - dkey(doe, dov).sum(dtype=np.uint64)
    return np.uint64(k)


def build():
    relab = fuse.relab_table()
    rules = fuse.load_rules()
    ids = sorted(rules)
    keys = np.zeros(len(ids) * NP, dtype=np.uint64)
    ridx = np.zeros(len(ids) * NP, dtype=np.int16)
    sidx = np.zeros(len(ids) * NP, dtype=np.int16)
    t0 = time.time()
    for j, rid in enumerate(ids):
        eo, ei, (doe, dov), (die, div) = rules[rid]
        k = np.zeros(NP, dtype=np.uint64)
        if len(ei):
            k = k + HE[relab[:, ei]].sum(axis=1, dtype=np.uint64)
        if len(eo):
            k = k - HE[relab[:, eo]].sum(axis=1, dtype=np.uint64)
        if len(die):
            k = k + (HDe[relab[:, die]] * KD +
                     HDv[relab[:, div]]).sum(axis=1, dtype=np.uint64)
        if len(doe):
            k = k - (HDe[relab[:, doe]] * KD +
                     HDv[relab[:, dov]]).sum(axis=1, dtype=np.uint64)
        keys[j * NP:(j + 1) * NP] = k
        ridx[j * NP:(j + 1) * NP] = j
        sidx[j * NP:(j + 1) * NP] = np.arange(NP, dtype=np.int16)
    o = np.argsort(keys, kind='stable')
    np.save(os.path.join(OUT, 'lin_keys.npy'), keys[o])
    np.save(os.path.join(OUT, 'lin_rule.npy'), ridx[o])
    np.save(os.path.join(OUT, 'lin_sigma.npy'), sidx[o])
    print(f"linear index built: {len(keys)} instances, "
          f"{len(np.unique(keys))} distinct, {time.time()-t0:.1f}s")


def run(topn):
    K = np.load(os.path.join(OUT, 'lin_keys.npy'))
    Kr = np.load(os.path.join(OUT, 'lin_rule.npy'))
    Ks = np.load(os.path.join(OUT, 'lin_sigma.npy'))
    ids = sorted(fuse.load_rules())
    relab = fuse.relab_table()
    names, W = fuse.load_corpus()
    sig = list(permutations(range(1, 8)))
    sidx_of = {s: i for i, s in enumerate(sig)}
    blind = [l.strip() for l in open(os.path.join(OUT, 'blindspot12.txt'))
             if l.strip()]
    starts = sorted({v[0] for v in W.values()})

    cache = {}
    for C in names:
        for ot in ('F', 'R'):
            tst, tflat, tdr = W[(C, ot)]
            for sst in starts:
                tab = relab[sidx_of[fuse.rho_of(tst, sst)]]
                nf = np.zeros(NP, dtype=bool)
                nf[tab[np.flatnonzero(tflat)]] = True
                nd = np.full(NP, -1, dtype=np.int32)
                de = np.flatnonzero(tdr >= 0)
                nd[tab[de]] = tab[tdr[de]]
                cache[(C, ot, sst)] = (nf, nd)
    print("caches built", flush=True)

    # rank targets per blind class by |symdiff|
    jobs = []
    for B in blind:
        cand = []
        for C in names:
            if C == B:
                continue
            for ob in ('F', 'R'):
                sst, sf, sd = W[(B, ob)]
                for ot in ('F', 'R'):
                    tf, td = cache[(C, ot, sst)]
                    sd_ = int((sf ^ tf).sum())
                    cand.append((sd_, B, ob, C, ot))
        cand.sort()
        jobs += cand[:topn] if topn else cand
    print(f"{len(jobs)} (blind, frame, target) jobs", flush=True)

    t0 = time.time()
    hits = []
    out = open(os.path.join(OUT, 'sumset_results.tsv'), 'w')
    out.write("blind\to_src\ttarget\to_tgt\tsymdiff\tents_out\tents_in\t"
              "doors_out\tdoors_in\tsumset_hits\n")
    for i, (sdv, B, ob, C, ot) in enumerate(jobs):
        sst, sf, sd = W[(B, ob)]
        tf, td = cache[(C, ot, sst)]
        eo = np.flatnonzero(sf & ~tf)
        ei = np.flatnonzero(tf & ~sf)
        se = np.flatnonzero(sd >= 0)
        te = np.flatnonzero(td >= 0)
        dom = se[td[se] != sd[se]]
        dim = te[sd[te] != td[te]]
        kreq = linkey(eo, ei, dom, sd[dom], dim, td[dim])
        want = kreq - K
        pos = np.searchsorted(K, want)
        pos[pos >= len(K)] = 0
        m = np.flatnonzero(K[pos] == want)
        out.write(f"{B}\t{ob}\t{C}\t{ot}\t{sdv}\t{len(eo)}\t{len(ei)}\t"
                  f"{len(dom)}\t{len(dim)}\t{len(m)}\n")
        if len(m):
            for j in m[:20]:
                hits.append((B, ob, C, ot, ids[Kr[j]], int(Ks[j]),
                             ids[Kr[pos[j]]], int(Ks[pos[j]])))
        if i % 50 == 0:
            print(f"  {i}/{len(jobs)}  {time.time()-t0:.1f}s "
                  f"hits so far {len(hits)}", flush=True)
    out.close()
    print(f"SUMSET hits (hash-level, unverified): {len(hits)}  "
          f"{time.time()-t0:.1f}s")
    with open(os.path.join(OUT, 'sumset_hits.tsv'), 'w') as fh:
        fh.write("blind\to_src\ttarget\to_tgt\trule1\tsigma1\trule2\t"
                 "sigma2\n")
        for h in hits:
            fh.write("\t".join(map(str, h)) + "\n")


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        build()
    else:
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
