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
- **Loop-count relation (s35, corpus law, derivation OPEN):** the number of distinct
  2-loops a walk's w2 edges use satisfies `L = S + #doors − ((n−1)! − 1)`, equivalently
  `length = n! + (n−1)! + (n−3) + Λ` with `Λ = L + Σ_{w≥4}(w−3)·inter[w]` — verified
  exceptionless on 22,062 n=6 872s, 4 off-shell 873s (incl. a wild
  18×w3/4×w4/1×w5 allocation), and all 87 known n=7 walks
  (`analysis/counting/loop_census.py`, exit-0 verifier). One char = one Λ-unit on the
  record shell: an 871 is a Λ=28 object, a 5905 is Λ=141. If derived, this becomes the
  cycle-level restatement of the waste identity; SURGERY-DESIGN §10.1 builds the I3
  prune tier T4 on it either way.
