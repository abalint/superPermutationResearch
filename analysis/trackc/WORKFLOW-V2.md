# Track C v2 workflow — the full pipeline, end to end

Spec: `docs/TRACKC2-DESIGN.md` (binding; deviations get recorded there).
Results ledger for the session: `analysis/trackc/RESULTS-s19.md`.
This file is the operational runbook: every stage, its command, where outputs
land, and what gate must pass before the next stage.

## Stage 0 — build + correctness gates (Mac)

```bash
cd analysis/trackc && make          # cc -O2 -Wall -Wextra dlx7g.c -o dlx7g -lm
make gates                          # v1 row parity + n6std baseline
# v2 column parity (byte-identical Python <-> C, blocks everything downstream):
python3 colfeat.py --parity-dump runs/parity_col_py.txt
./dlx7g data/trackc/instances/n6std.txt --dump-col-features data/trackc/parity/cover_rows.txt > runs/v2/parity_col_c.txt
diff runs/v2/parity_col_c.txt runs/parity_col_py.txt   # must be empty
# flagless regression pins (bit-exact, any drift = build failure):
#   n6std blind: SOLVED 25 rows @ 21,627 nodes
#   chain 26 blind: EXHAUSTED @ 8,548,527 nodes
```

## Stage 1 — instance export (Mac)

Chain index = line index in `analysis/farm/farm_chains.jsonl`, index-aligned
with `analysis/cover7/results_n7_merged.csv` (verdict column: STRUCTURAL /
UNSAT / OPEN). Train/eval split is LOCKED in the design §3 — eval chains
{5,25,26,43,72,73,74,76} are never trained on.

```bash
python3 analysis/trackc/solve_guided.py --chains analysis/farm/farm_chains.jsonl --index <i> ...
# or bulk: instances.py machinery; exports are byte-checked against
# analysis/trackc/runs/census/instances/wl_NNN.txt where those exist.
```

## Stage 2 — generation sweep (PC farm, `ssh transcribe`)

Farm conventions (hard rules): `analysis/cover7/REMOTE-FARM.md`. Work only
under `F:\superpermFarm`; everything long-running via `detach.exe` (which
cannot launch powershell directly — go through `cmd.exe /c tc2runw.bat`);
never touch python processes or `F:\audioPrime`.

Scripts (committed in `analysis/farm/`): `tc2scale.ps1` (idempotent backfiller,
20 workers, done-markers — rerun to top up), `tc2status.ps1`, `tc2stop.ps1`
(kills only its own recorded PIDs), `jobs.txt` / `evaljobs.txt` (run matrix).

```bash
scp analysis/trackc/dlx7g.c "transcribe:F:/superpermFarm/trackc2/"   # + rebuild via cl /O2
ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\trackc2\tc2scale.ps1"
ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\trackc2\tc2status.ps1"
```

BUILD GATE on the PC (design §8 risk 4): Windows binary blind on chain 26 must
print EXHAUSTED nodes=8548527 before any ledger row is trusted.

Outputs: subtree logs `F:\superpermFarm\trackc2\gen\<chain>_<runtag>.jsonl`
(runtags `blind`, `e15s1`, `e15s2`, ...), ledger `trackc2\ledger.csv`, stderr
`trackc2\logs\`. Volume note: ~215 MB per 600 s open-chain run (~35 GB per full
sweep) — mine on the PC or gzip before pulling.

## Stage 3 — corpus mining (either side)

```bash
python3 analysis/trackc/mine_subtrees.py gen/*.jsonl --out data/trackc/coleffort_<tag>.jsonl
python3 analysis/trackc/mine_subtrees.py gen/*.jsonl --pairs data/trackc/colpairs_<tag>.jsonl  # v2.1 within-state pairs
```

## Stage 4 — training (Mac)

```bash
python3 ml/fit_col_effort.py --train data/trackc/coleffort_*.jsonl \
    --holdout <inst1,inst2> --name trackc2_<tag>        # regression mode
python3 ml/fit_col_effort.py --pairwise --train data/trackc/colpairs_*.jsonl ...  # v2.1
# exports ml/models/trackc2_<tag>.txt (trackc-cw1 10) + .json
```

Holdout is by instance; eval-chain logs are NEVER in --train. Offline metrics
(R², Spearman, pair acc) are diagnostic only — deployment decisions come from
G2v2/G1 search performance (design §7).

## Stage 5 — guided runs / gates

```bash
# guided engine, MRV band Δ:
./dlx7g <inst.txt> --col-weights ml/models/trackc2_<tag>.txt --col-delta 0|1
# full validated pipeline (any SAT must survive Rust validate):
python3 analysis/trackc/solve_guided.py <inst> --col-weights ... --col-delta ...
```

- G2v2 (primary): blind vs guided nodes-to-exhaust on the 8 eval chains; blind
  baselines are recorded in design §7. GO = median ≥1.3× on the six non-trivial
  chains, no >2× blowup.
- G1/G1b: n7std / c5906 K=18, 60-min budget, cross-instance by construction.
- G3 (on GO): guided pass-2 over the 138 OPEN chains on the farm; any new
  EXHAUSTED = census closure; any SAT → validate → world record check.

## Session discipline

Every stage that changes numbers appends to `docs/JOURNAL.md`; design
deviations go in `docs/TRACKC2-DESIGN.md`; gate results in
`analysis/trackc/RESULTS-s19.md`. Commit at stage boundaries.
