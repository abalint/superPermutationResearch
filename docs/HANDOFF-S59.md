# Handoff — the s60+ front (fresh agent, start here)

Supersedes `HANDOFF-S57.md` (read it second — its state holds except
where amended below; S56 for P1a/slack-tax detail, S55 for Gheorghe/
fl1577/Aut background). Read JOURNAL s59 first. The active design doc
is **`docs/NOVELTY-DESIGN.md`**, now read through THREE corrections:
the §6.1 pool-precision milestone is retired (s57), the walk-order
PREFIX milestone that replaced it is refuted (s59), and §6.4's
realizer-throughput arithmetic must use the measured QS-B curve
(s59), not "~100 decisions/s".

## What changed in s59 (in six sentences)

1. **The walk-order prefix proposer is REFUTED as a route**: 18,750
   legal walk-order prefixes on three known-SAT control chains (cap
   ruled out as confounder by oracle calibration first) produced 0
   SAT for both the scored proposer and random baseline — because a
   walk-order prefix has **zero error tolerance** (1 wrong row of 30:
   SAT 0.583 → 0.000, ≥75% provably dead; required per-step accuracy
   ≈ 1.0 vs measured 0.20–0.39 even oracle-guided).
2. That is the same rigid-certificate fact that killed pool precision
   in s57 — so **assumption-guessing devices are retired as a class**;
   the surviving directions on #0/#24 are **row-shrink** (pairwise cut
   store — queued; no-good harvesting from the proposer's ~31k sound
   prefix refutations) and **prefix retrieval** (relabel-conjugacy
   lookup against the 1,425 known group0 cover rows), not guessing.
3. **The s56 "3×R cliff" was a BUDGET artifact, not a determinism
   artifact**: at a common 120 s budget, ε=0 matches or beats ε=0.15
   on every differing cell (one s56 "unreachable" cell was 0.6M nodes
   short of its own solution; on another, restarts LOSE a solution
   ε=0 finds in 86.7 s). Corrected band: lastSAT 2.69–3.50×R; all six
   full-pool cells stay UNKNOWN in both lanes.
4. **s57's absolute-size claim is CONFIRMED lane-robustly**: same
   chain, same 4.39×R — 1,425 rows SAT in both lanes, 2,734 rows
   UNKNOWN in both; a lower-multiplier 3.42×R/2,154-row instance is
   UNKNOWN. (The decoy gradient itself can never show this: rows ≈
   5.2×pool, pearson 0.990.)
5. **QS-B was never actually run in s56** — now measured (1,160
   samples, both lanes, identical): ~200 decisions/s at ≤3×R →
   4.9–5.8/s at 4.0×R → 0.21–0.23/s at 4.8×R (~900× collapse), so
   §6.4's "cover master provably realizable IF ≤3×R" fails at the
   open chains' 4.6–4.9×R at any achieved precision.
6. #0/#24 got 4 more witness-lane probes (2×560 s each, prefix DFS):
   honest UNKNOWN, explicitly weaker evidence than s57's probes; a
   deterministic 1-core long run is now at least as promising as the
   16-seed witness lane in s57 REPORT §9 (still NOT recommended).

Also this session: ROADMAP.md carries the a(6)=872 reckoning (n=6
solved → theory testbed; validation ladder = n=7 5905 evidence, shell
growth, n≥8 Egan−1); two SWEEP-QUEUE entries await Andrew's approval.

## The work menu (s60, priority order)

1. **Pairwise cut store #0/#24** (SWEEP-QUEUE entry, `approved: NO`,
   ~9 core-hours farm) — the sound row-shrink route toward ≲1500
   rows. Cheap local complement: harvest no-goods from
   `out/s59/prefix/prefix_propose.py --check-from 6 --step-cap 0.2`
   with greedy prefix minimization on every rc 2.
2. **A0 gate re-run** at 120 s, both lanes (~90 min, local): the s56
   "0/6 from chain alone" baseline is the last uncorrected 15 s
   artifact — do not cite it until this runs.
3. **Prefix retrieval probe** (cheap, local): are any open-chain rows
   relabel-conjugate to the 1,425 rows appearing in the 131 known
   group0 covers? Lookup, not guessing — the only surviving prefix
   idea (`out/s59/prefix/REPORT.md` §9.4).
