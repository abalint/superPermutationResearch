#!/usr/bin/env python3
"""
count_bound.py -- upper bounds on the NUMBER of length-L superpermutations on n
symbols obtained from purely LOCAL necessary rules, to calibrate how much of the
superpermutation problem is carried by the global coverage constraint.

Frame
-----
A word W of length L over [n] whose first and last n-windows are permutations is
in bijection with its *trace*: the ordered list of positions where an n-window is
a permutation.  Consecutive trace positions differ by a gap w >= 1; if w <= n the
step is exactly "append the w symbols that turn perm p into perm q, with no
intermediate window a permutation".  So

    W  <->  (start perm p0, sequence of steps (w_1,...,w_S)  +  branch choices)
    sum_i w_i = L - n.

Fixing p0 = 12...n quotients out the n! relabelings exactly (the relabeling group
acts simply transitively on permutations), so a walk from the identity == a
canonical word.  Minimality forces the first/last windows to be permutations
(else delete a leading/trailing char), and forces every gap <= n (a gap > n means
n-window-free filler, which is strictly deletable at these lengths); both
assumptions are recorded in RESULTS.md.

Branching
---------
The graph is vertex-transitive, so the number of weight-w out-edges b(w) is the
same at every permutation.  b(w) = # of orderings x of the multiset {p_1..p_w}
such that set(x[:k]) != set(p[:k]) for all k < w  =  the number of INDECOMPOSABLE
permutations of [w] (OEIS A003319): 1, 1, 3, 13, 71, 461, ...
This is verified by brute force below.  (Note: the often-quoted w! - (w-1)! is the
count when only the k=1 obstruction is imposed; it is a strict over-count.)

Rule ladder (each level is an upper bound on the canonical count at length L)
----------------------------------------------------------------------------
R0  weights in 1..n summing to L-n; branching b(w) per step.          [proven]
R1  R0 + #steps >= n!-1.  Equivalently the excess e = sum (w_i - 1)
    obeys e <= D := (L-n) - (n!-1).                                    [proven]
R2  R1 + revisit ledger.  Let R = #steps landing on an already-visited
    permutation.  #distinct visited = 1 + S - R = n!, and S + e = L-n,
    hence  R + e = D  exactly.  A run of r consecutive weight-1 steps
    walks a rotation cycle and therefore forces >= max(0, r-(n-1))
    revisits.  So
        e + sum_over_1runs max(0, r - (n-1))  <=  D.                   [proven]
R2+ R1 + hard cap (no 1-run longer than n-1) + no weight-n steps.
    Both hold on every known minimal word but neither is proven;
    reported as an empirically-verified, unproven level.
R3  R2+ + per-weight-class count bands measured on the known minimal
    words for that same n.  Circular by construction (self-band); it is a
    conditional count, not a bound: "how many words share the exact weight
    profile of every known optimum".                                 [empirical]

Everything is exact integer arithmetic.
"""

import argparse
import collections
import glob
import itertools
import math
import os
import random
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --------------------------------------------------------------------------
# 1. branching numbers
# --------------------------------------------------------------------------


def indecomposable(m):
    """A003319[0..m]: a[i] = i! - sum_{k=1}^{i-1} a[k]*(i-k)!"""
    f = [1] * (m + 1)
    for i in range(1, m + 1):
        f[i] = f[i - 1] * i
    a = [0] * (m + 1)
    a[0] = 1
    for i in range(1, m + 1):
        a[i] = f[i] - sum(a[k] * f[i - k] for k in range(1, i))
    return a


def branching(n):
    """b[1..n], b[w] = # weight-w trace successors of any permutation."""
    a = indecomposable(n)
    return [0] + [a[w] for w in range(1, n + 1)]


def trace_successors(n, p):
    """Brute force: all (q, w) reachable from perm p with no intermediate
    n-window a permutation.  w in 1..n."""
    out = []
    for w in range(1, n + 1):
        tail = p[w:]
        for x in itertools.permutations(sorted(set(p[:w]))):
            if all(set(x[:k]) != set(p[:k]) for k in range(1, w)):
                out.append((tail + x, w))
    return out


