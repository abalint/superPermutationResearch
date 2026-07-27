#!/usr/bin/env python3
"""Train a small numpy MLP on cost_to_go and export it in the Rust JSON contract.

Architecture: 11 standardized inputs (the v2 feature contract; the three
deficit-distribution columns default to 0 for old-schema JSONL) -> hidden
relu layers -> 1 linear output. Previously exported 8-input models keep
loading in Rust unchanged (append-only, length-dispatched contract).
Trained with Adam on minibatches, early stopping on the held-out split
(every 5th rollout, same as fit_linear.py). The label is standardized during
training and the scale is folded back into the last layer on export, so the
exported net maps standardized features directly to raw cost_to_go:

    {"kind":"mlp","n":..,"feature_order":[11],"x_mean":[11],"x_std":[11],
     "layers":[{"w":[[out x in]],"b":[out],"act":"relu"}, ..., act "identity"]}

After writing, inference is re-implemented from the JSON file alone and
checked against the trained net (max abs diff < 1e-9 on 1000 samples).

With --residual the training label is cost_to_go - lb_arc and the exported
JSON carries "target": "residual" (the Rust scorer adds lb_arc back).
Reported metrics are always in absolute cost_to_go space.

Usage:
    python3 ml/train_mlp.py data/roll_n6_*.jsonl [--residual] --export ml/models/mlp_n6.json
"""

import argparse
import json
import os

import numpy as np

import common


def init_params(sizes, rng):
    """He-initialised weights. sizes e.g. [8, 64, 64, 1]."""
    Ws = [
        rng.normal(0.0, np.sqrt(2.0 / fin), size=(fout, fin))
        for fin, fout in zip(sizes[:-1], sizes[1:])
    ]
    bs = [np.zeros(fout) for fout in sizes[1:]]
    return Ws, bs


def forward(Ws, bs, X):
    a = X
    for i, (W, b) in enumerate(zip(Ws, bs)):
        a = a @ W.T + b
        if i < len(Ws) - 1:
            a = np.maximum(a, 0.0)
    return a[:, 0]


def grad_step(Ws, bs, X, y):
    """MSE loss; returns (loss, dWs, dbs)."""
    acts = [X]
    a = X
    for i, (W, b) in enumerate(zip(Ws, bs)):
        a = a @ W.T + b
        if i < len(Ws) - 1:
            a = np.maximum(a, 0.0)
        acts.append(a)
    err = acts[-1][:, 0] - y
    loss = float(np.mean(err**2))
    delta = (2.0 / len(y)) * err[:, None]
    dWs, dbs = [None] * len(Ws), [None] * len(bs)
    for i in reversed(range(len(Ws))):
        dWs[i] = delta.T @ acts[i]
        dbs[i] = delta.sum(axis=0)
        if i > 0:
            delta = (delta @ Ws[i]) * (acts[i] > 0)
    return loss, dWs, dbs


def train(Xtr, ytr, Xte, yte, hidden, seed, lr=1e-3, batch=4096, max_epochs=100,
          patience=10):
    rng = np.random.default_rng(seed)
    Ws, bs = init_params([Xtr.shape[1]] + hidden + [1], rng)
    params = Ws + bs
    m = [np.zeros_like(p) for p in params]
    v = [np.zeros_like(p) for p in params]
    b1, b2, eps, t = 0.9, 0.999, 1e-8, 0
    best_rmse, best, stale = np.inf, None, 0
    for epoch in range(max_epochs):
        order = rng.permutation(len(ytr))
        for lo in range(0, len(ytr), batch):
            idx = order[lo : lo + batch]
            _, dWs, dbs = grad_step(Ws, bs, Xtr[idx], ytr[idx])
            t += 1
            for p, g, mi, vi in zip(params, dWs + dbs, m, v):
                mi *= b1
                mi += (1 - b1) * g
                vi *= b2
                vi += (1 - b2) * g * g
                p -= lr * (mi / (1 - b1**t)) / (np.sqrt(vi / (1 - b2**t)) + eps)
        rmse = float(np.sqrt(np.mean((forward(Ws, bs, Xte) - yte) ** 2)))
        if rmse < best_rmse - 1e-6:
            best_rmse, stale = rmse, 0
            best = ([W.copy() for W in Ws], [b.copy() for b in bs])
        else:
            stale += 1
            if stale >= patience:
                break
        if epoch % 10 == 0:
            print(f"  epoch {epoch:3d}  held-out rmse (std units) {rmse:.5f}")
    print(f"  stopped after epoch {epoch}, best held-out rmse (std units) {best_rmse:.5f}")
    return best


