#!/usr/bin/env python3
"""Track C v2 trainer: linear effort regressor over DLX column choices.

docs/TRACKC2-DESIGN.md §2 (feature vector + weights file), §3 (corpus format),
§4 (this spec).  Conventions mirror ml/fit_cover_rank.py: numpy only, feature
standardization folded into the exported weights so the C engine applies a raw
dot + bias, held-out split by whole groups (there: covers; here: *instances*).

Corpus (JSONL, one line per logged node — see analysis/trackc/mine_subtrees.py):
    {"inst": tag, "depth": d, "cand": k, "col": id,
     "feats": [10 floats], "subtree": nodes, "outcome": "exhaust"}

Model: ridge on target `y = log1p(subtree)` (predicted log-effort; the engine
covers the candidate column with the MINIMUM score).  Samples are reweighted so
every depth decile carries equal total weight — near-root frames have subtrees
orders of magnitude larger than deep frames, and unweighted least squares would
spend all of its capacity on them (§4).

Held-out = whole instances (`--holdout chain5,chain26`), never sampled rows:
records from one search share a policy and a tree, so a random row split leaks.

Usage:
    python3 ml/fit_col_effort.py --train data/trackc/coleffort_s19.jsonl \\
        --name cw1 --holdout chain5,chain26 [--l2 1e-2]
    # --l2 omitted => sweep and pick the best held-out R^2
    python3 ml/fit_col_effort.py --self-test    # synthetic round-trip
"""

import argparse
import json
import math
import os

import numpy as np

# docs/TRACKC2-DESIGN.md §2, LOCKED order.
FEATURE_ORDER = [
    "sz_log",
    "sz_rel",
    "static_sz_log",
    "is_root",
    "grounded_c",
    "pending_log",
    "mean_child_load",
    "min_child_load",
    "frac_parents_grounded",
    "active_cols_log",
]
NF = len(FEATURE_ORDER)
TARGET = "log1p(subtree)"
WEIGHTS_MAGIC = "trackc-cw1"

L2_GRID = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]
NDEC = 10  # depth buckets (deciles)


# ------------------------------------------------------------------- data


def load(paths):
    """-> (X (n,NF), y (n,), depth (n,), inst (n,) of str)."""
    X, y, depth, inst = [], [], [], []
    for path in paths:
        with open(path) as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                f = d["feats"]
                if len(f) != NF:
                    raise SystemExit(f"{path}:{lineno} feature width {len(f)} != {NF}")
                X.append(f)
                y.append(math.log1p(d["subtree"]))
                depth.append(d["depth"])
                inst.append(d.get("inst", os.path.basename(path)))
    if not X:
        raise SystemExit("no records found")
    return (
        np.asarray(X, dtype=float),
        np.asarray(y, dtype=float),
        np.asarray(depth, dtype=float),
        np.asarray(inst),
    )


def depth_buckets(depth):
    """Decile bucket id per record (edges = deciles of the depth distribution).

    Heavy ties collapse buckets, so a corpus with fewer than 10 distinct depths
    simply gets fewer — still balanced — buckets.
    """
    edges = np.quantile(depth, np.linspace(0, 1, NDEC + 1)[1:-1])
    return np.searchsorted(edges, depth, side="left")


def depth_balanced_weights(depth):
    """Equal total weight per depth decile; mean weight 1 (§4)."""
    if len(depth) == 0:
        return np.zeros(0)
    b = depth_buckets(depth)
    w = np.zeros(len(depth))
    for k in np.unique(b):
        m = b == k
        w[m] = 1.0 / m.sum()
    w *= len(depth) / w.sum()  # normalize to mean weight 1
    return w


# ------------------------------------------------------------------ model


def fit_ridge(X, y, w, l2):
    """Weighted ridge on standardized X.  -> (beta (NF,), b0).

    The intercept is never penalized; standardized columns make the l2 grid
    comparable across features.
    """
    n, p = X.shape
    A = np.hstack([X, np.ones((n, 1))])
    W = w[:, None]
    G = A.T @ (W * A)
    reg = np.eye(p + 1) * l2
    reg[p, p] = 0.0
    sol = np.linalg.solve(G + reg, A.T @ (w * y))
    return sol[:p], float(sol[p])


def standardize(X, w):
    mu = np.average(X, axis=0, weights=w)
    var = np.average((X - mu) ** 2, axis=0, weights=w)
    sd = np.sqrt(var)
    sd[sd < 1e-12] = 1.0
    return mu, sd


def r2(y, pred):
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot <= 0:
        return float("nan")
    return 1.0 - float(np.sum((y - pred) ** 2)) / ss_tot


def rankdata(a):
    """Average-tie ranks (scipy.stats.rankdata equivalent; numpy only)."""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="stable")
    ranks = np.empty(len(a), dtype=float)
    s = a[order]
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i : j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return ranks


def spearman(a, b):
    """Spearman rho = Pearson correlation of average-tie ranks."""
    if len(a) < 2:
        return float("nan")
    ra, rb = rankdata(a), rankdata(b)
    ra -= ra.mean()
    rb -= rb.mean()
    den = math.sqrt(float(ra @ ra) * float(rb @ rb))
    if den <= 0:
        return float("nan")
    return float(ra @ rb) / den


