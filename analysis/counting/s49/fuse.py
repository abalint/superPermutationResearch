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

UNTARGETED (s52): the modes above are TARGETED -- they ask whether a
named class C is reachable.  `untargeted` asks the open question: apply
an edit-preconditioned r1 to the source, RESCAN the whole vocabulary
against the intermediate F' for preconditioned r2, apply each, replay
ONCE per fused product, and canon-gate the product against the
220-class project shell.  A product in the 220 is a rediscovery (an
edge of the fused-pair graph); a product OUTSIDE it at length <= 5906
is an ESCAPE -- the event the sweep exists to find.

Usage: python3 fuse.py index        # build+save the instance key index
       python3 fuse.py depth1       # exact single-rule test, all pairs
       python3 fuse.py depth2 [maxinst]
       python3 fuse.py untargeted --shard i/24 [--out D] [--dry-run]
                                   [--limit N] [--prefilter]
       python3 fuse.py untargeted --control --src <class.txt> [--orient F]
                                   [--target <class.txt>] [--stop-on-target]
"""
import csv
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone
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
# s51 re-scope: the canon gate targets the 220-class PROJECT SHELL, not
# the 198 of DIRS.  220 = 198 + kristan5906_web (2) + novel5906d (20);
# this is exactly m3_check's n=7 index + SUPPLEMENTARY.
DIRS220 = DIRS + ['data/novel5906d', 'data/kristan5906_web']
RECORD = 5906

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


# ------------------------------------------------------------------
# s52: the UNTARGETED fused-pair sweep
# ------------------------------------------------------------------

def file_map(dirs):
    """class file name -> path.  endswith('.txt') EXACTLY -- data/
    kristan5906_web/ holds .txt.rediscovery files that a '*.txt*' glob
    would inflate 2 -> 5 (HANDOFF-S51 trap)."""
    m = {}
    for d in dirs:
        p = os.path.join(R, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if f.endswith('.txt'):
                m.setdefault(f, os.path.join(p, f))
    return m


def walk_arrays(path, orient):
    """(start perm id, flat bool[NP], doors int32[NP]) for one
    orientation of one class file -- the same coordinates load_corpus
    uses, but for a single file (no 198-class parse at startup)."""
    src = open(path).read().strip()
    txt = src if orient == 'F' else src[::-1]
    E, D, st = structure(first_visit_path(txt, N))
    flat = np.zeros(NP, dtype=bool)
    for c in E:
        for p in E[c]:
            flat[pid[p]] = True
    dr = np.full(NP, -1, dtype=np.int32)
    for a, b in D.items():
        dr[pid[a]] = pid[b]
    return pid[st], flat, dr


def check_plans(rules, ids):
    """Per-rule ORDERED precondition checks for the early-exit scan.

    Semantics are loopswap_apply/i4a `edit`: removals validate against
    the ORIGINAL structure, additions against the POST-REMOVAL one, so
    a doors_in whose exit is also a doors_out exit needs NO free-slot
    check (32 of the 864 rules reuse an exit that way; fuse.py's
    depth1/depth2 scan tests `doors[e] == -1` on the original and so
    silently never fires them).

    Order = most selective first: doors_out (exit present AND pointing
    at the exact target, ~0.3% of sigmas) then ents_out (~17%) then
    ents_in / doors_in (which barely narrow anything).
    """
    plans = []
    for rid in ids:
        eo, ei, (doe, dov), (die, div) = rules[rid]
        out_exits = set(int(x) for x in doe)
        ck = []
        for a, b in zip(doe.tolist(), dov.tolist()):
            ck.append((0, a, b))                      # 0 = doors_out
        for p in eo.tolist():
            ck.append((1, p, -1))                     # 1 = ents_out
        for p in ei.tolist():
            ck.append((2, p, -1))                     # 2 = ents_in
        for a in die.tolist():
            if a not in out_exits:
                ck.append((3, a, -1))                 # 3 = doors_in slot
        plans.append(ck)
    return plans


def preconditioned(flat, doors, relab, plans):
    """[(rule index, sigma index)] over the whole 4,354,560-instance
    table, by early-exit column narrowing.  Exactly equivalent to the
    all-columns scan of sizing_untargeted.preconditioned modulo the
    doors_in/doors_out reuse fix above."""
    inst = []
    full = np.arange(NP, dtype=np.int64)
    for j, ck in enumerate(plans):
        surv = full
        for kind, a, b in ck:
            col = relab[surv, a]
            if kind == 0:
                m = doors[col] == relab[surv, b]
            elif kind == 1:
                m = flat[col]
            elif kind == 2:
                m = ~flat[col]
            else:
                m = doors[col] == -1
            surv = surv[m]
            if surv.size == 0:
                break
        for k in surv:
            inst.append((j, int(k)))
    return inst


def apply_arrays(flat, doors, tab, rule):
    """(flat', doors') as arrays after one conjugated rule instance."""
    eo, ei, (doe, dov), (die, div) = rule
    fp = flat.copy()
    if len(eo):
        fp[tab[eo]] = False
    if len(ei):
        fp[tab[ei]] = True
    dp = doors.copy()
    if len(doe):
        dp[tab[doe]] = -1
    if len(die):
        dp[tab[die]] = tab[div]
    return fp, dp


def apply_py(fset, dmap, tab, rule):
    """(flat' as set of ids, doors' as dict) -- the replay coordinates."""
    eo, ei, (doe, dov), (die, div) = rule
    f2 = set(fset)
    if len(eo):
        f2.difference_update(tab[eo].tolist())
    if len(ei):
        f2.update(tab[ei].tolist())
    d2 = dict(dmap)
    if len(doe):
        for e in tab[doe].tolist():
            d2.pop(e, None)
    if len(die):
        for e, v in zip(tab[die].tolist(), tab[div].tolist()):
            d2[e] = v
    return f2, d2


def load_shell_index():
    """The 220-class project shell, m3_check convention (published
    n=7 index + every SUPPLEMENTARY project index)."""
    sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))
    from m3_check import SUPPLEMENTARY, load_index
    here = os.path.join(R, 'analysis', 'counting')
    idx = load_index(os.path.join(here, 'upstream5906_canon_index.tsv'))
    for supp in SUPPLEMENTARY.get(7, []):
        p = os.path.join(here, supp)
        if os.path.exists(p):
            idx.update(load_index(p))
    return idx


def _canon(s):
    """m3_check's canonical form, imported (not re-implemented) so the
    gate can never drift from the committed indexes."""
    global _CANON
    if _CANON is None:
        sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))
        from m3_check import canon as _c
        _CANON = _c
    return _CANON(s)


_CANON = None


def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def run_untargeted(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='fuse.py untargeted')
    ap.add_argument('--shard', help='i/24 -- one (class, orientation)')
    ap.add_argument('--sources', default=os.path.join(OUT,
                                                      'blindspot12.txt'))
    ap.add_argument('--out', default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--prefilter', action='store_true',
                    help="the spec's optional tightness cut: skip replay "
                         'unless |flat|+#doors == the source tightness '
                         '(861 at n=7).  MEASURED VACUOUS: all 864 rules '
                         'have (d|ents| + d|doors|) = 0, so every fused '
                         'pair preserves the identity and this flag cuts '
                         'exactly 0%%.  Kept (and control-validated) only '
                         'because a future non-net-zero tier would need it.')
    ap.add_argument('--control', action='store_true')
    ap.add_argument('--src', help='control: source class file name')
    ap.add_argument('--orient', default=None, choices=['F', 'R'])
    ap.add_argument('--target', help='control: class file to look for')
    ap.add_argument('--stop-on-target', action='store_true')
    ap.add_argument('--gate-intermediate', action='store_true',
                    help='(default ON) also replay+canon-gate F\' itself, '
                         'so a fused product is reported as a 2-step chain '
                         'A -r1-> B -r2-> C.  ~0.4%% overhead (one extra '
                         'replay per intermediate) and it closes the one '
                         'orientation gap: r2 applied to the REVERSE of a '
                         'VALID intermediate is a single-rule move out of '
                         "that intermediate's class, which the s46/s50 "
                         'shell-closure sweeps already cover -- but only '
                         'if we know what class the intermediate is in.')
    ap.add_argument('--no-gate-intermediate', action='store_true')
    ap.add_argument('--verify-scan', action='store_true',
                    help='cross-check the early-exit scan against the '
                         'all-columns reference on the source')
    a = ap.parse_args(argv)

    fm = file_map(DIRS220)
    if a.control:
        if not a.src:
            ap.error('--control needs --src')
            return 1
        jobs = [(a.src, o) for o in ((a.orient,) if a.orient else ('F', 'R'))]
        shard_id = 'control'
    else:
        if not a.shard:
            ap.error('--shard i/24 (or --control)')
            return 1
        i, k = (int(x) for x in a.shard.split('/'))
        srcs = [l.strip() for l in open(a.sources) if l.strip()]
        alljobs = [(B, o) for B in srcs for o in ('F', 'R')]
        if k != len(alljobs):
            print(f"NOTE: --shard */{k} but {len(alljobs)} "
                  f"(class, orientation) jobs exist", flush=True)
        if not 0 <= i < k:
            ap.error(f'shard index out of range 0..{k-1}')
            return 1
        jobs = alljobs[i::k] if k != len(alljobs) else [alljobs[i]]
        shard_id = str(i)
    outdir = a.out or os.path.join(R, f'out/s52/untargeted/shard_{shard_id}')
    os.makedirs(outdir, exist_ok=True)

    relab = relab_table()
    rules = load_rules()
    ids = sorted(rules)
    plans = check_plans(rules, ids)
    rarr = [rules[r] for r in ids]
    idx220 = None if a.dry_run else load_shell_index()
    sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))
    from loopswap_apply import make_tables, replay_ids
    TUP, _pid, ROT, G = make_tables(N)
    print(f"untargeted shard {shard_id}: {len(jobs)} (class, orientation) "
          f"job(s); {len(ids)} rules x {NP} sigmas = {len(ids)*NP} instances"
          + ("" if a.dry_run else f"; shell gate {len(idx220)} classes"),
          flush=True)

    status = open(os.path.join(outdir, 'STATUS'), 'a')
    stat = open(os.path.join(outdir, 'stats.tsv'), 'w')
    stat.write("src\to_src\tinter_i\trule1\tsigma1\tmid_class\t"
               "r2_instances\tprefilter_pass\treplays\treplay_killed\t"
               "rediscoveries\tself_edges\tlonger\tescapes\tsec\n")
    edg = open(os.path.join(outdir, 'edges.tsv'), 'w')
    edg.write("src_class\to_src\trule1\tsigma1\trule2\tsigma2\t"
              "mid_class\ttgt_class\tlen\n")
    gate_mid = not a.no_gate_intermediate
    tot = dict(inter=0, r2=0, pre=0, rep=0, kill=0, redis=0, self=0,
               longer=0, esc=0)
    t_all = time.time()
    found_target = False
    for (B, ob) in jobs:
        if B not in fm:
            print(f"  SKIP {B}: not in {DIRS220}", flush=True)
            continue
        st, sf, sd = walk_arrays(fm[B], ob)
        tight = int(sf.sum()) + int((sd >= 0).sum())
        t0 = time.time()
        base = preconditioned(sf, sd, relab, plans)
        print(f"  {B}[{ob}] start={TUP[st]} tightness |flat|+#doors="
              f"{tight}: {len(base)} preconditioned r1 instances "
              f"({time.time()-t0:.1f}s)", flush=True)
        if a.verify_scan:
            ref = _reference_preconditioned(sf, sd, relab, rarr)
            same = sorted(base) == sorted(ref)
            print(f"  verify-scan: fast={len(base)} reference={len(ref)} "
                  f"identical={same}", flush=True)
        todo = base[:a.limit] if a.limit else base
        for ii, (j, k) in enumerate(todo):
            t1 = time.time()
            tab = relab[k]
            fp, dp = apply_arrays(sf, sd, tab, rarr[j])
            inst2 = preconditioned(fp, dp, relab, plans)
            fset = set(np.flatnonzero(fp).tolist())
            de = np.flatnonzero(dp >= 0)
            dmap = {int(e): int(dp[e]) for e in de}
            c = dict(pre=0, rep=0, kill=0, redis=0, self=0, longer=0, esc=0)
            mid = '-'
            if gate_mid and not a.dry_run:
                ip = replay_ids(fset, dmap, st, N, TUP, ROT, G)
                if ip is None:
                    mid = 'replay-dead'
                else:
                    ish = hashlib.sha256(_canon(ip).encode()).hexdigest()
                    mid = idx220.get(ish)
                    if mid is None:
                        mid = f'OUTSIDE-{len(ip)}-{ish[:12]}'
                        if len(ip) <= RECORD:
                            # a DEPTH-1 escape: r1 alone left the shell
                            nm = (f"untargeted-MIDESCAPE-{len(ip)}-"
                                  f"{ids[j]}s{k}-{ish[:12]}-{B}")
                            p = os.path.join(outdir, nm)
                            if not os.path.exists(p):
                                open(p, 'w').write(ip)
                            print("!" * 72, flush=True)
                            print(f"!!  DEPTH-1 ESCAPE {len(ip)} OUTSIDE THE "
                                  f"220: {B}[{ob}] + {ids[j]}[s{k}] -> {nm}",
                                  flush=True)
                            print("!!  STILL REQUIRED: m3_check.py -n 7 + "
                                  "cargo run --release -- validate -n 7 "
                                  "--complete", flush=True)
                            print("!" * 72, flush=True)
                            status.write(f"{_now()}\tMIDESCAPE\t{nm}\n")
                            status.flush()
            if not a.dry_run:
                for (j2, k2) in inst2:
                    tab2 = relab[k2]
                    f2, d2 = apply_py(fset, dmap, tab2, rarr[j2])
                    if a.prefilter and len(f2) + len(d2) != tight:
                        continue
                    c['pre'] += 1
                    c['rep'] += 1
                    prod = replay_ids(f2, d2, st, N, TUP, ROT, G)
                    if prod is None:
                        c['kill'] += 1
                        continue
                    L = len(prod)
                    if L > RECORD:
                        c['longer'] += 1
                        continue
                    sha = hashlib.sha256(_canon(prod).encode()).hexdigest()
                    hit = idx220.get(sha)
                    if L == RECORD and hit:
                        if hit == B:
                            c['self'] += 1
                        else:
                            c['redis'] += 1
                            edg.write(f"{B}\t{ob}\t{ids[j]}\t{k}\t"
                                      f"{ids[j2]}\t{k2}\t{mid}\t{hit}\t{L}\n")
                            if a.target and hit == a.target:
                                found_target = True
                    else:
                        c['esc'] += 1
                        tag = 'SHORTER' if L < RECORD else 'ESCAPE'
                        nm = (f"untargeted-{tag}-{L}-{ids[j]}s{k}-"
                              f"{ids[j2]}s{k2}-{sha[:12]}-{B}")
                        p = os.path.join(outdir, nm)
                        if not os.path.exists(p):
                            open(p, 'w').write(prod)
                        ban = ("!" * 72)
                        print(ban, flush=True)
                        print(f"!!  {tag} {L} OUTSIDE THE 220-CLASS SHELL: "
                              f"{B}[{ob}] + {ids[j]}[s{k}] + "
                              f"{ids[j2]}[s{k2}] -> {nm}", flush=True)
                        print("!!  STILL REQUIRED: python3 analysis/counting/"
                              f"m3_check.py -n 7 {p}", flush=True)
                        print("!!  AND: cargo run --release -- validate -n 7 "
                              f"--file {p} --complete", flush=True)
                        print(ban, flush=True)
                        status.write(f"{_now()}\t{tag}\t{nm}\n")
                        status.flush()
                    if found_target and a.stop_on_target:
                        break
            dt = time.time() - t1
            stat.write(f"{B}\t{ob}\t{ii}\t{ids[j]}\t{k}\t{mid}\t"
                       f"{len(inst2)}\t"
                       f"{c['pre']}\t{c['rep']}\t{c['kill']}\t{c['redis']}\t"
                       f"{c['self']}\t{c['longer']}\t{c['esc']}\t{dt:.3f}\n")
            tot['inter'] += 1
            tot['r2'] += len(inst2)
            for key in c:
                tot[key] += c[key]
            if (ii + 1) % 10 == 0 or ii + 1 == len(todo):
                stat.flush()
            status.write(f"{_now()}\t{B}[{ob}]\t{ii+1}/{len(todo)}\t"
                         f"replays={tot['rep']}\tr2={tot['r2']}\t"
                         f"redis={tot['redis']}\tesc={tot['esc']}\n")
            status.flush()
            if found_target and a.stop_on_target:
                break
        if found_target and a.stop_on_target:
            print(f"  target {a.target} FOUND -- stopping", flush=True)
            break
    stat.close()
    edg.close()
    el = time.time() - t_all
    line = (f"TOTAL shard {shard_id}: intermediates {tot['inter']}, "
            f"r2 instances {tot['r2']}, prefilter-pass {tot['pre']}, "
            f"replays {tot['rep']}, replay-killed {tot['kill']}, "
            f"rediscoveries {tot['redis']}, self-edges {tot['self']}, "
            f"longer {tot['longer']}, ESCAPES {tot['esc']}, {el:.1f}s")
    print(line, flush=True)
    status.write(f"{_now()}\tDONE\t{line}\n")
    status.close()
    with open(os.path.join(outdir, 'summary.tsv'), 'w') as fh:
        fh.write("key\tvalue\n")
        fh.write(f"shard\t{shard_id}\n")
        fh.write(f"jobs\t{';'.join(f'{b}[{o}]' for b, o in jobs)}\n")
        fh.write(f"dry_run\t{int(a.dry_run)}\nprefilter\t{int(a.prefilter)}\n")
        for kk, vv in tot.items():
            fh.write(f"{kk}\t{vv}\n")
        fh.write(f"seconds\t{el:.1f}\n")
    if a.target:
        print(f"CONTROL target {a.target}: "
              f"{'FOUND' if found_target else 'NOT FOUND'}")
        return 0 if found_target else 3
    return 0


def _reference_preconditioned(flat, doors, relab, rarr):
    """All-columns scan (sizing_untargeted.preconditioned) with the
    doors_in/doors_out reuse fix -- the correctness reference."""
    inst = []
    for j, (eo, ei, (doe, dov), (die, div)) in enumerate(rarr):
        ok = np.ones(NP, dtype=bool)
        if len(eo):
            ok &= flat[relab[:, eo]].all(axis=1)
        if ok.any() and len(ei):
            ok &= ~flat[relab[:, ei]].any(axis=1)
        if ok.any() and len(doe):
            ok &= (doors[relab[:, doe]] == relab[:, dov]).all(axis=1)
        if ok.any() and len(die):
            out_exits = set(int(x) for x in doe)
            keep = [t for t, e in enumerate(die.tolist())
                    if e not in out_exits]
            if keep:
                sub = die[keep]
                ok &= (doors[relab[:, sub]] == -1).all(axis=1)
        for k in np.flatnonzero(ok):
            inst.append((j, int(k)))
    return inst


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'index'
    if cmd == 'untargeted':
        return run_untargeted(sys.argv[2:])
    relab = relab_table()
    rules = load_rules()
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
    sys.exit(main() or 0)
