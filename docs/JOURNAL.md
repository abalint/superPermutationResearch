# Lab journal

Newest entry first. Every working session appends an entry: what was done, what was
measured, what surprised us, what's next. This file is the "pick up where we left off"
mechanism — read it before touching code.

---

## 2026-07-27 (session 2) — arc features + arc bound; corpus; linear baseline beats hand bounds

**Built: weight-1 arc features, incrementally maintained.** Arcs = connected components
of the *unvisited* perms under weight-1 (rotation) edges — the refinement of cycles into
maximal unvisited runs. O(1) maintenance per move in both `Walk::advance` and the beam's
`State` (new `Graph::pred1` inverse-rotation table). `Features` gained `arcs` and
`succ1_unvisited` (`#[serde(default)]`, so old JSONL still parses). A from-scratch
recount oracle test pins the incremental update.

**Built: the arc bound — provably tighter, admissible.** Every arc must be first-entered
by a weight ≥ 2 edge except the one headed by `succ1(cur)`, so
`lb_arc = r + arcs − [succ1(cur) unvisited]` is admissible and dominates the cycle bound
pointwise (proof sketch in `src/bound.rs` docs; admissibility + dominance asserted along
greedy trajectories in tests). Beam takes `--bound cycle|arc`.

**Negative result worth keeping: the tighter bound does NOT help beam.** n=6:

| width | cycle | arc |
|---|---|---|
| 500 | 894 | 894 |
| 2000 | 890 | 891 |
| 8000 | 883 | 888 |

Beam is not A*: a pointwise-tighter admissible bound reorders the frontier but still
doesn't *predict*, and empirically ranks slightly worse. This kills the "just tighten
the hand bound" alternative and sharpens the phase-2 thesis — the evaluator must be a
predictor, not a bound. (`--bound` default stays `cycle`.)

**Built: trajectory logging.** `greedy --log f.jsonl` and `beam --log f.jsonl` replay
the final path through a `Walk` and emit the same JSONL records as rollouts
(`rollout::log_trajectory`; `BeamResult` now carries `path`). Test pins ε=0 rollout ≡
logged greedy trajectory, byte-identical.

**Corpus generated** (`data/`, gitignored): n=5 ε ∈ {.05,.15,.30} × seeds {0,1000} ×
400 = 2400 rollouts (288k records; ε=.05 hit the optimum 153); n=6 same ε, seed 0,
150 each = 450 rollouts (324k records); plus greedy/beam trajectory logs for both n.

**Linear baseline: the features carry real signal.** `ml/fit_linear.py` (numpy OLS,
held-out split by rollout, features + both hand bounds + bias):

| n | predictor | held-out RMSE | MAE | R² |
|---|---|---|---|---|
| 5 | lb_cycle | 51.7 | 42.3 | 0.36 |
| 5 | lb_arc | 51.5 | 42.1 | 0.36 |
| 5 | linear | **17.8** | 13.2 | **0.92** |
| 6 | lb_cycle | 428.1 | 352.5 | **0.05** |
| 6 | lb_arc | 426.3 | 350.5 | 0.06 |
| 6 | linear | **133.0** | 95.6 | **0.91** |

The n=6 row is the money quote: the hand bounds explain ~5% of cost-to-go variance —
a quantitative restatement of "beam prunes blind at n=6" — while a *linear* model over
six cheap features explains 91%. Escalation to GBT/MLP is justified per plan.

**Caveats to carry forward.** (1) Labels are behavior-policy returns (ε-greedy), not
optimal cost-to-go — mixed-ε corpora inflate variance-explained; the bootstrap loop
(search → relabel → retrain) is what fixes label quality. (2) RMSE 133 at n=6 is far
too coarse to steer 872-vs-890 endgames yet; what matters first is *ranking* frontier
states better than the bounds do.

**Next session, concretely:**
- Wire a learned score into beam: `score = len + α·predict(features)` with batch
  evaluation per level; keep the score a pure function of `(cur, visited, len)` so the
  dedup argument survives. Start with the linear model (its coefficients are just a dot
  product — no Python in the loop), sweep α and width at n=5 (must still find 153), then
  first learned-score n=6 runs vs the 873/890 baselines (success ladder rung 1).
- GBT baseline on the same corpus (sklearn if available) to see how much nonlinearity
  buys over linear before committing to an MLP.
- Remaining feature from the plan: residual cycle-graph degree stats (2-cycle adjacency
  between rotation cycles) — needs a cheap incremental formulation.

## 2026-07-27 — handoff prep; gap analysis; phase-2 success ladder

**Docs pass for fresh-agent handoff.** Added `docs/ARCHITECTURE.md` (code map: modules,
data structures, CLI data flow, JSONL schema, phase-2 extension points) so nobody has
to reverse-engineer `src/`. Reading order for a fresh agent is in CLAUDE.md.

**Gap analysis — where greedy stands vs. targets.** Greedy is provably the
sum-of-factorials construction, so:

