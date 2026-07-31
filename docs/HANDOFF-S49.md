# Handoff — the s50+ front (fresh agent, start here)

Supersedes `HANDOFF-S48.md`. Read JOURNAL s49 (blind-spot proofs, the
w4 theorems, the lift shells), s48 (re-closure + the Δalloc=0 cover
twin), s47 (R-BND + the 4 novel classes); this is the two-page version
with entry points and traps.

## State of the world in ten sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records and
   record-shell structure validate the engine.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7). The
   published n=7 shell is **194 classes / 8 allocations** (upstream
   `superpermutators/superperm` at `235a074`); the PROJECT shell is
   **198**: s47's 4 novel (843,18) classes are **SUBMITTED as PR #52**
   (`data/novel5906c/`, still open as of 2026-07-30 — on merge, flip
   NOTE.md to PUBLISHED and the published count to 198 here and in
   CLAUDE.md). All 198 are pure-w3 (re-censused s49).
3. **The 198 is closed under every tier** (s48), and as of s49 the
   **blind spot's isolation is a PROOF**: depth-1 exhaustive (0 hits,
   all 4,354,560 rule instances × 9,456 rigidity-forced frames) and
   targeted fused depth-2 (0 over 4,249,684 fused pairs + a 5.2×10⁹-pair
   direction-symmetric sumset). Sequential chains are vacuous at every
   depth given closure (the s49 argument); the ONE remaining loop-swap
   idea is the queued untargeted fused sweep (escape to a class OUTSIDE
   the 198).
4. **Targeted composition needs NO replay**: rigidity forces the frame
   per (source, target) orientation pair and replay is deterministic,
   so the required edit is an identity and reachability is
   set-membership (`analysis/counting/s49/fuse.py`). The
   97.8–99.998% replay-kill statistic does not apply to that search.
