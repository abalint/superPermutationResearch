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

Usage:
    python3 ml/fit_linear.py data/roll_n5_*.jsonl
"""

import json
import sys

import numpy as np

FIELDS = [
    "r",
    "cycles_remaining",
    "intact_cycles",
    "current_cycle_remaining",
    "arcs",
    "succ1_unvisited",
]


def load(paths):
    rows, rollout_ids = [], []
    rid = -1
    for path in paths:
        with open(path) as fh:
            for line in fh:
                f = json.loads(line)
                if f["step"] == 0:
                    rid += 1
                rows.append(
                    [f.get(k, 0) for k in FIELDS] + [f["cost_to_go"], f["n"]]
                )
                rollout_ids.append(rid)
    data = np.asarray(rows, dtype=np.float64)
    ns = set(data[:, -1].astype(int))
    assert len(ns) == 1, f"mix of n values {ns}; fit one n at a time"
    return data[:, :-1], np.asarray(rollout_ids), ns.pop()


def metrics(pred, y):
    err = pred - y
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return {
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(err))),
        "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
    }


def report(name, pred, y):
    m = metrics(pred, y)
    print(f"  {name:24s} rmse {m['rmse']:8.3f}   mae {m['mae']:8.3f}   R² {m['r2']:8.4f}")


def main(paths):
    data, rids, n = load(paths)
    X, y = data[:, : len(FIELDS)], data[:, len(FIELDS)]
    r, k, cur_rem = X[:, 0], X[:, 1], X[:, 3]
    arcs, succ1 = X[:, 4], X[:, 5]
    lb_cycle = r + k - (cur_rem > 0)
    lb_arc = np.where(r > 0, r + arcs - succ1, 0.0)
    if not np.any(arcs):
        print("note: no arc features in input (old-schema JSONL); lb_arc is meaningless")

    test = rids % 5 == 0
    train = ~test
    # Design matrix: raw features + both hand bounds + bias.
    D = np.column_stack([X, lb_cycle, lb_arc, np.ones(len(y))])
    coef, *_ = np.linalg.lstsq(D[train], y[train], rcond=None)

    print(
        f"n={int(n)}  rows={len(y)}  rollouts={rids.max() + 1}  "
        f"train_rows={int(train.sum())}  test_rows={int(test.sum())}"
    )
    print("held-out (every 5th rollout):")
    report("lb_cycle (admissible)", lb_cycle[test], y[test])
    report("lb_arc (admissible)", lb_arc[test], y[test])
    report("linear regressor", D[test] @ coef, y[test])
    print("train:")
    report("linear regressor", D[train] @ coef, y[train])
    names = FIELDS + ["lb_cycle", "lb_arc", "bias"]
    print("coefficients:")
    for name, c in zip(names, coef):
        print(f"  {name:24s} {c:+.4f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
