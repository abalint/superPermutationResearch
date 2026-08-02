#!/usr/bin/env python3
"""s51 menu item 3: the w4 DEMOTION TRADE  (S+1, d3+1, d4-1),  dlen = 0.

LENGTH ALGEBRA (T0 / THEORY s7).  For a pure tight walk with S sojourns,
doors of weights w_j and 720-S (resp 5040-S) intra w1 steps,

    len = (n! + n - 2) + S - 2D + sum_j w_j
        = (n! + n - 2) + S + sum_j (w_j - 2)
        = (n! + n - 2) + S + d3 + 2*d4 + 3*d5 + ...

so  dlen = dS + sum_w (w-2)*d(count_w).  The unit family

    DEMOTION(w):  delete one w-door, add one entry, add one (w-1)-door
                  dS=+1, d(count_w)=-1, d(count_{w-1})=+1
                  dlen = +1 + (w-3) - (w-2) = 0                (any w>=3)

is length-conserving for EVERY w.  At w=3 the "(w-1)-door" is a plain w2
inter-sojourn step, i.e. no door at all, and DEMOTION(3) IS the R-BND
FWD unit trade (S+1, D-1) of docs/RBND-RULE.md -- which this instrument
reproduces exactly in `--w-from 3` mode (the machinery control).  At
w=4 it is the (S+1, d3+1, d4-1) demotion trade: the only length-
conserving w4 move (s49 killed the door-for-boundary shape at w>=4,
dlen = 3-w; this is a DIFFERENT, 3-object shape (0,1,1,1) that no rule
in any of the five tables has).

The inverse move is PROMOTION(w): delete one entry, delete one
(w-1)-door, add one w-door -- also dlen = 0.  Both directions are
implemented; demotion o promotion is checked as an involution.

MECHANICS (derived in out/s51/demotion/DESIGN.md; complete, not
heuristic).  A tight walk replays deterministically from
(E = per-cycle entry sets, D = doors, start).  Arc exits are
exits = rot^-1(entries).  Define the CLAIM map: exit p claims D[p] if
p is a door exit, else g(rot(p)) when that is an entry (otherwise p is
FREE).  A valid walk has exactly one orphan entry (= the start) and
either one free exit or one doubly-claimed entry (the walk end's
untraversed edge).  Deleting door (x->y) orphans y and reactivates x's
w2 edge; adding entry a splits an arc, creating the new exit
q = rot^-1(a) (claiming g(a)) and the new orphan a.  At most ONE entry
may end up unclaimed (it is the new start), so `a` is claimed either by
a w2 edge out of a FREE exit of the post-deletion structure (branch A --
x itself is normally the only such exit, giving the forced
a = g(rot(x))), or by the new door (branch B, v = a), or `a` IS the new
start (branch C).  In branches B and C one of {y, start} must then be
claimed by t_x = g(rot(x)) or by g(a), which forces
a in {g^-1(y), g^-1(start)} unless t_x in {y, start}.  Every surviving
(a, u, v) is replayed; replay is the decider; and the PRODUCT'S OWN
structure is re-derived, because a door added at the walk END is never
traversed and silently degenerates the trade into the dlen = -1 drop.

Usage (repo-root cwd; deterministic; TSV outputs):
  python3 analysis/counting/s51/demotion.py census 6 data/upstream872 \
      --files data/loopswap/n6_w4_classes.txt --out out/s51/demotion/census.tsv
  python3 analysis/counting/s51/demotion.py demote 6 data/upstream872 \
      --files data/loopswap/n6_w4_classes.txt --out out/s51/demotion/n6rec
  python3 analysis/counting/s51/demotion.py promote 6 data/upstream872 \
      --files <list> --out out/s51/demotion/n6prom
  python3 analysis/counting/s51/control.py brute 6 <dir> --limit K  # controls
  python3 analysis/counting/s51/demotion.py demote 7 data/upstream5906 --w-from 3 \
      --out out/s51/demotion/ctl_w3_n7   # machinery control: reproduces R-BND FWD
Options: --w-from W (default 4), --shard i/k, --index <extra canon index tsv>,
         --limit N, --quiet.
"""
import hashlib
import os
import sys
from collections import Counter
from itertools import permutations

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "..", ".."))
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting")
from loop_ledger_probe import first_visit_path, g, rot, rotc, weight  # noqa: E402
from i4a_apply import replay, structure  # noqa: E402
from m3_check import SUPPLEMENTARY, canon, load_index  # noqa: E402

