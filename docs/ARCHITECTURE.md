# Architecture

Code map for the `superperm` crate (phases 1–3). Math background lives in
`docs/THEORY.md` — this file only covers what the code does and where to change it.
Binary + library crate: `src/lib.rs` exports the modules, `src/main.rs` is the CLI.
The Python training side lives in `ml/` (see its section below); the two halves talk
only through rollout JSONL (Rust → Python) and model JSON (Python → Rust).

## Module map

Dependency sketch (arrows point at dependencies):

```
main.rs ─→ graph, greedy, beam, beam2, model, rollout, trace, validate
trace ───→ beam (Scorer), graph, walk
greedy ──→ walk ──→ bitset, bound, graph
rollout ─→ walk, bound, graph        (+ rand, serde_json)
beam ────→ bitset, bound, graph, model   (does NOT use walk — see Extension points)
beam2 ───→ beam (Jitter, splitmix), bitset, bound, graph (Preds), model
model ───→ (serde_json only; pure inference)
validate → graph (factorial, rank)
bound ───→ (serde only; pure arithmetic + Features struct)
graph ───→ bitset (w2_bridges_delta takes a visited BitSet)
bitset ──→ no crate deps
```

- **`src/bitset.rs`** — `BitSet`, a fixed-capacity bitset over `Box<[u64]>`.
  `new(nbits)`, `set(i)`, `get(i)`, `popcount()`, `first_clear(limit) -> Option<usize>`.
  Derives `Hash`/`Eq` so it can be part of the beam dedup key. Padding bits in the last
  word are never set, so word-wise equality/hash is sound for same-capacity sets.
- **`src/graph.rs`** — the permutation overlap graph. Free functions
  `factorial(n)`, `rank(perm: &[u8]) -> usize` (Lehmer rank), `unrank(n, rank) -> Vec<u8>`;
  `struct Graph` with `Graph::new(n)` (asserts `3..=8`) and the static helper
  `Graph::overlap(a, b) -> usize` (brute-force suffix/prefix overlap, used for path
  reconstruction and as the test oracle). Also `struct Preds` (`Preds::new(&Graph)`),
  weight-graded predecessor lists — the exact edge-set mirror of `succs` (`(p, w)` in
  `preds.lists[r]` iff `(r, w)` in `succs[p]`), same ordering guarantees with head =
  `pred1`. Built on demand by the two-ended searcher only; `Graph` itself stores just
  the O(1) `pred1` map. Phase-3 item 3 additions: `w2x`/`w2rev` (the unique
  *cross-cycle* weight-2 successor per rank — `P[2..] + P[1] + P[0]` — and its
  inverse; a bijection) and `Graph::w2_bridges_delta(visited, cycle_rem, q)`, the
  shared incremental update for the `w2_bridges` feature used by `Walk::advance`,
  the beam's `child_state`/`score_move`, and guided rollouts' `child_features`.
- **`src/bound.rs`** — `lower_bound(r, k, current_cycle_has_unvisited) -> usize`, the
  admissible bound `r + k − [current cycle has unvisited]` (THEORY.md §3);
  `lower_bound_arc(r, arcs, succ1_unvisited)`, the tighter arc bound
  `r + arcs − [succ1(cur) unvisited]` (admissibility proof in the module docs);
  `lower_bound_arc2(r, arcs, succ1_back_unvisited, pred1_front_unvisited)`, the
  two-ended arc bound `max(r, r + arcs − [succ1(back) unvisited] − [pred1(front)
  unvisited])` — admissible for the deque move set, proof sketch in the module docs
  (the `max` floor covers both free ends landing on the same arc; with the prepend
  side dead it reduces exactly to `lb_arc`); and `struct Features` (serde
  `Serialize`/`Deserialize`), the rollout JSONL record.
- **`src/walk.rs`** — `struct Walk<'g>`, the incremental search state shared by greedy
  and rollouts. `Walk::new(&Graph)`, `advance(rank, weight)`, `first_unvisited_succ()`,
  `unvisited_succs()`, `fallback_target()`, `lb()`, `features()`, `done()`,
  `len_chars()`, `string()`, `graph()`.
- **`src/greedy.rs`** — `greedy(&Graph) -> GreedyResult { string, len, path: Vec<u32> }`.
  Deterministic baseline; hits 9/33/153 for n=3,4,5 (hard invariant) and 873 for n=6.
