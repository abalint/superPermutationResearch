# Lab journal

Newest entry first. Every working session appends an entry: what was done, what was
measured, what surprised us, what's next. This file is the "pick up where we left off"
mechanism — read it before touching code.

---

## 2026-07-27 (session 7) — phase 3 opens: stratified beam GO (from-scratch 873); two-ended beam NO-GO (evaluation, not ordering); field news: urdvr repo (Egan−1 at n=11–13, n=7 5907s)

Three parallel subagent threads: roadmap items 1 and 2 (implement + sweep each), plus
documentation of a new community email/repo. Both probes returned decisive answers,
and they converge.

**Item 1 — stratified beam: GO, both metrics met (commit `83724ac`).** New beam
`State` counters `half_open` (cycles with 1–2 visited members — the structure records
keep alive) and `nearly_done` (1–2 unvisited), O(1)-incremental. Frontier bucketed by
`(intact/B, half_open/B, nearly_done/B)`; selection reserves up to `--strat-quota`
best candidates per occupied bucket, then fills the width in global score order. Score
function untouched (admissibility/dedup arguments unchanged); off-mode pinned
bit-identical by test. Results (boot1 α=1; unstratified baseline 874 everywhere):

- **From-scratch n=6 = 873, validated** — the first sub-874 without prefix seeding.
  `beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1 --stratify
  --strat-quota 4 --strat-bucket 1` (~8 s; also quotas 1/5/6/8 at w2000; quota 4 holds
  at w8000/32000). String saved to `data/result_stratified_873.txt`; independently
  reproduced bit-identical. Distinct from greedy's 873 and the seeded 873.
- **Record survival transformed**: fraction of record-trajectory states inside the
  kept window at levels 118–601 goes **0.15% → 99.55%** (quota 4:1); 96/100 records
  are never outside the window at any level (baseline: 100/100 pruned by level 118).
  First-prune level for the remaining 4: 288–380 (was median 62).
- Quota response is sharply non-monotone (2–3 catastrophic at 897–904; 1 and 4–8 give
  873; 12–32 degrade); fine buckets beat coarse (default 32:4 stays at 874). Jitter
  and seed-prefix both *anti-compose* with stratification; arc bound + stratification
  is worse than plain arc (reserved width is wasted without a discriminative scorer).
- **The surprise that matters: the winning 873 is greedy-shaped** (600/96/18/4/1
  weight histogram, heavy moves at steps ≡ 0 mod 30), not record-shaped. Record-like
  states now survive the whole walk yet never win — selection is fixed, and what
  remains between 873 and 872 is *evaluation*.

**Item 2 — two-ended (deque) beam: NO-GO, clean negative (commit `5fbee1c`).** New
`beam2` subcommand: state `(front, back, visited)`, append-successor/prepend-
predecessor moves, weight-graded predecessor lists (`Preds`, exact mirror of succs),
mirrored features, dedup on `(front, back, visited)`, and the two-ended arc bound
`lb_arc2 = max(r, r + arcs − [succ1(back) unvisited] − [pred1(front) unvisited])`
with proof sketch in `src/bound.rs` and oracle-tested admissibility along arbitrary
deque walks. Recovers 33/153 (n=5 needs width ≥ ~1000, where the winning 153 uses 44
prepends — real two-ended optima exist). n=6 from scratch: arc2 scoring **899/898/897**
at w2000/8000/32000 — *worse* than one-ended arc (891), because the deque squares
state variety per level (same visited set × many (front,back) pairs) and the flat
bound can't rank the extras. The learned model transferred into the new move space
lands **exactly on the 874 plateau** (w2000 and w8000, a different 874 string, only 6
prepends); jitter forcing 220–364 prepends moves arc2 only 899 → 892. Per the roadmap
criterion: **the blindness is evaluation, not decision order** — item 5's future case
rests on structural moves, not ordering freedom. Side-find: a width-1 beam reproduces
greedy's 873 under both bounds (previously unrecorded).

