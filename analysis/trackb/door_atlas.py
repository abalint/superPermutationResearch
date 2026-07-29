#!/usr/bin/env python3
"""T1 (TRACKB-DESIGN par.2): reduce and verify the door atlas.

Input: the raw TSV from `cargo run --release -- atlas -n 6` (one row per
weight->=3 edge: door AND intra-orbit rotation; 720 x 150 rows).

Verifications (all must hold, exit non-zero otherwise):
  1. Row count and per-perm weight histogram (w3: 6, w4: 24, w5: 120).
  2. Relabeling-orbit closure: the 150 edges out of the identity perm,
     relabeled by sigma_p : identity -> p, reproduce the full table for
     every p (edge set, weights, and interior-perm windows all commute
     with relabeling). The canonical atlas is therefore 150 rows.
  3. Intra-orbit edges are exactly the rotations rot-3/4/5 (one per weight
     per perm), confirming the T0 move inventory (i2 lives at w2, and
     intra w6 does not exist).

Output: door_atlas_canonical.tsv -- the 150 canonical edges (source =
identity 123456) with weight, target word, same-cycle flag, target-cycle
necklace, entry offset (w1-steps from the door's landing perm back to the
cycle representative under the canonical labeling), and the interior
permutation windows (as words) that the emergent-edge/canonicalization
filter needs: a door is legal in canonical reading iff every interior
perm is already visited.

Summary printed: per-weight door counts, cross- vs same-cycle, distinct
target cycles, and the interior-perm histogram (the fraction of doors
that are UNCONDITIONALLY usable, i.e. zero interior perms).
"""

import sys
from collections import Counter, defaultdict
from itertools import permutations


def rank(p):
    """Lehmer rank of a permutation word (tuple of 1..n)."""
    n = len(p)
    r = 0
    for i in range(n):
        smaller = sum(1 for j in range(i + 1, n) if p[j] < p[i])
        f = 1
        for k in range(2, n - i):
            f *= k
        r += smaller * f
    return r


def necklace(p):
    return min(tuple(p[i:] + p[:i]) for i in range(len(p)))


def main(argv):
    if len(argv) != 2:
        print("usage: door_atlas.py <raw_atlas.tsv>")
        return 2
    rows = []
    with open(argv[1]) as f:
        header = f.readline()
        assert header.startswith("from_rank\t")
        for ln in f:
            fr, w, to, fc, fo, tc, to_off, interior = ln.rstrip("\n").split("\t")
            rows.append(
                (
                    int(fr),
                    int(w),
                    int(to),
                    int(fc),
                    int(fo),
                    int(tc),
                    int(to_off),
                    tuple(int(x) for x in interior.split(";")) if interior else (),
                )
            )

    n = 6
    perms = list(permutations(range(1, n + 1)))
    perms.sort()  # lex order == Lehmer rank order
    assert all(rank(p) == i for i, p in enumerate(perms[:50]))

    # 1. counts
    assert len(rows) == 720 * 150, len(rows)
    per_perm_w = defaultdict(Counter)
    edge = {}
    for fr, w, to, *_rest, interior in [
        (r[0], r[1], r[2], r[3], r[7]) for r in rows
    ]:
        per_perm_w[fr][w] += 1
        edge[(fr, to)] = (w, interior)
    assert all(c == {3: 6, 4: 24, 5: 120} for c in per_perm_w.values())

    # 2. relabeling-orbit closure
    identity = perms[0]
    canon = [r for r in rows if r[0] == 0]
    assert len(canon) == 150
    for p in perms:
        sigma = {identity[i]: p[i] for i in range(n)}  # identity -> p
        for _, w, to, _, _, _, _, interior in canon:
            q = perms[to]
            q_img = tuple(sigma[v] for v in q)
            key = (rank(p), rank(q_img))
            assert key in edge, (p, q_img)
            w2, interior2 = edge[key]
            assert w2 == w
            interior_img = tuple(
                sorted(rank(tuple(sigma[v] for v in perms[ir])) for ir in interior)
            )
            assert interior_img == tuple(sorted(interior2)), (p, q, interior)

    # 3. intra-orbit edges are exactly rot-3/4/5
    for fr, w, to, fc, _, tc, _, _ in canon:
        p = perms[fr]
        if fc == tc:
            assert perms[to] == p[w:] + p[:w], (p, w, perms[to])
    intra = [r for r in canon if r[3] == r[5]]
    assert sorted(r[1] for r in intra) == [3, 4, 5]

    # canonical output + summary
    outpath = "analysis/trackb/door_atlas_canonical.tsv"
    with open(outpath, "w") as f:
        f.write(
            "weight\ttarget_word\tsame_cycle\ttarget_necklace\tentry_offset\t"
            "n_interior_perms\tinterior_words\n"
        )
        for fr, w, to, fc, fo, tc, to_off, interior in sorted(
            canon, key=lambda r: (r[1], r[2])
        ):
            q = perms[to]
            f.write(
                "{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
                    w,
                    "".join(map(str, q)),
                    int(fc == tc),
                    "".join(map(str, necklace(q))),
                    to_off,
                    len(interior),
                    ";".join("".join(map(str, perms[ir])) for ir in interior),
                )
            )

    print(f"verified: 720x150 rows are the relabeling orbit of {len(canon)} canonical edges")
    for w in (3, 4, 5):
        sub = [r for r in canon if r[1] == w]
        cross = [r for r in sub if r[3] != r[5]]
        tgt_cycles = len({r[5] for r in cross})
        ih = Counter(len(r[7]) for r in sub)
        free = sum(1 for r in sub if not r[7])
        print(
            f"w{w}: {len(sub)} edges ({len(cross)} cross-cycle doors to "
            f"{tgt_cycles} distinct cycles, {len(sub) - len(cross)} intra); "
            f"interior-perm histogram {dict(sorted(ih.items()))}; "
            f"unconditionally-usable doors: {free}/{len(sub)}"
        )
    print(f"canonical atlas written: {outpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
