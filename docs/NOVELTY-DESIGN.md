# NOVELTY-DESIGN.md — the self-derived-novelty program (s53)

Synthesis of the 2026-07-31 four-agent research sweep (three surveys +
the K₄ hunt) into one ranked program. The question Andrew posed: *we
thrive when seeded from a known solution and fail at self-derived
novelty — what machinery from game solving and other computational
math record hunts can fix that?*

Source reports (full text, ~100 cited URLs each, preserved outside the
repo): `../extraDocs/2026-07-31-research-game-solving.md`,
`../extraDocs/2026-07-31-research-math-records.md`,
`../extraDocs/2026-07-31-research-superperm-field.md`.
The K₄ hunt result is in `out/s53/k4hunt/` + `data/loopswap/rules_n7_s53.tsv`
(orchestrator-verified; journal s53 entry).

## 1. Diagnosis — the five facts the surveys agree on

1. **The plateau-at-record+1 is a TIE PLATEAU, not a pruning failure**
   (Asai & Fukunaga, IPC-wide measurement): near the optimum almost
   every node has f = f*. Our s24 "zero slack" result is this exact
   pathology. Fixes are known (tie-breaking policies, refutation
   framing) — width and better bounds are not among them.
2. **Nothing in the record literature works cold.** DeepCubeA,
   AlphaZero-style loops, PatternBoost, Go-Explore, Meta-NRPA all
   bootstrap. Our seeded-good/cold-bad split is the normal condition,
   not a defect. The design question is making a seeded loop emit
   solutions FAR from its seeds — which is a representation question.
3. **Every escape from a known-solution neighborhood in the surveyed
   record hunts came from searching a smaller structured space**
   (programs, difference sets, orbits, Gram matrices, kernels), never
   from a stronger optimizer in object space. Egan/Houston's own 5906
   (palindromic kernels, |G|=2) is an instance.
