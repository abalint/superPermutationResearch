# Track C v2 — session 19 build + gate results (2026-07-28)

Spec: `docs/TRACKC2-DESIGN.md` (v2 column choice + v2.1 pairwise addendum).
Ops conventions born this session: `docs/OPERATIONS.md`. Pipeline runbook:
`analysis/trackc/WORKFLOW-V2.md`. All Mac runs `cc -O2`; farm runs MSVC `cl /O2`.

## Build (all committed s19)

- Engine `dlx7g.c`: `--col-weights/--col-delta` (choice within the MRV band),
  `--col-epsilon/--col-seed`, `--log-subtrees` (dead-end mining, exact labels at
  frame pop), `--dump-col-features`, `--mrv-stats`; v2.1 adds `shash` (Zobrist
  over the placed-row set) and `--probe-rate/--probe-cap` (counterfactual
  same-state column probes via force_col re-entry, isolated counters).
- Python: `colfeat.py` (10-feature extractor over the v1 replay machinery),
  `mine_subtrees.py` (+`--pairs`), `ml/fit_col_effort.py` (ridge regression +
  `--pairwise` IRLS RankNet, standardization folded into `trackc-cw1` export),
  `solve_guided.py` col-flag passthrough.

## G0 — correctness / parity: PASS

- Column parity Python↔C: **byte-clean** (25 nodes, 1,300 lines, all active
  columns per node).
- Flagless engine bit-identical to v1: n6std SOLVED 25 rows @ **21,627** nodes;
  chain 26 EXHAUSTED @ **8,548,527**. Zero-weights Δ=0 identical (tie-break =
  MRV). v1 row parity still clean. Windows build reproduces chain 26 exactly
  (design §8 risk 4 gate) — and chain 25 blind on the farm exactly matched the
  Mac census run (199,733,787), a second cross-platform bit-repro.
- `--log-subtrees` without probes: byte-identical records to pre-v2.1 modulo
  the added `shash` key; probes leave main `nodes` untouched (verified equal
  with probes on/off, chain 26).
- Guided n6std through the full pipeline (smoke weights): Rust-validated
  **872** at both Δ=0 and Δ=1. [G0 with the final model: see G2v2 section.]

## M0 — MRV tie multiplicity (decides Δ): ties are the COMMON case

62–74 % of decision nodes have ≥2 MRV-tied columns (n6std 61.8 %, chain5
73.2 %, chain26 71.8 %, n7std-capped 73.9 %); median |C*₀| 2–3, |C*₁| 4–10.
Δ=0 is a live lever. Zero-learning mechanism datum: Δ=1 with all-zero weights
finds the n6std cover in 2,044 vs 21,627 nodes (10.6×).

## Smoke run — honest negative that reshaped the method

Single-instance-dominated smoke corpus (99.8 % chain 84, truncated tree) →
regression model made eval chain 26 **2.70× worse** at Δ=0, 8.83× at Δ=1
(verdicts unchanged; loop mechanics validated end-to-end). Diagnosis: plain
effort regression conflates state hardness with choice quality. Response:
v2.1 within-state pairwise data (§3b of the design).

## M1 — pairwise viability (local, chains 26/82): probes win

- Within-run transpositions are structurally impossible (DLX sibling row-sets
  are disjoint — a run never revisits a state); organic pairs exist only
  across seeds: 0–56k pairs/10⁶ records, ~3–5k pairs/min.
- Probes (p=0.02, cap 20k): **375–393k pairs/10⁶ records, 150–177k pairs/min**,
  overhead 1.41–1.63×, main search node-identical.
- Local 2-chain pairwise fit: held-out pair acc .746 overall — but **.532 on
  equal-size (Δ=0-relevant) pairs**: on this tiny corpus the model mostly
  rediscovers MRV. The multi-chain corpus is the real test.

## G2v2 — blind baselines (farm, complete) and gate

