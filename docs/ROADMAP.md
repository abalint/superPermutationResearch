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

- [x] Cheap-edge (weight-1) connected components — `arcs` + `succ1_unvisited` features,
      O(1) incremental in walk and beam; also yields the tighter admissible arc bound
      (`--bound arc`), which empirically does *not* improve beam ranking (JOURNAL
      2026-07-27 s2)
- [ ] Remaining residual-graph features: residual cycle-graph degree stats, distance to
      untouched regions — incrementally maintained
- [x] Generate large labeled corpus (n=5: 288k records, n=6: 324k; ε-greedy mix + greedy
      and beam trajectory logs via `--log`)
- [x] Linear baseline regressor: held-out R² 0.92 (n=5) / 0.91 (n=6) vs 0.36 / 0.05 for
      the hand bounds (`ml/fit_linear.py`)
- [ ] GBT baseline (`ml/fit_gbt.py` exists, diagnostic-only; never run — deprioritized
      after RMSE proved uncorrelated with beam quality, JOURNAL s3 lesson 4)
- [x] Small MLP; CPU inference wired into beam scoring as `length + α·prediction`
      (`src/model.rs`, `beam --model m.json --alpha a`)
- [x] Ablation: learned score vs. hand bound at equal wall-clock (874 @ 6.2 s vs 890;
      n=5 gate holds), width sweep 500–128 000
- [x] First n=6 runs + bootstrap loop, two rounds: **874, validated — a hard plateau**
      across ~15 scorers; jitter-diversified restarts (~120 runs) cannot break it
      (JOURNAL 2026-07-27 s3)

**Next round (rung 1 attack — see JOURNAL s3 for rationale):**
- [ ] Residual training targets: fit `cost_to_go − lb_arc`, keep the anchor in the label
- [ ] Model-guided rollouts: learned score as rollout policy (close the
      search → relabel → retrain loop properly)
- [ ] Greedy-prefix seeding: beam from greedy prefixes of varying depth; find where the
      learned beam diverges from 873's basin

**Success ladder at n=6 (each rung is a milestone):**
1. Learned-score beam matches greedy (873) — learned beam is at 874, hand-bound at 890.
2. Beam finds 872 (matches the world record).
3. < 872 is a new world record; 867–871 is open territory above the proven bound.

**Exit criterion (minimum): at equal wall-clock, learned-score beam beats hand-bound
beam at n=6. — ✅ MET 2026-07-27 (874 vs 890 at width 2000; hand bound needs 4× the
time for even 883). Rung 1 still open.**

## Phase 3 — scale & record attempts

- [ ] Cycle-level (super-node) search representation
- [ ] Multi-core parallel beam / MCTS-style search
- [ ] n=6: attack the 867–872 gap
- [ ] n=7: bootstrap from n=6 net; attack the 5884–5906 gap (cloud CPU burst if bottlenecked)

## Non-goals

- Exhaustive lower-bound *proving* (distributed Chaffin-style verification) — different
  budget class, different project.
- n ≥ 8 — constructions beat search there for the foreseeable future.
