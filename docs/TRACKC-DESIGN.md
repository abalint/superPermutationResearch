# Track C design — learned row ordering inside the DLX rooted-cover search

Status: opened session 17 (2026-07-27). This is the build spec; deviations must be
recorded here. Context: `docs/ITEM5-DESIGN.md` §4–5 (Track C is the thesis),
JOURNAL s13/s15 (the failure mode Track C targets: **no engine we have can FIND a
rooted cover even on known-SAT instances** — CaDiCaL, Python DLX, C DLX all stall
> 45 min on n=7 standard K=5 and on the real 5906's K=18 chain, while UNSAT
verdicts come fast). Ordering inside a complete DFS cannot break correctness —
it only changes *when* a solution or exhaustion is reached — so unlike s8's beam
scorers, a learned preference here is exploit-proof by construction. That is why
this is the right first deployment.

## 1. The decision being learned

A DLX node chooses a column `c` (kept fixed: **MRV, ties by lowest column index**
— identical in trainer and engine, this is load-bearing), then tries candidate
rows in some order. Track C learns that order: a linear scorer over per-candidate
features, trained pairwise (RankNet, s8 architecture) so that at replay states of
known covers the true cover's row outranks its siblings.

State = partial cover (DLX internal state + rooted-forest state). Candidate = an
active row of `c`. All features below are per-(state, candidate-row) and must be
O(children) using quantities DLX already maintains (`size[col]`, forest
`parent_of`), plus two cheap incremental maps defined in §2.

## 2. Feature vector — LOCKED, v1 (order matters; 8 features)

Notation: row `r` has children orbits `ch(r)` (n−2 of them: 4 at n=6, 5 at n=7),
parent orbit `p(r)`. `size[x]` = current number of active candidate rows of
active column `x` (the DLX column count). "Placed" = row currently in the partial
cover. A placed row is **grounded** iff its parent-orbit ownership chain reaches
a kernel root through placed rows (roots are grounded by definition). Engine and
trainer must maintain:
  - `grounded[orbit]` — orbit is a root, or is a child of a grounded placed row.
    (Equivalently: covered orbits inherit groundedness from their covering row's
    parent chain.) Maintained incrementally with the forest trail.
  - `pending[orbit]` — count of placed-but-ungrounded rows `r'` with `p(r') ==
    orbit` (they become groundable when `orbit` is covered by a grounded row).

Features, exactly this order:

