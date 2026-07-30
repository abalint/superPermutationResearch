# Lab journal

Newest entry first. Every working session appends an entry: what was done, what was
measured, what surprised us, what's next. This file is the "pick up where we left off"
mechanism — read it before touching code.

---

## 2026-07-30 (session 38b) — three farm sweeps folded (operator ran the queue back-to-back, Andrew-approved): **the n=7 pair-compound tier is CLOSED at the 4840 band — and unlike every earlier tier its equal-cost shell is EMPTY: 7,321,635 exact re-solves (from 1.57B raw pairs, 189 extractions), 0 improved, 0 equal-cost in ANY allocation, 0 Λ violations** — single recompositions sit on a dense equal plateau (48.5% at n=7, 48.2% at n=6: n-generic) but compounding two moves leaves the plateau entirely and strictly costs, so at this band the compound tier is closed to EQUALITY, not merely to improvement; recomp-1 closure extends 4905→4840 (297,232 moves, 0 events) and merge+ties extend to ~410-perm tails (NOT the ~440 the anchor implies — max-blocks 60 binds at n=7, observed anchors 4629–4689); **the Kristan seam (844,17)↔(843,18) is absent from all three sweeps**; and the loop-count relation now stands on 7.3M independent exact re-solves with zero violations

Fold-only entry (results verbatim in SWEEP-QUEUE, ops details in the
three `ops:` commits). What each run settles:

- **`n7a4840recomp`** (recomp-1, 87 walks, 47.3 s/walk): the n=7
  single-recomposition closure law extends from ~136-perm to ~200-perm
  tails — 297,232 moves, 0 improved, 0 new-allocation equals, Kristan
  seam never appears. Equal-cost rate 48.5% vs n=6's 48.2%
  (`a585recomp`): the dense-but-degenerate shell is not an n=6
  artifact. (The 585-band 200-sample M3 precedent — every sampled
  equal is its own source class — was not re-run at this band.)
- **`n7a4600seam` + `n7a4600seamfull`** (merge+ties): no S1 tie and no
  S−1 merge produces a cross-allocation walk anywhere in the n=7
  corpus down to ~410-perm tails; the Kristan unit-trade stays
  unrealized. **Operator's caveat adopted as a standing trap: at n=7
  the BLOCK CEILING binds, not the anchor** — every walk hit
  `--max-blocks 60` and cut deeper than requested (4629–4689 vs 4600),
  so band claims must quote observed anchors, and a true ~440-perm
  band needs 70–80 blocks = a different exact-solve regime.
- **`n7a4840recomp2`** (I3, 8.5 min wall on 12 workers): the headline
  above. Funnel: 1,574,583,671 raw pairs → 9,673,573 post-T1 (0.61%)
  → 7,321,635 exact re-solves (net −2/−1/0 = 49,735/943,145/6,328,755).
  All three tripwires silent (no candidate, no Kristan banner, no Λ
  violation). The zero-equal result sharpens s38's §10.6 refutation
  from one walk to the whole n=7 corpus: pair compounds don't explore
  a wider equal plateau, they strictly cost — consistent with the
  natural compound pricing +6, and further evidence that equal-length
  compound crossings need midgame ORDER, which no anchored instrument
  offers. THEORY §6's loop-relation entry now cites the 7.3M-solve
  calibration.

**Still queued (approval pending):** n=6 recomp2 520-band tight
(round-robin probe first, reshipped binary `bdc9625` already on the
PC) and the 450-band probe-only entry.

**Handoff refreshed (s38c):** `docs/HANDOFF-S38.md` written (supersedes
HANDOFF-S37) — the midgame-order front as work-menu item 1, the
as-built instrument stack, the new traps (block ceiling binds at n=7;
single-walk probe bias; §10.8 wins over §10.4 where they disagree;
extraction is provably lossy — don't re-hope it), and the cold-start
reading order. CLAUDE.md, OPS-BACKGROUND-AGENT.md and
RESEARCH-AGENT-S29.md repointed.

## 2026-07-30 (session 38) — I3 BUILT (`tail-atsp --recomp2`, SURGERY-DESIGN §10.8) and its first measurement KILLS the extraction hope: **the natural 2-compound is NOT expressible at anchored reach — extraction AND absorption of the `126354`@181 part both price exactly +6 over equal (the part is entered by a w2 edge; any local seam repair re-spells a full window), while nature's compound enters both whole-6s through w3 doors that exist only under a globally different midgame order** — the compound tier lives in midgame ORDER, not midgame depth (M-2b′ sharpened; the s24 blocked zone indicted a third time, now at certificate level); first sweeps: A side @520 = 111,216 exact re-solves, **zero equal-cost completions of any kind**, zero Λ violations, 6 min/walk; n=7 @4840 = 75,201 solves, 89 s/walk, zero events — the whole-corpus n=7 sweep (~2.2 h) is queued

Rust session; 139 tests green (133 + 6 new pins); clippy/fmt clean.
The build follows SURGERY-DESIGN §10.4/§10.6/§10.7 with two corrections
found while building (both now in §10.8):

**Built (src/tailatsp.rs + CLI).** `--recomp2` = distinct-cycle variant
PAIRS from recomp-1's enumeration, plus one context per extraction
candidate (straddling cycle, exactly one prefix part: float the part
into the tail, hard-heal the prefix seam x→y, then identity + single +
pair moves on the extended instance — extraction+single is itself a
2-compound recomp-1 never tried). Incumbent-seeded exact re-solves;
every complete find is validated, allocation-classified, and checked
against the s35 loop-count relation (the T4 tripwire — banner, never a
prune; `loop_relation` mirrors loop_census.py in Rust). Kristan-seam
banner at n=7. Flags: `--recomp2-wide` (T2 off), `--recomp2-tight`
(nets −2/−1 only, ~4× cheaper).

**Correction 1 — T1 must admit net −2.** §10.4 wrote ΔS ∈ {−1, 0};
nature's own minimal compound is net −2 (two merges + two door
promotions, equal length) — the budget as written excluded the
mandatory oracle by construction. Built range: {−2, −1, 0}.

**Correction 2 — T2, n-generically.** M-R1's vocabulary {6, 2|4, 3|3,
2|2|2} is exactly the singleton-free compositions of 6, so T2 as built
= "the moved cycle's full composition (remaining prefix parts + new
arcs) contains no part of size 1". s37's ~470–900 solves/walk figure
assumed net −1 only and a full-cycles-only vocabulary reading; the
as-built instrument solves ~100× more and is still affordable (below).

**The s38 headline — the §10.6 oracle FAILS, with mechanism.** From
`872.up-55088ebb4107` (A side, (145,3)) at anchors 455 AND 523: all 36
whole-6 × whole-6 entry pairs on `126354`+`123654` after extraction of
`126354`@181×4 are REFUTED at equal length; the B-entry compound's
true optimum is +6 over equal (108 vs 102 / 82 vs 76, materializing to
a valid 878), extraction-identity alone is +6, and the mirror move
(absorption: extend the prefix part's ride to the whole-6 in place,
`tests/s38_measure.rs`) is also +6, because w_in=2 → w_new=6. The
mechanism is general: the part sits behind a w2 entry, and no local
repair of a w2 seam costs less than a full re-spell. Nature's B side
pays w3 doors into whole-6s at depths 502/630 — positions no
extraction/absorption at A's seams can offer. Verdict pinned as a
regression test (`natural_compound_refuted_at_anchored_reach`).
Strategic consequence: I3's product is the pair-closure negative (plus
any novel finds); reaching the compound tier needs a midgame-order
instrument — the same wall the completion-policy work (s23–s25) faces
from the search side.

**First sweeps (single-walk probes; round-robin before any farm
projection).** A side @523/41 blocks: 5.98M raw pairs (3 contexts),
181,300 post-T1, 111,216 solves (net −2/−1/0 = 2,772/24,738/83,706),
zero equal-cost completions, zero improvements, zero Λ violations,
367.5 s — net ≤ 0 moves essentially never complete equal at deep
anchors, pairs included (the merge law extends to compounds). n=7
`02d771908307` @4840/33 blocks: 75,201 solves, 89.1 s, zero events.
Three queue entries appended (n=7 4840 whole-corpus ~2.2 h FIRST, n=6
520 tight ~1 day farm, n=6 450 probe-only); the 450-band full-net
single-walk probe (54 blocks) was killed unfinished — two attempts,
> 10 and > 12 solver-minutes each without completing one walk, i.e.
≥ 2× the 520 cost with no upper bound measured; full-net 450 is off
the table pending a tight round-robin probe (see the queue entry).

**Folded: `a585recomp` (operator, farm, done).** The single-edit tier
is CLOSED at the 585 band corpus-wide: 27,873,361 recompositions over
all 22,062 classes, 0 improved, 0 new-allocation equals, 13.4M (48.2%)
same-allocation equals; a 200-file random M3 sample of the emitted
equals is 200/200 equivalent-to-known AND each to its OWN source class
— the equal-cost neighbourhood is huge in moves, one point in class
space. (Strong evidence, not exhaustion: 2/walk sampling.)

**Farm note (operator):** s38 changed `src/tailatsp.rs` ⇒ cross-compile
+ reship before ANY post-s38 farm run. A fresh
`x86_64-pc-windows-gnu` build was made this session (see OPERATIONS).

**Next session, concretely:** run the n=7 recomp2-4840 sweep when
approved (it's the whole corpus — the Kristan-seam existence question
under pair compounds); round-robin-probe the n=6 520 tight sweep and
queue-revise; the two older n=7 queue entries still pending; then the
open list unchanged (loop-count relation derivation, ip=1 study,
per-allocation NRPA, Track C overhead).

## 2026-07-30 (session 37) — I3 staging step 2 MEASURED (SURGERY-DESIGN §10.7), build green-lit with a corrected design: **full-tail exactness at compound reach is infeasible (~110 blocks at anchor 180 vs the ~50 exact-B&B ceiling) but the straddle pivot is CHEAP — straddling cycles are rare (mean 2.2/walk at 450/520, one prefix part each), so I3 = tail pair-recomp + single prefix-part extraction at anchor 450 (blocks ≤ ~56)**; prune factors measured on the real variant space: raw pair size 2.0M/walk (520) / 3.7M (450), T1 net−1 cuts to 0.3%, +T2 vocabulary to **0.02% ≈ 470–900 exact re-solves/walk** — far under budget; and an honest correction: **T4 is TAUTOLOGICAL** (the loop-count relation makes Λ = waste − ((n−1)!−2), so Λ-neutrality IS length-neutrality) — downgraded from prune to solver-bug tripwire assertion

Python-only session; 133 tests green; no Rust yet (that is s38).

**Measured (all in §10.7):**
- **Blocks vs anchor** (8 specimens + 45-file round-robin sample):
  ~110 blocks at anchor 180 (max 112), 54 at 450, 40 at 520. The
  compound tier's 181–718 span is unreachable by any full-tail exact
  instrument — confirming the M-2b′ pivot.
- **Straddle frame is tiny:** 2.2 straddling cycles/walk (450 and
  520), each exactly one prefix part. Extraction (remove one prefix
  part of a straddling cycle, heal the seam exactly, float its perms
  as a mergeable block, re-solve the tail) adds ≤ 1 block. The
  natural-compound A side has 6 extraction candidates at 450
  including the required `126354`@181.
- **T1/T2 factors:** cross-cycle pair space 2.0M/walk (520) / 3.7M
  (450); T1 net −1 → 0.3% (6.2k / 12.2k); T1 net 0 → 2.0%; T1+T2
  (vocab 17/63 on full cycles) net −1 → 0.02% = ~470/~900 exact
  re-solves per walk. Build order: T1+T2 first, T1-only
  (broader-negative, 1|5-in) second.
- **T4 correction:** with L = S + #doors − ((n−1)!−1), algebra gives
  Λ ≡ waste − ((n−1)!−2) ⇒ Λ-neutral = length-neutral. As a filter it
  admits exactly what T1's budget admits — nothing. Kept as an
  internal consistency assertion on every materialized compound (the
  cycle-level REFRAME stands; its pruning power was already inside
  the waste identity).

**Green light (s38): build `--recomp2`** — tail pair enumeration
under T1(+T2), single prefix-part extraction, incumbent-seeded exact
re-solves at anchors 450/520, §10.4 controls + the softened §10.6
natural-compound oracle (find AN equal-cost (143,5) completion from
`55088ebb4107` via the two merges; report its m3 class vs
`d141177d85e1` either way). Farm note for the operator: s38 will
change `src/tailatsp.rs` — reship before any farm run after it lands.

**Still open:** fold `a585recomp` (operator); the two pending n=7
queue entries; ip=1 study; per-allocation NRPA/beam; Track C overhead.

**Handoff refreshed (s37b):** `docs/HANDOFF-S37.md` written (supersedes
HANDOFF-S32) — six-sentence state of the world, the n-generic
instrument stack, the s38 build-first work menu with spec pointers
into SURGERY-DESIGN §10, and the trap list (now including s37's
tautology-check lesson). CLAUDE.md reading order and the stale
HANDOFF-S28 references in OPS-BACKGROUND-AGENT.md /
RESEARCH-AGENT-S29.md now point at it.

## 2026-07-30 (session 36) — M-2 co-occurrence census RUN (`analysis/trackb/recomp_cooccur.py`, 1,071 controlled pairs, 7 s): **T5 is dead (zero bulk joint-locality: used-loop 14.2% vs null 14.4%), but nature exhibits exactly TWO minimal 2-compounds and they are the SAME object mirrored — (145,3)↔(143,5), the two LARGEST shells (S1-disconnected per s32), bridged by two merges + two door promotions on the SAME two cycles `126354`(2|4↔6) + `123654`(3|3↔6) with the same part entries, recurring across independent controlled pairs** — the compound tier's existence proof, its first pinned oracle, and a hard anchor-reach constraint: the compound's parts span depths 181–718, so `--recomp2` at anchor ≥ 520 could NEVER find it — the compound tier lives across the midgame (the same band s24 indicted)

Continuation session (same day as s33–s35). Python only; 133 tests
green. Design doc updated in place: SURGERY-DESIGN §10.6 (M-2 results,
revising §10.3–10.5 where measured).

**Built — `recomp_cooccur.py`** (imports recomp_census machinery; walk
cache): M-2a locality flags per recomposed-cycle pair (static 2-loop
sharing, USED 2-loop sharing, w2 adjacency, door links, depth
distance) against a non-recomposed tail-cycle-pair null; M-2b
minimal-flux table; M-2c unit-pair autopsies. Pairs TSV regenerated
with `surgery_pairs.py 150` (54 s, not committed — regeneration is one
command).

**Verdicts (each now in SURGERY-DESIGN §10.6):**
- **M-2a: no bulk locality.** 389,218 recomposed-cycle pairs sit at
  the null on every measure; static-loop sharing is actually BELOW
  null (20.3% vs 38.2%). The canceling flux is delocalized — T5 has
  no support; I3 prunes are T1–T4 only.
- **M-2b: the minimal-compound population is different.** recomps=2
  pairs: 2 (both |net|=|ΔS|=2, both (145,3)×(143,5), both the same
  two cycles + entries, cycle pair locally linked 1/1); recomps=6/8
  pairs: ~40% local. Minimal compounds are local and SPECIFIC —
  exactly like the s29 unit trade, the natural 2-compound is one
  recurring object.
- **M-2b′: anchor reach.** Parts at depths 181–718 ⇒ the compound
  tier is invisible to deep-anchored tail instruments; --recomp2
  needs anchor ~180 (measure block counts first) or straddling-cycle
  support. This RESOLVES why the closure picture holds while shells
  are provably compound-connected.
- **M-2c: 12 unit-type controlled pairs** (4 deep = clean single-seam
  `135462`, as s29 said; 8 shallow bundle it with 6–11 canceling
  events).
- **New pinned oracle for the I3 build:** from `55088ebb4107`
  ((145,3)), anchor ≤ 180, the two merges must re-derive
  `d141177d85e1`'s class at equal length (mirror from `00c66faaa43f`).

**Next session, concretely (s37):** staging step 2 — T1/T2/T4 prune
factors + block-count measurement at anchor ~180 on the 8 n=6
specimens (is exact block-ATSP even feasible at ~540-perm tails? if
not, the I3 design pivots to straddling-cycle support at moderate
anchors before any build); fold `a585recomp` when the operator lands
it; the two n=7 queue entries if approved.

## 2026-07-30 (session 35) — Multi-move tier DESIGNED (SURGERY-DESIGN §10: I3 = `tail-atsp --recomp2`, pair compounds with prune tiers T1 budget / T2 vocabulary / T3 admissible price / T4 Λ-neutrality / T5 co-occurrence, M-2 measurement pass specced BEFORE build per the standing directive) on top of a NEW conservation law found while designing: **the loop-count relation `L = S + #doors − ((n−1)!−1)`** — equivalently `length = n! + (n−1)! + (n−3) + Λ`, `Λ = L + Σ(w−3)·heavy doors` — **exceptionless on 22,062 n=6 872s (Λ=29: pure-w3 classes L=29, the 397 single-w4 L=28, the 18 double-w4 L=27), 4 off-shell 873s (Λ=30, incl. a wild 23-door allocation), and all 87 n=7 walks (Λ=142/143)** ⇒ one char = one Λ-unit: an 871 is a Λ=28 object, a 5905 is Λ=141, and NO Λ-neutral edit can shorten a walk — the cheap new prune for every compound enumerator

Continuation session (same day as s33/s34). No Rust changes; 133 tests
green. The two n=7 queue entries stand in SWEEP-QUEUE with `approved:`
fields for Andrew (recomp-4840, deep-seam 4600); the operator's n=6
`a585recomp` farm sweep still runs.

**Measured first (design-before-code directive): the 2-loop census at
n=6.** s34's L1 (every 5906 = exactly 142 2-loops) begged the n=6
question. `analysis/counting/loop_census.py` (n-generic, exit-0
verifier) over all 22,062 classes: L is NOT invariant — it splits
27/28/29 — but the split lands EXACTLY on the w4-bearing allocations:
L + #w4 + 2·#w5 = 29 with zero exceptions (the 18 double-w4 classes at
L=27, the 397 single-w4 at L=28, all pure-w3 at L=29). Heavy doors
substitute for 2-loops at exactly (w−3) loops per door. Off-shell
probe: all four local 873s satisfy Λ=30 exactly, including the wild
(S=120, 18×w3+4×w4+1×w5) stratified-beam walk — so this is not a
record-shell artifact. Algebra against the s22 waste identity reduces
it to the loop-count relation `L = S + #doors − ((n−1)!−1)` (check:
Kristan 843+18−719=142 ✓, wild 873 120+23−119=24 ✓). Likely a small
theorem — derivation flagged OPEN in THEORY.md §6; corpus-law status
until proven.

**Designed — SURGERY-DESIGN §10 (I3, the multi-move tier).**
- §10.1 the 2-loop frame: improvement ⇔ Λ−1 (remove a distinct
  2-loop or demote a heavy door); T4 = skip exact re-solves for
  Λ-neutral pairs, computable from arc structures pre-ATSP.
- §10.2 budgets: S−1 targets need net-split −1 (M-R2), d3−1 targets
  net 0 + separable door demotion (M-R4); n=7 instantiation includes
  the Kristan-seam existence question ((844,17)↔(843,18) as a
  2-recomposition compound — s33 proved it is no single edit).
- §10.3 M-2 co-occurrence census (RUN BEFORE BUILD): joint locality
  of recomposed-cycle pairs (M-2a), pair types carrying the net in
  minimal-flux controlled pairs (M-2b), full joint autopsy of the four
  natural unit pairs (M-2c) — machinery already in recomp_census.py.
- §10.4 the instrument: pair moves over recomp-1's variant
  enumeration; unpruned ~845k pairs/walk ≈ 1 h/walk is unusable, so
  T1–T5 with measured prune factors gate the build (target ≤ ~5k
  exact solves/walk); controls pinned in the doc (n=5 optimum,
  synthetic composition, seam-edit + Λ-neutral compound).
- §10.5 staging: M-2 → prune-factor measurement on specimens → build
  → probe → sweep n=7 FIRST (87 walks = the whole corpus is a probe).

**Next session, concretely (s36):** run M-2 (Python only); fold
`a585recomp` when the operator lands it; the two n=7 queue entries if
approved. Then the T1/T2/T4 prune-factor measurement (staging step 2)
— only after that does --recomp2 get built.

## 2026-07-30 (session 34) — twoCycles files DECODED, the s33 completeness caveat RESOLVED: the community `7_5906_twoCycles_*` files are per-string ANNOTATIONS (7/7 files bijective, group i = exactly the 142 2-loops its string traverses) — **the published n=7 corpus IS the 83 strings; our 84-class index covers all published data**; NEW 2-loop corpus laws (`upstream5906_twocycles.py`, exit-0 verifier): **every known 5906 uses EXACTLY 142 distinct 2-loops — invariant across all six L0 allocations and Kristan's class — every 5907 exactly 143, and length = 5764 + #2loops on all 87 walks** (waste = (n−1)!−2 + L; one char = one 2-loop; a 5905 is a 141-2-loop cover); operator doc updated with n=7 rates + n-generic alarm path

Continuation session (same day as s33). No Rust changes; 133 tests
green. Ops doc: `OPS-BACKGROUND-AGENT.md` alarm path is now n-generic
(`validate -n <n>`, `m3_check -n 7`), rates tables split n=6/n=7 with
the s33 measurements, and the stale 0.6 s/walk anchor-450 figure is
corrected to the true 2.0 s/walk (sorted-order bias).

**Decoded — the twoCycles notation.** Structure: Mathematica-style
nested lists; each `twoCycles_nsk<K>` file holds one GROUP per string
of its companion `nsk<K>` string file (group counts match string counts
file-by-file: 2,2,1,9,52,8,9 = 83), each group = 142 distinct 7-perms.
Semantics (solved empirically, then verified 83/83): 2-loops are
phase-specific (840 at n=7 = n!/(n−1); they do NOT partition the
perms); the jump-composed map g(q) = q2..q6 q1 q7 generates the 6
equivalent generators of a loop, so loop_id = min over the g-orbit; a
walk's w2 edge a→b lies on the loop generated by rot(a); a listed
tuple t denotes the loop generated by rot(t) (the pre-jump phase —
solved on the single-string kernel file at 142/142, then bijective
everywhere). **Wrong hypotheses killed on the way:** tuples are not
sojourn-entry perms (overlap ~ background 24/142); closure under
rotation + w2-swap applied anywhere is the whole graph (1 class of
5040), so naive '2-cycle partition' does not exist at walk level.

