# Handoff — the s44+ front (fresh agent, start here)

Supersedes `HANDOFF-S41.md`. Read JOURNAL s43 (the discovery), s42
(why the old front saturated), s41/s41b (the published discoveries);
this is the two-page version with entry points and traps.

## State of the world in eight sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records (871,
   more 871s, 870, 5905, higher n) validate the engine, and the
   program ends only at full solution or maximal conclusion.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7):
   `length ≥ n! + (n−1)! + (n−3) + Λ`, every known record at equality.
   The project's 8 novel 5906 classes are published
   (superpermutators/superperm PR #50, merged by Houston; the
   canonical n=7 record shell is 92 classes / 8 allocations).
3. **The natural-move vocabulary has TWO complementary tiers.**
   Cover-PRESERVING moves (s40's rigid rotor⟷door rules R-compound /
   R-unit / R-K7, found by cover-collision census, executable via
   `i4a_apply.py`); and the s43 discovery: cover-CHANGING,
   door-preserving **loop-swap moves**, invisible to the census by
   construction, found by the **tail-conjugacy detector**.
4. **Tail-conjugacy** (s43, `analysis/counting/tail_conjugacy_census.py`):
   inequivalent classes sharing literal relabel-conjugate traversal
   suffixes. n=6: 108 NEW pairs share ≥480 of 720 perm visits (12
   pairs ≥540, max 563); n=7: 93 NEW pairs at ≥200 of 5040, nine of
   them >1000, and the 9 known rule edges isolated at exactly 2520.
5. **The deep pairs all carry one move shape** (s43,
   `tail_pair_anatomy.py`): same allocation, ALL doors identical,
   k cycle-disjoint 2-loops swapped for k others riding k swapped
   2-part rotors (k=3 at n=6, k=8 at n=7), both walks tight, objects
   in the unanchorable midgame band. The relabel-canonical
   swap-signature census collapses n=6's 108 pairs to **14 rigid
   rules, the top two with 46 and 20 instances** (R-L6a/R-L6b,
   `data/tailconj/tail_swap_sigs_n6.tsv`).
6. **Nothing in the swap tier is executable yet** — that is the s44
   front: doors identical ⇒ in i4a replay coordinates the edit is
   pure entry-set replacement; oracle = re-derive all observed pairs,
   then conjugated sweeps become novel-class generators with a
   vocabulary an order of magnitude richer than R-K7's.
7. **Anchored instruments and the cover census stay closed/saturated**
   at both n (s38b, s42) — the open front is tail-conjugacy +
   loop-cover coordinates.
