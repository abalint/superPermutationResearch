# Handoff — the s47+ front (fresh agent, start here)

Supersedes `HANDOFF-S45.md`. Read JOURNAL s46 (band closure, the R-K7
unmasking, the blind-spot census, the cover-twin discovery), s45 (gen-2
closure negative), s44 (the discovery event); this is the two-page
version with entry points and traps.

## State of the world in eight sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records and
   record-shell structure validate the engine.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7). The n=7
   record shell is **194 published classes / 8 allocations**, 110 of
   them (57%) this project's; upstream `superpermutators/superperm` at
   `235a074`, unchanged since PR #51.
3. **The loop-swap vocabulary is 862 directed canonical rules**
   (622 + the 240 from s46's sub-256 band,
   `data/loopswap/rules_n7_a4840_band200.tsv`) — but canonical ids
   quotient by S₇ only, NOT reversal, so the tables double-count
   reversal-frame variants (the "near-pure door rules" ARE R-K7: s46).
4. **The shell is CLOSED under everything executable**: all 862
   loop-swap rules (s45 + s46 band sweep, 0 novel 0 shorter) AND the
   i4a cover-preserving tier (s46 ran the first full-194 R-K7 sweep —
   s41 only ever covered 92 — 0 novel). New classes need a genuinely
   new move tier or a source outside the closure.
5. **The natural-move graph is the accumulating product**: 2,003
   undirected edges in `data/loopswap/lswap_sym_edges_n7_ALL_union.tsv`
   (THE file for graph analyses), 180/194 classes touched, 20
   components, giant of 85. Kristan's class is connected only by R-K7
   (its single edge, the (844,17)↔(843,18) seam).
6. **The 14 untouched classes are GENUINELY isolated**: zero
   tail-conjugacy pairs at ≥200 shared perms (census-exhaustive), and
   in the full per-class sweep accounting every preconditioned firing
   on them dies at replay (5,384/5,384; touched classes all keep ≥2
   survivors). Nothing tail-anchored can reach them.
