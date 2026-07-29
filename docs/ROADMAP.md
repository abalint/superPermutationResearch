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
   350 + learned beam; JOURNAL s6). Strengthened in s7: **from-scratch 873** with no
   seeding via the stratified beam (phase-3 item 1).
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

1. [x] **Stratified beam** — ✅ **GO, both metrics met (JOURNAL s7)**: from-scratch
       n=6 **873** validated (`--stratify --strat-quota 4 --strat-bucket 1`, w2000,
       ~8 s; first sub-874 without seeding); record-state mid-walk survival
       0.15% → 99.55%. But the winning 873 is greedy-shaped — record states survive
       yet never *win*: the constraint moved from selection to evaluation. Notes:
       quota response non-monotone (2–3 catastrophic, 1/4–8 good); fine buckets beat
       coarse; anti-composes with jitter and seed-prefix; needs the learned scorer.
2. [x] **Two-ended (deque) beam — decision-order probe** — ✅ ran, **NO-GO
       (JOURNAL s7)**: arc2 scoring 897–899 (worse than one-ended 891 — deque
       squares state variety, flat bound can't rank it); learned transfer lands
       exactly on the 874 plateau; forced prepends don't help. The blindness is
       evaluation, not ordering ⇒ weight items 3–4; item 5's case is structural
       moves, not ordering freedom. (`beam2` kept in-tree: recovers 33/153, oracle-
       tested admissible two-ended arc bound.) Original design: state
       `(front, back, visited)`; moves prepend a predecessor or append a successor,
       so the string's *front* can be built last, with near-full information —
       decoupling decision order from string position (the property LKH and the
       kernel+2-cycle constructions have maximally, and append-only search lacks
       entirely; reversal symmetry cannot simulate it). Needs predecessor lists by
       weight, mirrored features (`pred1_unvisited`), and the two-ended arc bound
       `r + arcs − [succ1(back) unvisited] − [pred1(front) unvisited]`. Caveats:
       blind decisions are relocated to the string's middle, not eliminated, and the
       records' weave spans the middle 70% of the walk. Go/no-go: from-scratch n=6
       < 874 ⇒ the decision-order hypothesis is real, fund item 5's insertion moves
       generously; ≥ 874 ⇒ the blindness is evaluation, not ordering — weight
       items 3–4.
3. [x] **Deficit-distribution features + rank training on expert corpora** — ✅ ran,
       **partial: features GO, evaluator NO-GO (JOURNAL s8)**. `half_open`/
       `nearly_done`/`w2_bridges` landed end-to-end (v2 11-feature contract, old
       models bit-identical; `w2_bridges` separates record midgames perfectly:
       1.9 mean vs identically 0 on greedy-shaped walks). Expert corpus tripled to
       298 distinct 872s (gain1 mass generation) + 596 traced trajectories
       (reverse-and-relabel augmentation). But across 10 models × 186 validated n=6
       runs: best = 873, only from boot1⊕rank blends, every string byte-identical
       to the existing stratified 873 — the rank direction never flips a boot1
       decision. Population-contrast scorers are *exploitable* (beam manufactures
       bridge-rich junk: 1765-length blowups; pure rankers fail the n=5 gate).
       Anchored residual ranker = best standalone (888 < arc's 891; first nonzero
       midgame rank-wins, 10/484 levels; pair acc 89.8%, w2_bridges the strongest
       discriminator). Verdict: the 872 structure is not expressible as a static
       linear preference over these counts — credit for the weave must be
       conditional on completing it ⇒ items 4–5. n=7 baseline set: stratified
       transfer = 5913 from scratch (ties greedy; bar 5907). Original spec: features
       = count of cycles with exactly 1–2 visited members, 2-cycle adjacency between
       partially-visited cycles (O(1)-incremental in Walk AND beam State; the
       `half_open`/`nearly_done` counters from item 1 are already in beam State).
       Train to *rank* expert states above rollout states at equal level — expert
       data: `data/records872/` (100 validated 872s) + 2 new 872s in
       `../extraDocs/superpermutation-examples/` (urdvr repo, JOURNAL s7 — its
       `gain1.py search` also mass-generates fresh n=6 records in seconds, and its
       three verified n=7 words at 5,907 are the first sub-5,913 expert data for the
       n=7 rung) + Chaffin per-waste-budget optimal prefixes
       (`ChaffinMethodResults/Chaffin_6_W_<w>.txt` in the community repo —
       provably perfect openings, machine-verified). Free 2× augmentation: every
       expert trajectory yields a second valid example by reverse-and-relabel
       (reversal symmetry; the record population is mirror-closed but individual
       872s are not palindromes — 0/100 in our sample, so a palindrome-constrained
       search likely caps at 873 and is not pursued). Metric: item 1 already fixed
       *survival* (record-trajectory states in the kept window: 0.15% → 99.55%), so
       the bar moves to *winning* — record-shaped states must outrank greedy-shaped
       ones inside the stratified window; then beam length < 873.
4. [x] **Exact endgame tablebase** — ✅ built and ran (JOURNAL s9); **metric MET,
       but the verdict closes the endgame door entirely**. Held–Karp DP over
       (remaining subset, cur), exact by the triangle-inequality argument
       (`src/endgame.rs`; practical ceiling m = 25 at ~1.7 GB / ~7 s per state).
       Bolted onto the beam (`--endgame m --endgame-top K`, bit-identical search,
       per-state exact-vs-own-descendant accounting) and onto arbitrary prefixes
       (`endgame` subcommand). Metric: 7–11 per 2000 frontier states' exact endgames
       beat their own beam completions (max gain 4) — nonzero, but *never at the
       top*: the score-rank-0 state's completion was already optimal in every
       config, and no frontier state completes below the beam's own result.
       Theorems established: the stratified-873 config's **entire** w2000 frontier
       at r=20 completes to ≥ 873; the unstratified boot1 frontier to ≥ 874 (the
       873/874 difference is decided before level 700); greedy's/stratified's/
       seeded's 873s and the record 872 all have provably optimal last-25 tails;
       all 296 known 872s have optimal last-20 tails (no hidden sub-872). Use going
       forward: item 5's searcher should call the tablebase as its terminal solver
       (once ≤ ~20 remain, finish optimally, no search); a DFS branch-and-bound
       completion prover could push theorem depth past m=25 without 2^m RAM if ever
       needed. The 872-vs-873 game is over before r=25 ⇒ all steering weight on
       item 5.
5. [~] **Cycle-level move space — kernel-parameterized certificate search**
       (`docs/ITEM5-DESIGN.md`; JOURNAL s10–s11). **n=6 kernel door CLOSED with a
       proof (s11)**: in the gain-one grammar (complete rows, hops of any cost),
       871 is unreachable — skip-priced ledger waste = 148 − K/4 + Σskip/4 + f4
       + 2f5, forced-map period 4, absolute pivot confinement, max V = 8 with
       exactly 12 ledger-optimal chains, all 12 failing the rooted exact cover
       (`analysis/kernelchain/`, exhaustive). **Egan−1 = 872 is optimal in the
       class; the standard kernel is a proven optimum.** Remaining work,
       re-centered (design note §4): **Track A** — n=7 max-V₇ campaign (period/
       pivot structure unknown; V₇ ≥ 15 + feasible cover beats 5906); **Track B**
       — out-of-grammar sojourn-level search at n=6 (general identity: waste =
       S−1+#w3+2#w4+3#w5; 871 ⇒ e.g. S=144 with three w3s) + impossibility
       lemmas — **designed s21, `docs/TRACKB-DESIGN.md`; build s22–s25**
       (opening-first: L0/L1 class ledger + M1 PASS, canonical opening
       exhaustion + M2 PASS, frontier→beam completion machinery T3/T2 —
       C2 PASS, C1 oracle PASS, C1 pipeline open at 874 with the failure
       isolated to midgame ranking; s25: NRPA over the shared sojourn
       `Grammar` built — n=5 control PASS, cold start plateaus 883,
       record-warm-started policy re-derives a known 872 END-TO-END;
       M3 = independent ≤872 still open, next via neighborhood diversity +
       record bandit + warm-depth curriculum); **Track C** — the thesis: learned evaluator over partial
       certificates/sojourn plans (records as labeled data), deployed where
       Tracks A/B explode. **v1 built and gated s17** (`docs/TRACKC-DESIGN.md`,
       `analysis/trackc/RESULTS-s17.md`): corpus 310 certs / 21,423 pairs,
       parity-clean guided C DLX (`dlx7g`), holdout ranker models. Mechanism
       GO (22× nodes-to-cover on n=6; cross-n transfer 0.746 pair acc);
       n=7 cover gates NO-GO at 60 min (6/6 timeout both arms); row order
       proven irrelevant to UNSAT under fixed MRV ⇒ v2 lever = learned
       column choice, then dead-end mining, value-based restarts, CDCL
       biasing. Bonus: dlx7g = fast third refutation engine; local census
       sweep running (`analysis/trackc/census_sweep.sh`). Original framing below, superseded where it
       conflicts: play on the 120 rotation cycles —
       entry/exit points and weave order as moves, so the record structure is a move,
       not an accident. Design constraints sharpened by s8 + Robin's thread reply:
       (a) the weave must be a *move*, not a statically-rewarded feature — s8 proved
       population-contrast scoring of the shape is exploitable; (b) the kernel must
       be a *parameter* of the move space, not hard-coded — the n=7 record (5906)
       came from a nonstandard kernel, and sub-Egan−1 provably lives outside the
       standard-kernel gain-one census. The urdvr certificate machinery (W1–W7,
       trade vocabulary, DLX exact cover) is the starting formalization. Search = anytime DFS with the admissible waste-budget test
       (budget 147, never prunes a live branch — immune to the "looks wasteful early,
       converges later" deception) ordered by the learned evaluator instead of
       width-pruned. This proof-grade-pruning + learned-guidance + structural-moves
       combination is the configuration nobody has run.
6. [ ] Multi-core parallel search once 1–5 fix *what* is searched
7. [ ] n=6: attack the 867–872 gap with the above
8. [ ] n=7: bootstrap from n=6 net; attack the 5884–5906 gap (cloud CPU burst if
       bottlenecked)

Anti-goals within phase 3: no more re-tuning of the 8-feature move-level scorer
(s6 proved that pit empty three ways); no joining the waste-146 proving race.

## Non-goals

- Exhaustive lower-bound *proving* (distributed Chaffin-style verification) — different
  budget class, different project.
- n ≥ 8 — constructions beat search there for the foreseeable future.