8. Two agents share this repo: YOU (research — think, measure, build,
   write the JOURNAL) and an OPERATOR (runs anything > 30 min via
   `docs/SWEEP-QUEUE.md`; Andrew approves per-entry — don't launch,
   don't nag).

## The work menu (in priority order)

1. **Build the loop-swap applier** (i4a mode or sibling script):
   entry-set replacement + deterministic replay. Oracle: re-derive
   all 108 n=6 and 31 n=7 anatomized pairs byte-identically. Then
   literal + conjugated application of R-L6a (46 instances) across
   the n=6 archive; M3-gate every product; re-ask the (144,4)
   unreached-allocation question with the new vocabulary.
2. **Complete the swap-rule table**: signature census of the
   shallower n=6 tiers (437 groups at 420-perm tails, 1,114 at 360 —
   uncensused), and the n=7 pairs below 256 shared perms.
3. **Cross-length tail-conjugacy**: 5907s vs 5906s (`--all` over 95
   walks, minutes); a 5907→5906-tail relation would be the first
   length-crossing natural move.
4. **Pending approvals, unchanged:** n=6 forward conjugated R-sweep
   (~100 min); n=6 recomp2 520/450 bands (SWEEP-QUEUE).
5. **Still open, untouched:** run-losing-pair fine anatomy (3 R-K7
   pairs merge two runs); R-compound/R-unit lift to n=7; M-4b/M-4d;
   ip=1; per-allocation NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (each has bitten at least once; s43 additions first)

- **Tail-conjugacy depth tiers:** the rule tier is the DEEP end.
  Shallow cuts (≥256 perms at n=7) include distant relatives — up to
  82 loops swapped, doors changed. Quote the door-identical invariant
  only where measured (164/178 signature rows; all ≥400-perm n=6 and
  ≥500-perm n=7 pairs). Generic walks share 64–127-perm endgame tails
  routinely — a collision is only interesting past the null model
  (JOURNAL s43 has the n=7 histogram).
- **Swap signatures are relabel+side canonical but context-free:**
  equal signature = same moved objects, NOT yet a firing condition.
  Replay-sufficiency ≫ precondition (s41 trap, still in force):
  never project applier yields from signature counts.
- **Palindromy differs by n:** the deep n=7 pairs are relabel-
  palindromes (head share = tail share, symmetric window); the n=6
  pairs share ONE end. Don't assume either shape at a new n.
- **Launch protocol:** > 30 min projected ⇒ SWEEP-QUEUE entry +
  Andrew's per-entry approval. < 5 min just run; between, time-box
  and watch. Heartbeats are part of any long run's launch.
- **`m3_check --build-index` writes to the COMMITTED per-n index
  path** — never use it for side indexes; write the TSV directly.
- **The n=7 corpus spans TWO local dirs** (`data/upstream5906` +
  `data/novel5906`, published union = 92; `data/upstream5907` where
  relevant). Quoting "84" is stale.
- **Canonical frame:** 2-loop ids and rule objects are NOT
  relabel-invariant; closure claims need the conjugated (`apply-sym`)
  version. Tail-pair anatomy diffs live in the pair's ALIGNED frame —
  cross-pair comparison only via the canonical signature.
- **Tight ≠ only:** deficit > 0 walks are legal; a Λ-tripwire hit on
  a found walk is banner-worthy structure, not a solver bug.
- **The block ceiling binds at n=7, not the anchor**; quote OBSERVED
  anchors. Round-robin probe before every projection.
- **Farm binary staleness:** rebuild + reship after ANY change to
  `src/tailatsp.rs`/`src/corpus.rs` (`docs/OPERATIONS.md`); shipped:
  `bdc9625` (s43 was Python-only — no reship needed).
- **Doc drift:** SURGERY-DESIGN §10.8 wins over §10.4; §11.6/§11.7
  are as-built truth for I4-A.
- **Don't re-hope extraction:** w2-seam extraction is +6-lossy
  (pinned). The compound/swap tiers are reached by rule application,
  not anchored move widening.
- **Calibrated ≠ proven:** the loop-count INEQUALITY is proven;
  corpus tightness, census profiles, M-R laws are calibrated. Say
  "published" for n=7 claims (published includes our 8).
- **Tautology check before celebrating a new law** — s43 passed it by
  measuring the full pairwise null distribution first; keep doing
  that.
- **Equal-cost flood semantics:** ~half of single recompositions are
  equal-cost non-events; I4/swap products are equal-length BY
  CONSTRUCTION — events are M3-novel classes and unreached
  allocations only.
- **Cap-at-target starves NRPA** (hunt 874, collect ≤872).
  **16 GB local RAM** — don't stack RAM-heavy work on a sweep.
- **Session end ritual:** JOURNAL entry (fold `done` queue results),
  `cargo test --release` green (139), clippy `-D warnings`, fmt,
  commit → `git pull --rebase` → push. Leave cold-start ready; when
  this handoff goes stale, write the successor and repoint CLAUDE.md
  + agent docs.
- **Publishing:** via the `../superperm` clone (fork `fork` =
  abalint/superperm, branch + PR; PR #50 is the precedent). Always
  `git pull` and re-verify novelty against CURRENT contents; only
  Andrew decides when to publish.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s43/s42/s41b/s41 (the two vocabulary tiers and
   how each was found).
3. `docs/THEORY.md` §7 (theorem); `docs/SURGERY-DESIGN.md` §11
   (loop-cover frame, rules, I4-A as-built).
4. `analysis/counting/tail_conjugacy_census.py` +
   `tail_pair_anatomy.py` docstrings, and `data/tailconj/` TSVs.
5. `data/novel5906/NOTE.md` (published discoveries);
   `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