HERE = os.path.join(R, 'analysis', 'counting')
GINV, ROTINV = {}, {}
NPERM = {}


def build_inv(n):
    GINV.clear()
    ROTINV.clear()
    for p in permutations(range(1, n + 1)):
        GINV[g(p)] = p
        ROTINV[rot(p)] = p


def sp(p):
    return "".join(map(str, p))


# ---------------------------------------------------------------- structure

def exits_of(E):
    """arc exits = rot^-1(entry) for every entry (arcs <-> entries)."""
    out = set()
    for ents in E.values():
        for e in ents:
            out.add(ROTINV[e])
    return out


def flat_of(E):
    f = set()
    for v in E.values():
        f |= v
    return f


def claim_report(E, D, n):
    """(claim: entry -> [claimers], orphans, conflicts, free_exits) or None
    if a door points at a non-entry or sits on a non-exit (dead)."""
    flat = flat_of(E)
    ex = exits_of(E)
    if any(p not in ex for p in D):
        return None
    claim, free = {}, []
    for p in ex:
        if p in D:
            t = D[p]
            if t not in flat:
                return None
        else:
            t = g(rot(p))
            if t not in flat:
                free.append(p)
                continue
        claim.setdefault(t, []).append(p)
    orphans = [e for e in flat if e not in claim]
    conflicts = [e for e, v in claim.items() if len(v) > 1]
    return claim, orphans, conflicts, free


def legal_profile(rep):
    """Necessary degree profile of a replayable structure: exactly one
    orphan (the start) and exactly one of {free exit, doubly-claimed
    entry} (the walk end's untraversed edge)."""
    if rep is None:
        return None
    claim, orph, conf, free = rep
    if len(orph) != 1 or len(free) > 1 or len(conf) > 1:
        return None
    if len(free) + sum(len(claim[c]) - 1 for c in conf) != 1:
        return None
    return orph[0]


def alloc_of(E, D, n):
    S = sum(len(v) for v in E.values())
    wc = Counter(weight(x, y, n) for x, y in D.items())
    return S, tuple(sorted(wc.items()))


def predicted_len(E, D, n):
    fact = 720 if n == 6 else 5040
    S = sum(len(v) for v in E.values())
    return fact + n - 2 + S + sum(weight(x, y, n) - 2 for x, y in D.items())


def add_entry(E, a):
    E2 = {c: set(v) for c, v in E.items()}
    E2.setdefault(rotc(a), set()).add(a)
    return E2


def del_entry(E, a):
    E2 = {c: set(v) for c, v in E.items()}
    E2[rotc(a)].discard(a)
    return E2


# ---------------------------------------------------------------- the move

def targets_at(u, w, n):
    """all v with u[w:] == v[:n-w] (weight <= w; caller checks == w).
    NB the overlap is n-w symbols, not w -- the two coincide only at
    n = 2w, which is why an n=6/w=3 test cannot catch an error here."""
    head = u[w:]
    rest = [s for s in range(1, n + 1) if s not in head]
    return [head + t for t in permutations(rest)]


def sources_at(v, w, n):
    """all u with u[n-w:] == v[:n-w]."""
    tail = v[:n - w]
    rest = [s for s in range(1, n + 1) if s not in tail]
    return [p + tail for p in permutations(rest)]


