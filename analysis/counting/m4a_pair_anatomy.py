#!/usr/bin/env python3
"""s40, M-4a (SURGERY-DESIGN §11.4): anatomy of the cover-sharing pairs.

The s39 cover census (loop_ledger_probe.py cover) found that the
used-loop set is a near-perfect class invariant whose ONLY collisions
are the natural edit boundaries: 12 pairs at n=6 (8× (145,3)↔(143,5)
compound-type, 4× (143,5)↔(142,6) unit-type) and exactly 1 at n=7 —
the Kristan seam (844,17)↔(843,18). Each pair = one loop cover
traversed in two globally different orders.

This script diffs the two traversals of each shared cover in the
theorem's coordinates (THEORY §7: a record = tight loop cover =
Φ = splits full loops + bridge-forest of doors + D+1 door-terminated
single chains):

  - rotors:   which cycles are split, and how (arc compositions);
  - doors:    exit/entry cycles, weight, and which chain each kills;
  - loops:    which loops are FULL in one walk and PARTIAL in the
              other (the demotions the compound move performs);
  - locality: do the changed rotors/doors/loops share cycles?
  - order:    how much of the time-ordered run sequence survives.

Pair lists are the s39 census output; re-derive them any time with
`loop_ledger_probe.py cover 6 data/upstream872` (needs the gitignored
archive) / `cover 7 data/upstream5906` (committed).

Usage: python3 analysis/counting/m4a_pair_anatomy.py [-n 6|7|all]
       python3 analysis/counting/m4a_pair_anatomy.py scan
Exit 0 iff every pair verifies (same cover, both walks tight).

`scan` counts, over the full n=6 archive, the classes carrying each
side's COARSE context of the two rigid rewrite rules M-4a found
(compound: rotors 123654+126354 ⟷ doors 136254→135264 + 162354→132654;
unit: rotor 135462 ⟷ door 135624→135426) — the headroom estimate for
an I4-A rule-application instrument (finer seam conditions not
checked, so these are upper bounds on applicability).
"""
import os
import sys
from collections import Counter

import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting")
from loop_ledger_probe import first_visit_path, g, lam, rot, rotc, weight

PAIRS_N6 = [  # s39 census, data/upstream872 (local archive)
    ("00c66faaa43f", "138d980ad903"),
    ("0105a4b77ce8", "b020caf20414"),
    ("21ccd615e236", "6c85c887e9f4"),
    ("28f85542ce8f", "d0725ab410df"),
    ("2dfc4bc44ed0", "cf4dd22d21fc"),
    ("3bc0308226c0", "84065fb5e583"),
    ("55088ebb4107", "d141177d85e1"),
    ("6f9ab3e1f3b5", "85fad452de0d"),
    ("790718c298dc", "9724c36ea4d7"),
    ("993900e69429", "d47218b82805"),
    ("d159e5ca0117", "faede39dbc44"),
    ("f6fbb176c33e", "fa9dd5040f16"),
]
PAIRS_N7 = [("a30c7c517d7b", "d9a28c2d8195")]  # the Kristan seam


def s(p):
    return "".join(map(str, p))


def loop_cycles(lp, n):
    """The n−1 1-cycles a 2-loop passes through (rotc of its g-orbit)."""
    out, q = set(), lp
    for _ in range(n - 1):
        out.add(rotc(q))
        q = g(q)
    return out


def walk_struct(path, n):
    """Tight-cover coordinates of one walk (asserts the theorem's shape)."""
    arcs = []  # (cycle, entry, exit, start-depth in first-visit perms)
    start = 0
    for i in range(len(path)):
        if i + 1 == len(path) or rotc(path[i + 1]) != rotc(path[i]):
            arcs.append((rotc(path[start]), path[start], path[i], start))
            start = i + 1
    S = len(arcs)
    by_cycle = {}
    for ai, a in enumerate(arcs):
        by_cycle.setdefault(a[0], []).append(ai)

    trans = []  # (w, exit, entry, depth of the entry perm)
    for i in range(S - 1):
        a, b = arcs[i][2], arcs[i + 1][1]
        w = weight(a, b, n)
        trans.append((w, a, b, arcs[i + 1][3]))

    # rotors: split cycles with arc sizes in SPATIAL order (start at the
    # spatially-first entry after the lexicographically-min perm)
    rotors = {}
    rotor_depths = {}
    for c, ais in by_cycle.items():
        if len(ais) < 2:
            continue
        rotor_depths[c] = sorted(arcs[ai][3] for ai in ais)
        entries = {arcs[ai][1]: ai for ai in ais}
        # walk the cycle spatially from its canonical perm
        sizes, cur, order = [], None, []
        p = c
        for _ in range(n):
            if p in entries:
                order.append(p)
            p = rot(p)
        for e in order:
            ai = entries[e]
            length = 1
            q = arcs[ai][1]
            while q != arcs[ai][2]:
                q = rot(q)
                length += 1
            sizes.append(length)
        rotors[c] = sizes

    doors = []  # (depth, w, from-cycle, to-cycle, killed entry v)
    for w, a, b, dep in trans:
        if w >= 3:
            doors.append((dep, w, rotc(a), rotc(b), rot(a)))

    loop_edges = {}
    for w, a, b, _ in trans:
        if w == 2:
            loop_edges.setdefault(lam(b), set()).add(rot(a))
    full = {lp for lp, qs in loop_edges.items() if len(qs) == n - 1}
    partial = {}
    for lp, qs in loop_edges.items():
        if lp in full:
            continue
        chains = []
        for q in qs:
            if g(q) not in qs:  # chain end
                chains.append(g(q))  # the entry the chain STOPS AT
        partial[lp] = (len(qs), chains)

    # chain terminators: entry v whose successor edge is killed by a
    # door/end = rot(exit) of the door's source arc / the last arc
    killers = {v: f"door w{w} {s(cf)}->{s(ct)}" for _, w, cf, ct, v in doors}
    killers[rot(arcs[-1][2])] = "END"

    run_seq = []
    for w, a, b, _ in trans:
        if w == 2:
            lp = lam(b)
            if not run_seq or run_seq[-1] != lp:
                run_seq.append(lp)

    return {
        "S": S, "D": len(doors), "rotors": rotors, "doors": doors,
        "rotor_depths": rotor_depths,
        "cover": frozenset(loop_edges), "full": full, "partial": partial,
        "killers": killers, "run_seq": run_seq,
        "splits": S - len(by_cycle),
    }


