# Residual-graph admissible lower bound ("Bound-1 localized") — design

Status: opened session 19 (2026-07-28), after the urdvr/Hunter Lean LB landed
(S(6) ≥ 869; see `../extraDocs/2026-07-28-urdvr-lean-lower-bound.md`, clone at
`../extraDocs/superpermutations-hunter`, paper `paper/hunter_bound.tex`).
Goal: an admissible lower bound B(state) on the cost of completing a partial
walk (state = cur + visited set), strong enough to close the gap between our
current root valuation (~840 at n=6) and the Hunter-style valuation (~869).
Uses: beam pruning (`len + B > target` ⇒ provably dead), future
branch-and-bound, and the certified floor under any learned evaluator
(evaluator = B + learned residual ⇒ exploit-proof below the floor).

## STATUS — session 19 implementation (2026-07-28)

**Landed:** `src/lb_residual.rs`, `--bound residual` on `beam`/`trace`,
maintained in `Walk::advance` **and** the beam's `State`/`score_move`
(beam2 untouched). Default paths unchanged; the canonical stratified
learned-model n=6 run still returns **873**.

| Tier | Claim | Verdict |
|---|---|---|
| 1 — exact residual class accounting | `r + arcs − [succ1(cur) ∈ R]` | **Landed, and proved *optimal*** (§B): the existing arc bound is exactly the best bound obtainable from per-class accounting. Parity with today's bound is a theorem, not a coincidence — no intra-class refinement can beat it. |
| 2 — door structure | `+ door + intact + long` (§C) | **Landed and proven** — a residual-local door argument giving ≥3-cost and ≥4-cost entries. Uplift over the arc bound: **+1.8** chars at depth 200 (n=6), **+4.0** at 400, **+5.6** at 550, **+9.4** at 650. |
| 2 — the `(n−2)!` / `q_k` terms | root ≥ 860 at n=6 | **NOT proven, and the obstruction is identified** (§D). Both routes are dead residual-locally; the root value stays 838 at every tier. |
| 3 — non-admissible floor | `heuristic_floor_not_admissible` | Landed, **ordering only**, wired into nothing. Measured to exceed the exact truth on 252/5200 (n=5) and 27/5200 (n=6) GA samples, i.e. it *is* inadmissible — kept for experiments only. |

**Gates** (all run 2026-07-28; harness `tests/residual_bound.rs`, run with
`cargo test --release --test residual_bound -- --ignored --nocapture --test-threads=1`):

* **GA** 10,400 sampled states (5,200 each at n=5, n=6; greedy/beam prefixes
  at random depths + randomized ε-suffixes, tails m ∈ 2..18), truth from the
  exact endgame tablebase: **0 violations**. Slack n=5 min 0 / median 3 /
  mean 2.75 / max 11; n=6 min 0 / median 6 / mean 7.17 / max 25. Plus a
  large-m tail (m = 20, 22, 24, 25 at both n): 16 samples, **0 violations**,
  slack 2–18. `min = 0` = the bound is exactly tight on some states.
* **GB** root values are identical for all three tiers — cycle = arc =
  residual = **142 (n=5) / 838 (n=6) / 5758 (n=7)**, i.e. totals 147 / 844 /
  5765. Every door is alive at the root, so the Tier-2 terms are 0 there;
  see §D for why nothing local can move this. Over 100 beam states at depth
  200 (n=6): mean cycle 608.99, arc 608.99, residual 610.74 (**uplift
  +1.75**, and residual < arc on 0 of 100).
* **GC** n=6 stratified beam, width 2000, `--strat-quota 4 --strat-bucket 1`:
  `--bound cycle` **902** (26.7 s), `--bound arc` **902** (27.9 s),
  `--bound residual` **894** (29.6 s) — **8 characters better, no
  regression**, ~11 % slower. Mean worst-kept score per level (the pruning
  threshold) rises by **+2.63**, so the beam window is genuinely tighter.
  The canonical *learned-model* config is unaffected by `--bound` (the flag
  conflicts with `--model`) and still returns 873.
