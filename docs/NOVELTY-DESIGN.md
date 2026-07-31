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
  end-to-end Lean 4 / mathlib, zero sorries, under group audit). If
  either holds, 871 is dead and n=6 becomes a *calibration domain
  with known ground truth* — still valuable, no longer a target.
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
open chains ARE the program; chains #0/#24 are its named targets. The
new method stack, in order of prototyping cost:
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
in-session at n=6 (ground truth known).

**P4 — Deform-the-surface metaheuristics** (game survey #1): GLS
penalties on weight-≥2 arcs, STUN with f₀ = record, SISR
ruin-and-recreate, GAIN_CRITERION=NO / PATCHING_C=5 EXTENDED — the
modern replacements for 2018-era LKH restarts. Run AFTER the fl1577
instrument (P5) says which of these escape basins on a problem with
the same measured pathology. n=7 at 5040 nodes = LAUNCH.

**P5 — Instruments before engines** (cheap, in-session, do early):
  a. **fl1577 proxy**: the TSPLIB instance with our exact disease
     (22,628 optima, mean plateau 1238; LKH + NeuroLKH + MABB-LKH all
     stall at optimum+5, 0/10). Minutes per iterate; any P4 recipe
     that can't crack fl1577 doesn't get n=7 CPU.
  b. **Aut groups of our known classes** (math survey #1 first step):
     decides Kramer–Mesner |G|>2 viability either way.
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
