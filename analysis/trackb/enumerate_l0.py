#!/usr/bin/env python3
"""L0 enumeration + class ledger (TRACKB-DESIGN par.2, post-T0 form).

Coordinates. T0 (verify_identity.py, 806 walks, zero exceptions) fixed the
fully general waste identity for any canonical (first-visit) walk at n=6:

    waste = (S-1) + d3 + 2*d4 + 3*d5 + 4*d6 + ip

where S = sojourn count, dK = cycle-changing (door) transitions of weight K
(d6 = fallback-style 0-overlap doors; intra-orbit w6 is impossible at n=6 --
rotation by 6 is the identity), and ip = total priced waste of intra-orbit
skip moves, ip = i2 + 2*i3 + 3*i4 + 4*i5 (rotate-by-k passes k-1 already-
visited members and costs k-1 waste). The design's original 5-tuple carried
i2 alone; T0 showed i3/i4/i5 and d6 are legal walk moves under budget 146,
so the allocation tuple here is (S, d3, d4, d5, d6, ip). L1 refines ip's
composition per cycle; at L0 only its priced total constrains anything.

Universe. Budget waste <= 146 (target 871), S in [120, 147] (every one of
the 120 rotation cycles needs >= 1 sojourn; S-1 <= waste).

Closure lemmas applied per allocation:

  LB-869 (urdvr Lean floor, adopted s19/s20): waste <= 143 <=> length <= 868
    < 869 = S(6) lower bound. Closes everything below the live shell; the
    live (a-priori-open) shell is waste in {144, 145, 146} = lengths
    {869, 870, 871}.

  Lemma B (pass-over capacity; NEW, from T0's canonical-reading lemma):
    In canonical reading an intra-orbit skip move (rotate-by-k, k in 2..5)
    passes k-1 members that must ALL be already visited, and lands on (and
    thereby covers) an unvisited member of the same cycle. Consider a cycle
    covered by p sojourns, sojourn j covering len_j members (sum = 6,
    len_j >= 1; the door entering sojourn j lands on its first covered
    member). Skip moves happen only between consecutive covers, so sojourn j
    has len_j - 1 skip slots, each passing at most 4 members (rotate-5);
    passed members must come from earlier sojourns' covers, so
    pass_j <= min(V_j, 4*(len_j - 1)) with V_j = sum_{k<j} len_k, and the
    cycle's priced intra waste is sum_j pass_j <= f(p) :=
    max over compositions of that sum = (0, 4, 6, 6, 4, 0) for p = 1..6
    (p=2 realized by covers {0..3} then enter 5, rotate-5 past 0,1,2,3 to 4).
    Marginal gain per extra part is 4, 2, 0, ..., so with S - 120 extra
    parts total, spreading splits over distinct cycles at p = 2 dominates:

        ip <= 4 * (S - 120).

    In particular S = 120 forces ip = 0. Allocations violating this are
    closed unconditionally.

Annotations (not closures):

  s11-grammar-subregion: for rows with ip = 0 and d6 = 0, the gain-one
    certificate-grammar sub-region of the allocation is closed by the s10/s11
    theorem (Egan-1 = 872 optimal in-grammar); residual openness is
    out-of-grammar structure only.
  perfect-ride family: S = 120 rows are exactly the no-split walks (120 full
    rides + 119 doors); minimizing waste over that family is a 120-node
    cycle-level ATSP over the door atlas (T1) -- exactly solvable, a cheap
    future closure path.

Output: ledger_l0.csv (live-shell rows only, one per allocation) plus
summary counts including M1 (fraction of live shell closed by lemma).
Verified against the corpus: every T0-measured walk allocation must map to
waste >= 147, i.e. OUTSIDE this ledger (no known walk is sub-872).
"""

import csv
import os
import sys

BUDGET = 146
LB_WASTE_FLOOR = 144  # waste <= 143 <=> length <= 868 < 869 (Lean LB)
LIVE = (144, 145, 146)  # lengths 869, 870, 871


