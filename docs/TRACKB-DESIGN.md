# Track B design — opening-first sojourn-level search at n=6 ("the opening book")

Status: design note opened session 21 (2026-07-29). **Build status (s22,
2026-07-29): T0 DONE (§2 blockquote), L0 ledger DONE + M1 PASS
(`analysis/trackb/enumerate_l0.py`, ledger_l0.csv), T1 atlas DONE
(`atlas` subcommand + `analysis/trackb/door_atlas.py`), L2 sojourn DFS BUILT
(`src/sojourn.rs`, `sojourn-dfs`) + M2 PASS in book mode (§6 blockquote).
s23 (2026-07-29): T3 DONE (`--dump-frontier` + `beam --seed-file`
multi-seed injection), C2 PASS, C1 oracle PASS / pipeline NOT PASSED —
completion-blocked at 879 vs a measured 878 beam-completion ceiling (§6
blockquote). s24 (2026-07-29): T2 DONE (`Scorer::Composed` + admissible
`--max-len` cap): pipeline 879 → 874 (first learned-signal win on
completion; robust plateau), cap proven sound with big viable-search
speedups, and the capped failures prove the midgame RANKING (levels ~60–450)
is the sole remaining failure — the record's own line has zero cap slack
until the end, so no bound/width/cap can fix selection there. Next: NRPA +
bandit → re-run C1 → M3. JOURNAL s22–s24 have all numbers.** This is the concrete state/move
design that ITEM5-DESIGN §6.2 named as Track B's missing prerequisite. Inputs:
(a) the opening-decides-everything evidence chain (s5/s6/s7/s9, §1 below); (b) the
s11 grammar theorem (sub-872 must leave the certificate grammar); (c) the s19
residual bound; (d) the s20 Vlad frame cross-validation; (e) a survey of solved-game
techniques (this session's discussion) — the design's organizing principle is that
every solved single-agent game handled its opening by **enumeration + canonical
exhaustion + budgeted exploration**, never by evaluation alone.

Standing context: Track B is **downgraded, not retired** (s20: sub-872 word ~5–10%
likely). The design is therefore deliberately **two-sided**: the same class
machinery that organizes the search also produces impossibility lemmas, and given
that Vlad's top rung rests on two open soundness obligations (O5/O6), an
independent closure path over waste-146 structures has standalone value even if no
871 exists. Cost profile: Mac-local; the farm is not budgeted unless §6 M3 fires.

## 1. Evidence: the game is decided in the opening (all theorem- or measurement-grade)

- s5: every record path is pruned by the move-level beam at level **62–118** and is
  mid-walk excluded by up to ~68 chars — the divergence from the greedy basin
  happens in the first ~20 sojourns.
- s6: greedy-prefix seeding has a sharp cliff at 350/719 — decisions after mid-walk
  are recoverable, decisions before are not.
- s7: stratification's entire 873-vs-874 value is delivered early (s9 theorem 2:
  the difference is decided strictly before r=20).
- s9 theorems: the stratified w2000 frontier at r=20 completes to ≥873; every known
  record and all our 873s have provably optimal last-25 tails. Nothing is at stake
  in the endgame; the tablebase closes it for free.
- s11: in-grammar 871 is impossible; the search target is out-of-grammar structure,
  which by §2 is *opening/midgame* structure by construction.

Solved-game imports, one line each: **Chinook** (opening book grown as a proof tree
from the root, meeting the endgame DB — our L0–L2 spine + tablebase tails);
**God's-number Rubik's** (partition into cosets, close each by bounded search — our
L0 allocations are the cosets; per-class verdict = lemma or search); **snake-in-the-
box** (canonical-form DFS exhausts early layers up to symmetry — §4 step 2);
**AlphaZero root behavior** (bandit at the root where value cannot discriminate —
§4 step 3); **Morpion/NRPA** (nested policy adaptation learns openings with no
evaluator — §4 step 4); **LKH tour merging** (recombine elite openings — §7 side
probe).

## 2. Coordinates: general waste ledger and the opening-class hierarchy

Budget: `waste = length − 725`; window {869..872} (urdvr Lean floor 869). Target
871 ⇒ waste ≤ 146. General identity (ITEM5 §3, with the intra-orbit caveat made a
first-class term):

