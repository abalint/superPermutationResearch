# Computational result: Egan−1 (872) is optimal within the gain-one certificate class at n = 6

Status: **draft for sharing — pending independent verification** (a second,
clean-room implementation in Rust is planned; the current proofs are one Python
implementation, gate-validated as described below). Date: 2026-07-27.
Scripts: `analysis/kernelchain/` in this repository (pure stdlib Python 3;
runtimes on a laptop are seconds to ~30 s per stage).

## Statement

Fix n = 6 and consider superpermutation walks in the **gain-one certificate
class** in the sense of urdvr's certificate machinery
(github.com/urdvr/superpermutation-examples), which we formalize as:

- moves are doors `T_k(w) = w[k:] + reverse(w[:k])` with k = 1 (rotation) and
  k = 2 (the unique cross-cycle weight-2 edge), plus **hops**: doors of cost
  ≥ 3, each replacing a splice of a kernel loop and opening the next kernel loop;
- a **kernel** of K orbit-disjoint marked loops (complete 2-cycles) chained by
  K − 1 hops, ridden forward from the loop containing the identity's orbit;
- non-kernel coverage by **complete oriented rows** (a marked loop entered from a
  parent orbit, riding its other orbits fully, returning to the parent), whose
  ownership relation forms a forest rooted in the kernel, children partitioning
  the non-root orbits exactly once (exact cover).

All 296 currently known distinct 872s (100 community records + 196 DLX-generated)
lie in this class with the standard K = 4 kernel — we verified this by a
cycle-level trace of each (exact grammar, zero exceptions).

> **Result. Within this class — for every kernel size K, every hop-cost
> assignment, and every rooted exact cover — no word of length ≤ 871 exists.
> Egan−1 = 872 is optimal in the class, and the standard (K = 4) kernel is a
> proven optimum, not a convention.**

Corollary: allowing *incomplete* rows does not help — each incompleteness raises
the sojourn count and hence the waste by ≥ 1 (see the ledger below), so
incomplete-row certificates tie 872 at best. Consequently any n = 6 word of
length ≤ 871, if one exists, must leave the certificate grammar itself
(non-laminar structure, weight-2 moves other than the cross-cycle door, or
mid-walk weight ≥ 4 moves).

## Method

Everything reduces to a waste ledger plus three finite computations.

**1. General identity** (any tight superpermutation walk whose intra-orbit moves
are all weight 1 — true of every known record and of greedy; an intra-orbit
weight-2 move adds 1 further waste per occurrence without ending a sojourn):
`waste = (S − 1) + #w3 + 2·#w4 + 3·#w5`, where S is the number of sojourns
(maximal single-orbit runs) and #wk counts weight-k moves. For n = 6:
length = 725 + waste; the records have S = 145, #w3 = 3, waste 147.

**2. Skip-priced ledger** (certificate class). A kernel loop arrived at entry k
that exits by a hop replacing splice j rides `((j−k) mod 5) + 1` entries and
skips `4 − ((j−k) mod 5)` orbits; skipped orbits must be bought back by extra
rows. With f4/f5 hops of cost 4/5:

```
waste = 148 − K/4 + Σskip/4 + f4 + 2·f5
871   ⇔  V := K − Σskip − 4·f4 − 8·f5 ≥ 8      (Σskip ≡ K mod 4)
```

**3. Period-4 obstruction** (`chain.py`). The forced (skip-0) hop-successor map
on all 720 (loop, arrival-entry) states is a permutation of cycle period exactly
4. Hence skip-free chains cap at K = 4 — this is *why* the standard kernel has
n − 2 loops — and longer chains must pay skips.

**4. Pivot confinement** (`skipchain.py`). A door of any cost ends with the
pivot symbol, so hops never leave a pivot class: every chain lives inside one of
the six 24-loop classes (checked computationally for costs 3–6 and analytically).

**5. Exhaustive chain census** (`skipchain.py`). Branch-and-bound over chains
with hop costs 3–6 (complete, ~30 s): **max V = 8**, attained by exactly 12
chains — six (K = 22, Σskip = 14) and six (K = 20, Σskip = 8, one skip-0 cost-4
hop), one per pivot class, each set relabelings of a single chain. V = 12
(length 870) is unreachable.

**6. Cover refutation** (`skipcover.py`). For each of the 12 ledger-optimal
chains, an exhaustive rooted-forest exact-cover search over its non-root orbits
finds **zero covers**. The checker is validated positively: under the standard
K = 4 kernel it finds a forest-valid 25-row cover (the known 872 structure) in
~11 s.

Steps 5 and 6 together give the result: length 871 requires V ≥ 8 with a
complete-row cover; all V = 8 structures exist and all fail coverage.

## Validation gates

- The hop relation, extracted from the certificate compiler, reproduces the
  standard kernel's three hops as the unique connecting options for its loop
  pairs, with the correct cut permutations.
- The ledger reproduces every known data point: standard K=4 → 872 with the
  exact 141/3 weight census of all 296 records; at n = 7, K=5 → 5907 (the three
  known standard-kernel words) and the 5906 record's census (822 T2 / 19 T3,
  five incomplete groups, 20-loop nonstandard kernel) prices as a K=20
  certificate paying 2 characters of concessions.

## What this does and does not say

- It **does** close, at n = 6, the direction "adapt the gain-one machinery to
  nonstandard kernels": no kernel choice helps; 872 is the class optimum.
- It does **not** bound general superpermutations: 867–871 remain open outside
  the class. The general identity in step 1 says any 871 must realize
  S − 1 + #w3 + 2#w4 + 3#w5 = 146 — e.g. 144 sojourns with three w3 moves — in
  some structure no known word exhibits.
- At n = 7 the analogous question (max V₇; V₇ ≥ 15 would give 5905 < 5906) is
  open and computable with the same method; the 5906 itself shows the n = 7
  class is richer (its kernel escapes the standard form while staying in the
  grammar).

## Reproduction

```
cd superPermutationResearch
python3 analysis/kernelchain/chain.py       # loops, pair graph, gate, period
python3 analysis/kernelchain/skipchain.py   # ledger, B&B census (max V = 8)
python3 analysis/kernelchain/skipcover.py   # cover refutation + positive control
```

Credits: the certificate formalization and compiler are urdvr's
(superpermutation-examples); the nonstandard-kernel direction was suggested by
R. Houston on the same thread. The skip-priced ledger, the period-4 and
pivot-confinement lemmas, the exhaustive census, and the cover refutation are
this project's contribution.