def demotion_moves(E, D, st, n, w_from=4):
    """Every admissible DEMOTION(w_from) edit of a structure.

    Yields (label, E2, D2, start2, branch).  w_to = w_from - 1; when
    w_to == 2 no door is added (this is exactly R-BND FWD)."""
    w_to = w_from - 1
    flat = flat_of(E)
    ex = exits_of(E)
    out = []
    for x, y in sorted(D.items()):
        if weight(x, y, n) != w_from:
            continue
        D1 = dict(D)
        del D1[x]
        t_x = g(rot(x))
        # free exits of the post-deletion structure (x is normally the
        # only one: sources measure 0 free exits)
        free1 = [p for p in ex if p not in D1 and g(rot(p)) not in flat]
        # ---- candidate new entries -------------------------------------
        cands = []                      # (branch, a, feeder-exit or None)
        for p in free1:                 # branch A: a is w2-fed by p
            a = g(rot(p))
            if a not in flat:
                cands.append(('A', a, p))
        if w_to >= 3:                   # branch B/C: a fed by the new
            # door, or a IS the new start; both need y or start supplied
            # by t_x or g(a), which forces a (unless the t_x gate is open)
            bset = []
            if t_x in (y, st):
                bset = [q for q in GINV if q not in flat]      # a is free
            else:
                for cand in (GINV[y], GINV[st]):
                    if cand not in flat:
                        bset.append(cand)
            for a in bset:
                cands.append(('B', a, None))
        seen = set()
        for branch, a, feeder in cands:
            if (branch, a) in seen:
                continue
            seen.add((branch, a))
            E2 = add_entry(E, a)
            flat2 = flat | {a}
            q = ROTINV[a]
            ex2 = ex | {q}
            if w_to == 2:
                # R-BND FWD degenerate: no door added
                cand_doors = [None]
            else:
                cand_doors = []
                for u in sorted(ex2):
                    if u in D1:
                        continue
                    for v in targets_at(u, w_to, n):
                        if v in flat2 and weight(u, v, n) == w_to:
                            cand_doors.append((u, v))
            for cd in cand_doors:
                if cd is None:
                    D2, lab = D1, "nodoor"
                else:
                    u, v = cd
                    D2 = dict(D1)
                    D2[u] = v
                    lab = f"{sp(u)}>{sp(v)}"
                    # cheap necessary prefilter: at most one of
                    # {y, a, start} may end up unclaimed
                    # every entry a new claim can land on: the feeder
                    # that w2-supplies `a` (branch A), x's reactivated w2
                    # edge, the split arc's new exit, and the door itself
                    supplied = {v}
                    if feeder is not None and feeder != u:
                        supplied.add(a)
                    if u != x:
                        supplied.add(t_x)
                    if u != q:
                        supplied.add(g(a))
                    if len({y, a, st} & supplied) < 2:
                        continue
                st2 = legal_profile(claim_report(E2, D2, n))
                if st2 is None:
                    continue
                out.append((f"DEM{w_from}/{sp(x)}>{sp(y)}/+{sp(a)}/{lab}",
                            E2, D2, st2, branch))
    return out


def promotion_moves(E, D, st, n, w_to=4):
    """Every admissible PROMOTION(w_to) edit: delete one entry, delete one
    (w_to-1)-door, add one w_to-door.  Exact inverse shape of demotion.

    Prefilter: after the two deletions at most TWO entries may be
    orphaned and at most two exits free (one added door can serve one of
    each; the survivor is the new start / the new end)."""
    w_from = w_to - 1
    flat = flat_of(E)
    out = []
    doors_lo = [(u, v) for u, v in sorted(D.items())
                if weight(u, v, n) == w_from] if w_from >= 3 else [None]
    for a in sorted(flat):
        c = rotc(a)
        if len(E[c]) < 2:               # a cycle must keep an entry
            continue
        E2 = del_entry(E, a)
        flat2 = flat - {a}
        for dl in doors_lo:
            D1 = dict(D)
            if dl is not None:
                u, v = dl
                del D1[u]
            else:
                u = v = None
            # deleting entry a removes the exit rot^-1(a); a door sitting
            # there is only admissible if it is the door being deleted
            # (that IS the inverse of a demotion whose new door sat on
            # the split arc's new exit)
            if ROTINV[a] in D1:
                continue
            rep = claim_report(E2, D1, n)
            if rep is None:
                continue
            claim, orph, conf, free = rep
            # the added door supplies one claim and withdraws at most
            # one, so it can fix at most one orphan and one conflict
            if len(orph) > 2 or len(free) > 2 or len(conf) > 2:
                continue
            ycands = set(orph)
            if len(orph) <= 1:          # rare: door may create the conflict
                ycands |= flat2
            for yy in sorted(ycands):
                for xx in sources_at(yy, w_to, n):
                    if xx in D1 or weight(xx, yy, n) != w_to:
                        continue
                    if rot(xx) not in flat2:
                        continue        # xx must be an arc exit of E2
                    D2 = dict(D1)
                    D2[xx] = yy
                    st2 = legal_profile(claim_report(E2, D2, n))
                    if st2 is None:
                        continue
                    lab = "nodoor" if dl is None else f"{sp(u)}>{sp(v)}"
                    out.append((f"PRO{w_to}/-{sp(a)}/{lab}/{sp(xx)}>{sp(yy)}",
                                E2, D2, st2, 'P'))
    return out


# ---------------------------------------------------------------- driver

def load_index_for(n, extra=None):
    record = 872 if n == 6 else 5906
    idx = load_index(os.path.join(HERE, f"upstream{record}_canon_index.tsv"))
    for supp in SUPPLEMENTARY.get(n, []):
        p = os.path.join(HERE, supp)
        if os.path.exists(p):
            idx.update(load_index(p))
    for e in (extra or []):
        if os.path.exists(e):
            idx.update({k: 'SHELL:' + v for k, v in load_index(e).items()})
    return idx