4. **Extended-census Σ15–16 sweep** (SWEEP-QUEUE entry, `approved:
   NO`, ~2.7 core-hours farm).
5. **NOVELTY-DESIGN §6.0/§6.4 edits** per `out/s59/cliff/REPORT.md`
   §8 — fold the measured QS-B curve and the two milestone
   retirements into the design doc proper.
6. j-tax closure (unchanged from S56 menu item 3): n=5 cap-154
   exhaustive (queued), n=6 midgame probe design, the 868→872 gap.
7. Andrew's calls: the two queue approvals, Grayzel/Gheorghe contact,
   Kristan outreach, grammar writeup.

## Traps (s59 additions; S57's list applies EXCEPT trap (d), corrected)

- **s57 trap (d) is superseded**: s56 hardness numbers were 15 s
  BUDGET artifacts. Report both lanes at a stated budget; ε>0 is not
  automatically better and can lose solutions ε=0 finds. Never say
  "regenerate with restarts" as if restarts were the fix.
- The **A0 "0/6"** (JOURNAL s56 §1) is an uncorrected budget
  artifact — not citable until re-run (s60 item 2).
- **Assumption-guessing is dead as a class** on rigid certificates
  (365/365 single-deletion UNSAT): neither pools (s57) nor prefixes
  (s59) can be gated by guessing ~30 independent choices.
- **Oracle-calibrate the completion cap before gating**: m=20 at cap
  ≤5 s is a dead cell (0% of known-TRUE prefixes complete) — a gate
  number from an uncalibrated cell is uninformative by construction.
- NOVELTY-DESIGN §6.4's "~100 decisions/s/core" was 3 cells at ≤2×R;
  the measured curve collapses ~900× by 4.8×R — redo any realizer
  arithmetic with `out/s59/cliff/qsb_summary.json`.
- dlx7g rc 2 under ε>0 may be sound (source-level argument, s59) —
  but keep recording it as UNKNOWN until independently audited.
- Per-chain paneling, lane separation, census-family scoping,
  first-error labels, SWEEP-QUEUE approval hygiene: all S57/S56
  traps still apply as written (minus (d) above).

## Key artifacts (regenerable, uncommitted)

- `out/s59/prefix/` — prefixlib.py, prefix_propose.py (feedback DFS),
  gate.py/gate2.py, farm_run.py, build_positives.py, corrupt.py,
  overlap.py, rankprobe.py, depthprobe.py, full JSONL ledgers,
  REPORT.md (orchestrator-filed; §9 = recommendations, §6 = the
  zero-error-tolerance mechanism).
- `out/s59/cliff/` — geninst.py, run_gradient.py, stage3.py, qsb.py,
  trials.tsv (142 runs), qsb_trials.tsv (1,160), qsb_summary.json,
  instances.json (36/36 byte-identical to s56), inst/, REPORT.md
  (§7 = queue-entry draft, §8 = recommended NOVELTY-DESIGN edit).
- `out/s57/proposer/`, `out/s57/express/` — still present, still the
  reference implementations (dlxrun.py remains the mandatory runner).
- On the farm PC: Grayzel run `D:\superpermFarm\grayzel\runs\g3`
  (the a(6)=872 evidence; copy home before any farm cleanup) and the
  fl1577 study `out/fl1577_pc_study/` (shipped home, committed s58).

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s59, s58, s57; `docs/HANDOFF-S57.md` for what it
   carries from s56/s55.
3. `out/s59/prefix/REPORT.md` §6/§9 and `out/s59/cliff/REPORT.md`
   (the two current primary sources).
4. `docs/NOVELTY-DESIGN.md` (apply the three corrections at top of
   this file), `docs/ROADMAP.md` (the 2026-07-31 dated section).
5. `docs/SWEEP-QUEUE.md` (two pending `approved: NO` entries),
   `docs/THEORY.md` §7, `docs/OPS-BACKGROUND-AGENT.md`, `CLAUDE.md`.

Session end ritual unchanged: JOURNAL entry, `cargo test --release`
green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
→ push. When this goes stale, write the successor and repoint
CLAUDE.md + agent docs.