* **GD** `cargo test --release` 95/95 green (9/33/153 pins untouched),
  `cargo clippy --release --all-targets -- -D warnings` clean, `cargo fmt`
  applied.

## Hard invariant (absolute)

B must NEVER exceed the true optimal completion cost of the state — for
**covering walks** (revisits of covered perms allowed), not merely Hamiltonian
completions. Any term without a written proof for arbitrary residual covering
walks stays OUT of the admissible bound (it may ship separately as a heuristic
ordering term, clearly separated in code and docs). Greedy 9/33/153 and all
existing defaults unchanged; the new bound is opt-in (`--bound residual`).

## Tier ladder

- **Tier 1 (safe, must land):** exact residual class accounting. r = uncovered
  perms; c = rotation classes with ≥1 uncovered perm. Every step covers ≤1 new
  perm (≥ r steps, weight ≥1 each); inter-class steps have weight ≥2 and the
  walk must enter every residual class other than cur's current class at least
  once ⇒ B₁ = r + (c − 1) − [cur in a residual class] adjustments, all proven
  in the doc. Expected root value n=6 ≈ 838–842 (≈ parity with today; the
  value is the exact fragment-aware accounting + the platform for Tier 2).
- **Tier 2 (the prize, research):** localize the door/freshness argument.
  Hunter's per-vertex price q_k ≈ 1 + 1/k + 1/(k(k−1)) + … comes from: entries
  chained by weight-2 doors follow the τ₂ functional structure (period k−1),
  a sustained chain forces the chart, deviations cost ≥3, post-chart ≥4
  (`lem:tau2/tau3/rigidity/closure`). The global proof runs through the
  F-transform on complete paths; the task is a residual-local version: for an
  arbitrary covering walk of R, lower-bound the number of ≥3-weight entries
  forced by the door structure of R's residual classes. Every claimed term
  requires a written proof (in this doc) + empirical non-violation on the
  tablebase sample. If proven: B₂ → r·q_k-shaped, root ≈ 869 at n=6.
- **Tier 3 (fallback, non-admissible):** any Tier-2 term that resists proof
  but never violates the tablebase empirically ships as `heuristic_floor`,
  usable for move/beam ORDERING only — never pruning. Code must make the
  distinction impossible to confuse (separate function, loud naming).

---

# Proofs (session 19)

Notation: state `(cur, visited)`, residual set `R = complement(visited)`,
`r = |R|`, `A = R ∪ {cur}` the set of permutations the walk may still
*stand on*. `σ = succ1` is the left rotation, `τ(v) = v₃…v_n v₂ v₁` the
**door** (`Graph::w2x`, the unique cross-class weight-2 successor),
`τ⁻¹ = Graph::w2rev`. Rotation classes are the σ-orbits (size n,
`(n−1)!` of them). Arcs are the maximal runs of consecutive residual
permutations inside a class; a wholly residual class is one *circular*
arc.

## §A. Reduction: covering walks ≡ first-visit sequences

The overlap weight obeys the triangle inequality `w(a,c) ≤ w(a,b)+w(b,c)`
(concatenating the two completions reaches `c` from `a` at that cost, and
`w(a,c)` is minimal). Let W be any covering walk from `cur` that visits
every member of R, possibly revisiting covered permutations, and let
`v₁,…,v_m` be the order of *first* visits of R. Splitting W at those
first visits and applying the triangle inequality to each segment gives
`cost(W) ≥ w(cur,v₁) + Σ w(vᵢ,vᵢ₊₁)`. Conversely any such sequence is a
covering walk. Hence

> **(A1)** the optimal covering cost equals the minimum of
> `Σ w(v_{i−1}, v_i)` over sequences `cur = v₀, v₁, …, v_m` with
> `{v₁,…,v_m} = R` **distinct**.

This is the same fact that makes `src/endgame.rs` exact, so the
tablebase truth used in gate GA is exactly the quantity being bounded.
Every proof below may therefore assume a simple first-visit sequence,
and it transfers to arbitrary covering walks. Two consequences used
throughout:

