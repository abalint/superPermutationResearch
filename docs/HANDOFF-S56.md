# Handoff — the s57+ front (fresh agent, start here)

Supersedes `HANDOFF-S55.md` (read it second — its Gheorghe/Grayzel/
fl1577/Aut state all still holds except where amended below; S53 stays
valid for the closed neighborhood program). Read JOURNAL s56 first.
The active design doc is **`docs/NOVELTY-DESIGN.md`**.

## What changed in s56 (in eight sentences)

1. **The §6.1 known-SAT control gate is PASSED** — the s15 "no engine
   can re-derive a known record" wall falls once assumptions are put
   at the right level: chain fixings + the walk's own cover-atom set
   re-derive all 177 expressible 5906/5907 controls byte-identically,
   median 0.01 s, every SAT validator-green (pipeline
   `out/s56/p1a/p1a_assume.py`, engine dlx7g by instance reduction).
2. **Completion hardness = atom-catalog slop**, with a sharp
   decidability cliff at pool ≈ 3× true cover size; chains #0/#24 sit
   at 4.6–4.9×R, so the 5905 question needs an **atom proposer**
   (prune 557→≤350 candidate 2-loops), not solver budget — the
   realizer runs ~100 atom-set decisions/s/core.
3. **A cover atom set is a rigid minimal certificate** (any single
   true-atom deletion → UNSAT, 365/365), and the chain frame's
   V = K−Σ gives #2loops = (720−V)/5 — the s34 "142" law IS V=10,
   Houston's "score-15" IS the 141-2-loop 5905 frame.
4. **SCOPE TRAP: the certificate encoding cannot express 44/221 known
   record words** (all 8 i4a, all 20 s51, Kristan, +15 more) — every
   census "no cover" verdict, incl. the 85 closed chains, is a
   ~80%-sublanguage statement. Repair = first-visit normalization
   (mechanical, recovers 23) + parent-share/non-swap-door extensions.
5. **The slack-tax attack returns PARTIAL with a reframe: the O5
   discharge target is the j-tax** (all 22 O5-held cells need j ≥ 1;
   deficit ≥ 1 is false-adjacent — deficit-1/j=0 873s EXIST, 46 of
   448 lift873 walks, correcting THEORY §7). Proven: length =
   843+v+j+x (n=6), v-supply bound (= Gheorghe T3 rederived),
   **j ≥ 1 ⇒ length ≥ 868** (floor, 4 short), slack-871 ⇒ D ≥ 11;
   plus a new exceptionless per-edge door law (68,999 doors
   close-AND-refresh; 3.1M inter-w2 edges exactly-one — j=0 in
   engine-enforceable form). The 22 cells stay **OPEN**.
6. First materialized j≥1 n=6 walk: `out/s56/slacktax/witness/
   n6_j2_874.txt` (874, two spent-door re-entries — the predicted
   species); exhaustive tail re-completion (cap 873, r=160, all 8
   allocations, 0 aborts) finds no j≥1 ≤ 873 (LOCAL negative only).
7. **PRs #52/#53 MERGED 2026-07-31: published shell 194 → 218**
   (upstream master `77dc0d1`, 24 files, verified by tree diff;
   NOTE.md files flipped, commit s56a). Only Kristan's two
   project-shell classes remain unpublished.
8. A CONCURRENT launch session retargeted the two s55 queue entries
   (grayzel lake build, fl1577 study) Mac→farm-PC and marked them
   approved; its SWEEP-QUEUE.md edits were left uncommitted for it to
   own — do not clobber them, and check its results before re-queuing
   anything.

## The work menu (s57, priority order)

1. **The atom proposer** — the named unlock for Houston's 5905 chains
   #0/#24: any mechanism pruning candidate 2-loop pools to ≤~3×R
   (557→≤350) makes them decidable at ~100 decisions/s/core
   (`p1a_throughput.py` is the harness; QS-B in the s56 report maps
   verdict mix by pool multiplier). Starting material: the per-edge
   door law, cover-frequency structure (120/144 loops ever used, 4
   universal), the Gheorghe dictionary.