5. **The vocabulary is 398 distinct moves = 864 directed rules across
   FIVE tables** (never "the four"): the 862 + the s48 pair in
   `rules_n7_s48_covertwin.tsv`. `rule_annotation_n7.tsv` now covers
   all 864 (object #398 = E0397). Rule sizes run to **|ents_out| = 534**
   (the old "max 228" is wrong); Δ = −Δ exactly — the vocabulary is
   closed under reversal as absolute edits.
6. **Two w≥4 theorems (s49)**: a door-for-boundary unit trade has
   Δlen = 3 − w, so R-BND's w=3 is FORCED and the w4 FWD trade IS the
   record-break move (never fires naturally 830/830 + 396/396; 100%
   replay-dead when forced); and no length-conserving w≥4 boundary
   trade exists (needs two loop closures from one door deletion —
   impossible). The REV-w4 lift (Δlen = +1, 10–16% survival) built the
   first w4-bearing shells: `data/lift873_n6/` (448 classes) and
   `data/lift5907_n7/` (232 classes, six d4=1 allocations no known n=7
   string occupied). Lift-and-drop is an exact involution — the shells'
   value is as INTERMEDIATES for the queued sweeps.
7. **The n=6 REV fingerprint is real but one-sided**: 313 classes
   (1.42%) carry the s48 mirror-consistent profile — perfect on the
   (142,6) FWD side of the four R-unit edges, zero on the (143,5) REV
   side, allocation-conditional (0 in the records class). A second
   asymmetry (`F_REVEND ≠ R_REVSTART`) is EXACTLY the 415 w4-bearing
   classes: the w4 door itself blocks R-BND's REV-START slot (821/821).
   Census: `data/loopswap/rbnd_rev_census_n6_full.tsv`.
8. **The blind spot is 12, committed, and structurally lopsided**:
   `data/loopswap/blindspot_n7.tsv` (11 of 12 in (844,17), one at
   (838,23)); exact admissible-frame metrics in
   `blindspot_admdiff_n7.tsv`. `up-1b8244ba04bb` is the outlier: 23
   doors, ZERO door-identical partners in the 198 (no door-free fusion
   at any depth can reach it), nearest neighbour a novel5906c class.
   Kristan-to-novel is impossible with corrected numbers: admissible
   edits are 622–735 entries PLUS 15–18 doors (never quote 531).
9. **The Δalloc=0 cover twin** (`rbnd-0dad` ~ `rbnd-2641`, both
   (843,18)) is realized by rule object #398; cover census 198 → 180;
   Kristan's class is cover-isolated from the four novel classes and
   absent from the R-BND graph; nothing escapes the
   (842,19)–(843,18)–(844,17) pocket under any single rule or depth-1
   sequential composite.
10. Working modes: anything > 30 min goes through `docs/SWEEP-QUEUE.md`
    (Andrew approves per-entry — don't launch, don't nag); heavy
    tool-loop work is delegated to **Opus subagents**; the orchestrator
    re-verifies every load-bearing claim itself before writing docs.

## The work menu (in priority order)

1. **The four queued s49 sweeps** (all `approved: NO` — Andrew's call):
   - **lifted-5907 loop-swap sweep** (~49 min extrapolated, dry-run
     first) — the strategic one: a loop-swap move inside the w4 5907
     shell followed by the FWD-w4 drop (Δlen = −1) is the only known
     composite shape that leaves the pocket's length band at all.
   - **lifted-873 control** (~10 min) — same question at n=6.
   - **full sumset** (~84 min) + **untargeted fused sweep** (~33 h
     single-core / ~1.4 h farm) — close fused depth 2 completely.
   - The two loopswap sweeps need a small `--record` parameter patch to
     `loopswap_apply.py` (hardcoded 872/5906 silently discards
     above-record products — vacuous 0 without it).
2. **PR #52 watch**: `gh pr view 52 -R superpermutators/superperm`; on
   merge flip `data/novel5906c/NOTE.md` → PUBLISHED, published shell →
   198 here + CLAUDE.md.
3. **The w4 demotion trade** `(S+1, d3+1, d4−1)`, Δlen = 0 — the only
   length-conserving w4 move; connects occupied n=6 allocations
   (140,6,1)×388 ↔ (141,7)×4; NO instrument implements it.
4. **`up-1b8244ba04bb` anatomy** (the 23-door blind outlier).
5. **Pending approvals, unchanged** (SWEEP-QUEUE): n=6 expanded
   loop-swap sweep (~2 h); n=6 forward conjugated i4a sweep (~100 min);
   n=6 recomp2 bands.
6. **Still open, untouched**: run-losing-pair fine anatomy; M-4b/M-4d;
   ip=1; per-allocation NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (s49 additions first; each older one has bitten at least once)

- **A control that fails silently looks exactly like a strong
  negative.** Run the positive controls in
  `analysis/counting/s49/control.py` before believing any 0 from the
  fused instrument (s49's first control run returned a false 0/200 from
  a bug in the control itself).
- **`loopswap_apply.py` hardcodes record = 872/5906** — any sweep over
  above-record corpora (the lift shells) silently discards every
  product without the `--record` patch.
- **Never quote 531 for Kristan-to-novel** (free-frame minimum): the
  admissible-frame edits are 622–735 entries + 15–18 doors.
- **The metric law is descriptive, not a proof** — vocabulary sizes
  reach 534, not 228; the blind spot's single-rule isolation is proven
  only by the s49 depth-1 exhaustion.
- **The s48 fingerprint is allocation-conditional** — do not use it as
  a general bridge detector (one-sided at n=6); and do not conflate it
  with the kind-2 (w4-indicator) asymmetry — separate columns in the
  census TSV, and the TSV's `asym_orient`/`asym_endstart` flags encode
  different predicates than the headline sets (derive sets from the
  `profile` column).
- **`rule_annotation_n7.tsv` quirks**: columns 17–18/19–20 are
  duplicated (s47 double-run; values identical); `ab88abce72ba`'s
  census edge count reads 302, truth 304 — fix at next regeneration,
  don't "correct" single cells by hand.
- **s49 instruments live in `analysis/counting/s49/`** and expect
  repo-root cwd; `fuse.py index` rebuilds the ~200 MB scratch indexes
  under `out/s49/item1/` in ~45 s.
- **Node-naming across tiers**: normalize by hash12 before any graph
  union (`rbnd_edges_n7.tsv` is now the corrected 32-row table; the
  old 30-row pseudo-vertex version is gone).
- **The R-BND 9-column TSV is promiscuous as well as weak**: use
  `rbnd.py` intrinsic modes; skip its TSV rows in loop-swap sweeps.
- **The 4 novel classes are SUBMITTED, not published** — published
  shell is 194 until PR #52 merges; upstream novelty claims require a
  fresh `git pull` in `../superperm` first. m3_check's index includes
  them (198), so re-finding them exits 0, not 2.
- **Closure language**: name the corpus — "over the 194" vs "over the
  198" — and now also the tier depth ("single-rule", "sequential",
  "targeted fused depth-2"). Above-record shells (873/5907) carry NO
  novelty language — m3_check applies only at ≤872/≤5906.
- **Sharding is mandatory for n=7 apply-sym** (≤12,000
  rule-entries/shard; the OOM is the rule instance table, not the
  corpus). Always `--dry-run` first.
- **Replay-kill (97.8–99.998%) applies to SWEEPS, not to targeted
  composition** (which is replay-free) — don't project either regime's
  numbers onto the other.
- **Extraction/synthesis from a closed corpus returns closure**;
  synthesis is TOTAL (s47) — reach claims need externally-derived
  rules.
- **`canon_rule` quotients by S₇ only**; `revquot_audit.py`'s numpy
  canonicalizer does 864 rules in ~40 s — never the naive loop.
- **Rule TSVs are 9-column s44 format — never add a 10th column** (a
  fused pair of 9-column rules is still 9-column; R-BND fusions are
  not, and are out of scope for the format).
- **m3_check ritual**: EVERY candidate ≤5906 (n=7) or ≤872 (n=6) goes
  through `m3_check.py` + the Rust validator before any novelty
  language; the orchestrator re-runs gates itself. Only Andrew decides
  publications.
- **Launch protocol**: > 30 min projected ⇒ SWEEP-QUEUE + Andrew's
  per-entry approval; < 5 min just run; between, time-box and watch.
  No `timeout(1)` on this Mac — background-launch and poll the PID.
- **The n=7 record corpus spans FOUR dirs** (+ the two ABOVE-record
  lift shells `data/lift873_n6/`, `data/lift5907_n7/` — don't mix them
  into record-shell counts).
- **`tail_conjugacy_census.py` takes dirs space-separated;
  `loopswap_apply.py --dirs` comma-separated.** Its KNOWN-EDGE column
  is now correct (41 → 1,546) — pass `--edges` for custom unions.
- **Doc drift**: SURGERY-DESIGN §10.8 over §10.4; §11.6/§11.7 as-built
  for I4-A; JOURNAL s44–s49 as-built for I5/R-BND/fusion;
  `docs/RBND-RULE.md` as-built for R-BND; the committed
  `upstream5906_structure` output predates novel5906b/c (95 rows).
- **Swap-signature equality is a carrier invariant, not a move
  invariant; tight ≠ only; block ceiling binds at n=7; farm binary
  staleness; cap-at-target starves NRPA; equal-cost flood semantics;
  calibrated ≠ proven; tautology check before celebrating a law** —
  all unchanged.
- **Session end ritual**: JOURNAL entry, `cargo test --release` green
  (139), clippy `-D warnings`, fmt, commit → `git pull --rebase` →
  push. When this handoff goes stale, write the successor and repoint
  CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s49/s48/s47.
3. `docs/RBND-RULE.md` (boundary-trade tier, rigidity theorem);
   `docs/THEORY.md` §7; `analysis/counting/loopswap_apply.py`
   docstring (I5 as-built); `analysis/counting/s49/README.md` (the
   fused-composition + w4 instruments); `docs/SURGERY-DESIGN.md` §11.
4. `data/loopswap/` (5 rule tables; ALL_union at 2,006 edges;
   `rbnd_edges_n7.tsv` 32-row; `blindspot_n7.tsv` +
   `blindspot_admdiff_n7.tsv`; `rbnd_rev_census_n6_full.tsv`;
   annotation TSVs); `data/tailconj/tail_pairs_n7_a4840_198.tsv`;
   `data/lift873_n6/NOTE.md` + `data/lift5907_n7/NOTE.md`;
   `data/novel5906c/NOTE.md`; `out/s49/` (scratch, regenerable).
5. `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
