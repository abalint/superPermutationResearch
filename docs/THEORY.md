# Theory & framing

This file records the intellectual framing behind the project so a future session (human
or AI) can pick up the thread without re-deriving it.

## 1. The problem as graph search

A superpermutation on `n` symbols contains all `n!` permutations as substrings. Build a
directed graph:

- **Node** = one permutation of `{1..n}`.
- **Edge weight** `w(P → Q)` = the number of characters you must append to `P` so that
  `Q` appears = `n − overlap(P, Q)`, where overlap is the longest suffix of `P` that is a
  prefix of `Q`.

A superpermutation is a walk that visits every node; its length is
`n + Σ edge weights`. Finding the minimal superpermutation is essentially a shortest
Hamiltonian path — the **asymmetric traveling salesman problem** on this graph. This is
not just an analogy: Houston's 872 for n=6 came from feeding exactly this graph to an
ATSP heuristic (LKH).

Greedy search (always take the max-overlap successor, lexicographic tie-break) produces
the classic palindromic construction with length `Σ_{k=1..n} k!` — 9, 33, 153, 873. The
existence of 872 proves greedy is not optimal from n=6 on: sometimes a locally expensive
edge buys a globally shorter walk. That is why this is a *search* problem.

## 2. The 1-cycle structure (why search is tractable at all)

The weight-1 edge out of `P` is unique: the left-rotation `P[1..] + P[0]`. Rotations
partition the `n!` permutations into `(n−1)!` **1-cycles** of size `n`. Collapsing each
cycle to a super-node turns the search into "in what order do I visit cycles, and where
do I enter/leave each one" using weight-2/3 edges — a massive reduction in depth and
branching factor. Egan's n=7 record and the community "kernel" searches operate at this
level. Our beam search tracks per-cycle remaining counts for exactly this reason.

## 3. The admissible lower bound (phase-1 pruning)

For a partial walk with `r` unvisited permutations spread over `k` cycles that still
contain unvisited members:

```
lb = r + k − (1 if the current permutation's cycle still has unvisited members else 0)
```

Every remaining permutation costs ≥ 1 appended character; every cycle other than
(possibly) the current one must be *entered* via an edge of weight ≥ 2, i.e. ≥ 1 extra
character. This is the same style of reasoning as the published
`n! + (n−1)! + (n−2)! + n − 3` lower bound, weakened to O(1) incremental maintenance.
Beam states are scored by `length_so_far + lb`.

## 4. The phase-2 bet: a learned value function over the residual graph

Hand-derived bounds (waste tracking, cycle counting) are provably correct but blind to
non-local structure — they cannot express "this region of remaining cycles is awkwardly
connected and will force expensive weight-3 hops in 300 moves."

The plan: replace/augment `lb` with a **learned cost-to-go regressor** whose input is
*not* the raw visited bitmask (720–5040 bits, zero cross-size generalization, forces
memorization of permutation IDs) but **features of the residual graph** — the subgraph of
unvisited permutations:

- count / fraction of fully-intact cycles vs. partially-eaten ones
- degree statistics of the residual cycle graph (cheap exits still available per cycle)
- number of connected components under cheap edges (each extra component ≈ a future toll)
- distance from the current position to the nearest untouched region

These are permutation-ID-agnostic and (after size-normalization) mostly n-agnostic. The
transfer story: train on n=5 where labeled data is nearly free (optimum known, exhaustive
generation cheap), use as a warm start, then fine-tune AlphaZero-style at n=6/7
(search with current net → label states with observed outcomes → retrain → repeat).

Training signal (already implemented in phase 1): epsilon-greedy rollouts log
`(features, cost_to_go)` pairs per visited state to JSONL — standard supervised
regression data.

### Honest scaling assessment

- **Distribution shift is real.** n=6 is the first n where greedy stops being optimal —
  each n can exhibit structure the previous n never showed. Zero-shot transfer is not
  the claim; faster bootstrap convergence is.
