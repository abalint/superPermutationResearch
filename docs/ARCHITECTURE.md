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
greedy ──→ walk ──→ state ──→ bitset, bound, graph, lb_residual
rollout ─→ walk, state, bound, graph  (+ rand, serde_json)
beam ────→ state, bitset, bound, graph, model
beam2 ───→ state, beam (Jitter, splitmix), bitset, bound, graph (Preds), model
sojourn ─→ state (CycleState), graph
unionsearch → state (CycleState), corpus, graph, lb_residual
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
  shared incremental update for the `w2_bridges` feature, called from the single
  rule `SearchState::child_w2_bridges` in `src/state.rs`.
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
- **`src/state.rs`** — **the shared incremental search state (s64 P3): one definition
  of every counter update rule in the crate.** `struct CycleState` (visited set,
  per-cycle unvisited counts, `cur`, `len`, `k`, `r`, `intact` and the residual bound's
  `door`/`long`) is embedded by *every* engine — `Walk`, the beam's `State`, beam2's
  `State2`, the sojourn DFS's `State` and the union DFS's `UnionState`.
  `struct SearchState` = `CycleState` + the beam-family counters (`arcs`, `half_open`,
  `nearly_done`, `w2_bridges`, `steps`) and is embedded by `Walk`/`State`/`State2`.
  Three ways to apply the same rules: `visit`/`advance` (in place — walk, sojourn,
  union DFS), `child(…, Cursor, Residual)` (build a child from a parent plus an
  already-cloned visited set — the beams), and the individual `child_*` readers
  (`child_arcs`, `child_k`, `child_intact`, `child_cur_rem`, `child_rem_of`,
  `child_half_open`, `child_nearly_done`, `child_w2_bridges`,
  `child_deficit_profile`, `child_residual`), which give one child counter in O(1)
  from the parent's cached values *without materializing the child* — what beam
  candidate scoring, `bucket_key` and the feature vectors call. `Cursor::Onto` is an
  append/one-ended move; `Cursor::Keep` is beam2's prepend (the current permutation
  stays standable — its residual transition is `lb_residual::child_terms_keeping_cur`).
  `SearchState::recount` recomputes all fourteen counters from scratch and is the
  reference implementation the four drift tests compare against.
