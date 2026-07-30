# Handoff — the s39+ front (fresh agent, start here)

Supersedes `HANDOFF-S37.md`. Read JOURNAL s38/s38b for the latest
sessions; this is the two-page version with entry points and traps.

## State of the world in six sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records (871,
   more 871s, 870, 5905, higher n) validate the engine, and the
   program ends only at full solution or maximal conclusion.
2. **Both hunting grounds are corpus-complete and closed under every
   anchored edit tier we have built.** n=6 (22,062 classes, record
   872, LB 869): closed under reorder/ties/merge/recomp-1 to ~270-perm
   tails, 28M recompositions at the 585 band with zero events. n=7 (87
   known walks: 84 × 5906 + 3 × 5907, committed at
   `data/upstream5906`/`5907`): closed under reorder/ties/merge to
   ~410-perm tails, recomp-1 to ~200-perm tails, and — new in s38b —
   the PAIR-COMPOUND tier (I3) closed at the 4840 band with an **empty
   equal-cost shell**: 7,321,635 exact re-solves, 0 improved, 0
   equal-cost in any allocation.
3. **The compound tier is real but lives in midgame ORDER — this is
   the confirmed frontier, from both directions.** s36 located
   nature's only minimal 2-compound ((145,3)↔(143,5), two merges + two
   door promotions on cycles `126354`+`123654`, parts at depths
   181–718). s38 built `--recomp2` to chase it and REFUTED its own
   oracle with mechanism: extraction AND absorption of the `126354`@181
   part price exactly +6 over equal — the part sits behind a w2 entry,
   and any local repair of a w2 seam re-spells a full window, while
   nature's equal-length crossing pays w3 doors that exist only under
   a globally different midgame order. Search-side, s24 proved the
   same zone (levels ~60–450) is where beam ranking fails with zero
   bound slack. Anchored instruments cannot reach it; that is now a
   theorem-grade dead end, not a hunch.
4. **The instrument stack is n-generic and complete through pairs**
   (`src/tailatsp.rs`): blocks + junction pricing + exact block-order
   ATSP; flags `--ties`, `--merge`, `--recomp`, and s38's `--recomp2`
   (pair recompositions under T1 combined-net ∈ {−2,−1,0} + T2
   "no size-1 part in the moved cycle's full composition", single
   prefix-part extraction of straddling cycles, Λ-tripwire on every
   find, Kristan-seam banner at n=7; `--recomp2-tight` = nets −2/−1,
   `--recomp2-wide` = T2 off). Every candidate at-or-under record must
   pass `validate -n <n> --file <f> --complete` AND
   `python3 analysis/counting/m3_check.py [-n 7] <f>` (exit 2 = novel
   = drop everything).
5. **Standing laws with their caveats:** the loop-count relation
   `L = S + #doors − ((n−1)!−1)` (corpus law, derivation OPEN in
   THEORY §6 — now survived 7.3M independent exact re-solves via the
   s38 tripwire; Λ-neutrality IS length-neutrality, so it is an
   assertion, never a prune); the recomp-1 equal-cost plateau is dense
   and n-generic (48.2% n=6 / 48.5% n=7) yet collapses to the source
   class under M3 (200/200 sample); pair compounds have NO equal
   plateau at all; the Kristan seam (844,17)↔(843,18) is absent from
   every band swept.
6. Two agents share this repo: YOU (research — think, measure, build,
   write the JOURNAL) and an OPERATOR (runs/monitors everything > 30
   min via `docs/SWEEP-QUEUE.md`; it fills status/result fields, you
   only append entries; Andrew approves per-entry and manages the
   queue himself).

## The work menu (in priority order)

1. **The midgame-order design question (the new front — design before
   code, per the standing directive).** What instrument can reorder or
   re-derive levels ~60–450? Inputs to think with: s24 (capped beam:
   the record's own trajectory has `len + lb_residual ≤ 872` at every
   step — zero slack to prune until the end; completion from depth
   ≥ 450 is a solved oracle), s38 §10.8 (the w2-seam mechanism and the
   +6 ledger), M-2b′/s38b (compound crossings are global midgame
   rearrangements), and the NRPA/policy line (s25: warm-start
   re-derives 872 but off-line deviations cost ≥ 2 chars). A design
   doc section (SURGERY-DESIGN §11 or a new doc) comes before any
   Rust.
