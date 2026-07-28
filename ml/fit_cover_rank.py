#!/usr/bin/env python3
"""Track C trainer: pairwise linear ranker over DLX candidate rows.

docs/TRACKC-DESIGN.md §2 (feature vector + weights file), §3 (corpus format),
§4 (holdout design), §6 (this spec). Architecture mirrors ml/fit_rank.py (the
s8 anchored ranker): RankNet-style logistic loss on score differences,
full-batch gradient descent on standardized features, L2, standardization
folded into the exported weights so the C engine applies a raw dot + bias.

Corpus (JSONL, one line per DLX decision node):
    {"inst": cover-tag, "n": 6|7, "col": id, "pos": row_id,
     "neg": [row_ids], "feats": {row_id: [8 floats]}}
Pairs are (pos, neg) within a node; siblings share the node's state so all
node-constant terms cancel — exactly what the pairwise loss is for.

Held-out = whole covers (certs), never sampled pairs: 1-in-`--holdout-every`
covers per source file, chosen deterministically in sorted-tag order. Metric =
pair accuracy (fraction of held-out pairs with s(pos) > s(neg), strict; ties
count as misses, matching the engine's descending-score / row-id tie break
which cannot see any signal in a tie).

Usage:
    python3 ml/fit_cover_rank.py --train data/trackc/corpus_n6.jsonl \
        data/trackc/corpus_5906.jsonl --name modelA [--l2 1e-3]
    # --l2 omitted => sweep 1e-4..1e-1 and pick the best held-out pair accuracy
    # --eval <jsonl>+ => extra pure-transfer evaluation sets (no training)
"""

import argparse
import json
import os

import numpy as np

# docs/TRACKC-DESIGN.md §2, LOCKED order.
FEATURE_ORDER = [
    "min_child_sz_log",
    "mean_child_sz_log",
    "scarce_children",
    "parent_is_root",
    "parent_grounded",
    "parent_depth_log",
    "static_min_child_log",
    "grounds_pending",
]
NF = len(FEATURE_ORDER)

L2_GRID = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]


def load(paths):
    """Read decision nodes. Returns (nodes, pos_feats, neg_feats, inst, src).

    pos_feats/neg_feats are (n_pairs, NF) arrays aligned pair-wise; inst is the
    per-pair cover tag, src the per-pair source file. nodes is a list of
    (pos_row, [neg_rows], pos_vec, [neg_vecs], inst, src) for node-level metrics.
    """
    nodes = []
    P, N, inst, src = [], [], [], []
    for path in paths:
        tag = os.path.basename(path)
        with open(path) as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                feats = d["feats"]
                pv = np.asarray(feats[str(d["pos"])], dtype=float)
                assert pv.shape == (NF,), f"{path}:{lineno} bad feature width"
                nv = [np.asarray(feats[str(r)], dtype=float) for r in d["neg"]]
                key = f"{tag}::{d['inst']}"
                nodes.append((d["pos"], list(d["neg"]), pv, nv, key, tag))
                for v in nv:
                    P.append(pv)
                    N.append(v)
                    inst.append(key)
                    src.append(tag)
    if not P:
        raise SystemExit("no (pos, neg) pairs found")
    return (
        nodes,
        np.asarray(P),
        np.asarray(N),
        np.asarray(inst),
        np.asarray(src),
    )


def holdout_mask(inst, every):
    """True where the pair belongs to a held-out cover.

    Covers are grouped per source file so every source contributes held-out
    covers; within a file, sorted tag order, index % every == 0.
    """
    held = set()
    by_src = {}
    for key in sorted(set(inst.tolist())):
        by_src.setdefault(key.split("::", 1)[0], []).append(key)
    for keys in by_src.values():
        for i, k in enumerate(keys):
            if i % every == 0:
                held.add(k)
    return np.array([k in held for k in inst]), held


def fit(D, l2, iters, lr):
    """Minimize mean softplus(-D w) + l2/2 |w|^2 by GD with momentum."""
    w = np.zeros(D.shape[1])
    v = np.zeros_like(w)
    n = len(D)
    for _ in range(iters):
        z = D @ w
        # d/dz softplus(-z) = -sigmoid(-z)
        g = -(D.T @ _sigmoid(-z)) / n + l2 * w
        v = 0.9 * v - lr * g
        w = w + v
    return w, float(np.linalg.norm(g))


