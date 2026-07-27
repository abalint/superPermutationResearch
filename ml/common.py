"""Shared loading, splitting, and metrics for the ml/ scripts.

Schema: docs/ARCHITECTURE.md, "Rollout JSONL schema". One JSON object per
line; step == 0 starts a new rollout. The split is by *rollout* (every 5th
held out), not by row — rows within a rollout share a label scale.

The 8-feature contract (order shared with the Rust beam):
    RAW_FIELDS + [lb_cycle, lb_arc]
    lb_cycle = r + cycles_remaining - [current_cycle_remaining > 0]
    lb_arc   = (r > 0) ? r + arcs - succ1_unvisited : 0
"""

import json

import numpy as np

RAW_FIELDS = [
    "r",
    "cycles_remaining",
    "intact_cycles",
    "current_cycle_remaining",
    "arcs",
    "succ1_unvisited",
]
FEATURE_ORDER = RAW_FIELDS + ["lb_cycle", "lb_arc"]


def load(paths):
    """Read JSONL files -> (X_raw [rows x 6], y cost_to_go, rollout_ids, n)."""
    rows, rollout_ids = [], []
    rid = -1
    for path in paths:
        with open(path) as fh:
            for line in fh:
                f = json.loads(line)
                if f["step"] == 0:
                    rid += 1
                rows.append(
                    [f.get(k, 0) for k in RAW_FIELDS] + [f["cost_to_go"], f["n"]]
                )
                rollout_ids.append(rid)
    data = np.asarray(rows, dtype=np.float64)
    ns = set(data[:, -1].astype(int))
    assert len(ns) == 1, f"mix of n values {ns}; fit one n at a time"
    nraw = len(RAW_FIELDS)
    return data[:, :nraw], data[:, nraw], np.asarray(rollout_ids), ns.pop()


def features8(X_raw):
    """Raw 6-column matrix -> the 8-feature contract (appends lb_cycle, lb_arc)."""
    r, k, cur_rem = X_raw[:, 0], X_raw[:, 1], X_raw[:, 3]
    arcs, succ1 = X_raw[:, 4], X_raw[:, 5]
    lb_cycle = r + k - (cur_rem > 0)
    lb_arc = np.where(r > 0, r + arcs - succ1, 0.0)
    return np.column_stack([X_raw, lb_cycle, lb_arc])


def split(rollout_ids):
    """Held-out = every 5th rollout. Returns (train_mask, test_mask)."""
    test = rollout_ids % 5 == 0
    return ~test, test


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
    print(
        f"  {name:24s} rmse {m['rmse']:8.3f}   mae {m['mae']:8.3f}   R² {m['r2']:8.4f}"
    )
    return m
