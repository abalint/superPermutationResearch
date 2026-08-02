#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s62/jtax/cover_search.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s62 D1: EXHAUSTIVE decision of the PERFECT-RIDE family at any n.

Family F(n)  =  pure complete first-visit walks with
      splits = 0   and   v = (n-2)!   (the minimum the loop-supply bound allows)
It is exactly the family that the MASTER inequality forces on any j>=1 walk
at the bottom of the length ladder (LOG.md D1.3).  In F(n):
  * every 1-cycle carries exactly ONE arc, a full n-perm ride
  * the v = (n-2)! entered 2-loops EXACTLY COVER the (n-1)! 1-cycles, so the
    arc-start of every cycle is DETERMINED by the cover
  * the walk is R maximal w2-runs joined by R-1 doors, and
        length = BASE + R + xp,   j = R - (n-2)!,   xp = sum_doors (w-3)
    with BASE = n! + (n-1)! + (n-3) - (n-2)! + ... see LOG (n=6: length=843+R+xp)

Search: for every exact cover containing lam(identity) -- the walk's first
perm may be taken = identity by relabeling -- every walk of F(n) with
length <= TMAX.  Deterministic, exhaustive within the family.

Usage: cover_search.py <n> <TMAX> [--jmin K] [--wmax W] [--verbose]
"""
import sys
import time
from itertools import permutations
from math import factorial
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib62 import rotc, lam, weight  # noqa: E402


def build(N):
    PERMS = list(permutations(range(1, N + 1)))
    PIDX = {p: i for i, p in enumerate(PERMS)}
    CYC = {}
    for p in PERMS:
        CYC.setdefault(rotc(p), len(CYC))
    CYCOF = [CYC[rotc(p)] for p in PERMS]
    LOOPID = {}
    for p in PERMS:
        LOOPID.setdefault(lam(p), len(LOOPID))
    LOOPOF = [LOOPID[lam(p)] for p in PERMS]
    G = [PIDX[p[1:N - 1] + (p[0], p[N - 1])] for p in PERMS]
    ROTINV = [PIDX[p[-1:] + p[:-1]] for p in PERMS]
    LOOPCELLS = [[] for _ in range(len(LOOPID))]
    for i in range(len(PERMS)):
        LOOPCELLS[LOOPOF[i]].append(i)
    LOOPMASK = [sum(1 << CYCOF[i] for i in cells) for cells in LOOPCELLS]
    DOORS = {}
    for w in range(3, N + 1):
        tbl = []
        for i, a in enumerate(PERMS):
            outs = []
            head = a[w:]          # weight w <=> overlap n-w
            for tail in permutations(a[:w]):
                b = head + tail
                jb = PIDX[b]
                if weight(a, b, N) == w and CYCOF[jb] != CYCOF[i]:
                    outs.append(jb)
            tbl.append(outs)
        DOORS[w] = tbl
    return dict(N=N, PERMS=PERMS, PIDX=PIDX, NCYC=len(CYC), CYCOF=CYCOF,
                LOOPOF=LOOPOF, NLOOP=len(LOOPID), G=G, ROTINV=ROTINV,
                LOOPCELLS=LOOPCELLS, LOOPMASK=LOOPMASK, DOORS=DOORS)


def all_covers(B):
    NCYC, NLOOP = B["NCYC"], B["NLOOP"]
    inc = [[] for _ in range(NCYC)]
    for l in range(NLOOP):
        for c in B["LOOPCELLS"][l]:
            inc[B["CYCOF"][c]].append(l)
    full = (1 << NCYC) - 1
    out = []

    def rec(cov, chosen):
        if cov == full:
            out.append(tuple(chosen))
            return
        c = 0
        while cov >> c & 1:
            c += 1
        for l in inc[c]:
            if B["LOOPMASK"][l] & cov:
                continue
            chosen.append(l)
            rec(cov | B["LOOPMASK"][l], chosen)
            chosen.pop()
    rec(0, [])
    return out


def run(N, TMAX, jmin=1, wmax=None, verbose=False):
    t0 = time.time()
    B = build(N)
    NCYC = B["NCYC"]
    RUNMAX = N - 1                      # a run rides at most n-1 arcs
    VMIN = factorial(N - 2)
    BASE = factorial(N) + factorial(N - 1) + (N - 3)   # length = BASE + R + xp
    if wmax is None:
        wmax = N
    covers = all_covers(B)
    lam0 = B["LOOPOF"][B["PIDX"][tuple(range(1, N + 1))]]
    sel = [c for c in covers if lam0 in c]
    print(f"n={N}: {NCYC} cycles, {B['NLOOP']} loops, cover size {VMIN}; "
          f"exact covers {len(covers)}, containing lam(id) {len(sel)}")
    print(f"length = {BASE} + R + xp,  j = R - {VMIN};  "
          f"TMAX={TMAX} jmin={jmin} wmax={wmax}")
    best, nodes, wit = {}, 0, {}
    start = B["PIDX"][tuple(range(1, N + 1))]
    G, ROTINV, CYCOF, DOORS = B["G"], B["ROTINV"], B["CYCOF"], B["DOORS"]
    for cov in sel:
        entry = [0] * NCYC
        for l in cov:
            for i in B["LOOPCELLS"][l]:
                entry[CYCOF[i]] = i
        isentry = bytearray(len(B["PERMS"]))
        for c in range(NCYC):
            isentry[entry[c]] = 1
        stack = []

        def rec(e, used, nused, runs, xp, runlen):
            nonlocal nodes
            nodes += 1
            if nused == NCYC:
                ln = BASE + runs + xp
                j = runs - VMIN
                if j >= jmin and ln <= TMAX and (j not in best or ln < best[j]):
                    best[j] = ln
                    wit[j] = (cov, list(stack))
                return
            rem = NCYC - nused
            extra = rem - (RUNMAX - runlen)
            addruns = 0 if extra <= 0 else -(-extra // RUNMAX)
            if BASE + runs + addruns + xp > TMAX:
                return
            if runlen < RUNMAX:
                nb = G[e]
                c = CYCOF[nb]
                if not (used >> c & 1):
                    stack.append((2, nb))
                    rec(nb, used | (1 << c), nused + 1, runs, xp, runlen + 1)
                    stack.pop()
            a = ROTINV[e]
            for w in range(3, wmax + 1):
                if BASE + runs + 1 + xp + (w - 3) > TMAX:
                    break
                for b in DOORS[w][a]:
                    if not isentry[b]:
                        continue
                    c = CYCOF[b]
                    if used >> c & 1:
                        continue
                    stack.append((w, b))
                    rec(b, used | (1 << c), nused + 1, runs + 1,
                        xp + (w - 3), 1)
                    stack.pop()
        rec(start, 1 << CYCOF[start], 1, 1, 0, 1)
    dt = time.time() - t0
    print(f"nodes={nodes}  runtime={dt:.1f}s")
    if best:
        print("MIN LENGTH BY j in the perfect-ride family:")
        for j in sorted(best):
            print(f"   j={j}: {best[j]}")
        if verbose:
            for j in sorted(best):
                cov, st = wit[j]
                print(f"   witness j={j}: cover={cov}")
                print(f"     steps={st}")
    else:
        print(f"NO walk in the perfect-ride family with j>={jmin} "
              f"and length <= {TMAX}")
    return best, wit


def materialize(N, cov, steps):
    """Rebuild the walk string from a search witness (perfect-ride family)."""
    from itertools import permutations as _pm
    PERMS = list(_pm(range(1, N + 1)))
    entries = [tuple(range(1, N + 1))] + [PERMS[b] for (_, b) in steps]
    path = []
    for e in entries:
        p = e
        for _ in range(N):
            path.append(p)
            p = p[1:] + p[:1]
    s = "".join(str(c) for c in path[0])
    for a, b in zip(path, path[1:]):
        w = weight(a, b, N)
        s += "".join(str(c) for c in b[N - w:])
    return s, path


if __name__ == "__main__":
    n = int(sys.argv[1])
    tmax = int(sys.argv[2])
    jm = int(sys.argv[sys.argv.index("--jmin") + 1]) if "--jmin" in sys.argv else 1
    wm = int(sys.argv[sys.argv.index("--wmax") + 1]) if "--wmax" in sys.argv else None
    best, wit = run(n, tmax, jm, wm, "--verbose" in sys.argv)
    if "--emit" in sys.argv:
        import os as _os
        d = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                          "witness")
        _os.makedirs(d, exist_ok=True)
        for j in sorted(wit):
            cov, st = wit[j]
            s2, _ = materialize(n, cov, st)
            f = _os.path.join(d, f"n{n}_j{j}_{best[j]}.txt")
            open(f, "w").write(s2 + "\n")
            print(f"  wrote {f}  (len {len(s2)})")


