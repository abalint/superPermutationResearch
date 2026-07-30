# Handoff — the s40+ front (fresh agent, start here)

Supersedes `HANDOFF-S38.md`. Read JOURNAL s39 (and s38/s38b) for the
latest sessions; this is the two-page version with entry points and
traps.

## State of the world in seven sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records (871,
   more 871s, 870, 5905, higher n) validate the engine, and the
   program ends only at full solution or maximal conclusion.
2. **Both hunting grounds are corpus-complete and closed under every
   anchored edit tier built** (reorder/ties/merge/recomp-1 at both n;
   s38b: the n=7 pair-compound tier closed at the 4840 band with an
   EMPTY equal-cost shell — 7.3M exact re-solves, zero equals).
3. **The loop-count relation is now a THEOREM (s39, THEORY §7):**
   `length ≥ n! + (n−1)! + (n−3) + Λ` for every pure complete walk,
   deficit = (splits−Φ) + (D+1−P), both terms ≥ 0 — and every known
   record sits at equality: **a record is a TIGHT LOOP COVER**
   (Φ = splits fully-ridden 2-loops spanning the w2 cycle space, a
   bridge-forest of doors, D+1 door-terminated single chains).
4. **The cover census turned the compound tier from invisible to
   pinned:** the used-loop set is a near-perfect class invariant
   (22,050 covers / 22,062 n=6 classes) whose ONLY collisions are the
   natural edit boundaries — 8× (145,3)↔(143,5) compound pairs + 4×
   (143,5)↔(142,6) unit pairs at n=6, and at n=7 the single collision
   is **the Kristan seam (844,17) `a30c7c517d7b` ↔ (843,18)
   `d9a28c2d8195`** — the seam every anchored sweep missed, realized
   as a cover-preserving global reordering.
5. **The open front is instrument I4 (SURGERY-DESIGN §11):** I4-A =
   tight-traversal search of a FIXED cover (13 oracle pairs to
   re-derive; products are equal-length walks in new classes/
   allocations; the Kristan seam by construction); I4-B (staged) =
   cover synthesis for Λ−1 objects (an 871 = a tight 28-loop cover;
   DLX-shaped). Measurement pass M-4 comes BEFORE any build: M-4a
   pair anatomy → M-4b traversal counting → M-4c Λ-bound for the s24
   blocked zone → M-4d 871-cover counting.
6. **The instrument stack through pairs is n-generic and done**
   (`src/tailatsp.rs`: `--ties`/`--merge`/`--recomp`/`--recomp2`);
   every candidate at-or-under record passes
   `validate -n <n> --file <f> --complete` AND
   `python3 analysis/counting/m3_check.py [-n 7] <f>` (exit 2 = novel
   = drop everything).