**The laws (all 87 walks, `analysis/counting/upstream5906_twocycles.py`
re-verifies, exit 0 = all pass):**
- **L1 (2-loop count invariant):** every known 5906 traverses exactly
  **142** distinct 2-loops — all six allocations, S from 836 to 844,
  Kristan's included; every known 5907 exactly **143**. The count is
  BLIND to the S↔door trade that separates the allocation shells.
- **L2 (length identity, corpus-calibrated):** length = n! + (n−1)! +
  4 + #2loops = 5764 + L on every known walk; equivalently waste =
  (n−1)!−2 + L. Egan n=7 (5908) sits at L=144: **each char saved is
  exactly one 2-loop dropped, so a 5905 in this frame is a 141-2-loop
  cover** — the cycle-level restatement of the hunt target, connecting
  the tail-surgery program back to the Track A cover framing.

**Why this matters for the hunt:** the n=6 fear (a 75× hidden corpus
behind our sample) does NOT recur at n=7 — closure laws quoted against
the 84-class index are quoted against everything published. And the
142-invariant is a new, sharp structural constraint: whatever compound
edit or early divergence produces a 5905, at the cycle level it must
REMOVE a 2-loop, not rearrange within the 142.

**Next session, concretely (s35):**
- **Multi-move tier design doc** (standing directive: design before
  code), now armed with both the n=6 conservation law and the n=7
  2-loop frame: compound edits must change L, not just repartition.
- Fold the operator's `a585recomp` n=6 farm result; the two pending
  n=7 queue entries if approved (recomp-4840, deep-seam 4600).
- Open: ip=1 study, per-allocation NRPA/beam, Track C overhead cut.

## 2026-07-30 (session 33) — n=7 CORPUS ASSEMBLED (84 known 5906 classes + 3 urdvr 5907s, all validator-complete; `data/upstream5906/` + `data/upstream5907/`, committed) and the ENGINE-GENERALITY TEST PASSED: every s28–s31 instrument runs at n=7 unchanged — I1 reorder (3 bands to ~270-perm tails), ties (2 bands), merge (3 bands), recomp-1 (full corpus, 199,391 moves) — verdict **the n=7 corpus is closed under every local move exactly like n=6's** (0 improvements, 0 cross-allocation products anywhere, 49% equal-cost same-allocation density, 174/174 recomp samples gate as rediscoveries); NEW structural map: **all 84 known 5906s are PURE-w3 over exactly 6 allocations** (waste 860 = (S−1)+#w3, no w4+, no intra), the dominant shell is (S=844, 17×w3) with 61 classes, and **Kristan's 5906 is the SOLE occupant of (843,18) — one S↔door unit-trade from the dominant shell, the precise n=7 echo of the n=6 natural pair — yet NO single tail edit connects them in the anchorable zone** (unlike n=6, where the seam surfaced at the 520 band); M3 gate now n-generic (`m3_check.py -n 7`, committed 84-class index)

Research-agent session; the operator's `a585recomp` n=6 farm sweep runs
in parallel (untouched). No Rust changes — the entire session is new
Python + data + sweeps, and that is itself the headline: `tail-atsp`
and the whole instrument ladder are n-generic AS BUILT. 133 tests
green, clippy/fmt clean.

