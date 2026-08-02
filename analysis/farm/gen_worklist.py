#!/usr/bin/env python3
"""gen_worklist.py -- enumerate the V7=15 (length-5905) kernel-chain tiers and
emit KernelFinder `nsk` ride-length patterns, in priority order.

Run from analysis/ :  python3 gen_worklist.py worklist.txt

Chain machinery mirrors analysis/kernelchain7/enum15.py; pattern semantics
mirror analysis/cover7/chain7.py:

    chain tuple = (L, k, j, sk, s, t, c)
    ride length of a loop = ((exit_splice j - arrival entry k) mod 6) + 1
    terminal loop (j = None) rides 6 - sk orbits
    pattern = concatenation of the per-loop ride lengths, len(pattern) == K

Every chain here uses cost-3 hops only, so V = K - Sigma; V = 15 <=> Sigma =
K - 15.  Terminal loops are allowed a partial ride (chain7.verify_chain permits
0 <= sk <= 5 on the last element); including that is what makes the tier counts
come out at the published 5 / 21 / 48 / 149.

VALIDATION GATE: the K=27 tier must regenerate the five patterns already
running in F:\\superpermFarm\\runs\\c0..c4 (farmlaunch.ps1).  The script asserts
this and refuses to emit a worklist otherwise.
"""
from itertools import permutations
import sys

N = 7; ALPHA = "1234567"; NE = 6

# s64 P1: ONE copy of the rotation-frame quartet, in pylib/canonical.py.
# `canon` here is the least-ROTATION canon -- NOT m3_check's relabel+reversal
# canon.  pylib keeps the two apart by name (canon_rotation vs
# canon_relabel_rev); the local alias preserves every call site below.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
from pylib.canonical import canon_rotation as canon, door, loop_of, tv  # noqa: E402,F401

# ---------------------------------------------------------------- loop tables
loops = []
for pivot in ALPHA:
    rest = [c for c in ALPHA if c != pivot]; seen = set()
    for p in permutations(rest):
        nk = canon("".join(p))
        if nk not in seen:
            seen.add(nk); loops.append((pivot, nk))
li = {lp: i for i, lp in enumerate(loops)}
entries, sources, orbitsets = [], [], []
for (a, C) in loops:
    e = C + a; es, ss, os_ = [], [], set()
    for _ in range(NE):
        es.append(e); ss.append(e[-1] + e[:-1]); os_.add(canon(e)); e = tv(e)
    entries.append(es); sources.append(ss); orbitsets.append(frozenset(os_))

ID = canon(ALPHA)
cls = [L for L in range(840) if loops[L][0] == '7']      # one pivot class
lidx = {L: i for i, L in enumerate(cls)}
E3 = [[None] * NE for _ in range(120)]                   # cost-3 hop successor
for i, L in enumerate(cls):
    for j, s in enumerate(sources[L]):
        t = door(s, 3); M = li[loop_of(t)]
        E3[i][j] = (lidx[M], entries[M].index(t))
L0g = [L for L in cls if ID in orbitsets[L]][0]
L0 = lidx[L0g]; K0 = [canon(e) for e in entries[L0g]].index(ID)


def enum_exact(Ktar, Star):
    """All cost-3 chains of exactly Ktar loops whose non-terminal skips sum to
    Star (the terminal loop's own skip is added by enum_tier)."""
    out = []
    def dfs(i, k, used, K, pen, path):
        if K == Ktar:
            if pen == Star: out.append(list(path))
            return
        if pen > Star or Star - pen > 5 * (Ktar - K): return
        for s in range(NE):
            if pen + s > Star: break
            j = (k - 1 - s) % NE
            M, ka = E3[i][j]
            if used >> M & 1: continue
            dfs(M, ka, used | (1 << M), K + 1, pen + s, path + [(i, k, j, s)])
    dfs(L0, K0, 1 << L0, 1, 0, [])
    return out


def pattern(path, term_skip):
    """Ride-length digit string for a chain given its hop path + terminal skip."""
    digits = [((j - k) % NE) + 1 for (i, k, j, s) in path]
    digits.append(NE - term_skip)
    return ''.join(str(d) for d in digits)


def enum_tier(K, Sigma):
    """All V=15 chains with K loops and total skip Sigma, as nsk patterns."""
    pats = []
    for t in range(0, NE):                       # terminal loop skip
        for path in enum_exact(K, Sigma - t):
            pats.append(pattern(path, t))
    assert len(set(pats)) == len(pats), f"duplicate patterns in K={K}"
    for p in pats:
        assert len(p) == K
        assert sum(NE - int(d) for d in p) == Sigma
    return sorted(pats)


KNOWN_K27 = [
    '666646664666466466646664666',
    '666646664664666466466646666',
    '666646646664666466466646666',
    '666646664664666466646646666',
    '666466646664664666466646666',
]

TIERS = [(27, 12), (29, 14), (30, 15), (31, 16)]   # V = K - Sigma = 15

if __name__ == '__main__':
    tiers = {}
    for (K, S) in TIERS:
        tiers[K] = enum_tier(K, S)
        print(f"K={K} Sigma={S}: {len(tiers[K])} chains", file=sys.stderr)

    # ---- VALIDATION GATE ----
    got, want = set(tiers[27]), set(KNOWN_K27)
    if got != want:
        print("VALIDATION GATE FAILED", file=sys.stderr)
        print("  missing: ", sorted(want - got), file=sys.stderr)
        print("  extra:   ", sorted(got - want), file=sys.stderr)
        sys.exit(1)
    print("VALIDATION GATE PASSED: K=27 patterns match the five running chains",
          file=sys.stderr)

    # Priority order: K=29, then K=30, then K=31. K=27 is already running in
    # runs\c0..c4 and is deliberately NOT part of the worklist.
    out = []
    for K in (29, 30, 31):
        out.extend(tiers[K])
    dest = sys.argv[1] if len(sys.argv) > 1 else 'worklist.txt'
    with open(dest, 'w', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')
    print(f"wrote {len(out)} patterns to {dest}", file=sys.stderr)