2. **Derive the loop-count relation** (THEORY §6, flagged OPEN).
   Likely a small theorem via the waste identity + 2-loop structure of
   w2 edges; 7.3M-solve empirical support. A proof upgrades all Λ
   bookkeeping and closes a standing "calibrated ≠ proven" caveat.
3. **Queued sweeps awaiting Andrew** (`docs/SWEEP-QUEUE.md`) — closure
   bookkeeping, NOT blockers for 1 or 2: n=6 recomp2 520-band tight
   (round-robin probe first; farm binary `bdc9625` already shipped)
   and the 450-band probe-only entry. Andrew manages the queue — don't
   launch, don't nag.
4. **Still open, untouched:** the ip=1 study (ε-rollouts only
   exerciser; no known 872 uses a priced skip); per-allocation
   NRPA/beam over `data/frontiers_s28/`; Track C v2's 2.4×
   scoring-overhead cut (core architecture under the premise, parked
   only on this blocker).

## Traps (each has bitten at least once)

- **Launch protocol:** > 30 min projected ⇒ SWEEP-QUEUE entry +
  Andrew's per-entry approval. < 5 min just run; between, time-box and
  watch. Heartbeats are part of any long run's launch.
- **The block ceiling binds at n=7, not the anchor** (s38b): every
  4600-band walk cut deeper than requested (observed 4629–4689).
  Quote OBSERVED anchors in any band claim; a true ~440-perm band
  needs 70–80 blocks — a different exact-solve regime.
- **Single-walk probes mislead** (s38b): the n=7 recomp2 probe walk
  was an unusually wide 33-block instance — 89 s/walk against a 49
  s/walk fleet mean. Round-robin probe before every farm projection
  (the a450b50 lesson, again, in new clothes).
- **Farm binary staleness:** the PC has no Rust toolchain;
  cross-compile (`x86_64-pc-windows-gnu`, crt-static) + reship after
  ANY change to `src/tailatsp.rs`/`src/corpus.rs`
  (`docs/OPERATIONS.md` §"tail-atsp farm harness"). Current shipped
  binary: `bdc9625` (includes everything through s38). Also run the
  post-ship PowerShell parse check (the s38b supervisor crash).
- **Doc drift on T1/T2:** §10.4's T1 as WRITTEN ({−1,0}) would have
  excluded nature's own compound; the as-built truth is §10.8 (net
  −2..0; T2 = singleton-free full composition). When spec and build
  disagree, §10.8 wins.
- **Don't re-hope extraction:** prefix-part extraction/absorption at a
  w2-entered seam is provably +6-lossy (pinned test
  `natural_compound_refuted_at_anchored_reach`). The compound tier is
  not reachable by widening anchored move sets.
- **Alphabetical-prefix bias:** never project a sweep from the first K
  corpus files (measured 1.9–3.3×). Probe round-robin.
- **Calibrated ≠ proven:** `--fresh-doors`, census profiles, M-R laws,
  the loop-count relation, and the closure laws are corpus-calibrated.
  Claims made with them say so. The n=7 M3 index covers all PUBLISHED
  data (s34 decode) — say "published", not "all known".
- **Tautology check before celebrating a new law:** s37's T4 lesson —
  check a "new" invariant is not a re-parameterization of an old one
  before building on it.
- **Equal-cost flood semantics:** ~half of all SINGLE recompositions
  complete at equal cost — NOT events. Sample through m3_check; only
  improvements, new-allocation completions, and M3-novel classes are
  events. (Pair compounds are the opposite: any equal-cost pair
  completion is remarkable — none has ever been observed.)
- **Cap-at-target starves NRPA** (s25, twice-measured): hunt cap 874,
  collect ≤ 872.
- **16 GB local RAM:** `sojourn-dfs --dedup exact` near 60M nodes is
  the ceiling; don't stack RAM-heavy work on a local sweep.
- **Session end ritual:** JOURNAL entry (fold any `done` queue results
  — the operator never writes the JOURNAL), `cargo test --release`
  green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
  → push (the operator also commits; never rewrite pushed history).

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s38b + s38 (the current front and how it was
   measured).
3. `docs/SURGERY-DESIGN.md` §10 END-TO-END, especially §10.8 (the
   as-built instrument + the refutation mechanism) — and §10.6/§10.7
   for what it corrected.
4. `docs/SWEEP-QUEUE.md` (pending/done; Andrew manages approvals) and
   `docs/OPS-BACKGROUND-AGENT.md` (operator interface).
5. `CLAUDE.md` (commands incl. the recomp2 block, hard invariants).
