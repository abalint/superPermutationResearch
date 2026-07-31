# Handoff — the s56+ front (fresh agent, start here)

Supersedes `HANDOFF-S53.md` (which stays valid for everything it says
about the closed neighborhood program — read it second). Read JOURNAL
s55 (P0 both halves + P5a/P5b), then s54 (the cover-algebra amendment
and the §6.1 three-valued contract), then s53/s52b via HANDOFF-S53.
The active design doc is **`docs/NOVELTY-DESIGN.md`**, now carrying
s55 annotations inline.

## What changed since S53 (in nine sentences)

1. **P0 is half-adjudicated.** Grayzel's Lean proof of a(6)=872 is
   statement-FAITHFUL with a clean trust surface — except everything,
   both bounds included, is `native_decide` (compiler-trusted). The
   decisive `lake build` is a SWEEP-QUEUE entry, `approved: NO`.
   Neither claimed proof has real community audit ("mid-audit" was
   survey overstatement — count the messages: 2 and 0).
2. **Gheorghe's frame IS our loop-cover grammar**: s=splits, B=D+1,
   bridge lemma `deficit = j + (v−L) ≥ j`, zero exceptions over
   22,062; his s=25/B=4 prediction on Houston's witness recomputed
   from our ledger and exact.
3. **His O5 gap localizes to slack covers only**: all 22 O5-held δ=4
   cells have j ≥ 1 (deficit ≥ 1 — a walk species never observed in
   any corpus we hold); the 55 tight cells are O5-free. **The
   discharge route is ours: prove the slack tax (deficit ≥ 1 ⇒
   length ≥ 872)** — kills all 22 cells without his catalogues. His
   O6 (production-prune certificates), not O5, blankets the whole
   872 rung.
4. **Kramer–Mesner |G|>2 is a NO** (P5b done): theorem |Aut_str| ≤ 2
   always; 0 of 22,282 known record classes at either n has
   |Aut_cov|>2; the only record symmetry is |G|=2 reversal-type =
   Egan's palindromic-kernel trick, already fully exploited (84/84
   published 5906 covers). All 108 fully-asymmetric classes are ours
   (102 = the whole loop-swap tier) — a new structural fact for the
   grammar writeup. Refutation sweeps only, cover-level, if ever.
5. **Cover-count correction: 183 → 178.** The freeze number is
   orientation-canonical; fully quotiented (S₇×ι) the 220-class shell
   has 178 distinct covers (180 up to S₇). §6.4's unseeded cover
   master must exclude by fully-quotiented orbit.
6. **fl1577 proxy is BUILT and bites** (P5a done): stall reproduced
   at exactly optimum+5; survey claims verified against primaries
   (a first); P4's named GAIN_CRITERION=NO recipe is 40–60× worse
   than stock LKH on its own gate — demoted to control. Recipe study
   queued (`approved: NO`).
7. n=6 window still {869..872} pending P0; n=7 window [5888, 5906]
   unchanged, 5905 = δ21 the sole record front.
8. Project shell unchanged: 220 classes / 9 allocations; **PUBLISHED
   218 as of 2026-07-31** — PRs #52 AND #53 merged (s56 verified
   upstream master `77dc0d1`, 24 files added; the only unpublished
   project-shell classes are Kristan's two).
9. Everything the neighborhood program closed stays closed
   (HANDOFF-S53 §"State of the world" items 1–2, 9–10 unchanged).

## The work menu (s56, priority order)

1. **P0 closure**: (a) `lake build` — queued, LAUNCH, needs Andrew's
   approval; deliverable = the two AxiomAudit outputs verbatim.
   (b) **The slack-tax attack** (in-session): materialize slack
   (deficit ≥ 1) n=6 walks via `loop_ledger_probe.py`
   instrumentation, then door-pricing minimization under deficit ≥ 1
   (`upstream872_door_pricing.py`) — target: min length over slack
   walks ≥ 872, which discharges all 22 O5-held cells from our side.