```
waste = (S − 1) + #w3 + 2·#w4 + 3·#w5 + i2
```

where S = sojourn count (maximal in-cycle runs), the wI counts are inter-sojourn
transition weights, and `i2` counts intra-orbit weight-2 moves (double rotations —
the unique non-w2x w2; each skips a cycle member, forcing a later revisit).
**T0 (before any ledger use): machine-verify this identity, including the i2 term,
over the full corpus** (296 records, greedy, all 873s, rollout walks) — the i2-free
form is verified, the i2 pricing is not yet.

> **T0 DONE (2026-07-29, `analysis/trackb/verify_identity.py`, 806 strings, zero
> exceptions).** The stated form is exact on every walk whose only moves are w1,
> w2 (both kinds), and cycle-changing w3/w4/w5 — all 297 records (147 = 144+3),
> all 873s, greedy n=5/6, Kristan's n=7 5906 (860 = 842 + 18·w3, i2=0 —
> n-generic).
> The i2 pricing was exercised on 319 ε-rollout walks (up to i2=14), exact on
> all. Two correction terms exist beyond the stated form, both measured and
> exactly priced by the **general identity**
> `waste = (S−1) + Σ_{w≥3}(w−2)·inter[w] + Σ_{w≥2}(w−1)·intra[w]`:
> (a) intra-orbit rotations of weight k≥3 (priced k−1); (b) weight-≥6 doors
> (priced w−2). Both occur only in ε-rollouts/fallbacks, never in records or
> greedy — but both are legal under budget 146, so **L0 must carry them** (or
> close them by lemma). New structural lemma from T0 (emergent-edge, intra-orbit
> case): in the canonical first-visit reading, an intra-orbit rotate-by-k exists
> only when all k−1 skipped members are ALREADY VISITED — otherwise the appended
> characters spell the skipped members and the move decomposes into cheaper
> moves. Canonical i2 therefore means "pass over a visited member", not "skip
> and revisit later". Bonus fact: Egan's 873 is a pure w2-door walk (S=149,
> zero w3+/i2) — a different cycle-level shape from greedy's 873 (S=120,
> 18/4/1).

Door facts that shape the space: at weight 2 there are exactly two successors —
the intra-orbit double rotation (the i2 move) and `w2x = P[2:]+P[1]+P[0]` (the
unique cross-cycle w2 door). So out-of-grammar freedom at n=6 lives in exactly:
sojourn lengths outside {2,3,4,6}, non-laminar interruption structure, mid-walk
w3+/i2 placement, and w3+ door choices beyond the kernel-fragment pattern. **T1:
build the general door atlas** — for w in {3,4,5}, the static cycle-level table of
(exit offset → target cycle, entry offset) realized by each door; the out-of-
grammar analog of urdvr's T2 table. Size ~720 × O(w!) rows, one-off.

The class hierarchy (each level is an "opening book" chapter; chess = ECO codes):

- **L0 — waste allocations.** Tuples `(S, #w3, #w4, #w5, i2)` with
  `(S−1) + #w3 + 2#w4 + 3#w5 + i2 ≤ 146`, `S ∈ [120, 147]` (every cycle needs ≥1
  sojourn), `#w3+#w4+#w5 ≤ S−1`. A few hundred tuples; trivially enumerable. The
  s11 theorem already closes the laminar/w2x-only/complete-row region; record it
  per-tuple. Ledger discipline copied from s20: a CSV with per-class status
  (`closed-lemma | closed-search | open`), closure artifact, and effective tier —
  Vlad's GAPS/ERRATA/weakest-link model, adopted wholesale.