# ------------------------------------------------------------------ train


def train(X, y, depth, inst, holdout, l2_grid, verbose=True):
    """-> report dict with folded coef/bias and held-out metrics."""
    held = np.isin(inst, list(holdout)) if holdout else np.zeros(len(y), bool)
    tr = ~held
    if not tr.any():
        raise SystemExit("holdout consumed every instance")

    wtr = depth_balanced_weights(depth[tr])
    mu, sd = standardize(X[tr], wtr)
    Ztr = (X[tr] - mu) / sd

    results = []
    for l2 in l2_grid:
        beta, b0 = fit_ridge(Ztr, y[tr], wtr, l2)
        coef = beta / sd
        bias = b0 - float(np.sum(beta * mu / sd))
        ptr = X[tr] @ coef + bias
        if held.any():
            pte = X[held] @ coef + bias
            score = r2(y[held], pte)
            rho = spearman(y[held], pte)
        else:
            score, rho = r2(y[tr], ptr), spearman(y[tr], ptr)
        results.append((score, l2, coef, bias, beta, b0, rho, r2(y[tr], ptr)))
        if verbose:
            print(f"  l2={l2:<8g} train R2 {results[-1][7]:+.4f}   "
                  f"{'held-out' if held.any() else 'in-sample'} R2 {score:+.4f}"
                  f"   rho {rho:+.4f}")
    score, l2, coef, bias, beta, b0, rho, r2tr = max(
        results, key=lambda t: (t[0] if np.isfinite(t[0]) else -1e18, -t[1])
    )

    rep = {
        "feature_order": FEATURE_ORDER,
        "coef": [float(c) for c in coef],
        "bias": float(bias),
        "target": TARGET,
        "holdout": sorted(holdout),
        "n_records": int(len(y)),
        "n_train": int(tr.sum()),
        "n_holdout": int(held.sum()),
        "instances": sorted(set(inst.tolist())),
        "l2": float(l2),
        "train_r2": float(r2tr),
        "held_out_r2": float(score) if held.any() else None,
        "held_out_spearman": float(rho) if held.any() else None,
        "in_sample_r2": float(r2tr),
        "in_sample_spearman": float(spearman(y[tr], X[tr] @ coef + bias)),
        "std_coef": [float(c) for c in beta],
        "std_bias": float(b0),
        "depth_buckets": int(len(np.unique(depth_buckets(depth[tr])))),
    }
    if held.any():
        rep["per_holdout_inst"] = {}
        for t in sorted(set(inst[held].tolist())):
            m = inst == t
            p = X[m] @ coef + bias
            rep["per_holdout_inst"][t] = {
                "n": int(m.sum()),
                "r2": float(r2(y[m], p)),
                "spearman": float(spearman(y[m], p)),
            }
    return rep


# ----------------------------------------------------------------- export


def export(rep, name, out_dir):
    stem = name if name.startswith("trackc_") else f"trackc_{name}"
    os.makedirs(out_dir, exist_ok=True)
    txt = os.path.join(out_dir, stem + ".txt")
    with open(txt, "w") as fh:
        fh.write(f"{WEIGHTS_MAGIC} {NF}\n")
        fh.write(" ".join("%.12g" % v for v in rep["coef"] + [rep["bias"]]) + "\n")
    js = os.path.join(out_dir, stem + ".json")
    with open(js, "w") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    return txt, js


def read_weights(path):
    """Read back a `trackc-cw1` weights file -> (coef, bias)."""
    with open(path) as fh:
        head = fh.readline().split()
        if head[0] != WEIGHTS_MAGIC or int(head[1]) != NF:
            raise SystemExit(f"{path}: not a {WEIGHTS_MAGIC} {NF} weights file")
        vals = [float(x) for x in fh.readline().split()]
    if len(vals) != NF + 1:
        raise SystemExit(f"{path}: expected {NF} coefs + bias, got {len(vals)}")
    return np.asarray(vals[:NF]), vals[NF]


# --------------------------------------------------------------- self-test