* **(A2)** the predecessor of `x`'s first visit lies in `A ∖ {x}`;
* **(A3)** distinct `x ∈ R` have distinct first-visit steps, so a charge
  levied once per `x ∈ R` never double-counts a step.

## §B. Tier 1 is exactly the arc bound — and that is optimal

**(B1) In-class edges cost exactly the rotation distance.** For a
permutation `P` and `1 ≤ j < n`, `overlap(P, σ^j P) = n − j` exactly: the
suffix `P[j..]` is a prefix of `σ^j P`, and a longer match would force
`P[j−1] = P[j]`, impossible for distinct symbols. So moving `j` positions
forward inside a class costs exactly `j`, and any edge leaving a class
has weight ≥ 2 (weight-1 edges are rotations).

**(B2) Exact per-class accounting.** Attribute each step to the class of
its *target*; every step is attributed exactly once. Fix a residual class
`C ≠ class(cur)` with residual set `S = R ∩ C`, `m = |S|`, and let the
cyclic gaps between consecutive members of `S` be `g₁ ≥ … ≥ g_m`
(`Σ gᵢ = n`). Suppose the walk enters `C` from outside `t ≥ 1` times.
Each entry costs ≥ 2 by (B1). Between entries the walk moves inside `C`
by rotations, so the members of `S` are covered by `t` cyclic blocks,
each starting at an entry point; the total in-class travel is the total
forward rotation, which is minimised by skipping the `t` largest gaps:
`travel ≥ max(0, n − Σ_{i≤t} gᵢ)`. Therefore the cost attributed to `C`
is at least

```text
φ(C) = min_{1 ≤ t ≤ m} [ 2t + max(0, n − Σ_{i≤t} gᵢ) ].
```

**(B3) φ collapses to the arc count.** Write `h(t) = 2t + n − Σ_{i≤t} gᵢ`;
then `h(t+1) − h(t) = 2 − g_{t+1}`, so `h` decreases exactly while the
next gap exceeds 2 and the minimum is attained at `t = α := #{i : gᵢ ≥ 2}`,
giving `φ(C) = Σ_i min(gᵢ, 2) = m + α`. And `α` is precisely the number
of **arcs** of `C` (a gap ≥ 2 is the break between two arcs; a wholly
residual class has all gaps 1 and `φ = h(1) = n + 1 = m + 1`, its single
circular arc). The same computation for `cur`'s class, where the first
sojourn starts at `cur`'s (covered) position at distance `a` inside its
gap `g*`, gives
`ψ = Σ_{other gaps} min(g,2) + min(g* − a, 2)`, which equals
`m + α − [σ(cur) ∈ R]` in every case. Summing:

> **(B4) Theorem.** The best bound obtainable by per-class accounting is
> exactly `Σ_C φ(C) = r + #arcs − [σ(cur) ∈ R] = lb_arc`.

So Tier 1 *is* the shipped arc bound, and the design doc's expected
"parity with today" is provable rather than empirical. It also says where
to dig: since the intra-class gap structure is fully exploited, **every
further character must come from cross-class (door) structure.**

## §C. Tier 2 (proven): the residual door bound

**(C1) The in-neighbour census.** The weight-`w` in-neighbours of `x` are
the `w!` permutations `t ++ x[..n−w]` with `t` an arrangement of
`x[n−w..]`. So `x` has exactly **one** weight-1 in-neighbour `σ⁻¹(x)`
(in-class), exactly **two** weight-2 in-neighbours — the in-class
`σ⁻²(x)` and the cross-class **door** `τ⁻¹(x)` — and exactly **six**
weight-3 in-neighbours. This is the vertex-level content of Hunter's
`lem:successors`/`lem:tau2` and is pure word algebra: it needs no path
hypothesis, so it localizes verbatim. `src/lb_residual.rs` tabulates all
nine (`PredTable`).

**(C2) Minimum-in-edge term.** Let
`minin(x) = min{ w(y→x) : y ∈ A ∖ {x} }` (capped at `min(4,n)`: if none of
the nine tabulated in-neighbours is available, every in-edge has weight
≥ 4). By (A2) the first visit of `x` costs ≥ `minin(x)`; by (A3) these are
distinct steps. Hence

