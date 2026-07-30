# Handoff — the s42+ front (fresh agent, start here)

Supersedes `HANDOFF-S39.md`. Read JOURNAL s39→s41b for how the last
four sessions unfolded; this is the two-page version with entry
points and traps.

## State of the world in eight sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records (871,
   more 871s, 870, 5905, higher n) validate the engine, and the
   program ends only at full solution or maximal conclusion.
2. **The loop-count relation is a THEOREM (s39, THEORY §7):**
   `length ≥ n! + (n−1)! + (n−3) + Λ` for every pure complete walk,
   deficit = (splits−Φ) + (D+1−P), both ≥ 0 — and every known record
   sits at equality: **a record is a TIGHT LOOP COVER** (Φ = splits
   fully-ridden 2-loops spanning the w2 cycle space, a bridge-forest
   of doors, D+1 door-terminated single chains). An 871 satisfies
   Λ + deficit = 28; a 5905, 141.
3. **The compound tier's vocabulary is THREE rigid rewrite rules**
   (s40, SURGERY-DESIGN §11.6): R-compound and R-unit at n=6, R-K7
   (the Kristan seam) at n=7 — each an object-for-object identical
   local surgery (rotor ⟷ door trade) recurring across unrelated
   classes, extracted from the cover-sharing pairs the s39 census
   found. Depths of the moved objects explain retroactively why every
   anchored instrument missed them.
4. **The rules are executable and PRODUCTIVE** (s41,
   `analysis/counting/i4a_apply.py`, SURGERY-DESIGN §11.7): a tight
   walk replays deterministically from (start, entry sets, doors), so
   a rule = a ~6-perm structure edit + replay. Oracle: all 13 pairs
   re-derived byte-identically. The symmetry-conjugated sweep
   produced **8 NOVEL 5906 classes in two allocations never seen at
   n=7 — (839,22) and (835,26)** — the first genuinely new
   record-length walks this project has generated.
5. **They are PUBLISHED:** superpermutators/superperm **PR #50,
   merged same-day by Robin Houston** (2026-07-30). The canonical
   published n=7 record shell is now **92 classes across 8
   allocations**, 8 walks + 2 profiles contributed by this project.
   Locally: `data/upstream5906/` still holds the pre-PR 84;
   `data/novel5906/` holds our 8 (NOTE.md has provenance);
   `m3_check -n 7` auto-loads BOTH committed indexes.
6. **n=6 is saturated where n=7 was not:** the full 22,062-class
   archive is CLOSED under the conjugated REVERSE rules (20 edges =
   16 compound + 4 unit — the complete natural-move graph, committed
   at `data/i4a_products_sym_rev/i4a_sym_edges.tsv`), including a
   hard negative: **0 (144,4) products in 2,104 replays** — the
   unoccupied allocation resists nature's own moves under full
   symmetry. The n=6 FORWARD conjugated sweep is queued (approval
   pending, ~100 min local).
7. **Anchored instruments (I1/I2a/recomp-1/I3) remain closed at both
   n** — s38b's empty pair-compound shell etc.; nothing new there;
   the open front is entirely in loop-cover coordinates.