- **`src/beam.rs`** — `beam_search(&Graph, width, Scorer) -> BeamResult { string, len,
  path }`. Level-synchronous beam search; `enum Scorer` selects `Bound(Bound::Cycle |
  Bound::Arc)` (score = `len + lb`) or `Learned { model: &Model, alpha }` (score =
  `len + α·predict(features)`, or `len + lb_arc + α·predict` when the model is
  residual-target — the anchor is added back in the scorer because the label had it
  subtracted; see JOURNAL s3 lesson 1). `beam_search_jittered(…, Option<Jitter>)` adds deterministic score
  jitter (`Jitter { eps, seed }`): a Zobrist hash of the visited set, maintained
  incrementally in each `State`, gives every candidate a pure-function-of-
  `(cur, visited, seed)` offset in `[0, eps)` — dedup-safe, and bit-identical to the
  plain search when off. `beam_search_seeded(…, Option<Jitter>, seed_prefix)` replays
  the first `seed_prefix` greedy moves through the beam's own counter updates to build
  the root state (`0` = bit-identical to the unseeded search; must be `< n! − 1`); the
  reported result includes the prefix. `beam_search_stratified(…, Option<Stratify>)`
  (+ `beam_search_stratified_cutoffs`) adds width reservation per structural class
  (phase-3 item 1): candidates are bucketed by the quantized deficit profile
  `(intact, half_open, nearly_done)` — `half_open` = cycles with exactly 1–2 visited
  members, `nearly_done` = cycles with exactly 1–2 unvisited members, both new
  O(1)-incremental `State` counters — and selection runs two passes over the globally
  sorted candidates: pass 1 keeps up to `Stratify::quota` best candidates per occupied
  bucket (counts divided by `Stratify::bucket` to form the key), pass 2 fills the rest
  of the width in global score order; kept states are re-sorted into global order.
  The dedup set spans both passes and the bucket key is a pure function of
  `(cur, visited)`, so the keep-first minimum-length argument is unchanged.
  `stratify = None` (and `quota = 0`) is bit-identical to the plain beam (pinned by
  test against pre-stratification output strings; CLI: `beam --stratify
  [--strat-quota Q --strat-bucket B]`). Private: `struct State`, `struct JitterCtx`,
  `fn score_move`, `fn child_arcs`, `fn child_state`, `fn bucket_key`.
- **`src/beam2.rs`** — two-ended (deque) beam search, phase-3 item 2's decision-order
  probe (NO-GO at n=6 but kept in-tree; recovers 33/153 — n=5 needs width ≥ ~1000).
  `beam2_search(&Graph, width, Scorer2, Option<Jitter>) -> Beam2Result { string, len,
  path, moves }` (`moves` = decision order as `(rank, prepended?)`; `path` = string
  order front→back). A state is a deque `(front, back, visited, len)`; a move appends
  an unvisited successor of `back` or prepends an unvisited predecessor of `front`
  (via `graph::Preds`, built once per search). `enum Scorer2`: `Arc2` (score =
  `len + lb_arc2`) or `Learned { model, alpha }` — a *transfer* scorer feeding the
  one-ended 8-feature contract computed relative to `back`. Structure mirrors
  `beam.rs` (level-synchronous, O(1) candidate scoring from parent counters, sort +
  keep-first dedup + width truncation, path arena) with two differences: the dedup
  key is `(front, back, visited)` — equal visited sets with different ends are
  genuinely distinct states — and every score must be a pure function of
  `(front, back, visited, len)`; the weight-`n` fallback fires only when *both* ends
  are stuck. Jitter reuses `beam::Jitter` with a `(front, back, visited)`-pure
  offset; ε=0 is bit-identical. Private: `struct State2` (the beam `State` counters
  plus `front`/`back` instead of `cur`), `Jitter2Ctx`, `score_move2`, `child_arcs2`.