```text
cost ≥ Σ_{x∈R} minin(x) = r + door,     door = Σ_{x∈R} (minin(x) − 1).
```

This is the residual-local door argument: **an entry into `x` must cost
≥ 3 exactly when `σ⁻¹(x)`, `σ⁻²(x)` and `τ⁻¹(x)` are all covered**, and
≥ 4 when all six weight-3 in-neighbours are covered too. The latter is
the residual-local analogue of `lem:closure`'s "a jump into a fresh class
costs ≥ 4" — obtained *without* the chart, since we can simply read off
which in-neighbours are still standable instead of proving that they must
all lie in a rigid chart.

**(C3) Intact-class term.** If a class `C` is wholly residual, the first
member of `C` visited is entered from outside `C` (an earlier-visited
member would contradict firstness), so that step costs ≥ 2 by (B1). But
every `x ∈ C` has `σ⁻¹(x) ∈ C ⊆ R ⊆ A`, so term (C2) charged it exactly
1 — whichever member is entered first. One further character may
therefore be charged per intact class: `+ intact`.

**(C4) Dead-door term.** Let `C` have exactly one covered member
`p ≠ cur`; its residual part is the single arc `α = C ∖ {p}` with head
`h = σ(p)`. Term (C2) charged `minin(h) = 2` (weight-1 in-neighbour `p`
is covered; weight-2 in-neighbour `σ⁻²(h) ∈ α ⊆ R` is available) and 1
for every other member. The first member of `α` visited is entered from
outside `α`, and

* for `x ≠ h` that entry costs ≥ 2, because the only weight-1
  in-neighbour `σ⁻¹(x)` lies inside `α` — one above its (C2) charge of 1;
* for `x = h` it costs ≥ 3 **whenever the door `τ⁻¹(h)` is unavailable**,
  since `h`'s in-neighbours of weight ≤ 2 are `p` (covered), `σ⁻²(h)`
  (inside `α`) and `τ⁻¹(h)` — one above its (C2) charge of 2.

So when `τ⁻¹(h) ∉ A`, one further character may be charged for `C`
regardless of which member is entered first: `+ long`. `cur`'s own class
is excluded (its single covered member would be `cur`, and then
`σ⁻¹(h) = cur ∈ A` makes the entry cheap).

The charges of (C2) sit on distinct steps, and (C3)/(C4) charge excess
*above* the (C2) charge of one specific step each, so they add:

> **(C5) Theorem.** `B_residual = r + door + intact + long` is admissible
> for arbitrary covering walks, and dominates `lb_arc` pointwise: every
> open arc's head `h` has `σ⁻¹(h) ∉ R`, so `minin(h) ≥ 2` unless
> `σ⁻¹(h) = cur` (at most one arc), whence
> `door ≥ #open arcs − [σ(cur) ∈ R]`, while circular arcs are the intact
> classes counted by (C3).

**(C6) What was deliberately dropped.** The fully general form of the
per-arc refinement replaces (C3)+(C4) by
`Σ_arcs min_{x∈α} (E(x) − minin(x))`, where `E(x)` is the cheapest entry
from outside `x`'s *arc*. Measured on beam frontiers at n=6 it is
identical to the shipped bound at depths 200/400/550 and worth +1.25
characters at depth 650, at the price of per-class recomputation per
candidate — not worth it. The dual out-edge bound
(`Σ_{v∈A} minout(v) − max minout`) was also measured: 525 vs 611 at depth
200 and 89 vs 97 at depth 650, i.e. strictly weaker everywhere, so
`max(in, out)` adds nothing.

## §D. What did NOT localize — and precisely where it breaks

The missing mass is the `(n−2)!` term of the classical bound
`n! + (n−1)! + (n−2)! + n − 3 = 867` (n=6) and Hunter's further `+2`.
Our root value is 844, so **23 + 2 characters are missing at the root**,
and every one of them lives in a structure that is provably not visible
from `(cur, R)` alone. Two routes were attempted and both are dead.

