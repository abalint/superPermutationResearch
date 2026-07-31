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

s56 addition — the SLACK ledger (Gheorghe bridge lemma, out/s55/gheorghe/
DICTIONARY.md §2).  Alongside `deficit` we now also measure

  v  = #distinct arc-start 2-loops  (his `v`; the L-set is a subset, our L2)
  j  = (splits + D + 1) − v         (his `j`)
  deficit = j + (v − L) >= j        (the bridge lemma)

so a walk's slack is split into the part his frame sees (`j`) and the
door/first-arc part (`v − L`).  `slack`/`hunt`/`exhaust` report both.

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
  python3 loop_ledger_probe.py slack <n> <file-or-dir...>
      # s56 control/census: deficit, j and (v−L) per walk over a corpus;
      # prints every slack (deficit>0) walk, a (deficit,j,v−L) histogram
      # and the min length per deficit value.  Always prints `words read`.
  python3 loop_ledger_probe.py hunt <n> <count> <seed> [wmax] [outdir]
      # s56 slack-walk materializer: random complete walks, keep the
      # SHORTEST slack walk seen (writes it to outdir if given), report
      # min length by deficit and the tight/slack length gap.
  python3 loop_ledger_probe.py exhaust <n> <cap> [maxnodes]
      # s56 exhaustive slack tax: DFS over ALL complete first-visit walks
      # of length <= cap, reporting min length among pure slack walks and
      # among pure tight walks (theorem-grade at n=3,4).
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


_LAM = {}


def lam(p):
    c = _LAM.get(p)
    if c is not None:
        return c
    orb = [p]
    for _ in range(len(p) - 2):
        orb.append(g(orb[-1]))
    c = min(orb)
    for q in orb:
        _LAM[q] = c
    return c


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

    # s56: Gheorghe's v = #distinct arc-start 2-loops (DICTIONARY §2).
    # The L-set is a subset of it (L2), so v >= L and deficit = j + (v-L).
    v = len({lam(a[1]) for a in arcs})
    j = splits + D + 1 - v
    v_minus_L = v - L

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
        "v": v, "j": j, "vmL": v_minus_L,
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


def expand(args):
    """file/dir arguments -> sorted list of .txt paths (s56)."""
    import os

    files = []
    for arg in args:
        if os.path.isdir(arg):
            files += [
                os.path.join(arg, f)
                for f in sorted(os.listdir(arg))
                if f.endswith(".txt")
            ]
        else:
            files.append(arg)
    return files


def slack_report(n, files):
    """s56 mode `slack`: deficit / j / (v-L) census over a corpus."""
    read = 0
    hist = Counter()
    minlen = {}
    slackers = []
    impure = 0
    for f in files:
        s = open(f).read().strip().replace("\n", "")
        if not s or set(s) - set("123456789"):
            continue
        path = first_visit_path(s, n)
        if len(path) != factorial(n):
            print(f"  SKIP (incomplete: {len(path)}/{factorial(n)} perms): {f}")
            continue
        read += 1
        r = analyze(path, n, verbose=False)
        if r["intra"]:
            impure += 1
        hist[(r["deficit"], r["j"], r["vmL"])] += 1
        d = r["deficit"]
        if d not in minlen or len(s) < minlen[d][0]:
            minlen[d] = (len(s), f)
        if d > 0:
            slackers.append((len(s), f, r))
    print(f"words read: {read} (impure, intra w>=2 present: {impure})")
    print("(deficit, j, v-L) histogram:")
    for k, c in sorted(hist.items()):
        print(f"  deficit={k[0]} j={k[1]} v-L={k[2]} : {c}")
    print("min length by deficit:")
    for d in sorted(minlen):
        ln, f = minlen[d]
        print(f"  deficit={d}: {ln}   e.g. {f}")
    if slackers:
        print(f"SLACK WALKS ({len(slackers)}):")
        for ln, f, r in sorted(slackers)[:50]:
            print(f"  len={ln} deficit={r['deficit']} j={r['j']} "
                  f"v-L={r['vmL']} splits={r['splits']} D={r['D']} L={r['L']} {f}")
    else:
        print("SLACK WALKS: none (every input walk is a tight loop cover)")
    return read


def hunt_report(n, count, seed, wmax, outdir=None):
    """s56 mode `hunt`: materialize slack walks from random complete walks."""
    import os

    rng = random.Random(seed)
    base = factorial(n) + factorial(n - 1) + (n - 3)
    minlen = {}
    best_slack = None
    got = 0
    for _ in range(count):
        path = random_complete_walk(n, rng, wmax)
        if path is None:
            continue
        got += 1
        # score the STRING's own first-visit reading, not the raw graph path
        # (a heavy edge can spell fresh perms inside its appended block)
        s = path_to_string(path, n)
        path = first_visit_path(s, n)
        if len(path) != factorial(n):
            continue
        r = analyze(path, n, verbose=False)
        if r["intra"]:
            continue
        length = len(s)
        d = r["deficit"]
        if d not in minlen or length < minlen[d]:
            minlen[d] = length
        if d > 0 and (best_slack is None or length < best_slack[0]):
            best_slack = (length, path, r)
    print(f"walks generated: {got} (pure ones scored; base = {base})")
    print("min length by deficit:")
    for d in sorted(minlen):
        print(f"  deficit={d}: {minlen[d]}")
    if best_slack:
        length, path, r = best_slack
        print(f"SHORTEST SLACK WALK: len={length} deficit={r['deficit']} "
              f"j={r['j']} v-L={r['vmL']} splits={r['splits']} D={r['D']} L={r['L']}")
        s = path_to_string(path, n)
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            p = os.path.join(outdir, f"slack_n{n}_{length}_d{r['deficit']}.txt")
            open(p, "w").write(s + "\n")
            print(f"  wrote {p}")
        else:
            print(f"  {s}")
    else:
        print("SHORTEST SLACK WALK: none found")
    return 0