- **The exponent wins eventually.** A perfect oracle evaluator still walks a factorially
  deep space. Realistic hunting grounds: n=6 (872 vs. lower bound 867 — 5 chars of gap)
  and n=7 (5906 vs. 5884 — 22 chars). n=8 was long assumed to be construction-only
  territory, but the July 2026 46204 result (see §6) shows structured, cycle-level
  approaches can shave Egan's formula even there — raw permutation-level beam search at
  n=8 remains out of reach, though.
- **Eval cost is the real bar.** The evaluator runs at every node expansion. If it is
  100× slower than a waste counter it must prune >100× better to win on wall-clock.
  Features must be maintained incrementally; the net must be small and batch-evaluated.

## 5. Chess-engine analogy — what carries over and what doesn't

| Chess engine concept | Here |
|---|---|
| Evaluation function | cost-to-go lower bound / learned regressor |
| Selective search, candidate moves | cycle-level moves, weight-ordered successors |
| Alpha-beta | **does not apply** (no adversary); the analogs are beam search, A*, branch-and-bound |
| AlphaZero self-play loop | rollout → label → retrain bootstrap at target n |
| Transposition table | mostly useless: state = (position, visited-set), collisions are rare |
| ~80-ply games | n! -step "games" (720 at n=6) — value error compounds much harder |

## 6. Facts worth not re-deriving

- Proven minima: 1, 3, 9, 33, 153 (n=1..5). 153 proven by exhaustive distributed search
  (Chaffin method).
- Best known: 872 (n=6, Houston 2014), 5906 (n=7, Egan 2019), 46204 (n=8, Raudvere,
  July 2026 — verified by Houston et al. on the Superpermutators group).
- General lower bound: `n! + (n−1)! + (n−2)! + n − 3` → 867 (n=6), 5884 (n=7).
- General upper bound: `n! + (n−1)! + (n−2)! + (n−3)! + n − 3` (Egan) → 46205 (n=8) —
  now beaten by 1 at n=8, and reportedly at n=9 (408,965) and n=10 (4,037,046) too
  (Echols, July 2026; independently checked, write-up pending).
- **Structure of the 46204:** Houston's analysis — a *tree-like* superpermutation:
  standard kernel (principal 3-cycle) plus 833 two-cycle extensions, each contributing
  6 new 1-cycles. This is exactly the cycle-level tree representation planned for
  phase 3, and strengthens the conjecture that tree-like superpermutations below
  Egan's bound exist for all n. Local copies of the announcement thread and Houston's
  extension tree live outside this repo in `../extraDocs/`.
- A found superpermutation is **self-certifying** — validation is a linear scan. Records
  require no trust in the search that produced them.
