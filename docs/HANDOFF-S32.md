# Handoff — the s32+ front (fresh agent, start here)

Supersedes `HANDOFF-S28.md`. Read JOURNAL s28–s31 for the full story;
this is the two-page version with entry points and traps.

## State of the world in five sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records (871,
   more 871s, 870, higher n) are how the engine is validated, and the
   program ends only at full solution or maximal conclusion.
2. The n=6 hunt targets 871 (record 872, Lean-proven LB 869); every
   871 lives in a waste-146 L0 allocation one unit edit from one of the
   8 specimen-backed anchors, and the 22,062-class community corpus is
   the specimen base (`data/upstream872/`, gitignored; canonical index
   committed for the M3 gate).
3. **The corpus is closed under every local move built so far**
   (SURGERY-DESIGN §"closure picture"): splice-closed (s26b),
   block-order-optimal to ~270-perm tails (I1 + farm a450b50),
   merge-closed to ~200 (488,350 moves, one rediscovery), the S1 tie
   graph connects the 8 allocation shells by exactly ONE edge (the
   natural (143,5)↔(142,6) pair), and single-cycle recomposition is
   dense at equal length (48% of moves) but every sampled product is a
   known class.
4. Therefore an 871 differs from every known 872 by a COMPOUND edit
   (≥ 2 coordinated recompositions; the s29 census conservation law
   `net splits = ΔS, 1,071/1,071` fixes each target's budget) or
   diverges before the anchorable zone (~depth 450).
5. Two agents share this repo: YOU (research — think, measure, build,
   write the JOURNAL) and an OPERATOR (runs/monitors everything > 30
   min via `docs/SWEEP-QUEUE.md`; it fills status/result fields, you
   only append entries; Andrew approves per-entry).

## The instrument stack (all in `src/tailatsp.rs`, all n-generic)

`tail-atsp` decomposes any walk tail at an anchor into blocks (= sojourn
parts), prices junctions by overlap, and solves block-order ATSP
exactly (HK ≤ 20 blocks, two-tier B&B above). Flags: `--ties`
(equal-cost orders, cross-allocation detector), `--merge` (S−1 unit
edit), `--recomp` (complete single-cycle recomposition — subsumes
merge). Oracles pinned in tests: the tie oracle AND the merge/recomp
seam oracle both re-derive the committed specimen pair
(`data/surgery_specimens/`) byte-identically. Every candidate ≤ 872
must pass `validate --complete` AND `python3
analysis/counting/m3_check.py` (exit 2 = novel vs all 22,062 classes)
before ANY claim. Exit code 2 from a sweep = 871 candidate = drop
everything.

## The work menu (in priority order)

1. **n=7 corpus assembly + first n=7 sweeps (the engine-generality
   test).** Gather the 83 published 5906s (community repo
   superpermutators/superperm — `analysis/counting/upstream872_dump.py`
   is the template for the sparse clone + forward-renumbering), plus
   Kristan's 5906 (`../extraDocs/verify_tk5906.py` has it) and the
   three 5907s (urdvr repo, see extraDocs notes). Then run the SAME
   instruments at n=7: I1 reorder → ties → merge → recomp on 5906-class
   tails. The record-to-bound gap there is 18 chars (5906 vs 5888) —
   far more room than n=6's 3. Mind: block counts scale with tail
   length; probe anchors before sweeping; everything > 30 min goes to
   the queue.
2. **Multi-move tier (design doc BEFORE code — standing directive).**
   Compound edits: k recompositions with a net budget from the
   conservation law (S−1 targets need net −1; d3−1 targets net 0 with
   a door demotion). Start with measurements: which PAIRS of
   recompositions co-occur in natural cross-allocation pairs
   (`analysis/trackb/recomp_census.py` has the per-cycle machinery);
   then extend `tail-atsp` with 2-cycle compound enumeration (the
   search space is (cycles × 63)², so pruning by the census laws is
   the design problem).
3. **Queued sweeps awaiting Andrew's approval** (`docs/SWEEP-QUEUE.md`):
   full-corpus recomp-585 (~1.5–4.5 h farm; exhaustive version of the
   closure law + alarm paths) and the anchor-450 tie band (~3.5–4 h).
   Don't launch these yourself; don't nag — Andrew approves in the doc.
4. **Still open, untouched:** the ip=1 study (3 waste-146 targets need
   a priced pass-over, a move NO known 872 uses; ε-rollouts are the
   only exercisers — `rollouts --strings` + `verify_identity.py`);
   per-allocation NRPA/beam over `data/frontiers_s28/`; Track C v2's
   2.4× scoring-overhead cut (the evaluator is core engine architecture
   under the premise, parked only on this blocker).

## Traps (each has bitten at least once)

- **Launch protocol:** anything projected > 30 min needs a SWEEP-QUEUE
  entry and Andrew's per-entry approval. < 5 min just run; in between,
  time-box and watch. Heartbeats are part of any long run's launch.
- **Farm binary staleness:** the PC has no Rust toolchain. After ANY
  change to `src/tailatsp.rs`, `src/corpus.rs`, or `src/main.rs`,
  cross-compile (`x86_64-pc-windows-gnu`, crt-static) and reship
  `F:\superpermFarm\tailatsp\superperm.exe` BEFORE farm runs
  (`docs/OPERATIONS.md` §"tail-atsp farm harness").
- **Alphabetical-prefix bias:** never project a sweep from the first K
  corpus files — measured bias 1.9–3.3×. Probe round-robin.
- **Calibrated ≠ proven:** `--fresh-doors`, census profiles, and every
  M-R law are corpus-calibrated. Claims made with them say so, or run
  with them off. The closure laws all carry their band/vocabulary
  caveats — state them.
- **Equal-cost flood semantics:** same-allocation equal-length
  recompositions are ~half of all moves — they are NOT events. Sample
  them through m3_check (60/60 known so far); only improvements,
  new-allocation completions, and M3-novel classes are events.
- **Cap-at-target starves NRPA** (s25, twice-measured): hunt with cap
  874, collect ≤ 872.
- **16 GB local RAM:** `sojourn-dfs --dedup exact` near 60M nodes is
  the ceiling; don't start RAM-heavy work while a local sweep runs.
- **Session end ritual:** JOURNAL entry (fold in any `done` queue
  results — the operator never writes the JOURNAL), keep `cargo test
  --release` green (133), clippy `-D warnings`, fmt, `git pull
  --rebase` before commit (the operator also commits), push.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` latest entry (current state, concrete next steps).
3. `docs/SURGERY-DESIGN.md` §9 (census laws M-R1..7) + §"closure
   picture" (what is dead and why).
4. `docs/SWEEP-QUEUE.md` (what is running/queued) and
   `docs/RESEARCH-AGENT-S29.md` (the two-agent boundary in detail).
5. `CLAUDE.md` (commands, hard invariants).