4. **Refutation outperforms optimization near the optimum** (~2000×
   per position in Rokicki's cube computations). At a fixed budget the
   bound should be a hard feasibility test (cap/decision runs), not a
   soft ordering key. Chaffin's method is this formulation; our capped
   beam / --tt decision modes already are too.
5. **Our thin shell is thin in construction type, not count**: the
   22,062 known 872s collapse to a few hundred 2-cycle-graph
   isomorphism classes dominated by one treelike family. Local moves
   are trapped *by construction*, which the s44–s52b closure proofs
   (tier closed; blind spot arithmetic; K₄ saturation — §4) verify
   from the inside.

## 2. Field facts that gate the program (verified, not survey claims)

- **a(6) = 872 has two independent claimed proofs** (Gheorghe
  209-cell, preliminary, DOI 10.5281/zenodo.21653956; Grayzel
  end-to-end Lean 4 / mathlib, zero sorries). If
  either holds, 871 is dead and n=6 becomes a *calibration domain
  with known ground truth* — still valuable, no longer a target.
  **(s55 correction: neither is "under group audit" — Grayzel's
  thread has one clarifying question, Gheorghe's zero replies; the
  correct status is announced and unexamined. s55 P0 results: Grayzel
  statement FAITHFUL, trust surface clean except everything incl.
  both bounds is `native_decide`; decisive `lake build` is queued in
  SWEEP-QUEUE. Gheorghe's frame = our loop-cover grammar exactly
  (s=splits, B=D+1, deficit = j + (v−L)); his O5 gap is localized to
  22/115 δ=4 cells, ALL requiring slack covers (deficit ≥ 1, never
  observed in any corpus we hold) — the 55 tight cells are O5-free;
  his O6 (production-prune certificates), not O5, blankets the whole
  872 rung. Discharge route from our side: prove the slack tax
  `deficit ≥ 1 ⇒ length ≥ 872`. See JOURNAL s55.)**
- **Houston's 5905 program exists and was abandoned mid-run.** Two
  explicit score-15 n=7 kernels (lengths 27, 29) that "would give
  5905" if completable; Egan started them Feb 2019, no
  completion/refutation ever posted; Garner's request for the full
  sub-5907 kernel list went unanswered. The published engine
  (KernelFinder len≤30 default; PermutationChains tractable only in
  fullSymm mode) cannot handle the asymmetric completions a 5905 hunt
  needs. **Both kernels are chains #0 and #24 of our own 223-chain
  census — still OPEN after our 30-min SAT + DLX budgets.** Three
  independent parties have now failed to decide them with generic
  engines; s18's "better method, not bigger budget" is the field-wide
  verdict.
- **LKH at n=7: configured by Houston since Jan 2018 (RUNS=50000),
  publicly advertised, zero posted results**; repo pins LKH-2.0.7,
  untouched since Feb 2018. The Oct-2018 record was still 5913 and
  fell analytically. A modern re-run (ruin-and-recreate, POPMUSIC
  candidates didn't exist in 2018) is a legitimate *idle-core
  background job*, nothing more.
- **Concorde failed at n=6 twice** (Houston 2014; Pantone cluster
  2019). Edge-additive relaxations are provably capped (Gheorghe
  Thm 2.1: Houston's word is tight on all 719 edges). SAT cannot even
  FIND an 872 (tuzz/supersat, days of solver time, length-866
  coverage clauses never propagate). Generic exact tech is closed.
- **Chaffin/DCM died March 2023 at waste 122** (>100M CPU-hours;
  target 146). Our "116" notes were stale. Results server dead —
  frontier unconfirmable, and moot at n=6 if the proofs hold.

## 3. The ranked program

Ordering logic: information-per-CPU-hour first; record-path relevance
second. Items marked LAUNCH go to Andrew's launch agent as specs
(>30 min rule); everything else is in-session scale.

**P0 — Adjudicate a(6)=872.** (~1 day, mostly reading + one Lean
build = LAUNCH for the build.) Audit Grayzel for *statement
faithfulness* (definitions, not axioms); attack Gheorghe's O5
(continuation abstraction — his one open logical gap; our
loop-cover/door grammar is the right instrument; his framework
predicts Houston's witness at s=25, B=4 — recompute from our ledger
as a cross-check). Gates everything n=6.

**P1 — Reopen Track A as "finish Houston's 5905 program."** The 138
open chains ARE the program; chains #0/#24 are its named targets.
**(s54: all P1 work is built under the three-valued completion
contract of §6.1; its first milestone is the known-SAT control gate.)**
The new method stack, in order of prototyping cost:
  a. **Ledger/grammar cuts in the completion engines**: wire the s34
     2-loop law (5905 ⇔ 141-2-loop cover; length = 5764 + #2loops),
     the waste identity, fresh-doors, and door-pricing as propagators
     / column filters in DLX and as clauses in the SAT encoding. The
     zero-candidate-column test closed 52/223 instantly — these are
     its stronger siblings.
  b. **Exact very-large-neighborhood completion** (game survey #3):
     corridor / Balas–Simonetti DP at m≈16 (~5×10⁷ states) searches a
     super-exponential tour neighborhood exactly; dynasearch over
     block order is O(m²). Aimed at chain completion instead of
     generic ATSP.
  c. **Local-branching certificates** (Fischetti–Lodi): the
     constraint IS k′-opt for tours; with cutoff 5905 a "no" is a
     *proof* that no k′-opt improvement exists from a given 5906/5907
     — turns our above-record corpora into certificate factories.
  d. **Answer Garner**: enumerate ALL sub-5907 kernels past len 30,
     no palindromic restriction (KernelFinder mods or our own
     enumerator + McKay canonical augmentation). Publishable field
     infrastructure regardless of outcome. LAUNCH for the full
     enumeration; sizing run in-session.

**P2 — The shell-descent pilot (Andrew's idea #1), n=6 first.**
Above-record shells are mobile where the record shell is rigid (s51
demotion on lift-873: 399 products / 200 classes / 3 new allocations
vs 0 at record level). Design:
  1. *Populate unseeded*: bulk-generate diverse 873/874s (stratified
     beam over jitter seeds; NRPA --collect 874), archive-binned by
     allocation — breadth, not copies. (In-session at small scale;
     LAUNCH at corpus scale.)
  2. *Census*: canonicalize; map the 873 shell's allocations vs the
     record shell's 8.
  3. *Descend*: full length-reducing stack (merge / recomp /
     recomp2-tight / demotion where admissible) on every class;
     every product → validator + m3. Exit 2 = first self-derived
     novel 872. If a(6)=872 is proven, the pilot converts to a
     *calibrated instrument test*: we know exactly what descent may
     and may not find.
  4. n=7 version (5907→5906 yields novel classes for the grammar
     publication; 5906→5905 is the record play) is gated on unseeded
     entry to the 5907/5908 shell — currently impossible (from-scratch
     best 5913); candidate entry: P1's completion engines run at cap
     5907/5908, or P4 metaheuristics.
  CAUTION (s50): lifted shells conjugate — populate independently or
  the descent lands back in known classes by construction.

**P3 — Cover-sampling triage (Andrew's idea #2, corrected).**
"Random openings + boardstate evaluation" survives review only in
this form: sample at the CYCLE/COVER level (a boardstate = partial
2-loop cover + waste schedule, ~40–50 choices, not ~200 chars);
evaluate with EXACT ledger arithmetic (waste identity, pass-over
lemma, 2-loop law, zero-candidate columns), NEVER the learned
evaluator (s5: it prunes every record path by level ~62) nor the
admissible bound (s24: zero slack = no signal); select by a
DIVERSITY ARCHIVE over ledger coordinates (MAP-Elites/Go-Explore
discipline), not top-k by score. This is the sampled generalization
of the chain census and shares P1's completion engines. Prototype:
in-session at n=6 (ground truth known). **(s54: read §6 first — the
sampling side is deferred behind §6.1's control gate; the near-term
cover-level work is §6.2's vocabulary-completeness instruments.)**

**P4 — Deform-the-surface metaheuristics** (game survey #1): GLS
penalties on weight-≥2 arcs, STUN with f₀ = record, SISR
ruin-and-recreate, GAIN_CRITERION=NO / PATCHING_C=5 EXTENDED — the
modern replacements for 2018-era LKH restarts. Run AFTER the fl1577
instrument (P5) says which of these escape basins on a problem with
the same measured pathology. n=7 at 5040 nodes = LAUNCH.

**P5 — Instruments before engines** (cheap, in-session, do early):
  a. **fl1577 proxy**: the TSPLIB instance with our exact disease
     (≥22,628 optima SAMPLED — not a count, s55; mean plateau 1238;
     LKH + NeuroLKH + MABB-LKH all
     stall at optimum+5, 0/10). Minutes per iterate; any P4 recipe
     that can't crack fl1577 doesn't get n=7 CPU.
     **(s55: BUILT — harness + LKH-3.0.13 at `out/s55/fl1577/`, stall
     reproduced at exactly optimum+5; all four survey claims verified
     against primaries (Ochoa–Veerapen 2018, arXiv:2501.04072), with
     two caveats: the optima count is sampled, and Concorde SOLVES
     fl1577 — it is hard for local search only, so the 873→872 analogy
     holds at landscape level, not tractability level. First output:
     the GAIN_CRITERION=NO / PATCHING_C=5 recipe named in P4 is
     40–60× WORSE than stock LKH here — demoted from candidate to
     control. Recipe study = SWEEP-QUEUE entry.)**
     **(next session: recipe study RUN on the farm PC (SWEEP-QUEUE) —
     THE GATE PREMISE FLIPS. At a 600s single-core budget, stock LKH
     itself cracks fl1577 4/10 (the published 0/10 was a budget
     artifact of `MAX_TRIALS=DIMENSION`, not a landscape barrier), so
     "cracks fl1577" barely discriminates anymore — 24/50 cells cracked
     across 5 recipes, independently re-verified from raw coordinates.
     Two new recipes both clear the (now weak) bar with room to spare:
     `kickburst` (strong double-bridge kicks, K=6×3) 6/10, `popga`
     (LKH's population/ERX-recombination layer + finite per-run budget)
     10/10 — and an ancillary control isolates recombination from mere
     restarting (restart-only control 5/10 vs popga's 10/10, so
     recombination roughly doubles the crack rate and is by far the
     fastest to optimum). Before spending n=7 CPU on either, re-gate at
     a shorter budget where the field actually separates — not run yet,
     Andrew's call.)**
  b. **Aut groups of our known classes** (math survey #1 first step):
     decides Kramer–Mesner |G|>2 viability either way.
     **(s55: DONE, verdict NO on buying a |G|>2 engine. Theorem:
     |Aut_str| ≤ 2 for EVERY superpermutation at every n — S_n acts
     freely, only reversal∘involution can survive — so string-level
     KM with |G|>2 is vacuous by proof. Cover-level: 0/220 n=7 and
     0/22,062 n=6 classes have |Aut_cov|>2; S_n-only stabilizers are
     ALL trivial; the only symmetry the record set carries is |G|=2
     reversal-type (Egan's palindromic-kernel trick, already fully
     exploited: 84/84 published 5906 covers carry it). Provenance
     split: every community-found class is cover-symmetric, all 108
     fully-asymmetric classes are ours (102 = the whole loop-swap
     tier). If KM runs at all: cheap refutation sweeps ("no 5905 with
     symmetry G"), never as a search expected to reach known shells.
     Correction: the "183 covers" freeze is orientation-canonical
     only; fully quotiented (S₇×ι) the 220-class shell has 178
     distinct covers (180 up to S₇ alone). Artifacts
     `out/s55/aut/`.)**
  c. **Local-optima network** of the n=6 873 shell (canonicalized):
     measures basin structure before we pay for escapes.
  d. **PatternBoost data-shape check** on the 22,062 (tokenization =
     ledger coordinates, not raw strings; success metric for run 1 =
     samples landing in unseen construction classes, NOT finding
     871). Full training = LAUNCH.

## 4. What is explicitly closed (do not respend)

- Rewrite-rule/neighborhood program at n=7: tier closed at 220 (s53
  K₄ hunt: 14 residual cover groups = forward shadows + glued-K₄
  splits + 3 provably-no-unit-diff groups; vocabulary now
  mirror-complete via S53A/S53B, zero new reachability).
- The n=6 neighborhood program (s52b, concurrent operator session):
  archive closed under conjugated forward i4a AND the full 33-rule
  loop-swap table; the 12-class blind spot closed under the untargeted
  fused-pair tier (all 10,942 survivors are SELF-maps — at depth 2 the
  tier fails to move, not merely to escape); the w3→w4 promotion trade
  replay-dead corpus-wide (4.72M admissible completions, 0 products —
  the can't-lose M3 hunt won nothing).
- Generic SAT / Concorde / edge-additive relaxations at n=6 (§2).
- Naive LKH restarts at n=7 (9 months of 2018 availability, nothing).
- Chaffin exhaustion to waste 146 (~10^16× short at shutdown).
- Cold NRPA / random character-level rollouts (883 plateau; midgame
  death, twice measured).

## 5. Launch discipline

Per the standing protocol: nothing >~30 min runs from this session.
P0 (Lean build), P1d (kernel enumeration), P2 step 1 at scale, P4 at
n=7, P5d training are LAUNCH items — each needs a SWEEP-QUEUE entry
with runtime estimate, artifact list, heartbeat plan, and abort
command before Andrew's launch agent takes it. Everything else
(P1a prototypes at n=6, P3 prototype, P5a–c) is in-session scale.

## 6. The cover-algebra amendment (s54)

Source: an external research proposal Andrew brought in 2026-07-31,
evaluated and revised through two rounds; both rounds + the evaluation
preserved at `../extraDocs/2026-07-31-research-cover-algebra.md`. Its
factual grounding checked out claim-by-claim. The accepted reframing:
**the loop cover is the game position** (the 220-classes-yet-183-covers
freeze says covers are the scarcer object; s55: 183 is
orientation-canonical — fully quotiented the count is 178, scarcer
still), and the move vocabulary
should ultimately be *derived* algebraically rather than extracted one
rule family at a time — but gated as below.

### 6.0 The organizing principle

**Candidate-cover supply is not scarce; decidable asymmetric
completion is scarce.** No engine here or anywhere finds covers on
known-SAT controls (s15); 138/223 chains sit undecided at 30-min
budgets. Any method that increases cover supply without improving
completion decidability makes the pipeline busier while lowering its
information per CPU-hour. Every generator idea answers one question
first: what fraction of its output can the realizer DECIDE?

**s56/s59 answer (folded in s60, from `out/s59/cliff/REPORT.md`): not a
pool-precision threshold.** The s56 "sharp cliff at ≈3×R" is a property
of the decoy-pool instance family, in which pool size and row count are
collinear (r = 0.99) — at a fixed 4.39×R the same chain is SAT at 1,425
rows and UNKNOWN at 2,734, and a lower 3.42×R / 2,154-row instance is
UNKNOWN, in both solver lanes. The controlling variable is absolute
instance size (rows, and loops through rows). The s56 boundary was
measured at a 15 s budget; at 120 s it moves up one step on half the
panel (2.45–3.46 → 2.69–3.50 ×R) but does not dissolve, its edge cell
is seed-dependent, and randomized restarts are neutral-to-harmful here
— every "unreachable" in the s56 record is an UNKNOWN at 15 s.

### 6.1 The three-valued completion contract (binding on all P1 work)

Every completion call receives explicit structural assumptions (cover
atoms, ledger constraints, chain fixings) and returns exactly one of:

- **SAT** → a validated word (validator + m3_check ritual unchanged),
  with the witness replayable from the assumptions;
- **UNSAT** → a checkable certificate or independently reproducible
  exhaustion, projected to the *smallest assumption subset*
  responsible, stored as a reusable cut over cover space;
- **UNKNOWN** → a scheduling/profiling signal ONLY. **A timeout must
  never become a no-good cut.**

The cut store + assumption manager is the "Benders" layer: an
interface standard, not a solver. Cut producers by component —
P1a: ledger contradictions, fresh-door violations, zero/impossible
columns, waste-capacity failures. P1b: corridor/block-neighborhood
impossibility certificates. P1c: certified k′-opt/local-branching
exclusions (a "no" at cutoff 5905 proves no k′-opt improvement exists
from that 5906/5907 — witness corpora become certificate factories).
**Gate: the outer cover master activates only after P1a–c re-derive
known 5906s from their own cover/chain assumptions at usable rates
(the known-SAT control gate) and convert a meaningful fraction of
candidates into witnesses or certified cuts.**

**Milestone status (s60 fold-in).** The control gate itself PASSED in
s56 (177/177, extended to 221/221 in s57). But both successor
milestones that were supposed to open the generative tier are now
retired, for one shared structural reason: **assumption-guessing
devices are dead as a class on rigid certificates** (delete one true
atom ⇒ UNSAT, 365/365). The §6.1-gated pool-precision milestone
(557→≤350, ≤3×R) was refuted as specified in s57 (131 of 177 controls
are covers of ONE chain; no chain-only 100%-recall filter reaches
3×R); its replacement, the walk-order prefix proposer, was refuted in
s59 (18,750 legal prefixes on three known-SAT control chains, 0 SAT,
scored AND random; mechanism: a walk-order prefix has zero error
tolerance — 1 wrong row of 30 drops SAT 0.583 → 0.000, vs measured
per-step accuracy 0.20–0.39 even oracle-guided). The surviving P1
directions on the open chains are SOUND ones only: row-shrink
(pairwise cut store), no-good harvesting from the refutation stream,
and prefix RETRIEVAL against known cover rows — not guessing.

### 6.2 Vocabulary-completeness instruments (cheap, standalone, P5-grade)

The s44–s53 closures prove closure *under the discovered vocabulary*;
they do not prove the vocabulary complete. Completeness is computable,
and these instruments have value even if realization stays hard:

a. **ker-A encoding test.** Serialize covers as integer atom vectors
   `x` (2-loop dispositions, partial-chain endpoints, doors,
   split-profile atoms, Λ surcharges; complement variables for binary
   bounds) with invariant rows `A` from THEORY §7's equality terms
   (coverage, entry/exit balance, one disposition per 2-loop, split
   counts, door incidence, Λ budget, proved modular identities).
   Every verified cover-preserving rule must satisfy
   `A·(x_tgt − x_src) = 0`; a failure indicts the ENCODING (something
   mutable treated as invariant), not the rule.
b. **Blind-spot fiber diagnostic.** Same-fiber membership for the 12
   blind classes vs an ordinary shell class. Same fiber → search for
   connecting moves; different fiber → the differing row NAMES the
   higher-tier invariant. The known arithmetic obstruction
   (entry-diff 536 ≢ 0 mod 6) should reappear as a lattice fact —
   a cross-check on encoding and obstruction at once.
c. **Targeted move oracle** (preferred over basis enumeration). An IP
   solved one move at a time: smallest canonical kernel vector with
   bounded support/coefficients, applicable to a chosen source cover,
   ledger-preserving, canonically symmetry-broken, excluding the known
   rule orbits and all previously returned orbits; objective favors
   blind-region reach, cover-topology change under a tight ledger,
   multi-frame support, bounded-defect novelty. Lift the orbit only on
   application; replay every instance; add an orbit no-good; iterate.
   Sacrifices the fiber-connectivity theorem, attacks the actual
   question directly.
d. **Gated 4ti2 ladder** (only if the oracle motivates a basis view).
   Gate A: schema validation at n=5 (rules ∈ ker A, legal covers in
   fiber, illegal covers violate named rows, complement semantics).
   Gate B: ONE anchored n=6 allocation, circuits only, external orbit
   canonicalization, full sizing report (rank, kernel dim, raw vs
   canonical circuit counts, stabilizer distribution, support/degree,
   memory/wall, overlap with the 33 rules, replay-valid new orbits).
   Gate C: fiber-truncated Markov only on a positive circuit verdict.
   **Production n=7 Graver: ruled out** (astronomically
   symmetry-redundant; 4ti2 has no group quotient).

### 6.3 Pattern refutation tables (not PDB heuristics)

Loop-obligation abstractions with additively partitioned exact costs
are admissible by construction — but they are REFUTATION instruments,
deployed only inside capped/decision runs and the realizer. Judge by:
states proved impossible under cap, chains closed, node/time on known
UNSAT controls, reusable conflict patterns, P1b/c certificate rates.
Never a frontier ordering key: s24's zero-slack theorem and the §1.1
tie-plateau diagnosis rule out bounds as midgame ranking fixes.

### 6.4 Deferred generative tier (opens only after the 6.1 gate)

- **Unseeded cover master**: `Ax = b`, Λ + deficit ≤ budget, the 183
  known covers as no-good exclusions (s55: exclude by fully-quotiented
  orbit — 178 distinct under S₇×ι — or a relabeled copy of a known
  cover leaks through) — known words used only as
  exclusions and validation. Milestone: a previously unknown cover
  satisfying every proved necessary condition — the self-derived-
  novelty target at cover level, BEFORE any word.
- **Door-forest / cross-join sampler**: cycle basis + spanning forest
  of door connections + chain terminations — the constructive dual of
  THEORY §7's equality characterization (doors = bridge forest).
- **Cover-circuit recombination**: decompose cover-vector symmetric
  differences into kernel circuits; exchange coordinated circuit
  subsets (replaces the dead exact-state braid splice). Population-
  dependent — corpus expansion, not cold discovery.
- **Branch-and-price** if the atom catalog outgrows enumeration
  (columns = legal sojourn chains / loop blocks; duals = a global
  scarcity signal).
- **Realizability arithmetic (s60 fold-in):** the realizer's "~100
  atom-set decisions/s/core" is a multiplier ≤3 figure — measured
  ~200/s at ≤3×R, 5/s at 4.0×R and 0.22/s at 4.8×R with 26–29/30
  non-decisions (`out/s59/cliff/qsb_summary.json`), while the open
  chains sit at 4.6–4.9×R — so the cover master's realizability must
  be re-argued against the decision-rate curve, not a scalar.
- **5905 lanes**: separate deficit lanes (tight Λ=141 per the s34
  2-loop law, plus slack lanes); scoped outcomes only — "no cover
  under the current atom catalog" is NOT "no 5905" unless the catalog
  is proven complete.

### 6.5 Effect on the §3 ranking

P0 and P5 unchanged (P0 still first — cheap and gating). P1 gains 6.1
as its binding contract and the known-SAT control gate as its first
milestone. P3's exact-arithmetic + diversity-archive discipline
stands, but its sampling side moves to 6.4; the near-term cover-level
work is 6.2's instruments (a–c in-session at n=6; d Gate B likely
LAUNCH). P2/P4 unchanged.
