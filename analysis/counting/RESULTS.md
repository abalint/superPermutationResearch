# Counting superpermutations with local rules only

**What this measures.** How many length-`L` words survive purely *local* necessary
conditions, versus how many superpermutations there actually are. The ratio is a
direct read on how much of the problem is carried by the **global coverage
constraint** — the part no local ledger can see.

Everything here is exact integer arithmetic. Reproduce with:

```
python3 analysis/counting/count_bound.py            # ~6 s, single core
python3 analysis/counting/count_bound.py --skip-mc  # ~3 s, deterministic only
```

---

## 1. The frame

A word `W` of length `L` over `[n]` whose first and last `n`-windows are
permutations is in bijection with its **trace**: the ordered positions where an
`n`-window is a permutation. Consecutive trace positions differ by a gap
`w ≥ 1`; for `w ≤ n` the step is exactly "append the `w` symbols carrying perm
`p` to perm `q`, with no intermediate window a permutation". So

```
W  <->  (start perm p0, step weights (w_1..w_S), branch choices),   Σ w_i = L − n.
```

Fixing `p0 = 12…n` quotients out the `n!` relabelings **exactly** (relabeling acts
simply transitively on permutations), so *walk from the identity == canonical
word*. This matches how the ground truth is counted: `Chaffin_4_W_6.txt` holds 1
word and `Chaffin_5_W_29.txt` holds 8 words, both "starting with 123…n".
No reversal quotient is applied (divide by ~2 if you want one).

Two standing assumptions, both forced at minimal `L`: the word starts/ends on a
permutation window (otherwise delete the offending end character), and no gap
exceeds `n` (a larger gap is `n`-window-free filler, deletable at these lengths).

### Branching numbers — the task's formula was wrong

`b(w)` = number of weight-`w` out-edges at any permutation. Brute force
(`verify_branching`, all of `n = 3..6`) gives

| w | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| **`b(w)` (brute force)** | 1 | 1 | 3 | 13 | 71 | 461 |
| `w! − (w−1)!` (assumed) | 0 | 1 | 4 | 18 | 96 | 600 |

`b(w)` is the count of **indecomposable permutations** of `[w]` (OEIS A003319):
appending `x_1..x_w` lands on a permutation iff `{x} = {p_1..p_w}`, and the
intermediate window at offset `k` is a permutation iff `set(x[:k]) = set(p[:k])`,
so the legal `x` are exactly the orderings with no proper prefix-set match.
`w! − (w−1)!` imposes only the `k = 1` obstruction and is therefore a strict
over-count. Vertex-transitivity of the profile was verified over **all**
permutations for `n = 3, 4, 5`, which is what licenses "multiply by `b(w)` per
step" as an exact walk count.

---

## 2. The rule ladder

| level | added constraint | status |
|---|---|---|
| **R0** | steps of weight `1..n` summing to `L−n`, branching `b(w)` | **proven** (and exact: this *is* the walk count) |
| **R1** | `#steps ≥ n!−1`, i.e. excess `e = Σ(w_i−1) ≤ D := (L−n) − (n!−1)` | **proven** (each step adds ≤ 1 new perm) |
| **R2** | R1 + revisit ledger: `e + Σ_{1-runs} max(0, r − (n−1)) ≤ D` | **proven** (see below) |
| **R2+** | R1 + hard cap (no 1-run > `n−1`) + no weight-`n` step | **empirically verified, unproven** |
| **R3** | R2+ + per-weight-class count bands measured on that same `n`'s optima | **empirical & circular** — a conditional count, not a bound |

**R2's proof.** Let `R` = number of steps landing on an already-visited
permutation. Distinct perms visited `= 1 + S − R = n!`, and `S + e = L − n`,
hence `R + e = D` *exactly*. A run of `r` consecutive weight-1 steps walks a
rotation cycle of length `n`, so it forces at least `max(0, r−(n−1))` revisits.
Summing gives the ledger inequality. R2 is strictly weaker than a hard run cap
(it *prices* long runs instead of banning them) but is fully proven; it happens to
coincide with the hard cap whenever `e = D`.

### Verification status of every ingredient

