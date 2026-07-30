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

### I2b — grammar re-cover (staged behind I2a)

Unchanged from §5 (sojourn-dfs from a mid-walk state under target
caps), now with measured bounds: branching from M-R1's 4 compositions,
budget pruning from M-R2, cost model from M-R3. Required for the ip=1
targets, which no composition edit can express (i2 is a move-class
change, not a recomposition).
