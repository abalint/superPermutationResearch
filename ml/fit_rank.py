#!/usr/bin/env python3
"""Pairwise linear ranker: expert states above background states at equal level.

Phase-3 item 3 (docs/ROADMAP.md). Instead of regressing cost_to_go, learn a
linear score s(x) = w.x that *ranks* expert-trajectory states (record 872
traces and their reverse-relabels) BELOW background states (eps-greedy
rollouts, beam trajectories) drawn at the same level — lower score = better,
matching the beam's ascending sort. Level = r (unvisited perm count), which
the JSONL gives directly and which determines the beam level at fixed n.

Loss is RankNet-style logistic on score differences: for a pair
(expert e, background o) at equal r, loss = softplus(s(e) - s(o));
full-batch gradient descent on standardized features, L2-regularized.

The export is the SAME v2 linear JSON contract fit_linear.py writes
(standardization folded into coef/bias; default target "absolute"), so the
Rust beam loads it unchanged: score = len + alpha * pred. A ranker's scale
is arbitrary, so alpha needs a wide sweep on the beam side. With
--residual the export carries target "residual" instead — training is
unchanged (the pairwise loss never sees the target), but the beam then
scores len + lb_arc + alpha * pred, keeping the admissible anchor that a
pure rank score lacks (s3 lesson 1: without it the n=5 gate fails at
every alpha).

Held-out pairs: trajectories are split by rollout id (every 5th held out,
common.split) independently on each side; reported pair accuracy =
fraction of held-out pairs with s(expert) < s(background).

Usage:
    python3 ml/fit_rank.py --expert data/expert872_v2.jsonl \
        --other data/roll_n6_e0.01_s500000_v2.jsonl [...] \
        [--pairs 200000] [--epochs 300] [--lr 0.5] [--l2 1e-4] \
        [--seed 0] [--export ml/models/rank_n6.json]
"""

import argparse
import json
import os

import numpy as np

import common


def sample_pairs(r_e, r_o, n_pairs, rng):
    """Index pairs (i into expert rows, j into background rows) with equal r.

    Levels are sampled uniformly from those present on BOTH sides, then a
    uniform row on each side within the level — so endgame levels are not
    swamped by the (much larger) background corpus.
    """
    by_r_e, by_r_o = {}, {}
    for arr, by in ((r_e, by_r_e), (r_o, by_r_o)):
        order = np.argsort(arr, kind="stable")
        vals, starts = np.unique(arr[order], return_index=True)
        for v, s, t in zip(vals, starts, list(starts[1:]) + [len(arr)]):
            by[int(v)] = order[s:t]
    levels = np.array(sorted(set(by_r_e) & set(by_r_o)))
    assert len(levels) > 0, "expert and background corpora share no r level"
    lv = rng.choice(levels, size=n_pairs)
    i = np.empty(n_pairs, dtype=np.int64)
    j = np.empty(n_pairs, dtype=np.int64)
    for v in np.unique(lv):
        m = lv == v
        i[m] = rng.choice(by_r_e[int(v)], size=int(m.sum()))
        j[m] = rng.choice(by_r_o[int(v)], size=int(m.sum()))
    return i, j


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--expert", nargs="+", required=True, help="expert JSONL")
    ap.add_argument("--other", nargs="+", required=True, help="background JSONL")
    ap.add_argument("--pairs", type=int, default=200_000)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--lr", type=float, default=0.5)
    ap.add_argument("--l2", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--export", metavar="PATH", help="write model JSON here")
    ap.add_argument(
        "--residual",
        action="store_true",
        help="export target: residual (beam adds the lb_arc anchor back; "
        "training is unchanged)",
    )
    args = ap.parse_args()

    Xe_raw, _, rid_e, n_e = common.load(args.expert)
    Xo_raw, _, rid_o, n_o = common.load(args.other)
    assert n_e == n_o, f"expert n={n_e} != background n={n_o}"
    Xe, Xo = common.features(Xe_raw), common.features(Xo_raw)
    r_e, r_o = Xe_raw[:, 0].astype(int), Xo_raw[:, 0].astype(int)

    # Standardize on the pooled corpus (guard all-constant columns).
    pool = np.vstack([Xe, Xo])
    mu, sd = pool.mean(axis=0), pool.std(axis=0)
    sd[sd == 0] = 1.0
    Ze, Zo = (Xe - mu) / sd, (Xo - mu) / sd

    rng = np.random.default_rng(args.seed)
    i, j = sample_pairs(r_e, r_o, args.pairs, rng)
    # Held-out split by trajectory on both sides; a pair is held out if
    # either side's trajectory is.
    tr_e, _ = common.split(rid_e)
    tr_o, _ = common.split(rid_o)
    train = tr_e[i] & tr_o[j]
    D = Ze[i] - Zo[j]  # want w.D < 0
    Dtr, Dte = D[train], D[~train]

    w = np.zeros(D.shape[1])
    for epoch in range(args.epochs):
        z = Dtr @ w
        g = Dtr.T @ (1.0 / (1.0 + np.exp(-z))) / len(Dtr) + args.l2 * w
        w -= args.lr * g
    acc_tr = float(np.mean(Dtr @ w < 0))
    acc_te = float(np.mean(Dte @ w < 0))
    print(
        f"n={int(n_e)}  expert_rows={len(Xe)}  background_rows={len(Xo)}  "
        f"pairs={args.pairs} (train {int(train.sum())} / held-out {int((~train).sum())})"
    )
    print(f"pair accuracy: train {acc_tr:.4f}   held-out {acc_te:.4f}")
    print("coefficients (standardized):")
    for name, c in zip(common.FEATURE_ORDER, w):
        print(f"  {name:24s} {c:+.4f}")

    if args.export:
        coef = w / sd
        bias = -float(np.sum(w * mu / sd))
        model = {
            "kind": "linear",
            "n": int(n_e),
            "feature_order": common.FEATURE_ORDER,
            "coef": [float(c) for c in coef],
            "bias": bias,
            "target": "residual" if args.residual else "absolute",
        }
        os.makedirs(os.path.dirname(args.export) or ".", exist_ok=True)
        with open(args.export, "w") as fh:
            json.dump(model, fh, indent=1)
            fh.write("\n")
        print(f"wrote {args.export}")


if __name__ == "__main__":
    main()
