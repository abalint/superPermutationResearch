# Cross-class surgery design (s28)

Design doc for HANDOFF-S28 item 1 — the flagship structural move after s26
killed splicing and s26c revealed the 8-allocation corpus. Per Andrew's
standing directive: measurements and design BEFORE implementation. §2's
feasibility measurements were run 2026-07-29 (scripts committed alongside
this doc); every design decision below cites the measurement that forced it.

## 1. Why this, why now

s26 measured that the community corpus is splice-closed: recombining known
872s verbatim yields nothing new at any scale. s25's discriminator showed
single-move deviations from a record cost ≥ 2 chars. So the remaining
structural move is **surgery**: edits that change a walk's L0 allocation —
trade doors against sojourn boundaries — because every 871 lives in a
waste-146 allocation that is one unit edit from a specimen-backed anchor
(s27 neighbor map), and NO known 872's allocation hosts an 871
(LB-869 closes waste ≤ 143; s10/s11 close the in-grammar subregion).

The question this doc answers: **what does a legal allocation-changing edit
actually look like, and what instrument searches over them?** s26c gave us
918 non-records-class specimens to learn from; s27 gave us their door
pricing. What was missing is the walk-level mechanics of a real trade.

## 2. Feasibility measurements (drive every decision below)

Scripts: `analysis/trackb/surgery_feasibility.py` (full-corpus braid-state
census, ~4 min), `analysis/trackb/surgery_pairs.py` (cross-allocation
specimen pairs), `analysis/trackb/tail_autopsy.py` (cycle-level tail diff),
`analysis/trackb/tail_block_atsp.py` + `tail_block_sweep.py` (block-ATSP
prototype; production version is §4's build). Corpus = all 22,062 community
classes (`data/upstream872/`, forward-renumbered identity-start).

1. **Cross-allocation braid sharing is real and pair-complete.** The
   corpus braid has 10,034,458 states ((visited, cur), recomb.rs's key);
   **22,266 are shared by ≥ 2 allocations, and all 28 pairs of the 8
   allocations share states.** (143,5)×(145,3) — the pair the door-pricing
   work targets — share 8,011 states down to depth 231. Depth profile:
   opening-trunk-dominated (deciles 0–2 hold 21,040 of 22,266) with a thin
   tail reaching depth 584.
2. **Zero unequal-length reconvergences, corpus-wide, cross-allocation
   included.** Every shared state is reached at identical prefix length by
   every walk through it (s26's measurement 2, now at 75× the corpus and
   across allocations). No free improvement exists ANYWHERE in the known
   corpus's state graph: an 871 must create states no known 872 visits.
   Corollary: at a shared state, partial waste is equal, but the partial
   LEDGER may differ — allocation identity is not fixed by a shared prefix.
3. **Natural surgery specimens exist.** 11 cross-allocation walk pairs
   share a state at depth ≥ 250 (`surgery_pairs.py`, threshold sweep). The
   deepest: `872.up-b020caf20414` (142,6,0,0,0) and `872.up-0105a4b77ce8`
   (143,5,0,0,0) are **byte-identical for their first 584 perm visits**,
   then re-cover the same residual 136 perms two different ways at equal
   cost (163 chars). Four pairs are (142,6)×(143,5) trades; five are
   (140,6,1)×(145,3) — the w4-bearing trade against the records class.
4. **The unit trade is a block reordering with junction re-pricing.**
   Autopsy of the deepest specimen: both tails cover the SAME 24 cycles
   with the SAME per-cycle split compositions — the tails are the same
   three block-runs A, B, C in different orders. The (142,6) tail plays
   `(w1-entry) A ·w3· B ·w3· C` — the w1 entry extends the prefix's last
   sojourn (a merge). The (143,5) tail plays `(w2-entry) C ·w2· A ·w3· B`.
   Net: one door demoted to a w2 crossing, one extra sojourn boundary,
   char-for-char equal (163 = 163). **This is the (S+1, d3−1) unit edit of
   the waste-146 neighbor map, realized by nature as pure block
   reordering.** Junction prices are what the orderings buy.
5. **The deeper trade recomposes, not just reorders.** The w4-bearing
   specimen ((140,6,1)×(145,3), anchor depth 283, 75-cycle residual):
   15 of 75 cycles are covered with DIFFERENT split compositions across
   the pair (whole-6 ↔ 3|3 ↔ 2|4 ↔ ...). Multi-door trades change the
   composition census, so reordering-only search cannot express them —
   there is a move hierarchy (§3).
6. **Exact block-order optimization is feasible at real anchor depths.**
   Prototype (scratch `block_atsp.py`): decompose a tail into blocks
   (maximal w1-runs, cut at every w≥2 move), price junctions by overlap
   weight, solve the ATSP-path exactly. At the depth-584 anchor (26
   blocks): both specimen tails are **block-order-optimal** (ATSP optimum
   = 163 = actual; two distinct optimal orders = the two specimens.
   Cross-checked at depth 620 by full Held–Karp, optimum = actual = 121).
   Python scales to ~26 blocks (<1 s B&B, min-in-edge bound); ~33 blocks
   times out, and occasional ≤27-block instances take minutes — the
   min-in-edge bound is too weak; Rust + assignment-relaxation bound
   targets ~40 blocks (≈ 250-perm tails).
8. **Mini-sweep at anchor ≈ depth 585 (300-walk corpus sample,
   `tail_block_sweep.py`, 346 s): 249 of 249 solvable anchors are
   block-order-optimal, 0 improvements** (51 skipped at > 27 blocks;
   block counts 22–27, median 26). The 872s look block-order-optimal at
   this band the way their ≤25-perm tails are tablebase-optimal (s9) —
   the full-corpus sweep and DEEPER anchors are where I1's verdict lives,
   and a single improvement anywhere is an 871 candidate.
7. **Junction pricing is allocation-blind.** The ATSP cost function never
   mentions (S, d3, ...): a cheaper order lands in whatever allocation its
   junction weights imply — including specimen-free ones like
   (144,4,0,0,0) (zero known 872s) and the ip=1 targets. The instrument
   searches across the L0 shell natively, where every grammar-based
   instrument fixes caps upfront.

## 3. The move vocabulary

From measurements 4–5, surgery decomposes into two move tiers:

- **S1 — block reordering (junction re-pricing).** Preserve the residual
  cover's blocks (hence per-cycle compositions); permute their order;
  junctions re-price by overlap weight; entry move may merge with the
  prefix sojourn (w1) or open a boundary (w2+). Changes (S, d3, d4)
  freely within constant block set. Exactly searchable (measurement 6).
- **S2 — recomposition.** Change how cycles are split into sojourn parts
  (whole-6 ↔ 3|3 ↔ 2|4 ↔ 2|2|2 ↔ 1|5). Required for multi-door trades
  (measurement 5). Search space = the sojourn grammar from a mid-walk
  state under TARGET caps rather than the walk's own — a grammar-engine
  build, staged behind S1's verdict.

Anchors (where surgery applies): any deep state of any known 872 — the
cross-allocation shared states of measurement 1 are the ones where two
covers are already known, but every state on every walk is a candidate cut
point. Measurement 2 says the anchor itself never gives improvement; the
saving, if it exists, is strictly inside the re-cover.

## 4. Instrument I1 — `tail-atsp` (build this)

New Rust subcommand. Per (walk, anchor): decompose the tail into blocks,
build the junction cost matrix (overlap weights; node 0 = anchor cur,
free path end), solve the ATSP-path EXACTLY (B&B; lower bound =
assignment relaxation on the unvisited submatrix, falling back to
min-in-edge sum; incumbent = the walk's own order). Output per anchor:
`blocks, actual, optimum, verdict` — and on `optimum < actual`, materialize
the reordered walk, self-validate, and write the candidate to
`data/surgery_finds/` with a LOUD banner (then: M3 gate + validator, the
s27b ritual, before ANY claim).

Sweep mode: all 22,062 archive walks × anchors at every block boundary in
depth ∈ [D_min, 720−25] (the last ~25 perms are tablebase-proven optimal —
s9 — so anchors there are pointless; D_min set by the ~40-block ceiling).
Estimated cost: the corpus sweep at one anchor band ≈ 22k exact solves;
Rust B&B at ≤ 40 blocks should hold well under the 30-min launch-protocol
line — measure on 100 walks first, and batch with heartbeats if not.

Verdict semantics (honest claims):

- **Any improvement = an 871 candidate** (tail cost −1 at equal prefix) —
  instant M3-gate event. Even −0 ties that land in NEW allocations are
  reportable (a first 872 in (144,4) or ip=1 would be an M3-class novelty
  and a neighbor-map event; collect ties whose implied allocation differs
  from the source walk's).
- **No improvement corpus-wide = a new corpus law**: "every known 872 is
  block-order-optimal from depth D" — the fixed-decomposition caveat
  stated ALWAYS (an 871 could still recompose; that's S2's question).

Controls & pins (write as tests before the sweep):

- The depth-584 specimen pair: 26 blocks, optimum = actual = 163, and the
  OTHER specimen's order is among the optima (verifies the solver sees
  cross-allocation orders).
- Held–Karp cross-check pin at ≤ 20 blocks (measurement 6's 121).
- n=5: every 153-record tail must be block-order-optimal (153 is proven
  optimal; any "improvement" is a solver bug).
- A hand-mangled tail (swap two blocks, +1 char) must be repaired to the
  original cost.

## 5. Instrument I2 — anchored re-cover under target caps (staged)

S2's engine: from an anchor state (cur, visited, partial ledger), search
covers of the residual set with the sojourn grammar under a TARGET
allocation's caps+profile — the 13 distance-1 waste-146 targets and the 3
ip=1 targets are the interesting cap sets. This is `sojourn-dfs`
generalized to a non-identity mid-walk start plus `beam --seed-file` /
NRPA warm-start as completion engines; the anchor's residual is ~136–450
perms, exactly the blocked zone, so expect bound-blocking — the honest
budget is "exhaust shallow anchors (≤ ~150 residual perms), truncate-and-
report elsewhere". **Build only after I1's sweep verdict**: if I1 finds
candidates, I2 prioritizes their anchors; if I1 proves block-order
optimality, I2 is the only remaining door and its design gets its own
measurement pass (which recompositions do the 15 recomposed cycles of
measurement 5 actually use? — that census bounds I2's branching).

## 6. Staging

1. **Build I1** (`src/tailatsp.rs` + `tail-atsp` CLI, controls of §4).
2. **Anchor-band sweep** over the corpus, shallowest-feasible D_min;
   collect improvements AND new-allocation ties.
3. **Verdict** → JOURNAL: candidates through the M3 ritual, or the
   block-order-optimality law with its depth frontier.
4. **I2 design pass** (recomposition census on the 15 cycles + the s27
   door-pricing bands) — separate doc section, conditional on 3.

## 8. s28 build outcomes (same day — I1 is BUILT and the first sweeps ran)

`src/tailatsp.rs` + `tail-atsp` CLI landed with all §4 controls as tests
(n=5 proven-optimum control, mangled-order repair, materialize identity
round-trip, HK/B&B agreement, the 8 committed allocation specimens
pinned block-order-optimal at anchor ≥ 585). Implementation notes: the
anchor adapts per walk (cut moves DEEPER until the instance fits
`--max-blocks` — nothing is skipped); B&B bound is two-tier (min-in-edge,
then Hungarian assignment relaxation only where the cheap tier fails to
prune); ~1000× the Python prototype (300 walks: 0.3 s vs 346 s).

**The oracle passed end-to-end, crossing an allocation boundary.**
`tail-atsp --ties` anchored at the natural cut of the specimen pair
(committed at `data/surgery_specimens/`), run from the (143,5) side,
re-derives the (142,6) partner BYTE-IDENTICALLY as an equal-cost tie,
and `m3_check.py` classifies the product as equivalent-to-known — the
full surgery pipeline (anchor → blocks → exact search → materialize →
validate → M3 gate) is proven on the one edit nature performed. Pinned
in `tailatsp::tests::tie_oracle_rederives_partner_across_allocations`.

**Sweep verdicts (fixed-decomposition caveat always):**

- Anchor ≥ 585 (≤ 27 blocks, ~136-perm tails): **all 22,062 community
  classes are block-order-optimal, 0 improvements** (23 s).
- Anchor ≥ 520 (≤ 40 blocks, ~200-perm tails): **all 22,062 classes
  block-order-optimal, 0 improvements** (875 s, ties not collected; the
  early 27 ms/walk probe underestimated — hard instances have a heavy
  tail, mean ≈ 40 ms).
- Anchor ≥ 450 (≤ 50 blocks): ~0.6 s/walk → full corpus ≈ 3.5 h; a
  launch-protocol run, queued for Andrew's go-ahead.

Next-step queue after the sweeps: tie CENSUS mode (count/collect
new-allocation ties corpus-wide — measures how connected the allocation
shells are under S1 alone), then the I2 design pass per §5.

## 7. Anti-goals

- **No unconditional impossibility claims from I1.** Fixed decomposition
  ⇒ "block-order-optimal", never "no 871 from this anchor".
- **Don't re-run splice search.** Measurement 2 closed it corpus-wide;
  I1's search space (new orders = new states) is disjoint by construction.
- **Don't build I2 speculatively.** Its cost is grammar-engine scale;
  gate it on I1's verdict (§5).
- **Don't sweep anchors in the tablebase zone** (last ~25 perms, s9) or
  past the ~40-block ceiling; both waste exactness where it's already
  spent or can't be had.

## 9. s29 measurement pass — the recomposition census (I2's design inputs)

Scripts: `analysis/trackb/recomp_census.py` (full-walk per-cycle
composition diff over controlled pairs, junction pricing, net-split
accounting), `analysis/trackb/recomp_doors.py` (door locality). A
controlled pair = two walks byte-identical to a shared depth
(`surgery_pairs.py`), so every composition diff is attributable to the
tails and both tails re-cover the SAME residual set. Sample: 11 deep
pairs (anchor ≥ 250) and the widened 1,071-pair set (anchor ≥ 150,
11 of the 28 allocation-pair types; (141,7) — the only 1|5-bearing
allocation, 4 classes — has no pair at depth ≥ 150 and is unmeasured).
28,664 recomposition events total. Findings, each a design constraint:

- **M-R1 (vocabulary).** Exactly 6 edit types occur: 6↔2|4 (17,202),
  6↔3|3 (8,797), 2|4↔3|3 (2,295), 2|2|2↔6 (218), 2|2|2↔2|4 (131),
  2|2|2↔3|3 (21). Compositions stay inside {6, 2|4, 3|3, 2|2|2} —
  **1|5 never participates in a natural recomposition.** I2's per-cycle
  move set is 4 compositions, not the 545-profile universe.
- **M-R2 (conservation).** Net splits over recomposed cycles = ΔS
  **exactly, 1,071/1,071 pairs**. Composition diffs fully account for
  the sojourn-count trade; doors balance the waste identity on top. So
  an I2 edit toward a target allocation has a KNOWN net-split budget:
  S_target − S_anchor (e.g. −1 for every S−1 waste-146 target).
- **M-R3 (rigid junction pricing).** Per event, the junction-weight
  delta is modal at 2× the part difference — one extra w2 entry per
  extra part — in ≈96% of events (16,630/17,202 at −2 for 6↔2|4;
  8,407/8,797 for 6↔3|3; 215/218 at −4 for 2|2|2↔6; 2,199/2,295 at 0
  for 2|4↔3|3). Every deviation is a door entering a part of the
  recomposed cycle. Composition edits are cost-predictable BEFORE
  search; doors are the only pricing wildcard.
- **M-R4 (door delocalization + target recurrence).** In the 11 deep
  pairs, 39 of 43 tail doors land on cycles that are NOT recomposed —
  door edits and composition edits are separable moves. And surplus
  door targets recur across unrelated pairs of the same allocation
  type: every (140,6,1) side spends `w4→145623, w3→142563, w3→142356,
  w3→156423`; every (142,6)×(143,5) unit pair demotes `w3→135426` and
  recomposes the SAME cycle `135462` (second part re-entered at
  `213546`, all four pairs). The unit trade is one specific recurring
  object, not a family.
- **M-R5 (natural ≠ minimal).** Median 28 recomposed cycles per
  controlled pair (max 40) against net budgets ≤ 5 — opposite-direction
  events mostly cancel. Nature does not exhibit minimal edits; whether
  a MINIMAL edit (net −1 in one or few events) can complete at all is
  exactly the open question I2 tests.
- **M-R6 (spread).** 114/120 cycles participate corpus-wide; no global
  concentration (top cycle 514/28,664). Per-family concentration is
  real (M-R4) but I2 cannot restrict its cycle set a priori. (The 6
  never-recomposed cycles are opening-trunk cycles covered inside the
  shared prefixes — a control artifact, not structure.)
- **M-R7 (entry reuse, partial).** In ~65% of events the coarser
  side's part-entry perms are a subset of the finer side's — split
  points prefer to reuse the whole cover's entry — but 35% introduce
  new entries. I2 must allow new entry perms (door-atlas edges), with
  reuse as a search-order heuristic, not a constraint.

**Also sharpened by this pass (corrects §2.4's reading):** the
(142,6)↔(143,5) unit trade is NOT composition-preserving. The full-walk
diff shows exactly ONE recomposed cycle — the anchor-seam cycle, whose
entry merge/split is the S±1 — which the in-tail autopsy could not see.
Block reordering reaches it because reordering changes which block
merges with the prefix sojourn: **S1 can recompose exactly the seam
cycle and nothing else.** That is why the tie oracle crossed the
allocation boundary, and why interior recompositions (the w4 pairs,
14–29 cycles) are strictly I2 territory.

### I2a — the merge-move instrument (build first)

The cheapest I2 move with a direct 871 payoff: for each (walk, anchor),
for each tail cycle covered with a SPLIT composition (both parts inside
the tail; straddling cycles need a shallower anchor), merge it whole —
replace its parts with one 6-block (entry at either part's entry, exit
re-priced) — and re-solve the block-order ATSP exactly on the modified
block set. Net −1 part = the S−1 unit edit = **waste 146 = an 871
candidate** if the ATSP completes at tail cost −1. This extends I1 with
one move tier while keeping exactness; per-solve cost ≈ I1's. Verdict
semantics mirror §4: any completion at −1 → M3 ritual; none corpus-wide
→ "no single-merge 871 within anchored tails" (vocabulary-and-anchor
caveat stated always). Split moves (6→3|3 etc., 3–6 rotations per
cycle) and door demotion enter only as compensating moves for net-0
targets — staged behind the merge sweep's verdict.

### The closure picture (s30–s32 sweep verdicts, read together)

Every exact single-edit instrument has now swept the corpus, and they
agree. With the fixed caveats stated once here (anchored tails only;
single edits; recomposition class-novelty sampled, not exhaustive —
full sweep queued):

| move type | band swept | moves | product |
|---|---|---|---|
| S1 reorder (I1) | ≥ 450 (~270-perm tails) | all orders, exact | 0 improvements |
| S1 ties | ≥ 520 | all equal-cost orders | **1** cross-allocation 872 — the specimen pair |
| S−1 merge (I2a) | ≥ 520 | 488,350 | 0 improvements; **1** equal 872 — the same pair |
| recomp-1 (I2a) | ≥ 585 (probes, 138 walks) | ~175k | 0 improvements; 48% equal-cost, all sampled M3-known |
| S1 ties, deep | ≥ 585 | full corpus | 0 cross-allocation ties (the known one sits at 580) |
| splice (s26b) | whole walks | full braid | closed up to symmetry |

**The known-872 corpus is closed under every local move built so far,
and the 8 allocation shells are connected by exactly ONE edge — the
(143,5)↔(142,6) door-demotion the natural pair performs.** (144,4) is
never reached; no ip=1 allocation is ever reached; the equal-length
shell is locally dense (half of all recompositions re-complete at 872)
but every sampled product is a known class. An 871 therefore differs
from every known 872 by a COMPOUND edit — at least two coordinated
recompositions (the census conservation law fixes the budget arithmetic)
— or by divergence earlier than the anchorable zone (~depth 450).

### I2b — grammar re-cover (staged behind I2a)

Unchanged from §5 (sojourn-dfs from a mid-walk state under target
caps), now with measured bounds: branching from M-R1's 4 compositions,
budget pruning from M-R2, cost model from M-R3. Required for the ip=1
targets, which no composition edit can express (i2 is a move-class
change, not a recomposition).

## 10. s35 — the multi-move tier (I3) design

Standing directive honored: this section precedes any code. Inputs: the
§9 census laws, the §"closure picture" (single edits are dead at both
n), and the s34–s35 2-loop frame.

### 10.1 The 2-loop frame (new, s34–s35 — the cycle-level conservation law)

`analysis/counting/loop_census.py` (exit-0 verifier). For a walk, let
L = number of DISTINCT 2-loops its w2 edges lie on (phase-specific
loops, n!/(n−1) of them; a w2 edge a→b lies on the loop generated by
rot(a)). Measured exceptionless on 22,062 n=6 872s + 4 off-shell 873s
+ all 87 known n=7 walks (three lengths, two n):

    L = S + #doors − ((n−1)! − 1)                     [loop-count relation]
    length = n! + (n−1)! + (n−3) + Λ,  Λ = L + Σ_{w≥4}(w−3)·inter[w]

(The two are arithmetically equivalent given the s22 waste identity;
the loop-count relation is the new content — how many distinct 2-loops
a walk uses is DETERMINED by its sojourn count and door count. Likely
a small theorem; derivation is an open task, flagged in THEORY.md §6.
Until derived, both carry corpus-law status.)

Consequences for compound-edit design:

- **One character = one Λ-unit.** An 871 is a Λ=28 object (n=6), a
  5905 is Λ=141 (n=7). Every improving edit must reduce Λ: remove one
  distinct 2-loop from the cover, or demote a heavy door w→w−1 (w≥4).
  The n=6 waste-146 targets restate as: S−1 at fixed doors ⇒ L drops
  by 1 (merge two sojourn-groups sharing a loop); d3−1 ⇒ L drops by 1
  too (one less door, S fixed). There is no Λ-neutral route to −1.
- **T4 prune (cheap, new):** a candidate compound whose local loop/door
  deltas are Λ-neutral cannot shorten the walk — skip its exact
  re-solve. Computable at enumeration time from the two variants' arc
  structures, before any ATSP work.

### 10.2 Targets and budgets (what a compound must accomplish)

n=6 (from §2 + M-R2): every 871 sits in a waste-146 allocation one
unit from the 8 anchors. Two families, each with FIXED arithmetic:
  - S−1 targets: net splits = −1 (M-R2) across the compound, doors
    unchanged; Λ via L−1.
  - d3−1 targets: net splits = 0, one w3 door removed (door demotion
    is a separable move, M-R4, with recurring specific targets).
n=7 (s33 map): same two families around the 6 shells at waste-859;
  the Kristan seam — (844,17)↔(843,18) is nature's only n=7 shell
  edge and is NOT a single tail edit (s33) — becomes I3's first
  existence question: is it a 2-recomposition compound in-band?

### 10.3 Measurement M-2 BEFORE build: recomposition co-occurrence

The census (M-R5) says natural pairs recompose a median 28 cycles
against net budgets ≤ 5 — nature is non-minimal. What it did NOT
measure: the JOINT structure. Before building the pair enumerator, run
a co-occurrence pass over the 1,071 controlled pairs
(`analysis/trackb/recomp_census.py` machinery already computes
per-cycle events):

  M-2a  For each pair of recomposed cycles in one controlled pair:
        are they in the same 2-loop? door-adjacent? within k perm
        visits in either walk? (Joint-locality histogram.)
  M-2b  Restricted to the minimal-flux controlled pairs (net ≤ 5,
        fewest recomposed cycles): which composition-type pairs
        (6↔2|4 with 3|3↔6, …) carry the net? (The canceling bulk vs
        the paying edit.)
  M-2c  The four natural (142,6)×(143,5) unit pairs: FULL joint
        autopsy — the one known shell edge, as a template for what a
        minimal compound looks like end-to-end.

Products: a joint-locality prior (restrict I3's cycle-pair set), a
pair-type prior (order the variant pairs), and a reality check on
whether ANY natural pair is close to minimal (if none is, I3 searches
outside nature's exhibited moves — stated in every verdict).

### 10.4 Instrument I3 — `tail-atsp --recomp2` (build AFTER M-2)

Move space: unordered pairs {(cycle_i, variant_a), (cycle_j, variant_b)},
i ≠ j, from recomp-1's per-cycle variant enumeration (same-cycle
compounds are already inside recomp-1's full arc-partition sweep).
Unpruned size at the n=6 585 band: ~1,300 single moves/walk → ~845k
pairs/walk × ~4 ms/exact-re-solve ≈ 1 h/walk — unusable. Pruning
tiers, in evaluation order (cheapest first, each measured before the
next is built):

  T1 budget (M-R2): combined net-split = ΔS(target) ∈ {−1, 0}.
  T2 vocabulary (M-R1): compositions inside {n, 2|4, 3|3, 2|2|2};
     1|5 arcs opt-in only (broader-negative mode).
  T3 admissible price precheck (M-R3): optimistic junction delta
     (rigid −2/part + best-case door absorption) must reach
     ≤ incumbent − 1; modal pricing is NOT assumed (deviations are
     door-mediated and must stay reachable).
  T4 Λ-neutrality (10.1): skip pairs whose loop/door deltas cannot
     reduce Λ.
  T5 (only if T1–T4 leave > ~1k pairs/walk): joint-locality prior
     from M-2a — cycle pairs outside the measured co-occurrence
     support go last (ordering, not exclusion — else a completeness
     caveat attaches to every negative verdict).

Exactness: surviving pairs get the full apply + incumbent-seeded
block-ATSP re-solve, same bookkeeping identity pin as recomp-1.
Verdicts/alarm path unchanged (§4): shorter ⇒ candidate ritual
(validate + m3_check at the right n); equal-length new-allocation ⇒
written + gated; a (844,17)→(843,18) equal at n=7 = the Kristan seam
FOUND — report loudly either way.

Controls (pinned tests before any sweep): n=5 proven-optimum (no
compound below opt − 1 with HK cross-check); synthetic composition —
apply two known equal-cost recomp-1 moves on disjoint cycles, verify
--recomp2 re-finds the composed state at the composed cost; the
seam-edit pin composed with a Λ-neutral second move must still price
at exactly inc − 1.

### 10.5 Staging

  1. M-2 census (Python, one session, no Rust).
  2. T1/T2/T4 enumeration-count measurement on the 8 n=6 specimens +
     8 n=7 round-robin walks (prune factors BEFORE solver work; if
     the product of measured factors leaves > ~5k exact solves/walk,
     design T5 from M-2a before building).
  3. Build --recomp2 + controls; probe; queue sweeps (n=7 first —
     87 walks, the whole corpus is a probe; then n=6 585 band).

Anti-goals: no k ≥ 3 compounds until k = 2 is swept closed; no learned
ordering inside I3 (Track C stays quarantined until its overhead fix);
no vocabulary widening and no ip=1 moves here (ip=1 remains I2b/grammar
territory — a compound of recompositions cannot express it).

### 10.6 M-2 RESULTS (s36 — measured; revises 10.3–10.5 where noted)

`analysis/trackb/recomp_cooccur.py` over the regenerated 1,071
controlled pairs (`surgery_pairs.py 150`; ~7 s):

- **M-2a — NO bulk joint locality; T5 is DEAD as designed.** Over
  389,218 recomposed-cycle pairs: used-loop sharing 14.2% vs null
  14.4%, w2-adjacency 7.3% vs 7.0%, door links 0.1% both, depth
  distance slightly WIDER than null, static-loop sharing BELOW null
  (20.3% vs 38.2%). The canceling bulk flux is delocalized (M-R4
  extended to pairs). T5 as a locality prior has no measured support
  — I3 relies on T1–T4 only.
- **M-2b — nature exhibits exactly TWO minimal 2-compounds, and they
  are the SAME object mirrored.** The recomps=2 controlled pairs
  (both |net| = |ΔS| = 2, both between (145,3) and (143,5) — the two
  LARGEST shells, which the s32 tie census proved S1-disconnected):
  `55088ebb4107×d141177d85e1` (anchor 180) and
  `00c66faaa43f×138d980ad903` (anchor 228) recompose the SAME two
  cycles with the SAME part entries — `126354` (2|4↔6, entries
  354126/263541) and `123654` (3|3↔6, entries 541236/236541) — two
  merges + two door promotions. As with the s29 unit trade, the
  natural 2-compound is ONE specific recurring object, not a family.
  And its cycle pair IS locally linked (1/1 in both) — minimal
  compounds are local even though bulk flux is not (recomps=6/8 pairs:
  ~40% local vs 14% bulk).
- **M-2b′ — anchor-reach constraint (revises 10.4).** The natural
  compound's parts sit at depths 181–718: an in-tail pair enumerator
  anchored at ≥ 520 could never have found it. --recomp2 must either
  run at anchors ~180 (block counts permitting — measure first) or
  handle straddling cycles (one part in-tail, one in-prefix), which
  single-edit I2a deliberately excluded. This is the concrete reason
  the closure picture holds: the compound tier lives across the
  midgame, exactly where s24 located the ranking failure.
- **M-2c — the unit-pair set widens 4 → 12.** All 12 (142,6)×(143,5)
  controlled pairs confirm the s29 story at depth ≥ 250 (single seam
  cycle `135462`); the 8 shallower ones bundle the unit trade with
  6–11 canceling recompositions — more evidence that only the deep
  pairs isolate minimal edits.
- **New pinned control for the I3 build (extends 10.4 controls): the
  natural-compound oracle.** From `872.up-55088ebb4107` ((145,3)) with
  anchor ≤ 180, --recomp2 applying the two merges on `126354` and
  `123654` must re-price to exactly equal length and re-derive
  `872.up-d141177d85e1`'s class ((143,5)) — nature's 2-compound,
  driven by the instrument. (Mirror: `00c66faaa43f` from the (143,5)
  side.)
- **Target arithmetic unchanged:** the natural compound is
  equal-length (net −2, +2 doors); an 871 needs net −1 at fixed doors
  (or net 0 with a demotion) — I3 searches a vocabulary nature uses,
  toward budgets nature doesn't exhibit. State this in every verdict.

### 10.7 s37 — feasibility + prune factors MEASURED (staging step 2); T4 CORRECTED

Python-only measurements on the 8 specimens (+ 45-file round-robin
corpus sample), pre-build per §10.5. Four verdicts:

- **Full-tail exactness at compound reach is INFEASIBLE; the straddle
  pivot is confirmed.** Blocks at anchor 180 ≈ 110 (corpus max 112)
  vs the demonstrated exact-B&B ceiling ~50 (anchor 450). No
  anchor-only instrument reaches the natural compound's 181–718 span.
- **Straddling is RARE — the extraction frame is cheap.** Mean 2.2
  straddling cycles per walk at anchors 450/520, each with exactly one
  prefix part. So I3's move space = tail-pair recompositions PLUS an
  optional single prefix-part extraction (remove one prefix part of a
  straddling cycle, heal its prefix seam exactly, add its perms as a
  floating/mergeable block, re-solve the tail). Block count grows by
  ≤ 1 (≈ 55 at anchor 450 — at the working edge, measure solve times
  in the build probe). The natural-compound A side (`55088ebb4107`)
  has 6 extraction candidates at 450, including the required
  `126354`@181.
- **T1/T2 factors (measured on the real variant space).** Raw
  cross-cycle pair space ≈ 2.0M/walk (anchor 520) / 3.7M (450) —
  larger than §10.4's estimate. T1 net −1 (the S−1 budget): 0.3% →
  6.2k / 12.2k pairs per walk. T1 net 0 (d3−1 family): 2.0%. Adding
  T2 (vocabulary on full cycles, 17/63) to net −1: **0.02% — ~470
  (520) / ~900 (450) exact re-solves per walk**, far under the §10.4
  ≤ 5k budget. Build order: T1+T2 sweep first; T1-only
  (broader-negative, 1|5-in) as the second pass.
- **T4 is TAUTOLOGICAL — downgraded from prune to assertion.** Given
  the s35 loop-count relation L = S + #doors − ((n−1)!−1), algebra
  gives Λ = waste − ((n−1)!−2): Λ-neutrality IS length-neutrality, so
  as an enumeration filter T4 admits exactly the pairs T1's budget
  arithmetic already admits. The relation's value stands as the
  cycle-level REFRAME (a 5905 is a 141-2-loop cover) and as a cheap
  internal consistency assertion on every materialized compound (the
  instrument should verify L + door terms against S and length and
  panic on mismatch — a solver-bug tripwire, not a prune).

**Green light (s38+): build `--recomp2`** = tail pair enumeration
under T1(+T2) at anchors 450/520 with single prefix-part extraction,
incumbent-seeded exact re-solves, the §10.4 controls plus the §10.6
natural-compound oracle (softened: the instrument must find AN
equal-cost (143,5) completion from the A side via the two merges;
its m3 class vs `d141177d85e1` is reported either way).
