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

v2.1 PAIRWISE mode (§3b).  Plain effort regression confounds *state hardness*
with *choice quality*.  `--pairwise` instead consumes within-state pairs from
`mine_subtrees.py --pairs`

    {"inst","shash","depth","fw":[10],"fl":[10],"yw","yl","src"}

and fits a RankNet logistic model on the score DIFFERENCE: score is predicted
effort (lower = better = covered first), so the winner must score below the
loser, and the loss is `softplus(-(s_loser - s_winner))`.  The bias cancels in
a difference and is exported as 0 — only within-node score *order* is ever used
by the engine.  Held-out metric is pair accuracy, split by instance.

Usage:
    python3 ml/fit_col_effort.py --train data/trackc/coleffort_s19.jsonl \\
        --name cw1 --holdout chain5,chain26 [--l2 1e-2]
    # --l2 omitted => sweep and pick the best held-out R^2
    python3 ml/fit_col_effort.py --pairwise --train data/trackc/pairs_s19.jsonl \\
        --name cwp1 --holdout chain82
    python3 ml/fit_col_effort.py --self-test    # synthetic round-trip
"""

import argparse
import gzip
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
TARGET_PAIRWISE = "ranknet(within-state pair, score = effort, lower wins)"
WEIGHTS_MAGIC = "trackc-cw1"

L2_GRID = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]
# pairwise loss is a SUM over pairs (not a mean), so the useful penalty range
# scales with the pair count -- hence a grid that reaches further up.
L2_GRID_PAIR = [1e-2, 1e-1, 1.0, 10.0, 100.0, 1000.0]
NDEC = 10  # depth buckets (deciles)


# ------------------------------------------------------------------- data


def _open(path):
    """Corpora are large; farm deliverables arrive gzipped."""
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


CHUNK = 250_000  # rows converted to numpy at a time (keeps peak RAM bounded)


def _flush(buf, chunks):
    """Convert a python-list chunk to float64 numpy and drop the list."""
    if buf:
        chunks.append(np.asarray(buf, dtype=float))
        del buf[:]


def load(paths):
    """-> (X (n,NF), y (n,), depth (n,), inst (n,) of str)."""
    Xc, X, y, depth, inst = [], [], [], [], []
    for path in paths:
        with _open(path) as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                f = d["feats"]
                if len(f) != NF:
                    raise SystemExit(f"{path}:{lineno} feature width {len(f)} != {NF}")
                X.append(f)
                if len(X) >= CHUNK:
                    _flush(X, Xc)
                y.append(math.log1p(d["subtree"]))
                depth.append(d["depth"])
                inst.append(d.get("inst", os.path.basename(path)))
    _flush(X, Xc)
    if not Xc:
        raise SystemExit("no records found")
    return (
        np.vstack(Xc),
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


# --------------------------------------------------------------- pairwise
#
# docs/TRACKC2-DESIGN.md §3b.  Everything below operates on DIFFERENCE vectors
# d = f_loser - f_winner; the model is correct on a pair iff coef . d > 0.


def load_pairs(paths):
    """-> (Fw (n,NF), Fl (n,NF), inst (n,), src (n,), depth (n,))."""
    Fwc, Flc = [], []
    Fw, Fl, inst, src, depth = [], [], [], [], []
    for path in paths:
        with _open(path) as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                fw, fl = d["fw"], d["fl"]
                if len(fw) != NF or len(fl) != NF:
                    raise SystemExit(
                        f"{path}:{lineno} pair feature width != {NF}")
                Fw.append(fw)
                Fl.append(fl)
                if len(Fw) >= CHUNK:
                    _flush(Fw, Fwc)
                    _flush(Fl, Flc)
                inst.append(d.get("inst", os.path.basename(path)))
                src.append(d.get("src", "?"))
                depth.append(d.get("depth", 0))
    _flush(Fw, Fwc)
    _flush(Fl, Flc)
    if not Fwc:
        raise SystemExit("no pairs found")
    return (
        np.vstack(Fwc),
        np.vstack(Flc),
        np.asarray(inst),
        np.asarray(src),
        np.asarray(depth, dtype=float),
    )


def fit_ranknet(D, l2, iters=60, tol=1e-10):
    """Newton/IRLS on sum softplus(-D beta) + l2/2 |beta|^2.  -> beta (p,).

    The L2 term keeps the Hessian positive definite even when the pairs are
    separable (the usual RankNet failure mode: |beta| runs to infinity), so a
    plain Newton step is safe; a halving line search guards the rest.
    """
    n, p = D.shape
    beta = np.zeros(p)

    def obj(b):
        z = D @ b
        return float(np.sum(np.logaddexp(0.0, -z)) + 0.5 * l2 * float(b @ b))

    f = obj(beta)
    for _ in range(iters):
        z = D @ beta
        s = 1.0 / (1.0 + np.exp(np.clip(z, -500, 500)))   # sigma(-z)
        grad = -(D.T @ s) + l2 * beta
        w = s * (1.0 - s)
        H = D.T @ (w[:, None] * D) + l2 * np.eye(p)
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        t = 1.0
        for _ls in range(30):
            cand = beta - t * step
            fc = obj(cand)
            if fc <= f:
                break
            t *= 0.5
        else:
            break
        if abs(f - fc) <= tol * max(1.0, abs(f)):
            beta, f = cand, fc
            break
        beta, f = cand, fc
    return beta


def pair_acc(D, coef):
    """Fraction of pairs where the winner scores strictly below the loser."""
    if len(D) == 0:
        return float("nan")
    return float(np.mean((D @ coef) > 0.0))


def train_pairwise(Fw, Fl, inst, src, holdout, l2_grid, verbose=True):
    """RankNet on within-state pairs.  -> report dict (same export contract)."""
    held = np.isin(inst, list(holdout)) if holdout else np.zeros(len(inst), bool)
    tr = ~held
    if not tr.any():
        raise SystemExit("holdout consumed every pair")

    # Standardize on the raw feature vectors seen on either side of a training
    # pair, then fold sd into the coefficients: d_std = (fl - fw) / sd.
    stack = np.vstack([Fw[tr], Fl[tr]])
    mu = stack.mean(axis=0)
    sd = stack.std(axis=0)
    sd[sd < 1e-12] = 1.0
    D = (Fl - Fw) / sd
    del mu  # a difference kills the location term; kept explicit on purpose

    results = []
    for l2 in l2_grid:
        beta = fit_ranknet(D[tr], l2)
        coef = beta / sd
        acc_tr = pair_acc(Fl[tr] - Fw[tr], coef)
        acc_te = pair_acc(Fl[held] - Fw[held], coef) if held.any() else acc_tr
        results.append((acc_te, l2, coef, beta, acc_tr))
        if verbose:
            print(f"  l2={l2:<8g} train pair-acc {acc_tr:.4f}   "
                  f"{'held-out' if held.any() else 'in-sample'} "
                  f"pair-acc {acc_te:.4f}")
    acc_te, l2, coef, beta, acc_tr = max(
        results, key=lambda t: (t[0] if np.isfinite(t[0]) else -1e18, -t[1])
    )

    rep = {
        "feature_order": FEATURE_ORDER,
        "coef": [float(c) for c in coef],
        "bias": 0.0,          # cancels in a within-state difference
        "target": TARGET_PAIRWISE,
        "mode": "pairwise",
        "holdout": sorted(holdout),
        "n_records": int(len(inst)),
        "n_train": int(tr.sum()),
        "n_holdout": int(held.sum()),
        "instances": sorted(set(inst.tolist())),
        "l2": float(l2),
        "train_pair_acc": float(acc_tr),
        "held_out_pair_acc": float(acc_te) if held.any() else None,
        "std_coef": [float(c) for c in beta],
        "std_bias": 0.0,
        "by_src": {s: int(np.sum(src == s)) for s in sorted(set(src.tolist()))},
    }
    rep["per_inst"] = {}
    for t in sorted(set(inst.tolist())):
        m = inst == t
        rep["per_inst"][t] = {
            "n": int(m.sum()),
            "held_out": bool(t in holdout),
            "pair_acc": float(pair_acc(Fl[m] - Fw[m], coef)),
        }
    rep["per_src_held"] = {}
    for s in sorted(set(src.tolist())):
        m = held & (src == s)
        if m.any():
            rep["per_src_held"][s] = {
                "n": int(m.sum()),
                "pair_acc": float(pair_acc(Fl[m] - Fw[m], coef)),
            }
    return rep


# ----------------------------------------------------------------- export


def export(rep, name, out_dir):
    stem = name if name.startswith("trackc") else f"trackc_{name}"
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

    ok = self_test_pairwise(out_dir) and ok
    print(f"[self-test] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def self_test_pairwise(out_dir):
    """Synthetic pairwise round-trip (§3b): a known effort direction must be
    recovered from within-state comparisons alone, and the exported weights
    must reproduce the in-memory pair verdicts."""
    rng = np.random.default_rng(7)
    n = 6000
    insts = np.array(["synA", "synB", "synC", "synD"])[rng.integers(0, 4, n)]
    src = np.where(rng.random(n) < 0.7, "probe", "transpo")
    w_true = rng.normal(size=NF)

    # Each pair is two candidate columns AT THE SAME STATE: a shared per-state
    # offset (the confound pairwise mode is designed to cancel) plus per-column
    # variation.  Labels come from the true effort order, with logistic noise
    # so the scale of w_true is identified.
    state = rng.normal(size=(n, NF)) * 3.0
    A = state + rng.normal(size=(n, NF))
    B = state + rng.normal(size=(n, NF))
    gap = (A - B) @ w_true
    a_wins = gap + rng.logistic(size=n) * 1.0 < 0.0   # lower effort wins
    Fw = np.where(a_wins[:, None], A, B)
    Fl = np.where(a_wins[:, None], B, A)

    print(f"\n[self-test] pairwise synthetic corpus: {n} pairs, "
          f"{len(set(insts.tolist()))} instances")
    rep = train_pairwise(Fw, Fl, insts, src, {"synD"}, L2_GRID_PAIR)
    ok = True
    acc = rep["held_out_pair_acc"]
    print(f"[self-test] held-out pair accuracy {acc:.4f}  (l2 {rep['l2']:g})")
    if not (acc > 0.75):
        print("[self-test] FAIL pairwise held-out accuracy <= 0.75")
        ok = False
    coef = np.asarray(rep["coef"])
    cos = float(coef @ w_true / (np.linalg.norm(coef) * np.linalg.norm(w_true)))
    print(f"[self-test] cosine(coef, true effort direction) {cos:+.4f}")
    if cos < 0.95:
        print("[self-test] FAIL pairwise direction not recovered")
        ok = False
    if rep["bias"] != 0.0:
        print("[self-test] FAIL pairwise bias must be 0 (it cancels)")
        ok = False

    txt, js = export(rep, "selftest_colpair", out_dir)
    fcoef, fbias = read_weights(txt)
    v_mem = (Fl - Fw) @ coef > 0
    v_file = (Fl - Fw) @ fcoef + 0.0 * fbias > 0
    if not np.array_equal(v_mem, v_file):
        print("[self-test] FAIL exported weights change pair verdicts")
        ok = False
    jrep = json.load(open(js))
    for k in ("feature_order", "coef", "bias", "target", "mode",
              "held_out_pair_acc", "by_src"):
        if k not in jrep:
            print(f"[self-test] FAIL pairwise JSON missing {k!r}")
            ok = False
    if jrep.get("target") != TARGET_PAIRWISE or jrep.get("mode") != "pairwise":
        print("[self-test] FAIL pairwise JSON metadata mismatch")
        ok = False
    os.remove(txt)
    os.remove(js)

    # A perfectly separable, noiseless problem must still terminate and be
    # right on every training pair (the L2 term is what makes this safe).
    D = rng.normal(size=(500, NF))
    D[(D @ w_true) < 0] *= -1.0
    beta = fit_ranknet(D, 1e-2)
    sep = float(np.mean((D @ beta) > 0))
    print(f"[self-test] separable-case train pair-acc {sep:.4f}")
    if sep < 0.999:
        print("[self-test] FAIL separable pairs not fit")
        ok = False
    print(f"[self-test] pairwise {'PASS' if ok else 'FAIL'}")
    return ok


# ------------------------------------------------------------------- main


def main_pairwise(args):
    Fw, Fl, inst, src, depth = load_pairs(args.train)
    holdout = {t for t in args.holdout.split(",") if t}
    known = set(inst.tolist())
    for t in sorted(holdout - known):
        print(f"  WARNING holdout instance {t!r} is not in the corpus")
    if not holdout:
        print("  WARNING no --holdout: reported pair accuracy is IN-SAMPLE only")

    grid = [args.l2] if args.l2 is not None else L2_GRID_PAIR
    rep = train_pairwise(Fw, Fl, inst, src, holdout, grid)

    print(f"\nmodel {args.name} (PAIRWISE, §3b)")
    print(f"  files        : {', '.join(args.train)}")
    print(f"  pairs        : {rep['n_records']} (train {rep['n_train']} / "
          f"held-out {rep['n_holdout']}) over {len(rep['instances'])} instances")
    print(f"  sources      : " + "  ".join(
        f"{k}={v:,}" for k, v in sorted(rep["by_src"].items())))
    print(f"  target       : {rep['target']}")
    print(f"  holdout      : {', '.join(rep['holdout']) or '(none)'}")
    print(f"  chosen L2    : {rep['l2']:g}")
    print(f"  train pair-acc   : {rep['train_pair_acc']:.4f}")
    if rep["held_out_pair_acc"] is not None:
        print(f"  HELD-OUT pair-acc: {rep['held_out_pair_acc']:.4f}")
        for s, d in sorted(rep["per_src_held"].items()):
            print(f"    src {s:<10} n={d['n']:>9,}  acc {d['pair_acc']:.4f}")
    print("  per instance (held-out marked *):")
    for t, d in sorted(rep["per_inst"].items()):
        print(f"    {'*' if d['held_out'] else ' '} {t:<22} n={d['n']:>9,}  "
              f"acc {d['pair_acc']:.4f}")
    print("  coefficients (standardized / folded):")
    for name, sc, c in zip(FEATURE_ORDER, rep["std_coef"], rep["coef"]):
        print(f"    {name:22s} {sc:+.4f}   {c:+.6g}")
    del depth
    if args.no_export:
        return 0
    txt, js = export(rep, args.name, args.out_dir)
    print(f"  wrote {txt}\n  wrote {js}")
    return 0


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
    ap.add_argument("--pairwise", action="store_true",
                    help="--train files are mine_subtrees.py --pairs output (§3b)")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args.out_dir)
    if not args.train or not args.name:
        raise SystemExit("need --train and --name (or --self-test)")

    if args.pairwise:
        return main_pairwise(args)

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