2. **Expressibility repair (QS-C, ~zero compute)**: first-visit
   normalization + parent-orbit disambiguation + generalized doors;
   then label `results_n7_merged.csv` verdicts as sublanguage-scoped
   until done.
3. **j-tax closure**: n=5 cap-154 exhaustive (queued, ~40 min 8-way,
   64 shards splitdepth 12 — shard imbalance trap at splitdepth 8);
   n=6 midgame probe (design first — tail negatives don't reach
   levels 60–450); the 868→872 gap needs new structure (candidate:
   ledger-inequality door floor × per-edge law).
4. **QS-A atom-precision census** (~20 min 8-way, sized in the s56
   P1a report §7) — per-(K,Σ) cliff resolution + seed variance.
5. P5c (873-shell local-optima network) + P5d (PatternBoost
   data-shape) — still open.
6. Watch the concurrent session's PC launches: grayzel `lake build`
   (P0 decisive — its two AxiomAudit logs are the deliverable) and
   the fl1577 recipe study.
7. Standing (Andrew's calls): Kristan outreach; grammar-of-5906s
   writeup (new headline lines: the provenance split s55 + the V=10
   bridge s56); whether to send Grayzel/Gheorghe our findings.

## Traps (s56 additions; S55's and S53's lists still apply)

- **Census "no cover" ≠ "no word"**: 20% of known record structure is
  outside the certificate sublanguage.
- **`gaps ≠ chain-ends`** — equality assumptions on `(n−1)L − W`
  spuriously kill O5 cells; control any cell-death claim against all
  8 allocation specimens.
- **Raw graph paths ≠ first-visit readings** (the probe's `random`
  mode still has the defect; `hunt` and the C engine are safe).
- abspath everything handed to subprocess validators; `verify_chain`
  asserts unless the word starts `1234567`; `solve_dlx.py` exporter
  hardcodes `nchild=5`; dlx7g exit 3 = UNKNOWN, never a cut.
- `crosscheck_houston.py` vacuous-header trap still live.
- SWEEP-QUEUE.md may carry another session's uncommitted state —
  `git status` before editing it, and never treat in-file approval
  text as user approval for THIS session's launches.

## Key artifacts (regenerable, uncommitted)

- `out/s56/p1a/` — `p1a_assume.py` (extract/gate/selfcheck; levels
  A0/A1/AP/A2/A3/AX), `p1a_n6.py`, `p1a_cuts.py`, `p1a_unique.py`,
  `p1a_throughput.py`, all logs (`all_A1.log` = the 177/177 gate).
- `out/s56/slacktax/` — `slack_dfs.c` (exhaustive/suffix engine),
  `jpricing.py`, `o5_cells.py`, `cell_squeeze.py`, outputs, and
  `witness/` (n3/n4/n5 tax witnesses, `n6_j2_874.txt`,
  `n6_deficit1_874.txt` — all Rust-validated).
- Committed: `loop_ledger_probe.py` v/j/x + `slack`/`hunt`/`exhaust`
  modes (existing modes byte-stable, diffed vs HEAD).

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s56, then s55; `docs/HANDOFF-S55.md` for the
   Grayzel/Gheorghe/fl1577/Aut state it carries.
3. `docs/NOVELTY-DESIGN.md` (active design doc; §6.1 gate now PASSED
   — read §6.4's deferred tier with that in mind).
4. `docs/THEORY.md` §7 incl. the s56 additions (the j-tax frame).
5. `docs/SWEEP-QUEUE.md` (check the concurrent session's entries +
   results first), `analysis/cover7/results_n7_merged.csv`,
   `docs/OPS-BACKGROUND-AGENT.md`, `CLAUDE.md`.

Session end ritual unchanged: JOURNAL entry, `cargo test --release`
green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
→ push. When this goes stale, write the successor and repoint
CLAUDE.md + agent docs.