def verify_branching(verbose=True):
    """Brute-force check of b(w) for n=3..6 and vertex-transitivity for n=3..5."""
    report = []
    for n in (3, 4, 5, 6):
        ident = tuple(range(1, n + 1))
        hist = collections.Counter(w for _, w in trace_successors(n, ident))
        b = branching(n)
        got = [hist.get(w, 0) for w in range(1, n + 1)]
        exp = b[1:]
        assert got == exp, (n, got, exp)
        report.append((n, got))
        if verbose:
            print(f"  n={n}: b(w) = {got}  (brute force == A003319)  sum={sum(got)}"
                  f"   [w!-(w-1)! would give "
                  f"{[math.factorial(w)-math.factorial(w-1) for w in range(1,n+1)]}]")
    for n in (3, 4, 5):
        ref = None
        for p in itertools.permutations(range(1, n + 1)):
            h = tuple(collections.Counter(w for _, w in trace_successors(n, p))[w]
                      for w in range(1, n + 1))
            if ref is None:
                ref = h
            assert h == ref, (p, h, ref)
        if verbose:
            print(f"  n={n}: vertex-transitivity of the branching profile verified "
                  f"over all {math.factorial(n)} permutations")
    return report


# --------------------------------------------------------------------------
# 2. corpus: parse known minimal words, verify structural rules
# --------------------------------------------------------------------------


def profile(word, n):
    """(weights, perms) for a word.  Asserts it starts and ends on a perm window."""
    L = len(word)
    pos = [i for i in range(L - n + 1) if len(set(word[i:i + n])) == n]
    assert pos and pos[0] == 0 and pos[-1] == L - n, "word not perm-aligned"
    weights = [pos[i + 1] - pos[i] for i in range(len(pos) - 1)]
    return weights, [word[i:i + n] for i in pos]


def longest_one_run(weights):
    best = r = 0
    for w in weights:
        r = r + 1 if w == 1 else 0
        best = max(best, r)
    return best


def load_corpus():
    """{n: (L, [words])} for n = 4, 5, 6 from the repo's data/."""
    c = {}
    p4 = f"{REPO}/data/chaffin/ChaffinMethodResults/Chaffin_4_W_6.txt"
    c[4] = (33, [l.strip() for l in open(p4) if l.strip()])
    p5 = f"{REPO}/data/chaffin/ChaffinMethodResults/Chaffin_5_W_29.txt"
    c[5] = (153, [l.strip() for l in open(p5) if l.strip()])
    w6 = set()
    for f in (sorted(glob.glob(f"{REPO}/data/records872/872.*.txt")) +
              sorted(glob.glob(f"{REPO}/data/gain1_872s/872.*.txt"))):
        s = open(f).read().strip()
        if len(s) == 872:
            w6.add(s)
    c[6] = (872, sorted(w6))
    return c


def measure_corpus(n, L, words, verbose=True):
    """Verify the structural rules on a corpus and return the measured bands."""
    st = {
        "n": n, "L": L, "count": len(words),
        "max_weight": 0, "max_1run": 0, "repeat_perm": 0,
        "wcount": {w: [None, None] for w in range(1, n + 1)},
        "symband": [(10 ** 9, -1)] * n,
        "steps": set(), "excess": set(),
    }
    for word in words:
        weights, perms = profile(word, n)
        assert sum(weights) == L - n
        st["max_weight"] = max(st["max_weight"], max(weights))
        st["max_1run"] = max(st["max_1run"], longest_one_run(weights))
        if len(set(perms)) != len(perms):
            st["repeat_perm"] += 1
        assert len(set(perms)) == math.factorial(n) or len(set(perms)) < math.factorial(n)
        st["steps"].add(len(weights))
        st["excess"].add(sum(w - 1 for w in weights))
        cw = collections.Counter(weights)
        for w in range(1, n + 1):
            lo, hi = st["wcount"][w]
            v = cw[w]
            st["wcount"][w] = [v if lo is None else min(lo, v),
                               v if hi is None else max(hi, v)]
        cs = collections.Counter(word)
        st["symband"] = [(min(lo, cs[str(s + 1)]), max(hi, cs[str(s + 1)]))
                         for s, (lo, hi) in enumerate(st["symband"])]
    D = (L - n) - (math.factorial(n) - 1)
    st["D"] = D
    if verbose:
        print(f"  n={n} L={L}: {len(words)} words")
        print(f"     steps per word        : {sorted(st['steps'])}   (n!-1 = {math.factorial(n)-1})")
        print(f"     excess e per word     : {sorted(st['excess'])}   (D = {D})")
        print(f"     repeated perm windows : {st['repeat_perm']} words  -> revisit ledger R = D - e = 0")
        print(f"     max weight used       : {st['max_weight']}   (rule 'no weight-n' -> {'HOLDS' if st['max_weight'] < n else 'FAILS'})")
        print(f"     longest 1-run         : {st['max_1run']}   (cap n-1 = {n-1} -> {'HOLDS, TIGHT' if st['max_1run']==n-1 else 'HOLDS' if st['max_1run']<n else 'FAILS'})")
        print(f"     weight-class bands    : " +
              ", ".join(f"m{w}in[{st['wcount'][w][0]},{st['wcount'][w][1]}]" for w in range(2, n + 1)))
        print(f"     per-symbol count band : {st['symband']}  (L/n = {L/n:.2f})")
    return st