- **L1 — cycle split profiles.** Per-cycle partition of its 6 visits into sojourn
  runs (now including 1s and 5s), aggregated as counts per partition type, with
  `Σ_cycles parts(c) = S`. Feasibility filters: counting/parity lemmas, transition-
  graph degree constraints (the sojourn walk visits cycle c exactly parts(c)
  times), door-atlas reachability, and — **cross-reference only, never trusted
  pruning** — Vlad's F1 (`Δ+δ ≥ 5`) / F2 (`3Δ+4δ+5(j−β) ≥ 20`) and cell kills
  once independently re-derived (his frame is corroborated 299/299 on our corpus;
  his kills are untested here). Each filter that closes an L1 class is a lemma;
  publishable in aggregate regardless of search outcome.
  **s27 update:** profiles are per-allocation DATA now, not the hard-coded
  records constant — `analysis/counting/upstream872_structure.py --profiles-dir`
  generates the allowed-composition set per specimen-backed allocation
  (`analysis/trackb/profiles/a<S>_<d3>_<d4>_<d5>_<ip>.txt`, loaded via
  `--profile-file`), and `grammar-check` validated all 22,062 community classes
  against their allocation grammars (719/719 moves each). Two corpus laws worth
  pruning with (both calibrated, not theorems): the composition vocabulary is
  just {6, 2|4, 3|3, 4|2, 2|2|2, 1|5, 5|1}, and every weight≥3 door opens an
  untouched cycle (66,999/66,999 events — the `--fresh-doors` cap).
- **L2 — canonical opening prefixes.** Concrete first-d-sojourn walks, deduped up
  to symbol relabeling: canonical key = (per-cycle visit-pattern multiset, waste
  ledger so far, current-cycle pattern), hashed Zobrist-style (Track C's `shash`
  lesson). Start perm fixed at identity WLOG; relabeling is then spent, so
  canonicalization acts on the *abstraction*, not the exact prefix — it defines
  bandit arms and dedup classes, while beam/DFS dedup below stays exact on
  `(cur, visited)`.

## 3. State and move design (sojourn level)

State = `(cur, visited: 720-bit, per-cycle visit patterns, waste ledger
(S, #w3, #w4, #w5, i2), residual-bound value)`. All fields are already in or
directly extend the beam `State` counters; no laminar stack — non-laminar structure
is legal by design. Maintenance stays O(1)/O(n) per move (repo invariant).

Move = one sojourn decision: `(ride ℓ more w1 steps | i2 skip, then exit via door
(w, target entry))`. This is a grouping of raw perm-level moves — the walk it
compiles to is validated by the existing validator, and the tablebase remains the
terminal solver at r ≤ 20 (s9: the last ~20 plies are free and exact).

Pruning: the admissible waste-budget test at budget 146 — `len + bound > 725 + 146
⇒ dead` — using `--bound residual` (s19; admissible, door terms proven, 0
violations on 10,400 tablebase states). Never prunes a live branch, so it is
immune to the looks-wasteful-early deception that kills move-level scoring of
record shapes (s8). Note `--bound` and `--model` do not compose yet (s19); §4
needs both — **T2: make bound-pruning and model-ordering compose in one search.**

## 4. The search loop (opening-first)

1. **Enumerate L0, filter L1** (pure computation, no search): emit the class
   ledger. Every lemma closure shrinks step 2's work; a full closure of waste
   ≤ 146 would be an independent a(6) = 872 proof path (not expected; every
   partial closure still narrows where 871 can hide).
2. **Canonical opening exhaustion** per open L0×L1 class: cycle-level DFS on the
   first d sojourns up to the L2 canonical key, waste-budget pruned. Target
   d ≈ 10–12 sojourns (≈ levels 50–70 — covering the zone where record paths
   historically diverge and die). Output: the opening frontier, one node per
   canonical class. Budget cap on node count; if a class exceeds it, record
   `open-oversize` in the ledger honestly (no silent truncation).
3. **Bandit over frontier nodes**: UCB with reward = best completion length found
   under that node (track min and 5th percentile — 872-vs-873 is a tail event, so
   allocate on the tail, not the mean; if tail variance swamps UCB, fall back to
   successive halving). Exploration constant tuned on the n=5 control.
4. **Rollout engines** per pull (both, cheapest first):
   (a) **NRPA** at sojourn level — policy = weights over move features (door
   weight, ride length, target-cycle residual class), softmax rollouts, adapt
   toward the best rollout at each nesting level, nesting 2–3, tablebase finish.
   No trained model needed on day one; NRPA is the technique of record for
   exactly this problem class (Morpion Solitaire).
   (b) **Constrained stratified learned beam** seeded at the node — generalize
   `--seed-prefix` to `--seed-file <walk>` (T3), keep stratification, and taper
   width with depth: wide through the contested levels, narrow after (s9 proved
   nothing is at stake late; the tablebase eats the tail anyway).
