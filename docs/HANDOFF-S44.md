# Handoff — the s45+ front (fresh agent, start here)

Supersedes `HANDOFF-S43.md`. Read JOURNAL s44 (the discovery event),
s43 (the detector), s42 (why the census saturated); this is the
two-page version with entry points and traps.

## State of the world in eight sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records and
   record-shell structure validate the engine; the program ends only
   at full solution or maximal conclusion.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7). The
   n=7 record shell is **194 published classes / 8 allocations** —
   ALL merged into superpermutators/superperm: 84 pre-project +
   our 8 (s41, PR #50) + our 102 (s44, PR #51, merged 2026-07-30).
   110 of the 194 (57%) are this project's discoveries
   (`data/novel5906/` + `data/novel5906b/`).
3. **The natural-move vocabulary is now THREE tiers, all executable:**
   cover-preserving rules (R-compound/R-unit/R-K7, `i4a_apply.py`,
   s40/s41); the s43/s44 cover-changing door-preserving **loop-swap
   tier** (`loopswap_apply.py` = I5: extract/oracle/apply-sym); and
   the swap+door composites (the n=7 allocation-crossing seams —
   extracted and oracled, in the same rule tables).
4. **The loop-swap move at entry level**: in replay coordinates
   (start, entry sets, doors) the move is pure entry-set replacement —
   exactly (n−1) entries per swapped loop, doors untouched. Rules are
   extracted literally from tail-conjugate pairs in their aligned
   frame and canonicalized over n! relabelings. Oracle: 1,300/1,300
   extractable pairs re-derive byte-identically (s44).
5. **The vocabulary collapses**: n=6 = 3 directed rules for the deep
   tier (one, `9a9c0f8835c0`, covers 104/108 deep + 91% of the 1,230
   shallow pairs), 33 for the full ≥360 tier; n=7 = 81 directed. The
   s43 14-signature census counted context shadows, not moves.
6. **One rule made 102 novel classes**: `ab88abce72ba` (pure 4-loop
   swap from ONE 409-shared-perm pair) swept conjugated over the
   published 92 and iterated frontier-wise → 60+34+8+0 (fixed point).
   n=6 is CLOSED under its deep rules (0 novel; 9,654 edges, 54% of
   the archive touched, 3,909 components, largest 44).
7. **The next multiplier is visible and unrun**: the 194-class corpus
   census shows **1,520 NEW tail-conjugate pairs** (up from 93), some
   sharing 86% of the walk — second-generation rule extraction from
   `data/tailconj/tail_pairs_n7_a4840_194.tsv` is s45 item 1.
8. Two agents share this repo: YOU (research) and an OPERATOR (runs
   anything > 30 min via `docs/SWEEP-QUEUE.md`; Andrew approves
   per-entry — don't launch, don't nag).

## The work menu (in priority order)

1. **Second-generation n=7 extraction**: `loopswap_apply.py extract`
   on the 1,520-pair census (dirs upstream5906,novel5906,novel5906b),
   oracle, dedupe vs the 81 known rules, conjugated sweep to fixed
   point, gate everything (validate + m3_check; the M3 gate already
   covers the 102). Watch for: rules extracted FROM new-class pairs
   firing back into unexplored corners; any door-changing composite
   crossing to an unseen allocation.
2. **The queued n=6 expanded sweep** (SWEEP-QUEUE, pending approval,
   ~2 h local): 30 shallow-tier rules, 31.2M candidate replays.
   After it: n=6 second-generation census (enlarged-graph pairs).
3. **Pending approvals, unchanged**: n=6 forward conjugated i4a
   R-sweep (~100 min); n=6 recomp2 520/450 bands.
4. **Still open, untouched**: run-losing-pair fine anatomy;
   R-compound/R-unit lift to n=7; M-4b/M-4d; ip=1; per-allocation
   NRPA/beam; Track C v2's 2.4× overhead cut.
   (Publication of the 102 is DONE — PR #51 merged 2026-07-30.)

## Traps (s44 additions first; each older one has bitten at least once)

- **The 102 are PUBLISHED (PR #51 merged).** m3_check's coverage of
  the 194 published classes = upstream index (84) + novel5906 index
  (8) + novel5906b index (102, via SUPPLEMENTARY) — complete, no
  rebuild needed. But any FUTURE "novel" claim still means re-pulling
  upstream first (new community solutions can land any time); only
  Andrew decides publications.
- **Frontier-only closure iteration is valid** (instances are fixed;
  old sources were fully swept), but the edge TSVs it produces are
  per-iteration — union them for graph analyses
  (`data/loopswap/lswap_sym_edges_n7*.tsv`).
- **Rule ≠ signature, in the collapse direction now**: distinct s43
  signatures can be the SAME entry-level rule (rotor compositions are
  carrier context). Precondition ≠ firing: >99% of preconditioned
  conjugated firings are replay-killed. Never project yields from
  precondition counts (s41 trap, two tiers deep now).
- **The aligned-frame extractor needs one shared head perm**; 4 of
  1,234 n=6 shallow pairs lack it and are unextractable. Don't quote
  "every pair extracts" without that asterisk.
- **`m3_check --build-index` writes to the COMMITTED per-n index
  path** — side indexes are written directly (the novel5906b index
  was; keep the header line, `load_index` skips row 1).
- **Launch protocol:** > 30 min projected ⇒ SWEEP-QUEUE + Andrew's
  per-entry approval (the s44 n=6 expanded sweep is queued, NOT run).
  < 5 min just run; between, time-box and watch.
- **The n=7 corpus now spans THREE local dirs**
  (`data/upstream5906` + `data/novel5906` + `data/novel5906b`),
  published union = **194**. Quoting "84", "92", or "unpublished 102"
  is stale.
- **Tail-conjugacy depth tiers:** the deep tier is rigid; ≥256-perm
  cuts include distant relatives (up to 82 loops, door changes) —
  those extract and oracle fine (s44) but are composites, not the
  local move. Generic endgame sharing is 64–255 perms (null model,
  JOURNAL s43).
- **Canonical frame:** rule objects are not relabel-invariant; closure
  claims need the conjugated sweep, and cross-pair comparison goes
  through the n!-canonical rule id.
- **Doc drift:** SURGERY-DESIGN §10.8 wins over §10.4; §11.6/§11.7
  are as-built truth for I4-A; JOURNAL s44 is as-built truth for I5
  (no design doc — the applier docstring is the spec).
- **Tight ≠ only; the block ceiling binds at n=7; farm binary
  staleness; cap-at-target starves NRPA; equal-cost flood semantics;
  don't re-hope extraction; calibrated ≠ proven; tautology check
  before celebrating a law** — all unchanged from HANDOFF-S43, all
  still in force.
- **Session end ritual:** JOURNAL entry (fold `done` queue results),
  `cargo test --release` green (139), clippy `-D warnings`, fmt,
  commit → `git pull --rebase` → push. When this handoff goes stale,
  write the successor and repoint CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s44/s43/s42 (the executable swap tier and how it
   was found).
3. `analysis/counting/loopswap_apply.py` docstring (I5 as-built);
   `docs/THEORY.md` §7; `docs/SURGERY-DESIGN.md` §11 (loop-cover
   frame, i4a).
4. `data/novel5906b/NOTE.md` (the 102); `data/loopswap/` (rule
   tables + edge censuses); `data/tailconj/` (pair censuses).
5. `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