**Built — n=7 corpus (`analysis/counting/upstream5906_dump.py`,
template upstream872_dump.py).** Sources, all local in `../extraDocs`:
the 83 published 5906 strings (community `known5906_corpus/7_5906_nsk*`,
7 files), Kristan's 5906 (`tk-5906-repeat.txt`, filtered to digits —
its "repeat" is bookkeeping, see 2026-07-29 note), and the three urdvr
5907s (`superpermutation-examples/n7/`). Canonicalization
(relabel+reversal, s26b convention): **84 strings → 84 classes** — the
83 published are pairwise inequivalent AND Kristan's is a genuine 84th.
All 87 files pass `validate -n 7 --complete`; corpus loader traces all
tight (Kristan's included — the simple-path reading is tight). The
archives are COMMITTED (530 KB; unlike n=6's 22,062-class archive) so
every n=7 sweep reproduces from a fresh clone. **Completeness caveat
(carry on every n=7 novelty claim): the community `twoCycles_*` files
are two-cycle EXTENSION SETS (set-of-tuples notation, thousands of
rows), not strings — undecoded, they may hide a much larger known
corpus (the n=6 lesson: our 296-string sample hid 22,062 classes).
Decoding them is queued work; until then "novel" at n=7 means
novel-vs-published-strings.**

**Built — M3 gate n-generic (`m3_check.py -n {6,7}`).** Per-n record
(872/5906) and committed canonical index
(`upstream5906_canon_index.tsv`, 84 classes). n=6 path regression-checked:
rebuilt index byte-identical to the committed one, specimens still gate
as rediscoveries, default invocation unchanged. Self-test: all 84 n=7
reps gate as rediscoveries (exit 0), 5907s report over-record.

**Built — n=7 structure census
(`analysis/counting/upstream5906_structure.py` →
`upstream5906_structure.tsv`).** T0 general identity holds 87/87
(verify_identity.py, exit 0). The L0 map:

| allocation (S, #w3) | classes |
|---|---|
| (844, 17) | 61 (73%) |
| (838, 23) | 9 |
| (840, 21) | 9 |
| (842, 19) | 2 |
| (836, 25) | 2 |
| **(843, 18)** | **1 — Kristan's, alone** |

All pure-w3 (no w4+, no intra) — cleaner than n=6's 8-allocation map
with its w4/w5 bearers. Waste 860 = (S−1)+#w3 throughout; the 5907s sit
at (858, 4): treelike, door-sparse, sojourn-heavy — a different design
regime entirely. **Kristan's class sits exactly one S↔door unit-trade
from the dominant shell — the same edit that forms n=6's one natural
edge (143,5)↔(142,6).**

**Sweeps (all local, minutes each — the n=7 corpus is 87 files, not
22,062).** Anchor bands scaled by perm count: 4905/5040 ≈ n=6's
585/720 (~136-perm tails), 4840 ≈ 520 (~200), 4770 ≈ 450 (~270).

- **I1 reorder: block-order-optimal corpus-wide at every band** —
  4905, 4840/b40, 4770/b50 (84+3 walks each, 0 improved, 0 skipped).
  The 5907s are also block-order-optimal (an improvement there would
  have been a new 5906).
- **Ties (4905, 4840): 0 cross-allocation ties.** The 6 allocation
  shells are S1-disconnected in these bands — at n=6 the one edge
  surfaced at 520-band depth; here NOTHING surfaces by ~200 perms.
- **Merge (4905: 595 moves; 4840: 1,141; 4770: 1,778): 0 improved, 0
  equal-cost completions at any band.** Stricter than n=6, where the
  520 band produced the specimen-pair rediscovery. **The Kristan
  unit-trade is NOT realizable as a single tail merge within the last
  ~270 perm visits of any known 5906.** If that edge exists it lives
  deeper — or the two shells arose by genuinely disjoint construction.
- **Recomp-1 full corpus at 4905 (5.6 min, 87 walks): 199,391 moves, 0
  improved, 0 new-allocation equals, 97,446 equal-cost same-allocation
  (49% — the same dense-but-closed shell as n=6's 48%).** All 174
  emitted samples (2/walk, the complete emission) gate through
  `m3_check -n 7` as rediscoveries of their own source class. 4840-band
  probe (4 walks, 51.7 s/walk): same verdict, sweep queued.

**Reading: the engine generalizes; so does the wall.** Every
instrument built for n=6 ran at n=7 unchanged and returned the same
closure picture: locally dense (half of all recompositions are free)
but closed (every product is a known class, no shell edge anywhere).
With an 18-char record-to-bound gap (5906 vs LB 5888) versus n=6's 3,
the negative space is telling us the same thing at both n: known
records are not single-edit-adjacent to anything new in their tails.
The n=7 differences worth exploiting: 6 shells not 8, pure-w3
vocabulary, a 61-class dominant shell, an unpaired 1-class shell
(Kristan's), and the 5907s' (858,4) treelike regime as a structurally
different seed population.

**Queued (SWEEP-QUEUE, both pending approval):** n=7 recomp-4840 full
(~75 min single-core; farm binary needs NO reship — e286355 already
has --recomp and n-generic support) and the n=7 deep-seam probe
(merge+ties at 4600, self-sizing).

**Next session, concretely (s34):**
- **Decode the twoCycles extension sets** (the corpus-completeness
  hole): map the set-of-tuples notation onto the tree-like
  kernel+2-cycle construction, materialize the implied 5906s, re-index.
  The n=6 lesson says the known corpus may be orders of magnitude
  bigger than 84 classes — every closure law gains power with corpus
  size.
- **Multi-move tier design doc** (handoff menu item 2, standing
  directive: design before code) — now with the n=7 numbers in hand:
  compound-edit budgets from the conservation law at both n.
- Fold the operator's `a585recomp` n=6 result when done; the two n=7
  queue entries if approved.
- Still open: ip=1 study, per-allocation NRPA/beam, Track C overhead.

## 2026-07-30 (session 32) — Tie census folded and the CLOSURE PICTURE written (SURGERY-DESIGN §"closure picture"): **the 8 allocation shells are S1-disconnected except for exactly ONE edge — the natural (143,5)↔(142,6) pair — and (144,4)/ip=1 are NEVER reached**; every local move now agrees the corpus is closed (splice, reorder ≤270 perms, merge ≤200, ties, recomp sampled) ⇒ an 871 is a COMPOUND edit or diverges before ~depth 450; fresh-agent handoff written (`docs/HANDOFF-S32.md`, supersedes S28)

Documentation/synthesis session at Andrew's request: fold the operator's
tie-census results, write the closure analysis, prepare the handoff.
No code changes; 133 tests stay green.

**Folded — tie census (operator, farm runs `a585ties`/`a520ties` +
probes; SWEEP-QUEUE has the ledgers).** Probe first killed a fear: tie
collection costs only 4.7–6.4× the plain sweep (6.6 ms/walk at 585,
0.26 s/walk at 520), not the feared blowup. Full corpus, both bands:

- Anchor ≥ 585: **0 new-allocation ties** in 22,062 walks (nearly
  vacuous in hindsight — the one known tie sits at anchor 580, just
  below the cut; the deeper band was the real question).
- Anchor ≥ 520: **exactly 1 new-allocation tie corpus-wide** —
  `872.up-0105a4b77ce8` (143,5) → (142,6), and it m3-gates as
  equivalent to `872.up-b020caf20414`: **the committed specimen pair,
  again**. The reached-allocation histogram is one cell, one member.

**The synthesis (now SURGERY-DESIGN §"closure picture", read that
table):** three independent move types — S1 reordering (ties), the S−1
merge, and (sampled) single-cycle recomposition — each produce exactly
zero improvements and at most one cross-allocation product over the
full corpus, and it is the SAME natural pair every time. Combined with
splice-closure and block-order-optimality to ~270-perm tails: **the
known-872 corpus is closed under every local move built so far; the
allocation shells are connected by exactly one edge; (144,4) and every
ip=1 target are unreachable by single edits of known tails.** The
missing character requires a compound edit (≥ 2 coordinated
recompositions — the s29 conservation law fixes each target's budget)
or a divergence earlier than the anchorable zone (~depth 450). This is
the sharpest negative space the project has had: the 871, if it
exists, is now known NOT to be adjacent to anything we hold.

**Handoff — `docs/HANDOFF-S32.md`** (supersedes HANDOFF-S28):
five-sentence state of the world, the engine-first premise, the
instrument stack, the s32+ work menu (n=7 corpus assembly first, then
the multi-move design pass, the two unapproved queue entries, the
untouched ip=1/NRPA/Track-C-overhead items), and the trap list
(launch protocol, farm reship, alphabetical bias, calibrated-vs-proven,
equal-cost flood semantics, cap-at-target, RAM ceiling, session
ritual). CLAUDE.md reading order now fronts it.

**Next session, concretely (s33):** the handoff's menu item 1 — n=7
corpus assembly and the first n=7 tail sweeps (the engine-generality
test with an 18-char gap); item 2 (multi-move design pass,
measurements first) if sweeps queue-block.

## 2026-07-30 (session 31) — Recomp-1 BUILT (`tail-atsp --recomp`, the COMPLETE single-cycle recomposition move — subsumes merge, adds splits/repartitions/entry rotations/1|5 arcs); both farm sweeps folded (a450b50: block-order-optimality extends to ~270-perm tails, 22,062/22,062; a520b40merge: 488,350 merge moves, the ONLY completion is the specimen-pair rediscovery); recomp probes at anchor 585: **~175k moves over 138 walks — 0 improvements, 0 new-allocation equals, but the shell is DENSE under same-allocation repartition (48% of moves complete at equal cost) and a 60-sample M3 batch says ALL are equivalent-to-known** — tentative law: the corpus is RECOMPOSITION-CLOSED at the 585 band

Research-agent session under the new engine-first premise (ROADMAP
"Premise", Andrew 2026-07-29). All 133 tests green (+2), clippy/fmt
clean. **Farm: reship `superperm.exe` before running the queued recomp
sweep — s31 changed `src/tailatsp.rs` and `src/main.rs`.**

**Folded farm results (operator, SWEEP-QUEUE):**
- **a450b50 (I1 reorder, anchor ≥ 450 / ≤ 50 blocks): all 22,062
  classes block-order-optimal, 0 skipped, 48.8 min on 24 cores.** With
  s28b and s9: reordering is dead as a route to 871 across every known
  872's last ~270 perm visits.
- **a520b40merge (I2a merge, anchor ≥ 520): 488,350 merge moves, 0
  improvements, exactly ONE equal-cost 872 at S−1 — the (142,6)
  partner-class rediscovery** (m3-gated). The S−1 merge, exhaustively
  applied to every known 872's last ~200 perms, only re-finds the one
  edit nature performed.

**Built — recomp-1 (`enumerate_recomps`/`apply_recomp` in
`src/tailatsp.rs`, `tail-atsp --recomp`).** The complete single-cycle
move: for each cycle, every alternative arc-partition of its tail perm
set — full cycles get all 2⁶−1 arc-start sets (63 variants), partial
cycles get per-run compositions (arcs never cross a prefix-covered gap
— that would be an i2-priced pass-over, outside I2a). Includes
out-of-vocabulary 1|5 singleton arcs deliberately (census M-R1 says
nature never uses them; a broader negative is a stronger law). Each
variant re-solved exactly with incumbent = equal-length junction total
+ 1: result one below = equal-length 872 (reported by allocation;
same-allocation samples emitted 2/walk for offline M3), two below = 871
candidate (banner, exit 2). Pins: n=5 proven-optimum control with
HK cross-check AND the length-bookkeeping identity (materialized length
= prefix + intra′ + J′) on every recomposed instance; the seam-edit pin
(recomp finds the specimen pair's whole-6 variant at exactly inc − 1).

**Probe verdicts (anchor 585, ~136-perm tails):**
- 8 specimens: 10,640 moves, 0 improved, 0 new-allocation, 4,979
  equal-cost same-allocation (47%).
- First-100 corpus walks: 126,815 moves (~1,270/walk, 5.4 s/walk), 0
  improved, 0 new-allocation, 60,736 equal-cost same-allocation (48%).
- **M3 batch over 60 sampled same-allocation equals: 60/60
  equivalent-to-known, 0 novel.**

**Reading: the 872 shell is locally DENSE but CLOSED.** Half of all
single-cycle recompositions complete at equal length — the
junction-neutral 2|4↔3|3 family the census priced at 0 — yet every
sampled product is a known class, no allocation ever changes, and
nothing improves. This extends splice-closure (s26b) to the
recomposition move at the 585 band: the corpus looks closed under
every local move we have built. The missing char is not adjacent to
the known corpus under single edits of its last ~136–270 perms.

**Queued (SWEEP-QUEUE):** full-corpus recomp-585 on the farm (~1.5–4.5
h on 24 cores; binary reship required first) — the exhaustive version
of the tentative law plus the 871/new-allocation alarm paths.

**Next session, concretely (s32):**
- **n=7 corpus assembly (engine premise item):** gather the 83
  published 5906s + Kristan's + the three 5907s into `data/` with the
  corpus loader conventions, then point `tail-atsp` (I1 reorder →
  merge → recomp, all n-generic) at 5906-class tails — first engine
  generality test where the record-to-bound gap is 18 chars, not 3.
- **Multi-move tier design** (if the farm recomp sweep is negative):
  two-cycle compensated edits (split+demote / merge+demote for the
  d3−1 targets), guided by the census conservation law — design doc
  section first per the standing directive.
- **Still open:** tie census (pending approval), ip=1 study,
  per-allocation NRPA/beam.

## 2026-07-29 (session 30) — I2a BUILT same-day (`tail-atsp --merge`): the merge oracle passes (from a shallow anchor the instrument re-derives the (142,6) partner from the (143,5) side BYTE-IDENTICALLY via merge + tie re-solve); full-corpus merge sweep at anchor ≥ 585: **240,874 merge moves over all 22,062 classes, 0 improvements AND 0 equal-cost completions** — in ≤136-perm tails a single merge cannot even re-price to EQUAL length; at anchor 520 the first instrument-created cross-allocation 872 appears in the wild (a rediscovery of the specimen pair's partner class — the full find→materialize→validate→M3-gate path proven in sweep mode)

Same-day continuation of s29 (the s26/s28b precedent: design §9 in the
morning, instrument by evening). All 131 tests green (+2), clippy `-D
warnings` clean, fmt clean. **Farm note: `src/tailatsp.rs` changed —
reship `superperm.exe` before any farm run of the new entry** (the
running a450b50 I1 sweep uses the old binary and is unaffected).

**Built — merge machinery in `src/tailatsp.rs` + `tail-atsp --merge`.**
`cycle_id`, `enumerate_merges` (pairs of same-cycle tail blocks whose
arc union is one contiguous ride: complementary pairs → all n entry
rotations, partial unions → arc-adjacency, 1 variant; pass-over merges
are OUT of vocabulary — they'd be i2-priced), `apply_merge` (blocks
replaced, cost matrix re-derived from the new `anchor_cur` field,
`intra`+1 for the healed boundary, incumbent-seeded B&B). Sweep mode
re-solves each merged instance with the unmerged optimum as incumbent:
result = opt−1 ⇔ equal-length 872 at S−1 (by the waste identity this
carries one extra door-unit — ALWAYS a different allocation than the
source; from (145,3) it would be the unoccupied (144,4)); result ≤
opt−2 ⇔ 871 candidate (banner, exit 2, M3 ritual). Controls pinned:
n=5 (153 proven optimal) admits no merge below optimum − 1 with HK
cross-check on every merged instance; **the merge oracle** — anchored
at 570 (shallower than the natural seam at 583 so BOTH parts of cycle
135462 are in-tail), the seam-merge variant entered at 462135 re-prices
to exactly opt−1 and the tie search re-derives the (142,6) partner
byte-identically. Nature's one edit, now driven by the instrument.

**Corpus sweep verdicts (single-merge vocabulary caveat attached):**

- **Anchor ≥ 585 (~136-perm tails): 240,874 merge moves over all
  22,062 classes — 0 improvements, 0 equal-cost completions** (192 s).
  Stronger than I1's law: in this band a merge can't even break even.
  The rigid −2 junction pricing (M-R3) is geometrically unrealizable in
  the last ~136 perms of every known 872 — the freed junction weight
  cannot be re-absorbed by any reordering.
- **Anchor ≥ 520, first-300 probe (alphabetical, biased): 6,579 moves,
  0 improvements, 1 equal-cost 872 at S−1** — source
  `872.up-0105a4b77ce8` (the committed specimen pair's (143,5) side!),
  merged at anchor 522 into allocation (142,6,0,0). `m3_check`:
  equivalent to `872.up-b020caf20414` — the natural partner's class,
  REDISCOVERED by the instrument in sweep mode. Not an M3 event, but
  the entire pipeline (find → materialize → validate → M3 gate →
  correct classification) is now proven outside the pinned oracle.
- Full anchor-520 merge sweep (~2–7 h single-core; probe bias caveat)
  queued in SWEEP-QUEUE.md for the operator/farm — reship the binary
  first.

**Reading of the day:** deep tails are merge-dead; the first live merge
appears exactly when the anchor drops below a natural seam (583). The
contested zone for S−1 surgery is the same midgame band everything else
points at — and the anchor-520/450 merge sweeps are the first
instruments that can actually search it exactly.

**Next session, concretely (s31):**
- **Operator results:** fold in a450b50 (I1 anchor-450) and, once
  approved+reshipped, the anchor-520 merge sweep; every `merge-eq-*`
  goes through m3_check (a novel class or unoccupied allocation is the
  event to watch for).
- **Split moves** (the reverse edit, 6→3|3 etc.): same machinery,
  branching 3–6 per cycle; interesting for the d3−1 waste-146 targets
  where a door demotion must be paid by +1 split — design the
  compensated two-move (merge+demote / split+demote) pass on top.
- **Multi-merge**: net −1 via k merges + (k−1) splits; the census says
  natural pairs use up to 29 canceling events — the instrument should
  search small k first.
- **Still open:** ip=1 ε-rollout study; per-allocation NRPA/beam over
  `data/frontiers_s28/`.

## 2026-07-29 (session 29) — Recomposition census over 1,071 controlled pairs (I2's design inputs, SURGERY-DESIGN §9): NEW conservation law **net splits = ΔS exactly, 1,071/1,071 pairs** (composition diffs fully account for the sojourn trade); vocabulary is 6 edit types inside {6, 2|4, 3|3, 2|2|2} — 1|5 NEVER naturally recomposed; junction pricing rigid (~96% of 28,664 events at one extra w2 per extra part; every deviation is a door entering the recomposed cycle); doors are DELOCALIZED from recompositions (39/43 tail doors land elsewhere) with recurring targets — the (142,6)↔(143,5) unit trade is ONE specific object (same cycle `135462` recomposed, same door `w3→135426` demoted, all four natural pairs); I2a designed = the merge-move instrument (single tail-cycle merge + exact block-ATSP re-solve → the S−1 waste-146 edit directly)

Research-agent session per `docs/RESEARCH-AGENT-S29.md`; the queued
sweeps (anchor-450, tie census) remain pending Andrew's go-ahead, so
this session did the unblocked flagship: the I2 design measurement pass.
No Rust changes; tests stay green (129).

**Built — `analysis/trackb/recomp_census.py` + `recomp_doors.py`.**
A controlled pair = two walks byte-identical to a shared depth
(`surgery_pairs.py`, re-run at min-depth 250 → the 11 s28 pairs, then
150 → **1,071 pairs covering 11 of 28 allocation-pair types**; (141,7)
has none at depth ≥ 150, so 1|5 edits stay unmeasured). Full-walk
per-cycle composition diff, junction pricing, net-split accounting,
door locality. 28,664 recomposition events censused.

**The findings are SURGERY-DESIGN §9 (M-R1..M-R7), headline four:**

- **Conservation (M-R2):** net splits over recomposed cycles = ΔS
  exactly, zero violations in 1,071 pairs — an I2 edit toward any
  target allocation has a known net-split budget (−1 for every S−1
  waste-146 target).
- **Vocabulary (M-R1):** 6 edit types, compositions closed over
  {6, 2|4, 3|3, 2|2|2}. I2 branches over 4 compositions per cycle,
  not 545 profiles.
- **Rigid pricing (M-R3):** ≈96% of events price at exactly one extra
  w2 entry per extra part; ALL deviations are door-couplings.
  Composition edits are cost-predictable before search.
- **Door delocalization + recurrence (M-R4):** doors move on their own
  cycles (39/43 off the recomposed set), and surplus door targets
  recur across unrelated pairs — every (140,6,1) side spends
  `w4→145623, w3→{142563, 142356, 156423}`; the unit trade always
  demotes `w3→135426` and recomposes `135462`.

**Correction to s28's §2.4 reading:** the (142,6)↔(143,5) unit trade is
NOT composition-preserving — the full-walk diff shows exactly one
recomposed cycle, the anchor-SEAM cycle (the in-tail autopsy was blind
to it). S1 block reordering can recompose exactly the seam cycle and
nothing else (the entry merge); that is why the tie oracle crossed the
allocation boundary. Interior recomposition (the w4 pairs: 14–29
cycles, net 5) is strictly I2 territory. Also: natural pairs are far
from minimal edits (median 28 recomposed cycles for net ≤ 5, M-R5) —
whether a MINIMAL net−1 edit can complete is exactly I2's question,
and nature doesn't answer it either way.

**Designed — I2a, the merge-move instrument (SURGERY-DESIGN §9).** For
each tail cycle with a split composition, merge it whole and re-solve
the block ATSP exactly: net −1 part = the S−1 unit edit = waste 146 =
**an 871 candidate directly**. One move tier on top of I1, per-solve
cost ≈ I1's; verdict semantics mirror §4 (any −1 completion → M3
ritual; none corpus-wide → "no single-merge 871 within anchored
tails", caveat always). Split/demote moves staged behind its verdict;
I2b (grammar re-cover under target caps) stays staged for the ip=1
targets.

**Next session, concretely (s30):**
- **Build I2a** (`tail-atsp --merge` or a sibling subcommand): merge
  enumeration + modified-block ATSP; controls: n=5 records must admit
  NO improving merge (proven optimum), the unit-pair seam must
  round-trip (merging the (143,5) split re-derives the (142,6) partner
  at equal cost), HK cross-check on modified block sets. Then the
  corpus sweep at anchor ≥ 585 (≈ 15× I1's 23 s — minutes) and ≥ 520.
- **Still queued for Andrew:** the anchor-450 I1 sweep (3.5 h) and the
  tie-census probe/full run (SWEEP-QUEUE.md).
- **Still open:** the ip=1 ε-rollout study; per-allocation NRPA/beam
  over `data/frontiers_s28/`; (141,7) pair hunt at shallower depth if
  1|5 edits ever matter.

## 2026-07-29 (session 28b) — Surgery instrument I1 BUILT same-day (`src/tailatsp.rs` + `tail-atsp` CLI): the tie oracle re-derives the (142,6) partner of the natural specimen pair from its (143,5) side BYTE-IDENTICALLY (full pipeline proven across an allocation boundary); NEW corpus law from two full sweeps — **every one of the 22,062 known 872 classes is block-order-optimal at anchor ≥ 585 (23 s) AND at anchor ≥ 520 / ≤ 40 blocks (875 s), 0 improvements** — the missing char is NOT won by reordering ≤ 200-perm tails

Same-day continuation of s28: with SURGERY-DESIGN.md written, I1 was
built per its §4 (the s26 precedent — design and build in one session,
doc first). All 129 tests green, clippy `-D warnings` clean, fmt clean.

**Built — `src/tailatsp.rs` + `tail-atsp` subcommand.** Decompose any
walk tail at an anchor into blocks (maximal w1-runs), price junctions by
overlap weight, solve the block-order ATSP-path exactly: Held–Karp ≤ 20
blocks (cross-check tier), B&B above it with a two-tier bound (min-in
edge, then Hungarian assignment relaxation only where the cheap tier
fails to prune). The anchor ADAPTS per walk — the cut moves deeper until
the instance fits `--max-blocks`, so no walk is skipped. ~1000× the s28
Python prototype (300 walks: 0.3 s vs 346 s). `--ties` collects
equal-cost orders and reports/writes those whose implied L0 allocation
differs from the source's. Improvements are materialized, validated, and
written with a loud banner + exit 2 (the M3 ritual still applies).
Controls pinned as tests: n=5 greedy-153 tails must be block-order-
optimal (proven optimum), mangled-order repair, materialize identity
round-trip, HK/B&B agreement, all 8 committed allocation specimens
optimal at anchor ≥ 585.

**The oracle passed — across an allocation boundary.** The natural
specimen pair is now committed at `data/surgery_specimens/` (NOTE.md has
the anatomy). From the (143,5) side, anchored at the natural cut,
`tail-atsp --ties` re-derives the (142,6) partner **byte-identically**
as an equal-cost tie, and `m3_check.py` correctly classifies the product
as equivalent-to-known. Anchor → blocks → exact search → materialize →
validate → M3 gate, end-to-end, on the one edit nature performed.
Pinned in `tie_oracle_rederives_partner_across_allocations`.

**NEW corpus law (fixed-decomposition caveat always attached): all
22,062 known 872 classes are block-order-optimal.** Two full-corpus
sweeps: anchor ≥ 585 (≤ 27 blocks, ~136-perm tails, 23 s) and anchor
≥ 520 (≤ 40 blocks, ~200-perm tails, 875 s) — **zero improvements**.
Combined with s9 (all record tails ≤ 25 perms are tablebase-optimal),
the picture sharpens: the missing character cannot be won by REORDERING
the cover blocks of any known 872's last ~200 perms — an 871 tail must
RECOMPOSE cycles (different split compositions), which is exactly
instrument I2's question (SURGERY-DESIGN §5). The law is also thesis
fuel for Track C: block order is a solved dimension; composition choice
is where the evaluator's signal must live.

**Also this session (ops):** anchor-450/≤50-block sweeps cost ~0.6
s/walk → ≈ 3.5 h full-corpus — queued behind the launch protocol for
Andrew's go-ahead. Tie CENSUS mode (`--ties` corpus-wide: how connected
are the allocation shells under S1 reordering alone?) is the other cheap
next probe.

**Next session, concretely (s29):**
- **Tie census** over the corpus at a few anchor bands — count
  new-allocation ties, which allocations they reach, whether (144,4) or
  any ip=1 target is EVER hit by an S1-reachable tie.
- **The 450 sweep** (3.5 h, launch protocol) if Andrew green-lights.
- **I2 design pass** per SURGERY-DESIGN §5: recomposition census on the
  w4 specimen's 15 recomposed cycles; anchored re-cover under the 13
  distance-1 waste-146 target caps.
- Still open from HANDOFF-S28: the ip=1 ε-rollout study; per-allocation
  NRPA/beam over `data/frontiers_s28/`.

## 2026-07-29 (session 28) — Cross-class surgery DESIGNED from corpus evidence (docs/SURGERY-DESIGN.md): cross-allocation braid sharing is real (22,266 states, all 28 allocation pairs) with ZERO unequal-length reconvergence corpus-wide; a natural specimen pair is byte-identical to depth 584 and shows the (S+1,d3−1) unit trade is a pure BLOCK REORDERING with junction re-pricing; block-ATSP prototype: both specimen tails and 249/249 sampled corpus tails are block-order-optimal at anchor ≈585; per-allocation M2 pass run for all 6 untested allocations (d4=0 complete ≤25M nodes; d4-bearing + 1|5-bearing truncate at 60M)

Two of the four s28 items (HANDOFF-S28) landed: the flagship surgery
design (measurements → `docs/SURGERY-DESIGN.md`, Andrew's
design-before-code directive) and the per-allocation M2 pass. Tests
stay green (124), no Rust changes this session.

**Measured 1 — cross-allocation braid census
(`analysis/trackb/surgery_feasibility.py`, full 22,062-class corpus,
~4 min).** The corpus braid has 10,034,458 (visited, cur) states;
**22,266 are shared by ≥2 L0 allocations, and every one of the 28
allocation pairs shares states** — braid-diff across allocations is
viable, not hypothetical. (143,5)×(145,3) share 8,011 states to depth
231. Depth profile is opening-trunk-dominated (deciles 0–2 hold 21,040)
with a thin tail to depth 584. **Zero unequal-length reconvergences,
corpus-wide, cross-allocation included** — s26's "no free splice
improvement" measurement now holds at 75× the corpus across allocations:
an 871 must create states no known 872 visits. Corollary worth keeping:
equal length + equal depth at a shared state forces equal partial WASTE
but not equal partial LEDGER — allocation identity is not fixed by a
shared prefix.

**Measured 2 — natural surgery specimens exist
(`analysis/trackb/surgery_pairs.py`).** 11 cross-allocation walk pairs
share a state at depth ≥250. The deepest: `872.up-b020caf20414`
(142,6,0,0,0) × `872.up-0105a4b77ce8` (143,5,0,0,0) are **byte-identical
for their first 584 perm visits**, then re-cover the same 136 residual
perms at equal cost (163 chars). Four pairs realize the (142,6)↔(143,5)
door-demotion trade; five realize (140,6,1)↔(145,3) — the w4 trade
against the records class, whose char accounting closes exactly (4 heavy
doors ↔ 5 extra sojourn boundaries ↔ 5 extra w1 rides).

**Found — the unit trade is a BLOCK REORDERING
(`analysis/trackb/tail_autopsy.py`).** The deepest specimen's two tails
cover the SAME 24 cycles with the SAME per-cycle split compositions —
the same three block-runs A,B,C in different orders: (142,6) plays
`(w1-entry) A ·w3· B ·w3· C` (the w1 entry merges with the prefix's last
sojourn), (143,5) plays `(w2-entry) C ·w2· A ·w3· B`. One door demoted
to a w2 crossing, one extra sojourn boundary, chars equal. **The
(S+1,d3−1) unit edit of the waste-146 neighbor map, realized by nature
as pure order + junction re-pricing.** The deeper trade is NOT
order-only: the w4 specimen pair (anchor 283, 75-cycle residual)
recomposes 15/75 cycles (whole-6 ↔ 3|3 ↔ 2|4) — so surgery has two move
tiers (S1 reorder / S2 recompose), and S2 needs grammar-level search.

**Built (prototype) + measured 3 — tail block-ATSP
(`analysis/trackb/tail_block_atsp.py`, `tail_block_sweep.py`).** Cut a
tail at an anchor into blocks (maximal w1-runs), price junctions by
overlap weight, solve the block-order ATSP-path EXACTLY (B&B, min-in
bound; Held–Karp cross-check at ≤20 blocks). Key property: junction
pricing is allocation-blind — a cheaper order lands wherever its
junctions imply, including specimen-free allocations ((144,4), ip=1
targets) that every grammar instrument must fix upfront. Results: both
specimen tails are block-order-optimal (optimum = actual = 163; the two
distinct optimal orders ARE the two specimens); **corpus mini-sweep at
anchor ≈ depth 585: 249/249 solvable walks block-order-optimal, 0
improvements** (51/300 skipped at >27 blocks; Python ceiling ~26 blocks,
min-in bound too weak past that — the Rust build gets an
assignment-relaxation bound, target ~40 blocks). Verdict semantics per
the design doc: any improvement = 871 candidate → M3 gate; corpus-wide
none = a new law ("block-order-optimal from depth D", always with the
fixed-decomposition caveat).

**Per-allocation M2 pass (exact d=6, `--fresh-doors`, census profiles,
60M-node cap, frontier dumps at `data/frontiers_s28/`, 16/class).**
With (145,3) 5.79M and (143,5) 21.72M from s27:

| class | verdict | nodes | classes |
|---|---|---|---|
| (142,6,0,0,0) | COMPLETE, 35 s | 24,776,155 | 3,328 |
| (140,8,0,0,0) | COMPLETE | 24,776,155 | 3,328 |
| (140,6,1,0,0) | TRUNCATED @60M | — | ≥3,945 |
| (138,8,1,0,0) | TRUNCATED @60M | — | ≥3,945 |
| (135,9,2,0,0) | TRUNCATED @60M | — | ≥3,283 |
| (141,7,0,0,0) | TRUNCATED @60M | — | ≥13,959 |

Structure discovered: at depth 6 the opening tree depends only on the
caps that can BIND at 6 sojourns — (142,6) ≡ (140,8) byte-identical
(d3 ∈ {6,8} never binds; identical profiles), (140,6,1) ≡ (138,8,1)
identical to the cap. (141,7) explodes (4× the classes) because its
census profile carries the **1|5 / 5|1 singleton splits** — the sound
tier's real enemy at d=6 is profile richness, not door count. The
d4/1|5-bearing exhaustions need the farm or stronger pruning; 16 GB
local RAM rules out materially bigger exact runs (s26 TT thrash lesson).

**Ops note (self-inflicted):** two "failed" zsh batch loops actually
survived their error and kept spawning duplicate sojourn-dfs runs
alongside the retry batch — caught via `ps` (three-fold duplication of
(140,8)/(138,8,1)), killed; dumps verified deterministic-identical.
Lesson: after a batch "fails", check for surviving children before
relaunching.

**Next session, concretely (s29):**
- **Build I1 (`tail-atsp` Rust subcommand)** per SURGERY-DESIGN §4:
  assignment-relaxation bound, controls (specimen pin 163, n=5 records
  must be optimal, mangled-tail repair, HK cross-check), then the
  full-corpus anchor-band sweep — collect improvements (871 candidates →
  M3 ritual) AND ties that land in NEW allocations (a first (144,4) or
  ip=1 872 would be an M3-class event).
- **I2 design pass** (conditional on I1's verdict): recomposition census
  over the 15 recomposed cycles of the w4 specimen; anchored re-cover
  under the 13 distance-1 waste-146 target caps.
- **Still open from HANDOFF-S28:** the ip=1 ε-rollout study; per-
  allocation NRPA warm-starts + union-restricted beam over the new
  frontier dumps.

## 2026-07-29 (session 27b) — M3 gate re-scoped to the full corpus (`analysis/counting/m3_check.py` + committed 22,062-class canonical index; alarm path proven with a hole-punched index); fresh-agent handoff written (`docs/HANDOFF-S28.md`)

Short hygiene session closing the last s26c queue item before the s28
surgery work.

**Built — the M3 novelty gate.** `analysis/counting/m3_check.py`:
canonical form = min(forward-renumber(s), forward-renumber(reverse(s)))
(the s26b convention), sha256 per class, index committed at
`analysis/counting/upstream872_canon_index.tsv` (22,062 rows, 2.0 MB) so
the gate runs on a fresh clone WITHOUT the gitignored archive
(`--build-index data/upstream872` regenerates it, 20 s). Checker
validates the candidate first (sliding-window, mirrors validate.rs),
then classifies: INVALID / valid-but->872 / EQUIVALENT-to-known(names
the class) / **NOVEL ≤872 → loud banner + exit 2**. Sanity battery all
correct: committed specimen and raw non-identity-start record and its
REVERSAL all map to their upstream classes, the s26 hybrid maps to its
byte-identical upstream class, greedy's 873 is "valid, not an M3
event", a truncated string is INVALID (686/720). The alarm path is
proven: hole-punch the specimen's class out of the index and the checker
fires exit 2 on it. **Every collected ≤872 from any instrument (nrpa
--collect, union-dfs, surgery) now goes through this gate + the Rust
validator before any claim.** M3's criterion is now formally
"inequivalent to all 22,062 community classes", closing the s26c queue.

**Handoff.** `docs/HANDOFF-S28.md` — five-sentence state of the world,
the s28 items with concrete entry points (surgery design first,
design-doc-before-code), and the traps (sample-bias ghosts predating
s26c, calibrated-vs-proven grammar caps, the gitignored archive, NRPA
cap-at-target, the launch protocol, the M3 ritual). CLAUDE.md reading
order now fronts it.

## 2026-07-29 (session 27) — Per-allocation grammar SHIPPED and corpus-validated (all 22,062 classes replay 719/719 through their allocation's caps+profile grammar); NEW corpus law from the door-pricing census: **every weight≥3 door opens an untouched cycle** (66,999/66,999 events → `--fresh-doors` cap, −10/−20% opening classes); waste-146 neighbor map: every anchor is ONE unit edit from an open 871 allocation, and three distance-2 targets need `ip=1` — a move NO known 872 uses

s26c consequence 1 (grammar re-scope) built and validated, plus the two
queued analyses. All 115 tests green (72 lib + 3 new pins in
`tests/alloc_grammar.rs`), clippy `-D warnings` clean, fmt clean.

**Built 1 — profiles are data now.** `upstream872_structure.py
--alloc-profiles/--profiles-dir` emits the per-allocation composition
census (`analysis/counting/upstream872_alloc_profiles.tsv`) and one
grammar-consumable profile file per specimen-backed allocation
(`analysis/trackb/profiles/a<S>_<d3>_<d4>_<d5>_<ip>.txt`);
`SplitProfile::from_file` + `--profile-file` on `sojourn-dfs`/`nrpa`
load them (`--records-profile` kept; the census-generated records file
equals the constant, pinned). The corpus-wide composition vocabulary is
exactly **7 types** — every allocation uses ⊆ {6, 2|4, 3|3, 4|2, 2|2|2}
except (141,7) which adds the 1|5/5|1 singletons; (135,9,2) drops 2|2|2
and is completely rigid (ONE whole-walk profile across its 18 classes).
Whole-walk profile counts per allocation: 314/121/77/14/1/10/8/4 — the
records class's 21,144 classes use only 314 profiles.

**Built 2 — `grammar-check` (the replay instrument) + corpus-scale
validation.** New subcommand: forward-renumbers any string to identity
start, replays its first-visit path through `Grammar::replay` (public
now), reports k-of-719, exits nonzero on failure. **All 22,062 community
classes replay 719/719 through their own allocation's caps + census
profile — 29 s for the whole corpus.** The check has teeth: the
1|5-bearing (141,7) specimen dies at move 414 under the records profile
(pinned). One specimen per allocation is committed at
`data/upstream872_specimens/` (NOTE.md has the table) so the pins run
without the gitignored archive.

**Found — a NEW corpus law (door-pricing census,
`analysis/counting/upstream872_door_pricing.py` → `.tsv`): every
weight-3/4/5 door in every known 872 lands on a completely untouched
cycle.** 66,999/66,999 door events across all 22,062 classes have
target-freshness 0; re-entries into split cycles ALWAYS use `w2x`.
Heavy doors are cycle-openers, exclusively. This is far from forced
(records class: ~0.56 chance per walk if doors were placed blindly among
entries; corpus-wide it is astronomical). Implemented as the opt-in
`--fresh-doors` cap on `sojourn-dfs`/`nrpa`/`grammar-check`
(`Grammar::fresh_doors`; calibrated-not-theorem, off by default,
exhaustion claims made with it must say so). With it ON the whole corpus
still replays 22,062/22,062 (pinned for the 8 specimens). Prune value at
exact d=6: records class 5.90M → 5.79M nodes and **2,114 → 1,898
classes (−10%)**; (143,5) 22.59M → 21.72M nodes and **4,041 → 3,245
classes (−20%)**. And feasibility news: **(143,5) exact d=6 exhaustion
completes at all** (~22M nodes, 28 s) — a second allocation is now
within the sound tier's reach.

**Door placement (the pricing picture).** Records class w3 doors are
bimodal — 26% in the first depth-decile, 30% in the last, thin midgame;
the extra doors of the other allocations sit exactly in that midgame
(near-uniform deciles for (143,5)/(140,6,1)). w4 doors are strictly
midgame instruments (depth 120–600, never first/last decile). Doors
overwhelmingly exit COMPLETED whole-6 sojourns (79–96% exit-part 6;
(141,7) is the outlier at 60% — the 1|5 walks). So cross-class surgery
must insert/remove doors in the midgame band levels ~60–450 — the same
contested zone every search instrument (s23/s25/s26) is blocked on.

**Waste-146 (871) target map
(`analysis/trackb/alloc_neighbors.py` → `waste146_neighbors.tsv`).**
4,932 open d6=0 waste-146 allocations; min unit-edit distance (L1 on
(S,d3,d4,d5,ip)) to the 8 specimen anchors: **13 at distance 1** —
every anchor has an `S−1` (sojourn merge) and/or `d3−1` (door demotion)
target — 6 at distance 2, the rest spread to 41. Two structural reads:
(1) ALL 13 distance-1 targets carry the s11-grammar-subregion-closed
annotation — an 871 there must leave the certificate grammar, consistent
with s19; (2) **three distance-2 targets have `ip=1`** ((135,9,1,0,1),
(138,8,0,0,1), (140,6,0,0,1); edit `d4−1 ip+1` from the w4-bearing
anchors) — outside the s11-closed subregion entirely, and no known 872
uses a priced pass-over skip (i2 never fires corpus-wide, s26c). Also
notable: the waste-NEUTRAL trade `(S−1, d3+1)` from the records anchor
lands on (144,4,0,0,0) — **zero known 872s live there**; the
specimen-backed allocations are sparse even within waste 147, so
"which allocations can host an 872" is itself a nontrivial constraint.

**Next session, concretely (s28):**
- **Cross-class surgery design proper** — braid-level diff of (143,5)
  walks against (145,3) neighbors: what re-covers the merged sojourns
  around the two extra midgame doors (the door-pricing TSV + the s26
  braid machinery are the inputs; 918 real specimens to learn from).
- **Per-allocation M2 pass** — exact/book exhaustion + frontier dumps
  per specimen-backed allocation with `--fresh-doors`; then
  union-restricted beam / NRPA warm-started per allocation.
- **The ip=1 targets** — what does a pass-over-bearing 871 look like?
  ε-rollout walks are the only i2 exercisers; seed a study there.
- **M3 re-scope (still queued from s26c)** — collector cross-check
  against all 22,062 classes up to relabel+reversal
  (`upstream872_census.py` has the machinery).

## 2026-07-29 (session 26c) — Full-corpus recalibration census (all 22,062 community classes): waste identity 22,062/22,062; exactly **8 specimen-backed L0 allocations** in 1:1 correspondence with the 8 weight multisets AND with **8 Vlad-frame cells** (his 11 identities pass corpus-wide — the s20 "single cell" was OUR sample bias, not his structure); **545 split profiles** vs the 1 the grammar hard-codes, including split types `1|5`/`5|1` the grammar never allowed; every "all known 872s…" note is now corrected in place (README, CLAUDE.md, TRACKB-DESIGN M3/§7)

Andrew's question — "do we need to analyse the new corpus now, all of our
notes are wrong" — triaged: theorems and machinery survive (bounds, endgame
tablebase, gain-1 certificate result, in-grammar-871 impossibility, the L0
*allocation* ledger); everything of the form "all known 872s share X" was
sample-scoped and is recalibrated by this census
(`analysis/counting/upstream872_structure.py` → `upstream872_structure.tsv`,
`upstream872_vlad_cells.txt`; corpus archive `data/upstream872/`, 22,062
forward-renumbered class representatives, gitignored).

**1 — Waste identity: 22,062/22,062, ip = 0 and zero intra-cycle w≥3 moves
corpus-wide.** T0 is now verified at full community scale — and the i2 term
never fires on any known 872: every weight-2 move in every known 872 is
cross-cycle. (ε-rollout walks remain the only i2 exercisers.)

**2 — The specimen-backed L0 shell is EXACTLY 8 allocations** (all waste
147, all ip=0):

| S | d3 | d4 | classes | share |
|---|----|----|---------|-------|
| 145 | 3 | 0 | 21,144 | 95.8% (the records class) |
| 143 | 5 | 0 | 470 | |
| 140 | 6 | 1 | 388 | w4 exists! |
| 142 | 6 | 0 | 19 | |
| 135 | 9 | 2 | 18 | two w4s |
| 140 | 8 | 0 | 10 | |
| 138 | 8 | 1 | 9 | |
| 141 | 7 | 0 | 4 | |

Track B's grammar, caps, and all s22–s25 verdicts live in row 1 only. The
918 other classes are the cross-class-surgery specimens we assumed didn't
exist — the "specimen-free waste-146 bootstrap" problem now has 7
specimen-backed NEIGHBOR allocations to learn the door pricing from.

**3 — Vlad frame: structure vindicated, "single cell" debunked.** All 11
of his identities/tests (T1–T9 incl. block confinement and cell-universe
membership) pass on every one of the 22,062 classes — his framework is
corpus-sound. But the corpus occupies **8 cells** (e up to 2, s from 15 to
25, always delta=5, j=0), in 1:1 correspondence with the L0 allocations.
The s20 "299/299 in (0,5,25,0)" was our sample bias; his B=4/x=0 ↔
575/141/3 equation holds only for the records class.

**4 — Split profiles: 545 distinct, and the type vocabulary was
incomplete.** The grammar's records profile (whole-6, 2|4, 3|3, 4|2,
2|2|2) is one of 545 observed profiles; type census over 2.65M cycle
visits: whole-6 dominates (2.10M), 3|3/2|4/4|2 ≈ 180k each, 2|2|2 = 4,817
— and **1|5 and 5|1 occur** (2 each, inside the S=141,d3=7 allocation): a
single-perm sojourn is legal in real 872s. `SojournDfs`/`Grammar` with
`--records-profile` cannot represent 545−1 of the observed profiles; the
profile mechanism needs to become per-allocation data, not one hard-coded
constant.

**Consequences queued (s27+):**
- Re-scope the sojourn grammar: caps + profile per specimen-backed
  allocation (8 configs), profile learned from the census TSV, not
  hard-coded.
- Cross-class surgery design now trains on 918 real specimens (door
  pricing across allocations: how do the (143,5) walks pay for the extra
  two w3 doors? Diff them against (145,3) neighbors in the braid).
- The waste-146 (871) target shell: which of the 8 allocations neighbor
  it in ledger space; lemma pass over the 26,416-allocation live shell
  with the 8 anchors.
- M3 independence re-scoped: inequivalent to all 22,062 classes
  (relabel+reversal), checked with `upstream872_census.py`.

---

## 2026-07-29 (session 26b) — The publish check DEBUNKS the hybrids and recalibrates the whole corpus picture: the two s26 hybrids are BYTE-IDENTICAL to strings in the community corpus (rediscoveries — no PR); the true known-872 universe is **50,009 strings / 22,062 relabel+reversal classes** (our 296 was a 1.3% sample, 290 classes, all ⊂ upstream); the "universal 575/141/3 multiset" is a SAMPLE ARTIFACT — upstream has **8 multisets including w4-bearing 872s** (918 classes outside the records class); and the community corpus is **SPLICE-CLOSED up to symmetry** (full 22,062-walk braid: 22,066 paths, 5 new walks, all equivalent to known)

Andrew asked to publish the two s26 hybrids / PR them to the community
corpus. Verification gates before publishing (equivalence = symbol
relabeling + reversal; canonical form = min of first-occurrence renumbering
of the string and its reversal) produced a cascade of findings that matter
far more than the hybrids:

**1 — The hybrids are rediscoveries.** Both are byte-identical (not merely
equivalent) to strings in `superpermutations/6/872-treelike.txt.gz` of
github.com/superpermutators/superperm. No PR. `data/hybrids872/NOTE.md`
records the correction; README/CLAUDE/RECOMB-DESIGN corrected in place.

**2 — Our corpus was a 1.3% sample.** Upstream n=6 holdings: 50,009 872
strings = **22,062 equivalence classes** (1,682 + 4,208 individual files,
plus bulk collections; the treelike family dominates). Our local 296
strings collapse to 290 classes (6 internal equivalent pairs we never
noticed), all present upstream. Nothing we hold is unknown.

**3 — The records class is NOT the whole story (major Track B
recalibration).** Weight-multiset census over all 22,062 classes: **8
distinct multisets**, not 1 — (575,141,3) covers 21,144 classes (95.8%),
then (577,137,5): 470, (580,132,6,**1 w4**): 388, (578,135,6): 19,
(585,123,9,**2 w4**): 18, (580,131,8): 10, (582,128,8,**1 w4**): 9,
(579,133,7): 4. Every s19/s20/s25 statement of the form "all known 872s
share one weight multiset / one coordinate cell" was calibrated on the
biased 296-sample. 918 classes (4.2%) live in OTHER L0 allocations —
including w4 doors, impossible in the records class 145,3,0,0,0 that ALL
Track B machinery (L2 DFS, NRPA grammar, s23–s25 verdicts) targets.
Specimen-backed allocations now exist beyond the records class. Queued
re-checks: Vlad-frame cell census over the 22k classes (the 299/299
single-cell result is now suspect as sample bias), L0 ledger live-shell
against 8 multisets, discriminator re-read.

**4 — The community corpus is splice-closed (the splice instrument is
EXHAUSTED).** Braid over all 22,062 class representatives
(forward-renumbered, identity-start): 10.03M states, 10.06M edges, 12
terminal states, ~22k junctions (depth profile now reaches 500–599: 15
junctions). Closure path count: **22,066** — five new walks, and all five
are equivalent (relabel+reversal) to known strings. Splicing cannot
produce anything new to the community at any scale. Clean negative;
consistent with the thin-shell picture, now measured on the full corpus.

Assets: `analysis/counting/upstream872_dump.py` (upstream → one
forward-renumbered representative per class; needs the sparse clone),
`analysis/counting/upstream872_census.py` (equivalence classes, multiset
census, novelty checks), `data/upstream872/` (gitignored local archive,
22,062 files). The braid handled the 22k-walk corpus in 16 s / 10M states
— the s26 machinery scales.

**Next (updated by this session):** re-scope Track B claims against the
full corpus (Vlad cell census, L0 ledger, which of the 8 multisets the
871-capable waste-146 classes neighbor); union-restricted beam and
cross-class surgery design now have 918 out-of-records-class SPECIMENS to
learn from instead of zero.

---

## 2026-07-29 (session 26) — Structural recombination built and measured (docs/RECOMB-DESIGN.md; `src/corpus.rs` + `src/recomb.rs` + `src/unionsearch.rs`): the splice closure of all 296 known 872s is EXACTLY 298 walks — **+2 new hybrid 872s** (known-872 corpus now 298), both crossings of ONE record pair at the braid's only midgame junction; record diversity is an opening phenomenon (293/296 junctions before depth 200, none after 500, one common terminal state); union-edge DFS built with a lossless union-specific STRAND prune (6× throughput, 4.3M nodes/s) — but union enumeration is INTRACTABLE even for a 2-record sub-corpus (the s23/s24 blocked zone measured a third way); the cap-871 decision run is ALSO bound-blocked (TRUNCATED at 200M nodes / 29 s, 0 completions — no lemma); near-miss splice repair KILLED by measurement before any code was written

Design-first session (Andrew's directive: design before implementation). The
four feasibility measurements (`analysis/trackb/recomb_feasibility.py`,
pure Python over the corpus, ~2 min) reshaped the s25 next-steps *before*
implementation and are the load-bearing content of `docs/RECOMB-DESIGN.md`
§2:

1. 6,434 states are shared by ≥2 byte-distinct records — at every depth —
   and ALL at equal prefix length (no free improvement anywhere).
2. The braid DAG (172,521 states, 172,816 edges, ONE terminal — all 296
   records end at the same final state) has exactly **298** root→terminal
   paths: splice closure = corpus + 2.
3. Near-miss repair is dead: at matched (cur, depth), cross-record
   visited-set symdiff is bimodal — 0 or ≥20 perms (63 pairs in 1..19 out
   of 60k+). There is nothing to repair with a capped beam. KILLED.
4. The union of record first-visit edges is TINY: 1,279 edges / 720 nodes,
   out-degree ≤2, weights 700/576/3 — which made exhaustive in-union search
   look feasible (it isn't; see below — the graph is small but the *tree*
   is exponential in the 232 opening junctions).

**Built 1 — `src/corpus.rs`.** Shared record loader: deterministic, skips
non-record files, HARD-ERRORS on untight/incomplete records (silent corpus
shrinkage would poison every census), dedups byte-identical strings.

**Built 2 — `src/recomb.rs` + `recomb` CLI (Probe R1).** Braid state-DAG,
u128 path count (a pin, not a big number: 298), full enumeration + `Walk`
replay + validation + corpus dedup, provenance segmentation, junction
histograms. All §2 pins reproduced in Rust and pinned in
`recomb::tests::n6_braid_pins` (runs in seconds). The **two hybrids**
(`data/hybrids872/872.h-10c7cbe.txt`, `872.h-287df8a.txt` + provenance.tsv)
are `872.g1-992c42f × 872.g1-ca00934` crossed in BOTH directions at steps
432/433 — the single junction in the 400–499 band. Both validate at 872,
both carry the universal 575/141/3 multiset (forced: the braid only
reconverges at equal length and the union has only 3 w3 edges). These are
genuine new members of the known-872 corpus, but splice-DERIVED — they do
not discharge M3 ("independent"), they prove the machinery.

**Built 3 — `src/unionsearch.rs` + `union-dfs` CLI (Probe R3, the §7
tour-merge).** Undo-based DFS (no per-node cloning; own incremental state
mirroring `Walk::advance` for the residual terms), cycle/residual bound
against `--cap`, `--tt` transposition mode (exact keys; sound for
decision/optimality, NOT enumeration — the tool prints which claim its
configuration supports), `--free k` off-union credits, `--max-nodes` with
honest COMPLETE/TRUNCATED verdicts, usage-ordered adjacency. Plus the
addition that earned its keep: **strand pruning** — `live_in[q]` = count of
unvisited union in-neighbours of unvisited `q`; if any unvisited perm has
none, isn't reachable from `cur` right now, and no free credit remains, the
subtree can never complete. Records never strand ⇒ lossless. Fires 2× as
often as the residual bound and lifted full-corpus throughput 0.7 → 4.3M
nodes/s.

**The negative result (kept, it's the finding).** Union ENUMERATION is
intractable at every scale that matters: full corpus TRUNCATED at 200M
nodes (47 s, 0 completions, max depth 581); even a 2-RECORD union does not
exhaust 50M nodes (0 completions, max depth 672) — mixed A/B prefixes stay
viable for hundreds of steps because record pairs share most edges, and
pure-record completions hide behind the *shallowest* divergence, which DFS
flips LAST. The blocked zone again, measured a third way (beam s23, policy
s25, exhaustive-DFS s26). The **cap-871 decision run (C-U3) is equally
blocked**: TRUNCATED at 200M nodes (29 s, 7.0M nodes/s, max depth 574,
bound prunes 23.0M vs 20.8M at cap 872 — barely tighter). The zero-slack
fact only kills RECORD paths at cap 871; the mixed-prefix churn has bound
slack, so no "no-871-in-union" lemma is obtainable from this instrument.
Also measured: TT pruning hit ZERO times in every n=6 run (exact-state
transpositions just don't occur in the churn region) — and the TT's memory
appetite sent the first 871 attempt into page-thrash; killed per the launch
protocol, re-run without TT, 20× faster. Controls that DO pass and are
pinned: n=5 single/pair suite, n=6 single-record COMPLETE (re-derives its
record byte-identically), n=6 pair TRUNCATED-with-strand-prunes.

**Next session, concretely:**
- **Union-restricted BEAM** — width sidesteps the shallowest-divergence-last
  pathology; restrict successor generation to union edges (+k free
  credits) in the proven residual+endgame beam. The cheap hunt for in-union
  interleaving 872s that DFS order can't reach.
- **Cross-class surgery design** (RECOMB-DESIGN §1(c)) — the only bootstrap
  for the specimen-free waste-146 classes; now with the s26 braid facts
  (opening-concentrated diversity) as constraints.
- Re-run `recomb` whenever the corpus grows (hybrids/union finds feed back;
  closure can only grow).
- Queued from earlier: perfect-ride ATSP closure probe, warm-depth
  curriculum.

All 72 lib tests green (112 total with integration suites), clippy `-D
warnings` clean, fmt clean. (`src/nrpa.rs` + shared `Grammar` in sojourn.rs): n=5 control PASS (153); cold-start n=6 plateaus at 883 (no gradient across the blocked zone); record warm-start (Track C §5) carries the policy to depth 500 and the full pipeline re-derives 872 END-TO-END (byte-identical to seed) — oracle-grade PASS for the policy machinery; discriminator verdict: the record's neighborhood contains ZERO other ≤873 completions in 288 rollouts — the 872 shell is thin, an independent ≤872 is a coordinated multi-move object, M3 pivots to structural recombination (splice/tour-merge/cross-class surgery); two hard lessons: cap-at-target starves the gradient, and the completion U-curve maps s23's blocked zone from the policy side

Build order continues (TRACKB-DESIGN §4 step 4a). All 112 tests green, clippy/fmt
clean.

**Built 1 — grammar extraction.** `sojourn.rs` now exposes `Grammar`
(caps + profile + emergent-edge interiors; `root()` / `children()` /
`feasible()`) — ONE move generator shared by the exhaustive DFS and the NRPA
rollouts, no grammar divergence possible. The refactor is behavior-preserving:
the M2 book-mode pin reproduces exactly (746,107 nodes, 13,527 classes, d=10
E=16).

**Built 2 — `src/nrpa.rs` + `nrpa` CLI.** Standard Rosin NRPA over the sojourn
move space: softmax policy over three feature codes per move (species; door
context = weight/exit-part/target-cycle residual+parts; exact `(cur, target)`
identity), nesting `--level`, `--iters` per level, replay-based adapt (+α on
chosen, −α·p on legal), deterministic under `--seed`. Rollouts hand off to the
beam tail at `--switch-depth` visited perms (`beam_search_multi_seeded_capped`
with `--tail-width`/`--max-len`/`--bound`/`--model`). Extras that turned out to
be load-bearing: `--prior β` (logit −β·waste — ride-biased start), 
`--early-tail` (in-grammar dead-ends complete via the unconstrained tail
instead of scoring dead), `--warm-start <record>` ×N `--warm-reps` (policy
pre-adapted toward known-record move sequences — the Track C §5 "NRPA policy
initialization" deployment point), `--collect L` (all distinct completions
≤ L, not just the best). Depth telemetry (min/mean/max visited perms at
hand-off/death) is printed every run — it is the cheapest view of whether the
policy is actually learning.

**Controls.** n=4: level 2 × 10 iters finds 33; cap 32 honestly kills all
rollouts (pinned tests). n=5 control PASS: prior=1, level 2 × 10 (100
rollouts, 8 s) finds validated 153; without the prior the same budget
plateaus at ~193 and 153 needs 512+ rollouts. Grammar validation for free:
a known 872's first-visit path replays **449/449 and 499/499 moves
in-grammar** — the records really live in this grammar at depth 500 (T0
corroborated at the move level).

**n=6 cold start is a dead end (kept as a negative result).** Three configs
(l2×30 prior 3, l3×10 prior 3, l2×30 prior 2; early-tail, w250 tail, cap
895): ALL plateau at **883**, found within the first ~2 rollouts and never
improved across 900+; hand-off depth stalls at mean ~85 (max 211) of 450.
Diagnosis: from depths 60–160 every prefix completes to ~883 (the s23
ceiling family), so the raw length signal cannot pull the policy deeper —
and the levels it must cross (~60–450) are exactly s23's
completion-blocked zone.

**Warm-start changes the game.** Single record (872.0053cad), prior 3:
reps 3 → depth mean 232/max 358 but best **890** — mid-depth hand-offs
complete WORSE than shallow ones (the completion U-curve: 883 from ~85,
890 from ~232, 872 from 500 — s23's blocked zone re-measured from the
policy side). reps 10 → mean 325, one rollout reaches 450, best **874**.
reps 20 + switch 500 + w8000 tail + cap 872: **872 at rollout 1, 0.2 s,
validated — byte-identical to the seed record.** The full policy → grammar
→ capped-tail pipeline re-derives a record end-to-end (the s23 oracle pass,
now through NRPA machinery instead of a copied prefix).

**Gradient lesson, learned twice.** Hunts with cap 872 + weaker warm-start
(reps 5/10, level 2): 0 live rollouts in 180 (~10 s per death), zero
adaptation signal — a cap at exactly the target starves NRPA (the n=4 test
pins the same effect). Correct hunt design: **cap 874 for gradient, collect
at ≤872.** With that (reps 20/15, l2×12, seeds 3/4): 43 and 28 live
rollouts, both runs re-find 872 — but the collection contains ONLY the seed
record; the explored neighborhood completes at 873/874. **M3 (independent
872) remains open.**

**Discriminator run (same session, after the handoff pass): the shell is
THIN.** Two independent hunts (seeds 3/7, reps 20, l2×12, cap 874,
`--collect 873`; 288 rollouts total, 81 live): the ONLY collected walk ≤873
is the seed record itself — **zero distinct 873s, let alone 872s**. Every
off-line completion lands at 874+. Combined with the fact that all 296 known
872s share one weight multiset and one s20 coordinate cell, the verdict:
single- or few-move deviations from a record cost ≥ 2 chars, so **local
policy-space exploration around one record cannot produce an independent
≤872 — a new 872 is a coordinated multi-move object.** This cheaply closes
the "tune exploration harder" alternative (temperature/alpha/nesting sweeps
de-prioritized). Analysis script: scratchpad `disc_analysis.py` pattern —
collected walks vs seed divergence positions vs the corpus.

**Next session, concretely (re-planned after the discriminator):**
- **Structural moves, not policy jitter.** (a) Record-pair recombination:
  splice compatible segments of two byte-distinct 872s (they share the
  weight multiset; find crossover points where prefix of A + suffix of B is
  a legal walk, tail-repair with the capped beam). (b) The queued §7
  tour-merge. (c) Cross-class surgery: legal cycle-level edits that CHANGE a
  record's L0 allocation (trade w3 door ↔ two w2 splits, introduce a priced
  skip) — also the only known bootstrap for the specimen-free waste-146
  classes where an 871 must live.
- Bandit over the 296 records as warm-starts still worth one cheap pass
  (some record may sit in a denser pocket), but with collection growth as
  reward and low per-record budget.
- Warm-depth curriculum (500 → 450 → 400 …) remains the path to making the
  policy own the blocked zone rather than ride the seed.
- Collector should cross-check `data/records872/` + `data/gain1_872s/`
  automatically and flag any byte-distinct ≤872 loudly (M3 criteria
  unchanged).

## 2026-07-29 (session 24) — T2 built (`Scorer::Composed` + admissible `--max-len` cap): composition is the first learned-signal WIN on completion (pipeline 879 → 874, robust plateau); cap proven sound + big speedups on viable searches; capped runs then PROVE the midgame ranking is the sole remaining failure — 872 needs a policy, not width; NRPA is next with three measured motivations

Build order continues; this session landed T2 in two pieces plus the verdict
experiments. All 105 tests green, clippy/fmt clean.

**Built 1 — `Scorer::Composed { bound, model, alpha }`** (score = `len +
lb(bound) + α·pred`, `src/beam.rs::model_pred` factored out of the `Learned`
arm; `trace::score_state` extended to match). CLI: `--bound` became optional;
`--model` alone = legacy `Learned` (bit-identical), `--bound` + `--model` =
composed. Pinned: α=0 ≡ `Bound(b)` for every bound; `Composed{Arc}` with a
residual-target model ≡ `Learned` (same anchor, same prediction).

**Built 2 — admissible length cap `--max-len L`** (T2's "residual-bound
pruning" from the design): discard any candidate with `len + lb > L` — lb is
admissible, so this is lossless for completions ≤ L, and the whole width goes
to states that can still make it. Beam can now die honestly
(`Option<BeamResult>`; CLI prints "NO completion within cap"). Pinned: n=5
cap=153 finds 153 under all three bounds, cap=152 dies (consistent with the
proven optimum); cap composes with multi-seeding.

**Result 1 — composition is the first productive learned signal on
completion.** Pipeline (24,214 sound d=6 records-class exemplars → beam):
`--bound residual --model linear_n6_res_boot1 --alpha 0.25` gives **874**
(vs 879 residual-only, vs the s23 oracle ceiling 878). Robust: α ∈
[0.15, 0.35] all 874; w8000 = w32000 = 874; 64-exemplars/class = 874; four
jitter seeds = 874; endgame adds nothing (len 850 + exact 24 every time).
Res-model magnitudes matter: α ≥ 0.5 degrades (880/889/891 on oracle seeds),
absolute-target models and the MLP are wall-clock impractical. The 874s are
DIFFERENT walks across configs (a level set, not one basin) — and
`verify_identity` shows they all **escape the records class** (S=120
greedy-shape, waste 149): the seeds force a records opening, the beam reverts
to greedy-style play and pays 2 chars for the mismatch.

**Result 2 — the cap is sound and fast, and its failures are informative.**
Every config that found 872 uncapped still finds it capped, faster: oracle
d500 w8000 3.7s → **0.16s**, d450 w32000 24s → **10s** (byte-identical
targets). But capped pipeline runs (w8000/w32000, with and without model)
all DIE at cap 872 — and even cap **873** dies at w8000, consistent with the
uncapped 874 floor.

**Result 3 — the verdict the two failures jointly prove.** Traced the
record's own trajectory: `len + lb_residual ≤ 872` at EVERY step (max
exactly 872, 0 violations) — so on the record's line the bound has no slack
to prune with until the very end, and in the opening/midgame (level ~60:
len+lb ≈ 770s) NOTHING is prunable — an admissible cap cannot help selection
there even in principle. Combined with s23: the ≤872 tree through the
records-class openings is width-truncated in the midgame because the scorer
misranks record-style states at levels ~60–450, and no bound, cap, width,
jitter, exemplar count, or α fixes it. **The midgame RANKING is the sole
remaining failure mode.** That is a policy problem — NRPA's exact shape.

**Next: NRPA (`src/nrpa.rs`)** over the sojourn move space (ride/skip/door
grammar of `src/sojourn.rs`), softmax policy on move features, nesting 2–3,
adapt-toward-best, tablebase/capped-beam finish (the capped beam is now a
fast completion oracle from depth ≥ ~450 — use it as NRPA's tail solver).
Then the bandit over frontier classes → re-run C1 → M3. Three measured
motivations carried in: (a) 879→874 says learned signal composes; (b) the
874 class-escape says completion must be HELD in-class (NRPA policy can);
(c) cap-death says only better midgame ordering can reach 872.

## 2026-07-29 (session 23) — T3 built (`--dump-frontier` + `beam --seed-file`, multi-seed injection); C2 PASS (pipeline finds 153); C1 verdict: oracle PASS (byte-identical 872 re-derived from its own depth-≥450 prefix) but the frontier→beam pipeline is COMPLETION-BLOCKED at 879, quantified ceiling 877–878; learned model + stratification actively HURT record-opening completion — residual bound is the best completion scorer

Build order = TRACKB-DESIGN §9; this session landed T3 → C1/C2. New code:
`sojourn-dfs --dump-frontier <tsv> --dump-per-class K` (states optionally carry
first-visit rank paths; ≤ K frontier exemplars dumped per L2 canonical class)
and `beam --seed-file <path>` (`SeedSpec::Walks`: one root state per walk,
replayed through the survivor-loop counter updates and **injected into the
level-synchronous loop at its own depth** — walks of different lengths enter at
different levels, arena chains all hang off node 0 so reconstruction, dedup,
stratification, jitter, and the endgame snapshot all compose unchanged). A
one-line seed file equal to the greedy prefix is **bit-identical** to
`--seed-prefix` (pinned by test). 3 new integration tests + 1 sojourn unit test
(dump paths replay to exactly `len` by max-overlap concatenation); all 99+4
tests green, clippy/fmt clean.

**C2 — PASS, with a transferable lesson.** Pipeline = sojourn DFS in greedy's
n=5 class (S=24, d3=4, d4=1, ip=0, waste 29) → frontier dump → multi-seed
beam. At `--dump-per-class 1` (abstraction tier): **154**. At exact dedup +
64 exemplars/class (473 seeds): **153, validated, under all three bounds**
(cycle/arc/residual, w2000, 0.2 s). The abstraction key is too coarse to pick
the right exemplar — in-class exemplar diversity is what closes the last char.

**C1 — the machinery control passes; the pipeline control does not, and the
blocker is now measured, not guessed.** Oracle = seed the beam with a known
872's own prefix (`872.0053cad`, relabeled to identity; script in scratchpad,
now `analysis/trackb/record_to_seed.py`). Completion-vs-depth curve:

| seed depth (perms) | learned+strat w2000 | residual w8000 | residual w32000 + endgame |
|---|---|---|---|
| 0 (scratch) | 873 | 894 (s19) | — |
| 14 | 899 | 877 | **878** (128 s) |
| 100 | 906 | 886 | — |
| 200 | 917 | 884 | 882 |
| 400 | 915 | 874 | 874 |
| 450 | 897 | 874 | **872** ✓ |
| 500 | 904 | **872** ✓ | — |
| 550 | 888 | 872 | — |
| 600 | **872** ✓ | — | — |

The d=600 / d≥450 completions are **byte-identical to the source record** and
validator-complete — the completion machinery is sound from the late midgame.
Three findings: (1) **the stratified learned beam — our best from-scratch
config — is the WORST record-opening completer** (899–917, worse than its own
873 from scratch, non-monotone in depth): the boot1 model is off-distribution
on record-class states and stratification protects the wrong states once the
opening is already record-shaped. The residual bound is the best completion
scorer by 15–30 chars. (2) The completion horizon is ~level 450 (w32000) /
500 (w8000): below it the beam abandons the record's line and loses 2–10
chars through the midgame. (3) From opening depth the ceiling is **878 even
given the TRUE record opening** (d=14, w32000 + exact endgame) — so no
frontier, however good, can reach 872 through beam-only completion at
feasible widths.

**Pipeline C1 runs saturate exactly that ceiling:** records' class, d=6
sound-exact frontier, 16 exemplars/class = 24,214 seeds over all 2,114
classes → residual w8000 + endgame = **879** (31 s); w32000 = **879** (136 s;
width-saturated). d=10 book frontier (13,527 classes × 1) → 883; learned
config → 893. The frontier layer is fine — the gap to 872 lives entirely in
beam completion through levels ~60–450. **C1 verdict: NOT PASSED as a
pipeline; machinery validated; the binding constraint is the completion
engine, quantified at +6–7 chars.** This is the Track B mirror of s22's
"bounds don't predict": completion needs a *policy* through the contested
zone, not a wider beam — exactly what the design's step 4a (NRPA at sojourn
level) + T2 (bound/model composition) are for. Track C's evaluator target is
now sharp: rank quality *conditional on record-class openings*, levels
60–450.

**Next (build order continues):** T2 `--bound` + `--model` composition, then
NRPA (`src/nrpa.rs`) over the sojourn move space with tablebase finish, then
bandit over frontier classes → re-run C1 → M3 verdict. The perfect-ride ATSP
closure probe (616 S=120 classes) and §7 tour-merge stay queued as idle-Mac
candidates. `record_to_seed.py` turns any record/string into seeds — reusable
for NRPA warm-starts and Track C training pairs.

## 2026-07-29 (session 22) — Track B build: T0 identity VERIFIED (806 walks, 0 exceptions, general form found), L0 ledger (78,813 allocations, M1 PASS 66.5%), NEW pass-over lemma (ip ≤ 4·(S−120)), T1 door atlas (150 canonical edges), L2 sojourn DFS built, M2 PASS in book mode (d=10, 746k nodes) with exact-tier infeasibility QUANTIFIED

Build order = TRACKB-DESIGN §9; this session landed T0 → L0+M1 → T1 → L2+M2.
New code: `analysis/trackb/{verify_identity,enumerate_l0,door_atlas}.py`,
`src/sojourn.rs` (sojourn-grammar DFS, 3 dedup tiers), `atlas` and
`sojourn-dfs` subcommands, `rollouts --strings` (RNG stream untouched).
All 99 tests green, clippy/fmt clean.

**T0 — the i2-priced identity is VERIFIED, and the fully general form is now
known.** `verify_identity.py` works on the string's first-visit reading
(immune to walk bookkeeping and emergent-edge ambiguity), 806 strings, zero
exceptions. The stated form `waste = (S−1) + #w3 + 2#w4 + 3#w5 + i2` is exact
on every walk whose moves are w1/w2/cross-cycle-w3..5 — all 297 records
(147 = 144+3, S=145), all 873s, greedy n=5/6, and (n-generic) Kristan's n=7
5906 (860 = 842 + 18·w3). i2 pricing exercised on 319 ε-rollout walks (up to
i2=14), exact on all. Two further move classes exist under budget 146 and are
exactly priced by the **general identity**
`waste = (S−1) + Σ_{w≥3}(w−2)·inter[w] + Σ_{w≥2}(w−1)·intra[w]`:
intra-orbit rotations k∈{3,4,5} (priced k−1) and w6 doors (priced 4; intra-w6
is impossible — rotation by 6 is the identity). Only ε-rollouts/fallbacks use
them, but L0 must carry them. **New structural lemma (canonical reading of
i2):** an intra-orbit rotate-by-k exists only when all k−1 skipped members are
ALREADY VISITED — else the appended chars spell them and the move decomposes.
So canonical i2 = "pass over a visited member", not "skip and revisit later".
Bonus: Egan's 873 is a pure w2-door walk (S=149, zero w3+/i2) — a different
cycle-level shape from greedy's 873 (S=120, 18 w3/4 w4/1 w5; confirms ITEM5
§3's 119+18+8+3=148, corrects ITEM5 §1's "15 w3" aside — now fixed there).

**L0 — ledger built; M1 PASS.** Post-T0 allocation tuple `(S, d3, d4, d5, d6,
ip)` with `ip` = priced intra-skip waste (i2+2i3+3i4+4i5). The design's "few
hundred tuples" was off two orders: **78,813 allocations at waste ≤ 146**.
Closures: **LB-869** (urdvr Lean floor: waste ≤ 143 ⇔ length ≤ 868) kills
44,541 (56.5%) — the live shell is waste ∈ {144,145,146} = lengths 869/870/871,
34,272 rows. **NEW Lemma B (pass-over capacity), machine-self-checked:** per
cycle with p sojourns the priced intra-skip waste is ≤ f(p) = (0,4,6,6,4,0)
for p=1..6 (skips sit in len_j−1 gaps of ≤4 passed members each, passed
members must be earlier-sojourn covers; spreading splits dominates) ⇒
**ip ≤ 4·(S−120)**; in particular S=120 ⇒ ip=0. Kills 7,856 live rows (22.9%).
**M1 = 66.5% of all allocations closed ≥ 50% — PASS** (honest live-shell
number: 22.9%). 26,416 open classes (7,441 at 869 / 8,747 at 870 / 10,228 at
871); annotations: 2,135 carry the s11-grammar-subregion note (ip=0, d6=0 —
in-grammar sub-region closed by s10/s11), 616 are the S=120 perfect-ride
family, closable outright by a 120-node cycle-level ATSP over the door atlas —
flagged as the cheapest next closure wave. Ledger: `analysis/trackb/
ledger_l0.csv` (34,272 live rows; LB-closed bulk not emitted, counts in
script output).

**T1 — door atlas built and orbit-verified.** `atlas` subcommand dumps all
720×150 weight-≥3 edges (cycle labels, in-cycle offsets, and each edge's
statically-known interior permutation windows — the emergent-edge filter
data). `door_atlas.py` proves the table is exactly the relabeling orbit of
**150 canonical edges** from the identity (edge set, weights, interior perms
all commute with relabeling) → `door_atlas_canonical.tsv`. Facts: per perm,
w3/w4/w5 = 6/24/120 edges, exactly one intra rotation each; **every
cross-cycle door of a given weight reaches a distinct cycle** (5/23/119
distinct targets); interior-perm histograms give the unconditionally-usable
door fractions **w3: 3/6, w4: 13/24, w5: 71/120** (a door is legal in
canonical reading iff its interior perms are all visited); the intra rot-k's
interiors are exactly its k−1 skipped members — independent confirmation of
the T0 lemma.

**L2 — sojourn DFS built; M2 PASS in book mode; exact exhaustion feasibility
now quantified (a design-assumption correction).** `src/sojourn.rs`: state =
(cur, visited, ledger, per-cycle packed part compositions, cur-part), moves =
the T0 canonical grammar (ride / skip with visited-pass-over legality / exit
door with the emergent-edge interior filter), class-completability pruning
(caps + owed-sojourn accounting, split-profile aware). Three dedup tiers:
**exact** (sound), **orbit** (sound quotient by relabeling — O(1) canonical
form: the unique relabeling sending cur to identity), **abstraction** (L2
canonical key: necklace multiset + ledger + current pattern, with a per-class
exemplar cap E). Measurements on the records' class (S=145, d3=3, profile
6|2,4|3,3|4,2|2,2,2):

| depth | exact nodes | orbit nodes | true classes | book E=16 nodes (classes) |
|---|---|---|---|---|
| 4 | 78,953 | 78,670 | 334 | 10,291 (272) |
| 6 | 5,899,572 | 5,887,556 | 2,114 | 58,835 (1,279) |
| 8 | >20M (oversize) | >20M | ≥3,921 | — |
| 10 | ~10⁹–10¹⁰ (proj.) | same | — | **746,107 (13,527), 2.6s** |

Findings: (1) **M2 PASSES in book mode** — d=10 exhaustion at E=16 within 10⁶
nodes (746k), 13,527 opening classes; E=64 gives 19,572 classes at 2.7M
nodes/9s. Coverage dial measured against exact ground truth: at d=4,
E=1/64/256 reach 174/323/334 of 334 classes; at d=6, E=256 reaches 94.4%.
(2) **The sound tiers cannot exhaust d=10** (exact tops out ≈ d=6–7 at 10⁷) —
the design's "~10⁶ nodes at d=10" holds only for the abstraction tier; closure
claims must either stay at d ≤ 6 (exact d=6 is 5.9M nodes, 6 s — usable!) or
wait for stronger pruning (residual-bound composition, T2). (3) **Negative
result worth keeping: orbit dedup is worthless here** (~0.3% reduction) — the
identity start anchors every branch, so cross-branch relabeling coincidences
barely occur; symmetry pays only at the abstraction level. (4) Exact-frontier
redundancy is enormous (3.07M states → 2,114 classes at d=6, ×1450) — the
canonical key is doing exactly the compression the bandit layer needs.

**Next (build order continues):** C1 control (the pipeline must re-find a
validated 872 from the records' class — needs completion machinery: seeded
beam/tablebase below the frontier, i.e. T3 `--seed-file` first) + C2 n=5;
then T2 bound/model composition; then bandit + NRPA → M3. Perfect-ride ATSP
closure probe (task from L0: closes all 616 S=120 live classes in one exact
solve) and the §7 tour-merge probe are idle-Mac candidates.

## 2026-07-29 (field news, no code) — Group thread on the Lean soundness bug behind a fake Collatz "disproof"; verdict: our adopted LBs (869/5888) are NOT threatened, but one cheap hygiene task queued (re-check urdvr's proof under the patched toolchain)

**Source.** Superpermutators thread, 2026-07-29 (Gould → Houston → Gould →
Raudvere → Das). Full thread, exploit details and our analysis in
`../extraDocs/2026-07-29-lean-soundness-thread.md`.

**The news.** A claimed Collatz disproof turned out to exploit
leanprover/lean4#14576 — the kernel accepted wrong-structure projections,
allowing an axiom-free proof of `False` — AND an independent bug in the nanoda
checker simultaneously, so neither caught it. Gould reads it as an exploit
chain, not an honest error, and asks how to treat AI-generated Lean proofs;
Houston's answer is version-survival (confidence accrues as proofs keep passing
new Lean releases); Raudvere (whose proof is exactly the artifact at stake for
us) says his real worry is *formalization* error — "correctly proving the wrong
true theorem" — mitigated by having strong models review a paper generated from
the Lean proof without the Lean as context; Gould floats a canonical Lean
formalisation of the problem on the community repo; Das proposes walk-level
tooling (per-transition overlap annotation, step-by-step kernel diffs, auto-
locating the "−1").

**Verdict for us (analysis in the extraDocs note).** (1) The soundness-bug
class needs adversarial kernel-API metaprogramming + an engineered hash
collision (per the issue: cannot fire accidentally) — no threat to urdvr's
good-faith proof. (2) The real residual risk, formalization error, is the one
we already partially covered in s19 *semantically, outside Lean*: their lemmas
matched forced-map periods we had measured independently BEFORE reading the
paper, and we recomputed 869/5888/46103 exactly + checked their G(E) against
our 223 chains. (3) Asymmetry worth remembering: record *strings* are
self-certifying, *lower bounds* are where Lean trust concentrates — any future
claimed LB (e.g. urdvr's (k−5)! capacity term) gets this thread's full
skepticism; any claimed record with a proof attached, we verify the string and
ignore the proof. (4) Worst case (869→867, 5888→5884) changes framing only —
no search-side correctness depends on the bounds.

**Queued:** T-lean — when the #14576 fix (PR #14577) ships in a release,
re-elaborate `extraDocs/superpermutations-hunter` (d452221) under the patched
toolchain, optionally `lean4checker`; record the version. The s19
kernelchain7-vs-`rot_j` script stays queued and doubles as a formalization
cross-check. No change to Track B priority.

## 2026-07-29 (field news, no code) — Kristan: a record-TYING 5906 at n=7 that visits one permutation twice; RESOLVED same day — the repeat is bookkeeping (byte-identical to a simple-path reading), simple-path pruning is provably lossless; the string is still genuinely new (only known non-symmetric 5906)

**Source.** Private email from Tomaž Kristan (2026-07-29 06:28), body just "All in
the zip file included" + a link. The zip never arrived; the material is published
on his site anyway (one-page JS app — click the "SuperPermutation 7" sidebar
entry, nothing renders without the click, so a plain fetch shows only a topic
index). Full writeup, provenance and translation in
`../extraDocs/2026-07-29-tomaz-kristan-5906-repeat.md`; string in
`../extraDocs/tk-5906-repeat.txt`; `../extraDocs/verify_tk5906.py` reproduces
every number and exits 0.

**Verified ours, independently.** Length 5906, covers **5040/5040** permutations,
**5041** permutation windows in 5900 total, `7324615` appears **exactly twice**,
non-palindromic. Weight histogram `{1: 4198, 2: 825, 3: 17}`, 5040 transitions
summing to 5899. Valid superpermutation; **ties** the 2014 record, does not beat it.

**The mechanism (not stated on his page — this is the finding).** The two
occurrences of `7324615` are 7 apart and the seven transitions between them are
*all weight 1*, visiting exactly the seven cyclic rotations of `7324615`, entered
and left by weight-2 edges. The walk enters a 1-cycle and **traverses it
completely, closing back to its entry vertex** — 7 weight-1 edges where the
standard construction spends 6 and exits from the last vertex. The closure costs
exactly 1 character and is repaid elsewhere: vs our own
`analysis/cover7/recompiled_5906.txt` the profile differs by **+2 weight-1, −1
weight-2** — length-neutral (4198 + 2·825 + 3·17 = 4196 + 2·826 + 3·17 = 5899).

**Why it lands on us.** Beam, the certificate grammar and cover7 all model n=7 as
a walk hitting each permutation **at most once** — a revisit is forbidden by
construction. This is an existence proof that a *record-tying* solution lives
outside the simple-path class. Open (not argued either way here): whether
relaxing the restriction can go *below* the simple-path optimum. Note the usual
shortcut argument does **not** apply — it deletes a repeated-vertex loop only when
the loop's other vertices are covered elsewhere, and here the loop is exactly what
covers the other six rotations. Second consequence: a fully-closed 1-cycle is a
loop type distinct from the 6-of-7 open traversal; if the certificate vocabulary
can't express it, it can't express this string.

**Corpus check DONE (same day) — both of his uniqueness claims hold against the
published 5906 corpus.** All 83 published 5906s
(github.com/superpermutators/superperm, `superpermutations/7/7_5906/`) verified:
**zero repeated vertices in any of them**, and every one has the two-fold
symmetry (reversal ∘ relabeling) that its search *imposed* — per the corpus
Readme all 83 came from PermutationChains seeded with palindromic kernels under
`fullSymm`. Kristan's string has **no** such symmetry (all 5040 relabelings ×
reversal tested) and is **not equivalent to any of the 83** under relabeling or
reversal — genuinely new, and an existence proof that the 5906 space extends
beyond the symmetric subspace (the corpus's symmetry is a search artifact).
Correction to an earlier draft of this entry: `recompiled_5906.txt` is NOT a
counterexample to "only non-palindromic" — it fails only the naive
digit-complement test, is fixed by reversal + relabeling `1234567→5264137`, and
is equivalent to a published solution (kernel `666466646646664666`).
Reproduce: `extraDocs/check_corpus_5906.py` (exits 0; downloads the corpus).

**CORRECTION (same day, later) — the "outside the simple-path class" claim
above is WRONG; the repeat is bookkeeping, not structure.** Deleting the second
`7324615` visit from the walk and rebuilding with minimal appends gives a
string **byte-identical** to the original: the weight-3 edge `5732461 →
2461537` appends `537`, whose interior window re-spells `7324615` on its own.
The same 5906 string therefore decomposes BOTH as the 5041-visit walk above AND
as a simple path over first occurrences (5040 distinct visits, gaps `{1: 4197,
2: 824, 3: 18}`, sum+7 = 5906). General fact worth recording: **every superperm
string is a simple walk over its first-occurrence windows** (consecutive first
occurrences at gap g overlap in ≥ 7−g chars, so edge weight ≤ g), hence the
minimum over all strings is attained by simple paths and **the sub-5906
question flagged above is CLOSED: revisits can never be required.** No change
to beam / grammar / cover7 pruning is warranted. The string is even reachable
by our own beam in principle — the `537` append is the canonical weight-3 move
from `5732461` to then-unvisited `2461537`, and the incidental repeat window is
forced and harmless; endpoint-only coverage crediting loses nothing either (an
edge whose interior spells an unvisited perm decomposes equal-cost as 1 +
(w−1) through it). What SURVIVES: a genuinely new 84th 5906, the only known one
without two-fold symmetry, carrying a motif absent from all 83 published
solutions (a weight-3 edge whose interior re-spells a covered perm — the
closed-1-cycle reading); whether the kernel/chain grammar spans that motif is
still a fair question, but about which simple-path optima the grammar reaches,
not about leaving the class. Reproduce: `extraDocs/shortcut_tk5906.py` (exits
0).

**QUEUED WORK (out of this analysis) — emergent-edge canonicalization filter,
now in TRACKB-DESIGN §9.** The one concrete machinery improvement from the
detour. A composed weight-2/3 move whose interior window spells an *unvisited*
permutation is byte-identical to the decomposed line through it, so the search
currently spawns duplicate subtrees (`graph.rs:135-151` generates all
successors with no filter; beam dedup can't merge them since the two readings
have different visited-sets). Fix: annotate perm-interior edges at graph build
time (static per edge — per node 1 of 2 weight-2 and 3 of 6 weight-3
successors at n=7), skip a composed edge at move generation iff an annotated
interior rank is unvisited, keep it iff all are visited (the Kristan case, so
his string stays reachable). Lossless for optimality AND enumeration; cost a
few bitset lookups per expansion. Payoff ranking: Track B L2 exhaustive DFS
and the endgame solver (true duplicate-subtree merging) >> beam (frees width
slots only). Not implemented — queued for the Track B build.

**Method withheld, deliberately.** He's hunting the record ("if he manages to get
under 5906 characters, you'll be the first to see it") and this looks like a
byproduct. **Don't press him.** If he volunteers: what produced it, was the repeat
targeted or found after the fact, does his encoding permit revisits *generally*,
and how many of his 5906s carry one.

---

## 2026-07-29 (session 21) — Track B DESIGNED: opening-first sojourn-level search (`docs/TRACKB-DESIGN.md`); solved-game survey reframed the whole attack around the proven "decided in the opening" theorems; no code, no runs

**Session shape.** Started as a survey: which *solved* games are better analogs
than chess (single-agent, absolute objective, optimality wanted)? Candidates
mapped: Rubik's/God's-number (coset partition ⇒ per-class closure), Chinook
(opening book as root proof tree + endgame DB), 15-puzzle/Sokoban (pattern DBs,
deadlock rules), Morpion Solitaire (NRPA — the record-setting technique for
exactly this problem class), snake-in-the-box (canonical early exhaustion),
LKH/tour-merging, AlphaTensor (construction-as-game). First-pass ranking put
retrograde endgame DP on top — **wrong, per our own s9 theorems** (endgame door
proven shut; Andrew caught it). Re-read through the opening lens, the imports
that survive are exactly the ones solved games use where evaluation is least
informative: enumeration, canonical exhaustion, budgeted root exploration,
policy adaptation.

**Product: `docs/TRACKB-DESIGN.md`** — the concrete state/move design ITEM5 §6.2
was missing. Skeleton: general waste ledger with i2 priced (T0 = machine-verify
before use); L0 waste-allocation × L1 split-profile class ledger with per-class
closed/open status (Vlad's GAPS/ledger process model adopted; his F1/F2 and cell
kills cross-reference only until re-derived); L2 canonical opening prefixes
(first ~10–12 sojourns, relabeling-canonical keys, Zobrist) exhausted per class;
UCB/successive-halving bandit over the opening frontier on tail-focused reward;
rollouts by sojourn-level NRPA (nesting 2–3) + seeded stratified beam with
depth-tapered width; tablebase closes r≤20; residual bound at budget 146 as the
admissible pruner (needs T2: `--bound`+`--model` composition; T3:
`--seed-file`). Two-sided by construction: every class closed by lemma is a
publishable narrowing of where 871 can hide (hedge against the ~5–10% prior),
and full closure would be an independent a(6)=872 path. Gates: C1 positive
control (re-find a validated 872 from the records' own class — s15 lesson
institutionalized), C2 n=5 gate, M1 lemma coverage, M2 exhaustion feasibility,
M3 (independent 872 or out-of-grammar ≤873) before any farm spend. Side probe
(§7, one afternoon): Cook–Seymour tour merge over the 296 known 872s — their
tails are provably shared, so the union graph is pure opening diversity; exact
search over it either finds 871 or gives independent tier-upgrade evidence on
Vlad's (0,5,25,0) cell.

**Also updated (fresh-agent handoff pass):** ROADMAP item 5 Track B and
ITEM5-DESIGN §6.2 point at the design note; CLAUDE.md's reading order + current-
state block now name Track B as the next implementation (s21+s20 are the
handoff); ARCHITECTURE.md gained a **"Track B implementation map"** section
(where T0/T1/T2/T3, the L0 ledger, `src/sojourn.rs`/`src/nrpa.rs`, and the gates
land in the code — API names verified against `src/`); README fronts Track B as
the current front. A fresh agent should be able to start at TRACKB-DESIGN §9
with no other context.

**Next session, concretely (build order = TRACKB-DESIGN §9):**
- T0: verify the i2-priced waste identity over the full corpus (296 records,
  greedy, 873s, rollouts).
- L0 enumeration + class ledger CSV; read M1 (what fraction closes by cheap
  lemma).
- T1 door atlas (w3/w4/w5 cycle-level door tables).
- Then L2 canonical DFS on the records' class → M2, and the C1 control.
- Independent of all of the above: the §7 tour-merge probe whenever idle.

## 2026-07-29 (session 20) — field news read: **Vlad Gheorghe's preliminary a(6) = 872 claim**; both offline verify tiers pass here; we cross-validated his coordinate frame on **299 of our own words (299/299, 11/11 identities)** — frame corroborated, cell kills untested, Track B downgraded not retired

Full read: `../extraDocs/2026-07-29-vlad-a6-872-claim.md`. Clone: `../extraDocs/a6-872`
(commit `f386a8a`). New tool: `analysis/counting/coords_a6_872_frame.py`.

**The claim (Superpermutators email, 2026-07-29 00:25).** a(6) = 872, i.e. the lower
bound a(6) ≥ 872, offered as a preliminary claim for refutation. A covering simple path
has `length = 867 + e + r + l` with `r = 0`; a four-line block/component confinement
theorem (`B ≥ κ = v − s + β` from Euler on the class×loop incidence graph D(P)) makes the
cells `(e, l, s, j)` finite; **209 cells across δ = 1..4 (8/26/60/115)**, all recorded
closed, partition machine-checked as a partition. Companion `a7/`: **a(7) ≥ 5896**,
conditional on the n=6 layer, frontier δ=12.

**Verified here.** `verify_all.py --tier 1` 9/9 (~9 s) and `--tier 2` 11/11 (~3 min, all
66 offline ledger checkers + adversarial reproducers), stock Python, unmodified. The
harness reports honestly that 50 bundle-bound rows are *skipped, not passed* and 60/176
ledger rows have no checker.

**Our contribution — the frame on 299 objects.** Their own §8 names "no clean-room
reimplementation" as the top gap; they checked the frame on Houston's 872, one
non-saturated 872, and the n=5 minima. We ran their definitions (no package code) over
**296 distinct 872s + 3 distinct 873s**: T1 length identity, T2 r=0, T3 s≤5l, T4 B+x=v−s+e,
T5 B≥κ & κ=v−s+β, T6 0≤j≤e & x=e−j, T7 β≤s−1 (β=0 at s=0), T8 block confinement, T9 cell in
universe — **299/299, zero exceptions**, including the l=0 corner (e=6, s=0, β=0) that
Houston does not exercise. Two facts fell out: (1) **our entire 872 population is
coordinate-degenerate — all 296 sit in the single cell (e,l,s,j) = (0,5,25,0)**, exactly
Houston's (Δ=0, B=4, x=0), so our corpus cannot discriminate between his cell kills at all;
(2) **his B=4, x=0 IS our s19 weight multiset 575/141/3** (3 weight-3 edges ⇒ 4 blocks, no
boundary excess) — two independently derived facts about the same object.

**Grading (his ledger, and we agree with it).** rungs 869/870 effective `V-orch` all-objects;
871 `V-orch` canonical; **872 effective `L`** — 22 of 115 δ=4 cells at `L`. Open: **O5
continuation abstraction** (a real logical hole, not an evidence shortfall — the packing is
demonstrably lossy in continuation-relevant fields, 14,464 collided fibres, and this failure
class fired twice in production), **O6 prune monotonicity** (208 site certificates: 190
certified, 7 insufficient, 6 failed-then-rescued), G1 argued out of the closure by
re-derivation + adversarial audit, `scope:canonical-suffices`. Two release archives are
defective and two more were reopened mid-certification. His own AI review fleet:
**true ~90–95%, proved-to-referee-standard ~40–65%.**

**Consequences for us.**
1. **n=6 window is unconditionally still {869..872}** (only 869 is kernel-checked, by HR's
   Lean). **Track B is downgraded, NOT retired** — a sub-872 word is now ~5–10% likely, and
   Track B is expensive; but the top rung rests on two open soundness obligations in exactly
   the direction where exhaustion fails silently.
2. **Our s12–s16 grammar result is untouched** and stays the only independently produced
   structural n=6 statement we hold.
3. **n=7: the 5905 campaign SURVIVES.** 5896 = 5884 + 12; our target is δ=21. No conflict.
   **The thing to watch is whether his framework pushes n=7 past δ≈21** — that, not the n=6
   claim, would moot the 138-open-chain census. Read `a7/bundle_v2` before the next farm pass.
4. **Search-side lever:** his filters F1 (`Δ + δ ≥ 5`) and F2 (`3Δ + 4δ + 5(j − β) ≥ 20`) are
   inequalities in coordinates maintainable incrementally on a partial path — same shape as
   the HR Bound-1 item already in `RESIDUAL-BOUND-DESIGN.md`. Candidate probe: F1/F2 as beam
   pruning terms.
5. **Process note worth copying:** `GAPS.md` + `ERRATA.md` + a ledger that computes *effective*
   tier as the weakest link over the dependency closure. Best model we have seen for publishing
   a claim of this kind, independent of whether it holds.

---

## 2026-07-28 (session 19) — Track C v2 BUILT AND GATED in one session: learned COLUMN choice, v2.1 within-state pairwise training, **G2v2 formal GO (median 1.50×, Δ=0)** with the real finding being K-CLASS CANONICALIZATION; farm PC OOM-wedged mid-sweep (recoverable); two urdvr Lean results landed (LB 869/5888; lift theorem S(n)≤Egan(n)−1 ∀n≥8)

Full results ledger: `analysis/trackc/RESULTS-s19.md`. Spec (with every
deviation recorded): `docs/TRACKC2-DESIGN.md`. Ops conventions born of this
session's failures: `docs/OPERATIONS.md`. Pipeline runbook:
`analysis/trackc/WORKFLOW-V2.md`.

**Built (all committed):** dlx7g grew `--col-weights/--col-delta` (learned
column choice inside the MRV band C*_Δ), `--col-epsilon`, `--log-subtrees`
(dead-end mining: every backtracked subtree is an exact effort label, even in
TIMEOUT runs), `--dump-col-features`, `--mrv-stats`; v2.1 added `shash`
(placed-row-set Zobrist) and `--probe-rate/--probe-cap` (counterfactual
same-state column probes — the strong-branching analog). Python: colfeat.py
(10-feature extractor, parity **byte-clean** vs C, 1300 lines), mine_subtrees
(+`--pairs`), mine_stream.py (O(1)-memory miner, byte-identical output),
fit_col_effort.py (ridge + pairwise IRLS RankNet). Flagless engine bit-exact
vs v1 (21,627 / 8,548,527 pins), Windows build reproduces exactly.

**Measured:** M0: MRV ties at 62–74% of decision nodes (Δ=0 is live); zero-
weight Δ=1 alone finds the n6std cover 10.6× faster. Smoke regression model =
honest negative (chain 26 2.7× WORSE — effort regression conflates state
hardness with choice quality) → v2.1 pairwise redesign. M1: within-run
transpositions structurally impossible (DLX never revisits a state); probes
yield 150–177k pairs/min at 1.4–1.6× overhead. G2v2 blind baselines complete
on the farm (8/8 EXHAUSTED, chain 25 cross-platform bit-repro).

**G2v2 (local corpus, 16 train chains, eval never trained on): pw1 Δ=0 GO on
the letter — median 1.501×, worst 1.61×.** But the mechanism is K-class
canonicalization, not per-instance insight: guided counts collapse to
K-determined values (5/25 both K=29 → 96.4M±0.03%; 26/73 both K=30 →
10.88M±0.004%) while blind differs 2.7–3.3× within those pairs; equal-size
pair acc is .52 (no within-band signal). Wins = expensive K-members pulled
down to typical; losses = lucky-blind pulled up. Deployment answer:
**portfolio (blind ∥ guided-Δ0, first exhaust wins)** — median 1.50×, worst
1.0× by construction. G0 side note: pw1 Δ=1 finds the n6std cover in **77
nodes** (vs 21,627) and Rust-validates to 872 — the SAT-side effect at n=6 is
large; G1 (n7std) untested this session.

**Farm incident:** sweep-1 (162 gen runs) died at 65/162 when the PC lost
process creation (CLR 80004005) — root cause: worker bookkeeping slurped
~200MB logs into PowerShell arrays ×20 workers. Everything is on-disk and
resumable; gen2 (pairwise probe sweep, fixed workers) fully staged. NEEDS
MANUAL REBOOT, then: clean ERROR- ledger rows → `tc2scale.ps1` → `tc2scale2.ps1`
(runbook in OPERATIONS.md + REMOTE-FARM.md).

**Field news (big day — both documented in ../extraDocs/ with our artifact
reads):** (1) urdvr/Hunter Lean LB: **S(6)≥869, S(7)≥5888** — our windows are
now {869..872} and [5888,5906]; their lem:tau3 PROVES our "forced period=n−2"
conjecture for all k, lem:closure derives our f4≥4 penalty; their closure
lemma permits 5 consecutive full-ride loops at n=7 vs our census patterns'
max 4 → **audit kernelchain7's enumeration** (correctness-relevant). Best
transferable: Bound-1 on the residual graph ⇒ admissible lb ~r(1+1/k+…) ≈ 869
vs our ~840 at the n=6 root. (2) urdvr lift theorem: **S(n) ≤ Egan(n)−1 for
all n≥8** (certificate-level induction; 6→7 provably fails; the 5906 record is
OUTSIDE his liftable grammar — upper-bound mirror of our n=6 result). No E−3
target exists in his program: **5905 remains ours alone.** Candidate DLX
pruning rule: `StandardKernelHighMissingObstruction.lean`.

**Late-s19 continuation (same day, PC rebooted by Andrew):** farm recovered
cleanly (worker OOM bug backported first — `tc2worker.ps1` now reports file
size, never slurps); sweep-1 finished 162/162; gen2 pairwise probe sweep ran
on the v2.1 binary; corpora shipped home. Four more results landed:

1. **G1/G1b/G3: no covers, no closures — and the gate currency was wrong.**
   pw1 on n7std/c5906: 6× TIMEOUT, maxdepth ≤ blind (the 77-node n6std
   SAT-side result did not transfer). G3 portfolio trial on open chains
   {0,1,9,10,31,83}: 0/6, guided the weaker arm every time. Root cause is a
   solo throughput probe: **the column policy costs 2.4–2.6× per node** (495k
   → 208k nodes/s), so G2v2's 1.50× node GO is **~0.6× in wall-clock — NO-GO
   as deployed**. Mechanism stands (trees really shrink); deployment is
   blocked on scoring overhead. Fix order: overhead (target ≤1.2×) → gen2
   retrain → re-gate in wall-clock. RESULTS-s19 has the full tables.
2. **Residual admissible bound landed (`--bound residual`,
   `src/lb_residual.rs`, proofs in RESIDUAL-BOUND-DESIGN.md):** first-visit
   reduction makes covering-walk admissibility rigorous; Tier-1 theorem —
   the existing arc bound is OPTIMAL among per-class accounting; Tier-2 door
   terms proven residual-locally (entries ≥3/≥4 as cheap in-neighbors die);
   GA 10,400 tablebase states, 0 violations; hand-bound stratified beam
   **902 → 894** at equal width. The Hunter q_k root strength is **provably
   non-localizable** (weight-≤2 graph is connected; exitlessness collapses on
   residual sets) — root stays 838+6, power grows with depth (+9.4 at d650).
   `--bound` and `--model` don't compose yet — the certified-floor evaluator
   integration is open.
3. **Counting calibration (`analysis/counting/`):** proven local rules
   overshoot true counts by 2.4/16.2/91.6 orders (n=4/5/6); smallest-
   nonzero-L has closed form n + n! + (n−1)! − 2 = 32/147/844 — local rules
   recover exactly the classical bound, independently confirming the
   residual-bound obstruction from the counting side. Branching numbers are
   the indecomposable permutations (A003319), not w!−(w−1)!. **All 296 known
   872s share one weight multiset (575·w1 + 141·w2 + 3·w3)** — the record
   class is maximally rigid. (Corpus is 296 words, not 298 — CLAUDE.md
   corrected.)
4. **Ops hardening after the farm wedge:** `docs/OPERATIONS.md` — pre-launch
   disclosure rule for >30-min compute, mandatory STATUS/ledger heartbeats,
   monitor + stall alerts, abort commands, runtime cheat sheet.

**Next session:** (1) dlx7g column-scoring overhead attack (feature caching /
incremental scores / score-only-on-ties), then re-gate G2v2 in WALL-CLOCK;
(2) DONE late s19 — pw2 retrain: equal-size acc .5191, canonicalization confirmed at coefficient level; optional lever: separate equal-size tie-break head (.5406 held-out, min_child_load); superseded item was: retrain pw on the gen2 55-chain pairwise corpus
(`analysis/trackc/runs/v2/farm/`) — offline check only: does equal-size pair
accuracy move off ~.52?; (3) integrate `--bound residual` with `--model`
(certified floor + learned residual — the founding-idea composition);
(4) kernelchain7 5-full-ride audit (lem:closure allows 5 at n=7; census
patterns max at 4 — coverage-of-enumeration question); (5) try
`StandardKernelHighMissingObstruction` as a DLX instance prefilter; (6) s16
Egan patch still unsent.

## 2026-07-28 (session 17b, overnight continuation) — census jumps 41 → **85/223 closed**: 52 chains are STRUCTURALLY uncoverable (zero-candidate column) and the farm's SAT pass missed 44 of them; merged multi-engine ledger committed; DLX sweep re-aimed at the 138 survivors

Overnight continuation of s17's Track C session, after s18's pass-1 census
landed. The local dlx7g sweep's first 37 chains held a surprise: 3 "UNSAT in
under a second" verdicts (chains 34/37/41, K=30) on chains the farm's CaDiCaL
ran 30 minutes on and left undecided. Investigation: those instances each have
a **zero-candidate column** in the canonical formulation
(`chain7.build_instance_from_chain`) — no rows can cover one orbit, so no cover
exists, unconditionally. That is s13's structural-refutation mechanism; the
farm worklist evidently never got the prefilter.

**Running the structural test over all 223 worklist chains: 52 are structurally
uncoverable** (14 × K=30, 38 × K=31; indices in
`analysis/cover7/results_n7_merged.csv`), of which **44 are new closures**
beyond CaDiCaL's 41. Merged census (`analysis/trackc/census_merge.py`, output
`analysis/cover7/results_n7_merged.csv`, precedence STRUCTURAL > UNSAT > OPEN,
any SAT surfaced loudly): **STRUCTURAL 52 + UNSAT 33 = 85/223 closed; 138 OPEN**
(5 × K=27, 19 × K=29, 30 × K=30, 84 × K=31).

**Discrepancy RESOLVED same night — encoder bug found and fixed.**
`sat_chain.py` (which `satworker.py` shells out to) built its at-least-one
clauses by iterating `by_col` — a dict **keyed from the rows** — so a column
with zero candidate rows never became a key and got *no clause at all*
(`sat_chain.py:51` pre-fix). CaDiCaL was handed a relaxation with 554/555
columns constrained: a genuinely hard formula whose contradiction was never
encoded — that is exactly why structurally-dead chains burned full 30-min
budgets. Consequences: the CNF was a strict clause-subset of the canonical
instance, so **all 41 pass-1 UNSAT verdicts remain sound**
(relaxation-UNSAT ⇒ true-UNSAT). Precision on the timeouts: only chains that
*have* a zero-candidate column lost a clause — so the 44 structurally-dead
timeouts were spent on a relaxation, while the remaining **138 open chains'
CNFs were bit-identical to canonical and their timeout verdicts stand** as
genuine hardness evidence (re-running CaDiCaL on them post-fix would change
nothing). Fixed: `sat_chain.py` now iterates `inst["columns"]` and
short-circuits a zero-candidate column to the exit-2 UNSAT path
("STRUCTURAL-UNSAT … 0 cuts, unconditional"). Verified locally with a stubbed
solver: chain 34 → exit 2 before any solving; chain 6 (non-structural) still
builds all 147,764 clauses and reaches the solver, with an assert that no
empty clause ever passes through. A SAT could never have slipped through
either way (`assert rep["exact_cover"]` fires post-model), so the bug only
ever wasted time, never soundness.

**Engine-agreement datum**: within the 37 chains both engines attempted, zero
dominance either way — DLX never closed a non-structural chain CaDiCaL
couldn't, and never timed out where CaDiCaL succeeded. The two encodings
appear to hit the same wall, which sharpens s18's conclusion: the 138
survivors need a different *method* (symmetry reduction, Track C v2 column
learning, better encodings), not more budget.

**Local sweep re-aimed**: now iterating exactly the 138 open chains
(worklist mode in `census_sweep.sh`), 10-min caps (decidable chains die in
minutes — median 1.85 min in pass 1), 4 nice'd workers, resumable CSV at
`analysis/trackc/runs/census/results.csv`. Any exit-0 SAT is flagged for
validation, never auto-believed. Expected yield is modest; the point is that
no open chain goes un-attempted by the second engine family.

**Sweep FINISHED (07:05 next morning): all 133 remaining open chains
attempted by DLX — 133/133 TIMEOUT at 10 min, no SAT, no new closures.**
Every one of the 223 census chains has now been attempted by both engine
families; the ledgers are committed (`analysis/cover7/results_n7_merged.csv`
+ the raw DLX ledger `results_n7_dlx_sweep.csv`). Final census: **85 closed
(52 structural, 33 search-UNSAT), 138 open, both engines agreeing the
survivors are out of reach of blind complete search at these budgets.**

**Next session:** (1) Track C v2 (learned column choice, dead-end mining) per
`analysis/trackc/RESULTS-s17.md`; (2) pass 2 on the 138 survivors should lead
with symmetry reduction, the one method that ever worked at n=7 (satworker's
encoder fix is in but changes nothing for the survivors — their CNFs were
already canonical); (3) the s16 upstream patch to Egan remains unsent.

## 2026-07-28 (session 18) — n=7 refutation pass 1 COMPLETE: 223/223 chains attempted, **41 unconditionally refuted**, 182 undecided at the 30-min budget, no SAT

The PC farm finished its first full sweep of the V₇=15 census. Ledger committed
as `analysis/cover7/results_n7_pass1.csv` (223 rows: timestamp, index, pattern,
K, Σ, engine, outcome, best_partial, minutes, pid, word_file).

| K | UNSAT / attempted | decided |
|---|---|---|
| 27 | 0 / 5 | 0% |
| 29 | 2 / 21 | 10% |
| 30 | 6 / 48 | 12% |
| 31 | **33 / 149** | 22% |
| **all** | **41 / 223** | **18%** |

**No SAT** — no candidate 5905 word from any chain.

**What the 41 are worth.** Each is an unconditional refutation: CaDiCaL UNSAT at
0 cuts over the exact-cover encoding, with **no symmetry assumption**, so it
rules out *every* cover of that chain — asymmetric ones included. That is
strictly stronger than the published negatives in this area, which come from
symmetry-reduced searches (Egan's 2SYMM route). And the column is
cross-validated: s16's patched PermutationChains, an independent engine on an
independent encoding, agreed with our verdicts on 6/6 chains sampled.

**Solve-time structure — decisive for pass 2.** UNSAT times: min 0.02, median
**1.85**, max 32.17 minutes; **25 of 41 landed under 5 minutes**. So decidable
chains are overwhelmingly *fast*, and the 182 timeouts are not "nearly done" —
they are qualitatively harder, not marginally slower. Raising the budget alone
will therefore yield little: a 4× budget would likely convert only the handful
near the 30-min boundary. Difficulty also tracks K inversely (K=31 decides 22%
of the time, K=27 zero of five) — consistent with lower-K chains having more row
freedom and hence bigger search spaces.

**Reading.** Pass 1 closes 18% of the penalty-≤16 space at n=7 unconditionally.
The remaining 182 need a better method, not more minutes — exactly the gap
Track C v1 identified from the other direction (s17: guided row ordering is a
22× win at n=6 but a NO-GO on the n=7 cover gates; the open lever is learned
*column* choice). Two engines, two sessions, same conclusion: n=7 cover decision
needs a structural improvement, not more compute.

**Next:** (1) pass 2 aimed at *method*, not budget — learned column choice
(Track C v2), symmetry-reduced encodings where chains admit them, or s17's
`dlx7g` as a third opinion on the survivors; (2) the 41 refutations plus s11's
n=6 theorem are enough to draft the write-up; (3) send the s16 fopen/`FILE*`
patch upstream to Egan.

## 2026-07-27 (session 17) — Track C v1 built end-to-end and gated: learned row ordering inside DLX works (22× on n=6) but does NOT crack the n=7 cover instances at 60 min; row order proven irrelevant to UNSAT under MRV; a local DLX census sweep opened as a third refutation engine

Track C (the thesis — learned evaluator inside the cover search) went from zero
code to a fully gated v1 in one session. Spec: **`docs/TRACKC-DESIGN.md`**
(locked 8-feature vector, pre-`cover(c)` timing, holdout design); results:
**`analysis/trackc/RESULTS-s17.md`**; code: `analysis/trackc/` (instances.py,
replay.py, `dlx7g.c`, solve_guided.py, census_sweep.sh), `ml/fit_cover_rank.py`,
models `ml/models/trackc_model{A,B,N6}.*`. Built by parallel subagents against
the locked spec; every cross-language boundary gated.

**What was built (all gates green):**
- **Corpus**: 296/296 n=6 record words extract to certificates and replay
  (`extract_certificate` → map to `gain1.build_instance(6)` rows →
  `check_cover`), plus 3/3 5907 and 11/11 5906 certs → **9,150 teacher-forced
  decisions / 21,423 (pos, neg) sibling pairs** over 12 exported instances
  (`data/trackc/instances/`, incl. the 5 open K=27 chains).
- **Engine**: `dlx7g` — guided descendant of the farm's C DLX: variable child
  count (n=6 and n=7 instances), incremental `grounded[]`/`pending[]` forest
  features on the undo trail, `--weights` linear row ordering, ε-restart
  diversification, `--dump-features` parity mode. **Python↔C feature parity is
  byte-clean** (the one boundary that could silently poison everything).
- **Trainer**: numpy pairwise RankNet (s8 architecture), standardization folded
  into exported weights; two honest holdout models (A: n6+5906, gates on 5907;
  B: n6+5907, gates on the 5906 K=18 chain).

**The positive result: the mechanism works.** On the n=6 standard instance
(known-SAT), learned ordering cuts nodes-to-first-cover **21,627 → 961 (22.5×,
model B)**. And cross-n transfer is real: a model trained ONLY on n=6 ranks
n=7 cover rows at 0.746 pair accuracy (chance 0.51). The certificate-level
features do carry structure across n — the thing item 3's walk-level features
never did.

**The honest negative: G1/G1b NO-GO.** On the two held-out known-SAT n=7 gates
(standard K=5, 690×4440, R=138; and the real 5906's K=18 chain, R=124), guided
and blind alike: 6/6 TIMEOUT at 60 min, max depth ~112/138 and ~98/124,
depth differences noise-level, ~600–790M nodes per run. Top-1 ≈ 0.62–0.68 per
node compounds to ~0 over a 138-deep all-correct descent — a static linear
ranker over local features cannot bridge the n=7 plateau. Per the design's
gate criteria the K=27 record attack (G3) was NOT triggered.

**A structural theorem-lite from G2**: with the column rule fixed (MRV), row
ordering permutes the DFS but the exhaustion tree is the *same node set* —
verified byte-identical node counts (60,037,516 and 8,548,527) blind vs guided
on two refuted chains. Row ordering is purely a time-to-first-solution lever;
**UNSAT economy needs learned COLUMN choice** — the top v2 lever.

**Bonus, possibly the sleeper result: dlx7g is a fast third refutation
engine.** It exhausted farm chain 5 (K=29) in 8 min and chain 26 (K=30) in
64 s locally — fresh independent confirmations of the CaDiCaL+Egan verdicts,
DLX encoding, third engine family. A **local census sweep** over the 218
unclaimed-by-us worklist chains is now running (`census_sweep.sh`, 4 workers,
30-min caps, resumable, results → `analysis/trackc/runs/census/results.csv`;
any exit-0 SAT candidate is flagged for validation, never auto-believed).
Check it before starting new compute on this machine.

**v2 levers recorded in RESULTS-s17.md**: (1) learned column choice, (2)
dead-end mining (off-path training), (3) value-based restarts, (4) CDCL
phase/branching biasing from the same model, (5) MLP. Dead v1 features:
`min_child_sz_log` (zero within-node variance under MRV — the chosen column is
everyone's child and the global min); `grounds_pending` weak-negative in
teacher-forced data.

**Next session:** (1) read `analysis/trackc/runs/census/results.csv` — the
sweep verdict tally (UNSATs close census chains; cross-check against the
remote farm's ledger); (2) Track C v2: learned column choice is the highest-EV
lever, dead-end mining second; (3) the farm patch upstream to Egan (s16)
remains unsent.

## 2026-07-27 (session 16) — two real upstream bugs found and patched in PermutationChains (not a stack overrun at all); the refutation census is now CROSS-VALIDATED by an independent engine (6/6 agree); one earlier claim retracted

**Root cause of the broken Windows build — two genuine defects in
`PermutationChains.c`, both invisible on macOS** (patch + upstream write-up:
`analysis/cover7/PermutationChains-fopen-fix.patch`, 3 lines):

1. **Invalid `fopen` mode strings `"wa"` / `"aa"`** (3 sites). BSD libc reads
   only the leading character and ignores the rest, so macOS behaves as
   intended. The Microsoft UCRT validates the whole string, trips the
   invalid-parameter handler, and calls `__fastfail(FAST_FAIL_INVALID_ARG)` —
   which raises **0xC0000409, the same status as a `/GS` stack-cookie
   failure**. That is why it misreported as a stack overrun and why `/Od`,
   `/GS-` and larger stacks all changed nothing. Reduced 12-line repro on the
   PC reproduces 0xC0000409 exactly under `cl /O2`. (glibc/mingw are a third
   case: they return NULL and the program exits via its own error path.)
2. **A dropped assignment**: the second `fopen`'s result is discarded, so `f`
   still points at the twoCycles stream `fclose`d three lines earlier ⇒ the
   NULL check tests the wrong pointer, `printSuperPerm` writes to a closed
   `FILE*`, `fclose` double-closes, and the real stream leaks once per solution
   (42,288 times at n=6). Undefined behaviour, masked on macOS only because BSD
   libc recycles the `FILE` slot and hands the stale pointer the new file.

With the patch, **native MSVC builds and works** (mingw-w64 too; the two
binaries are byte-identical in output). Gate on Windows: `5` → **6**,
`5 nsk444` → **6**, `6 ffc` → **36** (Egan's documented number), all exit 0 with
solution files written. The full `6` → 42,288 counts are still grinding
(~7.7k/42,288 at last look) — not a defect: F: does **48 ms per file
open/close** and Egan reopens two files per solution. Verdict any time via
`F:\superpermFarm\gate6verdict.ps1`. ASan/UBSan were unusable (sanitized
binaries hang in dyld init on this macOS) and could not have caught defect 2
anyway — `FILE` is not malloc-tracked.

**The result that matters: our refutation census is independently
cross-validated. 6 of 6 chains agree, 0 disagreements.** Egan's plain mode is a
complete DFS with sound pruning, so it is a true independent oracle for our
CaDiCaL UNSATs: chains 5, 25 (K=29) and 26, 43 (K=30) exhausted with 0
solutions, exit 0; chains 33, 35 (K=30) were rejected as structurally unviable
before search. Windows and macOS traces are byte-identical bar one
`sizeof(long)` line. Two independent engines, two independent encodings, same
verdicts — the UNSAT column of `results.csv` can be trusted.

**RETRACTION (s13 NOTES).** "PermutationChains asym coverFirst on chain 0: DXL
reached minColsLeft=0 — EXACT COVERS OF CHAIN 0 EXIST … process then died
silently" is **wrong on both counts**. `coverFirst` does not crash: chain 0
completes with exit 0 and zero solutions. And `minColsLeft=0` refers to the
cover-first *reduced* subproblem at depth 93, not a 141-size cover. There is no
evidence that chain 0 has a cover.

**Farm state:** 27 CaDiCaL workers, 60/223 claimed, ledger 6 UNSAT + 27
TIMEOUT-KILLED. Roughly 80% of chains exceed the 30-minute budget, so the first
pass will be a partial census; the sensible follow-up is a longer-budget second
pass over the survivors, or a better encoding.

**Next session:** (1) `results.csv` census tally; (2) send the patch upstream to
Egan — it is a live defect for anyone building his code on Windows; (3) Track C
(learned ordering) remains the one lever aimed at the instances both engines
time out on.

## 2026-07-27 (session 15) — the positive control paid for itself: the Windows PermutationChains binary was BROKEN (all its farm output void); no engine can *find* a known cover; farm re-aimed as a validated refutation engine (first real UNSATs)

A correctness session. Everything here follows from insisting on a positive
control before believing a negative.

**The control failed, then the binary failed.** Pointing the farm's engine at the
standard K=5 kernel — which provably HAS covers (the known 5907s are built from
it; our ledger's 143 = 138 rows + 5 loops matched exactly) — it ran 9 minutes,
reached PCsolSize 121/143 and exited empty. Chasing that, the agent ran Egan's
own smoke tests: **`PermutationChains.exe 5` and `6` exit `0xC0000409`
(STATUS_STACK_BUFFER_OVERRUN) with zero solution files**, under `/O2`, `/Od`, and
`/O2 /GS-` alike, while the identical source under clang on the Mac gives the
correct 6 and 42,288 solutions. ⇒ **Every chain that farm ever reported as
"finished" is void — those chains were never searched.** (This also retro-
explains s14's "orderly exits" and the Mac's mid-line truncations: a latent
memory bug, caught by MSVC's stack cookie, tolerated by clang.) The
PermutationChains farm was stopped.

**What the modes actually are** (source-read, for the record): `searchPC` (plain)
IS a complete DFS with only sound pruning — so an exhaust *would* be a genuine
refutation, if the binary worked. `trackPartial` is print-only. `coverFirst` is a
DLX pre-pass. `stabiliser/limStab/symmPairs/littleGroup/blocks/fullSymm` are
symmetry reductions. **Egan's n=7 recipe was `7 fullSymm limStab ffc`** — a
4-cycle kernel *plus symmetry* (762 solutions, ~30 min); he never claims plain
mode completes at n=7. The `nsk` path was verified faithful (`nsk444` ≡ default
at n=5 → 6 solutions; `nsk5555` ≡ default at n=6 → 42,288).

**The hard, honest negative: nothing we have can FIND a cover.** Control gate on
two known-SAT instances (standard K=5; the real 5906's K=18 chain), three
engines — CaDiCaL, Python DLX, C DLX — **none found a cover in > 45 min each**.
The 5907/5906 words this project "compiled and validated" in s13 were
**reconstructed from published words, not discovered**; that claim is corrected
here. These instances are simply hard, and Egan needed symmetry reduction to
crack them at all.

**Farm re-aimed as a refutation engine.** `satworker.py` (CaDiCaL over the
exact-cover encoding) runs because its **UNSAT direction is validated** (K=29
chain UNSAT in 33 s CaDiCaL / 49 s kissat, at 0 cuts = unconditional), and any
SAT would be auto-compiled and validated before being believed. 27 workers,
**30-min per-chain budget** (fixes s14's permanent queue stall — 193 of 218
chains had never started), atomic `O_CREAT|O_EXCL` claims, write-once row files
rebuilt into `F:\superpermFarm\results.csv`. Worklist 223 (5 K=27 first).
**First real outcomes: 3 UNSAT** (0.11–1.96 min each), 30/223 claimed.

**Reading.** The farm's realistic product is now a *census of refutations*
narrowing where a 5905 could hide — not a record. Combined with s11's n=6
theorem, the shape of a paper is "Egan−1 is optimal in the gain-one class at
n=6, and here is how much of the n=7 penalty-≤16 space is closed." The record
itself, if it is reachable at all, needs the search to get smarter — symmetry
reduction (Egan's own lever) or Track C's learned ordering — not more cores.

**Next session:** (1) read `results.csv` — how much of the 223 is closed; (2)
consider a symmetry-reduced encoding (the one lever known to work at n=7); (3)
Track C / Track B remain the research lines.

## 2026-07-27 (session 14) — the search moved to a 28-core PC (27 workers, 96% CPU, survives disconnect); two "crash" diagnoses refuted; the real open question is whether an orderly finish REFUTES a chain

Infrastructure session, plus one reinterpretation that may matter more than the
compute. Operating runbook: **`analysis/cover7/REMOTE-FARM.md`**; scripts:
**`analysis/farm/`**. Both are written for an agent with no memory of this work.

**The farm moved off the laptop.** Windows PC (`ssh transcribe`, 28 cores, 48 GB,
standard user, **not** admin). Everything lives on `F:\superpermFarm`; C: is
nearly full and `F:\audioPrime` (a separate production app) is off-limits.
Persistence was the whole problem: Windows OpenSSH kills its session's process
tree, WMI process creation is denied, and `schtasks` can only register
"Interactive only" tasks without stored credentials. Solved as a plain user with
**`detach.exe`** (`analysis/farm/detach.c`) — `CreateProcess` with
`CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP |
BELOW_NORMAL_PRIORITY_CLASS`, opening its own log handles and restricting
inheritance to exactly those three (otherwise the child inherits sshd's pipes and
every ssh call hangs). Verified by a marker process surviving a full disconnect.
An optional admin installer (SYSTEM tasks, `/sc ONSTART`, for reboot survival)
exists but was deliberately **not** run — more privilege than the job needs.

**Scaled to 27 workers / 96.2% CPU** (`farmscale.ps1`, backfilling scheduler
against a 218-pattern worklist, K=29 → K=30 → K=31; the 5 K=27 chains run
untouched at top priority). RAM is not the binding resource: 4.4 MB peak per
worker against 37 GB free, so cores bind (cap arithmetic and a 15%-free valve
are in the script anyway). `watchdog.ps1` does one backfill pass per call and
logs free RAM; it is called from the Mac, not scheduled (non-admin).
**Validation gate passed before any launch**: `gen_worklist.py` derives the
KernelFinder `nsk` patterns from the census (ride length `((j−k) mod 6)+1`) and
refuses to emit a worklist unless it reproduces the five known K=27 strings
exactly. Nuance found there: the published tier counts (5/21/48/149) only
reproduce if the **terminal loop is allowed a partial ride** — with a forced full
terminal ride the census is 5/21/40/141.

**Two "crash" diagnoses refuted by measurement, in sequence** (recorded so nobody
re-runs them): *stack overflow* — `searchPC`'s frame is 128 bytes over ~141
levels, peak stack under 100 KB; a 64 MB rebuild (`dumpbin`-verified) changed
nothing. *OOM* — 4.4 MB RSS against 37 GB free. What the logs actually show is an
**orderly exit**: a complete final line with trailing newline after the
`PCsolSize=…` best-partial dump, 0-byte stderr. Three K=29 chains "finished" in
~1 CPU-minute. (The mid-line truncation seen earlier on the *Mac* was genuine
memory pressure there — 13 solvers on a laptop — which is what sent the second
diagnosis down the wrong path.)

**THE OPEN QUESTION, and the session's real deliverable.** If the engine's plain
mode is exhaustive, then a chain finishing without a solution **refutes** it (no
rooted cover ⇒ no 5905 from that chain) — and the farm is a refutation engine
producing publishable negatives at ~1 CPU-minute per K=29 chain, which would
close large parts of the census fast. If the mode is bounded/heuristic, finishing
means only "this strategy gave up" and refutes nothing. **Positive control
launched** (`runs\ctrl`, standard K=5 kernel `nsk66666`, which provably HAS
covers — it is how the known 5907s were built): at last check it was climbing
normally (PCsolSize 121 of target 143). If it finds a cover, orderly completion
elsewhere is meaningful; if it also completes empty, every "finished" chain means
nothing. **Do not characterize any chain as refuted until this control returns.**

**Still no 5905.** Nothing about sessions 10–13's proven results changed.

**Next session:** (1) read the control's verdict first — it decides whether the
farm's finishes are refutations or noise, and hence what the whole campaign has
produced; (2) `watchdog.ps1` periodically to backfill; (3) if finishes ARE
refutations, tally which chains are eliminated and re-aim at the remaining
tiers + the pen ≥ 17 census; (4) Track C (learned ordering) and Track B (n=6
871 hunt) remain the unstarted research lines.

## 2026-07-27 (session 13) — record attempt round 1: no 5905 yet, but the formalization is proven record-capable (real 5906s parse as V₇=10 partial-ride certificates and recompile validated); 5904 closed at pen≤16; the open question reduced to concrete instances

One mega-thread (the cover agent; 2.4 h). Pipeline in **`analysis/cover7/`**;
engines were left running — check `pgrep -f "PermutationChains 7 nsk"`.

**The validation that matters most.** The actual 5906 record words exist on the
superpermutators GitHub (urdvr's tree never had them). Our
`extract_certificate` **accepts them as partial-ride certificates at exactly
V₇ = 10** — K=18/Σ=8, K=20/Σ=10, K=24/Σ=14 variants — precisely as the ledger
priced the 5906 sight unseen in s10, and the pipeline **recompiles a
cargo-validated 5906** from the extracted certificate. Positive controls also
rebuild the standard instance byte-identically and compile a validated 5907.
The formalization provably expresses record-class words end-to-end; nothing
about the framework is a toy.

**Census corrected and completed** (cross-validated against Egan's KernelFinder
after a diff caught 16 missed terminal-partial-ride chains): V₇=15 cost-3-only
= 5×K=27 / 21×K=29 / 48×K=30 / 149×K=31 (+1581 at K=32/33); **mixed-cost chains
don't exist at penalty ≤ 16**; V₇=20 = 4 chains.

**Search outcomes.** The wall is exact-cover existence, not rootedness (it
never engaged): all 4 V₇=20 chains structurally uncoverable ⇒ **5904 closed at
pen ≤ 16**; one K=29 chain proven UNSAT (CaDiCaL + kissat); 662 chains refuted
by zero-candidate columns; **all 8 palindromic K≤31 chains have no
2-fold-symmetric cover** — Egan's 2SYMM method (the only method that ever
produced a nonstandard n=7 record) provably cannot give 5905 from pen≤16
kernels. OPEN: the 5 K=27 chains (3 distinct up to reversal) and most K=30/31 —
CDCL/MILP/DLX stall for hours both ways; Egan's own engine gets deepest
(129/141 2-cycles) before a reproducible crash.

**Reading.** 5905 is neither found nor excluded — it now hinges on a handful of
named instances, and the failure mode (solvers stall, no refutation) means the
answer is genuinely hard, not obviously empty. This is also exactly the search
regime Track C was designed for (learned row/column ordering inside DLX at the
570-column scale where blind heuristics stall). Next moves recorded in
`analysis/cover7/README.md`: coverFirst crash fix, multi-day CDCL on the three
distinct K=27s (UNSATs would close Σ=12), the 916 open K=32/33, pen≥17 census,
cube-and-conquer on skipped-orbit columns.

## 2026-07-27 (session 12) — n=6 proof independently verified (clean-room Rust, all claims agree); n=7 campaign: V₇=15/20 kernels EXIST and are row-count-feasible — 5905/5904 now hinges on the rooted cover

Two threads, both landed. Sharing decision (Andrew): hold the n=6 result until
stronger confirmation (✅ this session) AND a positive finding to lead with —
the n=7 cover attempt (launched at session end) and Track B's 871 hunt are the
candidates.

**Thread 1 — clean-room verification: every claim AGREES (commit `f8603d3`).**
`src/cert.rs` (~900 lines + 8 tests) reimplements the n=6 kernel-chain proof
from the mathematical definitions alone — the agent was barred from reading the
Python campaign, extraDocs, and the result docs. `cert-verify -n 6` (1.4 s)
prints a per-claim verdict table: C1 forced map = permutation with 180 cycles
all length 4 ✓; C2 pivot confinement, entry-landing automatic ✓; C3 max V = 8
via exhaustive B&B (0.98 s, 15.8M nodes), exactly 12 chains, same (K,Σ,f4)
census ✓; C4 zero covers for all 12 — strengthened: no exact cover exists even
before rootedness — with the standard-kernel positive control finding a rooted
25-row cover ✓; C5 ledger ✓. `docs/RESULT-gain1-optimality-n6.md` upgraded to
"independently verified". Conventions worth remembering: door(s,5) = door(s,6)
identically at n=6; cost-6 strictly dominated.

**Thread 2 — n=7 max-V₇ campaign (`analysis/kernelchain7/`).** Gates: the three
known 5907s trace to standard-kernel certificates from raw strings (census
4182/853/4 — the kernel really is the K=5 standard chain, all three, up to
relabeling); the 5906 census prices to V₇=10 exactly. Structure: forced-map
period **5 = n−2** on all 5040 states (mirrors 4 = n−2 at n=6 — conjecture: the
forced period is n−2 generally, which would make the standard kernel the
skip-free maximum at every n); pivot confinement at all costs; **skip-1 lemma**
(720/720): skip-1 hops land on the preceding loop of their own forced 5-cycle,
so net-positive deviations cost ≥ 2 skip ⇒ **proven V₇ ≤ 74**, and the naive
signatures (K=18,Σ=3)/(K=24,Σ=4) are empty. Search (complete B&B infeasible at
n=7): **V₇ = 15 chains are plentiful** (100 enumerated; sample: K=27, Σ=12 =
standard-kernel prefix + six skip-2 deviations, R=114, 2662 eligible rows —
count-feasible); **V₇ = 20 exists** (4 found; K=46, Σ=26, R=94, 1545 eligible);
best heuristic V₇ = 36 (beam; would be waste 855 if coverable — but high-K
optima are already count-infeasible, echoing n=6). Ledger: V₇=15 ⇒ **5905**,
V₇=20 ⇒ **5904**. The 5906 word itself is not distributed anywhere in the urdvr
tree (kernel extraction impossible for now).

**The decisive open question is now singular: does any V₇ ≥ 15 chain admit a
rooted exact cover?** A yes, compiled and validated, is a world record. Odds
look materially better than n=6's refutation: the V₇=15 chains are low-K
(structure close to the standard kernel, which IS coverable), with 20×+ more
eligible rows than needed, whereas n=6's fatal chains rode 20–22 of a 24-loop
class. Next: kernel-parameterized DLX (urdvr's compiler is kernel-generic;
`build_instance` is the only standard-bound piece) over the 100 V₇=15 chains +
the 4 V₇=20s, forest pruning on, compile any solution via their certificate.py,
validate with our validator, price via the ledger.

**Also next: Track B design** (the n=6 871 hunt — sojourn-level out-of-grammar
search; sharpened fact from this session: every inter-orbit w2 is necessarily a
w2x edge, so Track B's freedom is purely structural: non-laminar nesting,
sojourn patterns outside {2,3,4,6}, w3/w4 placement — budget X + #w3 + 2#w4 +
3#w5 = 27 vs the records' 28).

## 2026-07-27 (session 11) — item 5 step 2 executed to a proof: Egan−1 = 872 is OPTIMAL in the gain-one grammar at n=6 (kernel door closed, any hop cost); n=7 becomes the in-grammar attack; n=6 sub-872 must leave the grammar

Continuation of s10, same day. Three probe rounds (one subagent, kept alive across
rounds) answered s10's "whole game" question — negatively, with exhaustive proofs.
Scripts committed to **`analysis/kernelchain/`** (self-contained stdlib Python;
gate-validated); design note revised in place (`docs/ITEM5-DESIGN.md` §3–4).

**Round 1 (relation + gate + first search).** Hop relation extracted from
certificate.py/liftcheck.py and validated: the standard kernel's three hops are
recovered as the *unique* options per pair. Findings: every loop has cost-3
out-degree exactly 5; **cost-3 hops preserve the pivot** (6 disjoint 24-loop
classes, orbit-disjointness automatic in-class); the strict full-ride relation has
**period exactly 4** from all 720 (loop, entry) states — K=8 strict is impossible,
and this is *why* the standard kernel has n−2 = 4 loops. Liberal (nsk-style
partial-ride) chains reach K=8..24 abundantly — but partial rides skip orbits.

**Round 2 (the skip-priced ledger — correction to s10's headline).** Skipped
kernel orbits must be bought back by rows: **waste = 148 − K/4 + Σskip/4**
(+f4 + 2f5 for cost-4/5 hops), so liberal K=8 lands back at 872 and the 871
target became K − Σskip − 4f4 − 8f5 ≥ 8 (minimal: K=12, Σskip=4). Exhaustive
answer: **K=12/Σ=4 does not exist; K=16/Σ=8 does not exist; max K−Σ = 8 only at
K=22/Σ=14** (6 chains, one per pivot class, relabelings of one) — and those die
on rows: 24 non-root orbits need 6 row loops, only 2 exist. Standard-kernel
sanity under the skip formula: all skips 0, waste 147 ✓.

**Round 3 (mixed costs — closing the last door).** My cross-pivot hypothesis was
*refuted*: a door of any cost ends with the pivot symbol (analytic +
computational), so pivot confinement is absolute at every hop cost. B&B over
costs 3–6 (complete, ~30 s): **max V = 8, exactly 12 ledger-optimal chains**
(the 6 old K=22s plus 6 new K=20/Σ=8 with one skip-0 cost-4 hop that resets the
period-4 cycle for free). **All 12 fail the rooted exact cover** (0 covers;
checker validated by re-finding the known 25-row cover under the standard
kernel, ~11 s). V=12 (⇒ 870) unreachable.

**Theorem (combined): in the gain-one certificate grammar — complete rows, hops
of any cost — length 871 is unreachable at n=6. Egan−1 = 872 is optimal in the
class; the standard kernel is a proven optimum, not a convention.** Incomplete
rows are strictly waste-positive (fewer children per split), so they tie 872 at
best. This answers Robin's nonstandard-kernel suggestion at n=6 with a proof,
and explains why the record has stood.

**Also derived (general, no grammar assumption): waste = (S−1) + #w3 + 2#w4 +
3#w5** for any tight walk with S sojourns — the bridge from the grammar theorems
to general search (an 871 needs e.g. S=144 with three w3s).

**Steering (user checkpoint this session): keep the novel bet central.** Recorded
in the design note §5: the chain campaign was scouting (tiny spaces, complete
search, ended in proofs — ML would have been decoration); the learned bet is
load-bearing where spaces explode. Re-centered plan, three tracks
(`ITEM5-DESIGN.md` §4):
- **Track A (in-grammar, n=7)**: port kernelchain to n=7 (840 loops; period and
  pivot structure unknown) — max V₇ campaign; V₇ ≥ 15 with a feasible cover
  beats 5906 (5905); the 5906's own kernel is a known-good seed. Cover search is
  large ⇒ first real deployment of Track C.
- **Track B (out-of-grammar, n=6)**: sojourn-level search for S−1+#w3+... = 146
  outside the certificate class; also the right frame for impossibility lemmas
  that could extend the proven floor toward 872.
- **Track C (the thesis)**: learned evaluator over partial certificates/sojourn
  plans — 296 records as labeled certificates, prefixes as positives, DLX
  dead-ends as negatives; s8 anchored ranker as baseline architecture.

**Next session: Track A** (n=7 port: period, max V₇, chain census — the decisive
computable question), and Track B's state/move design note.

## 2026-07-27 (session 10) — item 5 opened and designed: records are exactly K=4 certificates; waste = 148 − K/4 ⇒ an 8-loop kernel chain + 20-row cover = 871; design note committed

Two parallel subagent threads (cycle-level trace of the record corpus; formal
digest of the urdvr certificate machinery), then synthesis. The outputs interlock
so cleanly that item 5's design collapsed from "big open-ended build" to a
three-step attack on one finite combinatorial question. Full design:
**`docs/ITEM5-DESIGN.md`** (the session's product — this entry is the summary).

**Thread A — cycle-level trace of all 296 872s (script in scratchpad,
`cycletrace/cycletrace.py`, regenerable).** The record grammar is *exact*, zero
exceptions across 296 walks: 145 sojourns each; the transition alphabet is two
letters — 141 × `w2x` (every single w2 in every record is the cross-cycle
P[2:]+P[1]+P[0] edge; in-cycle w2 never occurs) + 3 × w3 (always to fresh cycles,
always at sojourn index ≡ 0 mod 5); sojourn lengths ∈ {2,3,4,6} only; splits only
2+4 / 3+3 / 4+2 / 2+2+2 with doubles + 2·triples = 25 always; interruption nesting
is laminar in 296/296 (depth up to 16 — the "tree-like" lore is true but deep, not
shallow); interruption gaps have ≡ 4 mod 5 sojourns with every gap cycle fully
completed. Contrast: greedy's 873 and our stratified 873 are cycle-level
*identical* (120 clean length-6 sojourns, no nesting) — the record trick is
swapping 15 w3 + 4 w4 + 1 w5 exits for 25 nested w2x detour-and-returns.

**Thread B — urdvr machinery digest (file:line-pinned).** Marked loop = pivot +
5-necklace, its 5 splices are w2x edges linking 5 cycles; oriented row = loop +
parent choice = exactly our detour (enter from parent, ride 4 children fully,
return); kernel = K orbit-disjoint loops chained by K−1 cost-3 hops
(T3(p)=T2(q)); certificate = kernel + rooted exact cover by rows; the walk-replay
exact-once condition is the only true correctness invariant. Load-bearing
discoveries: the certificate *compiler* is already kernel-generic (only
`build_instance`/`ladder`/`gain1c` hard-code K = n−2), it even anticipates
"nsk-style partial rides"; the n=7 5906 census (20 loops, 19 T3, 822 T2, 5
incomplete groups) identifies it as a K=20 certificate with concessions; and
rootedness/exact-cover are correctness conditions (rootless rows are never opened
by the walk), while {kernel size, row completeness, hop cost} are the class
restrictions — the doors to sub-Egan−1.

**Synthesis — the waste ledger (verified against every known data point).**
Hyperedge-forest counting gives waste = m + 118 (m = total loops, n=6), and with
complete rows m = 30 − K/4, so **waste = 148 − K/4, K ≡ 0 mod 4**: K=4 → 872
(= Egan−1, the 141/3 census of all 296 records), K=8 → **871 = world record**,
K=24 → 867 (the grammar floor lands exactly on the proven lower bound). Cross-n:
K=5 at n=7 → 5907 (exactly the urdvr words); perfect K=20 → 5904, and the actual
5906 is that certificate paying 2 chars of concessions — so **large kernel chains
provably exist at n=7**, and even repairing the 5906's five incomplete groups
would beat the record. Every relaxation (mixed-cost hop, partial ride) is priced
in the ledger; search never leaves proof-grade waste accounting.

**Execution plan (in the design note, each step with go/no-go):**
1. `src/cert.rs`: marked loop / oriented row / kernel-parameterized certificate +
   generalized W1–W7 checker + walk compiler. Gate: 296/296 records round-trip as
   K=4 certificates; the three 5907s parse at n=7; ledger machine-verified.
2. Kernel-chain search: enumerate the T3(p)=T2(q) pair relation on the 144 marked
   loops; DFS for K=8 orbit-disjoint chains. **This is the whole game at n=6** — a
   finite, fully checkable existence question nobody has answered.
3. Rooted-cover DLX over surviving kernels (adapt urdvr's Python `build_instance`
   first — the compiler is already generic; Rust port only if the probe lives).
   Any cover ⇒ compile ⇒ validate ⇒ 871.
4. Only if dry: priced relaxations (partial rides, mixed-cost hops), and the n=7
   K=20 attack seeded from the 5906's own extracted kernel.

Anti-goal carried forward (s8): no static rewarding of row-like shapes in
move-level beams — this searches the certificate space directly.

**Next session: step 1 (`src/cert.rs`) and step 2 (the K=8 chain question).** If
step 2 answers "no chain exists at cost 3", the ledger immediately prices the
fallbacks; if "yes", step 3 is a bounded DLX run from a known-good codebase.

## 2026-07-27 (session 9) — item 4 executed: exact endgame tablebase built; metric met, but the endgame door is proven shut (873/874/5913 all locked before the last 25 perms; every known record's tail is optimal)

Single thread this session: build ROADMAP item 4 end-to-end, then use it to convert
the standing "endgame is already solved" belief into theorems.

**Built (commit `cf257b9`).** `src/endgame.rs`: Held–Karp DP over
`(subset of remaining, last perm)` — `solve_endgame(g, cur, remaining)` returns the
provably minimal completion cost plus a witness order. Exactness is not heuristic:
the overlap distance satisfies the triangle inequality, so passing through visited
perms never helps and the optimal completion is exactly the optimal Hamiltonian path
on the remaining set (proof sketch in the module docs — every verdict below is a
theorem). `u16` table, `2^m·m` entries; practical ceiling `MAX_REMAINING = 25`
(~1.7 GB, ~7 s); m=20 is 40 MB / ~0.12 s. Two integrations: (1) `beam --endgame m
--endgame-top K` snapshots the top-K frontier states at r=m (pure instrumentation —
search bit-identical, pinned by test), exact-solves each post-hoc, and maps final
beam states back to their snapshot ancestors so each state's exact total is compared
against *its own* beam completion (the ROADMAP metric, measured per state); prints
the improved validated string if any exact total beats the beam. (2) `endgame`
subcommand: exact-complete a prefix of greedy or any traced string. Tests: brute-force
oracle (suffix + arbitrary sets), full n=4 solve from identity **= 33 exactly** (the
proven optimum, now an internal consistency theorem), greedy-n=5-prefix + exact
endgame = 153 with validation, snapshot purity + dominance (exact ≤ own descendant,
≥ global optimum). 81 tests green, clippy/fmt clean.

**Frontier experiments — metric MET, top never moves.** Config = the canonical
stratified 873 (boot1 α=1, w2000, quota 4, bucket 1) unless noted:

| run | best exact total | exact beats own descendant | beats beam result |
|---|---|---|---|
| n=6 strat, m=20, top=2000 (full frontier) | **873** (rank #0) | 7/2000 (max gain 3) | 0 |
| n=6 strat, m=24, top=64 | 873 (rank #0) | 4/64 (max 3) | 0 |
| n=6 unstrat boot1 (874 plateau), m=20, top=2000 | **874** (rank #0) | 11/2000 (max 4) | 0 |
| n=7 strat transfer (5913), m=20, top=200 | **5913** (rank #0) | 8/200 (max 4) | 0 |
| n=5 cycle-bound w2000, m=15, top=50 | 154* | 4/50 (max 4) | 0 |

(*n=5: the eventual 153-winner's ancestor sat below score-rank 64 at r=15 — top-64
missed it; top=width captures it, integration test pins this.) The go/no-go metric
("any frontier state whose exact endgame beats the heuristic one by ≥ 1 char") is
formally met at every n — but the gains live mid-frontier on states with no winning
future; the score-rank-0 state's heuristic completion was *already optimal* in every
single configuration.

**Theorems (the session's real product).**
1. **The stratified config's entire width-2000 frontier at r=20 completes to
   ≥ 873** — no endgame play of any kind reaches 872 from this beam; the record is
   lost before level 700.
2. **The unstratified boot1 frontier at r=20 completes to ≥ 874** — the
   873-vs-874 stratification difference is decided strictly before r=20.
3. **Optimal tails everywhere**: greedy's 873, the stratified 873, the seeded 873,
   and the record 872 all have provably optimal last-**25** tails (m=25 at the RAM
   ceiling; exact saves 0). s6's "no endgame deviation from greedy's basin ever
   saves a character" is now theorem-grade at 25-from-end.
4. **All 296 known 872s** (100 community + 196 gain1) have optimal last-20 tails —
   no known record hides a sub-872 completion (the free-world-record lottery ticket
   came up empty, exhaustively).
5. **All three urdvr n=7 5907s** have optimal last-22 tails — same story one size up.

**Reading.** Item 4 is done as a *finding* mechanism and the answer is a clean
negative-with-teeth: s5's "the endgame is already solved" is now proven, uniformly,
at n=5/6/7, for our walks and for every known record. Everything that separates 873
from 872 happens in the opening/midgame — exactly where s8 put it. The tablebase's
lasting value is as **infrastructure**: item 5's cycle-level searcher should call it
as a terminal solver (once ≤ ~20 perms remain, finish provably optimally — the last
~20 plies of any future search are free and exact), and any "nothing beats X from
this state" claim below m=25 is now one CLI call. If theorem depth beyond 25 is ever
needed, a DFS branch-and-bound completion prover (arc bound, no 2^m table) is the
natural extension — noted, not built.

**Next session (item 5, the big build — all steering weight now here):**
- Cycle-level (super-node) move space over the 120 rotation cycles; the 2-cycle
  weave as a *move* (s8: statically rewarding the shape is exploitable), kernel as a
  *parameter* (Robin: sub-Egan−1 lives outside the standard kernel; at n=6, Egan−1 =
  872 IS the record, so a closing nonstandard-kernel word is a world record).
- Start from the urdvr certificate machinery (W1–W7 checks, trade vocabulary, DLX
  exact cover) + our learned ordering; anytime DFS with the admissible waste-budget
  test (budget 147), endgame tablebase as terminal solver.
- Cheap first step: formalize the cycle-graph state (which cycles entered/left where,
  live w2 bridges) and enumerate legal weave-moves from a mid-walk record state — the
  move vocabulary falls out of tracing the 298 872s at the cycle level.

## 2026-07-27 (session 8) — item 3 executed: deficit features carry the expert signal, but no linear/MLP evaluator converts it (873 stands); n=7 from-scratch baseline 5913; field news (Robin: kernels; Theo: paint-waste)

Three threads again: n=7 probe, feature implementation, training/evaluation campaign.
Item 3's verdict is a clean partial: **the features work, the evaluator class is the
ceiling.** No sub-873; steering weight moves to items 4–5.

**Features landed (commit `ead4c8a`).** `half_open` (cycles with 1–2 visited) and
`nearly_done` (1–2 unvisited) now in `Walk` + JSONL; new **`w2_bridges`** = count of
unvisited cross-cycle weight-2 edges joining two partially-visited cycles (each perm
has exactly one cross-cycle w2 successor `P[2..]+P[1]+P[0]` — a bijection — so the
count is O(1)-amortized incremental via `Graph::w2_bridges_delta`, shared by Walk,
beam, and guided rollouts). Model contract is append-only length-dispatched:
`FEATURE_ORDER` (8) vs `FEATURE_ORDER_V2` (11); old models score bit-identically
(pinned to the exact bit pattern; stratified 873 reproduces byte-identical). beam2
skips the new features by design (documented NO-GO probe). 76 tests green. **The
feature does what the s5 autopsy demanded**: tracing a record vs our stratified 873,
midgame (steps 250–450) mean `w2_bridges` is 1.9 (max 7) vs **identically 0.0** on
every greedy-shaped walk; `half_open` 3.3 vs 0.3.

**Expert corpus tripled (prep for the campaign).** urdvr's `gain1.py search` is a
0.09 s/word mass generator: 200 seeds → 198 distinct 872s, **196 new** vs the known
corpus → `data/gain1_872s/` (gitignored). ("New" = byte-distinct; equivalence-class
status under relabel/reverse symmetry unchecked — urdvr's `equiv_check.py` can
classify if it ever matters. And to be explicit: these are *generated* by urdvr's
construction, not found by our search — our search floor remains 873.) With records872 + the 2 urdvr words: **298
distinct 872s**. Chaffin per-waste optimal prefixes downloaded to `data/chaffin/`
(599 files incl. all `Chaffin_6_W_<w>` exhaustive lists; unused this session —
`trace` requires complete strings — kept for a future prefix loader). Traced corpus:
596 expert trajectories (298 + 298 reverse-**and-relabel**; plain reversal doesn't
start at identity, so relabeling is mandatory), 429k rows, plus fresh v2 rollout/
trajectory corpora. **Trap documented: all pre-`ead4c8a` JSONL (including the
misleadingly named `boot_n6_elite925_v2.jsonl`) has the new fields zero-defaulted —
never train the new features on it.**

**Campaign (commit `a68d068`: `ml/fit_rank.py` + `beam --allow-n-mismatch`): NO-GO
on sub-873, with sharp structure.** 10 models × α × quota × width, 186 validated n=6
runs:

- **Best overall: 873, only from boot1 ⊕ β·rank pre-blends (β 0.05–1) — and every
  one is byte-identical to `data/result_stratified_873.txt`.** The rank direction
  never flips a single boot1 decision at any surviving β, any width to 32000: the
  873→872 gap is unreachable by *any reweighting in this feature basis* (extends
  s6's conclusion from 8 features to 11).
- **Population-contrast training is exploitable** — the session's most important
  negative mechanism: scorers trained to separate expert from background states turn
  `w2_bridges`/`half_open` into a classifier, and the beam then *manufactures*
  bridge-rich junk with no record future (expert+rollout OLS mix: 1765; pure
  rankers: fail the n=5 gate at every α, and their beams collapse record survival
  719→264 because junk out-ranks records on the ranker's own scale). Credit for
  structure must be conditional on being able to use it — a static linear map can't
  express that.
- **The anchored (residual) ranker is the honest signal-carrier**: pairwise ranker
  on `cost_to_go − lb_arc` (RankNet-style logistic loss, 89.8% held-out pair
  accuracy; standardized `w2_bridges` coef −3.33 = strongest expert discriminator)
  is the best standalone expert-informed scorer (888 @ w2000, beats arc's 891) and
  produces the **first-ever nonzero midgame rank-wins** (records winning the
  stratified window at 10/484 levels 118–601, vs 0 for boot1 and all blends). The
  features are real; linear/MLP over them is the ceiling.
- n=5 gate lesson: it screens *breakage*, not *poison* (expmix passed the gate at
  all α, then beamed 1765 at n=6).

**n=7 from-scratch baseline established: 5913, stratified learned beam — the n=6
story reproduces one size up.** Hand bounds are terrible (cycle 6180, arc 6130 @
w2000 — far worse than greedy, unlike n=6); the n=6-trained boot1 model transfers
with zero retraining (5970); stratification (quota 4 or 8) closes exactly to
**5913** at w2000 (~5.5 min) and w8000 (~21 min, same string) — a distinct string
from greedy's with the *identical* weight histogram (4320/600/96/18/4/1). Quota
response shifts (quota 1, a winner at n=6, gives 5961). The rank-blend transfers no
improvement (5913). Bar to beat: **5907** (urdvr words). `--allow-n-mismatch` now
enables cross-n model runs.

**Field news (documented in `../extraDocs/2026-07-27-urdvr-email-and-repo.md`).**
(1) **Robin's reply**: proving indefinite lifting would give the long-conjectured
Egan−1 upper bound; and — the actionable half — the gain-one machinery should be
adapted to **nonstandard kernels**, "as we were able to do for n=7" (the 5906).
Independent confirmation of our s7 boundary note: sub-Egan−1 means leaving the
standard-kernel move space, and item 5's cycle-level design must *parameterize the
kernel*. At n=6, Egan−1 = 872 IS the record, so any closing nonstandard-kernel word
there is a world record. (2) **Theo H.**: claims (opinion, no mechanism) that even
the 5906's nonstandard-kernel savings lift indefinitely — filed as
conjecture-on-conjecture; posted `paint_waste.cpp` (archived + compiled at
`../extraDocs/theo-paint-waste/`, copyleft): an analyzer emitting
`[clean_run_length:source_index]` pairs per waste symbol — his dirty-window counts
match our waste accounting exactly (record 872: 147 waste, max dirty run 2).

**Next session (item 4, with item 5's design brief sharpened):**
- **Exact endgame tablebase** (ROADMAP item 4): DP over (remaining subset, cur) for
  ≤ ~25–30 remaining perms; bolt onto beam/stratified frontier states. Metric: any
  frontier state whose exact endgame beats the heuristic one by ≥ 1 char. Also turns
  "nothing beats 873 from greedy's basin" claims into theorems.
- **Item 5 design note (from this session + Robin)**: cycle-level move space must
  (a) make the 2-cycle weave a *move*, not a feature to reward — the campaign proved
  rewarding the shape statically is exploitable; (b) parameterize the kernel. The
  urdvr certificate machinery (W1–W7 checks, trade vocabulary) is the starting
  formalization; its DLX search + our learned ordering is the unplayed combination.
- Cheap follow-ups: rank-corpus prefix loader for Chaffin positives (if item 4/5
  need an opening prior); n=7 expert trace (the three 5907s) once any n=7-aware
  scorer exists.

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