- **`src/walk.rs`** — `struct Walk<'g>`, the incremental search state shared by greedy
  and rollouts: the shared `SearchState` (field `st`) plus the emitted `chars`.
  `Walk::new(&Graph)`, `advance(rank, weight)`, `first_unvisited_succ()`,
  `unvisited_succs()`, `fallback_target()`, `cur()`, `steps()`, `lb()`, `features()`,
  `done()`, `len_chars()`, `string()`, `graph()`.
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
  members, `nearly_done` = cycles with exactly 1–2 unvisited members, both
  O(1)-incremental shared counters — and selection runs two passes over the globally
  sorted candidates: pass 1 keeps up to `Stratify::quota` best candidates per occupied
  bucket (counts divided by `Stratify::bucket` to form the key), pass 2 fills the rest
  of the width in global score order; kept states are re-sorted into global order.
  The dedup set spans both passes and the bucket key is a pure function of
  `(cur, visited)`, so the keep-first minimum-length argument is unchanged.
  `stratify = None` (and `quota = 0`) is bit-identical to the plain beam (pinned by
  test against pre-stratification output strings; CLI: `beam --stratify
  [--strat-quota Q --strat-bucket B]`). Private: `struct State` (= the shared
  `SearchState` + `zhash` + arena `node`), `struct JitterCtx`, `fn score_move`,
  `fn child_state`, `fn bucket_key` — the last three all read the shared `child_*`
  rules of `src/state.rs` rather than re-deriving them (s64 P3).
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
  offset; ε=0 is bit-identical. Private: `struct State2` (the shared `SearchState`,
  whose `cur` is this searcher's `back`, plus `front`, `zhash` and the arena node),
  `Jitter2Ctx`, `score_move2`. Since s64 P3 `State2` maintains **all fourteen**
  counters — before that it dropped `half_open`, `nearly_done`, `w2_bridges`, `door`
  and `long`, so beam2 could not score with the deficit features or the residual
  bound at all. The five recovered counters are maintained but **not scored with**:
  enabling them is a future decision, and the probe's output is unchanged (pinned).
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
- **`src/sojourn.rs`** — Track B's L2 sojourn-level canonical opening DFS (s22):
  `SojournDfs { g, caps: ClassCaps, profile: Option<SplitProfile>, depth,
  max_nodes, dedup: DedupMode, exemplars_per_class }.run() -> DfsStats`. Its
  `State` = the shared `CycleState` (`src/state.rs` — visited `BitSet`,
  `cycle_rem`, `cur`, `len`, `k`, `r`, and `intact`, which this searcher's
  feasibility test calls *untouched*) plus the sojourn ledger
  `(s, d3, d4, d5, ip)`, per-cycle `PackedParts` (3 bits per completed part) and
  `cur_part`. Moves = T0 canonical grammar; door
  legality uses `build_interiors(&Graph)` (interior perm windows per w≥3 edge,
  the emergent-edge filter). Dedup tiers documented on `DedupMode` (exact /
  orbit via the O(1) cur-inverse relabeling / abstraction with exemplar cap).
  s25: the move generator is factored into `Grammar { g, caps, profile,
  fresh_doors, interiors }` (`root(track_path)` / `children(&State) ->
  Vec<(SojournMove, State)>` / `feasible`) — the ONE source of legal moves,
  shared by the DFS and the NRPA rollouts; `children` preserves the DFS push
  order exactly (exemplar caps are order-sensitive; the M2 pin reproduces).
  s27: profiles load from census files (`SplitProfile::from_file`,
  `--profile-file`, per-allocation data in `analysis/trackb/profiles/`);
  `Grammar::replay(&[u32]) -> usize` is the public replay instrument behind
  the `grammar-check` subcommand (corpus-validated 22,062/22,062);
  `fresh_doors` = the s27 corpus law (heavy doors open untouched cycles
  only; opt-in, calibrated-not-proven, pinned in `tests/alloc_grammar.rs`).
- **`src/nrpa.rs`** — NRPA over the sojourn grammar (s25, TRACKB §4 step 4a):
  `nrpa_search(&NrpaCfg) -> NrpaResult`. Softmax policy = `HashMap<u64, f64>`
  over three feature codes per move (species / door context / exact `(cur,
  target)` identity, splitmix-hashed); nested adapt-toward-best (Rosin),
  replay-based `adapt` (+α chosen, −α·softmax all legal, prior included in
  the gradient). Rollouts hand off to
  `beam_search_multi_seeded_capped` at `switch_depth` visited perms; knobs
  that are load-bearing (all measured s25): `prior` (−β·waste logit bias —
  without it n=5 needs 5× the rollouts), `early_tail` (dead-ends complete via
  the unconstrained tail; without it the records class gives zero gradient),
  `warm_start`/`warm_reps` (policy pre-adapted toward record move sequences —
  cold start plateaus at 883, warm start re-derives 872), `collect_max` (all
  distinct completions ≤ L). Deterministic per `seed` (`StdRng`); depth
  telemetry (min/mean/max hand-off depth) in every result.
- **`src/corpus.rs`** — record corpus loading (s26, RECOMB-DESIGN §3):
  `load_corpus(&Graph, &[&Path]) -> Result<Vec<CorpusRecord { name, string,
  trace }>, String>`. Deterministic (sorted per-dir), skips non-record files,
  HARD-ERRORS on untight/incomplete records, dedups byte-identical strings.
  Shared by `recomb` and `unionsearch`.
- **`src/recomb.rs`** — record-pair splice closure (s26, RECOMB-DESIGN §4):
  `Braid::build(&Graph, &[CorpusRecord])` glues all record paths into the
  braid state-DAG (node = (visited BitSet, cur), edge = record step, layered
  by popcount); `braid.probe(corpus, max_walks) -> BraidResult` counts
  root→terminal paths (u128, overflow = error), enumerates the closure when
  small, validates + dedups hybrids, and reports junction histograms +
  segment provenance. Scales: 22,062 walks → 10M states in 16 s. Also
  `fnv1a64` (stable hash for emitted file names). s26b verdict: the
  community corpus is splice-closed up to relabel+reversal.
- **`src/unionsearch.rs`** — exhaustive DFS inside the corpus edge union
  (s26, RECOMB-DESIGN §5/§8.2): `UnionSearch::new(&Graph, corpus, UnionCfg
  { cap, bound, tt, tt_max, free, free_w, max_nodes }).run() -> UnionResult`.
  `UnionState` = the shared `CycleState` (`src/state.rs`, residual terms
  included) driven by `visit`/`unvisit` with an undo trail for the two
  non-invertible terms, usage-ordered adjacency, `--tt`
  decision mode (exact keys; sound for existence/optimality only), `--free`
  off-union credits, and the STRAND prune (`live_in[q]` = unvisited union
  in-neighbours; lossless — records never strand; 2× the bound's prune rate,
  6× throughput). Honest COMPLETE/TRUNCATED verdicts. Measured s26: union
  enumeration is intractable even for 2-record unions; TT fires zero times
  at n=6 — leave it off.
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
- **`src/main.rs`** — clap CLI (`struct Cli`, `enum Cmd`): subcommands `info`, `atlas`,
  `sojourn-dfs`, `nrpa`, `grammar-check`, `recomb`, `union-dfs`, `greedy`, `beam`,
  `beam2`, `trace`, `endgame`, `rollouts`, `cert-verify`, `validate`.

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

### The incremental counters (`src/state.rs`) — one rule each

Starts at rank 0 (identity) with its `n` chars already emitted. Per move all of these
update in O(1) or O(weight), in `CycleState::visit` / `SearchState::advance` (in
place) or `…::child` (parent → child), from the same `child_*` rules the beams read
for candidate scoring:

- `visited: BitSet` — set bit `rank`;
- `cycle_rem: Box<[u8]>` — unvisited count per cycle; decrement `cycle_rem[cycle_id[rank]]`;
- `k: u32` — cycles with ≥1 unvisited perm; decrement when a `cycle_rem` entry hits 0;
- `r: u32` — total unvisited perms; decrement;
- `intact: u32` — cycles with all `n` members unvisited; decrement iff the move's
  cycle was intact (the sojourn DFS calls this quantity `untouched`);
- `door` / `long: u32` — the residual bound's terms, maintained only when a
  `PredTable` is supplied (`lb_residual::ParentCtx` + `child_terms`, or
  `child_terms_keeping_cur` for a two-ended prepend); 0 otherwise;
- `arcs: u32` — weight-1 connected components (maximal unvisited rotation runs; a
  fully-unvisited cycle is one circular component): unchanged if the cycle was intact,
  else ±1/0 by the visited status of the two ring neighbors (`pred1`/`succ1`);
- `half_open` / `nearly_done: u32` — cycles with exactly 1–2 visited / 1–2 unvisited
  members, O(1) from the pre-decrement `cycle_rem` (phase-3 item 3);
- `w2_bridges: u32` — live cross-cycle weight-2 edges joining two partially-visited
  cycles, via `Graph::w2_bridges_delta` (O(1) per move, O(n) exactly when the move
  first touches an intact cycle — once per cycle, so O(1) amortized);
- `cur: u32` — rank the string currently ends with (the *appending* end in beam2);
- `len: u32` — characters emitted (`Walk` additionally keeps `chars: Vec<u8>`, with a
  `debug_assert_eq!` that the overlap really matches);
- `steps: u32` — moves taken.

`Walk::lb()` = `lower_bound(r, k, cycle_rem[cycle_id[cur]] > 0)` — O(1); `lb_arc()` =
`lower_bound_arc(r, arcs, succ1_unvisited())` — O(1), dominates `lb()`;
`lb_residual()` = `r + door + intact + long`, dominating both. `features()` is O(1)
(every field is cached); it is only called by the rollout generator, not in the
greedy/beam hot path.

### Beam state, arena, dedup (`src/beam.rs`)

`State { st: SearchState, zhash, node }` — since s64 P3 the counters *are* the shared
`SearchState` (`src/state.rs`), not a second copy of it; the beam adds only the
Zobrist hash of the visited set (0 when jitter is off, XOR-updated per move) and the
arena index. No state carries a string or path. `half_open` (cycles with exactly 1–2
*visited* members) and `nearly_done` (exactly 1–2 *unvisited*) are the phase-3 item-1
counters feeding the stratification bucket key — `bucket_key` reads them through
`SearchState::child_deficit_profile` instead of re-deriving the arithmetic, as do
`score_move` and `model_pred`.

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

## `pylib/` — the tracked Python instrument layer (s64 P1)

**Package home: `pylib/` at the repo root. Its copies are CANONICAL; the
`out/sNN` originals are FROZEN history and must stay byte-untouched.**
(Andrew's decision, s64; `docs/REFACTOR-BRIEF.md` §3 P1. Full detail and
the promotion table live in `pylib/README.md`.)

Before s64 the Python side was 387 files, 24% tracked, zero packages,
zero `__init__.py`, and 275 `sys.path` mutation sites — with ~1,940
lines of engine-grade instruments sitting in gitignored `out/`, two of
them hard-imported by tracked, farm-launched code. P1 promoted them by
copy into `pylib/` and pointed all tracked code at the package.

- **Promoted instruments** (byte copies + a provenance header naming the
  origin): `lib62`, `cover_search`, `mcover_search`, `verify_master`
  (from `out/s62/jtax/`), `dlxrun` (`out/s57/proposer/`), `symlib`
  (`out/s60/retrieval/`), `cutlib` (`out/s60/nogood/`), `anatlib`
  (`out/s61/anatomy/`), `paircuts` (`analysis/counting/s58/`), `chain7`
  (`analysis/cover7/`). The only divergences from the originals are
  import mechanics (`REPO` was computed three levels down; `pylib/` is
  one), each stated in the file's own header.
- **`pylib/walkio.py`** — the single `first_visit_path` (was 6 copies),
  `renumber` (6), `weight` (3), plus `first_visit_starts`, `overlap`,
  `rot`, `rotc`, `g`, `lam` and corpus loading.
- **`pylib/canonical.py`** — **both** `canon` semantics, under distinct
  names, because `canon` was overloaded across 17 definitions in two
  incompatible meanings: `canon_rotation` (least cyclic rotation —
  kernelchain/certificate frame, ships with `door`/`tv`/`inverse_tv`/
  `loop_of`) and `canon_relabel_rev` (`min(renumber(s),
  renumber(reverse(s)))` — the M3 class representative that every
  committed `*_canon_index.tsv` is keyed by). No bare `canon` is
  exported. Also `h12`/`hash12`.

### The import mechanism (use this, nothing else)

Scripts run as plain files from arbitrary depths, so Python puts the
*script's* directory on `sys.path`, never the repo root. Every entry
script carries exactly ONE line, identical everywhere — this is the only
sanctioned `sys.path` text in `analysis/` and `ml/`:

```python
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
```

It is depth-independent and cwd-independent (the old spellings included
`sys.path.insert(0, 'analysis/counting')`, which silently required the
repo root as cwd). Everything downstream goes through the package:

```python
import pylib
pylib.add_paths("analysis/counting")   # repo-relative, idempotent, front-inserted
pylib.add_legacy_paths()               # prefixlib / p1a_assume / certificate / gain1
from pylib.walkio import first_visit_path, weight
from pylib.canonical import canon_relabel_rev
```

Importing `pylib` puts the repo root and `pylib/` itself on `sys.path`,
so the promoted instruments' flat imports (`import lib62`, `import
chain7`) resolve to the promoted copies — `add_legacy_paths()`
deliberately re-prepends `pylib/` last so the frozen `out/` copies can
never win.

Still reached through `add_legacy_paths()` because P1 did not promote
them: `prefixlib` (`out/s59/prefix`), `p1a_assume` (`out/s56/p1a`), and
`certificate`/`gain1`, which live **outside this repo** in the sibling
`../extraDocs/superpermutation-examples/scripts` checkout — a hard
external dependency of the whole n=7 stack, since `chain7` imports
`certificate`.

Two exceptions keep their own probe and are NOT bootstrapped: the farm
shims `analysis/farm/{i4a,lswap,promote}_shim.py` search a
two-candidate farm layout (`$ROOT\repo\...` vs a Mac checkout) that the
repo-root walk cannot express. `mc28_shim.py` keeps the same probe shape
but now points it at `repo\pylib` instead of `repo\out\s62\jtax`, and
`mc28_ship.sh`/`mc28_env.ps1`/`mc28_fetch.sh` ship and hash the payload
from `pylib/` to match.

### `tests_py/` — the Python control suite (s64 P2)

`pytest.ini` (rootdir config, `testpaths = tests_py`) + `tests_py/`.
It **converts the repo's 31 hand-run control scripts into asserts and
invents no oracle**: every expected value is a §6 pin from
`out/s64/refactor/pins_before/MANIFEST.md`, or was derived by running the
shipped code. Instruments are driven through their real CLIs with
`subprocess` (`tests_py/conftest.py::run`), never imported and patched,
so wrapping cannot change what is under test. `out/` is gitignored, so
controls needing untracked inputs are wrapped in `conftest.needs(...)` —
a clean checkout is green **with skips**, never with errors.

- **fast tier** (`python3 -m pytest tests_py/`, ~60 s): the jtax pins
  (`test_pins_jtax.py`), the M3 gate and the tracked oracles
  (`test_controls_tracked.py`), the P1 merge units incl. the
  canonicalizer/`*_canon_index.tsv` agreement (`test_pylib_units.py`),
  the local-only s63 controls (`test_controls_out_local.py`), and the
  **determinism guard** (`test_determinism.py`).
- **slow tier** (`-m slow`, deselected by `addopts`): the s63 singleton
  fixpoint — its fixture backs up `out/s63/chains/singleton_farm0.json`,
  restores the original bytes and asserts the MANIFEST's sha1, because
  `out/sNN` is frozen — and the 36,304,934-node rung-869 two-engine
  parity pair.
- **the determinism guard** runs each DFS engine twice under
  `PYTHONHASHSEED=0` and `=1` and demands identical stdout (only
  wall-clock tokens normalized). Python randomizes `str.__hash__` per
  process, so set/dict iteration order over strings differs run to run:
  that is exactly the s63 cutconvert bug, generalized. Since
  REFACTOR-BRIEF §0 makes byte-identical replay the acceptance bar for
  every stage, this guard is load-bearing for every other pin.
- **`scripts/check.sh`** runs `cargo test --release` + the fast tier and
  exits non-zero on either failure (`--rust` / `--py` to run one side).
  Written for bash 3.2, the version the Mac ships.

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
- **Where new incremental features live**: `src/state.rs`, **once** (s64 P3 — there
  used to be five copies of the counters and their update rules, plus two more
  re-derivations inside `score_move`/`bucket_key`). Add the field to `CycleState` (if
  every engine needs it) or `SearchState`, write its rule as one `child_*` reader,
  apply that reader in `visit`/`advance` *and* `child`, extend `recount` with the
  from-scratch definition (the four drift tests then cover it automatically), and
  expose it in `Walk::features()` if it is a model feature. Consumers read the cached
  value or call the reader — never re-derive the arithmetic: that is exactly the
  duplication this module removed. Keep everything O(1)/O(n) per expansion, and extend
  the feature contract **append-only** in `ml/common.py` + `src/model.rs` (add the
  names to a new `FEATURE_ORDER_V<k>`, serde-default the JSONL field for backward
  compat — old models keep consuming their prefix). Note the *scoring* question is
  separate from the *maintenance* question: beam2 now maintains all fourteen counters
  (including the residual terms, relative to its appending end) but still scores with
  the 8-feature contract only — enabling v2/residual scoring there is a deliberate
  future change, not a side effect (see `Scorer2::Learned` docs).
- **Adding a CLI subcommand**: add a variant to `enum Cmd` in `src/main.rs` (clap
  derive) and a match arm in `main()`; put the logic in a library module and export it
  from `src/lib.rs`. Follow the existing pattern of printing a summary line then the
  payload.
- **Phase 3 status**: item 1 (stratified beam, `beam_search_stratified`), item 2
  (two-ended beam, `src/beam2.rs` + `Preds` + `lb_arc2`), and item 4 (endgame
  tablebase, `src/endgame.rs::solve_endgame` — theorem-grade, m ≤ 25, use it as
  the terminal solver in any new searcher) are built — see above. Item 5 split
  into Tracks A/B/C; the sojourn/cycle-level machinery now lives in
  `src/sojourn.rs` (exhaustive DFS, s22) and `src/nrpa.rs` (policy search,
  s25), both driving the shared `Grammar` move generator.

## Track B implementation map (`docs/TRACKB-DESIGN.md`; s22 status inline)

Where each §9 build-order task lands. New analysis code goes in `analysis/trackb/`;
new Rust search code follows the beam2 precedent — own state type and
module, do NOT patch `beam_search`.

- **T0 — DONE s22** (`analysis/trackb/verify_identity.py`, 806 walks, zero
  exceptions). Works on the string's first-visit reading. Established the
  general identity `waste = (S−1) + Σ_{w≥3}(w−2)·inter[w] + Σ_{w≥2}(w−1)·intra[w]`
  and the canonical-reading lemma (skips pass only visited members). Rollout
  strings come from `rollouts --strings <path>` (added s22, RNG-stream
  neutral).
- **L0 class ledger — DONE s22** (`analysis/trackb/enumerate_l0.py` →
  `ledger_l0.csv`, 34,272 live-shell rows; tuple extended to
  `(S, d3, d4, d5, d6, ip)` per T0). Closures: LB-869 floor + the pass-over
  lemma `ip ≤ 4(S−120)` (proof + brute-force self-check in the script).
  M1 PASS (66.5%). L1 refinement (per-class split profiles) not yet built.
- **T1 — door atlas — DONE s22**: `atlas` subcommand dumps all 720×150
  w≥3 edges (cycle labels, offsets, interior permutation windows);
  `analysis/trackb/door_atlas.py` verifies the relabeling-orbit structure and
  emits `door_atlas_canonical.tsv` (150 canonical edges). The weight-2 facts
  stay theorem-level (i2 + `w2x` only).
- **L2 — sojourn DFS — BUILT s22** (`src/sojourn.rs`, `sojourn-dfs`
  subcommand): `State` = `(cur, visited BitSet, ledger, per-cycle packed part
  compositions, cur_part, cycle_rem, untouched)`; moves = T0 canonical grammar
  (ride / skip with pass-over legality / doors with the emergent-edge interior
  filter via `build_interiors`); pruning = class caps + owed-sojourn
  completability (`SplitProfile`-aware). Three dedup tiers (`DedupMode`):
  `Exact` (sound), `Orbit` (sound relabeling quotient; measured worthless —
  identity start breaks the symmetry), `Abstraction` (L2 canonical key +
  per-class exemplar cap `--exemplars`; book mode, not exhaustion-sound).
  M2 PASS in book mode (d=10, E=16, 746k nodes, 13,527 classes); exact tier
  sound to d≈6 (5.9M nodes). s23: `--dump-frontier <tsv> --dump-per-class K`
  emits ≤ K frontier exemplars per canonical class with their first-visit
  rank paths (`FrontierSeed`; states carry paths only when dumping). NOT yet
  wired: residual-bound pruning (`len + bound > 725 + 146` — waits on T2).
- **NRPA rollout engine — BUILT s25** (`src/nrpa.rs`, `nrpa` subcommand; see
  the module list above for the full knob inventory). Verdicts: n=5 control
  PASS (153, 100 rollouts, prior=1); n=6 cold start plateaus at 883 (no
  gradient across the s23 blocked zone — depth stalls ~85/450); record
  warm-start re-derives 872 end-to-end (byte-identical to seed, rollout 1);
  hunt design must be cap 874 + collect ≤872 (cap-at-target starves the
  gradient). M3 (byte-distinct ≤872) OPEN — next: neighborhood diversity,
  record bandit, warm-depth curriculum (JOURNAL s25).
- **T2 — DONE s24**, two pieces. (a) `Scorer::Composed { bound, model,
  alpha }`: score = `len + lb(bound) + α·pred` (`model_pred` shared with the
  `Learned` arm; still a pure function of `(cur, visited, len)`); CLI
  `--bound` is now optional and composes with `--model`. Pinned: α=0 ≡ the
  bare bound; `Composed{Arc}` + residual-target model ≡ `Learned`.
  (b) admissible cap `beam --max-len L` (`beam_search[_multi_seeded]_capped`
  → `Option<BeamResult>`): candidates with `len + lb > L` are discarded —
  lossless within the cap; the beam can die honestly. Best completion
  config: `--bound residual --model linear_n6_res_boot1 --alpha 0.25`
  (pipeline 879 → 874, s24); the capped beam from depth ≥ ~450 is a fast
  exact-target completion oracle (0.16–10 s) for NRPA tails.
- **T3 — `--seed-file` — DONE s23** (`src/beam.rs::SeedSpec`,
  `beam_search_multi_seeded[_endgame]`): one root state per walk, replayed
  via `replay_walk` (the extracted greedy-prefix replay) and injected into
  the level-synchronous loop at its own depth (`pending` map keyed by
  visited count); arena chains hang off node 0 so reconstruction, dedup,
  stratify, jitter, and the endgame snapshot compose unchanged. A one-walk
  greedy prefix is bit-identical to `--seed-prefix` (pinned).
  `analysis/trackb/record_to_seed.py` converts any superperm string into
  seed lines (relabeled first-visit rank path).
- **Structural recombination — BUILT AND CLOSED s26** (`src/corpus.rs`,
  `src/recomb.rs`, `src/unionsearch.rs`; see the module list above and
  RECOMB-DESIGN §8): splice closure delivered exactly (+2 hybrids — s26b:
  both rediscoveries, byte-identical to community strings); union DFS built
  with the strand prune but enumeration/decision both bound-blocked. The
  probes are CLOSED as discovery instruments; `recomb` re-runs on corpus
  growth, and `Braid`/`load_corpus` are reusable substrate.
- **s26c recalibration (affects every row above):** the community corpus is
  22,062 relabel+reversal classes (`data/upstream872/`, gitignored archive;
  census tools `analysis/counting/upstream872_*.py`). Exactly 8
  specimen-backed L0 allocations (records class = 95.8%; w4-bearing 872s
  exist, S down to 135), 8 Vlad cells (1:1), 545 split profiles, split
  types `1|5`/`5|1` observed. `ClassCaps`/`SplitProfile::records_n6` and
  every grammar-scoped verdict (M2, C1, NRPA) cover ONLY the records
  class; s27 direction: per-allocation caps + profiles as data from the
  census TSV, cross-class door pricing from the 918 non-records specimens.
  M3 independence is judged vs the 22,062 classes up to equivalence.
- **Gates before any 871 hunting** (TRACKB-DESIGN §6): C1 — re-find a validated
  872 from the records' own class (S=145, #w3=3, 25 splits); C2 — the n=5
  pipeline still finds 153 (hard invariant); M2 — d=10 canonical exhaustion of
  the records' class within ~10⁶ nodes. M3 (independent 872 or out-of-grammar
  ≤ 873) gates farm spend. s23 status: C2 PASS (153 validated, all bounds;
  needs exact dedup + ≥64 exemplars/class — abstraction-tier 1/class gives
  154); C1 oracle PASS (byte-identical 872 from its own prefix at depth
  ≥ 450, residual w32000 + endgame; ≥ 500 at w8000) but pipeline NOT PASSED —
  879 vs a measured 878 ceiling from even the TRUE opening at d=14; blocked
  on beam completion through levels ~60–450, residual bound the best
  completion scorer (learned+stratify is 15–30 chars worse there).

## Performance notes

- Per beam expansion: candidate scoring is O(1) (`score_move`); generating a state's
  candidates is O(Σ w!) ≈ O(succ-list length) with an O(nfact/64) `first_clear` only in
  the rare fallback. Per level: sort is O(C log C) over C ≈ beam·Σw! candidates; each
  *survivor* costs an O(nfact/64) `BitSet` clone + hash — cloning/hashing bitsets for
  the ≤ width survivors is the dominant per-level cost at large n (630 words at n=8).
  Total levels: `nfact − 1`.
- `Walk::advance` is O(weight) (append) + O(1) counters; `first_unvisited_succ` is
  O(succ-list) worst case; `unvisited_succs` (rollouts only) allocates a Vec per step.
  `Walk::features` is O(1) (all cached).
- `SearchState::recount` (`src/state.rs`) is O(n! · n) — the from-scratch *reference*
  for the drift tests only; never call it in a search loop. The `#[cfg(test)]` drift
  guards inside `beam2_search` and `SojournDfs::run` that call it are compiled out of
  every release build.
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
`walk.rs`; `validate.rs`). **Counter-drift guards (s64 P3)** — four tests, all
comparing a real search path against `SearchState::recount`, the from-scratch
reference: `state.rs` (the rules themselves: in-place vs child construction vs the
two-ended `Cursor::Keep` transition, random walks at n=4/5), `walk.rs` (ε-greedy
random walks), `beam2.rs` (every `State2` the two-ended beam builds, both move
types), `sojourn.rs` (every state the DFS expands) — plus
`tests/deficit_features.rs`, which pins `Walk` against the beam's `State` through the
exact fixed-point score at every level, for the learned features and for all three
admissible bounds. Integration tests in `tests/known_optima.rs` pin:

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
