# Track C v2 design — learned COLUMN choice + dead-end mining in the DLX rooted-cover search

Status: opened session 19 (2026-07-28). Build spec; deviations must be recorded here.
Prereqs: `docs/TRACKC-DESIGN.md` (v1, row ordering), `analysis/trackc/RESULTS-s17.md`
(v1 verdict). The load-bearing v1 facts: (a) with the column rule fixed at MRV, row
order only permutes the DFS — the exhaustion tree is the identical node set (G2,
verified byte-identical node counts), so row learning can never shrink the tree;
(b) the offline row-ranking signal was real (cross-n pair acc .746) but did not
convert to cover-finding at n=7 depth. v2 attacks the tree itself: **which column
to cover next** is the only per-node decision that changes tree *size* for both
SAT and UNSAT outcomes, and any column policy whatsoever preserves completeness
and soundness (every active column must be covered on every path; choice order
cannot fabricate or lose solutions). Like v1, the deployment is exploit-proof by
construction.

## 1. The decision being learned

At a DLX node, v1 picked the column by MRV (min `size[c]`, ties by lowest column
index). v2 scores candidate columns with a learned linear model of per-column
features and covers the column with the **lowest predicted remaining effort**
(predicted log-subtree-size; see §3). Deployment is constrained to the MRV band:

    C*_Δ = { c active : size[c] ≤ min_size + Δ }

- `Δ = 0` (default): learned **MRV tie-break** — we never branch wider than MRV
  would; the model only chooses among minimum-size columns. Strictly-safe rollout.
- `Δ = 1`: measured relaxation, only deployed if gates pass (§7).
- Ties in predicted score: lowest column index (so ε=0, flat weights ⇒ exactly
  the v1 MRV engine). Note the C engine's MRV scans the active-column linked
  list with strict `<`, which is ascending-index order among surviving columns
  — identical to the Python replayer's explicit lowest-index rule; v2 keeps
  this equivalence load-bearing for the parity gate.

**M0 (measurement, precedes training):** fraction of nodes with |C*_0| ≥ 2 and the
distribution of |C*_0|, |C*_1| on n6std, two refuted n=7 chains, and n7std (node-
capped). If MRV ties are rare (< 10% of nodes), Δ=0 is inert and Δ=1 becomes the
training/deployment default. Record the numbers here once measured.

M0 RESULT: *to be filled in from the `--mrv-stats` measurement before training
begins — do not train until this section has numbers.*

## 2. Column feature vector — LOCKED, v2 (order matters; 10 features)

Notation as v1 §2: rows of column c are its active candidate rows; row `r` has
children orbits `ch(r)` (n−2 of them) and parent orbit `p(r)`; `size[x]` = active
DLX column count; `grounded[orbit]` and `pending[orbit]` exactly as maintained
since v1. All features are computed on the state BEFORE `cover(c)` (v1 timing
rule), for each candidate column, in O(size[c] · (n−2)).

| # | name | definition |
|---|------|-----------|
| 1 | `sz_log` | `log1p(size[c])` |
| 2 | `sz_rel` | `size[c] − min_size` (float; 0.0 everywhere when Δ=0) |
| 3 | `static_sz_log` | `log1p(initial size[c])`, precomputed at instance load |
| 4 | `is_root` | 1.0 if c is a kernel root orbit else 0.0 |
| 5 | `grounded_c` | 1.0 if `grounded[c]` else 0.0 |
| 6 | `pending_log` | `log1p(pending[c])` |
| 7 | `mean_child_load` | mean over rows r of c of ( mean over ch(r) of `log1p(size[child])` ) |
| 8 | `min_child_load` | min over rows r of c of ( min over ch(r) of `log1p(size[child])` ) |
| 9 | `frac_parents_grounded` | fraction of rows r of c with `grounded[p(r)]` |
| 10 | `active_cols_log` | `log1p(#active columns)` (node-level; shared by all candidates — carries no ranking signal within a node but anchors the effort regression across depths) |