def _sigmoid(z):
    out = np.empty_like(z)
    m = z >= 0
    out[m] = 1.0 / (1.0 + np.exp(-z[m]))
    e = np.exp(z[~m])
    out[~m] = e / (1.0 + e)
    return out


def pair_acc(D, w, nondegen=None):
    """Strict pair accuracy. With `nondegen` (bool mask of pairs whose feature
    difference is not identically zero), restrict to the learnable pairs — a
    degenerate pair is invisible to any linear model, so it drags every score,
    including the random-weight control, toward (1 - degen_frac) / 2."""
    if nondegen is not None:
        D = D[nondegen]
    if len(D) == 0:
        return float("nan")
    return float(np.mean(D @ w > 0))


def top1_acc(nodes, w, bias, keep):
    """Fraction of nodes where the positive is tried first by the engine rule
    (descending score, ties by lowest row id)."""
    hit = tot = 0
    for pos, negs, pv, nvs, key, _src in nodes:
        if not keep(key):
            continue
        tot += 1
        ps = float(pv @ w) + bias
        best = (-ps, pos)
        for r, v in zip(negs, nvs):
            best = min(best, (-(float(v @ w) + bias), r))
        if best[1] == pos:
            hit += 1
    return (hit / tot) if tot else float("nan"), tot


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", nargs="+", required=True, help="corpus JSONL")
    ap.add_argument("--name", required=True, help="model name (e.g. modelA)")
    ap.add_argument("--eval", nargs="+", default=[], help="extra eval-only JSONL")
    ap.add_argument("--l2", type=float, default=None, help="fixed L2 (else sweep)")
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--lr", type=float, default=0.5)
    ap.add_argument("--holdout-every", type=int, default=10, help="1-in-K covers")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", default="ml/models")
    ap.add_argument("--no-export", action="store_true")
    args = ap.parse_args()

    nodes, P, N, inst, src = load(args.train)
    held, held_keys = holdout_mask(inst, args.holdout_every)
    train = ~held
    n_covers = len(set(inst.tolist()))

    # Standardize on training pairs only (all candidate vectors they touch).
    pool = np.vstack([P[train], N[train]])
    mu, sd = pool.mean(axis=0), pool.std(axis=0)
    sd[sd == 0] = 1.0
    D = (P - N) / sd  # mu cancels in the difference; want w.D > 0
    Dtr, Dte = D[train], D[held]

    nz = ~np.all(np.abs(D) < 1e-12, axis=1)
    degen = float(1.0 - nz.mean())
    nz_tr, nz_te = nz[train], nz[held]
    # Features with zero within-node variance carry no pairwise signal at all.
    flat = [
        FEATURE_ORDER[i]
        for i in range(NF)
        if not np.any(np.abs(D[:, i]) > 1e-12)
    ]

    # L2 selection on held-out pair accuracy.
    grid = [args.l2] if args.l2 is not None else L2_GRID
    results = []
    for l2 in grid:
        w, gn = fit(Dtr, l2, args.iters, args.lr)
        results.append((pair_acc(Dte, w), pair_acc(Dtr, w), l2, w, gn))
        print(
            f"  l2={l2:<8g} train {results[-1][1]:.4f}  held-out "
            f"{results[-1][0]:.4f}  |grad|={gn:.2e}"
        )
    acc_te, acc_tr, l2, w, gn = max(results, key=lambda t: (t[0], -t[2]))
    acc_te_nz = pair_acc(Dte, w, nz_te)
    acc_tr_nz = pair_acc(Dtr, w, nz_tr)

    # Random-weight harness check (should sit at ~50% among learnable pairs).
    rng = np.random.default_rng(args.seed)
    draws = [rng.normal(size=NF) for _ in range(20)]
    rnd = float(np.mean([pair_acc(Dte, r) for r in draws]))
    rnd_nz = float(np.mean([pair_acc(Dte, r, nz_te) for r in draws]))

    coef = w / sd
    bias = -float(np.sum(w * mu / sd))  # rank-neutral; keeps scores centered
    t1_tr, n_tr_nodes = top1_acc(nodes, coef, bias, lambda k: k not in held_keys)
    t1_te, n_te_nodes = top1_acc(nodes, coef, bias, lambda k: k in held_keys)

    print(f"\nmodel {args.name}")
    print(f"  files        : {', '.join(args.train)}")
    print(
        f"  covers       : {n_covers} ({len(held_keys)} held out, "
        f"1-in-{args.holdout_every})"
    )
    print(
        f"  pairs        : {len(D)} (train {int(train.sum())} / "
        f"held-out {int(held.sum())}); degenerate (zero feature diff) "
        f"{degen*100:.1f}%"
    )
    print(f"  chosen L2    : {l2:g}   |grad| {gn:.2e}   iters {args.iters}")
    print(f"  pair acc     : train {acc_tr:.4f}   held-out {acc_te:.4f}")
    print(f"  pair acc (learnable pairs only): train {acc_tr_nz:.4f}   "
          f"held-out {acc_te_nz:.4f}")
    print(f"  node top-1   : train {t1_tr:.4f} ({n_tr_nodes})   "
          f"held-out {t1_te:.4f} ({n_te_nodes})")
    print(f"  random-w ctrl: held-out pair acc {rnd:.4f} "
          f"(chance {(1-degen)/2:.4f}); learnable-only {rnd_nz:.4f} "
          f"(chance 0.5000)")
    if flat:
        print(f"  NOTE: zero within-node variance (no pairwise signal): "
              f"{', '.join(flat)}")
    print("  coefficients (standardized):")
    for name, c in zip(FEATURE_ORDER, w):
        print(f"    {name:22s} {c:+.4f}")

    evals = {}
    for path in args.eval:
        _en, EP, EN, _ei, _es = load([path])
        ED = (EP - EN) / sd
        enz = ~np.all(np.abs(ED) < 1e-12, axis=1)
        a, anz = pair_acc(ED, w), pair_acc(ED, w, enz)
        ernd = float(np.mean([pair_acc(ED, r, enz) for r in draws]))
        evals[os.path.basename(path)] = {
            "n_pairs": int(len(ED)),
            "pair_acc": a,
            "pair_acc_learnable": anz,
            "random_weight_pair_acc_learnable": ernd,
        }
        print(f"  eval {os.path.basename(path):22s} pairs {len(ED):6d}  "
              f"pair acc {a:.4f}  learnable-only {anz:.4f} "
              f"(random-w {ernd:.4f})")

    if args.no_export:
        return
    stem = args.name if args.name.startswith("trackc_") else f"trackc_{args.name}"
    os.makedirs(args.out_dir, exist_ok=True)
    txt = os.path.join(args.out_dir, stem + ".txt")
    with open(txt, "w") as fh:
        fh.write(f"trackc-w1 {NF}\n")
        fh.write(" ".join("%.12g" % v for v in list(coef) + [bias]) + "\n")
    js = os.path.join(args.out_dir, stem + ".json")
    with open(js, "w") as fh:
        json.dump(
            {
                "feature_order": FEATURE_ORDER,
                "coef": [float(c) for c in coef],
                "bias": bias,
                "train": {
                    "files": list(args.train),
                    "n_pairs": int(len(D)),
                    "n_train_pairs": int(train.sum()),
                    "n_held_out_pairs": int(held.sum()),
                    "n_covers": n_covers,
                    "n_held_out_covers": len(held_keys),
                    "l2": float(l2),
                    "held_out_pair_acc": acc_te,
                    "train_pair_acc": acc_tr,
                    "held_out_pair_acc_learnable": acc_te_nz,
                    "train_pair_acc_learnable": acc_tr_nz,
                    "random_weight_pair_acc_learnable": rnd_nz,
                    "zero_within_node_variance": flat,
                    "held_out_top1": t1_te,
                    "train_top1": t1_tr,
                    "random_weight_pair_acc": float(rnd),
                    "degenerate_pair_frac": degen,
                    "std_coef": [float(c) for c in w],
                    "eval": evals,
                },
            },
            fh,
            indent=1,
        )
        fh.write("\n")
    print(f"  wrote {txt}\n  wrote {js}")


if __name__ == "__main__":
    main()
