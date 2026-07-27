# Roadmap

## Phase 1 — search infrastructure & baselines (n ≤ 5 testbed)

- [x] Permutation overlap graph: lex ranking, weight-w successor generation, 1-cycle decomposition
- [x] Deterministic greedy baseline — must reproduce 9 / 33 / 153 exactly
- [x] Beam search scored by `length + admissible cycle bound`, incremental O(1) bound maintenance
- [x] Superpermutation validator (self-certifying check)
- [x] Epsilon-greedy rollout generator → JSONL `(features, cost_to_go)` training data
- [x] Acceptance tests pinned to proven optima; clippy/fmt clean

**Exit criterion: beam search recovers the proven optima for n = 4 and 5.**

## Phase 2 — learned value function (n=5 → n=6 transfer)

- [ ] Feature engineering pass: residual-graph features beyond the phase-1 set
      (residual cycle-graph degree stats, cheap-edge connected components, distance to
      untouched regions), all maintained incrementally
- [ ] Generate large labeled corpus at n=4/5 (mix of greedy, epsilon-greedy, beam-path rollouts)
- [ ] Baseline regressors (linear, GBT) before any neural net — measure R² on cost-to-go
      vs. the hand bound's error
- [ ] Small MLP; batch CPU inference wired into beam scoring as `length + α·prediction`
- [ ] Ablation: learned score vs. hand bound at equal wall-clock, beam width sweep, n=5
- [ ] First n=6 runs; measure gap to 872. Bootstrap loop (search → relabel → retrain) at n=6

**Success ladder at n=6 (each rung is a milestone):**
1. Learned-score beam matches greedy (873) — hand-bound beam is currently 890.
2. Beam finds 872 (matches the world record).
3. < 872 is a new world record; 867–871 is open territory above the proven bound.

**Exit criterion (minimum): at equal wall-clock, learned-score beam beats hand-bound
beam at n=6, i.e. rung 1.**

## Phase 3 — scale & record attempts

- [ ] Cycle-level (super-node) search representation
- [ ] Multi-core parallel beam / MCTS-style search
- [ ] n=6: attack the 867–872 gap
- [ ] n=7: bootstrap from n=6 net; attack the 5884–5906 gap (cloud CPU burst if bottlenecked)

## Non-goals

- Exhaustive lower-bound *proving* (distributed Chaffin-style verification) — different
  budget class, different project.
- n ≥ 8 — constructions beat search there for the foreseeable future.