Corpus (local Mac, farm down): 16 train chains × 2 ε-seeds, probes 0.02/20k —
2.92G main nodes, 105.4M records, 40.1M pairs mined, capped to 2.08M pairs /
2.0M records. Training (holdout chain160 + chain7, 300k held-out pairs):
**pw1** pairwise acc .7366 held-out — but **.5217 on equal-size pairs**
(n=78k; the Δ=0-relevant number — the within-band signal is ~nil at
16-instance scale); **reg1** regression R² +.614, ρ +.653. Both dominated by
`sz_log` (+1.57σ): the models mostly rediscover MRV.

G0 with pw1: n6std Rust-validated **872** at Δ=0 (20,433 nodes) and Δ=1
(**77 nodes** vs 21,627 blind — the band + learning is dramatic on the SAT
side at n=6). All 19 eval runs EXHAUSTED, zero SAT, zero caps:

| chain | K | blind nodes | pw1 Δ=0 | pw1 Δ=1 | reg1 Δ=0 |
|---|---|---|---|---|---|
| 5 | 29 | 60,037,516 | 96,418,644 (0.62×) | 103,133,961 (0.58×) | — |
| 25 | 29 | 199,733,787 | 96,478,318 (2.07×) | 103,115,674 (1.94×) | — |
| 26 | 30 | 8,548,527 | 10,882,825 (0.79×) | 12,385,270 (0.69×) | 12,382,372 (0.69×) |
| 43 | 30 | 4 | 4 | 4 | — |
| 72 | 30 | 5 | 4 | 4 | — |
| 73 | 30 | 23,257,326 | 10,883,265 (2.14×) | 12,385,772 (1.88×) | — |
| 74 | 30 | 1,450,087 | 1,557,546 (0.93×) | 1,871,908 (0.77×) | 1,858,686 (0.78×) |
| 76 | 31 | 12,030,955 | 5,479,218 (2.20×) | 5,289,245 (2.27×) | 6,089,472 (1.98×) |

**Verdict: pw1 Δ=0 GO on the letter of the gate** — median 1.501× over the
six non-trivial chains, worst blowup 1.61× (chain 5) < 2×. Δ=1: median
1.326×, worst 1.72× — strictly dominated by Δ=0, not deployed. reg1 weaker
on all three spot checks, as the smoke run predicted.

**The finding that matters more than the median — K-class collapse.** Under
the learned policy, node counts converge to K-determined values: 5 and 25
(both K=29) exhaust at 96,418,644 / 96,478,318 (Δ=0); 26 and 73 (both K=30)
at 10,882,825 / 10,883,265 — while blind those pairs differ 3.3× and 2.7×.
The learned column order is near-instance-independent: it CANONICALIZES the
DFS per K-class rather than exploiting per-instance structure. The 2.1× wins
are the expensive member of each K-pair being pulled down to the K-typical
size; the losses are lucky-blind instances pulled up to it. Consistent with
equal-size pair acc ≈ .52: there is (as yet) no within-band per-instance
signal, but there IS a stable, variance-collapsing canonical order.

**Deployment implication:** the honest mode is a PORTFOLIO — run blind and
guided-Δ0 side by side per chain, take the first EXHAUSTED. On the eval set
that portfolio yields min(blind, guided) everywhere: median 1.50×, worst
case exactly 1.0×, blowup impossible by construction. G3/pass-2 should be a
bounded trial in this mode (the 138 open chains all have unknown blind tree
sizes — precisely the population where variance collapse to K-typical size
could convert TIMEOUTs into census closures).

## G1 / G1b / G3 (late s19, Mac) — no covers, no closures, and the number
that re-prices the whole gate

All runs with pw1 (n7std, c5906, chains 0/1 never in its corpus). G1: n7std
Δ=1 det/ε.05/ε.15 + Δ=0 det → 4× TIMEOUT at 424–502M nodes, maxdepth 103–109
of 138 (v1 blind refs: 708–777M, maxdepth ≤114). G1b: c5906 2× TIMEOUT,
maxdepth 85–87 of 124 (blind ref 93–94). The n6std 77-node SAT-side magic did
NOT transfer. G3 portfolio trial (chains 0,1,9,10,31,83; blind ∥ guided-Δ0,
30-min arms): 0/6 closures, all twelve arms TIMEOUT; guided explored only
0.30–0.76× blind's nodes in equal wall time and was the weaker portfolio arm
every time.

