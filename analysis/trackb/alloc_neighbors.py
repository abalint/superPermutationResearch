#!/usr/bin/env python3
"""Waste-146 (length-871) target shell vs the 8 specimen-backed anchors (s27).

Every known 872 lives in one of 8 L0 allocations (the s26c census). An 871
lives in some open waste-146 allocation. Cross-class surgery edits a walk's
allocation by local cycle-level rewrites; at ledger level these are unit
edits of the tuple (S, d3, d4, d5, ip) with waste coefficients
(1, 1, 2, 3, 1). This script ranks every OPEN waste-146 allocation by its
minimum L1 edit distance to a specimen-backed anchor — the surgery targets
reachable with the fewest priced rewrites from a real 872.

Unit edits (waste delta): S-1 = sojourn merge (-1); S+1 = split (+1);
d3-1 = w3 door -> w2x (-1); d4-1 & d3+1 = w4 -> w3 door (-1); etc.

Usage: python3 analysis/trackb/alloc_neighbors.py
           [--ledger analysis/trackb/ledger_l0.csv]
           [--out analysis/trackb/waste146_neighbors.tsv]
"""
import csv
import sys

ANCHORS = {  # allocation -> classes in the community corpus (s26c census)
    (145, 3, 0, 0, 0): 21144,
    (143, 5, 0, 0, 0): 470,
    (140, 6, 1, 0, 0): 388,
    (142, 6, 0, 0, 0): 19,
    (135, 9, 2, 0, 0): 18,
    (140, 8, 0, 0, 0): 10,
    (138, 8, 1, 0, 0): 9,
    (141, 7, 0, 0, 0): 4,
}
FIELDS = ["S", "d3", "d4", "d5", "ip"]


def dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def edit_str(anchor, target):
    parts = []
    for f, x, y in zip(FIELDS, anchor, target):
        if y != x:
            parts.append(f"{f}{y - x:+d}")
    return " ".join(parts)


def main():
    ledger = "analysis/trackb/ledger_l0.csv"
    out_path = "analysis/trackb/waste146_neighbors.tsv"
    args = sys.argv[1:]
    if "--ledger" in args:
        ledger = args[args.index("--ledger") + 1]
    if "--out" in args:
        out_path = args[args.index("--out") + 1]

    rows = []
    with open(ledger) as f:
        for r in csv.DictReader(f):
            if r["waste"] != "146" or r["status"] != "open":
                continue
            if r["d6"] != "0":
                continue  # anchors are all d6=0; d6 edits are not unit moves
            rows.append(
                (
                    tuple(int(r[k]) for k in FIELDS),
                    r["notes"],
                )
            )
    print(f"open waste-146 (871) allocations with d6=0: {len(rows)}")

    ranked = []
    for alloc, notes in rows:
        d, anchor = min((dist(alloc, a), a) for a in ANCHORS)
        ranked.append((d, alloc, anchor, notes))
    ranked.sort()

    hist = {}
    for d, *_ in ranked:
        hist[d] = hist.get(d, 0) + 1
    print("min-distance histogram (edits from nearest anchor):")
    for d in sorted(hist):
        print(f"  distance {d}: {hist[d]} allocations")

    print("\nall targets within 2 edits of a specimen-backed anchor:")
    near = [x for x in ranked if x[0] <= 2]
    for d, alloc, anchor, notes in near:
        a_str = ",".join(map(str, anchor))
        t_str = ",".join(map(str, alloc))
        print(
            f"  d={d}  {a_str} ({ANCHORS[anchor]} classes) -> {t_str}"
            f"  [{edit_str(anchor, alloc)}]" + (f"  {notes}" if notes else "")
        )

    print("\nper-anchor: nearest open 146 target and its distance:")
    for a in sorted(ANCHORS, key=lambda k: -ANCHORS[k]):
        d, alloc, notes = min(
            (dist(alloc, a), alloc, notes) for alloc, notes in rows
        )
        print(
            f"  {','.join(map(str, a))} ({ANCHORS[a]} cl): d={d} -> "
            f"{','.join(map(str, alloc))} [{edit_str(a, alloc)}]"
            + (f"  {notes}" if notes else "")
        )

    with open(out_path, "w") as f:
        f.write("min_dist\tS\td3\td4\td5\tip\tanchor\tedits\tnotes\n")
        for d, alloc, anchor, notes in ranked:
            f.write(
                f"{d}\t" + "\t".join(map(str, alloc)) + "\t"
                + ",".join(map(str, anchor)) + "\t"
                + edit_str(anchor, alloc) + f"\t{notes}\n"
            )
    print(f"\nwrote {out_path} ({len(ranked)} rows)")


if __name__ == "__main__":
    main()
