# CLAUDE.md — working conventions for this repo

## What this is

Research codebase hunting for short superpermutations via heuristic search, with a
planned learned value function.

## Fresh-agent reading order

1. `docs/JOURNAL.md` (latest entry) — current state, last results, concrete next steps.
2. `docs/ROADMAP.md` — which phase we're in and its success ladder.
3. `docs/ARCHITECTURE.md` — code map: modules, data structures, where phase-2 plugs in.
4. `docs/THEORY.md` — math framing; read §6 for facts not worth re-deriving.

Current state in one line: **phase 3 underway, items 1–2 done (JOURNAL s7)** —
from-scratch **873** at n=6 via the stratified beam (`beam -n 6 --width 2000 --model
ml/models/linear_n6_boot1.json --alpha 1 --stratify --strat-quota 4 --strat-bucket 1`,
~8 s; record-state mid-walk survival 0.15% → 99.55%, yet the winner is greedy-shaped),
and the two-ended `beam2` probe is a clean negative (learned transfer re-finds the
874 plateau; arc2 899 > one-ended 891) — together: the 872 blocker is **evaluation**,
not selection or decision order. New expert fuel documented in
`../extraDocs/2026-07-27-urdvr-email-and-repo.md` (urdvr repo: 2 new 872s, three n=7
words at 5,907, Egan−1 verified through n=12, gain-one generator). Next: **item 3**
— deficit-distribution features + rank training on expert corpora (reverse-relabel
augmentation), then item 4 (endgame tablebase); item 5's case is structural moves.

## Commands

```bash
cargo test --release                 # acceptance tests are pinned to proven optima (9/33/153)
cargo clippy -- -D warnings
cargo fmt
cargo run --release -- greedy -n 5
cargo run --release -- beam -n 5 --width 2000
cargo run --release -- rollouts -n 5 --count 200 --epsilon 0.15 --seed 0 --out out.jsonl
cargo run --release -- validate -n 5 <string>

# CURRENT BEST FROM SCRATCH — stratified learned beam, validated 873 (n=6), ~8 s (phase-3 item 1, JOURNAL s7):
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1 --stratify --strat-quota 4 --strat-bucket 1
# learned-score beam without stratification (phase 2) plateaus at 874 with the canonical boot1 model:
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1
# diversified restart (deterministic jitter; ε=0 is bit-identical to no jitter; anti-composes with --stratify):
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --jitter 0.03 --jitter-seed 7
# rung-1 seeded hybrid — a second, distinct 873 (n=6), ~2 s (three 873s known: greedy's, this, the stratified):
cargo run --release -- beam -n 6 --width 2000 --seed-prefix 350 --model ml/models/linear_n6_boot1.json --alpha 1
# two-ended (deque) beam, phase-3 item 2 probe (NO-GO but kept in-tree; arc2 bound by default, --model for transfer):
cargo run --release -- beam2 -n 5 --width 2000
# rung-1 mechanisms (all compose):
cargo run --release -- beam -n 6 --width 2000 --seed-prefix 120          # greedy-prefix seeding (0 = plain)
cargo run --release -- rollouts -n 6 --count 200 --epsilon 0.05 --seed 0 --model ml/models/linear_n6_boot1.json --alpha 1 --out out.jsonl  # model-guided
python3 ml/fit_linear.py data/roll_n6_*.jsonl --residual --export m.json # residual target (beam adds lb_arc back)

# record autopsy tooling (JOURNAL s5):
cargo run --release -- trace -n 6 --file data/records872/872.0053cad.txt --model ml/models/linear_n6_boot1.json --alpha 1 --score-log scores.tsv
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --cutoff-log cutoffs.tsv  # per-level prune thresholds

# training side (numpy only; see docs/ARCHITECTURE.md "ml/" section):
python3 ml/fit_linear.py data/roll_n6_*.jsonl
python3 ml/predict_check.py ml/models/linear_n6_boot1.json data/roll_n6_*.jsonl
```

Always benchmark and search in `--release`; debug builds are ~50× slower in the hot loop.

## Hard invariants — do not break

- Greedy with min-weight + lexicographic tie-break MUST produce 9, 33, 153 for n=3,4,5.
  If a graph/ordering refactor changes these numbers, the refactor is wrong.
- The lower bound must stay **admissible** (never exceed true remaining cost) — beam
  pruning correctness and any future branch-and-bound depend on it.
- Every produced string must pass the validator before being reported as a result.
- Rollout JSONL schema changes must be backward compatible or version-bumped — trained
  models depend on it.

## Conventions

- Symbols are `1..=n` as u8, rendered as ASCII digits.
- Ranks are lexicographic (Lehmer). Cycle = weight-1 rotation class, `(n−1)!` of them.
- New search features must be maintainable incrementally (O(1) or O(n) per expansion) —
  anything O(n!) per node is a non-starter at n ≥ 6.
- `beam.rs` does NOT reuse `walk.rs` — it keeps its own `State` counters so candidates
  score in O(1) without cloning, and `beam2.rs` keeps a third copy (`State2`, the deque
  searcher). Any new incremental feature must be maintained in `Walk::advance` AND the
  beam's `State`/`score_move` — and in beam2's `State2` if beam2 should score with it
  (see ARCHITECTURE.md, extension points). Also note: beam dedup assumes the score is a
  pure function of `(cur, visited, len)` (`(front, back, visited, len)` in beam2) — a
  learned evaluator must preserve that or the keep-first dedup argument breaks.
- Every working session ends by appending a dated entry to `docs/JOURNAL.md` and, if
  results changed, updating the README results table.

## Session workflow for AI agents

1. Read `docs/JOURNAL.md` (latest entry) → know where we left off.
2. Do the work; keep `cargo test --release` green.
3. Update JOURNAL.md (+ README results if applicable), commit with a descriptive message.
