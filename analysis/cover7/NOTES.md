# cover7 campaign state (session scratch — NOT a report)

## Proven-good pipeline
- chain7.py: chain -> instance (roots = RIDDEN orbits only; columns include
  skipped kernel orbits; disabled splices = kernel splices sourced in skipped
  orbits). Positive control: reproduces gain1.build_instance(7) exactly.
- Compile path VALIDATED end-to-end twice:
  - standard chain -> 5907 (candidate_5907_std.txt, cargo-validated, census 4182/853/4)
  - real 5906 (Egan/Vane nsk666466646646664666) extracted as K=18 Sigma=8
    V7=10 chain cert with 8 disabled splices -> recompiled by our
    compile_certificate -> 5906, cargo-validated (recompiled_5906.txt).
- 5906s downloaded from superpermutators/superperm GitHub (5906s/); several
  extract cleanly: K=18/S=8 (124 rows), K=20/S=10 (122 rows), K=24/S=14 (118
  rows) — all V7=10. PROOF that partial-ride chain covers exist at n=7.

## Chain census (complete, machine-verified)
- V=15 chains, cost-3 only, pen=Sigma: NONE below Sigma=12.
  Sigma<=16 complete: 5 x (K=27,S=12), 21 x (K=29,S=14), 40 x (K=30,S=15),
  141 x (K=31,S=16)  -> chains_V15_s14.jsonl / chains_V15_s16.jsonl.
- Mixed-cost (4/5 hops, pen=S+5f4+10f5): NONE with pen<=16 beyond the pure set
  (complete enum_mixed.py runs at PMAX=10/12/14/16).
- V=20 (K=46..61) and high-K V=15: REFUTED (zero-candidate columns).
- 47 of 181 tier-2 (K=30/31) refuted by unit propagation; 130 open.
- Palindromic chains (Egan-2SYMM candidates): s14 idx 2 (K=27), 18 (K=29);
  s16 idx 84,104,110,119,181,189 (K=31).

## Verdicts so far
- s14 idx 5 (K=29): UNSAT in 33.5s (no exact cover at all).
- K=27 chains: SAT undecided after 2h+ each (CaDiCaL, unphased).
- Egan's own data point: of 1.57M palindromic V>=10 kernels, only 7 yielded
  (symmetric) covers, all at V=10 — feasible chains are RARE; fruitful
  kernels' patterns look exactly like ours (6s and 4s).

## Running
- triage workers (600s/chain, some with 5906-cert phase bias) over 153 open
  chains -> triage_*.log
- sym_sat.py (2-fold symmetry, half-space SAT) on palindromic s14:2, s14:18
- chain 0 phased 2h; chain 4 unphased 2h (legacy)

## Session updates (running log)
- Census EXTENDED and cross-validated against Egan's KernelFinder: 223 chains
  at K<=31 (terminal partial rides included — my initial enum missed 16),
  byte-identical pattern sets. K<=33 via KernelFinder: +392 K=32, +1189 K=33
  (35 loop-revisiting patterns excluded — outside certificate grammar).
- kissat installed; kissat_chain.py reproduces chain-5 UNSAT (49s).
- All 8 palindromic V=15 chains (K<=31): NO 2-fold symmetric cover
  (sym_sat.py UNSAT; cross-validated by PermutationChains symmPairs
  'unviable' on chain 2). Egan's 2SYMM method cannot reach 5905 from these.
- PermutationChains asym coverFirst on chain 0: DXL reached minColsLeft=0 —
  EXACT COVERS OF CHAIN 0 EXIST (at least of the reduced/cover-first set);
  process then died silently (~15:18) — possible crash at searchPC handoff,
  reproducing with asym_c0b.
- Triage: K=27 chains 1,2,3 UNDECIDED at 900s (CaDiCaL, 5906-phase bias).

- PermutationChains coverFirst mode CRASHES silently mid-search on our nsk
  kernels (reproduced twice: asym_c0 died after minColsLeft=0, asym_c2 died
  at PCsolSize=129/141). Plain mode (no coverFirst — the mode Egan actually
  used for the 5906s) relaunched on all 5 K=27 chains: plain_c0..4.log,
  partials reach 114-122/141 within minutes. Solution files would be
  egan/7_5905_<pattern>.txt (spLen=5905 — the tool itself computes the
  length from the kernel score; any Found SOLUTION = a 5905 word).
- Tier-3 screen: 611/1581 K=32/33 chains refuted (zero-column), 916 open,
  margins still wide (K=33: ~490 loops for R=108).

## HANDOFF (processes that survive this session — all nohup'd)
- egan/plain_c0..4.log: PermutationChains plain mode, all 5 K=27 chains.
  A "Found SOLUTION" line + a file egan/7_5905_<pattern>.txt = THE RECORD:
  validate with `cargo run --release -- validate -n 7 --file <file> --complete`
  (each line of the file is one 5905 word).
- egan/asan_c2.log: ASan build hunting the coverFirst crash (coverFirst
  reached deeper partials than plain mode before crashing — fixing it is
  the best next lever).
- milp_c1_long.log: HiGHS 3h feasibility on chain 1 (UNSAT would refute).
- triage_chains_V15_s14_0.log: CaDiCaL phased on chain 0 (2h limit,
  effectively unbounded inside one solve call).
- janitor.sh kills over-budget sat_chain triage jobs (may itself die with
  the session — check `ps aux | grep sat_chain` manually).

## Verdict summary as of 15:45
- chain s14:5 (K=29): NO exact cover (CaDiCaL 33s + kissat 49s, UNSAT at
  0 cuts) — refuted.
- K=27 chains 0-3, K=29 chains 9-11,15-17: UNDECIDED at 900s CaDiCaL.
- All 8 palindromic K<=31 chains: no symmetric cover (proven, double-checked
  with Egan's own engine).
- Zero-column/propagation refutations: all 4 V20 chains, high-K V15,
  47/181 (K=30/31), 611/1581 (K=32/33).

## Tools
- sat_chain.py (CaDiCaL exact-cover + lazy rootless-cycle cuts; --phase-cert)
- sym_sat.py (symmetric classes; forbidden pairs sharing loop/column)
- dlx7.c/solve_dlx.py (C DLX + forest + pref rows; good for seeded finds)
- gain1c_param.c (LNS greedy; weak on these instances)
- milp_chain.py (HiGHS; too slow here)
- analyze_chain.py (zero-column refutation + unit propagation)
- enum_budget.py / enum_mixed.py (complete chain censuses)