2. **P1a under the §6.1 three-valued contract** (SAT → witness;
   UNSAT → certified minimal-core cut; UNKNOWN → scheduling only —
   a timeout is NEVER a cut): wire the s34 2-loop law, waste
   identity, fresh-doors, door-pricing as cuts in the DLX/SAT chain
   engines; **first milestone = the known-SAT control gate**
   (re-derive known 5906s from their own assumptions). Targets:
   chains #0/#24 (Houston's 5905 kernels).
3. **fl1577 recipe study** — queued, needs approval (~85 min 8-way
   Mac, hard-bounded).
4. **P5c** (873-shell local-optima network) + **P5d** (PatternBoost
   data-shape check) — the two remaining instruments.
5. THEORY §7: fold in Gheorghe's elementary per-edge reproof of the
   loop-count theorem (it also bounds v, which we never did).
6. ~~PR watch (#52, #53)~~ DONE s56: both merged 2026-07-31; NOTE.md
   files flipped to PUBLISHED, shell 194→218.
7. Andrew's standing calls: Kristan outreach; grammar-of-5906s
   publication (the provenance split is a new headline line for it);
   whether to send Grayzel/Gheorghe our findings (ledger staleness
   note; 15-vs-20 drift + receipt self-fulfillment) — field
   relations are his to run.

## Traps (s55 additions; S53's list still applies — read it)

- **A verification script that reads zero inputs can print all-PASS**
  — check the `words read: N` line before trusting green output
  (bitten in-session re-running `crosscheck_houston.py` bare).
- **LKH**: `MAX_TRIALS` defaults to DIMENSION and silently truncates
  budgets (harness pins 10⁶); bare `./LKH` blocks on interactive
  stdin — never invoke without a parameter file. TSPLIB's Heidelberg
  server is unreachable; use mirrors, verify checksums.
- **`extraDocs/a6-872` is STALE at f386a8a2**; the s55 pin is
  f47a4d51 (Raudvere-absorption commit). Don't update the stale
  clone; refetch fresh (refetch line in `out/s55/gheorghe/
  o5_closure.py` docstring, which also drift-checks the pin).
- **Audit-status survey claims ("mid-audit") are as unreliable as
  "never tried" claims** — verify by counting actual thread messages.
- **out/s55 scripts import from repo paths via `parents[N]`** — run
  them from their own directory or pass explicit paths.

## Key artifacts (all `out/s55/`, regenerable, uncommitted)

- `grayzel/` — statement extract + trust-surface inventory.
- `gheorghe/` — `DICTIONARY.md` (the full his↔ours table),
  `crosscheck_houston.py|.out`, `corpus_dictionary_check.py|.out`,
  `o5_closure.py|.out`, `houston/houston_872.txt`.
- `aut/` — `aut_scan.py`, `aut_controls.py`, `aut_n7.tsv`,
  `aut_n6.tsv` (22,062 rows), `summary.txt`, `controls.txt`, `ctrl/`.
- `fl1577/` — `run_fl1577.sh`, `bin/LKH` (3.0.13), `fl1577.tsp`
  (sha256-pinned), `cfg/`, `runs2/` (valid baseline; `runs/` is the
  pre-fix defect record).

## Reading order for a cold start

1. This file.
2. `docs/NOVELTY-DESIGN.md` (active design doc, s55-annotated).
3. `docs/JOURNAL.md` s55, s54; then s53/s52b via `HANDOFF-S53.md`.
4. `docs/SWEEP-QUEUE.md` (two pending s55 entries at the bottom;
   recomp2 520 still HELD).
5. Per program item: `../extraDocs/2026-07-31-research-*.md` (four
   reports), `analysis/cover7/results_n7_merged.csv` (chains #0/#24),
   `docs/OPS-BACKGROUND-AGENT.md`, `CLAUDE.md`.

Session end ritual unchanged: JOURNAL entry, `cargo test --release`
green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
→ push. When this goes stale, write the successor and repoint
CLAUDE.md + agent docs.