def path_to_string(path, n):
    s = "".join(map(str, path[0]))
    for a, b in zip(path, path[1:]):
        w = weight(a, b, n)
        s += "".join(map(str, b[n - w:]))
    return s


def exhaust(n, cap, maxnodes=0):
    """s56 mode `exhaust`: DFS over ALL complete first-visit walks of length
    <= cap (start perm fixed to identity, WLOG by relabelling), reporting the
    minimum length among pure SLACK walks and among pure TIGHT walks."""
    perms = [tuple(p) for p in permutations(range(1, n + 1))]
    idx = {p: i for i, p in enumerate(perms)}
    N = len(perms)
    fact1 = factorial(n - 1)
    loops = sorted({lam(p) for p in perms})
    lid = {lp: i for i, lp in enumerate(loops)}
    LOOP = [lid[lam(p)] for p in perms]
    CYC = {}
    for p in perms:
        CYC.setdefault(rotc(p), len(CYC))
    CY = [CYC[rotc(p)] for p in perms]
    # successors grouped by weight, each carrying the intermediate
    # permutations spelled inside the appended block (s34 simple-reading
    # constraint: an edge whose block spells an UNVISITED permutation never
    # occurs in a string's own first-visit reading — the string's reading is
    # a different path of the same length, enumerated separately).
    succ = [[[] for _ in range(n + 1)] for _ in range(N)]
    for i, a in enumerate(perms):
        for w in range(1, n + 1):
            head = a[w:]
            missing = [c for c in range(1, n + 1) if c not in head]
            for tail in permutations(missing):
                b = head + tail
                if b != a and weight(a, b, n) == w:
                    mids = []
                    for off in range(1, w):
                        win = a[off:] + b[n - w:n - w + off]
                        if len(set(win)) == n:
                            mids.append(idx[win])
                    succ[i][w].append((idx[b], mids))
    capw = cap - n  # budget for the sum of edge weights
    start = idx[tuple(range(1, n + 1))]

    visited = [False] * N
    visited[start] = True
    loopcnt = [0] * len(loops)   # multiplicity of each loop in the L-set
    ncyc = len(CYC)
    cyc_open = [n] * ncyc        # unvisited members per 1-cycle
    cyc_open[CY[start]] -= 1
    nopen = ncyc                 # 1-cycles still holding an unvisited perm
    best = {}                    # deficit -> min length
    stats = Counter()
    nodes = 0
    aborted = [False]

    def rec(cur, nseen, cost, S, D, Lcnt):
        # admissible arc bound: every remaining edge costs >= 1, and every
        # 1-cycle other than the current one that still holds an unvisited
        # perm needs at least one entry edge of weight >= 2 (+1 each).
        nonlocal nodes, nopen
        nodes += 1
        if maxnodes and nodes > maxnodes:
            aborted[0] = True
            return
        if nseen == N:
            splits = S - fact1
            deficit = splits + D + 1 - Lcnt
            length = cost + n
            stats[deficit] += 1
            if deficit not in best or length < best[deficit]:
                best[deficit] = length
            return
        rem = N - nseen
        for w in range(1, n + 1):
            if cost + w + (rem - 1) > capw:
                break
            for b, mids in succ[cur][w]:
                if visited[b]:
                    continue
                inter = CY[b] != CY[cur]
                if w >= 2 and not inter:
                    continue  # impure: excluded from the pure-walk ledger
                if any(not visited[m] for m in mids):
                    continue  # not a first-visit reading edge (s34)
                cb = CY[b]
                cyc_open[cb] -= 1
                closed = cyc_open[cb] == 0
                if closed:
                    nopen -= 1
                extra = nopen - (1 if cyc_open[cb] else 0)
                if cost + w + (rem - 1) + extra <= capw:
                    nS, nD, nL = S, D, Lcnt
                    added = -1
                    if inter:
                        nS += 1
                        if w >= 3:
                            nD += 1
                        elif w == 2:
                            added = LOOP[b]
                            if loopcnt[added] == 0:
                                nL += 1
                            loopcnt[added] += 1
                    visited[b] = True
                    rec(b, nseen + 1, cost + w, nS, nD, nL)
                    visited[b] = False
                    if added >= 0:
                        loopcnt[added] -= 1
                cyc_open[cb] += 1
                if closed:
                    nopen += 1
                if aborted[0]:
                    return

    sys.setrecursionlimit(max(2000, N + 100))
    rec(start, 1, 0, 1, 0, 0)
    print(f"n={n} cap={cap} nodes={nodes} aborted={aborted[0]}")
    print(f"complete pure walks by deficit: {dict(sorted(stats.items()))}")
    print("min length by deficit:")
    for d in sorted(best):
        print(f"  deficit={d}: {best[d]}")
    tight = best.get(0)
    sl = min((v for k, v in best.items() if k > 0), default=None)
    print(f"tight min = {tight}   slack min = {sl}   "
          f"SLACK TAX = {None if (tight is None or sl is None) else sl - tight}")
    return 0


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
    if mode == "slack":
        slack_report(n, expand(sys.argv[3:]))
        return 0
    if mode == "hunt":
        count = int(sys.argv[3])
        seed = int(sys.argv[4])
        wmax = int(sys.argv[5]) if len(sys.argv) > 5 else 3
        outdir = sys.argv[6] if len(sys.argv) > 6 else None
        return hunt_report(n, count, seed, wmax, outdir)
    if mode == "exhaust":
        cap = int(sys.argv[3])
        maxnodes = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        return exhaust(n, cap, maxnodes)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
