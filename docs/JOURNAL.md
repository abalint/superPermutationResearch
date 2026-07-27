# Lab journal

Newest entry first. Every working session appends an entry: what was done, what was
measured, what surprised us, what's next. This file is the "pick up where we left off"
mechanism — read it before touching code.

---

## 2026-07-27 (session 4) — rung-1 attack mechanisms implemented (residual targets, guided rollouts, prefix seeding); sweeps pending

**Built all three mechanisms from s3's "next session" list.** Implementation only —
no experiments run; a follow-up session/agents will do the sweeps.

1. **Residual training targets.** `ml/fit_linear.py` / `ml/train_mlp.py` take
   `--residual`: the label becomes `cost_to_go − lb_arc` and the exported JSON gains
   `"target": "residual"` (absent/`"absolute"` = old behavior; old model files load
   unchanged via serde default). Rust side: `Model::target()` / `is_residual()`;
   `score_move`'s `Scorer::Learned` arm scores residual models as
   `len + lb_arc + α·pred` — the admissible anchor is now in the label, per s3
   lesson 1. `lb_arc` is a pure function of `(cur, visited)`, so the dedup argument
   is untouched. Reported Python metrics stay in absolute space for comparability.
2. **Model-guided rollouts.** `rollouts --model m.json --alpha a`
   (`run_rollouts_guided`, `Guide`): the exploit move becomes the argmin of
   `len + w + α·predict(child features)` (+ child `lb_arc` for residual models) over
   unvisited successors; ties keep the sorted (weight, suffix) order. Child features
   are computed in O(1) from the walk's counters (`child_features`, mirror of the
   beam's `score_move`; parent intact count scanned once per step). Epsilon branch
   and RNG stream untouched ⇒ same seed still byte-identical; JSONL schema unchanged.
3. **Greedy-prefix seeding.** `beam --seed-prefix <depth>` (`beam_search_seeded`):
   replays the first `depth` greedy moves through the beam's own `State` counter
   updates (arena seeded with the prefix chain), then runs the remaining
   `n! − 1 − depth` levels. Depth 0 is bit-identical to the plain beam; depth must be
   `< n! − 1` (CLI errors politely). Composes with `--model/--alpha/--jitter/--bound`.