In features 7/8, a child orbit that is already covered (inactive) contributes
`log1p(0) = 0.0` — same convention as v1's row features under pre-cover timing.
For an inactive/covered parent orbit in feature 9, `grounded[p(r)]` reads the
maintained array as-is (covered orbits keep their groundedness).

Score = `dot(w, f) + b` = predicted log-effort; cover the candidate with the
**minimum** score, ties by lowest column index. Weights file (consumed by C):
text, line 1 = `trackc-cw1 10`, line 2 = 10 floats then bias (standardization
folded in by the trainer). Companion JSON exported for the Python side
(`feature_order`, `coef`, `bias`, `target`, training metadata).

**Parity gate (mandatory, blocks training):** teacher-forced replay of the n=6
standard 25-row cover (same trace file as v1), column policy fixed at plain MRV
for the replay; at every node, BOTH the Python extractor and the C engine's
`--dump-col-features` mode print the 10-vector at 6 decimal places for **every
active column** (not just C*). Byte-identical diff required, else build failure.

## 3. Training data — dead-end mining (effort labels)

Key fact: in DFS, every backtracked subtree is **fully exhausted** regardless of
how the whole run ends. So any run — including 10/30-min TIMEOUTs on open chains
— yields exact effort labels for every popped frame; only frames still on the
stack at timeout (and frames on a success path, if any) are censored and dropped.
This turns the 138 open chains' intractability into training signal.

Generation runs: dlx7g with `--log-subtrees <file>` writes one JSONL record per
qualifying node at frame pop:

    {"inst": tag, "depth": d, "cand": |C*_Δgen|, "col": chosen_id,
     "feats": [10 floats], "subtree": nodes_in_subtree, "outcome": "exhaust"}

Qualify = subtree ≥ 500 nodes, OR a deterministic 1/1024 hash-sample of smaller
ones (volume control; a 60M-node run yields ≤ ~120k + ~60k records). Only the
CHOSEN column's features are logged (sibling logging is a later option).
Diversity: `--col-epsilon p --col-seed s` — with prob p per node pick uniformly
from C*_1 instead of the policy choice. Generation default ε=0.15.

Sources (train/eval split is BY INSTANCE, locked before training):
- n=6: n6std, blind + ε runs (fast, in-sample mechanism data).
- n=7 TRAIN: the search-UNSAT chains minus the eval set, i.e. indices
  {82, 84, 85, 89, 98, 103, 106, 109, 127, 131, 134, 141, 150, 160, 174, 175,
  189, 194, 196, 217, 219, 220, 221, 222} (indices into
  `analysis/farm/farm_chains.jsonl`, index-aligned with
  `analysis/cover7/results_n7_merged.csv`), plus a sample of OPEN chains
  (their exhausted subtrees are clean labels), 10-min caps.
- n=7 EVAL (LOCKED before any training; never trained on): the 8 refuted
  chains {5, 25, 26, 43, 72, 73, 74, 76} — 5 (K=29) and 26 (K=30) are the v1
  G2 baseline pair (60,037,516 and 8,548,527 blind DLX nodes); the other six
  are the next search-UNSAT indices in order. Eval chains that blind DLX
  cannot exhaust within a 60-min cap are reported as capped and excluded from
  the G2v2 median (recorded, not silently dropped).
- The G1/G1b gate instances (n7std, c5906 K=18) are excluded from generation
  entirely: the known-SAT gates stay cross-instance by construction, replacing
  v1's A/B cert holdout (no cert-derived training data exists in v2).

Corpus assembly: `analysis/trackc/mine_subtrees.py` merges run logs →
`data/trackc/coleffort_*.jsonl` (gitignored except a small committed sample).

## 4. Model and trainer

`ml/fit_col_effort.py` (numpy only): linear least-squares / ridge on target
`y = log1p(subtree)`, features §2, feature standardization folded into exported
weights, depth-balanced sample weighting (bucket by depth decile, equal total
weight per bucket) so near-root giants don't drown deep decisions. Reports
held-out (by-instance) R² and Spearman ρ, and — diagnostic only — the
"regret@node": on eval-instance logs, fraction of nodes where the model ranks
the observed subtree correctly among logged alternatives at matched depth.
Exports `trackc-cw1` weights + JSON. Go/no-go currency is G2v2/G1 search
performance, not offline fit (v1 lesson, again).

