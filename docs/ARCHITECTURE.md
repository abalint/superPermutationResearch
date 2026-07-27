# Architecture

Code map for the `superperm` crate (phase 1). Math background lives in
`docs/THEORY.md` — this file only covers what the code does and where to change it.
Binary + library crate: `src/lib.rs` exports the modules, `src/main.rs` is the CLI.

## Module map

Dependency sketch (arrows point at dependencies):

```
main.rs ─→ graph, greedy, beam, rollout, validate
greedy ──→ walk ──→ bitset, bound, graph
rollout ─→ walk, bound, graph        (+ rand, serde_json)
beam ────→ bitset, graph             (does NOT use walk — see Extension points)
validate → graph (factorial, rank)
bound ───→ (serde only; pure arithmetic + Features struct)
bitset, graph → no crate deps
```

- **`src/bitset.rs`** — `BitSet`, a fixed-capacity bitset over `Box<[u64]>`.
  `new(nbits)`, `set(i)`, `get(i)`, `popcount()`, `first_clear(limit) -> Option<usize>`.
  Derives `Hash`/`Eq` so it can be part of the beam dedup key. Padding bits in the last
  word are never set, so word-wise equality/hash is sound for same-capacity sets.
- **`src/graph.rs`** — the permutation overlap graph. Free functions
  `factorial(n)`, `rank(perm: &[u8]) -> usize` (Lehmer rank), `unrank(n, rank) -> Vec<u8>`;
  `struct Graph` with `Graph::new(n)` (asserts `3..=8`) and the static helper
  `Graph::overlap(a, b) -> usize` (brute-force suffix/prefix overlap, used for path
  reconstruction and as the test oracle).
- **`src/bound.rs`** — `lower_bound(r, k, current_cycle_has_unvisited) -> usize`, the
  admissible bound `r + k − [current cycle has unvisited]` (THEORY.md §3);
  `lower_bound_arc(r, arcs, succ1_unvisited)`, the tighter arc bound
  `r + arcs − [succ1(cur) unvisited]` (admissibility proof in the module docs); and
  `struct Features` (serde `Serialize`/`Deserialize`), the rollout JSONL record.
- **`src/walk.rs`** — `struct Walk<'g>`, the incremental search state shared by greedy
  and rollouts. `Walk::new(&Graph)`, `advance(rank, weight)`, `first_unvisited_succ()`,
  `unvisited_succs()`, `fallback_target()`, `lb()`, `features()`, `done()`,
  `len_chars()`, `string()`, `graph()`.
- **`src/greedy.rs`** — `greedy(&Graph) -> GreedyResult { string, len, path: Vec<u32> }`.
  Deterministic baseline; hits 9/33/153 for n=3,4,5 (hard invariant) and 873 for n=6.
- **`src/beam.rs`** — `beam_search(&Graph, width, Bound) -> BeamResult { string, len,
  path }`. Level-synchronous beam search scored by `len + lb` under a selectable
  admissible bound (`Bound::Cycle` or `Bound::Arc`); private `struct State`,
  `fn score_move`, `fn child_arcs`.
- **`src/rollout.rs`** — `run_rollouts(&Graph, count, epsilon, seed, out: &mut impl Write)
  -> io::Result<RolloutSummary { rollouts, mean_len, min_len, lines }>`. Epsilon-greedy
  rollouts emitting JSONL `Features` lines. Also `log_trajectory(&Graph, path, out)`,
  which replays a recorded visit-order path through a `Walk` and emits the identical
  record format (used by `greedy --log` / `beam --log`).
- **`src/validate.rs`** — `validate(n, s: &str) -> Validation { n, length, distinct,
  total, complete }`. Sliding-window checker; the only accepted proof that a string is
  a superpermutation.
- **`src/main.rs`** — clap CLI (`struct Cli`, `enum Cmd`): subcommands `info`, `greedy`,
  `beam`, `rollouts`, `validate`.

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
- `cur: u32` — rank the string currently ends with;
- `chars: Vec<u8>` — append the last `weight` symbols of the target perm (a
  `debug_assert_eq!` checks the overlap really matches);