- **`src/model.rs`** — `enum Model` (`Linear` | `Mlp`), loaded from JSON via
  `Model::load(path)` / `Model::from_json(text)`; `predict(&self, x: &[f64; 8]) -> f64`
  is pure CPU inference (dot product, or 2×64 MLP with ReLU); `n()` (the n the model
  was trained for; the CLI refuses a mismatched `-n`), `kind()`; `enum Target`
  (`Absolute` | `Residual`, from the optional `"target"` JSON field, serde-default
  absolute so old files load unchanged), exposed as `target()` / `is_residual()` —
  residual models predict `cost_to_go − lb_arc` and every scorer must add `lb_arc`
  back.
- **`src/rollout.rs`** — `run_rollouts(&Graph, count, epsilon, seed, out: &mut impl Write)
  -> io::Result<RolloutSummary { rollouts, mean_len, min_len, lines }>`. Epsilon-greedy
  rollouts emitting JSONL `Features` lines. `run_rollouts_guided(…, Option<Guide>, out)`
  with `Guide { model: &Model, alpha }` replaces the greedy exploit move by the argmin
  of `len + weight + α·predict(child features)` (+ child `lb_arc` for residual models)
  over unvisited successors, ties broken by the sorted successor order; the epsilon
  branch and RNG stream are untouched, so `None` is exactly `run_rollouts` and same
  seed ⇒ byte-identical output. Also `log_trajectory(&Graph, path, out)`,
  which replays a recorded visit-order path through a `Walk` and emits the identical
  record format (used by `greedy --log` / `beam --log`).
- **`src/trace.rs`** — trajectory extraction from existing superpermutation strings
  (e.g. community records): `extract_path(n, s)` (first-visit rank order via a sliding
  window), `trace_string(&Graph, s) -> Trace { path, weights, input_len, replay_len,
  hist }` (maximal-overlap replay through a `Walk`; `replay_len == input_len` certifies
  a tight string), `score_state(&Walk, Scorer)` (beam-exact fixed-point score of a
  state, comparable with `LevelCutoff` thresholds), and `score_trajectory(&Graph,
  path, Scorer) -> Vec<(step, len, score)>`.
- **`src/validate.rs`** — `validate(n, s: &str) -> Validation { n, length, distinct,
  total, complete }`. Sliding-window checker; the only accepted proof that a string is
  a superpermutation.
- **`src/main.rs`** — clap CLI (`struct Cli`, `enum Cmd`): subcommands `info`, `greedy`,
  `beam`, `beam2`, `trace`, `rollouts`, `validate`.

## Core data structures

### `Graph` (`src/graph.rs`)

| Field | Meaning |
|---|---|
| `n: usize` | symbol count (3..=8; symbols are `1..=n` as `u8`) |
| `nfact: usize` | `n!`, vertex count |
| `perms: Vec<Vec<u8>>` | `perms[r]` = permutation with lexicographic (Lehmer) rank `r` |
| `succs: Vec<Vec<(u32, u8)>>` | `succs[r]` = `(successor rank, weight)` pairs, weight `1..=n−1` |
| `cycle_id: Vec<u32>` | rotation-cycle (1-cycle) label per rank, in `0..cycle_count` |
| `cycle_count: usize` | `(n−1)!` |
| `pred1: Vec<u32>` | weight-1 predecessor (right rotation) per rank; inverts `succ1` |

Helper: `Graph::succ1(r)` = `succs[r][0].0`, the unique weight-1 successor.

Ordering guarantees on `succs[r]` (pinned by unit test
`successor_lists_sorted_by_weight_then_suffix`):

1. sorted by weight ascending, then lexicographically by the appended `w`-char suffix
   (generated directly in this order — `Graph::new` enumerates arrangements of `P[..w]`
   with `next_permutation`, never sorts);
2. `succs[r][0]` is always the unique weight-1 successor = left rotation, which stays in
   the same cycle (this is what makes `cycle_id` traceable and greedy's tie-break
   canonical);
3. there are exactly `Σ_{w=1}^{n−1} w!` entries, all distinct targets. **Weight-`n`
   edges (zero overlap) are not stored** — every searcher handles them via an explicit
   fallback jump to `visited.first_clear(nfact)`, the lowest-ranked unvisited perm.

Greedy's move rule "first unvisited entry of `succs[cur]`" therefore means: minimum
weight, ties broken by lexicographically smallest appended suffix. Reordering `succs`
changes greedy's output — a hard invariant (see Testing).

### `Walk` (`src/walk.rs`) — incrementally maintained fields

