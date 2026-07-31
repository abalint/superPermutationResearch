# Handoff — the s49+ front (fresh agent, start here)

Supersedes `HANDOFF-S47.md`. Read JOURNAL s48 (the re-closure + the
Δalloc=0 cover twin and its rule), s47 (R-BND + the 4 novel classes),
s46 (band closure, cover twins); this is the two-page version with
entry points and traps.

## State of the world in nine sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records and
   record-shell structure validate the engine.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7). The
   published n=7 shell is **194 classes / 8 allocations** (upstream
   `superpermutators/superperm` at `235a074`); the PROJECT shell is
   **198**: s47's 4 novel (843,18) classes are **SUBMITTED as PR #52**
   (`data/novel5906c/`, still open as of 2026-07-30 — on merge, flip
   NOTE.md to PUBLISHED and the published count to 198 here and in
   CLAUDE.md).
3. **The 198 is RE-CLOSED under every tier (s48)**: fixed point under
   all loop-swap rules, the i4a tier (edge set unchanged at 26/13),
   and R-BND (32 directed / 8 undirected — never quote s47's 30/16,
   which double-counts `NEW-…` pseudo-vertices). Nothing escapes the
   (842,19)–(843,18)–(844,17) pocket, and no single-rule composite
   does either.
4. **The vocabulary is 398 distinct moves = 864 directed rules**:
   the 862 (three committed tables) + the s48 pair
   `4004c6042131`/`9233133e9c39` (`data/loopswap/rules_n7_s48_covertwin.tsv`)
   — a door-free 48-entry pure loop-swap, oracle-verified, a closed
   2-orbit under S₇×ι×τ with no image among the 862. It realizes the
   **first Δalloc=0 conjugated cover twin**: `rbnd-0dad` ~ `rbnd-2641`,
   both (843,18). `rule_annotation_n7.tsv` still annotates only the
   862.
5. **Cover census over the 198: 198 → 180** — the 4 novel classes add
   ZERO new canonical covers; each (842,19)↔(844,17) twin family
   absorbed exactly its bridging (843,18) intermediate (the twins stay
   direct-edge-less in every tier; R-BND resolves them only as 2-step
   paths). Kristan's class is cover-isolated from all four novel
   classes, absent from the R-BND graph, and **provably unreachable
   from them by any single loop-swap rule** (entry-diff 531 to each;
   531 ∤ 6) — the (843,18) pocket splits {Kristan} ⊔ {the four}.
6. **Rigidity theorem** (s47, proven twice): a 9-column rule replays
   from the source walk's start perm, forcing the relabeling uniquely;
   moves needing a different frame need an explicit re-rooting
   component (R-BND has one; the format cannot carry one — never add
   a 10th column). s48's extraction failures confirm it in the wild:
   12/16 new tail-conjugate pairs fail with exactly the re-rooting
   obstruction. Rule synthesis is TOTAL, hence vacuous — reach means
   something only for rules extracted elsewhere.
7. **R-BND precondition law, corrected (s48)**: FWD fires exactly once
   per tight orientation; REV fires on 396/396 n=7 orientations too —
   what varies is MULTIPLICITY (1 or 2). The 4 novel classes are the
   only orientation-asymmetric ones (2/1) — a mid-bridge fingerprint.
   At n=6, REV multiplicity ≈2 nearly always and the only survivors
   are the M-4a R-unit edge (R-BND ⊃ R-unit).
8. **The blind spot is 12 and METRIC**: min admissible entry-diff ≥432
   for untouched vs median 48 / max 384 for touched — zero overlap;
   s48 added no edge touching it. Single rules provably can't cross;
   the only live idea is composition chains through intermediates.
9. Working modes: anything > 30 min goes through `docs/SWEEP-QUEUE.md`
   (Andrew approves per-entry — don't launch, don't nag); heavy
   tool-loop work is delegated to **Opus subagents** (Andrew
   2026-07-30); the orchestrator re-verifies gates itself (s48: grep
   novelty from tables + re-fire with the committed applier + scan
   shard logs), synthesizes, and writes docs.

## The work menu (in priority order)

1. **Blind-spot composition chains.** 12 classes, nearest touched
   neighbours 36–74 loops away; the metric law forbids single rules;
   s48 proved the pocket contributes no bridge. Search short composite
   paths through intermediates — the union graph is
   `lswap_sym_edges_n7_ALL_union.tsv` (2,006 undirected, s48 rows
   included) + `rbnd_edges_n7.tsv` (normalize node names by hash12
   before any cross-tier union).
2. **PR #52 watch** (Andrew's call throughout): on merge flip
   `data/novel5906c/NOTE.md` → PUBLISHED, published shell → 198 in
   CLAUDE.md + this file. Check with
   `gh pr view 52 -R superpermutators/superperm`.
3. **R-BND extensions**: boundary trades at w≥4 doors; use the REV
   orientation-asymmetry fingerprint as a cheap mid-bridge detector
   (does any n=6 archive class show it? full per-walk census sizes
   ~22 min); iterate R-BND between loop-swap generations.
4. **Pending approvals, unchanged** (SWEEP-QUEUE): n=6 expanded
   loop-swap sweep (~2 h); n=6 forward conjugated i4a sweep
   (~100 min); n=6 recomp2 520/450 bands.
