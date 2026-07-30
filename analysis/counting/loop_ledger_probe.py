#!/usr/bin/env python3
"""s39 probe: the loop-count relation's exact ledger.

THEORY §6 flags the loop-count relation L = S + #doors − ((n−1)!−1)
as a corpus law with derivation OPEN. Hand analysis (s39) shows it is
CONDITIONAL: a legal n=3 walk with one w3 door (123,231,312 →w3→
321,213,132) has L=0 but S+D+1−(n−1)! = 2. So the true statement is an
inequality-plus-tightness-condition. This probe measures the exact
structure on real walks to pin the condition:

  deficit := (splits + D + 1) − L   where splits = S − (n−1)!
           = (length − base) − Λ    [algebraically, for pure walks]

Micro-structure verified per walk (each was a hand-derivation step):
  V1  arcs of a cycle partition its n perms contiguously and
      rot(exit of arc) = entry of the spatially-next arc;
  V2  the loop of a w2 edge a→b (census: g-orbit of rot(a)) equals
      λ(b) := g-orbit of b — loops are readable from the fed entry;
  V3  a full-cycle arc with w2-in and w2-out continues the SAME loop
      (coherent ride); a split-cycle arc always switches loops.

Ledger quantities measured (no formula assumed):
  S, D, W(=inter-w2), splits, σ(=split cycles), L, deficit;
  x   = full arcs with w2-in AND w2-out (coherent passages);
  runs = maximal time-runs of same-loop w2 edges (and Σr per loop);
  m_ℓ histogram (loop multiplicities), p_ℓ (path components of the
      used edges on each loop's (n−1)-cycle), Φ = fully-used loops;
  slot placement (start/end/door in/out on split vs full arcs).

Modes:
  python3 loop_ledger_probe.py walk <n> <file...>     # full ledger per walk
  python3 loop_ledger_probe.py random <n> <count> <seed> [wmax]
      # random complete first-visit walks (greedy over shuffled
      # weight-capped moves), report deficit distribution + any
      # deficit<0 counterexample (the sign conjecture killer)
  python3 loop_ledger_probe.py cover <n> <file...>
      # M-4 down-payment: per-walk USED-LOOP SET (the cover the
      # theorem certifies) — reports #distinct covers, cover sizes,
      # and pairwise overlap stats across the input walks
"""
import random
import sys
from collections import Counter
from itertools import permutations
from math import factorial


def first_visit_path(s, n):
    want = set(range(1, n + 1))
    seen, path = set(), []
    vals = [int(c) for c in s]
    for i in range(len(vals) - n + 1):
        win = tuple(vals[i : i + n])
        if set(win) == want and win not in seen:
            seen.add(win)
            path.append(win)
    return path


def weight(a, b, n):
    for k in range(n - 1, 0, -1):
        if a[n - k :] == b[:k]:
            return n - k
    return n


def rot(p):
    return p[1:] + (p[0],)


def rotc(p):
    return min(p[i:] + p[:i] for i in range(len(p)))


def g(q):
    n = len(q)
    return q[1 : n - 1] + (q[0], q[n - 1])


def lam(p):
    orb = [p]
    for _ in range(len(p) - 2):
        orb.append(g(orb[-1]))
    return min(orb)


