# CLAUDE.md — working conventions for this repo

## What this is

Research codebase hunting for short superpermutations via heuristic search, with a
planned learned value function.

## Fresh-agent reading order

1. `docs/JOURNAL.md` (latest entry) — current state, last results, concrete next steps.
2. `docs/ROADMAP.md` — which phase we're in and its success ladder.
3. `docs/ARCHITECTURE.md` — code map: modules, data structures, where phase-2 plugs in.
4. `docs/THEORY.md` — math framing; read §6 for facts not worth re-deriving.

Current state in one line: **phase 3 underway, items 1–4 done, item 5 step 2
proven out at n=6; the n=7 refutation census is COMPLETE at pass-1 budgets —
85/223 chains closed, 138 open, both engine families exhausted, farm and Mac
idle (JOURNAL s17b + s18; `docs/ITEM5-DESIGN.md`, `analysis/cover7/REMOTE-FARM.md`)**
— headline: **Egan−1 = 872 is optimal in the gain-one certificate grammar at n=6**
(skip-priced ledger waste = 148 − K/4 + Σskip/4 + f4 + 2f5; forced-map period 4;
absolute pivot confinement; max V = 8, all 12 optimal chains fail the cover —
exhaustive proofs). Sub-872 must leave the grammar. Next: **Track A** (n=7 max-V₇
campaign — V₇ ≥ 15 + cover beats 5906), **Track B** (sojourn-level out-of-grammar
search at n=6), **Track C** (learned partial-certificate evaluator — the thesis).
**Track C v1 landed s17** (`docs/TRACKC-DESIGN.md`, `analysis/trackc/RESULTS-s17.md`):
guided DLX row ordering works in principle (22× on n=6, real cross-n transfer) but
NO-GO on the n=7 cover gates at 60 min; v2 lever = learned column choice. Side
product: `analysis/trackc/dlx7g` is a fast third refutation engine; its census
sweep is FINISHED (all 223 chains attempted, no SAT) — ledgers committed at
`analysis/cover7/results_n7_merged.csv` (canonical, 85 closed / 138 open) and
`results_n7_dlx_sweep.csv` (raw DLX rows). No compute is running anywhere.
Prior state: —
from-scratch bests: n=6 **873** (stratified beam, ~8 s), n=7 **5913** (same config
+ `--allow-n-mismatch`, ties greedy, ~5.5 min; bar 5907). Item 3 verdict (s8): the
deficit features (`half_open`/`nearly_done`/`w2_bridges`, v2 11-feature contract)
carry the expert signal but no linear/MLP evaluator converts it — the 872 structure
needs credit *conditional on completing the weave*. Item 4 verdict (s9): the exact
endgame tablebase (`src/endgame.rs`, Held–Karp, theorem-grade, m ≤ 25) proves the
endgame door shut — the stratified config's entire w2000 frontier at r=20 completes
to ≥ 873 (unstratified ≥ 874; n=7 ≥ 5913), and every known record (296 × 872s,
3 × 5907s) plus all our 873s have provably optimal tails. The missing character is
won strictly before the last ~25 perms ⇒ all weight on **item 5** (cycle-level
moves; weave as a move, kernel as a parameter — Robin's thread reply + 5906
boundary fact; tablebase becomes the terminal solver). Expert corpus: 298 distinct
872s (`data/records872/` + `data/gain1_872s/`), Chaffin prefixes in
`data/chaffin/`, field news in `../extraDocs/2026-07-27-urdvr-email-and-repo.md`
`../extraDocs/2026-07-28-urdvr-lean-lower-bound.md` (Lean-formalized LB:
**S(6) ≥ 869, S(7) ≥ 5888, S(8) ≥ 46103** — n=6 window now {869..872}, n=7 window
[5888, 5906]; "exitless paths are exhausted, improvement must come from the
reduction" is the stated frontier), and
`../extraDocs/2026-07-28-urdvr-lift-nge8.md` (Lean lift theorem: **S(n) ≤
Egan(n)−1 for ALL n ≥ 8**, certificate-level induction; 6→7 lift provably
fails; the 5906 record is outside his liftable grammar — mirror of our n=6
result; NO E−3 target exists in his program, so 5905 remains ours alone;
candidate DLX pruning rule in `StandardKernelHighMissingObstruction.lean`).

**Live compute (check this first if picking up cold):** a remote 28-core Windows
PC (`ssh transcribe`) hosts the n=7 refutation farm — **currently IDLE**, pass 1
complete. Operating runbook: `analysis/cover7/REMOTE-FARM.md`; scripts:
`analysis/farm/`. Status in one line:
`ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\satstatus.ps1"`
(`status.ps1` is the retired PermutationChains-era reporter).
**Pass 1 is COMPLETE (s18): 223/223 chains attempted, 41 unconditionally
refuted, 182 undecided at 30 min, no SAT** — census committed at
`analysis/cover7/results_n7_pass1.csv`. Decidable chains are fast (median 1.85
min, 25/41 under 5 min), so the survivors need a better *method*, not a
bigger budget. The farm is currently IDLE. **s17b update: the merged
multi-engine census is `analysis/cover7/results_n7_merged.csv` — 85/223
closed (52 structural zero-candidate-column refutations, 44 of them missed by
the SAT pass; 33 search-UNSAT), 138 open.** Before pass 2, reconcile
satworker's encoding with `chain7` (chain 34 should be instant UNSAT; see
JOURNAL s17b).
It runs a CaDiCaL **refutation** engine; ledger
`F:\superpermFarm\results.csv`. UNSAT = a chain unconditionally closed; a SAT
would be a candidate **world record**, auto-compiled and then validated with
`validate -n 7 --file <f> --complete` before believing anything. Two hard facts
from s15: Egan's PermutationChains Windows build is BROKEN (all its earlier farm
output is void), and **no engine we have can FIND a cover even on known-SAT
control instances** — the 5907/5906 words we "compiled" were reconstructed from
published words, not discovered. Treat the farm as a refutation census, not a
route to a record.

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

# exact endgame tablebase (phase-3 item 4, JOURNAL s9) — verdicts are theorems:
cargo run --release -- endgame -n 6 --greedy --remaining 24            # optimal completion of a prefix (also --file <s.txt>; m <= 25, RAM ~2^m)
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1 --stratify --strat-quota 4 --strat-bucket 1 --endgame 20 --endgame-top 200  # exact-solve top frontier states at r=20

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