**Convergent read.** Fix selection (item 1): record states survive but never win. Fix
ordering (item 2): nothing changes. Both point at evaluation — the scorer cannot
recognize record-shaped midgames — which is exactly items 3 (deficit-distribution
features + expert-rank training) and 4 (exact endgame tablebase). Item 1 also moves
the baseline: the from-scratch bar is now 873, and stratification is the default
harness for any future scorer test.

**Field news (email from urdvr, 2026-07-27) — documented in
`../extraDocs/2026-07-27-urdvr-email-and-repo.md`, repo cloned to
`../extraDocs/superpermutation-examples/`.** New words + generator code
(github.com/urdvr/superpermutation-examples). All claimed lengths are exactly
**Egan−1** (n! + (n−1)! + (n−2)! + (n−3)! + n − 4): n=11 43,948,807; n=12
522,910,088; n=13 6,749,568,009 (n=13 word not yet distributed — no GitHub release).
We verified every distributed word: n=6/7 via our validator, n=8–12 via an
independent Lehmer-rank bitset checker. n=11/12 are new records by our ledger.
Contents relevant to us: **2 new 872s** (from-scratch DLX search, not in our 100),
**three n=7 words at 5,907** (first known with the standard 5-loop kernel; record is
5,906), 4–6 words each at n=8–10 (Raudvere/Echols originals + perturbed variants).
Construction: Egan−1 ⇔ a "gain-one" certificate (T1/T2/T3-only walk, standard kernel,
oriented complete-2-cycle exact cover forming a forest rooted in the kernel); three
modes — exact-cover search (DLX), perturbation (destroy ~30% of rows and rebuild),
and lifting n→n+1 (verified 9→13; **6→7 provably fails**; search-and-verify, no
induction proof). Author caveats recorded verbatim: generator evolved without
rigorous notes, may not reproduce exactly; lifting "usually (but not always?)" works.
**Discrepancy to raise on the thread: the email mentions Williams words in the repo,
but none exist in the tree, releases, or branches.**

Phase-3 implications of the repo: (a) real expert fuel for item 3 — the n=7 5907s
break our 5913 threshold, the new 872s extend the n=6 corpus, and `gain1.py search`
is a seconds-fast mass generator of fresh n=6 records; (b) for item 5, the repo *is*
a worked cycle-level move vocabulary (row destruction/rebuild, anchored trades,
trap-loop bans) with `liftcheck.py`'s W1–W7 as a machine-checkable "record-shaped"
predicate; (c) boundary fact: the 5,906 record **fails** the gain-one structure
(nonstandard kernel), so beating 5,906 means leaving that move space — gain-one is a
ceiling, not a ladder.

**Next session (item 3, with the new fuel):**
- Deficit-distribution features (count of cycles with exactly 1–2 visited members —
  `half_open` is already maintained in beam State; add the 2-cycle-adjacency stat and
  wire both into `Features`/JSONL + the model contract).
- Rank training: expert states (100+2 records via `trace`, Chaffin optimal prefixes,
  optionally mass-generated gain1 872s) above rollout states at equal level; reverse-
  relabel augmentation. Metric: record states *win* the stratified window, then beam
  length < 873.
- Cheap parallel probe: run the phase-2 scorer + stratification at n=7 for a first
  baseline (greedy 5913; new sub-target 5907 from the urdvr words).

## 2026-07-27 (session 6) — rung 1 achieved: validated 873 via greedy-prefix + learned endgame; residual and guided-loop attacks plateau at 874; PHASE 2 COMPLETE

Three parallel sweep campaigns over the s4 mechanisms (one subagent each), run
concurrently with the s5 record autopsy. Two clean negatives and one breakthrough.

