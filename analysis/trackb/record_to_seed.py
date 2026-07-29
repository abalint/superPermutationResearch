#!/usr/bin/env python3
"""Convert a superperm string to a first-visit rank path (relabeled so the
first permutation is the identity), emitting seed lines for beam --seed-file.

Usage: record_to_seed.py <file> <n> <prefix_len_1> [prefix_len_2 ...]
Prefix lengths are in visited-perm counts; 0 means the full path.
"""
import sys
from itertools import permutations


def lehmer_rank(p):
    n = len(p)
    rank = 0
    for i in range(n):
        smaller = sum(1 for j in range(i + 1, n) if p[j] < p[i])
        f = 1
        for k in range(2, n - i):
            f *= k
        rank += smaller * f
    return rank


def main():
    path_file, n = sys.argv[1], int(sys.argv[2])
    prefixes = [int(x) for x in sys.argv[3:]]
    s = open(path_file).read().strip()
    first = s[:n]
    # relabel so the first window is 12..n
    relab = {c: str(i + 1) for i, c in enumerate(first)}
    s = "".join(relab[c] for c in s)
    assert s[:n] == "".join(str(i + 1) for i in range(n))

    symbols = set(str(i + 1) for i in range(n))
    seen = set()
    ranks = []
    for i in range(len(s) - n + 1):
        w = s[i : i + n]
        if set(w) == symbols and w not in seen:
            seen.add(w)
            ranks.append(lehmer_rank([int(c) for c in w]))
    fact = 1
    for k in range(2, n + 1):
        fact *= k
    assert len(ranks) == fact, f"visited {len(ranks)} != {fact}"
    assert ranks[0] == 0
    for p in prefixes:
        cut = ranks if p == 0 else ranks[:p]
        print(",".join(str(r) for r in cut))


if __name__ == "__main__":
    main()