- **Loop-count relation (s35 corpus law → s39 THEOREM, §7 below):** for EVERY pure
  (intra-free) complete walk, `L ≤ S + #doors − ((n−1)! − 1)` — equivalently
  `length ≥ n! + (n−1)! + (n−3) + Λ` with `Λ = L + Σ_{w≥4}(w−3)·inter[w]` — with a
  structural characterization of equality (§7). The corpus-law EQUALITY form
  (verified exceptionless on 22,062 n=6 872s, 4 off-shell 873s, all 87 known n=7
  walks, Egan's 5908, and — via the s38 tripwire — 7,321,635 recomp2 re-solves) says
  every known record and near-record is a TIGHT LOOP COVER (§7's deficit = 0). One
  char = one Λ-unit on the tight shell: an 871 is a Λ=28 object (in general
  Λ + deficit = 28, so Λ ≤ 28), a 5905 is Λ ≤ 141. s37 showed the I3 tier T4 is
  tautological as a PRUNE (on the tight shell Λ-neutral = length-neutral), so it runs
  as a tripwire assertion; after §7, a tripwire "violation" on a found walk means a
  deficit>0 (structurally slack) walk — remarkable and worth the banner, but not a
  solver bug.

## 7. The loop-count theorem (s39 — proven, with equality characterization)

Setting: a complete first-visit walk over all `n!` permutations with NO intra-cycle
edges of weight ≥ 2 (every corpus walk qualifies). Notation: `S` sojourns,
`splits = S − (n−1)!`, `D` inter edges of weight ≥ 3 ("doors"), `W = S − 1 − D` w2
edges. The **2-loop** of a permutation `p` is its orbit under
`g(q) = q₂…q_{n−1} q₁ q_n` (orbit size `n−1`; `n!/(n−1)` loops; equivalently: the
parked last symbol plus the cyclic order of the rest). `L` = number of distinct
2-loops over the walk's w2 edges, `Λ = L + Σ_{w≥4}(w−3)·inter[w]`.

**Structural lemmas** (each verified exactly on record corpora by
`analysis/counting/loop_ledger_probe.py`, modes `walk`/`random`):

- **L1 (arcs).** The sojourns of a 1-cycle partition its `n` perms into contiguous
  cyclic intervals, and `rot(exit of an arc) = entry of the spatially-next arc`.
  (First-visit + completeness + w1 = rotation.)
- **L2 (loop readability).** The unique inter-w2 edge out of `a` lands on
  `g(rot(a))`, and its 2-loop equals the g-orbit of its LANDING perm. Hence the w2
  edge into an entry `v` is the loop-space edge `g⁻¹(v) → v`, and the w2 edge
  departing past `v`'s cycle-neighbour is `v → g(v)`: each loop's potential w2 edges
  form a directed (n−1)-cycle, and `v → g(v)` is used iff the arc spatially before
  `v` departs by w2.
- **L3 (coherence).** A full-cycle arc (its cycle has one sojourn) entered by w2 and
  exited by w2 continues the SAME loop; a split-cycle arc always switches loops
  (the n perms of a cycle lie on n distinct loops).

**Theorem.** For every pure complete walk:

    L  ≤  splits + D + 1,   equivalently   length  ≥  n! + (n−1)! + (n−3) + Λ,

and the deficit decomposes into two independently non-negative terms:

    deficit := (splits + D + 1) − L = (splits − Φ) + ((D+1) − P),

where `Φ` = fully-used loops (all n−1 edges used) and `P = L − Φ` = partially-used
loops.

**Proof.** (i) `Φ ≤ splits`: in the multigraph `G₂` on the `(n−1)!` 1-cycles whose
edges are the walk's W w2 edges, each fully-used loop is a closed cycle through its
n−1 distinct 1-cycles (L2), and distinct loops are edge-disjoint, hence linearly
independent in the cycle space: `Φ ≤ dim = W − (n−1)! + C` with `C` = components of
`G₂`. Adding the D door edges makes the transition graph connected (the walk is),
so `C ≤ D + 1`; substituting `W = S − 1 − D` gives `Φ ≤ splits`. (ii) `P ≤ D + 1`:
a partially-used loop's used edges form maximal chains on its (n−1)-cycle; each
chain's last edge `u → v` has its successor `v → g(v)` unused, which by L2 means
the arc spatially before `v` departs by a DOOR or is the walk's final arc. That arc
is unique per chain-end and each door/end serves exactly one entry (`v = rot` of
its exit), so chain-ends — hence partial loops — inject into the D doors plus the
walk end. ∎

**Equality (the tight-loop-cover class).** `deficit = 0` iff (a) every door bridges
two w2-components (`C = D + 1` exactly — the doors form a bridge-forest gluing the
w2-graph) and the cycle space of `G₂` is spanned by the fully-ridden 2-loops
(`Φ = splits`: no accidental cycles), and (b) there are exactly `D + 1` partial
loops, each a SINGLE chain, one terminated at each door and one at the walk's end.
**Every known record-shell walk is tight**: all 22,062 n=6 872s, all 87 known n=7
walks (both checked term-by-term), the four loose 873s/5907s/5908, and all 7.3M s38
recomp2 re-solves (via the tripwire). **s56 correction: NOT every off-shell 873 —
46 of the 448 `data/lift873_n6/` REV-w4 lift walks are slack (deficit=1, j=0,
v−L=1, all length 873), the first slack n=6 walks ever identified in-corpus.
"Slack has never been observed" is true only AT or BELOW record length.** Random
complete n=4 walks: deficit ≥ 0 in
11,400+ samples (5,400+ of them pure; both terms individually ≥ 0 on every pure
walk checked), ~5–8% tight. A legal walk CAN be
slack (e.g. at n=3: ride cycle 1, w3-door to cycle 2, ride it — L=0, deficit=2),
so the corpus's exceptionless tightness is a strong structure theorem for how
records are built: **a record is a tight loop cover — Φ = splits fully-ridden
2-loops spanning the w2 cycle space, glued by a bridge-forest of doors, plus D+1
door-terminated single chains.**

**Consequences.**
- The hunt targets restate as: an 871 satisfies `Λ + deficit = 28`, a 5905
  `Λ + deficit = 141` — and since deficit ≥ 0, `Λ ≤ 28` (resp. 141): one char
  below record means one fewer Λ-unit OR one unit of structural slack.
- The I3 Λ-tripwire asserts tightness, not consistency: a "violation" on a found
  walk is a deficit>0 walk (legal, structurally slack, never yet observed at
  record length) — banner-worthy, not a solver bug.
- **The loop cover is a near-perfect class invariant (s39 census,
  `loop_ledger_probe.py cover`):** 22,062 n=6 classes → 22,050 distinct covers;
  the ONLY collisions are 12 cross-allocation pairs sitting exactly on the natural
  edit boundaries — 8× (145,3)↔(143,5) (the compound-crossing type; s36's
  controlled-pair method had found 2) and 4× (143,5)↔(142,6) (the unit-trade
  type). At n=7: 84 classes → 83 covers, and the single collision is
  **(844,17) `a30c7c517d7b` ↔ (843,18) Kristan** — the Kristan seam, absent from
  every anchored sweep, EXISTS as a cover-preserving global reordering. Only 120
  of the 144 loops (canonical frame) are ever used by any known 872; 4 loops
  appear in every cover.

**s56 additions (the slack-tax / j-tax frame; instrumentation in
`loop_ledger_probe.py` modes `slack`/`hunt`/`exhaust`, artifacts
`out/s56/slacktax/`).** Write `v` = # distinct ENTERED marked loops,
`j = splits + D + 1 − v`. **s62 CORRECTION: this block originally used one
symbol `x` for two different quantities.** The two are `xp := Σ_doors(w−3)`
(the door overweight) and `v − L ≥ 0`; they coincide only when
`deficit = j`. Counterexample in-corpus: specimen `872.up-022441b7b1ff`
(allocation (140,6,1,0,0)) has `v−L = 0` but `xp = 1`, so
`843+v+j+(v−L) = 871 ≠ 872`. The correct pair of statements is the identity
below (with `xp`) AND `deficit = j + (v − L)` (the s55 Gheorghe-dictionary
bridge). Then, for every pure complete first-visit walk:

- **Exact length identity:** `length = n! + (n−1)! + (n−3) + v + j + xp`
  (verified per-walk on all 22,062 + 87 + 755 local corpus walks and on
  exhaustive n=3/4 enumerations; re-verified with the corrected `xp`
  reading on 22,062 + 448 + 87 + 10 walks in s62, 0 violations).
  Each unit of j costs exactly +1 char. The identity is a definition-chase
  from purity + completeness + first-visit alone (s62 §2.1) — it does not
  use the loop-count theorem.
- **Loop-supply bound:** `v ≥ ((n−1)! + splits)/(n−1)` (a 2-loop has n−1
  perms, so supplies ≤ n−1 arc starts) — Gheorghe's T3 `s ≤ 5l` rederived
  on our side. Combining: `length ≥ n! + (n−1)! + (n−2)! + (n−3) + j + xp +
  splits/(n−1)` — the classical bound's slack IS `j + xp + splits/(n−1)`.
  At n=6 this proves `j ≥ 1 ⇒ length ≥ 868` (4 short of the 872 target).
  **s62 sharpening — take the ceiling (MASTER):**
  `length ≥ n! + (n−1)! + (n−3) + ⌈S/(n−1)⌉ + j + xp`, since the supply
  lemma's underlying fact is exact: the n−1 perms of a 2-loop lie in n−1
  DISTINCT 1-cycles (a loop parks the last symbol; two perms of one cycle
  cannot share a last symbol), so `S ≤ (n−1)·v` in integers. At n=6:
  `length ≥ 867 + ⌈splits/5⌉ + j + xp`; at n=7:
  `length ≥ 5884 + ⌈splits/6⌉ + j + xp`. Verified on 22,062 + 448 + 87 + 10
  corpus walks and exhaustive n=3/4, 0 violations; exactly TIGHT on
  22,052/22,062 n=6 records (`out/s62/jtax/verify_master.py`).
- **Ledger inequality:** `(n−2)L ≥ (n−1)! − 1 − D`; at n=6,
  `4·splits + 5·D ≥ 115 + 4·deficit` (tight on 3/8 allocation specimens).
  At length 871: `D ≥ 7 + 4x + 4·deficit` — a slack 871 needs ≥ 11 doors
  (corpus max: 11), a deficit-2 871 needs ≥ 15.
- **Per-edge door law (exceptionless, 68,999 doors / 3.1M inter-w2 edges
  over all 22,062; same at n=7):** with `dc` = "edge closes its departing
  1-cycle", `dv` = "edge enters a fresh 2-loop": every w≥3 door has BOTH,
  every inter-w2 edge has EXACTLY ONE. This is j=0 in per-edge form — a
  second door law beside s27's landing-cycle law — and gives a refutation
  engine a per-edge test to enforce `j = 0` (equivalently, to price j ≥ 1).
- **Materialized species (firsts):** slack n=6 walks exist in-corpus (the
  46 lift873 walks above); the first j ≥ 1 n=6 walk ever materialized is
  `out/s56/slacktax/witness/n6_j2_874.txt` (874, j=2: exactly two doors
  with dv=0 — the predicted "re-entered loop with a spent door").
  Exhaustive tail re-completion (cap 873, last 160 perms, all 8
  allocation representatives, 71.3M nodes, 0 aborts) finds NO j≥1 walk
  ≤ 873 — a local negative only. Tax ladder: n=3 slack-tax 1 / j-tax 3
  (exhaustive); n=4 both 1 (exhaustive); n=5 slack-tax 1 exhaustive at
  cap 153, j-tax 1..2; n=6 observed slack min 873, j≥1 min 874.
- **The O5 discharge target reframes as the j-tax:** all 22 O5-held cells
  need j ≥ 1 (deficit ≥ 1 is weaker — deficit-1/j=0 873s exist one char
  above record, so a "deficit tax to 872" is false-adjacent). Their cell
  arithmetic forces D ∈ [19,26] and splits ≤ 8 — the opposite ledger
  corner from every known walk. `j ≥ 1 ⇒ length ≥ 872` remains OPEN
  (proved floor: 868; **s62: raised to 869**, see below).

**s62 additions (the MASTER rungs and the perfect-ride family;
artifacts `out/s62/jtax/`, report there).** All statements are for pure
complete first-visit walks.

- **Conditional rungs (corollary of MASTER at n=6):** `j ≥ 1 ⇒ length ≥
  868 + ⌈splits/5⌉ + xp`, so splits ≥ 1 (or xp ≥ 1) ⇒ ≥ 869; splits ≥ 6 ⇒
  ≥ 870; splits ≥ 11 ⇒ ≥ 871; **splits ≥ 16 (S ≥ 136) ⇒ ≥ 872**. The whole
  868→872 j-gap therefore lives at splits ≤ 15 — below every known 872
  allocation except (135,9,2,0,0), which sits exactly on the boundary. In
  particular tail re-completion from record prefixes (splits 25) can never
  probe the live cells: the record classes are excluded ≤ 871 for free.
- **Rung 869 (unconditional): `j ≥ 1 ⇒ length ≥ 869` at n=6.** Proof: MASTER
  forces the single surviving cell (v=24, j=1, xp=0, splits=0, D=24, len
  868); splits=0 + supply-tightness (S = 5v = 120) makes every entered loop
  supply all 5 of its perms as arc-starts, so the 24 loops EXACTLY COVER the
  120 one-cycles and every cycle's arc-start is determined by the cover (the
  perfect-ride rigidity); the resulting family is finitely enumerable
  (10,068 exact covers at n=6; 1,678 containing λ(123456) after relabeling
  WLOG) and `cover_search.py 6 868 --jmin 1` exhausts it: 36,304,934 nodes,
  NO walk (also none at jmin 0 — 867 is unreachable in-family, consistent
  with a(6)=872). Positive controls: the same engine re-derives a(4)=33 and
  a(5)=153 as its in-family j=0 minima.
- **Where the mechanism provably stops:** at length 869 six of the eight
  j≥1 cells have v=25 (loop-supply slack 5), where the cover no longer
  determines arc-starts and the rigidity evaporates; the two v=24 cells at
  869 are killed exhaustively (1.06e9 nodes). Rung 870 is NOT proven. And
  **none of the 22 O5 cells is supply-tight** (slacks 1–14,
  `o5_crosscheck.py`), so this composition has zero reach into the O5
  discharge at any budget — any rung above 869 must price loop-supply
  SLACK (entered-loop perms that are not arc-starts).
- **Cell universe (identity + supply only, `cells62.py`; independently
  matches s56's `cell_squeeze.py` 60/115 from a different frame):** j≥1
  cells by length: 868→1, 869→8, 870→26, 871→60, 872→115. Of the 115 at
  872, EXACTLY ONE lies in a known allocation: (140,8,0,0,0) with
  splits=20, D=8, v=28 — and it is supply-tight, i.e. a j=1 872 there must
  be a 28-loop multi-cover of the 120 cycles with all 140 incidences
  supplying. Rigid, enumerable, the best-shaped remaining target.
- **n=5 j-tax DECIDED = 1** (was {1,2}): explicit witness
  `out/s62/jtax/witness/n5_j1_154.txt` (154, j=1, validator-green,
  probe-confirmed, itself a perfect-ride walk), lower bound from s56's
  cap-153 exhaustive. Tax ladder: n=3→3, n=4→1, n=5→1 (all exact),
  n=6 ≥ 1 with observed min 874. The ladder does NOT grow with n.
- **n=7 transfer:** `length = 5764 + v + j + xp` (the s34 law
  `length = 5764 + #2loops` is its j=0 shadow; a 5905 is `v+j+xp = 141`),
  and MASTER gives `length ≥ 5884 + ⌈splits/6⌉ + j + xp` (verified on all
  87; tight on 3). Priced rule: **`j ≥ 1 ∧ S ≥ 841 ⇒ length ≥ 5906`** — so
  any 5905 with S ≥ 841 has j = 0 and the per-edge door law becomes a HARD
  constraint there (the known 5906s sit at S ∈ {838,840,843,844}; the
  (844,17) family and Kristan's (843,18) qualify). A j≥1 5905 needs
  v ≤ 140, S ≤ 840, D ≥ 20.