**Checks.** `cargo test --release` green (23 unit + 17 integration, 6 new tests:
residual-zero-model ≡ arc-bound beam at n=4/5; guided rollouts deterministic +
absolute-lb_arc ≡ residual-zero move-for-move; seed-prefix 0 identity, deep prefix
(117/119 at n=5) still valid, mid prefix (60) at n=5/w2000 still 153). Clippy/fmt
clean. Smokes: `beam -n 5 --width 2000 --seed-prefix 50` → 153 (0.12 s);
`rollouts -n 5 --count 5 --epsilon 0.1 --seed 0 --model ml/models/linear_n5_boot1.json`
→ mean 195.2 / min 179; residual linear fit on `data/roll_n5_e0.05_s0.jsonl`
(held-out RMSE 6.49 vs lb_arc's 23.40) beams 153 at n=5/w2000; ε=0 rollouts guided by
that residual model hit 153 on all 5 rollouts. `ml/predict_check.py` now adds `lb_arc`
back for residual models so its metrics stay absolute.

**Next session (the actual rung-1 sweeps, n=6):**
- Train residual linear/MLP on the boot corpora (`data/boot_n6_*.jsonl`); beam sweep
  α ∈ {0.25, 0.5, 1}, widths 2000–32000 — does the residual anchor beat blend-0.075?
- Generate a guided-rollout corpus (ε ∈ {0.01, 0.05}, boot1/blend0.075 as guide),
  retrain, re-beam — the properly closed search → relabel → retrain loop.
- Seed-prefix scan at n=6: depth ∈ {60, 120, …, 700} × {arc bound, boot1 model},
  looking for where the learned beam diverges from greedy's 873 basin.

## 2026-07-27 (session 3) — learned score in beam: 874; phase-2 exit criterion met; 874 is a hard plateau

**Built: learned value function wired end-to-end** (committed as `6c8140f`).
`ml/` trains linear (numpy OLS) and MLP (2×64, numpy, Adam) predictors and exports
JSON; `src/model.rs` loads them; beam scores candidates `len + α·predict(features)`
in O(1) per expansion via `--model m.json --alpha a`. Score stays a pure function of
`(cur, visited, len)`, so keep-first dedup survives. n=5 gate: every model config
still finds 153.

**Headline: n=6 = 874, validated — minimum phase-2 exit criterion met.** First hit by
a bound-blended linear model (blend α=0.075) at width 2000 in 6.2 s; also hit by
`linear_n6_boot1` (α anywhere in [0.5, 2]). Beats the hand-bound beam at equal
wall-clock *and* at 4× its wall-clock (890 @ w2000; 883 @ w8000/18 s). One character
from rung 1 (greedy's 873), two from the record (872).

**874 is a hard plateau.** ~60-run sweep (two subagents): ~15 scorers — linear/MLP ×
{raw, bound-blend, bootstrap round 1/2, elite-only, trajectory-only, corpus mixes} —
widths 500–128 000, all converge on exactly 874. Ledger lessons, in order of value:

1. **The admissible anchor is non-negotiable.** Pure learned score (no bound term)
   cliffs to 1600+. Blending or bootstrapping *on top of* `lb_arc` is what works.
2. **Label quality beats model capacity.** Strong-policy bootstrap data (ε ≤ 0.05
   rollouts + beam trajectory relabels) lets even the linear model learn the 874
   floor; the MLP on the same data does no better (and much slower: ~220 s/run).
3. **Corpus mixing is catastrophic in both directions** (mixed-ε or round-1+round-2
   blends: 880–1532). Second-round elite corpora are too narrow and hurt.
4. **Held-out RMSE is uncorrelated with beam quality** once the floor is in — the
   best-RMSE model ever trained here beams at 887–1532. Models must be selected by
   beam result, full stop.

**Built: deterministic score jitter** (uncommitted until this session's commit).
`--jitter <eps> --jitter-seed <s>`: Zobrist hash of the visited set, maintained
incrementally, gives every candidate a pure-function-of-`(cur, visited)` offset in
`[0, eps)` — dedup argument intact, bit-identical to plain beam when off. Purpose:
diversified restart portfolios to shake the last character loose.

**Negative result, and a clean one: jitter cannot break 874.** Five portfolios,
~120 runs (session was cut by an accidental close after portfolio B; C re-run and
harvested this session):

| portfolio | model | jitter ε | runs | best |
|---|---|---|---|---|
| A | blend0.075 | 0.25–2.0 | 48 | 877 (most 884–891) |
| A2 | blend0.075 | 0.01–0.12 | 48 | 874 (never 873) |
| W4000 | boot1 @ w4000 | 2.0 | 5 | 874 (jittered: 877+) |
| B | boot1, elite1 blends | 0.01/0.06 | 48 | 874 (boot1 only) |
| C | mlp_boot1_blend0.25 | 0.01–0.06 | 3 | 874 |

Small jitter reproduces 874 repeatedly; larger jitter only degrades. Read: the
models all steer into the same basin and the remaining character is *structural* —
874 is not a tie-breaking accident we can restart our way out of.

**Status vs. the ladder:** exit criterion ✅; rung 1 (873) open — needs a new idea,
not more restarts; rungs 2–3 likely need phase 3's cycle-level move space (LKH-style
local improvement / tree-like constructions are what actually set records).

**Next session, concretely:**
- **Residual targets:** train on `cost_to_go − lb_arc` instead of raw cost-to-go —
  the model then only has to learn the *correction*, and the anchor is built into
  the label, not just the score blend.
- **Model-guided rollouts:** generate the next corpus with the learned score as the
  rollout policy (current corpora are ε-greedy on *hand* heuristics), closing the
  search → relabel → retrain loop properly.
- **Greedy-prefix seeding:** start beams from greedy prefixes of varying depth —
  873's basin provably exists; find where the learned beam diverges from it.
- Housekeeping: `ml/models/` sweep artifacts are untracked by design (only canonical
  models committed); `data/` corpora regenerable from logged seeds.

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