Starts at rank 0 (identity) with its `n` chars already emitted. Per `advance(rank, weight)`,
all of these update in O(1) or O(weight):

- `visited: BitSet` — set bit `rank`;
- `cycle_rem: Box<[u8]>` — unvisited count per cycle; decrement `cycle_rem[cycle_id[rank]]`;
- `k: usize` — cycles with ≥1 unvisited perm; decrement when a `cycle_rem` entry hits 0;
- `r: usize` — total unvisited perms; decrement;
- `arcs: usize` — weight-1 connected components (maximal unvisited rotation runs; a
  fully-unvisited cycle is one circular component): unchanged if the cycle was intact,
  else ±1/0 by the visited status of the two ring neighbors (`pred1`/`succ1`);
- `half_open` / `nearly_done: usize` — cycles with exactly 1–2 visited / 1–2 unvisited
  members, O(1) from the pre-decrement `cycle_rem` (phase-3 item 3);
- `w2_bridges: usize` — live cross-cycle weight-2 edges joining two partially-visited
  cycles, via `Graph::w2_bridges_delta` (O(1) per move, O(n) exactly when the move
  first touches an intact cycle — once per cycle, so O(1) amortized);
- `cur: u32` — rank the string currently ends with;
- `chars: Vec<u8>` — append the last `weight` symbols of the target perm (a
  `debug_assert_eq!` checks the overlap really matches);
- `steps: u32` — advances taken.

`lb()` = `lower_bound(r, k, cycle_rem[cycle_id[cur]] > 0)` — O(1); `lb_arc()` =
`lower_bound_arc(r, arcs, succ1_unvisited())` — O(1), dominates `lb()`.
`features()` is O(cycle_count) (scans `cycle_rem` for `intact_cycles`); it is only
called by the rollout generator, not in the greedy/beam hot path.

### Beam state, arena, dedup (`src/beam.rs`)

`State { cur, len, visited: BitSet, cycle_rem, k, r, arcs, intact, half_open,
nearly_done, w2_bridges, zhash, node }` mirrors `Walk`'s counters but without `chars`
— no state carries a string or path. `half_open` (cycles with exactly 1–2 *visited*
members) and `nearly_done` (exactly 1–2 *unvisited*) are the phase-3 item-1 counters
feeding the stratification bucket key; item 3 mirrored them (plus `w2_bridges`) into
`Walk`/`Features` and the v2 model contract. `zhash` is the Zobrist hash of the
visited set (0 when jitter is off), XOR-updated per move.

- **Scoring without materialization**: `score_move(g, parent, q, w, parent_idx)`
  computes the child's `(len + lb, len, q, parent_idx)` tuple in O(1) from the parent's
  `(len, r, k, cycle_rem)` — no clone. Candidates for a whole level are collected,
  `sort_unstable()`d (deterministic total order), then only the ≤ `width` survivors get
  their `visited`/`cycle_rem` cloned.
- **Dedup key**: `(cur: u32, visited: BitSet)` in a `HashSet`. For duplicate keys the
  lb is identical (it depends only on `cur` and `visited`), so keep-first after the
  `(score, len, …)` sort keeps the minimum length.
- **Path arena**: `arena: Vec<(parent_node: u32, rank: u32)>`, root = node 0 =
  `(u32::MAX, 0)`. Each surviving state pushes one node. After the final level the best
  state's chain is followed back to `u32::MAX`, reversed, and the string is rebuilt by
  maximal-overlap concatenation using `Graph::overlap` (a `debug_assert_eq!` checks the
  rebuilt length equals the tracked `len`).
- **Fallback**: a state whose stored successors are all visited emits one weight-`n`
  jump candidate instead of dying silently.
- Levels run `for _depth in 1..nfact` — every level visits exactly one more perm, so
  the final beam holds only complete walks (`debug_assert_eq!(best.r, 0)`).

## CLI subcommand data flow (`src/main.rs`)

All subcommands take `-n <3..=8>` and start with `Graph::new(n)`.

- **`info`** — builds the graph, prints `nfact`, `cycle_count`, an edge histogram by
  weight computed by scanning `g.succs`, and successors per perm. No search.
