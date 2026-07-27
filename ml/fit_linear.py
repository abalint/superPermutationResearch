#!/usr/bin/env python3
"""Linear cost-to-go baseline vs. the hand bounds.

Reads rollout/trajectory JSONL (see docs/ARCHITECTURE.md for the schema),
fits an ordinary-least-squares regressor of cost_to_go on the state
features, and compares its held-out error against the two admissible hand
bounds used as point predictors:

    lb_cycle = r + k − [current_cycle_remaining > 0]
    lb_arc   = r + arcs − [succ1_unvisited]

The split is by *rollout* (every 5th rollout is held out), not by row —
rows within a rollout share a label scale, so a row-level split leaks.

The design matrix is [8-feature contract, ones]; with --export the fitted
model is written in the JSON contract the Rust beam loads (the ones-column
coefficient becomes "bias", so "coef" applies to the raw 8 features).

With --residual the training label is cost_to_go - lb_arc (the correction
above the admissible anchor) and the exported JSON carries
"target": "residual"; the Rust scorer adds lb_arc back. Reported regressor
metrics are always in absolute cost_to_go space, so runs stay comparable.

Usage:
    python3 ml/fit_linear.py data/roll_n5_*.jsonl [--residual] [--export ml/models/linear_n5.json]
"""

import argparse
import json
import os

import numpy as np

import common


def fit(X8, y, train):
    """OLS on [8 features, ones]. Returns (coef[8], bias)."""
    D = np.column_stack([X8, np.ones(len(y))])
    beta, *_ = np.linalg.lstsq(D[train], y[train], rcond=None)
    return beta[:-1], beta[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+", help="rollout/trajectory JSONL files")
    ap.add_argument("--export", metavar="PATH", help="write fitted model JSON here")
    ap.add_argument(
        "--residual",
        action="store_true",
        help="train on cost_to_go - lb_arc; export carries target: residual",
    )
    args = ap.parse_args()

    X_raw, y, rids, n = common.load(args.paths)
    X8 = common.features8(X_raw)
    lb_cycle, lb_arc = X8[:, 6], X8[:, 7]
    if not np.any(X_raw[:, 4]):
        print("note: no arc features in input (old-schema JSONL); lb_arc is meaningless")

    train, test = common.split(rids)
    y_fit = y - lb_arc if args.residual else y
    coef, bias = fit(X8, y_fit, train)
    # Report in absolute cost_to_go space regardless of the label.
    pred = X8 @ coef + bias + (lb_arc if args.residual else 0.0)

    target = "residual" if args.residual else "absolute"
    print(
        f"n={int(n)}  rows={len(y)}  rollouts={rids.max() + 1}  "
        f"train_rows={int(train.sum())}  test_rows={int(test.sum())}  target={target}"
    )
    print("held-out (every 5th rollout):")
    common.report("lb_cycle (admissible)", lb_cycle[test], y[test])
    common.report("lb_arc (admissible)", lb_arc[test], y[test])
    common.report("linear regressor", pred[test], y[test])
    print("train:")
    common.report("linear regressor", pred[train], y[train])
    print("coefficients:")
    for name, c in zip(common.FEATURE_ORDER + ["bias"], list(coef) + [bias]):
        print(f"  {name:24s} {c:+.4f}")

    if args.export:
        model = {
            "kind": "linear",
            "n": int(n),
            "feature_order": common.FEATURE_ORDER,
            "coef": [float(c) for c in coef],
            "bias": float(bias),
            "target": target,
        }
        os.makedirs(os.path.dirname(args.export) or ".", exist_ok=True)
        with open(args.export, "w") as fh:
            json.dump(model, fh, indent=1)
            fh.write("\n")
        print(f"wrote {args.export}")


if __name__ == "__main__":
    main()
