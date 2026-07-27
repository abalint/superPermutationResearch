#!/usr/bin/env python3
"""Evaluate a model JSON (linear or mlp, the Rust beam contract) on JSONL data.

Prints RMSE/MAE/R² on the held-out split (every 5th rollout, same as
fit_linear.py) and on all rows — a quick check for bootstrap rounds.
Residual-target models ("target": "residual") get lb_arc added back so the
comparison is always against raw cost_to_go.

The feature contract is append-only and length-dispatched: models
declaring the old 8-feature order are fed exactly the first 8 columns of
the 11-column matrix (bit-identical to their pre-phase-3 inputs); v2
models consume all 11 (deficit-distribution columns default to 0 for
old-schema JSONL).

Usage:
    python3 ml/predict_check.py ml/models/mlp_n6.json data/roll_n6_*.jsonl
"""

import argparse
import json

import numpy as np

import common


def predict(model, X8):
    if model["kind"] == "linear":
        return X8 @ np.array(model["coef"]) + model["bias"]
    if model["kind"] == "mlp":
        z = (X8 - np.array(model["x_mean"])) / np.array(model["x_std"])
        for layer in model["layers"]:
            z = z @ np.array(layer["w"]).T + np.array(layer["b"])
            if layer["act"] == "relu":
                z = np.maximum(z, 0.0)
        return z[:, 0]
    raise ValueError(f"unknown model kind {model['kind']!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model", help="model JSON path")
    ap.add_argument("paths", nargs="+", help="rollout/trajectory JSONL files")
    args = ap.parse_args()

    with open(args.model) as fh:
        model = json.load(fh)
    fo = model["feature_order"]
    assert fo in (common.FEATURE_ORDER, common.FEATURE_ORDER_V1), (
        "feature_order mismatch: model declares neither the v1 (8) nor the "
        "v2 (11) contract"
    )

    X_raw, y, rids, n = common.load(args.paths)
    if int(n) != model["n"]:
        print(f"warning: model n={model['n']} but data n={int(n)}")
    X = common.features(X_raw)
    # A v1 model consumes only the first 8 columns (bit-identical inputs
    # to the pre-phase-3 build).
    pred = predict(model, X[:, : len(fo)])
    if model.get("target") == "residual":
        pred = pred + X[:, 7]  # add the lb_arc anchor back
    _, test = common.split(rids)

    print(
        f"model={args.model} ({model['kind']})  n={int(n)}  rows={len(y)}  "
        f"target={model.get('target', 'absolute')}"
    )
    common.report("held-out (every 5th)", pred[test], y[test])
    common.report("all rows", pred, y)


if __name__ == "__main__":
    main()