| # | name | definition |
|---|------|-----------|
| 1 | `min_child_sz_log` | `log1p(min over ch(r) of size[child])` |
| 2 | `mean_child_sz_log` | mean over `ch(r)` of `log1p(size[child])` |
| 3 | `scarce_children` | (# children with `size ≤ 2`) / (n−2) |
| 4 | `parent_is_root` | 1.0 if `p(r)` is a kernel root orbit else 0.0 |
| 5 | `parent_grounded` | 1.0 if `grounded[p(r)]` else 0.0 (roots ⇒ 1.0) |
| 6 | `parent_depth_log` | if grounded: `log1p(#placed-row hops from p(r) up to a root)`; else 0.0 (roots: depth 0 ⇒ 0.0) |
| 7 | `static_min_child_log` | `log1p(min over ch(r) of initial size[child])`, precomputed at instance load |
| 8 | `grounds_pending` | `(Σ over ch(r) of pending[child])` / (n−2) |

Feature 8 is the thesis feature — credit for *completing* structure (placing the
row that grounds waiting subtrees), the thing s8 proved no static walk feature
could express. Features shared by all siblings at a node (e.g. `size[c]`, depth)
are deliberately excluded: pairwise loss cancels them.

**Timing (binding, settled during the build):** features are evaluated on the
state BEFORE `cover(c)` — the chosen column is still active, `size[c]` still
counts all its candidates, and candidates are enumerated from the active column.

Score = `dot(w, f) + b`, try rows in **descending score**, ties by row id.
Weights file format (consumed by the C engine): text, line 1 = `trackc-w1 8`,
line 2 = 8 whitespace-separated floats then the bias (standardization already
folded in by the trainer). The trainer also exports a companion JSON
(`feature_order`, `coef`, `bias`, training metadata) for the Python side.

**Parity gate (mandatory, blocks training):** a fixed replay trace (n=6 standard
instance, first known cover, teacher-forced) must produce byte-identical feature
vectors (printed at 6 decimal places) from the Python extractor and the C
engine's `--dump-features` mode, for every (node, candidate) pair. Any mismatch
is a build failure, not a tolerance.

## 3. Training data

Positives are replays of known covers ("teacher forcing"): at each node, MRV
picks `c`; the positive is the unique cover row covering `c`; negatives are all
other active candidates of `c`; place the positive, recurse. Each cert yields R
decisions (~25 at n=6, ~118–138 at n=7), each with its sibling negatives.

Sources on disk:
- n=6: 298 records (`data/records872/`, `data/gain1_872s/`) →
  `extract_certificate(word, n=6)` → covers over the standard-kernel instance
  `gain1.build_instance(6)` (100 cols × 464 rows). Gate: every extracted cert
  passes `check_cover` on the instance (drop + count failures).
- n=7 standard: 3 × 5907 certs (`analysis/cover7/cert5907_*.json`), instance
  `chain7.standard_chain()` (690 × 4440).
- n=7 nonstandard: 11 × 5906 certs (`analysis/cover7/cert5906_*.json`,
  K=18/20/24 families), instances rebuilt from each cert's chain.

Corpus format: JSONL, one line per decision node:
`{"inst": tag, "n": 6|7, "col": id, "pos": row_id, "neg": [row_ids],
"feats": {row_id: [8 floats]}}`. Written to `data/trackc/` (gitignored except a
small committed sample).

Dead-end negatives (rows whose subtree exhausted in real DLX runs) are a v2
refinement — sibling negatives first.

## 4. Holdout design (honesty requirement)

Two models, so every known-SAT gate is evaluated by a model that never saw it:
- **Model A**: train n=6 + all 5906-family certs → gate on n=7 **standard K=5**
  (5907, held out entirely).
- **Model B**: train n=6 + 5907 certs → gate on the **5906 K=18 chain** (held
  out entirely; the other 5906-family certs are also excluded from B since they
  share structure).

Cross-n transfer is intrinsic to the design: features are scale-normalized
(log1p, per-(n−2) fractions), no n-specific inputs.

## 5. Engine

`analysis/trackc/dlx7g.c` — descendant of `analysis/farm/dlx7_win.c` (same
instance text format from `solve_dlx.py`, same forest machinery, same exit
codes: 0 solution / 2 exhausted / 3 timeout). Additions:
- `--weights <file>`: linear model; per-node candidate ordering by descending
  score (feature spec §2). Without `--weights`: original behavior (baseline).
- `--dump-features <trace>`: teacher-forced replay of a given cover (row-id list
  file), print feature vectors per node — the parity gate.
- `--epsilon <p> --seed <s>`: with probability p per node, shuffle the scored
  order (restart diversity; deterministic given seed). Keep the node-cap restart
  machinery.
- Progress line to stderr every N nodes: nodes, max depth reached, elapsed.
Driver: `analysis/trackc/solve_guided.py`, mirroring `solve_dlx.py` (build
instance → run engine → `check_cover` → `compile_chain_cover` → Rust
`validate`). Any found cover MUST pass the Rust validator before being reported.

## 6. Trainer

`ml/fit_cover_rank.py` (numpy only): reads §3 JSONL, pairwise logistic loss
softplus(−(s_pos − s_neg)) over (pos, neg) sibling pairs, L2, full-batch GD,
feature standardization folded into exported weights. Reports held-out pair
accuracy (held-out = whole certs, not sampled pairs — split by cert id). Exports
§2 weights file + JSON.

## 7. Gates

- **G0 (correctness/parity)**: parity gate §2; guided engine re-finds the n=6
  standard 25-row cover; UNSAT verdicts on refuted chains unchanged (spot-check
  1–2 known-UNSAT chains exhaust to the same verdict).
- **G1 (headline)**: n=7 standard K=5 instance, Model A, 60-min budget. Blind
  baseline (no weights, seeds 0–2) vs guided. Metric: first rooted cover found
  (time, nodes); secondary: max depth profile. ANY validated cover here is a
  first for this project's engines.
- **G1b**: 5906 K=18 chain, Model B, same protocol.
- **G2 (UNSAT economy)**: nodes-to-exhaust guided vs blind on 2 small refuted
  chains (ordering also shapes exhaustion cost).
- **G3 (the record attack, only if G1 or G1b passes)**: the 5 open K=27 chains
  (`chains_V15_s14.jsonl` / farm worklist), long budget, background. Any SAT →
  compile → validate → **5905, world record**.

Held-out pair accuracy is diagnostic only; the go/no-go currency is G1/G1b
search performance (s8 lesson: offline metrics do not transfer on their own).

## 8. Risks

1. Teacher-forced states are all on-path; off-path guidance may be weak → v2:
   dead-end mining, DAgger-style. Accepted for v1.
2. MRV column order in training must match the engine exactly, including tie
   breaks — covered by the parity gate.
3. n=6 → n=7 transfer may fail; that is what the two-model holdout measures.
4. If guided DLX still can't crack G1, the fallback deployment is CDCL phase/
   branching biasing from the same model (`sat_chain.py --phase-cert` already
   exists as the hook) — noted, not built in v1.
