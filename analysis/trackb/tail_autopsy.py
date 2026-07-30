#!/usr/bin/env python3
"""Cycle-level autopsy of a cross-allocation specimen pair's divergent tails."""
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "upstream872"
N = 6
RANK = {"".join(p): i for i, p in enumerate(itertools.permutations("123456"))}
PERM = {i: p for p, i in RANK.items()}


def walk_of(name):
    s = (ARCHIVE / name).read_text().strip()
    seen, out = set(), []
    for i in range(len(s) - N + 1):
        r = RANK.get(s[i : i + N])
        if r is None or r in seen:
            continue
        seen.add(r)
        out.append((r, i + N))
    return out


def cyc(r):
    p = PERM[r]
    return min(p[i:] + p[:i] for i in range(N))


def autopsy(name, d0):
    w = walk_of(name)
    tail = w[d0 - 1 :]
    print(f"--- {name} tail from depth {d0} ({len(tail) - 1} transitions)")
    # sojourn segments: (cycle, run-length of w1s+entry perm)
    segs = []
    cur_cyc, run = cyc(tail[0][0]), 1
    for (r1, p1), (r2, p2) in zip(tail, tail[1:]):
        wgt = p2 - p1
        c2 = cyc(r2)
        if wgt == 1 and c2 == cur_cyc:
            run += 1
        else:
            segs.append((cur_cyc, run))
            cur_cyc, run = c2, 1
            if wgt >= 2:
                segs.append((f"w{wgt}", 0))  # move marker
    segs.append((cur_cyc, run))
    # compact print: moves + per-cycle sojourn lengths
    out = []
    for c, ln in segs:
        out.append(c if ln == 0 else f"{c[:6]}:{ln}")
    print("  " + " | ".join(out))
    # per-cycle composition in the tail
    comp = {}
    for c, ln in segs:
        if ln:
            comp.setdefault(c, []).append(ln)
    multi = {c: v for c, v in comp.items() if len(v) > 1 or sum(v) < 6}
    print(f"  cycles touched in tail: {len(comp)}; split/partial in-tail: {multi}")
    return comp


c1 = autopsy(sys.argv[1] if len(sys.argv) > 1 else "872.up-b020caf20414.txt", int(sys.argv[3]) if len(sys.argv) > 3 else 585)
c2 = autopsy(sys.argv[2] if len(sys.argv) > 2 else "872.up-0105a4b77ce8.txt", int(sys.argv[3]) if len(sys.argv) > 3 else 585)
common = set(c1) & set(c2)
print(f"\ncycles in both tails: {len(common)} of {len(c1)}/{len(c2)}")
diff = {c: (c1.get(c), c2.get(c)) for c in set(c1) | set(c2) if c1.get(c) != c2.get(c)}
print(f"cycles covered DIFFERENTLY: {len(diff)}")
for c, (a, b) in sorted(diff.items()):
    print(f"  {c}: {a} vs {b}")
