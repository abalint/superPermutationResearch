# Residual-graph admissible lower bound ("Bound-1 localized") — design

Status: opened session 19 (2026-07-28), after the urdvr/Hunter Lean LB landed
(S(6) ≥ 869; see `../extraDocs/2026-07-28-urdvr-lean-lower-bound.md`, clone at
`../extraDocs/superpermutations-hunter`, paper `paper/hunter_bound.tex`).
Goal: an admissible lower bound B(state) on the cost of completing a partial
walk (state = cur + visited set), strong enough to close the gap between our
current root valuation (~840 at n=6) and the Hunter-style valuation (~869).
Uses: beam pruning (`len + B > target` ⇒ provably dead), future
branch-and-bound, and the certified floor under any learned evaluator
(evaluator = B + learned residual ⇒ exploit-proof below the floor).

## Hard invariant (absolute)

B must NEVER exceed the true optimal completion cost of the state — for
**covering walks** (revisits of covered perms allowed), not merely Hamiltonian
completions. Any term without a written proof for arbitrary residual covering
walks stays OUT of the admissible bound (it may ship separately as a heuristic
ordering term, clearly separated in code and docs). Greedy 9/33/153 and all
existing defaults unchanged; the new bound is opt-in (`--bound residual`).

## Tier ladder

- **Tier 1 (safe, must land):** exact residual class accounting. r = uncovered
  perms; c = rotation classes with ≥1 uncovered perm. Every step covers ≤1 new
  perm (≥ r steps, weight ≥1 each); inter-class steps have weight ≥2 and the
  walk must enter every residual class other than cur's current class at least
  once ⇒ B₁ = r + (c − 1) − [cur in a residual class] adjustments, all proven
  in the doc. Expected root value n=6 ≈ 838–842 (≈ parity with today; the
  value is the exact fragment-aware accounting + the platform for Tier 2).
- **Tier 2 (the prize, research):** localize the door/freshness argument.
  Hunter's per-vertex price q_k ≈ 1 + 1/k + 1/(k(k−1)) + … comes from: entries
  chained by weight-2 doors follow the τ₂ functional structure (period k−1),
  a sustained chain forces the chart, deviations cost ≥3, post-chart ≥4
  (`lem:tau2/tau3/rigidity/closure`). The global proof runs through the
  F-transform on complete paths; the task is a residual-local version: for an
  arbitrary covering walk of R, lower-bound the number of ≥3-weight entries
  forced by the door structure of R's residual classes. Every claimed term
  requires a written proof (in this doc) + empirical non-violation on the
  tablebase sample. If proven: B₂ → r·q_k-shaped, root ≈ 869 at n=6.
- **Tier 3 (fallback, non-admissible):** any Tier-2 term that resists proof
  but never violates the tablebase empirically ships as `heuristic_floor`,
  usable for move/beam ORDERING only — never pruning. Code must make the
  distinction impossible to confuse (separate function, loud naming).

## Implementation

- Rust, new module (e.g. `src/lb_residual.rs`); state maintenance must be
  O(1)–O(n) per expansion (per-class uncovered counters: array of (n−1)!
  u16s; c maintained on decrement-to-zero; door-orbit structure precomputed at
  startup from τ₂). Wire into `Walk::advance` AND beam `State`/`score_move`
  (and NOT beam2 unless free), per the CLAUDE.md multi-copy rule. Beam dedup
  purity rule holds: B is a pure function of (cur, visited).
- `--bound residual` on beam/walk paths; default behavior bit-identical
  without the flag.

## Gates

- **GA (admissibility, blocks everything):** ≥10k sampled states with m ≤ 25
  remaining across n = 5 and 6 (greedy/beam prefixes + random completions),
  exact truth via the endgame tablebase: assert B ≤ truth on every sample,
  report the slack distribution. One violation = the term responsible is cut.
- **GB (strength):** root values (state after the initial permutation):
  report exact B at n = 5, 6, 7 per tier; Tier-1 target ≈ parity with the
  current bound, Tier-2 target ≥ 860 at n=6 (869-shaped). Also report B on
  100 random depth-200 n=6 beam states vs the current bound (mean uplift).
- **GC (search effect):** n=6 beam A/B at equal width (2000, canonical model
  config from CLAUDE.md): prune-rate/cutoff-log comparison + final lengths.
  Any regression in achieved length at equal width = report loudly.
- **GD (invariants):** cargo test --release green (9/33/153 pins), clippy
  clean, no default-path behavior change.

## Non-goals (this session)

No B&B driver, no learned-evaluator integration, no n=7 deployment — those
build on a gated bound, later.