7. Two agents share this repo: YOU (research) and an OPERATOR
   (`docs/SWEEP-QUEUE.md`; Andrew approves per-entry — don't launch,
   don't nag).

## The work menu (in priority order)

1. **I4-A mode 0 is BUILT and productive (s41, SURGERY-DESIGN §11.7,
   `analysis/counting/i4a_apply.py`)** — oracle 13/13 byte-identical;
   the conjugated sweep produced the project's FIRST NOVEL
   record-length classes: 8 new 5906s in two never-seen allocations
   ((839,22), (835,26); archived `data/novel5906/`, supplementary m3
   index committed). n=6 is closed under the conjugated REVERSE rules
   incl. a hard (144,4) negative (2,104 replays, 0 products). NOW: run
   the queued n=6 FORWARD sweep when approved; iterate rule-closure on
   the 8 new classes (do R-K7/tail instruments fire from them?);
   refresh the n=7 structure census for the new allocations.
2. **M-4b / M-4d** — traversal count of one known cover (exhaustive
   I4-A vs. guided); 871-cover combinatorial feasibility (a NO closes
   the 871 within the tight class, certificate-level).
3. **M-4c — the Λ-bound experiment**: is `loops-committed + admissible
   minimum additional` a nontrivial bound at depths 60–450? First new
   admissible signal for the s24 zero-slack wall if yes.
4. **Queued sweeps awaiting Andrew** (SWEEP-QUEUE): n=6 recomp2
   520-band tight (round-robin probe first; farm binary `bdc9625`
   shipped) and the 450-band probe-only entry. Closure bookkeeping,
   not blockers.
5. **Still open, untouched:** ip=1 study; per-allocation NRPA/beam
   over `data/frontiers_s28/`; Track C v2's 2.4× scoring-overhead cut
   (core architecture under the premise).

## Traps (each has bitten at least once)

- **Launch protocol:** > 30 min projected ⇒ SWEEP-QUEUE entry +
  Andrew's per-entry approval. < 5 min just run; between, time-box and
  watch. Heartbeats are part of any long run's launch.
- **Canonical frame (new, s39):** 2-loop ids are NOT relabel-
  invariant. Cover comparisons are between canonical representatives;
  "120/144 loops ever used, 4 universal" are canonical-frame facts —
  quotient before quoting them as absolute structure.
- **Tight ≠ only (new, s39):** deficit > 0 walks are legal. I4's
  tightness constraints are search restrictions, not laws; a Λ-
  tripwire "violation" on a found walk means a structurally slack walk
  (banner-worthy), not a solver bug.
- **The block ceiling binds at n=7, not the anchor** (s38b): quote
  OBSERVED anchors; a true ~440-perm band needs 70–80 blocks.
- **Single-walk probes mislead** (s38b): round-robin probe before
  every farm projection.
- **Farm binary staleness:** cross-compile + reship after ANY change
  to `src/tailatsp.rs`/`src/corpus.rs` (`docs/OPERATIONS.md`). Current
  shipped binary: `bdc9625`. Run the post-ship PowerShell parse check.
- **Doc drift on T1/T2:** where §10.4 and §10.8 disagree, §10.8 wins.
- **Don't re-hope extraction:** w2-seam extraction/absorption is
  provably +6-lossy (pinned test). The compound tier is reached by
  reordering, not by widening anchored move sets — that is what I4 is
  for.
- **Alphabetical-prefix bias:** never project a sweep from the first K
  corpus files. Probe round-robin.
- **Calibrated ≠ proven:** `--fresh-doors`, census profiles, M-R laws,
  and the closure laws are corpus-calibrated (the loop-count
  INEQUALITY is now proven; the corpus's TIGHTNESS is calibrated).
  The n=7 M3 index covers all PUBLISHED data — say "published".
- **Tautology check before celebrating a new law** (s37's T4 lesson).
- **Equal-cost flood semantics:** ~half of all single recompositions
  complete at equal cost — NOT events. Pair compounds are the
  opposite (any equal-cost pair completion is remarkable). I4-A
  products are equal-length BY CONSTRUCTION — the events there are
  M3-novel classes and unreached allocations, not equality itself.
- **Cap-at-target starves NRPA** (s25): hunt cap 874, collect ≤ 872.
- **16 GB local RAM:** don't stack RAM-heavy work on a local sweep.
- **Session end ritual:** JOURNAL entry (fold any `done` queue results
  — the operator never writes the JOURNAL), `cargo test --release`
  green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
  → push (never rewrite pushed history).

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s39 + s38b/s38 (the current front and how it was
   reached).
3. `docs/THEORY.md` §7 (the theorem + census facts) and
   `docs/SURGERY-DESIGN.md` §11 (I4 + M-4), then §10.8 for the
   refutation that motivated the front.
4. `docs/SWEEP-QUEUE.md` (pending/done; Andrew manages approvals) and
   `docs/OPS-BACKGROUND-AGENT.md` (operator interface).
5. `CLAUDE.md` (commands incl. the loop_ledger_probe block, hard
   invariants).
