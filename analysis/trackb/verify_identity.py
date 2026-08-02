#!/usr/bin/env python3
"""T0 (TRACKB-DESIGN par.2): machine-verify the i2-priced waste identity.

Stated identity (n=6 form, the one the L0 ledger will be built on):

    waste = (S - 1) + #w3 + 2*#w4 + 3*#w5 + i2

where the walk is the string's FIRST-VISIT permutation sequence with
maximal-overlap transition weights, S = number of sojourns (maximal runs
inside one rotation cycle), #wK = count of *inter-sojourn* (cycle-changing)
weight-K transitions, and i2 = count of intra-orbit weight-2 transitions
(double rotations).

Working on the string reading (first occurrences) rather than a searcher's
internal path makes the check independent of walk bookkeeping and immune to
the emergent-edge subtlety (Kristan 2026-07-29): a composed move whose
appended characters spell an unvisited permutation is read here as its
decomposed line, which is the canonical form of the same string.

The fully-priced general identity (arithmetic given the segmentation, so it
must hold with ZERO exceptions on every walk; verified as a self-check of
the decomposition):

    waste = (S - 1) + sum_{w>=3} (w-2)*inter[w] + sum_{w>=2} (w-1)*intra[w]

The stated n=6 form equals the general form exactly when intra[w] = 0 for
w >= 3 and inter[w] = 0 for w >= 6. T0's question is precisely whether such
moves occur in the corpus and what correction terms they force.

Usage:
    python3 verify_identity.py FILE [FILE ...]

Every non-empty line of every input file is treated as one candidate
superpermutation string (single-string .txt files and rollout --strings
files both work). n is inferred per line as the max digit. Exit 0 iff the
general identity holds on every line (it must) — the stated-form verdict
is reported per corpus slice.
"""

import sys
from collections import Counter
from math import factorial


# s64 P1: one body, in pylib/walkio.py.  Re-exported here because
# analysis/counting/upstream5906_structure.py imports both from this module.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
from pylib.walkio import first_visit_path, overlap  # noqa: E402,F401


def cycle_key(p):
    """Canonical rotation-cycle label: the minimal rotation of p."""
    n = len(p)
    return min(tuple(p[i:] + p[:i]) for i in range(n))


def analyze(s):
    """Ledger decomposition + identity check for one string."""
    n = max(int(c) for c in s)
    path = first_visit_path(s, n)
    nfact = factorial(n)
    complete = len(path) == nfact
    weights = []
    inter = Counter()  # cycle-changing transitions by weight
    intra = Counter()  # same-cycle transitions by weight
    S = 1
    for p, q in zip(path, path[1:]):
        w = n - overlap(p, q)
        weights.append(w)
        if cycle_key(p) != cycle_key(q):
            S += 1
            inter[w] += 1
        else:
            intra[w] += 1
    replay_len = n + sum(weights)
    waste = replay_len - (nfact + n - 1)
    stated = (S - 1) + inter[3] + 2 * inter[4] + 3 * inter[5] + intra[2]
    general = (
        (S - 1)
        + sum((w - 2) * c for w, c in inter.items() if w >= 3)
        + sum((w - 1) * c for w, c in intra.items() if w >= 2)
    )
    return {
        "n": n,
        "complete": complete,
        "visited": len(path),
        "input_len": len(s),
        "replay_len": replay_len,
        "tight": replay_len == len(s),
        "waste": waste,
        "S": S,
        "inter": dict(inter),
        "intra": dict(intra),
        "stated": stated,
        "general": general,
        "stated_ok": stated == waste,
        "general_ok": general == waste,
        # correction terms the stated form is missing on this walk
        "corr_intra_w3plus": {w: c for w, c in intra.items() if w >= 3},
        "corr_inter_w6plus": {w: c for w, c in inter.items() if w >= 6},
        "inter_w1": inter[1],  # must be 0: weight-1 moves cannot change cycle
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    total = 0
    stated_fail = []
    general_fail = []
    slices = {}  # file -> [results]
    for fname in argv[1:]:
        with open(fname) as f:
            lines = [ln.strip() for ln in f]
        results = []
        for idx, ln in enumerate(lines):
            if not ln or not ln.isdigit():
                continue
            r = analyze(ln)
            r["src"] = f"{fname}:{idx + 1}"
            total += 1
            results.append(r)
            assert r["inter_w1"] == 0, f"cycle-changing w1 move in {r['src']}"
            if not r["general_ok"]:
                general_fail.append(r)
            if not r["stated_ok"]:
                stated_fail.append(r)
        if results:
            slices[fname] = results

    print(f"strings checked: {total}")
    print(f"general identity failures: {len(general_fail)} (must be 0)")
    print(f"stated i2-form failures:   {len(stated_fail)}")
    print()
    hdr = (
        f"{'slice':58s} {'#':>4s} {'n':>2s} {'stated-ok':>9s} "
        f"{'tight':>5s} {'waste range':>12s} {'S range':>9s}"
    )
    print(hdr)
    for fname, results in slices.items():
        ok = sum(r["stated_ok"] for r in results)
        tight = sum(r["tight"] for r in results)
        ws = [r["waste"] for r in results]
        ss = [r["S"] for r in results]
        ns = sorted({r["n"] for r in results})
        print(
            f"{fname[-58:]:58s} {len(results):4d} "
            f"{'/'.join(map(str, ns)):>2s} "
            f"{ok:4d}/{len(results):<4d} {tight:5d} "
            f"{min(ws):5d}-{max(ws):<6d} {min(ss):4d}-{max(ss):<4d}"
        )
    if stated_fail:
        print("\nstated-form deviations (waste - stated = missing terms):")
        agg = Counter()
        for r in stated_fail:
            dev = r["waste"] - r["stated"]
            expl = (
                sum((w - 1) * c for w, c in r["corr_intra_w3plus"].items())
                + sum((w - 2) * c for w, c in r["corr_inter_w6plus"].items())
            )
            agg[dev == expl] += 1
        print(
            f"  {sum(agg.values())} deviating walks; deviation exactly explained by "
            f"intra-orbit w>=3 (priced w-1) + inter w>=6 (priced w-2) terms: "
            f"{agg[True]}/{sum(agg.values())}"
        )
        for r in stated_fail[:10]:
            print(
                f"  {r['src']}: waste={r['waste']} stated={r['stated']} "
                f"intra_w3+={r['corr_intra_w3plus']} inter_w6+={r['corr_inter_w6plus']}"
            )
    return 1 if general_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