def analyze(path, n, verbose=True):
    fact1 = factorial(n - 1)
    edges = []
    for a, b in zip(path, path[1:]):
        w = weight(a, b, n)
        inter = rotc(a) != rotc(b)
        edges.append((a, b, w, inter))

    intra = sum(1 for *_, w, inter in edges if not inter and w >= 2)
    if intra and verbose:
        print(f"  NOTE: {intra} intra edges present — ledger assumes pure")

    # arcs in time: maximal same-cycle runs
    arcs = []  # (cycle, entry, exit, first_idx, last_idx)
    start = 0
    for i in range(len(path)):
        if i + 1 == len(path) or rotc(path[i + 1]) != rotc(path[i]):
            arcs.append([rotc(path[start]), path[start], path[i], start, i])
            start = i + 1
    S = len(arcs)
    by_cycle = {}
    for ai, a in enumerate(arcs):
        by_cycle.setdefault(a[0], []).append(ai)

    # V1: contiguous partition + rot(exit) = spatially-next entry
    v1_ok = True
    spatial_next_entry = {}  # arc idx -> entry perm of spatially next arc
    for c, ais in by_cycle.items():
        entries = {arcs[ai][1]: ai for ai in ais}
        for ai in ais:
            nxt = rot(arcs[ai][2])
            if nxt not in entries:
                v1_ok = False
            else:
                spatial_next_entry[ai] = nxt

    # transitions between consecutive arcs
    trans = []  # (type, loop_or_None) aligned with arc boundary i -> i+1
    v2_ok = True
    for i in range(S - 1):
        a, b = arcs[i][2], arcs[i + 1][1]
        w = weight(a, b, n)
        if w == 2:
            lp = lam(rot(a))  # census assignment
            if lp != lam(b):
                v2_ok = False
            trans.append(("w2", lp))
        else:
            trans.append(("door", None))
    D = sum(1 for t, _ in trans if t == "door")
    W = sum(1 for t, _ in trans if t == "w2")

    # V3 + runs in time
    v3_ok = True
    runs_per_loop = Counter()
    cur_loop = None
    x = 0
    for i in range(S - 1):
        t, lp = trans[i]
        if t != "w2":
            cur_loop = None
            continue
        # does this w2 edge continue the previous run?
        cont = False
        if i > 0 and trans[i - 1][0] == "w2" and len(by_cycle[arcs[i][0]]) == 1:
            cont = True
            x += 1
            if trans[i - 1][1] != lp:
                v3_ok = False  # coherent passage must keep the loop
        if i > 0 and trans[i - 1][0] == "w2" and len(by_cycle[arcs[i][0]]) > 1:
            if trans[i - 1][1] == lp:
                v3_ok = False  # split passage must switch loops
        if not cont:
            runs_per_loop[lp] += 1
        cur_loop = lp
    runs = sum(runs_per_loop.values())
    L = len(runs_per_loop)

    splits = S - fact1
    sigma = sum(1 for ais in by_cycle.values() if len(ais) > 1)
    deficit = splits + D + 1 - L

    # per-loop used-edge components on the g-cycle
    used_edges = {}  # loop -> set of vertex q (edge q->g(q) used)
    for i in range(S - 1):
        t, lp = trans[i]
        if t == "w2":
            used_edges.setdefault(lp, set()).add(rot(arcs[i][2]))
    m_hist = Counter()
    p_excess = 0
    full_loops = 0
    chain_ends = 0
    for lp, qs in used_edges.items():
        m = len(qs)
        m_hist[m] += 1
        if m == n - 1:
            full_loops += 1
            p = 1
        else:
            # count maximal chains along the g-cycle
            p = sum(1 for q in qs if g(q) not in qs) or 1
            chain_ends += p
        p_excess += p - 1
    partial_loops = L - full_loops

    # slot placement
    s_split = s_full = 0
    touched_full = set()
    for i, a in enumerate(arcs):
        k = len(by_cycle[a[0]])
        in_slot = i == 0 or trans[i - 1][0] == "door"
        out_slot = i == S - 1 or trans[i][0] == "door"
        cnt = int(in_slot) + int(out_slot)
        if cnt:
            if k > 1:
                s_split += cnt
            else:
                s_full += cnt
                touched_full.add(i)
    tau_f = len(touched_full)

    # s39 theorem checks: Φ ≤ splits (cycle-space bound) and
    # P ≤ chain-ends ≤ D+1 (partial loops need doors); deficit
    # decomposes as (splits − Φ) + (D+1 − P), both terms ≥ 0.
    t_phi = splits - full_loops
    t_p = (D + 1) - partial_loops
    thm_ok = t_phi >= 0 and t_p >= 0 and chain_ends <= D + 1
    if verbose:
        print(
            f"  S={S} D={D} W={W} splits={splits} sigma={sigma} "
            f"L={L} deficit={deficit}"
        )
        print(
            f"  theorem terms: splits-Φ={t_phi} (D+1)-P={t_p} "
            f"chain-ends={chain_ends} (≤D+1={D + 1}) OK={thm_ok}"
        )
        print(
            f"  x={x} runs={runs} (W-x={W - x}) "
            f"run-excess Rx={runs - L} comp-excess Px={p_excess} "
            f"full-loops Φ={full_loops}"
        )
        print(f"  m_l histogram: {dict(sorted(m_hist.items()))}")
        print(
            f"  slots: on-split={s_split} on-full={s_full} "
            f"touched-full-arcs={tau_f}"
        )
        print(f"  V1 rot(exit)=next-entry: {v1_ok}  V2 loop=λ(fed): {v2_ok}  V3 coherence: {v3_ok}")
    return {
        "S": S, "D": D, "W": W, "splits": splits, "sigma": sigma,
        "L": L, "deficit": deficit, "x": x, "runs": runs,
        "Px": p_excess, "full_loops": full_loops,
        "partial_loops": partial_loops, "chain_ends": chain_ends,
        "t_phi": t_phi, "t_p": t_p, "thm_ok": thm_ok,
        "v1": v1_ok, "v2": v2_ok, "v3": v3_ok, "intra": intra,
        "len": None,
    }