def enumerate_allocations():
    """Yield (S, d3, d4, d5, d6, ip, waste) for all waste <= BUDGET."""
    for s in range(120, 148):
        base = s - 1
        rem0 = BUDGET - base
        for d6 in range(rem0 // 4 + 1):
            rem1 = rem0 - 4 * d6
            for d5 in range(rem1 // 3 + 1):
                rem2 = rem1 - 3 * d5
                for d4 in range(rem2 // 2 + 1):
                    rem3 = rem2 - 2 * d4
                    for d3 in range(rem3 + 1):
                        for ip in range(rem3 - d3 + 1):
                            yield (
                                s,
                                d3,
                                d4,
                                d5,
                                d6,
                                ip,
                                base + d3 + 2 * d4 + 3 * d5 + 4 * d6 + ip,
                            )


def classify(s, d3, d4, d5, d6, ip, waste):
    """(status, closure, notes) for one allocation."""
    if waste < LB_WASTE_FLOOR:
        return "closed-lemma", "LB-869", ""
    if ip > 4 * (s - 120):
        return "closed-lemma", "lemma-B-passover", ""
    notes = []
    if ip == 0 and d6 == 0:
        notes.append("s11-grammar-subregion-closed")
    if s == 120:
        notes.append("perfect-ride-family(ATSP-closable)")
    return "open", "", ";".join(notes)


def selfcheck_lemma_b():
    """Brute-force the per-cycle pass capacity f(p) and the 4-per-split cap."""
    from itertools import product

    def compositions(total, parts):
        if parts == 1:
            yield (total,)
            return
        for first in range(1, total - parts + 2):
            for rest in compositions(total - first, parts - 1):
                yield (first,) + rest

    f = {}
    for p in range(1, 7):
        best = 0
        for comp in compositions(6, p):
            v = 0
            tot = 0
            for j, ln in enumerate(comp):
                if j > 0:
                    tot += min(v, 4 * (ln - 1))
                v += ln
            best = max(best, tot)
        f[p] = best
    assert f == {1: 0, 2: 4, 3: 6, 4: 6, 5: 4, 6: 0}, f
    # spreading splits at p=2 dominates any multiset with the same extra-part
    # total: check exhaustively for E <= 27 over per-cycle part multisets
    for e in range(28):
        best = 0
        # partitions of e into per-cycle extras (each extra in 1..5)
        def rec(rem, max_extra, acc):
            nonlocal best
            if rem == 0:
                best = max(best, acc)
                return
            for x in range(1, min(rem, max_extra) + 1):
                rec(rem - x, x, acc + f[x + 1])

        rec(e, 5, 0)
        assert best == 4 * e, (e, best)


def main():
    selfcheck_lemma_b()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger_l0.csv")
    n_total = 0
    n_lb = 0
    live_rows = []
    for s, d3, d4, d5, d6, ip, waste in enumerate_allocations():
        n_total += 1
        status, closure, notes = classify(s, d3, d4, d5, d6, ip, waste)
        if waste < LB_WASTE_FLOOR:
            n_lb += 1
            continue  # bulk closed by the Lean floor; not emitted as rows
        live_rows.append(
            {
                "S": s,
                "d3": d3,
                "d4": d4,
                "d5": d5,
                "d6": d6,
                "ip": ip,
                "waste": waste,
                "length": 725 + waste,
                "status": status,
                "closure": closure,
                "notes": notes,
            }
        )

    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(live_rows[0].keys()))
        w.writeheader()
        w.writerows(live_rows)

    n_live = len(live_rows)
    n_b = sum(r["closure"] == "lemma-B-passover" for r in live_rows)
    n_open = sum(r["status"] == "open" for r in live_rows)
    n_gram = sum("s11" in r["notes"] for r in live_rows)
    n_ride = sum("perfect-ride" in r["notes"] for r in live_rows)
    per_len = {
        ln: sum(1 for r in live_rows if r["length"] == ln and r["status"] == "open")
        for ln in (869, 870, 871)
    }
    print(f"allocations, waste <= {BUDGET}:      {n_total}")
    print(f"closed by LB-869 (waste<=143):   {n_lb}  ({n_lb / n_total:.1%})")
    print(f"live shell (waste 144-146):      {n_live}")
    print(f"  closed by lemma B (pass-over): {n_b}")
    print(f"  open:                          {n_open}")
    print(f"    of which s11-subregion note: {n_gram}")
    print(f"    of which perfect-ride:       {n_ride}")
    print(f"  open by target length:         {per_len}")
    m1_live = n_b / n_live
    m1_all = (n_lb + n_b) / n_total
    print(f"M1 (live shell closed by lemma): {m1_live:.1%}")
    print(f"M1 (all allocations closed):     {m1_all:.1%}")
    print(f"ledger written: {out} ({n_live} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