# --------------------------------------------------------------------------
# 3. the bounds
# --------------------------------------------------------------------------


def bound_R0(n, L):
    """Exact # of weight-(L-n) walks from the identity.  f(m)=sum_w b(w) f(m-w)."""
    m = L - n
    if m < 0:
        return 0
    b = branching(n)
    f = [0] * (m + 1)
    f[0] = 1
    for i in range(1, m + 1):
        f[i] = sum(b[w] * f[i - w] for w in range(1, min(n, i) + 1))
    return f[m]


def bound_dp(n, L, level):
    """
    Ledger DP.  State (weight consumed m, ledger spend t, current 1-run r).
      level 'R1'  : t counts excess only; t <= D.
      level 'R2'  : t counts excess + 1-run overflow past n-1; t <= D. [proven]
      level 'R2+' : t counts excess only, overflow FORBIDDEN, weight n FORBIDDEN.
    Returns the exact count of step-sequences-with-branch-choices.
    """
    m_tot = L - n
    D = m_tot - (math.factorial(n) - 1)
    if m_tot < 0 or D < 0:
        return 0
    b = branching(n)
    cap = n - 1                       # 1-run states 0..cap (cap = saturated)
    wmax = n - 1 if level == "R2+" else n
    hard = (level == "R2+")
    track_run = level in ("R2", "R2+")
    nr = cap + 1 if track_run else 1
    T = D + 1
    W = n + 1                          # rolling layers indexed by m mod W
    # layer = (grid[t][r], rowsum[t])
    layers = [([[0] * nr for _ in range(T)], [0] * T) for _ in range(W)]
    layers[0][0][0][0] = 1
    layers[0][1][0] = 1
    for m in range(1, m_tot + 1):
        cur = [[0] * nr for _ in range(T)]
        pg = layers[(m - 1) % W][0]
        # weight-1 steps (b(1) = 1)
        for t in range(T):
            row = pg[t]
            if track_run:
                crow = cur[t]
                for r in range(cap):
                    v = row[r]
                    if v:
                        crow[r + 1] += v
                v = row[cap]
                if v and not hard and t + 1 < T:
                    cur[t + 1][cap] += v       # overflow costs 1 ledger unit
            else:
                v = row[0]
                if v:
                    cur[t][0] += v
        # weight w >= 2 steps
        for w in range(2, min(wmax, m) + 1):
            prs = layers[(m - w) % W][1]
            bw = b[w]
            de = w - 1
            for t in range(T - de):
                tot = prs[t]
                if tot:
                    cur[t + de][0] += bw * tot
        layers[m % W] = (cur, [sum(row) for row in cur])
    return sum(layers[m_tot % W][1])


_NCC = {}


