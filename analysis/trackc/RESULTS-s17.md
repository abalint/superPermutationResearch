# Track C v1 — session 17 gate results (2026-07-27)

Spec: `docs/TRACKC-DESIGN.md`. Code: this directory + `analysis/trackc/instances.py`,
`replay.py`, `ml/fit_cover_rank.py`. All runs on the Mac (8 logical cores), engine
`dlx7g` built `cc -O2`.

## Corpus

| source | certs extracted | decisions | (pos,neg) pairs |
|---|---|---|---|
| n=6 records (296 words) | 296/296 | 7,400 | 17,690 |
| n=7 5907 (standard K=5) | 3/3 | 414 | 1,635 |
| n=7 5906 (K=18/20/24) | 11/11 | 1,336 | 2,098 |
| total | 310 | 9,150 | 21,423 |

## G0 — correctness / parity: PASS

- Python↔C feature parity: `--dump-features` diff vs `parity_py.txt` **byte-clean**
  (25 nodes, 89 candidate lines, pre-cover timing).
- Blind engine on n6std: 25-row rooted cover, 21,627 nodes / 0.008 s → compiles to a
  Rust-validated **872**. Deterministic across reruns.

## Training (holdout per design §4)

| model | train | held-out pair acc | learnable-only | node top-1 |
|---|---|---|---|---|
| A (n6 + 5906) | .541 | .540 | .606 | .680 |
| B (n6 + 5907) | .546 | .545 | .609 | .621 |
| N6 (n6 only) | .529 | .499 | .568 | .637 |

Cross-n transfer (N6, zero n=7 training): pair acc **.746** on 5907, .662 on 5906
(random = .511). Findings: `min_child_sz_log` has zero within-node variance under
MRV (the chosen column is the global min and a child of every candidate) — dead
feature; `grounds_pending` (the thesis feature) is weak and slightly negative;
dominant signal is `mean_child_sz_log` **−0.84** (prefer rows whose children are
scarce columns).

## Learned ordering works where the instance is within reach (n6std, known-SAT)

| ordering | nodes to first cover |
|---|---|
| blind (row-id order) | 21,627 |
| model A | 2,835 (7.6×) |
| model B | **961 (22.5×)** |
| model N6 | 2,836 |

(n=6 covers are in-sample for all three models — mechanism evidence, not a holdout claim.)

## G1 / G1b — held-out known-SAT gates: NO-GO at 60 min

Protocol: 60-min budget; blind = no weights (det + ε=1.0 seeds 1,2 with 200M-node
restarts); guided = held-out model (det + ε=0.05/0.15 restarts).

| instance | run | verdict | nodes | maxdepth (target) |
|---|---|---|---|---|
| n7std (690×4440, R=138) | blind det / s1 / s2 | TIMEOUT | 777M / 713M / 708M | 114 / 102 / 100 (138) |
| n7std | guided A det / e05 / e15 | TIMEOUT | 631M / 600M / 599M | 112 / 109 / 108 |
| c5906 K=18 (R=124) | blind det / s1 / s2 | TIMEOUT | 595M / 574M / 585M | 93 / 94 / 91 (124) |
| c5906 K=18 | guided B det / e05 / e15 | TIMEOUT | 792M / 789M / 794M | 98 / 95 / 101 |

No cover found by any run; max-depth differences are noise-level. The v1 linear
teacher-forced ranker does not convert its offline transfer signal into
cover-finding at n=7 scale. G3 (K=27 record attack) not triggered per §7.

## G2 — UNSAT economy: null by construction (and a bonus)

With MRV fixed, row order permutes the DFS but the exhaustion tree is the same
node set — verified byte-identical node counts blind vs guided:
chain 5 (K=29) 60,037,516 nodes both (484 s vs 512 s); chain 26 (K=30) 8,548,527
both (64 s vs 81 s). Guided feature overhead ≈ 6–28 %.

Bonus: these are fresh, third-engine (DLX) confirmations of the CaDiCaL+Egan
UNSAT verdicts for farm chains 5 and 26 — and dlx7g exhausts K=29/30 chains in
1–8 min locally, which motivated `census_sweep.sh` (4 workers, 30-min caps,
results land in `runs/census/results.csv`, resumable).

## Verdict and v2 levers

Infrastructure GO (corpus, parity-clean engine, trainer all gated); evaluator
NO-GO for the n=7 cover hunt at v1. The s8 lesson reproduces at certificate
level: offline ranking metrics, even with real cross-n transfer, do not buy
search wins by themselves. Concretely: top-1 ≈ 0.62–0.68 per node compounds to
essentially zero probability of steering a 118–138-deep all-correct descent.

v2 levers, in rough order of expected value:
1. **Learned column choice** — the only lever that shrinks the tree itself
   (helps UNSAT and SAT; G2 proved row order cannot).
2. **Dead-end mining / off-path training** — v1 is teacher-forced (on-path
   states only); the engine already logs dead ends.
3. **Value-based restarts** — score partial states (not rows) and use it to
   drive restart/backjump policy instead of blind node caps.
4. **CDCL deployment** — feed model scores into `sat_chain.py --phase-cert`-style
   phase/branching biasing (hook exists; CaDiCaL is the strongest UNSAT engine here).
5. Nonlinear model (MLP) — cheap to try once any of 1–3 changes the regime.
