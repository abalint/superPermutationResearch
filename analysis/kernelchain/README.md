# kernelchain — proofs that Egan−1 is optimal in the gain-one grammar at n=6

Session-10 analysis scripts (pure Python 3 stdlib, self-contained — the marked-loop
/ door machinery is re-derived from first principles and gate-validated against the
standard kernel). Run each with `python3 <script>`; output is printed. See
`docs/ITEM5-DESIGN.md` §3–4 and JOURNAL s10–s11 for the results these establish.

- `chain.py` — marked-loop enumeration (144 loops), cost-3 hop pair graph,
  validation gate (recovers the standard kernel's three hops as unique options),
  first chain searches. Key facts: the forced (full-ride) hop-successor map has
  period exactly 4 for all 720 (loop, entry) states; cost-3 hops preserve the
  pivot, so chains live inside one 24-loop pivot class.
- `skipchain.py` — the skip-priced waste ledger
  (`waste = 148 − K/4 + Σskip/4 + f4 + 2·f5`), mixed-cost (3–6) branch-and-bound
  over chains, exhaustive census of ledger-optimal (V = K − Σskip − 4f4 − 8f5 = 8)
  chains: exactly 12 (6 × K=22/Σ=14 and 6 × K=20/Σ=8/one skip-0 cost-4 hop, one
  per pivot class). Also proves: hops of ANY cost end with the pivot symbol
  (analytic + computational), so pivot confinement is absolute; V = 12 (waste
  145, length 870) is unreachable.
- `skipcover.py` — rooted-forest exact-cover checker over a chain's non-root
  orbits. Validated by re-finding a forest-valid 25-row cover under the standard
  K=4 kernel (the known 872 structure, ~11 s); finds ZERO covers for all 12
  ledger-optimal chains.

**Combined theorem: length 871 is unreachable in the gain-one certificate grammar
(complete rows, hops of any cost) at n=6 — Egan−1 = 872 is optimal in the class,
and the standard kernel is a proven optimum, not a convention.**
