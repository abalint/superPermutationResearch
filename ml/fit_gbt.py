#!/usr/bin/env python3
"""Gradient-boosted-tree baseline: how much headroom is there over linear?

Diagnostic only — trees are NOT in the Rust model contract and cannot be
exported to the beam. Uses sklearn's HistGradientBoostingRegressor on the
same 8-feature contract and rollout-level split as fit_linear.py.

Usage:
    python3 ml/fit_gbt.py data/roll_n5_*.jsonl
"""

import argparse

from sklearn.ensemble import HistGradientBoostingRegressor

import common


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--max-iter", type=int, default=500)
    args = ap.parse_args()

    X_raw, y, rids, n = common.load(args.paths)
    X8 = common.features8(X_raw)
    train, test = common.split(rids)

    gbt = HistGradientBoostingRegressor(
        max_iter=args.max_iter, random_state=0, early_stopping=False
    )
    gbt.fit(X8[train], y[train])

    print(f"n={int(n)}  rows={len(y)}  max_iter={args.max_iter}")
    print("held-out (every 5th rollout):")
    common.report("gbt", gbt.predict(X8[test]), y[test])
    print("train:")
    common.report("gbt", gbt.predict(X8[train]), y[train])


if __name__ == "__main__":
    main()