- **`greedy`** — `greedy(&g)` → prints `length` and the string. (Loop: `Walk::new` →
  `first_unvisited_succ()` else `(fallback_target(), n)` → `advance` until `done()`.)
  `--log <file>` writes the trajectory's `Features` JSONL via `log_trajectory`.
- **`beam`** — `beam_search_jittered(&g, width, scorer, jitter)` (default width 1000)
  → prints length, wall-clock seconds (`Instant`), and the string. Scorer selection:
  `--bound cycle|arc` (default cycle), or `--model ml/models/m.json --alpha a`
  (learned score `len + α·predict`, or `len + lb_arc + α·predict` for residual-target
  models; the model's stored `n` must match `-n`, default
  `--alpha 1`). `--jitter <eps> --jitter-seed <s>` enables deterministic score jitter
  (`--jitter 0` = off = bit-identical to plain search). `--seed-prefix <depth>`
  (default 0) replays that many greedy moves as the root state (rejected unless
  `< n! − 1`); composes with `--model`/`--alpha`/`--jitter`/`--bound`. `--stratify
  [--strat-quota Q --strat-bucket B]` (defaults 32 / 4) enables per-bucket width
  reservation (see `beam_search_stratified` above; off = bit-identical; the canonical
  from-scratch 873 uses `--strat-quota 4 --strat-bucket 1` with the learned scorer —
  empirically it *anti-composes* with `--jitter` and `--seed-prefix`, JOURNAL s7).
  `--log <file>`
  writes the best path's `Features` JSONL. `--cutoff-log <file>` records one TSV line
  per level (`level, kept, best_score, worst_kept_score` — the pruning threshold, in
  length units = fixed-point/4096) via `beam_search_cutoffs`; pure instrumentation,
  bit-identical search.
- **`beam2`** — `beam2_search(&g, width, scorer, jitter)` (default width 1000) →
  prints length, wall-clock seconds, prepend/move counts, and the string. Scorer:
  two-ended arc bound by default, or `--model <path> --alpha <a>` for the one-ended
  learned-transfer scorer (stored `n` must match `-n`). `--jitter <eps>
  --jitter-seed <s>` as in `beam`. No `--bound`, `--seed-prefix`, `--stratify`, or
  logging flags — the probe stayed minimal.
- **`rollouts`** — opens `--out` as `BufWriter<File>`, calls
  `run_rollouts_guided(&g, count, epsilon, seed, guide, &mut writer)` → prints
  count/epsilon/seed (and model kind/alpha when guided), mean and min final length,
  lines written. Defaults: `--count 100`, `--epsilon 0.1`, `--seed 0`; `--out` is
  required. `--model <path> --alpha <a>` (default 1) guides the exploit move with a
  learned model; the JSONL schema is unchanged.
- **`trace`** — reads `--file`, requires it to validate as complete, then
  `trace_string` → prints length/replay length/visits, the move-weight histogram, and
  the positions of weight ≥ 3 moves. `--log <file>` writes the trajectory's `Features`
  JSONL (via `log_trajectory`). With `--bound cycle|arc` or `--model <path> --alpha
  <a>` (mutually exclusive), `score_trajectory` scores every state exactly as the
  beam's `score_move` would; `--score-log <file>` writes them as TSV
  (`step, len, score`), otherwise they print to stdout.
- **`validate`** — string from positional arg or `--file` (mutually exclusive; file
  content is trimmed) → `validate(n, &s)` → prints length, `distinct / total`,
  `complete`. With `--complete`, exits nonzero unless complete.

## Rollout JSONL schema (`bound::Features`)

One JSON object per line, serialized by `serde_json` in field declaration order.
Per rollout: exactly `n!` lines (start state at `step: 0`, then one per `advance`).
Rollout `i` uses `StdRng::seed_from_u64(seed.wrapping_add(i))` — fully reproducible.
`cost_to_go` is backfilled after the rollout finishes: `final_len − len_so_far`
(so the last line of each rollout has `cost_to_go: 0` and `r: 0`).

