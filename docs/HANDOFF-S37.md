# Handoff — the s38+ front — SUPERSEDED by HANDOFF-S38.md (kept as history)

Supersedes `HANDOFF-S32.md`. Read JOURNAL s33–s37 for the full story;
this is the two-page version with entry points and traps.

**s38 ADDENDUM (this doc predates it):** `--recomp2` is BUILT (work
menu item 1 done) and its §10.6 oracle is REFUTED — the natural
compound is not expressible at anchored reach even with extraction
(both extraction and absorption price +6 over equal; the compound
tier lives in midgame ORDER). Read JOURNAL s38 + SURGERY-DESIGN §10.8
before item 1's sweeps; three recomp2 queue entries await approval in
SWEEP-QUEUE. The farm binary is STALE for recomp2 until reshipped
(s38 changed `src/tailatsp.rs`). **s38b:** the n=7 sweeps all ran
(operator, farm) — pair-compound tier CLOSED at 4840 with an EMPTY
equal-cost shell (7.3M solves, 0 equal, 0 Λ violations), Kristan seam
absent everywhere, merge+ties closed to ~410-perm tails (block ceiling
binds at n=7, not the anchor — quote observed anchors). Binary
`bdc9625` is shipped. Remaining queue: n=6 recomp2 520 tight (probe
first) and the 450 probe-only entry.

## State of the world in six sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records (871,
   more 871s, 870, 5905, higher n) validate the engine, and the
   program ends only at full solution or maximal conclusion.
2. **Both hunting grounds are corpus-complete and closed under single
   edits.** n=6: 22,062 classes, record 872 (LB 869), closed under
   reorder/ties/merge/recomp to ~270-perm tails, shells connected by
   exactly one natural edge. n=7 (s33–s34): 84 known 5906 classes —
   the 83 published + Kristan's — COMMITTED at `data/upstream5906/`
   (+3 5907s), same closure verdicts from the same instruments run
   unchanged, and the twoCycles files are decoded annotations, so no
   hidden corpus lurks (the n=6 fear does not recur).
3. **The compound tier is real, specific, and located** (s36, M-2):
   nature's only minimal 2-compounds are one mirrored object bridging
   the two largest S1-disconnected shells (145,3)↔(143,5) — two merges
   + two door promotions on cycles `126354`+`123654` — and its parts
   span depths 181–718, which is WHY every deep-anchored single-edit
   sweep found the corpus closed.
4. **The next build is fully designed and measured** (SURGERY-DESIGN
   §10, esp. §10.6–10.7): `tail-atsp --recomp2` = tail pair-recomp
   under T1 budget (+T2 vocabulary) with single prefix-part extraction
   at anchors 450/520 — straddling cycles are rare (2.2/walk), prune
   factors measured at ~470–900 exact re-solves/walk, controls and the
   natural-compound oracle pinned in the doc. **s38 = build it.**
5. Useful new laws with their caveats: the loop-count relation
   `L = S + #doors − ((n−1)!−1)` (exceptionless on 22k+ walks, both n,
   incl. off-shell 873s; derivation OPEN; NOT a prune — Λ-neutrality
   is length-neutrality, s37's T4 correction) and the n=7 L0 map (all
   84 pure-w3 over 6 allocations; Kristan's (843,18) alone, one
   unit-trade from the (844,17) dominant shell, NOT single-edit
   reachable in-band).
6. Two agents share this repo: YOU (research — think, measure, build,
   write the JOURNAL) and an OPERATOR (runs/monitors everything > 30
   min via `docs/SWEEP-QUEUE.md`; it fills status/result fields, you
   only append entries; Andrew approves per-entry and manages the
   queue himself).

## The instrument stack (all n-generic, proven at n=6 AND n=7)

`tail-atsp` (`src/tailatsp.rs`): blocks + junction pricing + exact
block-order ATSP (HK ≤ 20, B&B to ~50 blocks / ~2 s at anchor 450).
Flags: `--ties`, `--merge`, `--recomp`. Oracles pinned in tests (tie,
merge/recomp seam). Anchor bands scale by perm count: n=7's
4905/4840/4770 ≈ n=6's 585/520/450 (`--max-blocks 40`/`50` at the two
deeper bands). Every candidate at-or-under record must pass
`validate -n <n> --file <f> --complete` AND
`python3 analysis/counting/m3_check.py [-n 7] <f>` (exit 2 = novel =
drop everything). Structure tools: `upstream5906_structure.py` (n=7 L0
census), `loop_census.py` (2-loop counts, the Λ verifier),
`upstream5906_twocycles.py` (annotation bijection + 142-loop law),
`recomp_cooccur.py` (M-2; needs `surgery_pairs.py 150 > pairs.tsv`
regenerated first, 54 s, not committed).

