#!/usr/bin/env python3
"""s43: anatomy of tail-conjugate pairs (the census that CAN see
non-cover-preserving rules).

Input: the --pairs/--all TSV from tail_conjugacy_census.py. For every
pair sharing at least --min-perms tail perms (default 256), align the
two walks under the tail relabeling and diff them in the s39 theorem's
coordinates (m4a_pair_anatomy.walk_struct): allocations, cover
intersection, promoted/demoted loops, rotor and door diffs, and where
the diff objects sit relative to the shared-tail boundary.

The alignment detail that makes the diff meaningful: if A's o_a-tail
matches B's o_b-tail from depth d under relabeling sigma (first-
occurrence renumbering of both tails), then sigma(B) is a walk whose
literal suffix EQUALS sigma'(A)'s — so we compare walk_struct of the
two RELABELED, orientation-aligned walks. Every structural difference
then lives strictly in the head (depth < d), and shared-cover loops
are literally identical objects, not just relabel-equivalent.

Usage:
  python3 analysis/counting/tail_pair_anatomy.py -n 7 out/s43/tail_all_n7.tsv \
      --dirs data/upstream5906,data/novel5906 [--min-perms 256]
"""
import os
import sys
from itertools import permutations
from math import factorial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loop_ledger_probe import first_visit_path, lam, rotc
from m4a_pair_anatomy import walk_struct
from tail_conjugacy_census import Walk, first_visit_starts, renumber


def swap_signature(wa, wb, ra_r, rb_r, recomposed, ca, cb, n):
    """Relabel-canonical form of a pair's swap bundle: the A-side and
    B-side rotors (cycle + composition) and swapped loops, minimized
    jointly over all n! relabelings (and A/B side order). Two pairs
    carry the SAME rigid move iff their signatures are equal."""
    a_rot = [(c, tuple(wa["rotors"][c])) for c in (ra_r - rb_r) | set(recomposed)]
    b_rot = [(c, tuple(wb["rotors"][c])) for c in (rb_r - ra_r) | set(recomposed)]
    a_lp, b_lp = sorted(ca - cb), sorted(cb - ca)

    def apply(sig, sigma):
        rots, lps = sig
        return (
            tuple(sorted((rotc(tuple(sigma[x - 1] for x in c)), comp)
                         for c, comp in rots)),
            tuple(sorted(lam(tuple(sigma[x - 1] for x in lp)) for lp in lps)),
        )

    best = None
    for sigma in permutations(range(1, n + 1)):
        for side in ((a_rot, a_lp, b_rot, b_lp), (b_rot, b_lp, a_rot, a_lp)):
            cand = (apply((side[0], side[1]), sigma), apply((side[2], side[3]), sigma))
            if best is None or cand < best:
                best = cand
    return best


def relabel_map(tail):
    """first-occurrence renumbering map char -> canonical char."""
    m, nxt = {}, 0
    for c in tail:
        if c not in m:
            nxt += 1
            m[c] = str(nxt)
    return m


def aligned_strings(wa, oa, wb, ob, d):
    """Both walks, orientation-aligned and relabeled so the shared
    d-tails become literally identical."""
    sa = wa.fwd if oa == "f" else wa.rev
    sb = wb.fwd if ob == "f" else wb.rev
    ta = sa[(wa.fwd_starts if oa == "f" else wa.rev_starts)[d] :]
    tb = sb[(wb.fwd_starts if ob == "f" else wb.rev_starts)[d] :]
    ma, mb = relabel_map(ta), relabel_map(tb)
    ra = "".join(ma[c] for c in sa)  # tail chars canonical; head chars
    rb = "".join(mb[c] for c in sb)  # get the same map (tail hits all n)
    assert ra.endswith(renumber(ta)) and rb.endswith(renumber(tb))
    return ra, rb