| Field | Type | Meaning |
|---|---|---|
| `n` | u32 | symbol count |
| `step` | u32 | advances so far (= perms visited − 1) |
| `r` | u32 | unvisited perm count |
| `cycles_remaining` | u32 | cycles with ≥1 unvisited perm (`k`) |
| `intact_cycles` | u32 | cycles with all `n` members unvisited |
| `current_cycle_remaining` | u32 | unvisited members of the current perm's cycle |
| `arcs` | u32 | weight-1 components among unvisited perms (serde-default; absent pre-phase-2 files read as 0) |
| `succ1_unvisited` | u32 | 1 if `succ1(cur)` is unvisited (serde-default) |
| `half_open` | u32 | cycles with exactly 1–2 visited members (serde-default; phase-3 item 3) |
| `nearly_done` | u32 | cycles with exactly 1–2 unvisited members (serde-default; phase-3 item 3) |
| `w2_bridges` | u32 | live cross-cycle weight-2 edges joining two partially-visited cycles — both endpoints unvisited, both endpoint cycles with ≥ 1 visited member (serde-default; phase-3 item 3; see `Graph::w2_bridges_delta`) |
| `len_so_far` | u32 | characters emitted |
| `cost_to_go` | u32 | characters the rollout actually needed from here (the label) |

Sample line (n=4, epsilon=0, first record):

```json
{"n":4,"step":0,"r":23,"cycles_remaining":6,"intact_cycles":5,"current_cycle_remaining":3,"len_so_far":4,"cost_to_go":29}
```

**Backward-compatibility rule (hard invariant, CLAUDE.md)**: schema changes must be
backward compatible or version-bumped — trained models depend on this format. Adding a
field is fine (old readers using serde ignore unknown fields only if configured; ours
error on missing fields, so removals/renames break `Deserialize`); anything else needs
an explicit version marker.

## `ml/` — Python training side

Pure numpy (sklearn only for the optional GBT diagnostic); talks to Rust only through
files. The feature contract is **append-only and length-dispatched** (phase-3 item 3):
v1 (8 features) `r, cycles_remaining, intact_cycles, current_cycle_remaining, arcs,
succ1_unvisited, lb_cycle, lb_arc`; v2 (11) appends `half_open, nearly_done,
w2_bridges`. The bounds are recomputed from the raw fields in `ml/common.py`; the
deficit-distribution columns default to 0 for old-schema JSONL, so mixed corpora fit
cleanly. New exports declare the v2 order; a model consumes exactly the first
`len(feature_order)` entries of the full vector the scorers compute, so committed
8-feature models score **bit-identically** to the pre-phase-3 build (pinned by test).
Held-out split is by *rollout* (every 5th), never by row.

- **`common.py`** — JSONL loading, feature assembly, split, RMSE/MAE/R² metrics.
- **`fit_linear.py <data.jsonl>...`** — OLS baseline; prints held-out metrics vs. the
  two hand bounds as point predictors; exports the Rust JSON contract. `--residual`
  trains on `cost_to_go − lb_arc` and exports `"target": "residual"` (reported
  regressor metrics stay in absolute space for comparability).
- **`train_mlp.py`** — numpy MLP (8 → relu hidden layers → 1), Adam, early stopping;
  label standardization folded back into the last layer on export. `--residual` as in
  `fit_linear.py`.
- **`fit_gbt.py`** — sklearn HistGradientBoostingRegressor, *diagnostic only*: trees
  are not in the Rust model contract and cannot be exported to the beam.
- **`predict_check.py <model.json> <data.jsonl>...`** — evaluate any exported model
  on any corpus (bootstrap-round sanity check).

Model JSON contract (what `src/model.rs` parses):
`{"kind": "linear"|"mlp", "n": <trained n>, "feature_order": [8 or 11 names — exactly
`FEATURE_ORDER` or `FEATURE_ORDER_V2`], ...}` — linear
adds `coef` + `intercept`; mlp adds `x_mean`, `x_std`,
`layers: [{w, b, act: "relu"|"identity"}, ...]` (all sized to the declared feature
count). Optional
`"target": "absolute"|"residual"` (absent = absolute, so pre-residual files load
unchanged); residual models predict `cost_to_go − lb_arc` and scorers add the anchor
back. Canonical committed models live in
`ml/models/` (`linear_n6_boot1.json` and `linear_n6_blend0.075.json` are the two
874-hitters; sweep artifacts stay untracked). `data/` corpora are gitignored but
regenerable — every rollout seed is logged in JOURNAL entries.

## Extension points