**Solo throughput probe (uncontended, 60 s, n7std): blind 495k nodes/s,
guided Δ=0 208k/s, Δ=1 194k/s — the learned column policy costs 2.4–2.6× per
node.** Re-scoring G2v2 in wall-clock: 1.50× median node reduction ÷ ~2.5×
per-node cost ≈ **0.6× — a NO-GO in the currency that actually matters.**
The v2 verdict therefore splits cleanly: the MECHANISM claim stands (learned
column choice shrinks the exhaustion tree — the thing v1 proved impossible
for rows), but the DEPLOYMENT fails on scoring overhead. Caveat for the
record: batch node counts under wall-clock caps are throughput-confounded
(runs were 6-way concurrent); the solo probe and all verdicts are clean, and
within-chain G3 comparisons shared identical contention.

Next lever, in order: (1) cut the 2.4× overhead (feature caching, incremental
column scores, scoring only at high-tie nodes) — at ≤1.2× overhead the
portfolio wins in wall-clock with the CURRENT model; (2) gen2 55-chain
retrain — does within-band signal appear at full diversity?; (3) only then
re-gate, in wall-clock.

## Infrastructure incident (documented for the record)

Sweep-1 (162 regression-generation runs, PC farm) reached 65/162 when the PC
lost the ability to create processes (CLR 80004005; SSH alive, F: reads hung).
Root cause (credible): worker bookkeeping slurped ~200 MB JSONL logs into
PowerShell arrays (`@(Get-Content).Count`) × 20 workers. Nothing of the user's
was touched; all state is on-disk and resumable (`tc2scale.ps1` after cleaning
any ERROR- ledger rows; fixed workers `tc2worker2.ps1` + fully-staged gen2
pairwise sweep via `tc2scale2.ps1`). Requires manual reboot. Lessons codified
in `docs/OPERATIONS.md`.

## Field news landed mid-session

urdvr/Hunter Lean-formalized lower bound: S(6) ≥ 869, S(7) ≥ 5888 —
n=6 window {869..872}, n=7 window [5888, 5906]. Details:
`../../extraDocs/2026-07-28-urdvr-lean-lower-bound.md`. A further claimed
(k−5)!-order term is in the author's verification; ~18 more at n=7 would moot
the 5905 record campaign (census-closure value of Track C is unaffected).

## Farm retrain (s19 final act) — the canonicalization verdict is confirmed

pw2 on the full gen2 corpus (6.0M pairs, 53 train instances, all K classes,
eval chains verified absent; holdout wl_011/032/085/106/196): held-out pair
acc .7271 overall — and **equal-size .5191 vs pw1's .5217**: 3.3× more
diversity moved the Δ=0-relevant number nowhere. Coefficient-level signature:
cos(pw1,pw2) = .9996, `sz_log` UP (+1.57→+1.71), and `static_sz_log` — the
only feature carrying per-instance structure — shrank 3× toward zero. Full
diversity converged the model HARDER onto MRV: K-class canonicalization is
what this feature set learns, full stop. reg2's R² jump (+.614→+.737) is
almost entirely the node-level depth anchor — no ranking content.

One crack worth keeping: an equal-size-ONLY refit reaches held-out **.5406**
(`min_child_load`-driven, clean train/test agreement) — genuine within-band
signal exists at ~4 pp, but it needs a separate tie-break head, not the joint
10-feature score (where `sz_log` swamps it).

**Decision: keep pw1 deployed; pw2/reg2 shipped as recorded artifacts. The
entire next-session budget goes to the 2.4× per-node scoring cost — the only
thing standing between the measured 1.50× node reduction and a wall-clock
win.**