def main():
    args = sys.argv[1:]
    n = 6
    if args[:1] == ["-n"]:
        n = int(args[1])
        args = args[2:]
    tsv = args[0]
    dirs, min_perms, verbose = [], 256, False
    signature = False
    sig_out = None
    sig_counts = {}
    sig_rows = []
    i = 1
    while i < len(args):
        if args[i] == "--dirs":
            dirs = args[i + 1].split(",")
            i += 2
        elif args[i] == "--min-perms":
            min_perms = int(args[i + 1])
            i += 2
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        elif args[i] == "--signature":
            signature = True
            i += 1
        elif args[i] == "--sig-out":
            sig_out = args[i + 1]
            i += 2
        else:
            i += 1
    nfact = factorial(n)

    files = {}
    for d in dirs:
        for f in sorted(os.listdir(d)):
            if f.endswith(".txt"):
                files[f] = os.path.join(d, f)

    pairs = []
    with open(tsv) as fh:
        next(fh)
        for line in fh:
            a, b, dd, sp, orient, status = line.rstrip("\n").split("\t")
            if int(sp) >= min_perms and status != "KNOWN-EDGE":
                pairs.append((a, b, int(dd), orient))
    pairs.sort(key=lambda p: p[2])
    print(f"{len(pairs)} NEW pairs sharing >= {min_perms} tail perms")

    walks = {}
    for a, b, *_ in pairs:
        for name in (a, b):
            if name not in walks:
                walks[name] = Walk(name, open(files[name]).read().strip(), n)

    for a, b, d, orient in pairs:
        oa, ob = orient
        ra, rb = aligned_strings(walks[a], oa, walks[b], ob, d)
        wa = walk_struct(first_visit_path(ra, n), n)
        wb = walk_struct(first_visit_path(rb, n), n)
        ca, cb = wa["cover"], wb["cover"]
        tight_a = len(wa["full"]) == wa["splits"] and len(wa["partial"]) == wa["D"] + 1
        tight_b = len(wb["full"]) == wb["splits"] and len(wb["partial"]) == wb["D"] + 1
        da = {(w, cf, ct) for _, w, cf, ct, _ in wa["doors"]}
        db = {(w, cf, ct) for _, w, cf, ct, _ in wb["doors"]}
        ra_r, rb_r = set(wa["rotors"]), set(wb["rotors"])
        recomposed = [c for c in ra_r & rb_r if wa["rotors"][c] != wb["rotors"][c]]
        # depths of diff objects (rotor sides + door sides not shared)
        depths = []
        for c in ra_r - rb_r:
            depths += wa["rotor_depths"][c]
        for c in rb_r - ra_r:
            depths += wb["rotor_depths"][c]
        for c in recomposed:
            depths += wa["rotor_depths"][c] + wb["rotor_depths"][c]
        for dep, w, cf, ct, _ in wa["doors"]:
            if (w, cf, ct) in da - db:
                depths.append(dep)
        for dep, w, cf, ct, _ in wb["doors"]:
            if (w, cf, ct) in db - da:
                depths.append(dep)
        span = f"{min(depths)}-{max(depths)}" if depths else "none"
        # shared literal HEAD: longest common prefix of the aligned
        # strings after head-side renumbering (heads relabel-conjugate)
        ha, hb = renumber(ra), renumber(rb)
        pfx = 0
        while pfx < min(len(ha), len(hb)) and ha[pfx] == hb[pfx]:
            pfx += 1
        starts_a = first_visit_starts(ra, n)
        head_perms = sum(1 for st in starts_a if st + n <= pfx)
        print(f"\n=== {a}[{oa}] ~ {b}[{ob}]  shared tail {nfact - d} perms (d={d})")
        print(f"  shared head: {head_perms} perms (lcp {pfx} chars)")
        print(f"  alloc A=(S={wa['S']},D={wa['D']}) B=(S={wb['S']},D={wb['D']}) "
              f"tight={tight_a and tight_b}")
        print(f"  cover: |A|={len(ca)} |B|={len(cb)} |A&B|={len(ca & cb)} "
              f"A-only={len(ca - cb)} B-only={len(cb - ca)}")
        print(f"  loops full-A&partial-B={len(wa['full'] - wb['full'] - (ca - cb))} "
              f"full-B&partial-A={len(wb['full'] - wa['full'] - (cb - ca))}")
        print(f"  rotors: A-only={len(ra_r - rb_r)} B-only={len(rb_r - ra_r)} "
              f"recomposed={len(recomposed)} shared-same={len(ra_r & rb_r) - len(recomposed)}")
        print(f"  doors: A-only={len(da - db)} B-only={len(db - da)} shared={len(da & db)}")
        print(f"  diff-object depth span: {span} (shared-tail boundary at {d})")
        if verbose:
            sig_a = sorted(tuple(sorted(wa["rotors"][c])) for c in ra_r - rb_r)
            sig_b = sorted(tuple(sorted(wb["rotors"][c])) for c in rb_r - ra_r)
            rec = sorted(
                (tuple(sorted(wa["rotors"][c])), tuple(sorted(wb["rotors"][c])))
                for c in recomposed
            )
            print(f"  A-only rotor compositions: {sig_a}")
            print(f"  B-only rotor compositions: {sig_b}")
            print(f"  recomposed (A->B): {rec}")
            # do the swapped loops ride the swapped rotors? loop->cycles
            from m4a_pair_anatomy import loop_cycles

            a_only_cyc = set()
            for lp in ca - cb:
                a_only_cyc |= loop_cycles(lp, n)
            b_only_cyc = set()
            for lp in cb - ca:
                b_only_cyc |= loop_cycles(lp, n)
            print(f"  A-only loops span {len(a_only_cyc)} cycles, "
                  f"hit {len(a_only_cyc & (ra_r - rb_r))} A-only rotors; "
                  f"B-only loops span {len(b_only_cyc)} cycles, "
                  f"hit {len(b_only_cyc & (rb_r - ra_r))} B-only rotors; "
                  f"span overlap {len(a_only_cyc & b_only_cyc)}")
        if signature:
            import hashlib

            sig = swap_signature(wa, wb, ra_r, rb_r, recomposed, ca, cb, n)
            h = hashlib.sha256(repr(sig).encode()).hexdigest()[:12]
            sig_counts.setdefault(h, []).append((a, b))
            sig_rows.append((a, b, nfact - d, len(ca - cb), len(da ^ db), h))
            print(f"  swap signature: {h}")
    if signature and sig_counts:
        print("\nsignature classes:")
        for h, members in sorted(sig_counts.items(), key=lambda kv: -len(kv[1])):
            print(f"  {h}: {len(members)} pairs")
    if sig_out and sig_rows:
        with open(sig_out, "w") as out:
            out.write("class_a\tclass_b\tshared_perms\tloops_swapped\t"
                      "doors_changed\tswap_signature\n")
            for row in sig_rows:
                out.write("\t".join(map(str, row)) + "\n")
        print(f"-> {sig_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