Phase 2's original extension points (learned scorer in `score_move`, model loading,
`--model/--alpha` CLI) are **implemented** — see `src/model.rs` and `Scorer::Learned`
above — as are the three rung-1 attack mechanisms: **residual targets**
(`--residual` in `ml/fit_linear.py` / `ml/train_mlp.py`, `"target"` field in the
model contract, anchor re-added in `score_move` and `best_guided`), **model-guided
rollouts** (`run_rollouts_guided` / `rollouts --model --alpha`), and **greedy-prefix
seeding** (`beam_search_seeded` / `beam --seed-prefix`). Still-relevant places to
plug in:

- **Score-shape changes**: training-side in `ml/` (change the label), inference-side
  the score expression lives in `score_move`'s `Scorer::Learned` arm in `src/beam.rs`
  (the residual branch shows the pattern). The sort/dedup argument in
  `beam_search` requires every score be a pure function of `(cur, visited, len)` —
  the jitter offset and the `lb_arc` anchor show how to add variation without
  breaking it.
- **Where new incremental features live**: `Walk` in `src/walk.rs` (add the field,
  update it in `advance`, expose it in `features()`), **and also** `State` +
  `score_move` in `src/beam.rs` — beam does not use `Walk`; it duplicates the counter
  maintenance for O(1) candidate scoring — **and** `child_features` in
  `src/rollout.rs`, the `Walk`-side mirror used by guided rollouts. `src/beam2.rs`
  keeps a *third* copy (`State2`/`score_move2`); mirror a feature there only if the
  two-ended searcher should score with it, and keep it a pure function of
  `(front, back, visited)`. Keep them in sync, keep everything O(1)/O(n) per
  expansion, and extend the feature contract **append-only** in `ml/common.py` +
  `src/model.rs` (add the names to a new `FEATURE_ORDER_V<k>`, serde-default the JSONL
  field for backward compat — old models keep consuming their prefix). Precedent:
  item 3's deficit-distribution features (`half_open`/`nearly_done`/`w2_bridges`) are
  maintained in `Walk` AND beam `State` (v2 contract), but deliberately NOT in beam2's
  `State2` — the NO-GO probe rejects v2 models instead (see `Scorer2::Learned` docs).
- **Adding a CLI subcommand**: add a variant to `enum Cmd` in `src/main.rs` (clap
  derive) and a match arm in `main()`; put the logic in a library module and export it
  from `src/lib.rs`. Follow the existing pattern of printing a summary line then the
  payload.
- **Phase 3 status**: item 1 (stratified beam, `beam_search_stratified`) and item 2
  (two-ended beam, `src/beam2.rs` + `Preds` + `lb_arc2`) are built — see above. For
  item 5 (cycle-level search) nothing is built yet. The cycle machinery to build
  on: `Graph::cycle_id`/`cycle_count`, the arc-component maintenance in
  `Walk::advance`/`child_arcs`, and THEORY.md's 2-cycle/tree background. This is a new
  search representation (super-node graph over rotation cycles), not a patch to
  `beam_search`.

## Performance notes

- Per beam expansion: candidate scoring is O(1) (`score_move`); generating a state's
  candidates is O(Σ w!) ≈ O(succ-list length) with an O(nfact/64) `first_clear` only in
  the rare fallback. Per level: sort is O(C log C) over C ≈ beam·Σw! candidates; each
  *survivor* costs an O(nfact/64) `BitSet` clone + hash — cloning/hashing bitsets for
  the ≤ width survivors is the dominant per-level cost at large n (630 words at n=8).
  Total levels: `nfact − 1`.
- `Walk::advance` is O(weight) (append) + O(1) counters; `first_unvisited_succ` is
  O(succ-list) worst case; `unvisited_succs` (rollouts only) allocates a Vec per step.
  `Walk::features` is O(cycle_count) — fine for rollouts, don't call it per-candidate
  in beam.
- `Graph::new` is O(nfact · Σw! · n) time and memory — fine up to n=8 (40320 vertices,
  5913 successors each); build it once and share `&Graph`.
- **Always run searches with `--release`**: debug builds are ~50× slower in the hot
  loop (CLAUDE.md), and the release profile enables `lto = true`,
  `codegen-units = 1` (`Cargo.toml`). Debug-only `debug_assert!`s in `Walk::advance`
  and `beam_search` also vanish in release.