5. **Still open, untouched**: run-losing-pair fine anatomy; M-4b/M-4d;
   ip=1; per-allocation NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (s48 additions first; each older one has bitten at least once)

- **Node-naming across tiers**: `rbnd_edges_n7.tsv` spells the same
  classes three ways (`NEW-<hash>`, `rbnd-NOVEL-5906-<hash>.txt`,
  `5906.rbnd-<hash>.txt`). Normalize by hash12 before any graph union
  or union-find dies double-counting.
- **`tail_conjugacy_census.py`'s KNOWN-EDGE column is stale**: it
  loads only the two base edge tables (~340 edges short). Recompute
  annotations against ALL_union + the R-BND tier.
- **Aligned-frame cover intersection ≠ canonical-cover equality**
  (`0dad~2641`: 134/142 aligned, canonical-identical). Don't read one
  off the other.
- **The R-BND 9-column TSV is promiscuous as well as weak**: its
  door-posting encoding generates ~90% of a mixed sweep's replays for
  nothing. Use `rbnd.py` intrinsic modes; skip the TSV rows in
  loop-swap sweeps (R-BND is at fixed point independently).
- **Sweep vocabulary ≠ the three tables anymore**: union in
  `rules_n7_s48_covertwin.tsv` (864 directed). Quote the vocabulary
  as **398 objects**.
- **The 4 novel classes are SUBMITTED, not published** — published
  shell is 194 until PR #52 merges; upstream novelty claims still
  require a fresh `git pull` in `../superperm` first. m3_check's
  index includes them (198), so re-finding them exits 0, not 2.
- **Closure language**: say which corpus explicitly — "over the 194"
  vs "over the 198". As of s48 both are closed under all known tiers.
- **Sharding is mandatory for n=7 apply-sym regardless of corpus
  size** (≤12,000 rule-entries/shard): the 8–9 GB OOM is driven by
  the rule instance table, not the corpus. Always `--dry-run` first
  (dry-run-exact 4 sessions running).
- **`tail_conjugacy_census.py` takes dirs space-separated;
  `loopswap_apply.py --dirs` comma-separated.**
- **Swap-signature equality is a carrier invariant, not a move
  invariant** (one R-BND move, three signatures at n=7 — s48).
- **Replay-kill worsens with depth** (97.8–99.998%). Never project
  yields from precondition counts (s48: 111/862 rules preconditioned,
  1 produced a survivor).
- **Extraction/synthesis from a closed corpus returns closure**; and
  synthesis is TOTAL (s47) — reach claims need externally-derived
  rules. Pairs touching genuinely-new classes are the exception
  (that's how the s48 rule was found legitimately).
- **`canon_rule` quotients by S₇ only**; `revquot_audit.py`'s numpy
  canonicalizer does 862 rules in 42 s — never the ~72-min naive loop.
- **The `oracle` CLI mode only runs `DEFAULT_SETS`**; drivers call
  `run_extract(..., do_oracle=True)`; memoize `canon_rule`.
- **Rule TSVs are 9-column s44 format — never add a 10th column.**
- **KNOWN-EDGE annotation hides rules from re-extraction** — union
  rule tables when you want the full vocabulary.
- **m3_check ritual**: EVERY candidate ≤5906 (n=7) or ≤872 (n=6) goes
  through `m3_check.py` + the Rust validator before any novelty
  language; the orchestrator re-runs gates itself. Only Andrew
  decides publications.
- **Launch protocol**: > 30 min projected ⇒ SWEEP-QUEUE + Andrew's
  per-entry approval; < 5 min just run; between, time-box and watch.
  No `timeout(1)` on this Mac — background-launch and poll the PID
  (or `caffeinate -w <pid>` to block on it).
- **The n=7 corpus spans FOUR dirs** (`data/upstream5906` +
  `data/novel5906` + `data/novel5906b` + `data/novel5906c`);
  published union = 194, project union = 198.
- **Doc drift**: SURGERY-DESIGN §10.8 over §10.4; §11.6/§11.7
  as-built for I4-A; JOURNAL s44–s48 as-built for I5;
  `docs/RBND-RULE.md` as-built for R-BND (edge counts per s48).
- **Tight ≠ only; block ceiling binds at n=7; farm binary staleness;
  cap-at-target starves NRPA; equal-cost flood semantics; calibrated ≠
  proven; tautology check before celebrating a law** — all unchanged.
- **Session end ritual**: JOURNAL entry, `cargo test --release` green
  (139), clippy `-D warnings`, fmt, commit → `git pull --rebase` →
  push. When this handoff goes stale, write the successor and repoint
  CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s48/s47/s46.
3. `docs/RBND-RULE.md` (the boundary-trade tier, rigidity theorem);
   `docs/THEORY.md` §7; `analysis/counting/loopswap_apply.py`
   docstring (I5 as-built); `docs/SURGERY-DESIGN.md` §11.
4. `data/loopswap/` (rule tables incl. `rules_n7_s48_covertwin.tsv`;
   ALL_union = loop-swap graph at 2,006 edges; `rbnd_edges_n7.tsv` =
   R-BND tier; `rbnd_rev_census_n7.tsv`; the annotation TSVs);
   `data/tailconj/` (`tail_pairs_n7_a4840_198.tsv` supersedes _194);
   `data/novel5906c/NOTE.md`; `out/s48/` (scratch, regenerable).
5. `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
