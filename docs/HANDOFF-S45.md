# Handoff — the s46+ front (fresh agent, start here)

Supersedes `HANDOFF-S44.md`. Read JOURNAL s45 (the closure negative and
the lesson attached to it), s44 (the discovery event and the I5
instrument), s43 (the detector); this is the two-page version with
entry points and traps.

## State of the world in eight sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records and
   record-shell structure validate the engine; the program ends only
   at full solution or maximal conclusion.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7). The
   n=7 record shell is **194 published classes / 8 allocations** —
   ALL merged into superpermutators/superperm: 84 pre-project +
   our 8 (s41, PR #50) + our 102 (s44, PR #51). 110 of the 194 (57%)
   are this project's discoveries. Upstream was re-pulled 2026-07-30
   at commit `235a074` and is unchanged.
3. **The natural-move vocabulary is THREE tiers, all executable:**
   cover-preserving rules (R-compound/R-unit/R-K7, `i4a_apply.py`,
   s40/s41); the door-preserving **loop-swap tier**
   (`loopswap_apply.py` = I5: extract/oracle/apply-sym, s43/s44); and
   the swap+door composites (allocation-crossing seams, same tables).
4. **The loop-swap tier is now EXHAUSTED on the 194-class shell** (s45).
   The full second-generation vocabulary — **604 directed rules**
   (`data/loopswap/rules_n7_a4840_gen2.tsv`, 541 new + 63 s44) plus the
   18 gen-2-absent s44 rules = **622 rules** — swept conjugated
   (5,040 relabelings × both orientations × 194 classes, 87,276
   candidate replays) gives **0 novel, 0 shorter: FIXED POINT AT
   ITERATION 1**. n=6 was already closed under its deep rules.
5. **What the second generation bought is the graph, not classes**:
   the natural-move edge census goes **433 → 1,675 undirected edges
   (3.9×), 175 of 194 classes touched, 20 components with a 75-node
   giant** (n=6's 9,654 edges have no giant — 3,909 components,
   largest 44). Committed union:
   `data/loopswap/lswap_sym_edges_n7_gen2_union.tsv`.
6. **Extraction/oracle still hold perfectly**: 1,003/1,003 extractable
   pairs re-derive byte-identically; the (n−1)·loops law has **zero
   exceptions** across all 516 door-free gen-2 rules (|ents_out| =
   |ents_in| = 6k, k = 1…85). 165 of 1,168 pairs are unextractable —
   all one reason, no shared head perm — but **143 of those 165 are
   still re-found as sweep edges**, so that gap is a frame limitation,
   not a move limitation.
7. **The front has moved.** Item 1 of the old menu is DONE and closed
   negative. New classes now need a genuinely different move tier or a
   source outside the current closure — not another re-extraction.
8. Two agents share this repo: YOU (research) and an OPERATOR (runs
   anything > 30 min via `docs/SWEEP-QUEUE.md`; Andrew approves
   per-entry — don't launch, don't nag).

## The work menu (in priority order)

1. **The 352 sub-256 pairs**: the s45 extraction used the s44 cut
   (`--min-perms 256`), which admitted 1,168 of the 1,520 NEW pairs in
   `data/tailconj/tail_pairs_n7_a4840_194.tsv`. The 352 pairs at
   200–255 shared perms are the last un-mined part of that census and
   cost minutes (extract + oracle + sharded sweep). Expect closure;
   run it to know, not to hope.
2. **The three near-pure door-move rules** in the gen-2 table
   (|ents_out| ∈ {0,1} with a 1–2 door diff) — the first objects of
   that shape at n=7, and door-churn with ~0 entry churn is exactly
   what crossed allocations at s41. Anatomize them against R-K7.
3. **The 19 untouched classes** (194 − 175): no loop-swap rule reaches
   them. Which allocations are they in, and what does that say about
   where the vocabulary is blind?
4. **The queued n=6 expanded sweep** (SWEEP-QUEUE, pending approval,
   ~2 h local): 30 shallow-tier rules, 31.2 M candidate replays. It
   now inherits the s45 closure-bias caveat — size the expectation
   down before quoting it as a discovery instrument.
5. **Pending approvals, unchanged**: n=6 forward conjugated i4a
   R-sweep (~100 min); n=6 recomp2 520/450 bands.
6. **Still open, untouched**: run-losing-pair fine anatomy;
   R-compound/R-unit lift to n=7; M-4b/M-4d; ip=1; per-allocation
   NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (s45 additions first; each older one has bitten at least once)

- **SHARDING IS MANDATORY for n=7 apply-sym at gen-2 scale.** 604
  rules × 5,040 relabelings = 3.04 M conjugated instances ≈ **8–9 GB;
  a single process OOMs.** Shard by rule at ≤12,000 total rule-entries
  (~1.2 GB peak). Sharding is exact — distinct canonical rules have
  disjoint relabeled-instance sets — and s45 proved it: the sharded
  replay total matched the dry-run sizing to the unit (47,929). Always
  `--dry-run` first to size, then shard.
- **Second-generation extraction from a closed corpus is biased
  toward returning closure.** Gen-2 rules are extracted from pairs in
  the enlarged corpus, and the enlarged corpus IS the first rule's
  closure — so the vocabulary is built from moves that stay inside it.
  **s44's 102 classes were a corpus-SIZE artifact, not a rule-quality
  one**; `ab88abce72ba` is not better than its 540 siblings, it just
  ran first on a 92-class shell. Never quote "re-extraction is the
  highest-expected-value instrument" again.
- **The loop-swap tier is EXHAUSTED on the 194 corpus.** Any novelty
  hope pinned on it is stale. Sweeping it again produces edges, not
  classes.
- **Where the s45 artifacts are**: rules
  `data/loopswap/rules_n7_a4840_gen2.tsv` (9-column s44 format —
  do NOT add a 10th column, `run_apply_sym` parses exactly 9 fields);
  union edge census
  `data/loopswap/lswap_sym_edges_n7_gen2_union.tsv`. Per-shard and
  per-iteration edge TSVs must be UNIONED for graph analyses; the
  committed union file is the one to use.
- **The `oracle` CLI mode only runs `DEFAULT_SETS`** — to oracle an
  arbitrary census you must call `run_extract(..., do_oracle=True)`
  from a driver. Extraction is O(n!) per canonical rule; memoize
  `canon_rule` or it dominates.
- **KNOWN-EDGE annotation hides rules from re-extraction**: 18 of the
  81 s44 rules did not reappear in gen-2 because
  `tail_conjugacy_census.load_known_edges` now loads the committed
  loop-swap edge TSVs, so their source pairs are filtered out of the
  NEW set. That is annotation drift, not a lost rule — union the rule
  tables when you want the full vocabulary (622, not 604).
- **Frontier-only closure iteration is valid** — s45 confirmed it
  directly by re-sweeping the 63 known rules over all 194 classes
  unsharded (0 novel). But the edge TSVs it produces are
  per-iteration; union them.
- **Rule ≠ signature, and precondition ≠ firing**: >91% of
  preconditioned conjugated firings are replay-killed at gen-2 scale
  (99%+ at n=6). Never project yields from precondition counts.
- **The aligned-frame extractor needs one shared head perm**; 165 of
  1,168 n=7 gen-2 pairs and 4 of 1,234 n=6 shallow pairs lack it.
  Don't quote "every pair extracts" without that asterisk — and don't
  conclude those pairs are unreachable (143/165 are reachable).
- **`m3_check --build-index` writes to the COMMITTED per-n index
  path** — side indexes are written directly (keep the header line,
  `load_index` skips row 1). SUPPLEMENTARY[7] = novel5906 +
  novel5906b indexes; gate coverage of the published 194 is complete.
- **Any FUTURE "novel" claim means re-pulling upstream first** (new
  community solutions can land any time); only Andrew decides
  publications.
- **Launch protocol:** > 30 min projected ⇒ SWEEP-QUEUE + Andrew's
  per-entry approval. < 5 min just run; between, time-box and watch.
  (No `timeout(1)` on this Mac — background-launch and poll the PID.)
- **The n=7 corpus spans THREE local dirs** (`data/upstream5906` +
  `data/novel5906` + `data/novel5906b`), published union = **194**.
  Quoting "84" or "92" is stale.
- **Tail-conjugacy depth tiers:** the deep tier is rigid; ≥256-perm
  cuts include distant relatives (up to 85 loops, door changes) —
  those extract and oracle fine but are composites, not the local
  move. Generic endgame sharing is 64–255 perms (null model, s43).
- **Canonical frame:** rule objects are not relabel-invariant; closure
  claims need the conjugated sweep, and cross-pair comparison goes
  through the n!-canonical rule id.
- **Doc drift:** SURGERY-DESIGN §10.8 wins over §10.4; §11.6/§11.7
  are as-built truth for I4-A; JOURNAL s44+s45 are as-built truth for
  I5 (no design doc — the applier docstring is the spec).
- **Tight ≠ only; the block ceiling binds at n=7; farm binary
  staleness; cap-at-target starves NRPA; equal-cost flood semantics;
  don't re-hope extraction; calibrated ≠ proven; tautology check
  before celebrating a law** — all unchanged, all still in force.
- **Session end ritual:** JOURNAL entry (fold `done` queue results),
  `cargo test --release` green (139), clippy `-D warnings`, fmt,
  commit → `git pull --rebase` → push. When this handoff goes stale,
  write the successor and repoint CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s45/s44/s43 (the closure negative, the discovery
   event, the detector).
3. `analysis/counting/loopswap_apply.py` docstring (I5 as-built);
   `docs/THEORY.md` §7; `docs/SURGERY-DESIGN.md` §11 (loop-cover
   frame, i4a).
4. `data/novel5906b/NOTE.md` (the 102); `data/loopswap/` (rule tables
   + edge censuses, incl. the gen-2 pair); `data/tailconj/` (pair
   censuses).
5. `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
