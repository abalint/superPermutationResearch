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

| chain | K | blind nodes | guided Δ=0 | guided Δ=1 |
|---|---|---|---|---|
| 5 | 29 | 60,037,516 | TBD | TBD |
| 25 | 29 | 199,733,787 | TBD | TBD |
| 26 | 30 | 8,548,527 | TBD | TBD |
| 43 | 30 | 4 (trivial) | — | — |
| 72 | 30 | 5 (trivial) | — | — |
| 73 | 30 | 23,257,326 | TBD | TBD |
| 74 | 30 | 1,450,087 | TBD | TBD |
| 76 | 31 | 12,030,955 | TBD | TBD |

**[PLACEHOLDER — local pipeline in flight: survey → probe generation (~16
train chains × 2 ε-seeds) → pairwise + regression training → guided eval.
GO = median ≥1.3× over the six non-trivial chains, no >2× blowup.]**

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
