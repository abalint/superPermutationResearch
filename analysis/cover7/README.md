# cover7 — the n=7 rooted-cover record attempt (session 13, ongoing)

Kernel-parameterized exact-cover pipeline over the V₇ ≥ 15 chains from
`../kernelchain7/`. Any rooted cover of a V₇=15 chain compiles to a word of
length **5905** (record: 5906); V₇=20 ⇒ 5904. Status: **no solution yet; the
question is open and reduced to concrete instances** (see below). Long-running
engine processes may still be active — check
`pgrep -f "PermutationChains 7 nsk"`.

## Pipeline (validated end-to-end)

- `chain7.py` — the kernel-parameterized instance builder + compiler glue
  (adapts urdvr's `gain1.py`/`certificate.py`; roots = *ridden* orbits only,
  skipped-orbit splices become `disabled_splices`).
- Positive controls, all cargo-validated: rebuilds the standard instance
  byte-identically; compiles a **5907** from the standard chain
  (`candidate_5907_std.txt`); and — decisive — the real 5906 records
  (superpermutators GitHub; absent from urdvr's tree) are **accepted by
  `extract_certificate` as partial-ride certificates at V₇=10**
  (`cert5906_*.json`: K=18/Σ=8, K=20/Σ=10, K=24/Σ=14 — exactly as the ledger
  priced them sight unseen), and `recompiled_5906.txt` is a re-compiled,
  validated 5906. Our formalization provably expresses record-class words.
- Census (`enum_budget.py`/`enum_mixed.py`, cross-validated against Egan's
  KernelFinder, 223 = 223 at K ≤ 31): V₇=15 cost-3-only = 5×K=27, 21×K=29,
  48×K=30, 149×K=31 (+1581 at K=32/33); **no mixed-cost chains exist at
  penalty ≤ 16**; V₇=20 = 4 chains. Chain data: `chains_V15*.jsonl`,
  `chains_V20.jsonl`.

## Results so far (negatives are proofs unless marked)

- All 4 V₇=20 chains: structurally uncoverable (zero-candidate columns) ⇒
  **5904 is closed at penalty ≤ 16**.
- One K=29 chain: **UNSAT** (CaDiCaL + kissat agree — no exact cover at all).
- 662 further chains refuted structurally (zero-candidate columns).
- All 8 palindromic K ≤ 31 chains: **no 2-fold-symmetric cover** (`sym_sat.py`,
  cross-validated by Egan's PermutationChains) — Egan's 2SYMM method, the only
  one that ever produced a nonstandard n=7 record, cannot give 5905 from
  penalty ≤ 16 kernels.
- OPEN: the 5 K=27 chains (3 distinct up to reversal) and most K=30/31 —
  CDCL/MILP/DLX all stall (neither model nor refutation after hours); Egan's
  engine reaches 129/141 2-cycles before a reproducible crash (ASan hunt was
  left running).

## Next steps (from NOTES.md)

(a) fix PermutationChains' coverFirst crash; (b) multi-day CDCL per K=27 chain
— three UNSATs would close Σ=12; (c) sweep the 916 open K=32/33; (d) census at
penalty ≥ 17 (mixed-cost first appears there); (e) cube-and-conquer on the 12
skipped-orbit columns. Full state in `NOTES.md`; heavy logs and third-party
code (Egan tools, 5906 words) remain in the session scratchpad `cover7/`.
