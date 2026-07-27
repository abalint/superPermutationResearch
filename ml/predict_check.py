#!/usr/bin/env python3
"""Evaluate a model JSON (linear or mlp, the Rust beam contract) on JSONL data.

Prints RMSE/MAE/R² on the held-out split (every 5th rollout, same as
fit_linear.py) and on all rows — a quick check for bootstrap rounds.

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
    assert model["feature_order"] == common.FEATURE_ORDER, "feature_order mismatch"

    X_raw, y, rids, n = common.load(args.paths)
    if int(n) != model["n"]:
        print(f"warning: model n={model['n']} but data n={int(n)}")
    pred = predict(model, common.features8(X_raw))
    _, test = common.split(rids)

    print(f"model={args.model} ({model['kind']})  n={int(n)}  rows={len(y)}")
    common.report("held-out (every 5th)", pred[test], y[test])
    common.report("all rows", pred, y)


if __name__ == "__main__":
    main()
