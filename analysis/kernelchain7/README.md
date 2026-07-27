# kernelchain7 — the n=7 max-V₇ campaign (session 12)

Port of `../kernelchain/` to n = 7 (840 marked loops, 720 orbits, 6 splices per
loop). Ledger: `waste = 862 − V₇/5`, `V₇ = K − Σskip − 5f4 − 10f5 − 15f6`;
length = 5046 + waste. Targets: V₇ = 15 → 5905 (beats the 5906 record),
V₇ = 20 → 5904.

Facts established (gates all passed; see JOURNAL s12):

- The three known 5907 words ARE standard-kernel gain-one certificates (traced
  from the raw strings: census 4182/853/4, kernel = the standard K=5 chain up to
  relabeling) — `trace5907.py`.
- Forced (skip-0) map period is exactly **5 = n−2** on all 5040 states,
  mirroring period 4 = n−2 at n=6 — `gates7.py`. Pivot confinement holds at all
  hop costs; each pivot class's 120 loops partition the 720 orbits.
- **Skip-1 lemma** (proven 720/720): a skip-1 hop lands on the *preceding* loop
  of its own forced 5-cycle, so skip-1 deviations cannot make progress; any
  net-positive deviation costs ≥ 2 skip. Corollary: **V₇ ≤ 74**, and the naive
  minimal signatures (K=18, Σ=3), (K=24, Σ=4) are empty.
- **V₇ = 15 chains are plentiful** (100 enumerated, `enum15.py`; e.g. K=27,
  Σ=12 = standard-kernel prefix + six skip-2 deviations; R = 114, 2662 eligible
  rows — count-feasible). **V₇ = 20 exists** (4 found; K=46, Σ=26, R = 94,
  1545 eligible rows). Best found overall: V₇ = 36 heuristically (beam,
  `beam7.py`, chains in `best_chain.txt` / `beam_best_w20000.txt`); complete
  B&B is infeasible at n=7 — bounds stand at 15 ≤ max V₇ ≤ 74.
- High-K ledger optima die at row-count feasibility (e.g. the K=99/Σ=64 V=35
  chain has 36 eligible loops for R=38), echoing the n=6 cover refutation.

**The open decisive question: does any V₇ ≥ 15 chain admit a rooted exact
cover?** Any yes, compiled and validated, is a world record (≤ 5905). This is
the kernel-parameterized DLX task; urdvr's compiler is kernel-generic and their
DLX solves same-scale instances (690 columns / 4440 rows) in seconds.