def gather(dirs, files_list=None, limit=None, shard=None):
    sel = None
    if files_list:
        sel = set(open(files_list).read().split())
    files = []
    for d in dirs:
        for f in sorted(os.listdir(d)):
            if f.endswith('.txt') and (sel is None or f in sel):
                files.append((f, os.path.join(d, f)))
    if shard:
        i, k = shard
        files = [f for j, f in enumerate(files) if j % k == i]
    if limit:
        files = files[:limit]
    return files


def cls(s):
    return hashlib.sha256(canon(s).encode()).hexdigest()


def run(mode, n, dirs, files_list, outdir, w_from, limit, shard, extra_idx,
        quiet):
    build_inv(n)
    record = 872 if n == 6 else 5906
    idx = load_index_for(n, extra_idx)
    files = gather(dirs, files_list, limit, shard)
    sys.stderr.write(f"index: {len(idx)} known classes; {len(files)} walks\n")
    os.makedirs(outdir, exist_ok=True)
    tot = Counter()
    edges, products, novel = [], {}, {}
    products_written = set()
    for fname, path_ in files:
        src = open(path_).read().strip()
        if not src.isdigit():
            continue
        src_cls = cls(src)
        src_tag = idx.get(src_cls, 'UNKNOWN-' + src_cls[:12])
        for orient, txt in (("F", src), ("R", src[::-1])):
            path = first_visit_path(txt, n)
            E, D, st = structure(path)
            back, _ = replay(E, D, st, n)
            tot['roundtrip-ok' if back == txt else 'roundtrip-BAD'] += 1
            tot['carrier-orientations'] += 1
            if mode == 'demote':
                mv = demotion_moves(E, D, st, n, w_from)
            else:
                mv = promotion_moves(E, D, st, n, w_from)
            tot['admissible-completions'] += len(mv)
            for label, E2, D2, st2, branch in mv:
                tot[f'branch-{branch}'] += 1
                pl = predicted_len(E2, D2, n)
                prod, why = replay(E2, D2, st2, n)
                if prod is None:
                    tot['replay-killed'] += 1
                    tot['kill:' + " ".join(
                        t for t in why.split('(')[0].split()
                        if not t.isdigit())[:40]] += 1
                    continue
                L = len(prod)
                tot[f'product-len-{L}'] += 1
                # GROUND TRUTH: re-derive the product's own structure.  A
                # door added at the walk END is never traversed, so the
                # edit silently degenerates into the (dlen = -1) w4 drop
                # -- the edited structure's allocation is then a lie.
                pE, pD, pst = structure(first_visit_path(prod, n))
                al = alloc_of(pE, pD, n)
                if L != pl:
                    # the new door was never traversed: this is the
                    # dlen = -1 R-BND FWD-w4 DROP, not the trade.  Still
                    # canon-gate it -- it is at or under the record.
                    tot['degenerate-dangling-door'] += 1
                    tot[f'degenerate-len-{L}'] += 1
                    if L <= record:
                        dc = cls(prod)
                        if idx.get(dc) is None:
                            nm = f"drop-{L}-{dc[:12]}.txt"
                            open(os.path.join(outdir, nm), 'w').write(prod)
                            print(f"*** DEGENERATE-DROP NOVEL len={L} {nm}"
                                  f" <- {fname}[{orient}] {label}", flush=True)
                            tot['degenerate-NOVEL'] += 1
                        else:
                            tot['degenerate-known'] += 1
                    continue
                tot[f'product-alloc-{al}'] += 1
                if al != alloc_of(E2, D2, n):
                    tot['ALLOC-MISMATCH'] += 1
                if L != len(txt):
                    tot['NOT-LENGTH-CONSERVING'] += 1
                pc = cls(prod)
                tag = idx.get(pc)
                if L <= record:
                    if tag is None:
                        nm = f"demo-{L}-{pc[:12]}.txt"
                        novel[pc] = (nm, prod)
                        open(os.path.join(outdir, nm), 'w').write(prod)
                        print(f"*** NOVEL-CANDIDATE len={L} {nm} <- "
                              f"{fname}[{orient}] {label}", flush=True)
                        tot['product-NOVEL'] += 1
                    else:
                        tot['product-known'] += 1
                else:
                    tot['product-above-record'] += 1
                    # above-record: NO novelty language; written for the
                    # validator and for class bookkeeping only
                    if pc not in products_written:
                        products_written.add(pc)
                        open(os.path.join(outdir,
                                          f"prod-{L}-{pc[:12]}.txt"),
                             'w').write(prod)
                        tot['above-record-in-known-shell' if tag
                            else 'above-record-outside-known-shell'] += 1
                products[(src_cls, pc)] = products.get((src_cls, pc), 0) + 1
                edges.append((fname, src_tag, orient, label, branch, L,
                              str(al), pc[:12],
                              tag if tag else 'NOVEL',
                              'SELF' if pc == src_cls else 'CROSS'))
                tot['edge-SELF' if pc == src_cls else 'edge-CROSS'] += 1
    ep = os.path.join(outdir, 'edges.tsv')
    with open(ep, 'w') as o:
        o.write("src_file\tsrc_class\torient\tmove\tbranch\tlen\talloc"
                "\ttgt_class12\ttgt_tag\tkind\n")
        for r in sorted(edges):
            o.write("\t".join(map(str, r)) + "\n")
    if not quiet:
        for k, v in sorted(tot.items()):
            print(f"{k}: {v}")
    print(f"\nedges written: {len(edges)} -> {ep}")
    print(f"distinct (src_class,tgt_class) pairs: {len(products)}")
    print(f"novel-candidate classes: {len(novel)}")
    return tot, edges


