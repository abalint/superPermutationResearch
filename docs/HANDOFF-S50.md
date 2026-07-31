# Handoff — the s51+ front (fresh agent, start here)

Supersedes `HANDOFF-S49.md`. Read JOURNAL s50 (the triple negative:
sumset closure + shells move + composite buys nothing), s49 (blind-spot
proofs, w4 theorems, the lift shells), s48/s47 (re-closure; R-BND);
this is the two-page version with entry points and traps.

## State of the world in ten sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records and
   record-shell structure validate the engine.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7). The
   published n=7 shell is **194 classes / 8 allocations** (upstream at
   `235a074`); the PROJECT shell is **198**: s47's 4 novel (843,18)
   classes are **SUBMITTED as PR #52** (still open as of 2026-07-31 —
   on merge, flip `data/novel5906c/NOTE.md` to PUBLISHED and the
   published count to 198 here and in CLAUDE.md). All 198 pure-w3.
3. **The blind spot (12 classes, `data/loopswap/blindspot_n7.tsv`) is
   now closed against everything short of the untargeted fused sweep**:
   single rules (s49 depth-1 exhaustion, 0 over 4.35M instances × 9,456
   frames), sequential chains at every depth (vacuity given closure),
   and fused pairs both directions precondition-free (s49 targeted
   depth-2 0/4.25M + s50 FULL sumset **0/9,456**,
   `data/loopswap/blindspot_sumset_n7_full.tsv`; min |EO_req| = 216,
   inside single-rule reach — the isolation is structural).
4. **The w4 route is closed too (s50)**: the loop-swap tier moves
   freely INSIDE both w4 shells (n=6: 166 undirected in-shell edges;
   n=7: 3,795; both shells CLOSED as class sets, zero ≤record
   products) but **every lift→move→drop bridge is already a known
   natural-move edge** (1,664/1,664 at n=7, 115/115 at n=6 after a
   direct control) — **lift → move → drop = move**; the REV-w4 lift
   conjugates the tier rather than escaping it. Shell structure is
   committed (`lswap{873,5907}_shell_edges_*.tsv`,
   `w4drop_bridges_n{6,7}.tsv`, `w4drop_map_n{6,7}.tsv`).
5. **Targeted composition needs NO replay** (s49): rigidity forces the
   frame and replay is deterministic, so reachability is
   set-membership (`analysis/counting/s49/fuse.py`; controls in
   `control.py` + `sumset_control.py` — run them before believing any
   0). The 97.8–99.998% replay-kill statistic applies to sweeps only.
6. **The vocabulary is 398 distinct moves = 864 directed rules across
   FIVE tables** (never "the four"); `rule_annotation_n7.tsv` covers
   all 864; sizes reach |ents_out| = 534; Δ = −Δ exactly.
   `loopswap_apply.py` now takes `--record` for above-record corpora
   (regression-proven byte-identical default).
7. **w4 theorems (s49)**: door-for-boundary trades have Δlen = 3 − w
   (w=3 forced; the w4 FWD trade IS the record-break move, never fires
   naturally, 100% replay-dead forced); no length-conserving w≥4
   boundary trade exists. The only length-conserving w4 move is the
   **demotion trade** `(S+1, d3+1, d4−1)` — unimplemented, and the
   lift shells now give it 680 carriers (menu item 3).