- `steps: u32` — advances taken.

`lb()` = `lower_bound(r, k, cycle_rem[cycle_id[cur]] > 0)` — O(1); `lb_arc()` =
`lower_bound_arc(r, arcs, succ1_unvisited())` — O(1), dominates `lb()`.
`features()` is O(cycle_count) (scans `cycle_rem` for `intact_cycles`); it is only
called by the rollout generator, not in the greedy/beam hot path.

### Beam state, arena, dedup (`src/beam.rs`)

`State { cur, len, visited: BitSet, cycle_rem, k, r, arcs, node }` mirrors `Walk`'s
counters but without `chars` — no state carries a string or path.

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
- **`beam`** — `beam_search(&g, width, bound)` (default width 1000, `--bound
  cycle|arc`, default cycle) → prints length, wall-clock seconds (`Instant`), and the
  string. `--log <file>` writes the best path's `Features` JSONL.
- **`rollouts`** — opens `--out` as `BufWriter<File>`, calls
  `run_rollouts(&g, count, epsilon, seed, &mut writer)` → prints count/epsilon/seed,
  mean and min final length, lines written. Defaults: `--count 100`, `--epsilon 0.1`,
  `--seed 0`; `--out` is required.
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

## Extension points for phase 2 (learned evaluator)

- **Where beam scoring happens**: `score_move` in `src/beam.rs` — the tuple's first
  element is `len + lb`. That single expression is the evaluator; a learned value
  function replaces (or blends with) the `lb` term there. Its only call sites are the
  two `cands.push(score_move(...))` calls inside the level loop of `beam_search`
  (normal successors and the weight-`n` fallback). Note the sort/dedup comment in
  `beam_search` assumes the score is a pure function of `(cur, visited, len)` — a
  learned score that breaks the "identical for duplicate keys" property invalidates the
  keep-first-min-length argument and the dedup logic must be revisited.
- **Where new incremental features live**: `Walk` in `src/walk.rs` (add the field,
  update it in `advance`, expose it in `features()`), **and also** `State` +
  `score_move` in `src/beam.rs` if the beam needs it — beam does not use `Walk`; it
  duplicates the counter maintenance for O(1) candidate scoring. Keep the two in sync,
  and keep everything O(1)/O(n) per expansion (CLAUDE.md convention).
- **Adding a CLI subcommand**: add a variant to `enum Cmd` in `src/main.rs` (clap
  derive) and a match arm in `main()`; put the logic in a library module and export it
  from `src/lib.rs`. Follow the existing pattern of printing a summary line then the
  payload.
- **Training-data knobs**: `run_rollouts` in `src/rollout.rs` — the policy is the
  `if options.is_empty() / rng < epsilon / else options[0]` block; `Features` +
  `Walk::features()` define what gets logged.

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
- `beam_n4_width_512_is_optimal` — beam(width 512) reaches 33 at n=4, validated.
- `beam_n5_width_2000_is_optimal` — beam(width 2000) reaches 153 at n=5, validated.
- `lower_bound_admissible_at_start_n4` — fresh-state `lb ≤ 33 − 4`.
- `lower_bound_never_exceeds_cost_to_go_on_greedy_trajectory_n4` — replays the greedy
  n=4 path through a `Walk`, asserting `lb ≤ actual remaining cost` at every step and
  `lb == 0` at the end.
- `validator_rejects_non_superperm` — incomplete and degenerate strings fail.
- `rollouts_deterministic_and_consistent` — same seed ⇒ byte-identical output; `n!`
  lines per rollout; every line round-trips through `Features`; `len_so_far +
  cost_to_go` is constant within a rollout with final `cost_to_go == 0`; epsilon=0
  reproduces the greedy length.

**Hard invariants** (CLAUDE.md): greedy must keep producing 9/33/153 — if a
graph/ordering refactor changes those numbers, the refactor is wrong, not the test;
the lower bound must stay admissible; every reported string must pass `validate`.
Run `cargo test --release` (the beam tests are slow in debug).