def census(n, dirs, files_list, out, w_from, limit, shard):
    """Per-carrier w4-door census + branch-condition firing rates."""
    build_inv(n)
    files = gather(dirs, files_list, limit, shard)
    rows, tot = [], Counter()
    for fname, path_ in files:
        src = open(path_).read().strip()
        if not src.isdigit():
            continue
        for orient, txt in (("F", src), ("R", src[::-1])):
            path = first_visit_path(txt, n)
            E, D, st = structure(path)
            end = path[-1]
            rep = claim_report(E, D, n)
            claim, orph, conf, free = rep
            flat = flat_of(E)
            S = sum(len(v) for v in E.values())
            wc = Counter(weight(x, y, n) for x, y in D.items())
            tot[f'src-orphans-{len(orph)}'] += 1
            tot[f'src-free-{len(free)}'] += 1
            tot[f'src-conflicts-{len(conf)}'] += 1
            tot[f'src-len-{predicted_len(E, D, n)}'] += 1
            for x, y in sorted(D.items()):
                if weight(x, y, n) != w_from:
                    continue
                t_x = g(rot(x))
                aA = t_x not in flat
                aB1 = GINV[y] not in flat
                aB2 = GINV[st] not in flat
                free_gate = t_x in (y, st)
                tot['w4-doors'] += 1
                tot['w4-branchA-open'] += int(aA)
                tot['w4-branchB-gy-open'] += int(aB1)
                tot['w4-branchB-gst-open'] += int(aB2)
                tot['w4-freegate-open'] += int(free_gate)
                rows.append((fname, orient, S, str(dict(sorted(wc.items()))),
                             sp(x), sp(y), sp(t_x), int(aA), int(aB1),
                             int(aB2), int(free_gate), len(free), len(conf),
                             sp(end), sp(st)))
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'w') as o:
        o.write("file\torient\tS\tdoor_weights\tdoor_x\tdoor_y\tt_x"
                "\tbranchA_open\tbranchB_gy_open\tbranchB_gst_open"
                "\tfreegate\tn_free\tn_conflict\tend\tstart\n")
        for r in rows:
            o.write("\t".join(map(str, r)) + "\n")
    for k, v in sorted(tot.items()):
        print(f"{k}: {v}")
    print(f"\n{len(rows)} w{w_from}-door rows -> {out}")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    mode = a[0]
    n = int(a[1])
    dirs = a[2].split(',') if len(a) > 2 and not a[2].startswith('--') else []
    def opt(name, d=None):
        return a[a.index(name) + 1] if name in a else d
    files_list = opt('--files')
    out = opt('--out', 'out/s51/demotion/' + mode)
    w_from = int(opt('--w-from', '4'))
    limit = int(opt('--limit')) if '--limit' in a else None
    shard = None
    if '--shard' in a:
        i, k = opt('--shard').split('/')
        shard = (int(i), int(k))
    extra = [opt('--index')] if '--index' in a else []
    quiet = '--quiet' in a
    if mode == 'census':
        census(n, dirs, files_list, out, w_from, limit, shard)
    elif mode in ('demote', 'promote'):
        run(mode, n, dirs, files_list, out, w_from, limit, shard, extra, quiet)
    else:
        print(f"unknown mode {mode}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