def pair_report(dirn, ha, hb, n, pref):
    fa = os.path.join(dirn, f"{pref}{ha}.txt")
    fb = os.path.join(dirn, f"{pref}{hb}.txt")
    wa = walk_struct(first_visit_path(open(fa).read().strip(), n), n)
    wb = walk_struct(first_visit_path(open(fb).read().strip(), n), n)
    ok = wa["cover"] == wb["cover"]
    tight_a = len(wa["full"]) == wa["splits"] and len(wa["partial"]) == wa["D"] + 1
    tight_b = len(wb["full"]) == wb["splits"] and len(wb["partial"]) == wb["D"] + 1
    print(f"\n=== {ha} (S={wa['S']},D={wa['D']}) <-> {hb} (S={wb['S']},D={wb['D']})"
          f"  same-cover={ok} tight={tight_a and tight_b}")

    ra, rb = set(wa["rotors"]), set(wb["rotors"])
    print(f"  rotors: A-only {sorted(s(c) for c in ra - rb)} | "
          f"B-only {sorted(s(c) for c in rb - ra)} | "
          f"shared {len(ra & rb)}"
          + (f" (recomposed: {[s(c) for c in ra & rb if wa['rotors'][c] != wb['rotors'][c]]})"))
    for c in sorted(ra | rb):
        if wa["rotors"].get(c) != wb["rotors"].get(c):
            print(f"    {s(c)}: A={wa['rotors'].get(c)} B={wb['rotors'].get(c)}")

    da = {(w, cf, ct) for _, w, cf, ct, _ in wa["doors"]}
    db = {(w, cf, ct) for _, w, cf, ct, _ in wb["doors"]}
    print(f"  doors: A-only {[(f'w{w}', s(cf), s(ct)) for w, cf, ct in sorted(da - db)]}")
    print(f"         B-only {[(f'w{w}', s(cf), s(ct)) for w, cf, ct in sorted(db - da)]}")
    print(f"         shared {len(da & db)}")

    # depths (first-visit perm index) of the objects the move touches
    dd = []
    for c in ra - rb:
        dd += [("rotorA", s(c), wa["rotor_depths"][c])]
    for c in rb - ra:
        dd += [("rotorB", s(c), wb["rotor_depths"][c])]
    for dep, w, cf, ct, _ in wa["doors"]:
        if (w, cf, ct) in da - db:
            dd += [("doorA", f"{s(cf)}->{s(ct)}", [dep])]
    for dep, w, cf, ct, _ in wb["doors"]:
        if (w, cf, ct) in db - da:
            dd += [("doorB", f"{s(cf)}->{s(ct)}", [dep])]
    flat = [d for *_, ds in dd for d in ds]
    print(f"  depths of moved objects: {sorted(flat)} "
          f"(span {min(flat)}–{max(flat)} of {720 if n == 6 else 5040})")

    dem = wa["full"] - wb["full"]  # full in A, partial in B
    pro = wb["full"] - wa["full"]
    print(f"  loops demoted A->B: {sorted(s(l) for l in dem)}; "
          f"promoted A->B: {sorted(s(l) for l in pro)}")
    onlyp_a = set(wa["partial"]) - set(wb["partial"])
    onlyp_b = set(wb["partial"]) - set(wa["partial"])
    both_p = set(wa["partial"]) & set(wb["partial"])
    moved = [
        lp for lp in both_p
        if wa["partial"][lp] != wb["partial"][lp]
    ]
    print(f"  partial-only-A {sorted(s(l) for l in onlyp_a)} "
          f"partial-only-B {sorted(s(l) for l in onlyp_b)} "
          f"re-chained-shared {sorted(s(l) for l in moved)}")

    # locality: cycles touched by the diff
    touched = set()
    for c in (ra ^ rb):
        touched.add(c)
    for c in ra & rb:
        if wa["rotors"][c] != wb["rotors"][c]:
            touched.add(c)
    for w, cf, ct in da ^ db:
        touched.add(cf)
        touched.add(ct)
    dl_cycles = set()
    for lp in dem | pro:
        dl_cycles |= loop_cycles(lp, n)
    print(f"  locality: {len(touched)} cycles touched by rotor/door diff; "
          f"demoted/promoted loops span {len(dl_cycles)} cycles; "
          f"overlap {len(touched & dl_cycles)}")

    # order preservation
    sa, sb = wa["run_seq"], wb["run_seq"]
    pfx = 0
    while pfx < min(len(sa), len(sb)) and sa[pfx] == sb[pfx]:
        pfx += 1
    sfx = 0
    while sfx < min(len(sa), len(sb)) - pfx and sa[-1 - sfx] == sb[-1 - sfx]:
        sfx += 1
    print(f"  run order: |A|={len(sa)} |B|={len(sb)} common prefix {pfx} "
          f"suffix {sfx} (middle {len(sa) - pfx - sfx} vs {len(sb) - pfx - sfx})")
    return ok and tight_a and tight_b, (dem | pro, touched)