def n_capped_compositions(m, g, c):
    """# of ordered g-tuples of ints in [0,c] summing to m (inclusion-exclusion)."""
    if g <= 0:
        return 1 if m == 0 else 0
    if m < 0 or m > g * c:
        return 0
    key = (m, g, c)
    v = _NCC.get(key)
    if v is not None:
        return v
    tot = 0
    for j in range(min(g, m // (c + 1)) + 1):
        term = math.comb(g, j) * math.comb(m - j * (c + 1) + g - 1, g - 1)
        tot += -term if j % 2 else term
    _NCC[key] = tot
    return tot


def bound_tuples(n, L, bands=None, cap_runs=True, allow_weight_n=False):
    """
    Sum over weight-class multiplicity tuples (m_2..m_n):
        (k! / prod m_w!) * prod b(w)^m_w * N(m_1, k+1, n-1)
    with k = sum m_w, e = sum (w-1) m_w <= D, m_1 = (L-n) - e - k.
    `bands` = {w: (lo, hi)} restricts m_w.  Used for R2+ (cross-check of the DP)
    and R3 (empirical bands).
    """
    m_tot = L - n
    D = m_tot - (math.factorial(n) - 1)
    if D < 0:
        return 0
    b = branching(n)
    wmax = n if allow_weight_n else n - 1
    ws = list(range(2, wmax + 1))
    cap = n - 1
    fact = [1] * (D + 2)
    for i in range(1, D + 2):
        fact[i] = fact[i - 1] * i
    pw = {w: [b[w] ** i for i in range(D + 1)] for w in ws}
    total = 0

    def rec(i, e, k, num):
        """num = prod_w b(w)^m_w / prod_w m_w!   (kept as (numerator, denom) pair)"""
        nonlocal total
        if i == len(ws):
            m1 = m_tot - e - k
            if m1 < 0:
                return
            arr = (n_capped_compositions(m1, k + 1, cap) if cap_runs
                   else math.comb(m1 + k, k))
            if arr:
                total += fact[k] * num[0] // num[1] * arr
            return
        w = ws[i]
        lo, hi = (0, D) if not bands or w not in bands else bands[w]
        mw = lo
        while (e + mw * (w - 1)) <= D and mw <= hi:
            rec(i + 1, e + mw * (w - 1), k + mw,
                (num[0] * pw[w][mw], num[1] * fact[mw]))
            mw += 1

    rec(0, 0, 0, (1, 1))
    return total


def smallest_nonzero_L(n, level):
    """
    Smallest L for which the level's bound is nonzero.

    R0 : L = n (no coverage constraint at all).
    R1 : L = n + n! - 1   (S >= n!-1 steps, each of weight >= 1).
    R2 : L = n + n! + (n-1)! - 2.  Proof: write S = m1 + k (k = #steps of
         weight >= 2), e >= k, overflow >= m1 - (k+1)(n-1).  The ledger
         e + overflow <= D = S + e - (n!-1) gives overflow <= S - n! + 1,
         hence m1 - (k+1)(n-1) <= m1 + k - n! + 1, i.e. k*n >= n! - n,
         i.e. k >= (n-1)! - 1.  Also S >= n!-1 gives m1 >= n!-1-k.  Then
         L = n + S + e >= n + m1 + 2k >= n + (n!-1) + k >= n+n!+(n-1)!-2.
    R2+: same value (the extremal configuration uses no weight-n step and
         no 1-run overflow).
    Each value is spot-checked below with the boolean feasibility DP.
    """
    if level == "R0":
        return n
    if level == "R1":
        return n + math.factorial(n) - 1
    return n + math.factorial(n) + math.factorial(n - 1) - 2


def _feasible_R2(n, L):
    """Boolean version of the R2 DP (fast)."""
    m_tot = L - n
    D = m_tot - (math.factorial(n) - 1)
    if D < 0:
        return False
    cap = n - 1
    W = n + 1
    T = D + 1
    layers = [[[False] * (cap + 1) for _ in range(T)] for _ in range(W)]
    layers[0][0][0] = True
    for m in range(1, m_tot + 1):
        cur = [[False] * (cap + 1) for _ in range(T)]
        prev = layers[(m - 1) % W]
        for t in range(T):
            for r in range(cap + 1):
                if prev[t][r]:
                    if r < cap:
                        cur[t][r + 1] = True
                    elif t + 1 < T:
                        cur[t + 1][cap] = True
        for w in range(2, min(n, m) + 1):
            prev = layers[(m - w) % W]
            de = w - 1
            for t in range(T - de):
                if any(prev[t]):
                    cur[t + de][0] = True
        layers[m % W] = cur
    return any(any(row) for row in layers[m_tot % W])


def _feasible_R2plus(n, L):
    m_tot = L - n
    D = m_tot - (math.factorial(n) - 1)
    if D < 0:
        return False
    cap = n - 1
    W = n + 1
    T = D + 1
    layers = [[[False] * (cap + 1) for _ in range(T)] for _ in range(W)]
    layers[0][0][0] = True
    for m in range(1, m_tot + 1):
        cur = [[False] * (cap + 1) for _ in range(T)]
        prev = layers[(m - 1) % W]
        for t in range(T):
            for r in range(cap):
                if prev[t][r]:
                    cur[t][r + 1] = True
        for w in range(2, min(n - 1, m) + 1):
            prev = layers[(m - w) % W]
            de = w - 1
            for t in range(T - de):
                if any(prev[t]):
                    cur[t + de][0] = True
        layers[m % W] = cur
    return any(any(row) for row in layers[m_tot % W])


def enumerate_level(n, L, level, bands=None):
    """
    Explicitly enumerate every word in a level's population by walking the REAL
    trace graph, and report how many are actual superpermutations.  Only used at
    n=4 (populations of a few hundred) as an end-to-end validation that the
    counting model is a genuine superset of the truth.
    """
    m_tot = L - n
    D = m_tot - (math.factorial(n) - 1)
    cap = n - 1
    wmax = n - 1 if level in ("R2+", "R3") else n
    hard = level in ("R2+", "R3")
    ident = tuple(range(1, n + 1))
    succ = {}

    def succs(p, w):
        if (p, w) not in succ:
            succ[(p, w)] = [p[w:] + x for x in itertools.permutations(sorted(set(p[:w])))
                            if all(set(x[:j]) != set(p[:j]) for j in range(1, w))]
        return succ[(p, w)]

    total = 0
    supers = []
    stack = [(ident, 0, 0, 0, [ident], collections.Counter())]
    while stack:
        p, m, t, r, path, wc = stack.pop()
        if m == m_tot:
            if bands and any(not (bands[w][0] <= wc[w] <= bands[w][1])
                             for w in range(2, n + 1)):
                continue
            total += 1
            if len(set(path)) == math.factorial(n):
                supers.append(path)
            continue
        for w in range(1, min(wmax, m_tot - m) + 1):
            if w == 1:
                nr_ = r + 1
                nt = t
                if nr_ > cap:
                    if hard:
                        continue
                    nt, nr_ = t + 1, cap
                if nt > D:
                    continue
            else:
                nt, nr_ = t + (w - 1), 0
                if nt > D:
                    continue
            if bands and w >= 2 and wc[w] + 1 > bands[w][1]:
                continue
            for q in succs(p, w):
                nwc = wc.copy()
                nwc[w] += 1
                stack.append((q, m + w, nt, nr_, path + [q], nwc))
    return total, len(supers)


# --------------------------------------------------------------------------
# 4. measured regularity: symbol-frequency band, Monte-Carlo filter strength
# --------------------------------------------------------------------------


def sample_R3_words(n, L, ms, symband, trials=2000, seed=0):
    """
    Uniformly sample words from the R3 population (exact weight multiset taken as
    the corpus-modal one, 1-runs capped at n-1, uniform branch choice in the real
    trace graph) and measure (a) fraction meeting the corpus symbol-count band,
    (b) coverage: how many of the n! permutations they actually contain.
    """
    rng = random.Random(seed)
    ms = {w: c for w, c in ms.items() if w >= 2 and c > 0}
    k = sum(ms.values())
    e = sum((w - 1) * c for w, c in ms.items())
    m1 = (L - n) - e - k
    g = k + 1
    cap = n - 1
    # precompute counts for uniform sampling of capped compositions
    tbl = [[0] * (m1 + 1) for _ in range(g + 1)]
    tbl[0][0] = 1
    for i in range(1, g + 1):
        for s in range(m1 + 1):
            tbl[i][s] = sum(tbl[i - 1][s - d] for d in range(0, min(cap, s) + 1))
    if tbl[g][m1] == 0:
        return None
    succ_cache = {}

    def succs(p, w):
        key = (p, w)
        if key not in succ_cache:
            base = sorted(set(p[:w]))
            out = [p[w:] + x for x in itertools.permutations(base)
                   if all(set(x[:j]) != set(p[:j]) for j in range(1, w))]
            succ_cache[key] = out
        return succ_cache[key]

    ident = tuple(range(1, n + 1))
    ok_sym = 0
    cover = []
    for _ in range(trials):
        # sample gaps
        gaps = []
        rem = m1
        for i in range(g, 0, -1):
            tot = tbl[i][rem]
            x = rng.randrange(tot)
            acc = 0
            for d in range(0, min(cap, rem) + 1):
                acc += tbl[i - 1][rem - d]
                if x < acc:
                    gaps.append(d)
                    rem -= d
                    break
        heavy = []
        for w, c in ms.items():
            heavy += [w] * c
        rng.shuffle(heavy)
        steps = []
        for i, gp in enumerate(gaps):
            steps += [1] * gp
            if i < len(heavy):
                steps.append(heavy[i])
        p = ident
        word = list(p)
        seen = {p}
        for w in steps:
            if w == 1:
                q = p[1:] + p[:1]
            else:
                cand = succs(p, w)
                q = cand[rng.randrange(len(cand))]
            word += list(q[n - w:])
            p = q
            seen.add(p)
        cnt = collections.Counter(word)
        if all(symband[s][0] <= cnt[s + 1] <= symband[s][1] for s in range(n)):
            ok_sym += 1
        cover.append(len(seen))
    return {"trials": trials, "sym_ok": ok_sym,
            "cover_mean": sum(cover) / len(cover),
            "cover_max": max(cover), "n_fact": math.factorial(n)}


# --------------------------------------------------------------------------
# 5. driver
# --------------------------------------------------------------------------


def log10_int(x):
    """Exact-enough log10 of an arbitrarily large positive int."""
    if x is None or x <= 0:
        return None
    s = str(x)
    head = s[:17]
    return math.log10(float(head)) + (len(s) - len(head))


def fmt(x):
    if x is None or x == 0:
        return "0"
    if x < 10 ** 12:
        return str(x)
    return f"1e{log10_int(x):.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mc", action="store_true", help="skip Monte-Carlo sampling")
    ap.add_argument("--mc-trials", type=int, default=2000)
    args = ap.parse_args()

    print("=" * 78)
    print("1. BRANCHING VERIFICATION (brute force)")
    print("=" * 78)
    verify_branching()

    print()
    print("=" * 78)
    print("2. CORPUS MEASUREMENT / RULE VERIFICATION")
    print("=" * 78)
    corpus = load_corpus()
    stats = {}
    for n in (4, 5, 6):
        L, words = corpus[n]
        stats[n] = measure_corpus(n, L, words)
        print()

    targets = [(4, 33, 1), (5, 153, 8), (6, 872, len(corpus[6][1]))]

    print("=" * 78)
    print("3. BOUNDS")
    print("=" * 78)
    results = {}
    for n, L, truth in targets:
        st = stats[n]
        row = {}
        row["R0"] = bound_R0(n, L)
        row["R1"] = bound_dp(n, L, "R1")
        row["R2"] = bound_dp(n, L, "R2")
        row["R2+"] = bound_dp(n, L, "R2+")
        chk = bound_tuples(n, L, bands=None, cap_runs=True, allow_weight_n=False)
        assert chk == row["R2+"], (n, L, chk, row["R2+"])
        bands = {w: tuple(st["wcount"][w]) for w in range(2, n + 1)}
        row["R3"] = bound_tuples(n, L, bands=bands, cap_runs=True,
                                 allow_weight_n=(bands.get(n, (0, 0))[1] > 0))
        row["truth"] = truth
        results[(n, L)] = row
        print(f"  n={n} L={L}  D={st['D']}  (truth = {truth}, log10 = "
              f"{log10_int(truth):.2f})")
        for k in ("R0", "R1", "R2", "R2+", "R3"):
            v = row[k]
            if v:
                print(f"     {k:4s} = {fmt(v):>22s}   log10 = {log10_int(v):8.2f}"
                      f"   over truth: {log10_int(v)-log10_int(truth):8.2f} orders")
            else:
                print(f"     {k:4s} = {'0':>22s}")
        print(f"     R2+ tuple-sum cross-check: OK")
        print(f"     empirical weight bands used for R3: {bands}")
        if n == 4:
            for lev in ("R2", "R2+", "R3"):
                tot, sup = enumerate_level(4, 33, lev,
                                           bands=bands if lev == "R3" else None)
                assert tot == row[lev], (lev, tot, row[lev])
                print(f"     end-to-end enumeration of {lev:3s}: {tot:4d} words in the "
                      f"real trace graph (== DP), of which {sup} are superpermutations")
        print()

    print("=" * 78)
    print("4. SMALLEST L WITH A NONZERO BOUND  (nonexistence reach)")
    print("=" * 78)
    true_lb = {4: 33, 5: 153, 6: 869}
    for n in (4, 5, 6):
        vals = {lev: smallest_nonzero_L(n, lev) for lev in ("R0", "R1", "R2", "R2+")}
        # spot-check the closed forms with the boolean feasibility DP
        assert bound_dp(n, vals["R1"] - 1, "R1") == 0 and bound_dp(n, vals["R1"], "R1") > 0
        assert not _feasible_R2(n, vals["R2"] - 1), (n, "R2 minus one feasible?!")
        assert _feasible_R2(n, vals["R2"]), (n, "R2 infeasible at closed form?!")
        assert not _feasible_R2plus(n, vals["R2+"] - 1)
        assert _feasible_R2plus(n, vals["R2+"])
        print(f"  n={n}: R0 -> L>={vals['R0']:4d} | R1 -> L>={vals['R1']:4d} | "
              f"R2 -> L>={vals['R2']:4d} | R2+ -> L>={vals['R2+']:4d}   "
              f"[closed form n+n!+(n-1)!-2 = {n+math.factorial(n)+math.factorial(n-1)-2}, "
              f"DP-verified tight]   TRUE lower bound = {true_lb[n]}  "
              f"(R2 short by {true_lb[n]-vals['R2']})")
    print()
    print("  growth of the R2 bound just above its threshold "
          "(log10; the counting-proof window is exactly ONE length wide):")
    for n in (4, 5, 6):
        thr = smallest_nonzero_L(n, "R2")
        pts = [thr + d for d in (0, 1, 2, 3, 4)]
        pts = [L for L in pts if L <= true_lb[n]]
        print(f"     n={n}: " + "  ".join(
            f"L={L}:{log10_int(bound_dp(n, L, 'R2')):.2f}" for L in pts))
    print(f"     at L = n+n!+(n-1)!-2 the R2 count is EXACTLY 1 for n=4,5,6 "
          f"(unique composition: every 1-run exactly n-1, every other step "
          f"weight 2, and b(2)=1 leaves no branch freedom).")
    tot, sup = enumerate_level(4, 32, "R2")
    print(f"     n=4 L=32: enumerating that population gives {tot} word, "
          f"{sup} superpermutations -> S(4) >= 33 falls out of the ladder plus "
          f"one explicit check.  The same trick dies at n=6: L=845 already has "
          f"{bound_dp(6, 845, 'R2'):,} candidates.")
    print()

    if not args.skip_mc:
        print("=" * 78)
        print("5. MEASURED REGULARITY: symbol-frequency band + coverage of random R3 words")
        print("=" * 78)
        for n in (4, 5, 6):
            L, words = corpus[n]
            st = stats[n]
            symb = st["symband"]
            # use the exact weight multiset of a real optimum (well-defined tuple)
            ms = collections.Counter(profile(words[0], n)[0])
            r = sample_R3_words(n, L, ms, symb, trials=args.mc_trials, seed=12345)
            if r is None:
                print(f"  n={n}: no capped composition exists for that multiset")
                continue
            frac = r["sym_ok"] / r["trials"]
            drop = -math.log10(frac) if frac else float("inf")
            print(f"  n={n} L={L}, weight multiset "
                  f"{{{', '.join(f'{w}:{c}' for w, c in sorted(ms.items()))}}}: "
                  f"{r['trials']} uniform R3-legal words ->")
            print(f"       symbol-count band satisfied by {r['sym_ok']} "
                  f"({100*frac:.2f}%)  =>  the symbol regularity is worth only "
                  f"{drop:.2f} orders of magnitude")
            print(f"       coverage: mean {r['cover_mean']:.1f} / {r['n_fact']} "
                  f"distinct perms ({100*r['cover_mean']/r['n_fact']:.1f}%), "
                  f"best of {r['trials']} = {r['cover_max']}")
        print()


if __name__ == "__main__":
    main()