5. Any completion ≤ 872 goes through `validate --complete` before being believed
   or reported (s15 discipline), then through the s20 coordinate-frame script as a
   free structural cross-check.

## 5. Track C tie-in (the thesis, deployed at the opening)

The evaluator's job here is *relative* ordering of opening states — never absolute
cost-to-go (the v2.1 lesson: pairwise/rank targets, not effort regression; the s3
lesson: RMSE is uncorrelated with search quality). Training data exists on day
one: 296 records give positive opening prefixes at every depth; step-4 rollouts
give matched-depth negatives; reverse-and-relabel doubles both. Deployment points,
in order of increasing coupling: bandit prior over frontier nodes → NRPA policy
initialization → beam ordering inside rollouts. Evaluation metric is
**depth-stratified rank quality on levels < 700 only** — endgame ranking is
already solved and must not pad the score. The L2 canonical keys make the Track C
K-class-canonicalization finding explicit structure rather than something the
model has to relearn.

## 6. Controls and go/no-go

- **C1 (positive control, gates everything):** given the records' own L0 class
  (S=145, #w3=3, rest 0) and their L1 profile (25 splits, {2,3,4,6} lengths), the
  full pipeline re-finds a validated 872 from scratch. If the machinery cannot
  find a known object in its known class, it cannot be trusted at 871 (s15: no
  engine we had could find known covers — institutionalize that lesson here).
- **C2:** the full pipeline at n=5 finds 153 (repo hard invariant, unchanged).
- **M1 (lemma side):** ≥ half of L0 allocations closed by lemma in the first
  working session on step 1. Cheap, and calibrates how much of the space is
  actually open.
- **M2 (exhaustion side):** d=10 canonical opening exhaustion of the records'
  class completes within ~10⁶ nodes. If not, the canonical key is too fine or the
  door alphabet too wide — fix before scaling out.
- **M3 (search side, the real gate):** bandit + NRPA produces an *independent*
  872 (byte-distinct from all 296 known — **re-scoped s26c: inequivalent, up
  to relabeling+reversal, to all 22,062 community classes; check with
  `analysis/counting/upstream872_census.py`**) from C1's class, or any
  validated ≤873 from an out-of-grammar class. GO ⇒ fund the 871 campaign (and only then the
  farm). NO-GO after C1 passes ⇒ Track B stays parked at lemma-production only.

> **Gate results so far (s22).** **M1 PASS**: 66.5% of the 78,813 L0
> allocations closed by lemma (LB-869 floor + the new pass-over lemma
> `ip ≤ 4(S−120)`); honest live-shell (waste 144–146) number: 22.9%, 26,416
> classes open. **M2 PASS in book mode, with a design correction**: d=10
> exhaustion of the records' class needs 746k nodes at exemplar cap E=16
> (13,527 canonical classes, 2.6 s) — within the ~10⁶ budget — but the
> *sound* tiers cannot reach d=10 (exact ≈ 5.9M nodes at d=6, oversize by
> d=8; the relabeling-orbit quotient buys ~0.3% because the identity start
> breaks the symmetry). Closure/exhaustion claims must stay at d ≤ 6 or wait
> for T2 residual-bound pruning; the book/bandit layer is unaffected
> (coverage dial E measured: at d=4, E=1/64/256 → 174/323/334 of 334 true
> classes). C1/C2 not yet run (need T3 completion machinery).
>
> **Gate results s23.** **C2 PASS**: greedy's n=5 class (S=24, d3=4, d4=1) →
> exact-dedup d=6 frontier, 64 exemplars/class (473 seeds) → multi-seed beam
> = validated 153 under all three bounds. Abstraction-tier 1/class gives 154:
> the canonical key is too coarse to pick the right exemplar — in-class
> exemplar diversity closes the last char. **C1 oracle PASS**: seeded with a
> known 872's own prefix, the beam re-derives the record byte-identically
> from depth ≥ 450 (residual w32000 + endgame; ≥ 500 at w8000; the stratified
> learned config only from ≥ 600 — it is the WORST record-opening completer,
> 899–917 from shallow prefixes; the residual bound is the best by 15–30
> chars). **C1 pipeline NOT PASSED, blocker quantified**: from the TRUE
> record opening at depth 14 the completion ceiling is 878 (w32000 + exact
> endgame), and pipeline runs saturate it — 24,214 sound d=6 exemplars over
> all 2,114 classes → 879 at both w8000 and w32000 (width-saturated). The
> gap to 872 lives entirely in beam completion through levels ~60–450: it
> needs a *policy* (step 4a NRPA, T2 composition), not a wider beam. The §4
> step-4b width-taper idea is thereby deprioritized; 4a is the next build.

## 7. Side probe (independent, one afternoon): tour merging over the 296

> **s26 verdict: BUILT AND BLOCKED.** `union-dfs` (docs/RECOMB-DESIGN.md §5,
> §8.2): the union graph is even sparser than estimated (1,279 edges,
> out-degree ≤ 2), but exact search inside it is intractable — TRUNCATED at
> 200M nodes even for 2-record unions, cap-871 decision equally blocked; the
> splice closure (§8.1) and the s26c full-corpus rerun (22,062 classes, 5
> closure walks, all equivalent to known — the community corpus is
> splice-closed) are the surviving products.

Cook–Seymour tour merging, opening-reframed: all 296 known 872s share optimal
greedy-basin tails (s9 theorem 4), so the union of their edge sets encodes pure
opening/midgame diversity. Build the union graph (~sparse: 296 walks × 719 edges,
heavy overlap), run exact B&B (or DLX/ILP) for a Hamiltonian path of length ≤ 871
restricted to it. Either outcome pays: 871 = record; exhaustion = "no 871 in the
recombination closure of every known 872's opening" — independent evidence about
the (0,5,25,0) cell that Vlad's program currently asserts at effective tier L.

## 8. Risks

1. Sojourn-level branching may still explode (ride × door × entry). Mitigation:
   start with the atlas-restricted door alphabet (w2x + w3 doors only, i2 allowed),
   widen to w4/w5 only on evidence — the s11 census says heavy doors buy waste
   fast, so the narrow alphabet covers the plausible 871 shapes first.
2. T0 may show the i2-priced identity needs correction terms — do T0 before the
   L0 ledger, not after.
3. Tail-event bandit rewards are noisy; successive halving is the fallback
   (§4.3), and C1 is the guard against tuning on noise.
4. The 5–10% prior on any sub-872 existing is the dominant risk — which is why
   the lemma ledger (§2 L0/L1) is a deliverable in its own right, not scaffolding.
5. Anti-goals carried forward: no static reward for record-like shapes in a
   move-level scorer (s8); no waste-146 exhaustive proving race (ROADMAP); no
   trusting Vlad's cell kills as pruning until independently re-derived (s20).

## 9. Build order (first working session)

T0 identity verification → L0 enumeration + ledger (M1 read) → T1 door atlas →
L2 canonical DFS + M2 on the records' class → C1/C2 controls → T3 `--seed-file`
+ T2 bound/model composition → bandit + NRPA → M3 verdict. The §7 tour-merge
probe is independent and can run any time the Mac is otherwise idle.

**Queued for the L2 DFS (from the 2026-07-29 Kristan-5906 analysis): the
emergent-edge canonicalization filter.** A weight-w move whose appended
characters spell an unvisited permutation `p` in an interior window builds a
string byte-identical to the decomposed line through `p` (weight k + weight
w−k), so generating both branches duplicates entire subtrees. Rule: annotate at
graph build time which edges have permutation interiors (static per edge; per
node exactly 1 of the 2 weight-2 successors and 3 of the 6 weight-3 successors
at n=7), then at move generation skip a composed edge whenever an annotated
interior rank is unvisited; keep it when all interior ranks are visited (that
case is real and record-tying — Kristan's string). Provably lossless for both
optimality and enumeration — every skipped branch's strings are built
identically by the surviving twin. Cost ≈ a few bitset lookups per expansion.
Biggest payoff here in the exhaustive DFS (duplicate-subtree merging); in beam
it only frees width slots since dominated candidates already lose on any
admissible bound. Details: JOURNAL 2026-07-29 (field news) and
`../../extraDocs/2026-07-29-tomaz-kristan-5906-repeat.md`.