def scan_archive():
    """Coarse rule-context census over data/upstream872 (fast path:
    arcs + doors only, no loop machinery)."""
    n = 6
    c_123654 = rotc(tuple(int(x) for x in "123654"))
    c_126354 = rotc(tuple(int(x) for x in "126354"))
    c_135462 = rotc(tuple(int(x) for x in "135462"))
    comp_doors = {
        (3, rotc(tuple(int(x) for x in "136254")), rotc(tuple(int(x) for x in "135264"))),
        (3, rotc(tuple(int(x) for x in "162354")), rotc(tuple(int(x) for x in "132654"))),
    }
    unit_door = (3, rotc(tuple(int(x) for x in "135624")), rotc(tuple(int(x) for x in "135426")))
    counts = Counter()
    d = "data/upstream872"
    for f in sorted(os.listdir(d)):
        if not f.endswith(".txt"):
            continue
        txt = open(os.path.join(d, f)).read().strip()
        if not txt.isdigit():
            continue
        path = first_visit_path(txt, n)
        arcs = []
        start = 0
        for i in range(len(path)):
            if i + 1 == len(path) or rotc(path[i + 1]) != rotc(path[i]):
                arcs.append((rotc(path[start]), path[start], path[i]))
                start = i + 1
        by_cycle = Counter(a[0] for a in arcs)
        doors = set()
        n_doors = 0
        for i in range(len(arcs) - 1):
            w = weight(arcs[i][2], arcs[i + 1][1], n)
            if w >= 3:
                doors.add((w, arcs[i][0], arcs[i + 1][0]))
                n_doors += 1
        S = len(arcs)
        alloc = (S, n_doors)
        counts[("total", alloc)] += 1
        if by_cycle[c_123654] == 2 and by_cycle[c_126354] == 2:
            counts[("compound-rotor-side", alloc)] += 1
        if comp_doors <= doors:
            counts[("compound-door-side", alloc)] += 1
        if by_cycle[c_135462] == 2:
            counts[("unit-rotor-side", alloc)] += 1
        if unit_door in doors:
            counts[("unit-door-side", alloc)] += 1
    for key in ["compound-rotor-side", "compound-door-side",
                "unit-rotor-side", "unit-door-side"]:
        tot = {a: c for (k, a), c in counts.items() if k == key}
        print(f"{key}: {sum(tot.values())} classes, by (S,D): "
              f"{dict(sorted(tot.items()))}")
    return 0


def main():
    which = "all"
    if len(sys.argv) == 2 and sys.argv[1] == "scan":
        return scan_archive()
    if len(sys.argv) == 3 and sys.argv[1] == "-n":
        which = sys.argv[2]
    all_ok = True
    recur = Counter()
    if which in ("6", "all"):
        print("### n=6 pairs (archive data/upstream872)")
        for ha, hb in PAIRS_N6:
            ok, (dloops, tcyc) = pair_report(
                "data/upstream872", ha, hb, 6, "872.up-")
            all_ok &= ok
            for c in tcyc:
                recur[s(c)] += 1
        print("\nrecurring diff-touched cycles across n=6 pairs:",
              {c: k for c, k in recur.most_common() if k > 1} or "none")
    if which in ("7", "all"):
        print("\n### n=7 pair (the Kristan seam, committed corpus)")
        for ha, hb in PAIRS_N7:
            ok, _ = pair_report("data/upstream5906", ha, hb, 7, "5906.up-")
            all_ok &= ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