8. Two agents share this repo: YOU (research — think, measure, build,
   write the JOURNAL) and an OPERATOR (runs anything > 30 min via
   `docs/SWEEP-QUEUE.md`; Andrew approves per-entry — don't launch,
   don't nag).

## The work menu (in priority order)

1. **Point the ladder at the 8 new classes — iterate rule-closure to
   a fixed point.** The s41 conjugated n=7 sweep ran on the OLD 84
   only: the new 8 have never been touched by ANY instrument. (a)
   conjugated R-K7 from the 8 (more novel classes? the move that
   created them may fire again); (b) cover census over all 92 (do the
   new classes pair with each other / the old corpus? new pairs ⇒
   possibly NEW RULES to extract via m4a_pair_anatomy); (c) tail-atsp
   bands + recomp on the 8; (d) refresh the n=7 structure census
   (`upstream5906_structure.py`) for the new allocations. Any new
   rule found loops back into i4a_apply's RULES table.
2. **The queued n=6 FORWARD conjugated sweep** (SWEEP-QUEUE, ~100 min
   local, probe-calibrated): given the n=7 precedent, novel
   (143,5)/(142,6) classes are live. Needs Andrew's approval.
3. **M-4b / M-4d / M-4c** (SURGERY-DESIGN §11.4): traversal count of
   one cover (exhaustive I4-A vs guided); 871-cover combinatorial
   feasibility (a NO closes the 871 within the tight class —
   certificate-level); the Λ-bound experiment for the s24 blocked
   zone (first new admissible midgame signal if it works).
4. **Older queue entries** (n=6 recomp2 520/450 bands) — closure
   bookkeeping, unaffected, still pending approval.
5. **Still open, untouched:** ip=1 study; per-allocation NRPA/beam
   over `data/frontiers_s28/`; Track C v2's 2.4× scoring-overhead cut
   (core architecture under the premise).

## Traps (each has bitten at least once)

- **Launch protocol:** > 30 min projected ⇒ SWEEP-QUEUE entry +
  Andrew's per-entry approval. < 5 min just run; between, time-box
  and watch. Heartbeats are part of any long run's launch.
- **`m3_check --build-index` writes to the COMMITTED per-n index
  path** (s41: it silently clobbered `upstream5906_canon_index.tsv`;
  restored from git). Never use it to build a side index — write the
  TSV directly (format: `canon_sha256\tclass_file`).
- **The n=7 corpus is now in TWO local dirs:** any "whole-corpus"
  n=7 sweep must include `data/upstream5906` AND `data/novel5906`
  (+ `data/upstream5907` where relevant). The published set (92)
  equals their union; quoting "84" is now stale.
- **Canonical frame (s39):** 2-loop ids and rule objects are NOT
  relabel-invariant. The literal rules/cover comparisons live in the
  canonical frame; the conjugated sweep (`apply-sym`) is the
  frame-complete version — prefer it for closure claims. "120/144
  loops used, 4 universal" are canonical-frame facts.
- **Tight ≠ only (s39):** deficit > 0 walks are legal. I4 tightness
  constraints are search restrictions, not laws; a Λ-tripwire
  "violation" on a found walk means a structurally slack walk
  (banner-worthy), not a solver bug.
- **Replay-sufficiency ≫ precondition (s41):** rule preconditions are
  promiscuous (21,559 literal R-compound-fwd carriers, 8 survivors).
  Never project yields from carrier counts; the replay decides.
- **The block ceiling binds at n=7, not the anchor** (s38b): quote
  OBSERVED anchors; a true ~440-perm band needs 70–80 blocks.
- **Single-walk probes mislead / alphabetical-prefix bias:**
  round-robin probe before every projection (bitten twice).
- **Farm binary staleness:** cross-compile + reship after ANY change
  to `src/tailatsp.rs`/`src/corpus.rs` (`docs/OPERATIONS.md`).
  Current shipped binary: `bdc9625` (i4a work is Python — no reship
  needed so far). Run the post-ship PowerShell parse check.
- **Doc drift:** where SURGERY-DESIGN §10.4 and §10.8 disagree, §10.8
  wins. §11.6/§11.7 are the as-built truth for I4-A.
- **Don't re-hope extraction:** w2-seam extraction/absorption is
  provably +6-lossy (pinned test). The compound tier is reached by
  rule application / reordering, not by widening anchored move sets.
- **Calibrated ≠ proven:** `--fresh-doors`, census profiles, M-R
  laws, closure laws are corpus-calibrated (the loop-count INEQUALITY
  is proven; corpus TIGHTNESS is calibrated). Say "published" for
  n=7 claims — and remember published now includes our 8.
- **Tautology check before celebrating a new law** (s37's T4 lesson).
- **Equal-cost flood semantics:** ~half of all single recompositions
  complete at equal cost — NOT events. Pair compounds: any equal is
  remarkable. I4 products are equal-length BY CONSTRUCTION — events
  there are M3-novel classes and unreached allocations only.
- **Cap-at-target starves NRPA** (s25): hunt cap 874, collect ≤ 872.
- **16 GB local RAM:** don't stack RAM-heavy work on a local sweep.
- **Session end ritual:** JOURNAL entry (fold any `done` queue
  results — the operator never writes the JOURNAL),
  `cargo test --release` green (139), clippy `-D warnings`, fmt,
  commit → `git pull --rebase` → push (never rewrite pushed history).
- **Publishing:** upstream contributions go via the
  `../superperm` clone (fork remote `fork` = abalint/superperm,
  branch + PR; PR #50 is the precedent — one-line file per solution
  in `superpermutations/<n>/`, verification in the PR body). Always
  `git pull` the clone and re-verify novelty against CURRENT contents
  first; only Andrew decides when to publish.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s41b/s41/s40/s39 (the front and how it was won).
3. `docs/THEORY.md` §7 (theorem + census facts);
   `docs/SURGERY-DESIGN.md` §11 end-to-end (§11.6 rules, §11.7
   as-built results) — then §10.8 for the refutation that motivated
   the pivot to loop coordinates.
4. `data/novel5906/NOTE.md` (the discoveries + publication status).
5. `docs/SWEEP-QUEUE.md` (pending/done; Andrew manages approvals) and
   `docs/OPS-BACKGROUND-AGENT.md` (operator interface).
6. `CLAUDE.md` (commands — the i4a/loop_ledger_probe blocks are the
   newest; hard invariants).