## 5. Engine changes (`analysis/trackc/dlx7g.c`)

All new behavior is flag-gated; with no new flags the binary is bit-identical to
v1 behavior (regression check: chain 26 blind exhausts in exactly 8,548,527
nodes; n6std blind cover at 21,627 nodes).

- `--col-weights <file>`: learned column choice within C*_Δ (min predicted
  effort). `--col-delta <int>` (default 0).
- `--col-epsilon <p> --col-seed <s>`: per-node exploration among C*_1 (for
  generation; deterministic given seed). Independent of v1's row `--epsilon`.
- `--log-subtrees <file>`: §3 JSONL logging (buffer per stack frame, write on
  pop; drop censored frames).
- `--dump-col-features <trace>`: parity mode (§2).
- `--mrv-stats`: M0 counters, printed at exit to stderr.
- v1 row `--weights` continues to work and composes with column choice.

Driver: `analysis/trackc/solve_guided.py` grows `--col-weights/--col-delta`
passthrough; any found cover still MUST pass `check_cover` →
`compile_chain_cover` → Rust `validate` before being believed.

## 6. Compute plan

- Mac (local): build, parity, M0, n=6 runs, corpus assembly, training, quick
  G2v2 spot checks. Heavy sweeps do NOT run locally.
- PC farm (`ssh transcribe`, 28 cores, idle since s18): (a) generation sweep —
  ε-runs over the train chains with subtree logging, 10-min caps; (b) G2v2 eval
  sweep — blind vs guided on the 8 eval chains; (c) G1/G1b 60-min runs; (d) if
  GO: pass-2 over the 138 open chains, guided. Per `analysis/cover7/
  REMOTE-FARM.md` conventions: never kill user processes, nice'd workers,
  results to CSV ledgers, scp logs back for training.

## 7. Gates

- **G0 (correctness/parity)**: column parity byte-clean; flagless binary
  reproduces v1 node counts exactly (chain 26 = 8,548,527; n6std = 21,627);
  guided engine still finds the n6std cover and it compiles to a Rust-validated
  872; guided UNSAT verdicts on 2 refuted chains unchanged in *verdict*
  (node counts now legitimately differ — that is the whole point).
- **G2v2 (primary, the tree-shrinking claim)**: blind MRV vs guided (Δ=0 and
  Δ=1) nodes-to-exhaust on the 8 held-out eval chains. **GO** = median node
  reduction ≥ 1.3× with no chain blowing up > 2×; stretch goal ≥ 2×. This is
  the go/no-go for pass-2 deployment (UNSAT economy was v1's proven-impossible
  axis — any consistent win here is new capability).
- **G1 (headline)**: n7std K=5, 60-min, blind (det + 2 seeds) vs guided
  (Δ=0/Δ=1, det + ε-restarts). Metric: first validated cover (time, nodes);
  secondary max-depth profile. Any validated cover is a project first.
- **G1b**: c5906 K=18, same protocol.
- **G3 (only on GO)**: G2v2 GO → guided pass-2 refutation sweep over the 138
  open chains on the farm (30-min caps) — every new UNSAT is a census closure;
  G1/G1b cover found → K=27 record attack (5905).

## 8. Risks

1. Effort labels are policy-dependent (subtree size under the run's own
   subsequent choices, not an intrinsic column property). Standard in learned
   branching; ε-exploration decorrelates. Accepted.
2. Δ=1 can regress badly on some instance; G2v2's no-blowup clause and Δ=0
   fallback bound the damage.
3. Training distribution is refuted/open chains; n6std and the SAT gates are
   structurally different (covers exist). The G1 gates measure exactly this
   transfer; a G2v2-only win still pays (census closures).
4. Windows farm build of the extended dlx7g must reproduce Mac node counts on a
   fixed chain before any farm ledger is trusted (same discipline as s15's
   PermutationChains lesson).