7. **The open discovery: conjugated cover twins** (s46). Canonicalizing
   used-loop covers over all 5,040 relabelings gives 194 → 180; every
   (842,19) class has a cover twin at (844,17) (byte-identical under
   swap 5↔6) — a PROVEN cover-preserving 2-unit allocation trade
   (S−2, #w3+2) that NO rule in any tier realizes. R-K7 trades one
   unit; this is the two-unit sibling, with specimens.
8. Working modes: anything > 30 min goes through `docs/SWEEP-QUEUE.md`
   (Andrew approves per-entry — don't launch, don't nag), and heavy
   tool-loop work is delegated to **Opus subagents** (Andrew
   2026-07-30); the orchestrator synthesizes and writes docs.

## The work menu (in priority order)

1. **Cover-twin anatomy → the realizing rule.** The three
   (842,19)↔(844,17) twin pairs: `up-8b8c8916a24a`~`up-dab493384582`
   (both in the blind spot), `up-331228e22360`~`up-756ff2ed09bd`,
   `lswap-9bd2a50baa0e`~`lswap-f4c2deec7c96`. Anatomize in theorem
   coordinates (doors/rotors/loops in the σ-aligned frame), derive the
   rewrite M-4a-style, oracle it on all three pairs, then conjugated
   sweep. This IS the R-compound/R-unit lift to n=7, with measured
   specimens. Reaching the blind-spot pair doubles as proof of concept.
2. **The alignment-free rule synthesizer** for the 14 zero-pair
   classes: build entry-replacement rules from the relabel-minimized
   entry-set difference between two classes instead of a shared
   traversal suffix (the aligned-frame extractor needs a shared head
   perm these classes cannot supply). Their nearest conjugated cover
   neighbors are 36–68 loops away — within the vocabulary's k ≤ 85
   range, so not out of reach in principle.
3. **Reversal-quotient audit**: recount the 862 under relabel+reversal
   canonicalization; annotate the tables (don't rewrite them — 9-column
   format is load-bearing). How much of the vocabulary is one move seen
   twice?
4. **Pending approvals, unchanged**: n=6 expanded sweep (SWEEP-QUEUE,
   ~2 h, 31.2 M replays — carries the closure-bias caveat); n=6 forward
   conjugated i4a R-sweep (~100 min); n=6 recomp2 520/450 bands.
5. **Still open, untouched**: run-losing-pair fine anatomy; M-4b/M-4d;
   ip=1; per-allocation NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (s46 additions first; each older one has bitten at least once)

- **Use `lswap_sym_edges_n7_ALL_union.tsv` for graph analyses.** The
  `_gen2_union` file is the union of the 8 gen-2 SHARDS only (this
  mis-scoped s45's "175 touched / 19 untouched" — truth was 177/17,
  now 180/14). ALL_union is a graph artifact, not provenance: one row
  per directed class pair, lexicographically smallest rule id; per-rule
  multiplicity lives in the source TSVs.
- **`canon_rule` quotients by S₇, NOT reversal.** Rule identity across
  tiers/frames needs relabel+reversal comparison — a23d031fbcd3 is
  R-K7 and no table shows it. Never conclude "new move shape" from
  canonical-id absence alone.
- **The empty-`ents_out` skip bug is FIXED** (s46,
  `loopswap_apply.py::run_apply_sym` — door-posting fallback). Before
  the fix such rules were silently never executed; only
  `51c13efc7a14` was affected in the whole vocabulary, and its
  fixed-path sweep (13 edges, 0 novel) is folded into ALL_union. If you
  ever see a rule "fire zero", check it was actually TRIED.
- **Replay-kill worsens with depth: 99.3% at the sub-256 band** (91.8%
  at ≥256, 99%+ at n=6). Never project yields from precondition
  counts — and never quote a rule count as reach.
- **Below 200 shared perms is unmined AND generic**: the census floor
  is 200; beneath it lies the s43 null band (64–255 overlaps generic
  endgame sharing), and extraction cost grows as tails shrink
  (`canon_rule` ~0.014 s/entry × 5,040 — the 240-rule band cost ~10 min
  memoized). Mining it needs a new census and a noise argument first.
- **SHARDING IS MANDATORY for n=7 apply-sym at scale**: ≤12,000 total
  rule-entries per shard (~1.2 GB peak; monolithic OOMs at 8–9 GB).
  Sharding is exact (disjoint relabeled-instance sets); both s45 and
  s46 matched dry-run sizing to the unit. Always `--dry-run` first.
- **Extraction from a closed corpus is biased toward returning
  closure** (s45 lesson) — re-extraction buys graph structure, not
  classes. The band was the last cheap widening; it's done.
- **The `oracle` CLI mode only runs `DEFAULT_SETS`** — arbitrary
  censuses need a driver calling `run_extract(..., do_oracle=True)`;
  memoize `canon_rule`.
- **Rule TSVs are 9-column s44 format — never add a 10th column**
  (`run_apply_sym` parses exactly 9 fields).
- **KNOWN-EDGE annotation hides rules from re-extraction** (the 18
  gen-2-absent s44 rules; two classes hang solely on them). Union rule
  tables when you want the full vocabulary.
- **m3_check ritual**: EVERY candidate ≤5906 (n=7) or ≤872 (n=6) goes
  through `m3_check.py` + the Rust validator before any novelty
  language; any FUTURE "novel" claim means re-pulling upstream first.
  Only Andrew decides publications.
- **Launch protocol**: > 30 min projected ⇒ SWEEP-QUEUE + Andrew's
  per-entry approval; < 5 min just run; between, time-box and watch.
  No `timeout(1)` on this Mac — background-launch and poll the PID.
- **The n=7 corpus spans THREE dirs** (`data/upstream5906` +
  `data/novel5906` + `data/novel5906b`), published union = 194.
- **Doc drift**: SURGERY-DESIGN §10.8 over §10.4; §11.6/§11.7 as-built
  for I4-A; JOURNAL s44–s46 as-built for I5 (applier docstring = spec).
- **Tight ≠ only; block ceiling binds at n=7; farm binary staleness;
  cap-at-target starves NRPA; equal-cost flood semantics; calibrated ≠
  proven; tautology check before celebrating a law** — all unchanged.
- **Session end ritual**: JOURNAL entry, `cargo test --release` green
  (139), clippy `-D warnings`, fmt, commit → `git pull --rebase` →
  push. When this handoff goes stale, write the successor and repoint
  CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s46/s45/s44.
3. `analysis/counting/loopswap_apply.py` docstring (I5 as-built);
   `docs/THEORY.md` §7; `docs/SURGERY-DESIGN.md` §11 (loop-cover
   frame, i4a, the M-4a rewrite-rule method the cover-twin work
   should follow).
4. `data/loopswap/` (rule tables + edge censuses; ALL_union is the
   graph file); `data/tailconj/` (pair censuses); `out/s46/` (scratch:
   band drivers, anatomies, per-class sweep accounting, conjugated
   cover censuses, the i4a-194 edges — gitignored, regenerable).
5. `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