## The work menu (in priority order)

1. **Build `--recomp2` (s38, Rust).** The spec IS the doc: SURGERY-
   DESIGN §10.4 (move space, T1/T2 filters, exactness, verdicts),
   §10.6 (natural-compound oracle, anchor-reach), §10.7 (straddle
   frame: extraction = remove ONE prefix part of a straddling cycle,
   heal the seam exactly, float its perms as a mergeable block; ≤ 1
   extra block at anchor 450). Controls before any sweep: n=5 optimum,
   synthetic composition of two known equal-cost recomp-1 moves, the
   seam-edit pin, and the natural-compound oracle (from
   `872.up-55088ebb4107`, anchor ≤ 450 with extraction of
   `126354`@181: find AN equal-cost (143,5) completion via the two
   merges; report its m3 class vs `872.up-d141177d85e1` either way —
   class equality is informative, not pinned). Then probe 8 specimens,
   queue sweeps: n=7 FIRST (87 walks = whole corpus is a probe), then
   n=6 520/450 bands.
2. **Queued sweeps awaiting Andrew** (`docs/SWEEP-QUEUE.md`): n=7
   recomp-4840 (~75 min) and the n=7 deep-seam probe (4600,
   self-sizing). Andrew manages the queue — don't launch, don't nag.
3. **Operator results to fold:** the n=6 `a585recomp` farm sweep
   (running as of s37) — fold its ledger into the JOURNAL + closure
   picture when `done` appears in SWEEP-QUEUE.
4. **Still open, untouched:** derive the loop-count relation (THEORY
   §6 flags it OPEN — a small proof would upgrade Λ bookkeeping to
   theorem); the ip=1 study (ε-rollouts only exerciser); per-allocation
   NRPA/beam over `data/frontiers_s28/`; Track C v2's 2.4×
   scoring-overhead cut (core architecture under the premise, parked
   only on this blocker).

## Traps (each has bitten at least once)

- **Launch protocol:** > 30 min projected ⇒ SWEEP-QUEUE entry +
  Andrew's per-entry approval. < 5 min just run; between, time-box and
  watch. Heartbeats are part of any long run's launch.
- **Farm binary staleness:** the PC has no Rust toolchain. s38 changes
  `src/tailatsp.rs` ⇒ cross-compile (`x86_64-pc-windows-gnu`,
  crt-static) and reship `F:\superpermFarm\tailatsp\superperm.exe`
  BEFORE any post-s38 farm run (`docs/OPERATIONS.md` §"tail-atsp farm
  harness"). The e286355 reship covers everything up to `--recomp`.
- **Alphabetical-prefix bias:** never project a sweep from the first K
  corpus files (measured 1.9–3.3×). Probe round-robin. (n=7's 87 files
  are small enough to just run whole.)
- **Calibrated ≠ proven:** `--fresh-doors`, census profiles, M-R laws,
  the loop-count relation, and the n=7 closure laws are
  corpus-calibrated. Claims made with them say so. The n=7 M3 index
  covers all PUBLISHED data (s34 decode) — say "published", not "all
  known", if being careful.
- **Tautology check before celebrating a new law:** s37's T4 lesson —
  the shiny new invariant reduced to the waste identity via one line
  of algebra. Before building a prune/instrument on a "new" law, check
  it is not a re-parameterization of an old one.
- **Equal-cost flood semantics:** ~half of all recompositions complete
  at equal cost — NOT events. Sample through m3_check; only
  improvements, new-allocation completions, and M3-novel classes are
  events.
- **Cap-at-target starves NRPA** (s25, twice-measured): hunt cap 874,
  collect ≤ 872.
- **16 GB local RAM:** `sojourn-dfs --dedup exact` near 60M nodes is
  the ceiling; don't stack RAM-heavy work on a local sweep.
- **Session end ritual:** JOURNAL entry (fold any `done` queue results
  — the operator never writes the JOURNAL), `cargo test --release`
  green (133), clippy `-D warnings`, fmt, `git pull --rebase` needs a
  clean tree — commit first, then rebase, then push (the operator also
  commits).

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` latest entry (current state, concrete next steps).
3. `docs/SURGERY-DESIGN.md` §10 END-TO-END (§10.1 frame, §10.4 spec,
   §10.6 M-2 results, §10.7 measured factors + T4 correction) — the
   s38 build implements exactly this.
4. `docs/SWEEP-QUEUE.md` (running/queued; Andrew manages approvals)
   and `docs/OPS-BACKGROUND-AGENT.md` (operator interface, rates).
5. `CLAUDE.md` (commands incl. the n=7 block, hard invariants).