def export(path, n, Ws, bs, x_mean, x_std, target):
    layers = []
    for i, (W, b) in enumerate(zip(Ws, bs)):
        layers.append(
            {
                "w": [[float(x) for x in row] for row in W],
                "b": [float(x) for x in b],
                "act": "relu" if i < len(Ws) - 1 else "identity",
            }
        )
    model = {
        "kind": "mlp",
        "n": int(n),
        "feature_order": common.FEATURE_ORDER,
        "x_mean": [float(x) for x in x_mean],
        "x_std": [float(x) for x in x_std],
        "layers": layers,
        "target": target,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(model, fh)
        fh.write("\n")


def infer_from_json(path, X_raw8):
    """Inference re-implemented from the JSON file alone (contract check)."""
    with open(path) as fh:
        model = json.load(fh)
    z = (X_raw8 - np.array(model["x_mean"])) / np.array(model["x_std"])
    for layer in model["layers"]:
        z = z @ np.array(layer["w"]).T + np.array(layer["b"])
        if layer["act"] == "relu":
            z = np.maximum(z, 0.0)
    return z[:, 0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--export", metavar="PATH", required=True)
    ap.add_argument("--hidden", type=int, nargs="+", default=[64, 64])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-epochs", type=int, default=100)
    ap.add_argument(
        "--residual",
        action="store_true",
        help="train on cost_to_go - lb_arc; export carries target: residual",
    )
    args = ap.parse_args()

    X_raw, y, rids, n = common.load(args.paths)
    X8 = common.features(X_raw)
    train_m, test_m = common.split(rids)

    lb_arc = X8[:, 7]
    y_fit = y - lb_arc if args.residual else y
    target = "residual" if args.residual else "absolute"

    x_mean = X8[train_m].mean(axis=0)
    x_std = X8[train_m].std(axis=0)
    x_std[x_std == 0] = 1.0
    y_mean, y_std = y_fit[train_m].mean(), y_fit[train_m].std()
    Z = (X8 - x_mean) / x_std
    yz = (y_fit - y_mean) / y_std

    print(
        f"n={int(n)}  rows={len(y)}  hidden={args.hidden}  seed={args.seed}  "
        f"target={target}"
    )
    Ws, bs = train(Z[train_m], yz[train_m], Z[test_m], yz[test_m], args.hidden,
                   args.seed, max_epochs=args.max_epochs)

    # Fold the label scale into the last layer: net now outputs raw cost_to_go.
    Ws[-1] = Ws[-1] * y_std
    bs[-1] = bs[-1] * y_std + y_mean

    pred = forward(Ws, bs, Z)
    # Report in absolute cost_to_go space regardless of the label.
    pred_abs = pred + lb_arc if args.residual else pred
    print("held-out (every 5th rollout):")
    common.report("mlp", pred_abs[test_m], y[test_m])
    print("train:")
    common.report("mlp", pred_abs[train_m], y[train_m])

    export(args.export, n, Ws, bs, x_mean, x_std, target)

    rng = np.random.default_rng(123)
    idx = rng.choice(len(y), size=1000, replace=False)
    diff = float(np.max(np.abs(infer_from_json(args.export, X8[idx]) - pred[idx])))
    assert diff < 1e-9, f"JSON round-trip mismatch: max abs diff {diff}"
    print(f"wrote {args.export}  (JSON round-trip max abs diff {diff:.3g} on 1000 samples)")


if __name__ == "__main__":
    main()
