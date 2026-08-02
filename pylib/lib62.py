# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s62/jtax/lib62.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s62 j-tax library: self-contained ledger coordinates for pure complete
first-visit walks.  Deliberately independent of loop_ledger_probe.py so the
s56 numbers get an independent re-derivation (cross-checked in check_lib.py).

Coordinates (n generic):
  S       sojourns  = number of maximal same-1-cycle runs of the walk ("arcs")
  splits  = S - (n-1)!
  D       doors     = inter-cycle edges of weight >= 3
  W       = S - 1 - D  inter-cycle weight-2 edges
  xp      = sum over doors of (w-3)                 [THEORY's  x = sum_{w>=4}(w-3)]
  v       = # distinct 2-loops containing an arc-START perm
  j       = splits + D + 1 - v
  L       = # distinct 2-loops carrying >= 1 used loop-edge

Identities/inequalities re-derived in LOG.md:
  length  = n! + (n-1)! + (n-3) + v + j + xp          (exact, every pure walk)
  S       <= (n-1) * v                                 (loop supply)
  =>  length >= n! + (n-1)! + (n-3) + ceil(S/(n-1)) + j + xp      [MASTER]
"""
from math import factorial


def rot(p):
    return p[1:] + p[:1]


def rotc(p):
    return min(p[i:] + p[:i] for i in range(len(p)))


def g(q):
    n = len(q)
    return q[1:n - 1] + (q[0], q[n - 1])


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


def weight(a, b, n):
    for k in range(n - 1, 0, -1):
        if a[n - k:] == b[:k]:
            return n - k
    return n


def first_visit_path(s, n):
    want = set(range(1, n + 1))
    seen, path = set(), []
    vals = [int(c) for c in s]
    for i in range(len(vals) - n + 1):
        win = tuple(vals[i:i + n])
        if set(win) == want and win not in seen:
            seen.add(win)
            path.append(win)
    return path


def analyze_path(path, n):
    """Ledger coordinates of a complete pure first-visit walk (list of perms).
    Returns None if the walk is impure (an intra-cycle edge of weight >= 2)."""
    fact1 = factorial(n - 1)
    # arcs
    arcs = []          # (cycle, entry, exit)
    start = 0
    for i in range(len(path)):
        if i + 1 == len(path) or rotc(path[i + 1]) != rotc(path[i]):
            arcs.append((rotc(path[start]), path[start], path[i]))
            start = i + 1
    # purity: inside an arc every step must be weight 1
    for a, b in zip(path, path[1:]):
        if rotc(a) == rotc(b) and weight(a, b, n) >= 2:
            return None
    S = len(arcs)
    splits = S - fact1
    D = 0
    xp = 0
    W = 0
    used_loop_edges = {}
    for i in range(S - 1):
        a, b = arcs[i][2], arcs[i + 1][1]
        w = weight(a, b, n)
        if w == 2:
            W += 1
            q = rot(a)
            used_loop_edges.setdefault(lam(q), set()).add(q)
        else:
            D += 1
            xp += w - 3
    v = len({lam(a[1]) for a in arcs})
    L = len(used_loop_edges)
    j = splits + D + 1 - v
    length = n + sum(weight(a, b, n) for a, b in zip(path, path[1:]))
    return {"n": n, "S": S, "splits": splits, "D": D, "W": W, "xp": xp,
            "v": v, "j": j, "L": L, "length": length,
            "deficit": splits + D + 1 - L,
            "used_loop_edges": used_loop_edges, "arcs": arcs}


def master_terms(r):
    """(identity_lhs, identity_rhs, master_rhs) for a result dict."""
    n = r["n"]
    base = factorial(n) + factorial(n - 1) + (n - 3)
    ident = base + r["v"] + r["j"] + r["xp"]
    sup = -(-r["S"] // (n - 1))          # ceil(S/(n-1))
    master = base + sup + r["j"] + r["xp"]
    return ident, master, sup