- Known micro-wart: in `beam_search`'s survivor loop the surviving `visited` bitset is
  cloned twice (`key.1.clone()` after moving it into the dedup key).

## Testing

Unit tests live in each module (`graph.rs`: rank/unrank roundtrip, successor counts,
sort order, brute-force weight oracle at n=4, cycle partition; `bitset.rs`; `bound.rs`;
`walk.rs`; `validate.rs`). Integration tests in `tests/known_optima.rs` pin:

- `greedy_hits_known_optima` — greedy length is exactly 9/33/153 for n=3/4/5, the
  output validates as complete, and `path.len() == nfact`.
- `greedy_n6_is_sum_of_factorials_873` — greedy at n=6 is exactly 873, validated.
- `beam_n4_width_512_is_optimal_under_both_bounds` / 
  `beam_n5_width_2000_is_optimal_under_both_bounds` — beam reaches 33 (n=4) and
  153 (n=5) under both the cycle and arc bounds, validated.
- `lower_bound_admissible_at_start_n4` — fresh-state `lb ≤ 33 − 4`.
- `lower_bound_never_exceeds_cost_to_go_on_greedy_trajectory_n4` — replays the greedy
  n=4 path through a `Walk`, asserting `lb ≤ actual remaining cost` at every step and
  `lb == 0` at the end.
- `validator_rejects_non_superperm` — incomplete and degenerate strings fail.
- `rollouts_deterministic_and_consistent` — same seed ⇒ byte-identical output; `n!`
  lines per rollout; every line round-trips through `Features`; `len_so_far +
  cost_to_go` is constant within a rollout with final `cost_to_go == 0`; epsilon=0
  reproduces the greedy length.
- `log_trajectory_matches_epsilon0_rollout` — `--log` replay is byte-identical to the
  ε=0 rollout records.
- `learned_lb_arc_model_reproduces_arc_bound_beam` — a linear model whose coefficients
  encode exactly `lb_arc` makes `Scorer::Learned` reproduce the arc-bound beam's
  result (pins the feature order and the score arithmetic).
- `residual_zero_model_reproduces_arc_bound_beam` — an all-zero residual-target model
  scores `len + lb_arc + 0`, so it must reproduce the arc-bound beam bit for bit
  (pins the residual score arithmetic).
- `guided_rollouts_deterministic_and_consistent` — model-guided rollouts are
  byte-identical for a fixed seed (ε = 0 and ε > 0), labels stay consistent, and the
  absolute lb_arc model agrees move-for-move with the residual zero model.
- `seed_prefix_zero_is_identity` / `seed_prefix_deep_n5_still_valid` /
  `seed_prefix_mid_depth_n5_width_2000_still_153` — depth 0 is bit-identical to the
  plain beam; a near-full greedy prefix still yields a valid complete result whose
  path starts with the prefix; a depth-60 prefix at n=5/width 2000 still finds 153.
- `jittered_beam_n4_still_optimal_and_zero_jitter_is_identity` — jitter ε=0 is
  bit-identical to the plain search; small jitter still finds 33 at n=4.
- `beam_path_replays_to_reported_length` — arena-reconstructed path really has the
  reported length.
- Stratification (phase-3 item 1):
  `stratify_off_is_bit_identical_to_pre_stratification_beam` — `stratify = None` and
  `quota = 0` reproduce the pre-stratification output strings byte for byte (pinned
  against commit 9b03761); `stratified_beam_gates_still_optimal` — 33/153 still found
  with stratification on; `stratified_selection_reserves_beyond_plain_cutoff` — the
  quota pass really keeps states the plain cutoff would prune.
- `tests/two_ended.rs` (phase-3 item 2, 7 tests) — `beam2` recovers 9/33/153
  (n=5 at width 2000, where the winner genuinely uses prepends); `lb_arc2`
  admissibility oracle-tested along random deque walks at n=4; deque reconstruction
  matches tracked lengths; jitter ε=0 identity; every perm visited exactly once.

**Hard invariants** (CLAUDE.md): greedy must keep producing 9/33/153 — if a
graph/ordering refactor changes those numbers, the refactor is wrong, not the test;
the lower bound must stay admissible; every reported string must pass `validate`.
Run `cargo test --release` (the beam tests are slow in debug).