def self_test(out_dir):
    """Synthetic round-trip: a known linear target must be recovered, and the
    exported text weights must reproduce the in-memory predictions."""
    rng = np.random.default_rng(0)
    n = 4000
    insts = np.array(["synA", "synB", "synC", "synD"])[rng.integers(0, 4, n)]
    depth = rng.integers(0, 120, n).astype(float)
    X = rng.normal(size=(n, NF)) * rng.uniform(0.5, 4.0, NF) + rng.uniform(-2, 2, NF)
    w_true = rng.normal(size=NF)
    b_true = 1.75
    y = X @ w_true + b_true + rng.normal(scale=0.05, size=n)

    print("[self-test] synthetic corpus: "
          f"{n} records, {len(set(insts.tolist()))} instances")
    rep = train(X, y, depth, insts, {"synD"}, L2_GRID)
    ok = True

    r2_te = rep["held_out_r2"]
    rho_te = rep["held_out_spearman"]
    print(f"[self-test] held-out R2 {r2_te:+.6f}  Spearman rho {rho_te:+.6f}")
    if not (r2_te > 0.99):
        print("[self-test] FAIL held-out R2 <= 0.99")
        ok = False
    if not (rho_te > 0.99):
        print("[self-test] FAIL held-out Spearman <= 0.99")
        ok = False

    cerr = float(np.max(np.abs(np.asarray(rep["coef"]) - w_true)))
    berr = abs(rep["bias"] - b_true)
    print(f"[self-test] max |coef - true| {cerr:.4g}   |bias - true| {berr:.4g}")
    if cerr > 0.02 or berr > 0.02:
        print("[self-test] FAIL coefficients not recovered")
        ok = False

    txt, js = export(rep, "selftest_coleffort", out_dir)
    coef, bias = read_weights(txt)
    pred_mem = X @ np.asarray(rep["coef"]) + rep["bias"]
    pred_file = X @ coef + bias
    derr = float(np.max(np.abs(pred_mem - pred_file)))
    print(f"[self-test] exported-weights max prediction delta {derr:.3g}")
    if derr > 1e-9:
        print("[self-test] FAIL exported weights do not reproduce predictions")
        ok = False
    jrep = json.load(open(js))
    for k in ("feature_order", "coef", "bias", "target", "holdout", "n_records"):
        if k not in jrep:
            print(f"[self-test] FAIL companion JSON missing {k!r}")
            ok = False
    if jrep.get("feature_order") != FEATURE_ORDER or jrep.get("target") != TARGET:
        print("[self-test] FAIL companion JSON metadata mismatch")
        ok = False

    # Spearman sanity against a hand-checkable case (ties averaged).
    rho = spearman([1, 2, 3, 4], [4, 3, 2, 1])
    if abs(rho + 1.0) > 1e-12:
        print(f"[self-test] FAIL spearman([1,2,3,4],[4,3,2,1]) = {rho}")
        ok = False
    rho = spearman([1, 2, 2, 3], [1, 2, 2, 3])
    if abs(rho - 1.0) > 1e-12:
        print(f"[self-test] FAIL spearman with ties = {rho}")
        ok = False

    # Depth balancing must equalize bucket mass.
    w = depth_balanced_weights(depth)
    b = depth_buckets(depth)
    mass = np.array([w[b == k].sum() for k in np.unique(b)])
    if mass.max() - mass.min() > 1e-9:
        print(f"[self-test] FAIL depth-bucket mass not equal: {mass}")
        ok = False
    print(f"[self-test] depth buckets {len(mass)}, mass/bucket {mass[0]:.2f} "
          f"(mean weight {w.mean():.4f})")

    os.remove(txt)
    os.remove(js)
    print(f"[self-test] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


# ------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", nargs="+", help="corpus JSONL (coleffort_*.jsonl)")
    ap.add_argument("--name", help="model name (e.g. cw1)")
    ap.add_argument("--holdout", default="",
                    help="comma-separated instance tags held out entirely")
    ap.add_argument("--l2", type=float, default=None, help="fixed L2 (else sweep)")
    ap.add_argument("--out-dir", default="ml/models")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args.out_dir)
    if not args.train or not args.name:
        raise SystemExit("need --train and --name (or --self-test)")

    X, y, depth, inst = load(args.train)
    holdout = {t for t in args.holdout.split(",") if t}
    known = set(inst.tolist())
    for t in sorted(holdout - known):
        print(f"  WARNING holdout instance {t!r} is not in the corpus")
    if not holdout:
        print("  WARNING no --holdout: reported R2/rho are IN-SAMPLE only")

    grid = [args.l2] if args.l2 is not None else L2_GRID
    rep = train(X, y, depth, inst, holdout, grid)

    print(f"\nmodel {args.name}")
    print(f"  files        : {', '.join(args.train)}")
    print(f"  records      : {rep['n_records']} (train {rep['n_train']} / "
          f"held-out {rep['n_holdout']}) over {len(rep['instances'])} instances")
    print(f"  target       : {rep['target']}")
    print(f"  holdout      : {', '.join(rep['holdout']) or '(none)'}")
    print(f"  chosen L2    : {rep['l2']:g}   depth buckets {rep['depth_buckets']}")
    print(f"  train R2     : {rep['train_r2']:+.4f}")
    if rep["held_out_r2"] is not None:
        print(f"  held-out R2  : {rep['held_out_r2']:+.4f}")
        print(f"  held-out rho : {rep['held_out_spearman']:+.4f} (Spearman)")
        for t, s in sorted(rep["per_holdout_inst"].items()):
            print(f"    {t:<22} n={s['n']:>8,}  R2 {s['r2']:+.4f}  "
                  f"rho {s['spearman']:+.4f}")
    print("  coefficients (standardized / folded):")
    for name, sc, c in zip(FEATURE_ORDER, rep["std_coef"], rep["coef"]):
        print(f"    {name:22s} {sc:+.4f}   {c:+.6g}")

    if args.no_export:
        return 0
    txt, js = export(rep, args.name, args.out_dir)
    print(f"  wrote {txt}\n  wrote {js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
