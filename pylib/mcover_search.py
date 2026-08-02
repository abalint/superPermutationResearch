#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s62/jtax/mcover_search.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s63: EXHAUSTIVE decision of the SUPPLY-TIGHT MULTI-COVER families at any n.

Generalizes `cover_search.py` (s62) from EXACT covers (splits = 0, v = (n-2)!)
to k-loop MULTI-covers with prescribed cycle multiplicities.

FRAME (all statements for pure complete first-visit walks)
---------------------------------------------------------
Fix v (# distinct 2-loops containing an arc-START) and splits (= S - (n-1)!).
The family M(n, v, splits) is the set of walks that are SUPPLY-TIGHT:

        S = (n-1)! + splits = (n-1) * v .

Supply-tightness forces (this is the multi-cover generalization of the s62
"perfect-ride rigidity", and it does NOT evaporate with excess incidences):

  * a 2-loop has n-1 perms lying in n-1 DISTINCT 1-cycles, and each perm can
    start at most one arc, so a loop supplies <= n-1 arc-starts; S = (n-1)v
    means EVERY perm of EVERY entered loop is an arc-start.  Hence the
    arc-start set is exactly  E = union of the v loops  (|E| = (n-1)v = S),
    DETERMINED by the loop set.  (What the s62 report calls "the cover no
    longer determines the arc-starts" is the SUPPLY-SLACK case S < (n-1)v,
    which this engine does not handle -- see --v/--splits check below.)
  * the v loops therefore MULTI-COVER the (n-1)! one-cycles: cycle c carries
    mult(c) = |E cap c| >= 1 arcs, sum mult = (n-1)v, excess = splits.
  * by L1 the arcs of a cycle are the contiguous cyclic intervals between
    consecutive entries, so all arcs are determined by E:
        exit(e) = rot^-1(sigma(e)),  sigma(e) = next entry after e in rot order.
  * by L2 the unique inter-cycle w2 edge out of a lands on g(rot(a)), so the
    w2 successor of the arc starting at e is
        phi(e) = g(sigma(e)),
    and phi is a PERMUTATION of E (g preserves loops, sigma preserves E).
    A maximal w2-run is therefore a contiguous segment of a phi-CYCLE, so
        R (= #runs = D+1)  >=  #phi-cycles  =:  K,
    which is a strong per-multi-cover prune (and reproduces the s62
    perfect-ride count: splits=0 => phi = g => K = v = 24 <= R = 25).
  * length = n! + (n-1)! + (n-3) + splits + R + xp,   j = splits + R - v,
    xp = sum_doors (w-3).   (splits=0 reduces to cover_search's formula.)

Search: for every multi-cover containing lam(identity) -- the walk's first
perm may be taken = identity by relabeling -- DFS over the arcs; the only
moves are the forced w2 step e -> phi(e) or a door of weight w>=3 out of
exit(e) onto an unused arc-start in another 1-cycle.

Difference from cover_search.py beyond the multi-cover: door edges of weight
w >= 3 can SPELL intermediate permutations ("mids").  In the perfect-ride
family every such mid is the entry of the departing cycle's own arc and is
already visited; with split cycles it can be an unvisited perm of a LATER arc,
which would break the first-visit reading (the s34 trap).  `--mids` (default)
requires every mid to lie in an already-used arc; `--no-mids` drops the test
(a strict SUPERSET search -- which is what cover_search.py does, so its
NEGATIVE results stay sound; use --no-mids for node-for-node comparison).

Usage:
  mcover_search.py <n> <TMAX> --v V --splits S [--jmin J] [--wmax W]
                   [--prune legacy|cyc] [--mids|--no-mids] [--count-only]
                   [--kstats] [--stride K] [--offset O] [--max-nodes N]
                   [--max-covers M] [--max-secs T] [--verbose] [--emit]
                   [--forest] [--emit-covers FILE] [--covers-file FILE]

  --emit-covers FILE   enumerate once and WRITE the admissible multi-cover
                stream, one cover per line (loop ids, ints, in enumeration
                order), with a trailing `# total N` and `# sha256 <body>`.
                Requires --stride 1: the file IS the whole stream.
  --covers-file FILE   skip enumeration entirely; verify the file's body
                sha256 and declared total, then process the lines with
                idx % stride == offset through the IDENTICAL prepare/DFS
                path.  Line index == the enumeration index a --stride run
                would have selected, so the two modes agree cover-for-cover.
                Exits 4 if the file fails verification.
                WHY: stride-sharding the ENUMERATION makes every shard
                re-walk the whole tree -- N shards do N x the enumeration
                for 1 x the search.  Emitting once removes that and makes
                the shards exactly balanced instead of balanced-in-mean.

  --count-only  enumerate the multi-covers only (sizing; no walk DFS)
  --kstats      with --count-only, also report the phi-cycle-count histogram
                and how many multi-covers survive the K <= Rmax prune
  --stride K --offset O   process only multi-covers with index % K == O
                (deterministic ROUND-ROBIN stratification for sizing: the
                multi-covers are independent subtrees, so an every-K-th
                sample is unbiased by construction -- never a first-K sample)
  --max-nodes / --max-covers / --max-secs   caps; the run then reports
                PARTIAL and exits 3 (never claim a negative from a capped run)
"""
import sys
import os
import time
from itertools import permutations
from math import factorial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib62 import weight                      # noqa: E402
from cover_search import build                # noqa: E402  (same tables)


# ---------------------------------------------------------------- structure

def add_rot(B):
    """cover_search.build gives ROTINV; add the forward rotation."""
    PERMS, PIDX = B["PERMS"], B["PIDX"]
    B["ROT"] = [PIDX[p[1:] + p[:1]] for p in PERMS]
    return B


def build_mids(B, wmax):
    """MIDS[w][a] parallel to B['DOORS'][w][a]: the intermediate permutation
    indices spelled by the edge a -> b (excluding a and b)."""
    N, PERMS, PIDX = B["N"], B["PERMS"], B["PIDX"]
    out = {}
    for w in range(3, wmax + 1):
        tbl = []
        for i, a in enumerate(PERMS):
            row = []
            for jb in B["DOORS"][w][i]:
                b = PERMS[jb]
                block = a + b[N - w:]
                mids = []
                for k in range(1, w):
                    win = block[k:k + N]
                    if len(win) == N and len(set(win)) == N:
                        mids.append(PIDX[win])
                row.append(tuple(mids))
            tbl.append(row)
        out[w] = tbl
    return out


def loop_frame(B):
    """Per-loop cycle sets and the 'decide each loop at its lowest cycle'
    scaffolding used by the multi-cover enumerator."""
    NCYC, NLOOP, CYCOF = B["NCYC"], B["NLOOP"], B["CYCOF"]
    lcyc = [sorted({CYCOF[i] for i in B["LOOPCELLS"][l]}) for l in range(NLOOP)]
    at = [[] for _ in range(NCYC)]
    for l in range(NLOOP):
        for c in lcyc[l]:
            at[c].append(l)
    new = [[] for _ in range(NCYC)]
    for l in range(NLOOP):
        new[lcyc[l][0]].append(l)
    # last cycle at which an uncovered cycle can still be covered
    deadline = [[] for _ in range(NCYC)]
    for c in range(NCYC):
        deadline[max(lcyc[l][0] for l in at[c])].append(c)
    return lcyc, at, new, deadline


class DSU:
    """Union-find with undo (for the --forest constraint)."""

    def __init__(self, n):
        self.p = list(range(n))
        self.r = [0] * n
        self.log = []

    def find(self, x):
        while self.p[x] != x:
            x = self.p[x]
        return x

    def union(self, a, b):
        """False (and no change) if a,b are already joined -- i.e. the edge
        would close a cycle."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        bump = self.r[ra] == self.r[rb]
        if bump:
            self.r[ra] += 1
        self.log.append((rb, ra, bump))
        return True

    def mark(self):
        return len(self.log)

    def rollback(self, m):
        while len(self.log) > m:
            rb, ra, bump = self.log.pop()
            self.p[rb] = rb
            if bump:
                self.r[ra] -= 1


def enum_multicovers(B, v, excess, must, cb, max_covers=None, max_secs=None,
                     t0=None, count_only=False, forest=False):
    """Every set of v loops covering all (n-1)! one-cycles (excess incidences
    = `excess`) and containing loop `must`, each EXACTLY ONCE.

    CANONICAL DECOMPOSITION (this is what fixes the nearcovers.py bug and
    makes counting cheap).  Given V, run the deterministic process: walk the
    cycles in index order; whenever cycle c is UNCOVERED, it is a TRIGGER and
    we harvest T_c = V ∩ {loops containing c} (nonempty; every loop of V has
    exactly ONE trigger, since a second trigger of the same loop would already
    be covered).  Write P = ∪ T_c and Z = V \\ P.  Then Z is exactly a subset
    of Zcand(P) = {loops whose cycles avoid every trigger} -- the loops the
    process can never see -- and conversely P ∪ Z is a multi-cover for ANY
    Z ⊆ Zcand(P) of the right size.  So

        #multi-covers of size v  =  sum over P of  C(|Zcand(P)|, v - |P|)

    with the `must` correction, i.e. the redundant loops are counted in closed
    form instead of enumerated.  The P-DFS branches on nonempty subsets of the
    (n) loops through the lowest uncovered cycle, so it is as tight as the
    exact-cover DFS in covers.py.

    Returns (count, nodes, stopped)."""
    from math import comb
    from itertools import combinations
    NCYC, NLOOP, LM = B["NCYC"], B["NLOOP"], B["LOOPMASK"]
    lcyc, at, _, _ = loop_frame(B)
    full = (1 << NCYC) - 1
    P = []
    excl = bytearray(NLOOP)
    # --forest: G* = bipartite (loops of V) x (one-cycles) incidence graph must
    # be ACYCLIC.  Measured law (out/s63/mcover/kstruct.py): K = #phi-cycles
    # attains its minimum v-splits exactly when G* is a forest, so any branch
    # whose R budget forces K = v-splits can be restricted to forests.
    dsu = DSU(NLOOP + NCYC) if forest else None

    def add_loop(l):
        for c in lcyc[l]:
            if not dsu.union(l, NLOOP + c):
                return False
        return True
    cnt = 0
    nodes = 0
    stopped = [False]
    if t0 is None:
        t0 = time.time()

    def leaf(trigmask):
        nonlocal cnt
        p = len(P)
        zc = [l for l in range(NLOOP) if not (LM[l] & trigmask)]
        need = v - p
        if need < 0:
            return
        inP = must in P
        if not inP and must not in zc:
            return
        if count_only and not forest:
            if inP:
                cnt += comb(len(zc), need)
            else:
                zc2 = [l for l in zc if l != must]
                cnt += comb(len(zc2), need - 1) if need >= 1 else 0
            return
        if inP:
            pool, forced = zc, ()
        else:
            pool, forced = [l for l in zc if l != must], (must,)
            need -= 1
            if need < 0:
                return
        for extra in combinations(pool, need):
            if forest:
                mk = dsu.mark()
                ok = True
                for l in forced + extra:
                    if not add_loop(l):
                        ok = False
                        break
                dsu.rollback(mk)
                if not ok:
                    continue
            cnt += 1
            if not count_only:
                cb(tuple(P) + forced + extra)
            if max_covers is not None and cnt >= max_covers:
                stopped[0] = True
                return

    def rec(cov, ncov, trigmask):
        nonlocal nodes
        if stopped[0]:
            return
        nodes += 1
        # excess is monotone: each loop adds n-1 incidences and <= n-1 new
        # cycles, and the Z loops add exactly n-1 excess each, so the running
        # P-excess can never exceed the family's total.
        if (B["N"] - 1) * len(P) - ncov > excess:
            return
        if cov == full:
            leaf(trigmask)
            if max_secs is not None and time.time() - t0 > max_secs:
                stopped[0] = True
            return
        if len(P) >= v:
            return
        c = 0
        while cov >> c & 1:
            c += 1
        cand = [l for l in at[c] if not excl[l]]
        room = v - len(P)
        tm = trigmask | (1 << c)
        # T_c = V ∩ (loops through c) is nonempty; every loop through c NOT in
        # T_c is permanently excluded from V (c is a trigger, so such a loop
        # would have to be harvested here) -- without this the same V is
        # generated many times over.
        # all loops of T contain c, so |T| = t costs at least t-1 excess
        cur = (B["N"] - 1) * len(P) - ncov
        maxt = min(room, len(cand), excess - cur + 1)
        for t in range(1, maxt + 1):
          for T in combinations(cand, t):
            m = cov
            for l in T:
                m |= LM[l]
            add = bin(m & ~cov).count("1")
            if (B["N"] - 1) * (len(P) + t) - (ncov + add) > excess:
                continue
            drop = [l for l in cand if l not in T]
            mk = None
            if forest:
                mk = dsu.mark()
                ok = True
                for l in T:
                    if not add_loop(l):
                        ok = False
                        break
                if not ok:
                    dsu.rollback(mk)
                    continue
            for l in drop:
                excl[l] = 1
            P.extend(T)
            rec(m, ncov + add, tm)
            del P[len(P) - t:]
            for l in drop:
                excl[l] = 0
            if forest:
                dsu.rollback(mk)
            if stopped[0]:
                return

    rec(0, 0, 0)
    return cnt, nodes, stopped[0]


def prepare(B, cov):
    """Arc frame of one supply-tight multi-cover.
    Returns dict with arcs (entry perm idx), arcof (perm -> arc id), exitp,
    phi (arc -> arc), pcyc (arc -> phi-cycle id), K, isentry, arcid."""
    NPERM = len(B["PERMS"])
    NCYC, CYCOF, ROT, G = B["NCYC"], B["CYCOF"], B["ROT"], B["G"]
    ent = [[] for _ in range(NCYC)]
    isentry = bytearray(NPERM)
    for l in cov:
        for i in B["LOOPCELLS"][l]:
            ent[CYCOF[i]].append(i)
            isentry[i] = 1
    arcs, arcid = [], [-1] * NPERM
    for c in range(NCYC):
        for e in ent[c]:
            arcid[e] = len(arcs)
            arcs.append(e)
    S = len(arcs)
    arcof = [-1] * NPERM
    exitp = [-1] * NPERM
    sigma = [-1] * NPERM
    for c in range(NCYC):
        for e in ent[c]:
            a = arcid[e]
            p, prev = ROT[e], e
            arcof[e] = a
            while not isentry[p]:
                arcof[p] = a
                prev = p
                p = ROT[p]
            sigma[e] = p
            exitp[e] = prev
    phi = [arcid[G[sigma[e]]] for e in arcs]
    pcyc = [-1] * S
    K = 0
    for a in range(S):
        if pcyc[a] < 0:
            x = a
            while pcyc[x] < 0:
                pcyc[x] = K
                x = phi[x]
            K += 1
    csize = [0] * K
    for a in range(S):
        csize[pcyc[a]] += 1
    return dict(arcs=arcs, arcid=arcid, arcof=arcof, exitp=exitp, sigma=sigma,
                phi=phi, pcyc=pcyc, K=K, csize=csize, isentry=isentry, S=S)


def materialize(B, F, steps, start):
    """Rebuild the walk string from a witness: steps = [(w, entry_perm_idx)]."""
    N, PERMS, ROT = B["N"], B["PERMS"], B["ROT"]
    entries = [start] + [b for (_, b) in steps]
    path = []
    for e in entries:
        p = e
        while True:
            path.append(PERMS[p])
            if p == F["exitp"][e]:
                break
            p = ROT[p]
    s = "".join(str(c) for c in path[0])
    for a, b in zip(path, path[1:]):
        w = weight(a, b, N)
        s += "".join(str(c) for c in b[N - w:])
    return s, path


# ---------------------------------------------------------------- the search

def read_covers(path, expect=None):
    """Stream a --emit-covers file.  Returns (header dict, total, sha_ok).
    The sha256 is over the BODY BYTES ONLY (the cover lines), so a shard can
    prove it holds the same cover stream the emitter produced before it
    processes a single line."""
    import hashlib
    hdr, total, sha_want, nlines = {}, None, None, 0
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for raw in fh:
            if raw.startswith(b"#"):
                t = raw.decode().strip("# \n").split()
                if t and t[0] == "mcover-covers":
                    for kv in t[2:]:
                        if "=" in kv:
                            k, val = kv.split("=", 1)
                            hdr[k] = val
                elif t and t[0] == "total":
                    total = int(t[1])
                elif t and t[0] == "sha256":
                    sha_want = t[1]
                continue
            h.update(raw)
            nlines += 1
    sha_got = h.hexdigest()
    ok = (sha_want == sha_got) and (total == nlines)
    if expect:
        for k, val in expect.items():
            if hdr.get(k) != str(val):
                print(f"*** COVERS FILE MISMATCH: header {k}={hdr.get(k)} "
                      f"but this run wants {val} ***")
                ok = False
    return hdr, nlines, ok, sha_got, sha_want, total


def iter_covers(path):
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            yield tuple(int(x) for x in line.split())


def run(N, TMAX, v, splits, jmin=1, wmax=None, prune="cyc", mids=True,
        count_only=False, kstats=False, stride=1, offset=0, max_nodes=None,
        max_covers=None, max_secs=None, verbose=False, forest=False,
        emit_covers=None, covers_file=None):
    t0 = time.time()
    B = add_rot(build(N))
    NCYC = B["NCYC"]
    S = NCYC + splits
    if S != (N - 1) * v:
        print(f"*** NOT SUPPLY-TIGHT: S = {NCYC}+{splits} = {S} != "
              f"{(N-1)*v} = (n-1)v.  This engine handles the supply-TIGHT "
              f"corner only (S = (n-1)v); with slack the arc-start set is no "
              f"longer determined by the loop set and needs a separate "
              f"assignment enumeration.  Refusing to run.")
        return None
    excess = S - NCYC
    if wmax is None:
        wmax = N
    BASE = factorial(N) + factorial(N - 1) + (N - 3)
    LBASE = BASE + splits                      # length = LBASE + R + xp
    RMIN = v - splits + jmin                   # j = splits + R - v >= jmin
    RMAX = TMAX - LBASE                        # xp >= 0
    print(f"n={N}: {NCYC} cycles, {B['NLOOP']} loops; multi-cover v={v} "
          f"splits={splits} S={S} excess={excess} (supply-tight)")
    print(f"length = {LBASE} + R + xp,  j = R - {v - splits};  "
          f"TMAX={TMAX} jmin={jmin} wmax={wmax} prune={prune} mids={mids}")
    print(f"admissible runs R in [{RMIN}, {RMAX}]")
    if RMAX < RMIN:
        print("EMPTY BY ARITHMETIC: no admissible R.  NO walk.")
        return {}, {}
    MIDS = build_mids(B, wmax) if mids else None
    start_perm = B["PIDX"][tuple(range(1, N + 1))]
    lam0 = B["LOOPOF"][start_perm]

    G, CYCOF, DOORS = B["G"], B["CYCOF"], B["DOORS"]
    best, wit, census = {}, {}, {}
    stats = dict(covers=0, seen=0, kept=0, nodes=0, khist={}, capped=False)

    def process(cov):
        stats["covers"] += 1
        if count_only and not kstats:
            return
        F = prepare(B, cov)
        K = F["K"]
        stats["khist"][K] = stats["khist"].get(K, 0) + 1
        if K > RMAX:
            return
        stats["kept"] += 1
        if count_only:
            return
        arcs, arcid, arcof = F["arcs"], F["arcid"], F["arcof"]
        exitp, phi, pcyc = F["exitp"], F["phi"], F["pcyc"]
        isentry = F["isentry"]
        RUNMAX = max(F["csize"])
        used = bytearray(F["S"])
        left = list(F["csize"])
        stack = []
        usecyc = (prune == "cyc")

        def rec(e, ai, nused, runs, xp, runlen, nopen):
            stats["nodes"] += 1
            if max_nodes is not None and stats["nodes"] > max_nodes:
                stats["capped"] = True
                raise StopIteration
            if nused == F["S"]:
                ln = LBASE + runs + xp
                j = runs - (v - splits)
                if j >= jmin and ln <= TMAX:
                    census[(j, ln)] = census.get((j, ln), 0) + 1
                    if j not in best or ln < best[j]:
                        best[j] = ln
                        wit[j] = (cov, list(stack))
                return
            rem = F["S"] - nused
            extra = rem - (RUNMAX - runlen)
            addruns = 0 if extra <= 0 else -(-extra // RUNMAX)
            if usecyc:
                cx = pcyc[ai]
                need = nopen - (1 if left[cx] else 0)
                if need > addruns:
                    addruns = need
            if LBASE + runs + addruns + xp > TMAX:
                return
            # (a) forced w2 continuation
            if runlen < RUNMAX:
                t = phi[ai]
                if not used[t]:
                    nb = arcs[t]
                    used[t] = 1
                    cy = pcyc[t]
                    left[cy] -= 1
                    stack.append((2, nb))
                    rec(nb, t, nused + 1, runs, xp, runlen + 1,
                        nopen - (1 if left[cy] == 0 else 0))
                    stack.pop()
                    left[cy] += 1
                    used[t] = 0
            # (b) doors
            a = exitp[e]
            for w in range(3, wmax + 1):
                if LBASE + runs + 1 + xp + (w - 3) > TMAX:
                    break
                row = DOORS[w][a]
                mrow = MIDS[w][a] if mids else None
                for k in range(len(row)):
                    b = row[k]
                    if not isentry[b]:
                        continue
                    t = arcid[b]
                    if used[t]:
                        continue
                    if mids:
                        ok = True
                        for m in mrow[k]:
                            if not used[arcof[m]]:
                                ok = False
                                break
                        if not ok:
                            continue
                    used[t] = 1
                    cy = pcyc[t]
                    left[cy] -= 1
                    stack.append((w, b))
                    rec(b, t, nused + 1, runs + 1, xp + (w - 3), 1,
                        nopen - (1 if left[cy] == 0 else 0))
                    stack.pop()
                    left[cy] += 1
                    used[t] = 0

        a0 = arcid[start_perm]
        used[a0] = 1
        left[pcyc[a0]] -= 1
        rec(start_perm, a0, 1, 1, 0, 1,
            K - (1 if left[pcyc[a0]] == 0 else 0))

    # ---- the three drive modes ------------------------------------------
    # (1) enumerate + search   (2) enumerate + EMIT the cover stream
    # (3) read the cover stream from FILE + search a stride slice of it
    # (2) and (3) exist because stride-sharding mode (1) makes EVERY shard
    # re-walk the WHOLE enumeration: N shards do N x the enumeration work for
    # 1x the search.  Emitting once and consuming the file removes that
    # entirely and makes the shards balanced (equal line counts) instead of
    # merely equal-in-expectation.
    import hashlib
    emit_fh = emit_h = None
    if emit_covers:
        if stride != 1:
            print("*** --emit-covers requires --stride 1 (the file IS the "
                  "whole stream; shard when CONSUMING it) ***")
            return None
        # newline="" -> NO platform newline translation.  Without it Windows
        # writes CRLF while the sha256 is taken over the LF bytes, so the
        # file's own hash never verifies (caught by the PC-side shim
        # self-test).  POSIX output is byte-identical either way, so this does
        # not change any Mac-emitted file.
        emit_fh = open(emit_covers, "w", newline="")
        emit_h = hashlib.sha256()
        emit_fh.write(f"# mcover-covers v1 n={N} v={v} splits={splits} "
                      f"forest={int(forest)}\n")

    def handle(cov):
        stats["seen"] += 1
        idx = stats["seen"] - 1
        if emit_fh is not None:
            line = " ".join(str(x) for x in cov) + "\n"
            emit_h.update(line.encode())
            emit_fh.write(line)
            return
        if stride > 1 and idx % stride != offset:
            return
        process(cov)

    if covers_file:
        hdr, nlines, ok, sha_got, sha_want, decl = read_covers(
            covers_file, expect={"n": N, "v": v, "splits": splits,
                                 "forest": int(forest)})
        print(f"covers file: {covers_file}")
        print(f"  header {hdr}  lines={nlines} declared_total={decl}")
        print(f"  sha256 body={sha_got}  expected={sha_want}  "
              f"VERIFIED={ok}")
        if not ok:
            print("*** COVERS FILE FAILED VERIFICATION -- refusing to run ***")
            sys.exit(4)
        ncov, enodes, estop = nlines, 0, False
        try:
            for cov in iter_covers(covers_file):
                stats["seen"] += 1
                if stride > 1 and (stats["seen"] - 1) % stride != offset:
                    continue
                process(cov)
        except StopIteration:
            stats["capped"] = True
            estop = True
    else:
      try:
        ncov, enodes, estop = enum_multicovers(
            B, v, excess, lam0, handle, max_covers=max_covers,
            max_secs=max_secs, t0=t0,
            count_only=((count_only and not kstats)
                        and emit_fh is None),
            forest=forest)
      except StopIteration:
        ncov, enodes, estop = stats["seen"], -1, True
        stats["capped"] = True
      if emit_fh is not None:
        ncov = stats["seen"]
        emit_fh.write(f"# total {ncov}\n")
        emit_fh.write(f"# sha256 {emit_h.hexdigest()}\n")
        emit_fh.close()
        print(f"EMITTED {ncov} covers -> {emit_covers}")
        print(f"  body sha256 {emit_h.hexdigest()}")
    dt = time.time() - t0
    print(f"multi-covers containing lam(id): total={ncov} "
          f"seen={stats['seen']} processed={stats['covers']}"
          + (f" (stride {stride} offset {offset})" if stride > 1 else "")
          + f"  enum_nodes={enodes}")
    if kstats or not count_only:
        print(f"phi-cycle-count histogram K: "
              f"{dict(sorted(stats['khist'].items()))}")
        print(f"survived K<=RMAX({RMAX}): {stats['kept']}")
    print(f"walk nodes={stats['nodes']}  runtime={dt:.1f}s")
    if stats["capped"] or estop:
        print("*** PARTIAL (cap hit) -- NOT a negative result ***")
    if count_only:
        return None
    if census:
        print(f"census (j,length)->#walks: {dict(sorted(census.items()))}")
    if best:
        print("MIN LENGTH BY j in this multi-cover family:")
        for j in sorted(best):
            print(f"   j={j}: {best[j]}")
        if verbose:
            for j in sorted(best):
                print(f"   witness j={j}: cover={wit[j][0]}")
                print(f"     steps={wit[j][1]}")
    else:
        print(f"NO walk in the supply-tight multi-cover family (v={v}, "
              f"splits={splits}) with j>={jmin} and length <= {TMAX}")
    if stats["capped"] or estop:
        sys.exit(3)
    return best, wit


def _argi(flag, default=None, cast=int):
    if flag in sys.argv:
        return cast(sys.argv[sys.argv.index(flag) + 1])
    return default


if __name__ == "__main__":
    n = int(sys.argv[1])
    tmax = int(sys.argv[2])
    vv = _argi("--v")
    sp = _argi("--splits")
    if vv is None or sp is None:
        print("need --v V and --splits S")
        sys.exit(2)
    res = run(n, tmax, vv, sp,
              jmin=_argi("--jmin", 1),
              wmax=_argi("--wmax", None),
              prune=_argi("--prune", "cyc", str),
              mids=("--no-mids" not in sys.argv),
              count_only=("--count-only" in sys.argv),
              kstats=("--kstats" in sys.argv),
              stride=_argi("--stride", 1),
              offset=_argi("--offset", 0),
              max_nodes=_argi("--max-nodes", None),
              max_covers=_argi("--max-covers", None),
              max_secs=_argi("--max-secs", None, float),
              verbose=("--verbose" in sys.argv),
              forest=("--forest" in sys.argv),
              emit_covers=_argi("--emit-covers", None, str),
              covers_file=_argi("--covers-file", None, str))
    if res and "--emit" in sys.argv:
        best, wit = res
        B = add_rot(build(n))
        st = B["PIDX"][tuple(range(1, n + 1))]
        d = _argi("--emit-dir",
                  os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "witness"), str)
        os.makedirs(d, exist_ok=True)
        for j in sorted(wit):
            cov, steps = wit[j]
            F = prepare(B, cov)
            s2, _ = materialize(B, F, steps, st)
            f = os.path.join(d, f"mc_n{n}_v{vv}_s{sp}_j{j}_{best[j]}.txt")
            open(f, "w").write(s2 + "\n")
            print(f"  wrote {f}  (len {len(s2)})")