| ingredient | how verified |
|---|---|
| `b(w) = A003319(w)` | brute force `n = 3..6`, exhaustive over all successors |
| vertex-transitive branching | brute force over all `n!` perms, `n = 3, 4, 5` |
| R1 (`steps ≥ n!−1`) | proven; also observed exactly tight on all 305 corpus words |
| R2 ledger | proven; corpus has `R = 0`, `e = D` in every word |
| R2+ hard 1-run cap `≤ n−1` | holds and is **tight** (`= n−1` attained) on all 305 corpus words; *not proven* |
| R2+ "no weight-`n` step" | holds on all 305 corpus words (max weight 3/4/3 for `n=4/5/6`); *not proven* |
| R3 weight bands | measured, self-referential — reported as regularity |
| DP correctness | R2+ DP cross-checked against an independent multiset/inclusion-exclusion sum at every `(n, L)` |
| whole frame | at `n=4, L=33` the R2/R2+/R3 populations were **enumerated as real walks** (224/218/15 words, matching the DP exactly) and contain **exactly 1** superpermutation |

### Corpus measured (`measure_corpus`)

| n | L | words | steps | `e` | `D` | max weight | max 1-run | weight profile |
|---|---|---|---|---|---|---|---|---|
| 4 | 33 | 1 (Chaffin `_4_W_6`) | 23 | 6 | 6 | 3 | 3 | `m2=4, m3=1` |
| 5 | 153 | 8 (Chaffin `_5_W_29`) | 119 | 29 | 29 | 4 | 4 | `m2∈[18,25], m3∈[2,4], m4∈[0,1]` |
| 6 | 872 | 296 (`records872/` + `gain1_872s/`) | 719 | 147 | 147 | 3 | 5 | `m2=141, m3=3` — **identical in all 296** |

Every corpus word has exactly `n!` distinct permutation windows (zero repeats),
so `R = 0` and `e = D` throughout — the proven ledger is saturated by the excess
alone. *(Note: 296 distinct 872-length words are on disk; `CLAUDE.md` says 298
in one place and 296 in another. 296 is what the files contain.)*

---

## 3. Main table — log10 of the bound

| level | n=4, L=33 | n=5, L=153 | n=6, L=872 |
|---|---:|---:|---:|
| **R0** | 11.59 | 70.32 | 460.63 |
| **R1** | 6.38 | 34.88 | 190.28 |
| **R2** *(last proven level)* | **2.35** | **17.05** | **94.07** |
| R2+ *(unproven)* | 2.34 | 16.96 | 93.77 |
| R3 *(empirical, circular)* | 1.18 | 16.43 | 92.99 |
| R3 + symbol band *(MC estimate)* | 0.04 | 14.30 | 92.83 |
| **truth** | **0.00** (=1) | **0.90** (=8) | **≥ 2.47** (296 known) |

Exact small values: R0(4,33) = 392 648 562 588, R1 = 2 423 627, R2 = 224,
R2+ = 218, R3 = 15, truth = 1.

### Calibration reading

* The **last proven** level (R2) overshoots the truth by
  **2.4 / 16.2 / 91.6 orders of magnitude** at `n = 4 / 5 / 6`.
* The gap **grows roughly like `n!`**: 2.4 → 16.2 → 91.6 orders, i.e. about
  **0.10–0.13 orders per step** of the walk (`94.07/719 = 0.131/step` at `n=6`). Equivalently,
  local rules leave an average residual branching factor of **≈ 1.35 per step**
  at `n=6` that only global coverage can remove.
* Each added local rule buys a fixed, shrinking amount and then stops:
  R0→R1 buys 270 orders at `n=6`, R1→R2 buys 96, R2→R2+ buys 0.30,
  R2+→R3 buys 0.78, symbol band buys 0.16. **The ladder is converging to
  something around 10^92, not to 10^2.5.**
* The most striking single number: **all 296 known 872s share one weight
  multiset** (141 weight-2 steps, 3 weight-3 steps, 575 weight-1 steps). Even
  after fixing that exact profile *and* capping 1-runs, there are **10^93** ways
  to lay it out — and 296 of them work. Local structure determines the *budget
  spending pattern* essentially completely and the *solution* not at all.
* A uniformly random R3-legal word (exact optimal weight multiset, capped runs,
  uniform branch choice) covers on average **51 % of the 720 permutations**
  (best of 3000 samples: 473/720). Coverage is not close to free.
