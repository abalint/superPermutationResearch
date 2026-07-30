#!/usr/bin/env python3
"""Feasibility prototype: tail block-ATSP at a surgery anchor.

Fix a walk's tail block decomposition (blocks = maximal w1-runs, cut at every
w>=2 move); exactly optimize the block ORDER. Junction cost = overlap weight
between exit perm of one block and entry perm of the next. Start = the anchor
state's cur (end of shared prefix). Path, not cycle (free end).

Exact solve: Held-Karp if blocks <= 22 else branch-and-bound with assignment
LB... for the prototype: B&B with min-in-edge bound, plus report assignment
relaxation LB and the walk's actual tail cost.
"""
import itertools
import sys
from functools import lru_cache
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


def w(p, q):
    """Overlap weight p->q for perm strings."""
    for o in range(N - 1, 0, -1):
        if p[N - o :] == q[:o]:
            # must actually be a valid successor: q = suffix + new chars
            return N - o
    return N


def blocks_of(walk, d0):
    """Cut tail (from depth d0, 1-indexed perm visits) into w1-run blocks.
    Returns list of (entry_perm, exit_perm, nperms), plus anchor cur perm."""
    tail = walk[d0 - 1 :]
    blocks = []
    ent = tail[0][0]
    prev_r, prev_p = tail[0]
    cnt = 1
    for r, plen in tail[1:]:
        if plen - prev_p == 1:
            cnt += 1
        else:
            blocks.append((PERM[ent], PERM[prev_r], cnt))
            ent, cnt = r, 1
        prev_r, prev_p = r, plen
    blocks.append((PERM[ent], PERM[prev_r], cnt))
    anchor_cur = PERM[walk[d0 - 2][0]] if d0 >= 2 else None
    return anchor_cur, blocks


def solve(name, d0):
    walk = walk_of(name)
    anchor, blocks = blocks_of(walk, d0)
    B = len(blocks)
    intra = sum(b[2] - 1 for b in blocks)  # w1 moves inside blocks
    # cost matrix: node 0 = anchor (exit=anchor cur), nodes 1..B = blocks
    exits = [anchor] + [b[1] for b in blocks]
    entries = [None] + [b[0] for b in blocks]
    C = [[0] * (B + 1) for _ in range(B + 1)]
    for i in range(B + 1):
        for j in range(1, B + 1):
            if i != j:
                C[i][j] = w(exits[i], entries[j])
    actual = sum(C[i][i + 1] for i in range(B)) + intra  # walk's own order = 1..B
    # exact Held-Karp over blocks (B <= ~22) or B&B
    FULL = (1 << B) - 1
    if B <= 22:
        import heapq

        # DP over subsets
        INF = float("inf")
        dp = [[INF] * B for _ in range(1 << B)]
        for j in range(B):
            dp[1 << j][j] = C[0][j + 1]
        for mask in range(1 << B):
            row = dp[mask]
            for j in range(B):
                cj = row[j]
                if cj == INF or not (mask >> j) & 1:
                    continue
                for k in range(B):
                    if (mask >> k) & 1:
                        continue
                    nm = mask | (1 << k)
                    nc = cj + C[j + 1][k + 1]
                    if nc < dp[nm][k]:
                        dp[nm][k] = nc
        best = min(dp[FULL])
    else:
        # branch & bound, bound = sum of min in-costs of unvisited
        min_in = [min(C[i][j] for i in range(B + 1) if i != j) for j in range(1, B + 1)]
        best = actual - intra  # incumbent = the walk's own junction cost

        import sys as _s

        _s.setrecursionlimit(10000)

        order = sorted(range(B), key=lambda j: -blocks[j][2])

        def bb(at, mask, cost):
            nonlocal best
            if mask == FULL:
                if cost < best:
                    best = cost
                return
            lb = cost + sum(min_in[j] for j in range(B) if not (mask >> j) & 1)
            if lb >= best:
                return
            for j in order:
                if not (mask >> j) & 1:
                    bb(j + 1, mask | (1 << j), cost + C[at][j + 1])

        bb(0, 0, 0)
        best += intra
        print(f"  (B&B) ", end="")
        return name, d0, B, actual, best

    best += intra
    return name, d0, B, actual, best


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "872.up-b020caf20414.txt"
    d0 = int(sys.argv[2]) if len(sys.argv) > 2 else 585
    n, d, B, actual, best = solve(name, d0)
    verdict = "IMPROVEMENT!" if best < actual else "block-order-optimal"
    print(f"{n} tail@{d}: {B} blocks; walk tail cost {actual}, ATSP optimum {best} -> {verdict}")