def random_complete_walk(n, rng, wmax):
    perms = set(permutations(range(1, n + 1)))
    cur = tuple(range(1, n + 1))
    seen = {cur}
    path = [cur]
    while len(seen) < len(perms):
        by_w = {}
        for w in range(1, wmax + 1):
            base = cur[w:]
            missing = [c for c in range(1, n + 1) if c not in base]
            cands = []
            for tailperm in permutations(missing):
                nxt = base + tailperm
                if nxt not in seen and weight(cur, nxt, n) == w:
                    cands.append(nxt)
            if cands:
                by_w[w] = cands
        if not by_w:
            return None
        # mostly greedy, but jump to a random heavier move 15% of the time
        # so doors land in diverse (also mid-ride) positions
        ws = sorted(by_w)
        w = ws[0] if rng.random() < 0.85 else rng.choice(ws)
        nxt = rng.choice(by_w[w])
        seen.add(nxt)
        path.append(nxt)
        cur = nxt
    return path


def main():
    mode = sys.argv[1]
    n = int(sys.argv[2])
    if mode == "walk":
        for f in sys.argv[3:]:
            s = open(f).read().strip()
            print(f"{f} (len {len(s)}):")
            path = first_visit_path(s, n)
            r = analyze(path, n)
            base = factorial(n) + factorial(n - 1) + (n - 3)
            print(f"  length-base = {len(s) - base}")
        return 0
    if mode == "cover":
        import os

        files = []
        for arg in sys.argv[3:]:
            if os.path.isdir(arg):
                files += [
                    os.path.join(arg, f)
                    for f in sorted(os.listdir(arg))
                    if f.endswith(".txt")
                ]
            else:
                files.append(arg)
        covers = {}
        for f in files:
            s = open(f).read().strip()
            if not s.isdigit():
                continue
            path = first_visit_path(s, n)
            loops = set()
            for a, b in zip(path, path[1:]):
                if weight(a, b, n) == 2 and rotc(a) != rotc(b):
                    loops.add(lam(b))
            covers[f] = frozenset(loops)
        distinct = {}
        for f, c in covers.items():
            distinct.setdefault(c, []).append(f)
        sizes = Counter(len(c) for c in covers.values())
        print(f"{len(covers)} walks, {len(distinct)} distinct loop covers; sizes {dict(sorted(sizes.items()))}")
        reps = list(distinct)
        if len(reps) > 1:
            # full pairwise is O(N^2) — sample when the cover set is large
            pairs = [
                (i, j)
                for i in range(len(reps))
                for j in range(i + 1, len(reps))
            ] if len(reps) <= 800 else None
            if pairs is None:
                rng = random.Random(0)
                pairs = [
                    tuple(rng.sample(range(len(reps)), 2)) for _ in range(200000)
                ]
                print("(pairwise stats from a 200k random pair sample)")
            ov = Counter()
            for i, j in pairs:
                ov[len(reps[i] & reps[j])] += 1
            print(f"pairwise |intersection| histogram over distinct covers: {dict(sorted(ov.items()))}")
            # loop-usage frequency: is any loop universal or near-universal?
            freq = Counter()
            for c in reps:
                for lp in c:
                    freq[lp] += 1
            top = freq.most_common(5)
            print(
                f"loop usage across {len(reps)} distinct covers: "
                f"{len(freq)} loops ever used; top shares "
                f"{[round(v / len(reps), 3) for _, v in top]}"
            )
        for c, fs in sorted(distinct.items(), key=lambda kv: -len(kv[1]))[:5]:
            print(f"  cover size {len(c)} shared by {len(fs)} walks, e.g. {fs[0]}")
        return 0
    if mode == "random":
        count = int(sys.argv[3])
        seed = int(sys.argv[4])
        wmax = int(sys.argv[5]) if len(sys.argv) > 5 else 3
        rng = random.Random(seed)
        defs = Counter()
        neg = None
        pure_defs = Counter()
        thm_bad = 0
        for i in range(count):
            # random move policy: greedy-by-weight but occasionally forced
            # to jump — vary by shuffling weight preference a little
            path = random_complete_walk(n, rng, wmax)
            if path is None:
                continue
            r = analyze(path, n, verbose=False)
            defs[r["deficit"]] += 1
            if r["intra"] == 0:
                pure_defs[r["deficit"]] += 1
                if not r["thm_ok"]:
                    thm_bad += 1
                    if thm_bad == 1:
                        print(f"THEOREM TERM VIOLATION (pure walk): {r}")
                        print(path)
            if r["deficit"] < 0 and neg is None and r["intra"] == 0:
                neg = path
        print(f"deficit histogram (all {sum(defs.values())} walks): {dict(sorted(defs.items()))}")
        print(f"deficit histogram (pure walks only): {dict(sorted(pure_defs.items()))}")
        print(f"theorem-term violations on pure walks: {thm_bad}")
        if neg:
            print("NEGATIVE-DEFICIT PURE WALK FOUND (sign conjecture DEAD):")
            print(neg)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