**(D1) The partition route (attempted first, refuted by computation).**
The hope: as weight-1 edges preserve rotation classes, weight-≤2 edges
might preserve a partition into `(n−2)!` "2-cycles" of size `n(n−1)`;
then the `(n−2)!` term would be a second-level class count, maintained by
the same decrement-to-zero counters, and residual-local by construction.
**This is false.** Computing the connected components of the graph on all
`n!` permutations with all edges of weight ≤ j (to reproduce: union-find
over all pairs `x → t ++ x[..n−w]`, `t` an arrangement of `x[n−w..]`,
`w ≤ j`):

| n | level 1 | level 2 | level 3 | (n−j)! would predict |
|---|---|---|---|---|
| 4 | 6 | **1** | 1 | 2, 1 |
| 5 | 24 | **1** | 1 | 6, 2 |
| 6 | 120 | **1** | 1 | 24, 6 |
| 7 | 720 | **1** | 1 | 120, 24 |

The weight-≤2 graph is **connected** for every n tested. The reason is
exactly the level-shift the Hunter paper spells out: `τ₂` is a map on
*block entries* (`τ₂(u) = τ(ex(u))` — the door applied at the **exit** of
the block entered at `u`), not a map on vertices. The 2-cycles are orbits
of that block-level map; an arbitrary weight-2 door taken from the middle
of a block leaves the orbit, so no vertex partition is closed under
weight-2 edges and there is no second level of counters to maintain.

**(D2) The run-length route (Hunter's own), and its exact break point.**
Hunter reaches `1/(k(k−1))` (i.e. the `(n−2)!` term) through
`prop:edgebounds`: a path on `ℓ` vertices has ≥ `⌈ℓ/(k(k−1))⌉ − 1` edges
of weight ≥ 3, because a maximal run of weight-2 boundaries spans at most
`k−1` blocks (`lem:tau2`, period `k−1`). That chain rests on
`lem:blockstructure`: *an exitless path never leaves a rotation class
before completing it*, so a path is a sequence of **full** blocks joined
by ≥2-jumps, boundaries sit exactly at multiples of `k`, and
`w(p) = ℓ + b − 2 + E` with `b = ⌈ℓ/k⌉`.

> **The break point is `lem:blockstructure`, and it is fatal at the first
> step.** "Early exit at `v`" means leaving `v` by a weight-≥2 edge *while
> `σ(v)` is still unvisited*. On a residual set, `σ(v)` is routinely
> **already covered** — it is not in `R` at all — so leaving the class
> early is not an early exit, and exitlessness stops forcing full-block
> traversal. Boundaries then no longer sit at multiples of `k`, `b =
> ⌈ℓ/k⌉` is wrong, the identity `w(p) = ℓ + b − 2 + E` collapses, and with
> it `lem:tau2`'s run bound (whose one-line proof — "a `k`-th weight-2
> block would revisit `c(u)`" — additionally uses path simplicity over the
> *whole* path, not just over `R`), `lem:rigidity`'s counting
> `N = Σ Lᵢ ≤ (E+1)n` (which counts blocks *traversed*, not fresh classes
> *covered*), and `lem:closure` (which has no chart to sit at the end of).

The word algebra of `lem:tau2`/`lem:tau3`/`lem:closure` — the six
weight-3 successors `T₁…T₆`, the identifications `T₃ = D₁`,
`T₄ = σ(D₀)`, `T₆ = σ²(D_m)`, the chart `C_{j,i} = τ₂^i τ₃^j(s)` — is
unconditional and does transplant; what does not transplant is the
*hypothesis* that a full, wholly-fresh window of `N = (k−1)(k−2)` blocks
occurs at all. And the reduction from general paths to exitless ones is
`thm:b1`'s F-transform, which is irreducibly global: it needs a
Hamiltonian path over all `k!` vertices, defines `C₀` by the **global**
visit order ("the earliest vertex of `c(v)` reached by `P`"), and
accounts for the surgery in one global weight identity with `minto`
minimised over the entire complement of a component.

