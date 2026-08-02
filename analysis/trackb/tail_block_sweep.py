#!/usr/bin/env python3
"""Mini-sweep: block-ATSP at the block boundary nearest depth ~585 for a
sample of corpus walks. Reports any improvement (=> 871 candidate) and the
block-count/timing distribution."""
import random
import sys
import time
from pathlib import Path

import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/trackb")
from tail_block_atsp import ARCHIVE, blocks_of, solve, walk_of

TARGET = 585
SAMPLE = int(sys.argv[1]) if len(sys.argv) > 1 else 300
MAXB = 27  # exact-B&B comfort zone


def boundary_near(walk, target):
    """Depth (1-indexed) of first perm of the block containing/after target."""
    best = None
    prev_p = walk[0][1]
    for d in range(2, len(walk) + 1):
        if walk[d - 1][1] - walk[d - 2][1] >= 2 and d >= target:
            return d
    return None


random.seed(28)
files = sorted(ARCHIVE.glob("*.txt"))
sample = random.sample(files, SAMPLE)
improved, optimal, skipped = 0, 0, 0
t0 = time.time()
bcounts = []
for i, p in enumerate(sample):
    w = walk_of(p.name)
    d0 = boundary_near(w, TARGET)
    if d0 is None:
        skipped += 1
        continue
    _, blocks = blocks_of(w, d0)
    if len(blocks) > MAXB:
        skipped += 1
        continue
    n, d, B, actual, best = solve(p.name, d0)
    bcounts.append(B)
    if best < actual:
        improved += 1
        print(f"IMPROVEMENT {p.name} @ {d0}: {actual} -> {best}  *** 871 CANDIDATE ***")
    else:
        optimal += 1
    if (i + 1) % 50 == 0:
        print(f"  {i + 1}/{SAMPLE} elapsed {time.time() - t0:.0f}s", file=sys.stderr)

print(f"\nsweep: {optimal} block-order-optimal, {improved} improved, {skipped} skipped")
if bcounts:
    print(f"blocks: min {min(bcounts)} med {sorted(bcounts)[len(bcounts) // 2]} max {max(bcounts)}")
print(f"total {time.time() - t0:.0f}s")