**Attack 1 — residual targets: negative, 874 everywhere.** Residual models
(`cost_to_go − lb_arc` labels) on the boot1 recipe: `linear_n6_res_boot1` (held-out
RMSE 25.1 in absolute space vs lb_arc's 92.7), `mlp_n6_res_boot1` (21.6), plus a
raw-ε-greedy-corpus control. Results: linear res_boot1 → **874** at α ∈ {0.25, 0.5}
for every width 2000–32000; α=1 → 875, α=2 → 1104 (the residual correction is
calibrated — pushing it harder now *degrades*); MLP → 874 (α ∈ {0.25, 0.5}); raw
corpus → 899–1640 (still poison regardless of target formulation). Jitter portfolio
(18 runs): 15× 874, 3× 875, never 873. n=5 gate passed by all models. Lesson-4
reconfirmed sharply: best RMSE ever trained here (21.6), identical beam result.
Label engineering is ruled out as the path to 873.

**Attack 2 — model-guided rollouts (closed loop): negative, 874 everywhere, with a
diagnosis.** The guided ε=0 policy scores **exactly 873 on all 50 probe rollouts** —
the model has memorized the greedy corridor — but is *more brittle off-path* than the
hand heuristic (ε=0.01: min 906 vs the hand policy's 873; worse at every ε > 0). Two
full guided rounds (search → relabel → retrain, ~325k + 217k rows, incl. fresh beam
trajectories): every retrained model (`linear_n6_guided1`, `_res`, `_mix`, `guided2`)
beams **874 at every α ∈ {0.5, 1, 2} and width ∈ {2000, 8000, 32000}**. Notable
non-replication: mixing guided with old boot corpora was harmless (874, vs s3's
880–1532 catastrophes) — s3's mixing failures were across *behaviorally different*
policies; guided-ε ≈ hand-ε here, so the mix is benign. Closing the loop cannot
escape a basin when the policy generating the data is the basin.

**Attack 3 — greedy-prefix seeding: rung 1 achieved, validated 873.**
`beam -n 6 --width 2000 --seed-prefix 350 --model ml/models/linear_n6_boot1.json
--alpha 1` → **873 in ~2 s**, validated complete (720/720) and independently
reproduced; string saved to `data/result_prefix_873.txt`. Full depth→length picture
(w2000):

| depth | 0 | 60–345 | 350 | 360–718 |
|---|---|---|---|---|
| boot1 α=1 | 874 | 875–876 | **873** | 873 |
| arc bound | 891 | 888–876 | — | 873 from 476 (band 476–480 non-monotone) |

Key numbers: the cliff is **sharp at depth 350 of 719 (~49% of the walk)** — 345 gives
876, 350 gives 873, no intermediate lengths, zero variance under jitter (32 runs) or
width (8000/32000). Shallow seeding actively *hurts* (60–345 → 875–876, worse than
unseeded 874): the model's midgame fights greedy's line rather than approximating it.
Deep prefixes (660–718, w32000, both scorers) → all exactly 873: **no endgame
deviation from greedy's basin ever saves a character**; the 872nd character must be
won in the first half. The blend0.075 model shows a seeding pathology (878 at depths
350/355 — worse than its own unseeded 874). Side-findings: the winning 873 is *not*
greedy's string (first divergence at char 440); blend0.075 is pre-blended — its
coefficients are already `0.075·model + 0.925·lb_arc`, so it runs with `--alpha 1`
(s3's "blend α=0.075" describes the training mix, not a CLI flag).

**Convergent picture (this session + s5 autopsy).** The seeding cliff at ~350 and the
autopsy's prune window (every 872 record excluded from the beam's score window from
level ~62–118 to ~601, by up to ~68 chars) agree: opening/midgame policy is the whole
game, the endgame is already solved by our scorer. The records' fixed signature
(575/141/3 weight profile — leave 1-cycles early via w2, weave them closed later) is
exactly what the k/intact features penalize, because no rollout corpus ever shows it
paying off. 874 → 873 fell to forcing the opening; 873 → 872 requires *generating*
record-like midgame states, which no reweighting of the current 8 features will do.

**Phase 2 verdict: complete.** Exit criterion met (s3), rung 1 met (this session,
hybrid greedy-prefix + learned-endgame beats both parents from scratch). Rung 2 (872)
is out of reach of the phase-2 design point — move to phase 3.

**Next session (phase 3 opening), concretely:**
- **Cycle-level move space**: super-node search over rotation cycles that *plans* the
  2-cycle weave (which cycles to leave half-open, where to spend the three w3 moves —
  records put them at steps ≡ 0 mod 30) instead of discovering it move-by-move.
- **Deficit-distribution features**: count of cycles with exactly 1–2 visited members,
  2-cycle adjacency between partially-visited cycles — the autopsy showed these
  separate record midgames from rollout midgames at equal (r, level).
- **Imitation corpus, free**: `data/records872/` (100 distinct validated 872s +
  fetch recipe, JOURNAL s5) can be traced to `Features` JSONL — expert
  demonstrations the rollout corpora structurally lack. A model trained to *rank
  record states above rollout states* at equal level is the cheapest test that the
  new features carry the signal.
- Infrastructure is ready: `trace` (first-visit trajectory + per-step beam-exact
  scores), `beam --cutoff-log` (prune thresholds), `--seed-prefix` (basin forcing)
  compose for any future what-does-the-beam-lose analysis.

## 2026-07-27 (session 5) — record autopsy: traced 100 community 872s; our scorer prunes every record path by level ≈62, midgame k/intact features are the blind spot

**Question answered this session: what do actual 872-length solutions do that our
searches prune, and at what depth / by what margin does the beam discard them?**

**Built.** (1) `trace` subcommand (`src/trace.rs`): `trace -n 6 --file s.txt
[--model m.json --alpha a | --bound cycle|arc] [--log f.jsonl] [--score-log f.tsv]` —
extracts a string's first-visit rank trajectory (sliding window), replays it through a
`Walk` (replay_len == input_len certifies tightness), prints the move-weight histogram
and weight ≥ 3 positions, optionally emits the `Features` JSONL and per-step
beam-exact scores (`score_state` mirrors `score_move`'s fixed-point arithmetic, so
scores compare exactly with cutoff logs). (2) `beam --cutoff-log f.tsv`
(`beam_search_cutoffs`): one TSV line per level — `level, kept, best_score,
worst_kept_score` (the pruning threshold); pure instrumentation, bit-identical search
(pinned by test). 5 new tests (26 total green), clippy/fmt clean. Corpus: 100 community
872 records + 873-tight/-egan downloaded to `data/records872/` (gitignored; all 100
validate complete and trace tight: replay 872, 720 visits, identity start).

**1 — Structure.** Move-weight histograms (719 moves each):

| walk | w1 | w2 | w3 | w4 | w5 |
|---|---|---|---|---|---|
| greedy 873 | 600 | 96 | 18 | 4 | 1 |
| our beam 874 (boot1 α=1, w2000) | 600 | 89 | 30 | 0 | 0 |
| **every one of the 100 records** | **575** | **141** | **3** | 0 | 0 |
| 873-egan | 571 | 148 | 0 | 0 | 0 |

All 100 records share the identical histogram: 25 fewer w1 and ~50 more w2 than
greedy/beam, exactly three w3 moves, never w4+. The 3 w3 moves sit at multiples of 30:
{630,660,690} (29 records), {30,60,90} (26), {30,60,690} (25), {30,660,690} (20).
Weight spend is uniform across the walk (~24–25 extra chars per 120-step bucket) —
records pay w2 steadily instead of finishing cycles and paying w3+ resets.

**2 — Divergence.** First visit-index where a record's rank sequence leaves greedy's
path: min 2, p25 28, median 62, p75 92, max 118 (only 8 distinct values:
{2,28,32,58,62,88,92,118}); 16 records leave the very first cycle after just one w1
move (weight pattern 1,2,… vs greedy's 1,1,1,1,1,2). Our beam-874 path shares greedy's
first 78 visits, so divergence vs beam874 is the same distribution capped at 78.

**3 — Prune depth (headline).** Scoring each record trajectory with the canonical
scorer (linear_n6_boot1, α=1) against `beam -n 6 --width 2000 --cutoff-log` per-level
thresholds: **all 100 records are pruned; first-prune level min 4 / p25 28 / median 62
/ p75 92 / max 118** — the beam discards every record branch inside the first ~16% of
the walk. Margin at first prune: 0.2–7.1 chars (median 5.5). Mid-walk the exclusion is
enormous: from level 118 to 601 **zero** record states score within the kept window
(per-record worst margin: median 68, max 114 chars). Records re-enter the window at
level ≥ 602 and by level 700 they'd *win* it (record score 863.9 vs cutoff 872.5) —
the endgame ranking is fine; the beam just can't generate those states. Width 32000
barely moves anything (median first-prune 62 → 62; the same 874). Under the arc bound
(w2000): median first-prune 90, margin always exactly 1 char — the bound is flat, not
wrong. Anchors: our own 874 path is never pruned (sanity, frac-within 1.0); greedy's
873 path survives to level 243 with worst margin 1.47. Caveat: this is a
necessary-condition analysis — the beam must also *generate* a state (parent must
survive), so true prune depth ≤ measured.

**4 — Feature gap.** Model residual (pred − actual cost-to-go) along trajectories:
the model overestimates record states by ~+129 chars in the opening vs +115 on its own
beam path (+9 delta), and the gap *widens* through the midgame — delta peaks at
**+52 chars around steps 290–430** — closing to +6 by the end. Feature-level cause (at
step 300, records mean vs beam874): intact 65.9 vs 69, k 73.8 vs 70, lb_arc 492 vs 488
— records look "worse" on every feature the model has, yet their actual cost-to-go is
*lower* (504.8 vs 506). With coefficients k +3.92 and intact −9.30, those two features
alone account for ~+44 of the +49 midgame prediction gap. The model reads "many
touched-but-unfinished cycles" as expensive; records deliberately keep ~4 more cycles
half-open (the 2-cycle weave) and close them later at cost ≈ the greedy-style walk —
structure the 8 features cannot see.

**Synthesis (steers phase 3).**
1. The 874 plateau is a *policy* gap, not a tie-break gap: every 872 lies outside the
   beam's score window from level ~62–118 onward by up to ~68 chars mid-walk. No
   width/jitter/restart tweak of the current scorer can recover them (32000 ≈ 2000).
2. The records' signature is fixed and known: 575/141/3 weight profile, w2 moves
   spread uniformly, exactly three w3 "super-moves" at steps ≡ 0 (mod 30). Our
   searches' signature (600 w1) means "always finish the current cycle" — the single
   biggest behavioral difference is leaving 1-cycles early via w2.
3. The learned model *actively* penalizes record-like states (k up, intact down ⇒
   pred up), because its training corpus (greedy-flavored rollouts) never shows that
   half-open-cycle structure paying off — label bias, not model capacity.
4. Concrete feature gap: at equal (r, level), records differ in *how* the unvisited
   mass is arranged across cycles (many cycles at small deficit vs few at large). A
   feature capturing the deficit distribution (e.g. count of cycles with exactly 1–2
   visited members, or 2-cycle adjacency stats between partially-visited cycles)
   would separate record midgames from rollout midgames.
5. Endgame is already solved by our scorer (records would top the beam from level
   ~640 on) — effort should go to opening/midgame policy, e.g. phase-3 cycle-level
   search that *plans* the 2-cycle weave instead of discovering it move by move.

Artifacts (scratchpad, regenerable): per-record trace logs/score TSVs, cutoff logs
for w2000/w32000 (model) and w2000 (arc), analysis scripts. Data in `data/records872/`
(gitignored), fetch commands in this entry's session transcript; re-download via
raw.githubusercontent.com from superpermutators/superperm `superpermutations/6/872/`.
Note: `data/873-tight.txt` is a multi-string file (comment + several 873s), not a
single superperm; `873-egan.txt` is a single string.

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