* The symbol-frequency band is nearly worthless as a filter at `n=6`: 68.6 % of
  random R3-legal words already satisfy the band measured on the real 872s
  (0.16 orders). It tightens with `n` in *relative* terms — corpus bands are
  `[0.73, 1.21]·(L/n)` at `n=4`, `[0.78, 1.11]` at `n=5`, `[0.92, 1.04]` at
  `n=6` — but that tightening is a property of long words, not a discriminator.
  It is also not expressible as a filter on weight compositions at all (weights
  don't determine symbol counts), so it is reported as a measured regularity and
  its strength estimated by Monte Carlo rather than folded into a bound.

---

## 4. Smallest `L` with a nonzero bound (nonexistence reach)

| level | n=4 | n=5 | n=6 |
|---|---:|---:|---:|
| R0 | 4 | 5 | 6 |
| R1 (`n + n! − 1`) | 27 | 124 | 725 |
| **R2 / R2+ (`n + n! + (n−1)! − 2`)** | **32** | **147** | **844** |
| true lower bound | 33 | 153 | **869** (Lean-formalized) |
| shortfall | 1 | 6 | 25 |

R2's threshold is proven in closed form (docstring of `smallest_nonzero_L`) and
spot-checked against the boolean feasibility DP at `threshold−1` (infeasible) and
`threshold` (feasible). So the local ladder **exactly recovers the classical
first-order lower bound** `n! + (n−1)! + n − 2` and nothing more. It does *not*
prove nonexistence below the true minimum at any `n`.

**The counting-proof window is exactly one length wide.** At
`L = n + n! + (n−1)! − 2` the R2 count is *exactly 1* for `n = 4, 5, 6` — a unique
composition (every 1-run exactly `n−1`, every other step weight 2, and `b(2)=1`
leaves no branch freedom). One character more and it explodes:

```
n=4:  L=32 → 1        L=33 → 10^2.35
n=5:  L=147 → 1       L=148 → 10^5.07    L=151 → 10^13.13
n=6:  L=844 → 1       L=845 → 10^9.69    L=848 → 10^27.36
```

At `n=4` that single candidate can be enumerated and shown not to be a
superpermutation, so `S(4) ≥ 33` falls out of the ladder plus one explicit check.
At `n=6` the same move dies immediately: `L=845` already has 4 925 157 131
candidates, and the true frontier sits 24 characters further up at 10^~85.

---

## 5. What would have to change for counting to bite

Nothing in this ladder is close. To turn a counting argument into a nonexistence
proof at, say, `n=6, L=871`, the bound must fall from ~10^93 to below 1 — you need
local rules that remove **~93 orders of magnitude**, i.e. essentially all
remaining freedom, ~0.13 orders per step, at every one of 719 steps. Rules that
each buy a fixed additive amount (0.3 here, 0.8 there) cannot do this; the buy has
to be *multiplicative per step*, which means it has to be a rule about how a step
constrains the *next* step, not about how many steps of each weight there are.

The mechanism that actually does this is the one this repo already uses, and it is
worth naming the identity precisely: **R1/R2 are the Hunter-ledger argument in its
crudest form.** `R + e = D` is a waste ledger; R2 prices 1-run overflow against
that budget and R1 prices excess weight. The gain-one certificate ledger at `n=6`
(`waste = 148 − K/4 + Σskip/4 + f4 + 2f5`, forced-map period 4, absolute pivot
confinement) is the *same* mechanism refined to the point where the budget is
provably exhausted — and it does bite: it proves 872 optimal inside the grammar.
The difference is entirely the granularity of the objects being priced. R2 prices
individual steps against a budget of 147 and leaves 10^94 configurations; the
gain-one ledger prices whole 2-cycles, kernels, skips and weaves against the same
147 and leaves 12 chains, all of which are then killed by an explicit cover check.

So the honest ladder continuation is not "more local rules" but **the next rung of
the same telescope**: the argument that produced the `(n−1)!` term (weight-1 runs
confined to a rotation cycle) applied one level up — weight-≤2 runs confined to a
2-cycle coset, which is exactly what yields the `(n−2)!` term of the
Aaronson–Johnston bound, and then again at the kernel level. Each rung converts
one layer of coverage structure into ledger currency. The measurement here says
the first two rungs together are worth about 366 of the 458 orders at `n=6`
(R0→R2), and the remaining 92 orders live entirely in structure the ledger cannot
yet charge for. A counting-style nonexistence proof requires pushing that
telescope until the budget is exhausted at the level where the solutions actually
live — which is the premise of the `gain-1` grammar work, and the reason the
sub-872 question had to be reframed as "must leave the grammar" rather than
"must beat a counting bound".

---

## Files

* `count_bound.py` — everything above; brute-force verification, corpus
  measurement, exact DP bounds, closed-form thresholds, Monte-Carlo regularity.
  Standard library only.
* Data consumed: `data/chaffin/ChaffinMethodResults/Chaffin_4_W_6.txt`,
  `Chaffin_5_W_29.txt`, `data/records872/*.txt`, `data/gain1_872s/*.txt`.