**Consequence, stated plainly.** At the root every door is alive
(`R` is everything), so every Tier-2 term above is 0 and the residual
bound *must* equal the arc bound there — 838. A residual-local bound
that reads only `(cur, R)` cannot express "sustaining cheap entries for
`k(k−1)(k−2)` further vertices forces the chart, whose closure then costs
4": that is a statement about a long stretch of the *future* walk, priced
by amortization over `ℓ₀ = k(k−1)(k−2) − k` vertices. Getting it
residual-locally needs a genuinely new device — a window/potential
argument over R (e.g. a certified lower bound on the number of *fresh*
classes any weight-2 run can cover in R, replacing "blocks traversed" by
"classes newly covered" throughout `prop:edgebounds`). That is the next
research step and is explicitly **not claimed here**.

## §E. Tier 3 (non-admissible, ordering only)

`lb_residual::heuristic_floor_not_admissible` returns
`max(B_residual, ⌈q_n · r⌉)` with Hunter's price
`q_k = 1 + 1/k + 1/(k(k−1)) + 1/((k−1)(k(k−1)(k−2)−k))` (`q₆ = 137/114`).
It is **not** admissible — GA measured it exceeding the exact truth on
252/5200 (n=5) and 27/5200 (n=6) samples, as expected, since `q_k` prices
an average vertex of a *complete* path and short fragmented residual
tails are far cheaper per vertex. It is wired into no scorer and no
pruning path; it exists so ordering experiments can try the shape.

---

## Implementation

- Rust, new module `src/lb_residual.rs`; state maintenance is O(1)–O(n)
  per expansion. The transition `(cur, R) → (q, R∖{q})` changes the
  standable set from `R ∪ {cur}` to `R` — i.e. it removes exactly `cur` —
  and that part is shared by every candidate of a state, so it is
  computed once per parent (`ParentCtx::new`, O(9²) lookups); per
  candidate only `q`'s own `minin` (9 lookups) and `q`'s rotation class
  need attention (`child_terms`, O(n)). Wired into `Walk::advance` AND
  beam `State`/`score_move` (not beam2), per the CLAUDE.md multi-copy
  rule. Beam dedup purity holds: `door`, `long` and `intact` are pure
  functions of `(cur, visited)`. The in-neighbour table is built only
  when `--bound residual` is selected, so every other scorer keeps its
  exact previous cost.
- `--bound residual` on the beam and trace paths; default behavior
  bit-identical without the flag.
- Tests: `PredTable` against brute-force in-neighbours; `minin` against a
  brute-force minimum over all standable predecessors; incremental
  `door`/`long`/`intact` against from-scratch recounts at every step of
  random walks (n = 3, 4, 5); dominance over `lb_arc`; admissibility
  against the exact tablebase on short tails; the residual-scored beam
  reproducing 9/33/153.

## Gates

- **GA (admissibility, blocks everything):** ≥10k sampled states with m ≤ 25
  remaining across n = 5 and 6 (greedy/beam prefixes + random completions),
  exact truth via the endgame tablebase: assert B ≤ truth on every sample,
  report the slack distribution. One violation = the term responsible is cut.
- **GB (strength):** root values (state after the initial permutation):
  report exact B at n = 5, 6, 7 per tier; Tier-1 target ≈ parity with the
  current bound, Tier-2 target ≥ 860 at n=6 (869-shaped). Also report B on
  100 random depth-200 n=6 beam states vs the current bound (mean uplift).
- **GC (search effect):** n=6 beam A/B at equal width (2000, canonical model
  config from CLAUDE.md): prune-rate/cutoff-log comparison + final lengths.
  Any regression in achieved length at equal width = report loudly.
- **GD (invariants):** cargo test --release green (9/33/153 pins), clippy
  clean, no default-path behavior change.

Results of all four are recorded in the STATUS section at the top.

## Non-goals (this session)

No B&B driver, no learned-evaluator integration, no n=7 deployment — those
build on a gated bound, later.