8. **The n=6 REV fingerprint is one-sided** (s49): 313 classes carry
   it, allocation-conditional, not a general bridge detector; the
   kind-2 asymmetry IS the w4 indicator (415/415; the w4 door blocks
   R-BND's REV-START slot 821/821).
9. **Kristan-to-novel admissible edits are 622–735 entries + 15–18
   doors (never quote 531)**; the (843,18) pocket splits {Kristan} ⊔
   {the four}; nothing escapes the (842,19)–(843,18)–(844,17) pocket
   under any single rule or depth-1 sequential composite.
10. Working modes: > 30 min goes through `docs/SWEEP-QUEUE.md` (Andrew
    approves per-entry — don't launch, don't nag); heavy tool-loop work
    → **Opus subagents**; the orchestrator re-verifies every
    load-bearing claim itself before writing docs.

## The work menu (in priority order)

1. **The untargeted fused sweep** — the ONLY remaining loop-swap-tier
   idea for the blind spot (fused escape to a class OUTSIDE the 198).
   Queued, **NOT approved** (~33 h single-core / ~4.2 h 8-way Mac /
   ~1.4 h farm when the PC frees up). Needs the `untargeted` mode added
   to `fuse.py` per the queue spec.
2. **PR #52 watch**: `gh pr view 52 -R superpermutators/superperm`; on
   merge flip NOTE.md → PUBLISHED, published shell → 198 here +
   CLAUDE.md.
3. **The w4 demotion trade** `(S+1, d3+1, d4−1)`, Δlen = 0: the only
   length-conserving w4 move; carriers now exist at both n
   (`data/lift873_n6/` 448, `data/lift5907_n7/` 232, plus the 415
   w4-bearing n=6 record classes); NO instrument implements it. At n=6
   it connects occupied record allocations (140,6,1)×388 ↔ (141,7)×4.
4. **`up-1b8244ba04bb` anatomy** — the 23-door blind outlier: zero
   door-identical partners in the 198, nearest neighbour a novel5906c
   class.
5. **Pending approvals** (SWEEP-QUEUE): n=6 expanded loop-swap sweep
   (~2 h); n=6 forward conjugated i4a sweep (~100 min); n=6 recomp2
   bands.
6. **Still open, untouched**: run-losing-pair fine anatomy; M-4b/M-4d;
   ip=1; per-allocation NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (s50 additions first; each older one has bitten at least once)

- **`--record` alone is NOT sufficient for shell sweeps**: the inline
  gate only indexes ≤record classes, so every in-shell rediscovery
  lands in the NOVEL bucket and the run prints "0 edges". Recover the
  self/non-self/new split by post-processing the provenance TSV against
  a canon index of the shell (s50 built
  `out/s50/lift{873,5907}_canon_index.tsv`; regenerate as needed).
- **Rule tables carry frame-variant duplicate ids**: `ab88abce72ba`,
  `cb47d5e063e0`, `ea1ae55099c1` have different stored rows in
  `rules_n7_a256.tsv` vs `_gen2.tsv` (same canonical id). Harmless
  under full conjugation; unions must dedup by id, not row.
- **Batched-wave shard drivers waste wall time on skewed loads** — use
  an `xargs -P` worker pool.
- **A control that fails silently looks exactly like a strong
  negative** — and s50 found the s49 sumset control was cited but never
  committed. Both controls now exist (`analysis/counting/s49/control.py`,
  `sumset_control.py`); run them before believing any 0 from the fused
  instruments.
- **Never quote 531 for Kristan-to-novel** (free-frame minimum): the
  admissible-frame edits are 622–735 entries + 15–18 doors.
- **The metric law is descriptive, not a proof** — vocabulary sizes
  reach 534, not 228; isolation claims rest on the s49/s50 exhaustive
  negatives.
- **The s48 fingerprint is allocation-conditional** — not a general
  bridge detector; don't conflate it with the kind-2 (w4-indicator)
  asymmetry; derive sets from the census `profile` column, not the
  flag columns.
- **`rule_annotation_n7.tsv` quirks**: columns 17–18/19–20 duplicated;
  `ab88abce72ba`'s census edge count reads 302, truth 304 — fix at next
  full regeneration only.
- **s49/s50 instruments live in `analysis/counting/s49/`**, expect
  repo-root cwd; `fuse.py index` rebuilds the ~200 MB indexes in ~45 s;
  `sumset.py` shards via S49_SOURCES/S49_TAG env vars.
- **Node-naming across tiers**: normalize by hash12 before any graph
  union. `lswap_sym_edges_n7_ALL_union.tsv` columns are
  (n, source, target, rule) — endpoints are columns 1–2, not 0–1.
- **The R-BND 9-column TSV is promiscuous**: use `rbnd.py` intrinsic
  modes; exclude `rules_n7_rbnd.tsv` from loop-swap sweeps.
- **The 4 novel classes are SUBMITTED, not published** — published
  shell 194 until PR #52 merges; upstream novelty needs a fresh
  `git pull` in `../superperm`. m3_check re-finds them exit 0, not 2.
- **Closure language**: name corpus AND tier depth. Above-record
  shells (873/5907) carry NO novelty language — m3_check applies at
  ≤872/≤5906 only. The lift shells are NOT record-shell classes —
  don't mix them into shell counts.
- **Sharding mandatory for n=7 apply-sym** (≤12,000 rule-entries per
  shard); always size first (s50 note: this instrument's "--dry-run"
  discipline was replaced by run-twice-byte-agree — either is
  acceptable, say which you used).
- **Replay-kill applies to SWEEPS, not targeted composition.**
- **Extraction/synthesis from a closed corpus returns closure**;
  synthesis is TOTAL — reach claims need externally-derived rules.
- **`canon_rule` quotients by S₇ only**; use the numpy canonicalizer.
- **Rule TSVs are 9-column s44 format — never add a 10th column.**
- **m3_check ritual**: EVERY candidate ≤5906/≤872 → `m3_check.py` +
  Rust validator before any novelty language; orchestrator re-runs
  gates itself. Only Andrew decides publications.
- **Launch protocol**: > 30 min ⇒ SWEEP-QUEUE + per-entry approval;
  < 5 min just run; between, time-box and watch. No `timeout(1)` on
  this Mac — background-launch and poll PIDs. Check for foreign
  compute before quoting timings (s50 found 5 foreign processes at
  ~100%).
- **The n=7 record corpus spans FOUR dirs**; the lift shells are
  separate above-record corpora.
- **`tail_conjugacy_census.py` dirs space-separated;
  `loopswap_apply.py --dirs` comma-separated.**
- **Doc drift**: SURGERY-DESIGN §10.8 over §10.4; §11.6/§11.7 as-built
  for I4-A; JOURNAL s44–s50 as-built for I5/R-BND/fusion/w4;
  `upstream5906_structure` output predates novel5906b/c.
- **Swap-signature equality is a carrier invariant; tight ≠ only;
  block ceiling binds at n=7; farm binary staleness; cap-at-target
  starves NRPA; equal-cost flood semantics; calibrated ≠ proven;
  tautology check before celebrating a law** — all unchanged.
- **Session end ritual**: JOURNAL entry, `cargo test --release` green
  (139), clippy `-D warnings`, fmt, commit → `git pull --rebase` →
  push. When this handoff goes stale, write the successor and repoint
  CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s50/s49/s48.
3. `docs/RBND-RULE.md`; `docs/THEORY.md` §7;
   `analysis/counting/loopswap_apply.py` docstring (incl. `--record`);
   `analysis/counting/s49/README.md`; `docs/SURGERY-DESIGN.md` §11.
4. `data/loopswap/` (5 rule tables; ALL_union 2,006; `rbnd_edges_n7.tsv`
   32-row; `blindspot_n7.tsv` + `blindspot_admdiff_n7.tsv` +
   `blindspot_sumset_n7_full.tsv`; shell edges + drop tables;
   `rbnd_rev_census_n6_full.tsv`; annotation TSVs);
   `data/tailconj/tail_pairs_n7_a4840_198.tsv`;
   `data/lift873_n6/NOTE.md` + `data/lift5907_n7/NOTE.md`;
   `data/novel5906c/NOTE.md`; `out/s50/` (scratch, regenerable).
5. `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
