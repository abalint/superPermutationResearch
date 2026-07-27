# Lab journal

Newest entry first. Every working session appends an entry: what was done, what was
measured, what surprised us, what's next. This file is the "pick up where we left off"
mechanism — read it before touching code.

---

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