| n | greedy | best known | gap | proven lower bound | gap to LB |
|---|---|---|---|---|---|
| 3–5 | 9 / 33 / 153 | same | 0 | same | 0 |
| 6 | 873 | 872 | 1 | 867 | 6 |
| 7 | 5913 (formula; not yet run) | 5906 | 7 | 5884 | 29 |

Consequences: (1) n ≤ 5 is a correctness harness only — greedy is already optimal
there, so no learning signal about *beating* anything exists below n=6. (2) The
phase-2 evaluator's bar is n=6.

**Phase-2 success ladder** (in order; each rung is a real milestone):
1. Learned-score beam **matches greedy (873)** at n=6 — currently hand-bound beam is
   17 chars worse (890 at width 2000), so this is not trivial.
2. Beam **finds 872** at n=6 (matches the record).
3. Anything **< 872** is a world record; anything ≥ 868 disproven only by exhaustion,
   so 867–871 is genuinely open territory.

**Next session, concretely:**
- Generate a large labeled corpus: `rollouts` at n=5 and n=6 with a few epsilons +
  seeds; also log states along greedy and beam trajectories (needs a small code
  addition — see ARCHITECTURE.md extension points).
- Fit a *linear* regressor on the existing features first; compare its cost-to-go
  RMSE against the hand bound's error on held-out rollouts. Only escalate to GBT/MLP
  if linear shows the features carry signal.
- Add residual-graph features next: cheap-edge connected components and residual
  cycle-graph degree stats, maintained incrementally in the walk state.

## 2026-07-26 — project start; phase 1 built

**Context.** Project born from a conversation about treating superpermutation
construction as chess-style game-tree search: permutations as nodes, added-length as
edge weight, heuristic evaluation + pruning instead of exhaustive enumeration. That
framing turns out to be the established one (ATSP on the overlap graph; Houston's 872
came from LKH). The genuinely open angle we're betting on: a *learned* cost-to-go
evaluator over residual-graph features instead of hand-derived bounds. Full framing in
THEORY.md.

**Decisions made.**
- Rust for the search core; JSONL boundary to a future Python model side; no GPU
  assumptions (small MLP over engineered features is the design point).
- Testbed discipline: n=4/5 (proven optima 33/153) are the correctness harness; n=6 is
  the first real hunting ground (best known 872, lower bound 867).
- Beam state tracks per-cycle remaining counts so the admissible bound
  `lb = r + k − [current cycle live]` is O(1) incremental.
- Weight-n "jump" edges kept out of adjacency lists; searches use an explicit fallback
  to the lowest-ranked unvisited perm so states can't dead-end.

**Built.** Graph (lex rank/unrank, weight-1..n−1 successor lists, 1-cycle decomposition),
deterministic greedy, level-synchronous beam with arena path reconstruction + dedup,
validator, epsilon-greedy rollout generator emitting `(features, cost_to_go)` JSONL,
CLI (`info`/`greedy`/`beam`/`rollouts`/`validate`), acceptance tests pinned to 9/33/153.

**Results.**
- All tests green (`cargo test --release`: 14 unit + 7 integration), clippy/fmt clean.
- Greedy: 9 / 33 / 153 / 873 for n=3..6 — exactly the sum-of-factorials construction,
  as required. All outputs validator-complete.
- Beam recovers the proven optima: n=4 → 33 (width 512, 0.007 s); n=5 → 153 (width
  2000, 0.19 s). **Phase-1 exit criterion met.**
- Surprise / key finding: at n=6, beam (width 2000) gives **890 — worse than greedy's
  873**. The admissible cycle bound `r + k − [cur]` stops discriminating between beam
  states at this size: most frontier states share nearly identical bounds, so the beam
  effectively prunes blind. This is the cleanest possible motivation for phase 2 — the
  evaluator, not the search loop, is the binding constraint.
- Rollouts (n=5, 200 runs, ε=0.15, seed 0): mean 214.85, min 178, 24 000 JSONL records.
  Plenty of spread between optimal (153) and mean — good label variance for regression.

**Same-day field news (Superpermutators Google Group, 2026-07-26).** Raudvere posted an
n=8 superpermutation of length **46204** — one below Egan's construction — verified by
Houston, who identified it as *tree-like*: standard kernel + 833 two-cycle extensions.
Echols followed with independently-checked n=9 (408,965) and n=10 (4,037,046)
candidates, each −1 vs. Egan. Two takeaways for us: (1) the cycle-level tree
representation planned for phase 3 is exactly the structure setting records right now;
(2) the community corpus lives at https://github.com/superpermutators/superperm — use
it for validation targets and known-solution features. Thread + Houston's extension
tree saved locally in `../extraDocs/` (outside the repo).

**Next session.**
- Start phase 2 feature engineering: residual cycle-graph degree stats and cheap-edge
  connected components, maintained incrementally.
- Generate a large n=4/5 rollout corpus; fit a linear regressor first and compare its
  cost-to-go error against the hand bound before reaching for a net.
