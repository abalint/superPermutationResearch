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

**Rung-1 attack round (JOURNAL s4 implementation, s6 sweeps):**
- [x] Residual training targets (`--residual`, `"target": "residual"`): negative —
      874 at every α/width; best-ever RMSE (21.6) changes nothing (JOURNAL s6)
- [x] Model-guided rollouts (`rollouts --model`): negative — guided ε=0 policy is
      exactly greedy (873) but more brittle off-path; two closed-loop rounds all beam
      874 (JOURNAL s6)
- [x] Greedy-prefix seeding (`beam --seed-prefix`): **rung 1 achieved — validated 873**
      via prefix depth 350 + learned endgame; sharp cliff at 350/719, no endgame
      deviation ever saves a character (JOURNAL s6)
- [x] Record autopsy tooling + analysis (`trace`, `beam --cutoff-log`): 100 community
      872s traced; all share the 575/141/3 weight signature; every record path is
      pruned by level ~62–118 and excluded mid-walk by up to ~68 chars; k/intact
      features actively penalize record midgames (JOURNAL s5)

**Success ladder at n=6 (each rung is a milestone):**
1. ✅ Learned-score beam matches greedy (873) — MET 2026-07-27 (hybrid: greedy prefix
   350 + learned beam; JOURNAL s6).
2. Beam finds 872 (matches the world record) — out of reach of the phase-2 design
   point (move-level beam + 8 features); requires generating record-like midgames.
3. < 872 is a new world record; 867–871 is open territory above the proven bound.

**Exit criterion (minimum): at equal wall-clock, learned-score beam beats hand-bound
beam at n=6. — ✅ MET 2026-07-27 (874 vs 890 at width 2000; hand bound needs 4× the
time for even 883). Rung 1 ✅ MET 2026-07-27 (873, seeded hybrid). PHASE 2 COMPLETE.**

## Phase 3 — beat the record-shaped pruning failure

Steering from the phase-2 endgame (JOURNAL s5/s6): the opening/midgame policy is the
whole game — records leave 1-cycles early via w2 moves and weave them closed later
(575/141/3 signature, three w3 moves at steps ≡ 0 mod 30); our features read that
structure as *expensive*, and the beam's global top-width selection crowds those
states out (0% of record states survive levels 118–601). The endgame is already
solved by the phase-2 scorer. The proving path (waste-146 exhaustion) is a closed
compute class (~10¹⁵× the 2019 distributed effort) — everything below is the
*finding* path. Items in execution order; each has a go/no-go metric.

1. [ ] **Stratified beam** (cheap; do first): reserve width per structural class
       (bucket frontier by deficit profile — untouched / half-open / nearly-done
       cycle counts) so record-like states can't be crowded out by greedy-like ones.
       Dedup + admissibility arguments unchanged. Metric: from-scratch n=6 < 874, and
       record-state survival fraction (via `trace` + `--cutoff-log`) > 0 mid-walk.
2. [ ] **Deficit-distribution features + rank training on expert corpora**: features
       = count of cycles with exactly 1–2 visited members, 2-cycle adjacency between
       partially-visited cycles (O(1)-incremental in Walk AND beam State). Train to
       *rank* expert states above rollout states at equal level — expert data:
       `data/records872/` (100 validated 872s) + Chaffin per-waste-budget optimal
       prefixes (`ChaffinMethodResults/Chaffin_6_W_<w>.txt` in the community repo —
       provably perfect openings, machine-verified). Metric: record-trajectory states
       inside the beam's kept window (currently 0% for levels 118–601) rises; then
       beam length.
3. [ ] **Exact endgame tablebase**: DP over (remaining subset, cur) once ≤ ~25–30
       perms remain (m·2^m states; ~30 is the RAM ceiling). Bolts onto any searcher:
       frontier states get true completion cost, and empirical claims ("nothing beats
       873 from greedy's basin") become theorems. Metric: any frontier state whose
       exact endgame beats the heuristic one by ≥ 1 char.
4. [ ] **Cycle-level (super-node) move space + waste-budget branch-and-bound with
       learned move ordering** (the big build): play on the 120 rotation cycles —
       entry/exit points and weave order as moves, so the record structure is a move,
       not an accident. Search = anytime DFS with the admissible waste-budget test
       (budget 147, never prunes a live branch — immune to the "looks wasteful early,
       converges later" deception) ordered by the learned evaluator instead of
       width-pruned. This proof-grade-pruning + learned-guidance + structural-moves
       combination is the configuration nobody has run.
5. [ ] Multi-core parallel search once 1–4 fix *what* is searched
6. [ ] n=6: attack the 867–872 gap with the above
7. [ ] n=7: bootstrap from n=6 net; attack the 5884–5906 gap (cloud CPU burst if
       bottlenecked)

Anti-goals within phase 3: no more re-tuning of the 8-feature move-level scorer
(s6 proved that pit empty three ways); no joining the waste-146 proving race.

## Non-goals

- Exhaustive lower-bound *proving* (distributed Chaffin-style verification) — different
  budget class, different project.
- n ≥ 8 — constructions beat search there for the foreseeable future.
