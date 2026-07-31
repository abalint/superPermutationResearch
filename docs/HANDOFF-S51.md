# Handoff — the s52+ front (fresh agent, start here)

Supersedes `HANDOFF-S50.md`. Read JOURNAL s51 (the Kristan arc: two
unpublished classes → the s51 rule family → shell 220 + the K₄ law;
the demotion family + its infeasibility theorem; the 1b8244 arithmetic-
blindness verdict), then s50/s49 for the closure proofs this builds on.
This is the two-page version with entry points and traps.

## State of the world in twelve sentences

1. **Engine-first premise unchanged** (ROADMAP "Premise"): records and
   record-shell structure validate the engine.
2. **The project shell is 220 classes / 9 allocations** (was 198/8):
   198 + Kristan's two unpublished classes (`data/kristan5906_web/`,
   both (842,19), both σ=1462537-reversal-symmetric, NOT in the
   community corpus — his discoveries, HIS to publish) + 20 project
   classes (`data/novel5906d/`, 16×(838,23) + 4×**(834,27) — the ninth
   allocation, previously empty**). PUBLISHED is still 194 (PR #52
   open; on merge flip novel5906c NOTE + counts here and in CLAUDE.md).
3. **The vocabulary grew a tier**: `data/loopswap/rules_n7_s51.tsv` —
   three UNIT rules of shape (0,1,2,1) {R-K7 `2692f93be643`, S51A
   `8384fb408dcb`, S51C `a9ba4a917654`} + three 2-unit composites
   {S51B, S51D, S51E}, 12 directed rows. None was in the 870 committed
   ids; all replay byte-identically.
4. **The K₄ law (s51, verified 10/10)**: every cover-sharing quadruple
   of the 220 shell is a complete K₄ whose six undirected edges are
   exactly the six s51 rules — unit star out of an OLD anchor class,
   composite opposite triangle. The tier adds ZERO new covers
   (orientation-canonical count still 183) and saturates at depth 1
   (fixed point at gen 2, twice). Edges:
   `data/loopswap/s51_tier_edges_n7.tsv` (172 directed, 46 nodes).
5. **The 220 shell is closed** under s51 tier depth 1; the old 864
   add zero edges from the 22 new classes into the 198 shell (25-shard
   marginal sweeps, both pools); V0004/v0005 take zero old-864 firings.
6. **The m3 gate covers all 220**: supplementary indexes
   `novel5906d_canon_index.tsv` + `kristan5906_web_canon_index.tsv`
   are wired into m3_check SUPPLEMENTARY (rebuild:
   `analysis/counting/build_supp_index_s51.py`). No more post-filter
   hand-holding for the Kristan hashes.
7. **The w4 demotion trade is a unit FAMILY** — DEMOTION(w), Δlen=0
   for all w≥3; DEMOTION(3) IS R-BND FWD. At n=6 record level it is
   **structurally infeasible both directions** (866/866 w4 doors, all
   gates closed; promotion 9,395 admissible → 100% replay-dead).
   Corollary: **any product of the full-corpus n=6 promotion sweep is
   a novel 872 by construction** — queued (~26 min 8-way), NOT
   approved. Instrument: `analysis/counting/s51/demotion.py` (+
   brute-force completeness control in `control.py`).
8. **`up-1b8244ba04bb` is arithmetically blind** — min entry-diff 536
   > vocabulary max 534, min door-edit 34 > 12/rule (24 fused), 536 ≡
   2 mod 6 — a different phenomenon from the (844,17) eleven
   (vocabulary-coverage, closed only by s49/s50 exhaustion). The
   untargeted fused sweep is PROVABLY VACUOUS for it within the 198.
9. **The blind spot is untouched by everything** — 12 classes, zero
   contact from the s51 tier (v0005's nearest blind is 1080 away).
10. **Kristan's method reading** (JOURNAL s51 §1): seeded,
    cover-preserving local search — his V0001→V0005 ladder walks ONE
    cover across three allocations; expect his future finds inside
    existing record covers, i.e. exactly where the K₄ law predicts
    missing unit rules.
11. **Targeted composition is replay-free** (s49) and the s49/s50
    exhaustive negatives stand unchanged — but note they are vs the
    198; nothing re-ran them vs the 220 (the 22 new classes' own
    reachability IS fully mapped).
12. Working modes unchanged: >30 min ⇒ SWEEP-QUEUE per-entry approval;
    heavy tool-loops ⇒ Opus subagents; the orchestrator re-verifies
    every load-bearing claim before it enters the docs.

## The work menu (priority order)

1. **Andrew's decisions** (blocked on him, don't act): publication +
   credit coordination for the Kristan-derived tier (read
   `data/novel5906d/NOTE.md` caveat first); whether to tell
   Kristan/the group that V0004/V0005 are archived and un-corpused;
   PR #52 watch; promotion-hunt approval (queue tail).
2. **Hunt more missing unit rules via the K₄ law**: the 14 remaining
   cover pairs/triples (list in JOURNAL s51 §3 / out/s51/closure
   census) are candidate incomplete simplices — compute admissible
   diffs around their anchors, extract any unit rules, sweep, repeat.
   This is the direct continuation of what just paid off twice.
3. **Re-scope the untargeted fused sweep** (queued, NOT approved):
   vacuous for 1b8244 within the 198; the remaining value is escape
   OUTSIDE the shell — and it should now target the 220.
4. **Demotion family extensions**: w≥5 (needs n=8-scale lift shells),
   the 200 lift-873 demotion products as carriers (three above-record
   allocations the s49 shell lacked; regenerable, out/s51/demotion/).
5. **Pending approvals** (SWEEP-QUEUE): the n=6 promotion M3 hunt
   (can't-lose design); the older n=6 entries.
6. **Still open, untouched**: run-losing-pair anatomy; M-4b/M-4d;
   ip=1; per-allocation NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (s51 additions first; the s50 list still applies — read it)

- **Minimal admissible frames are orientation-dependent**: minimize
  over all four src/tgt orientation combos or you hide unit rules
  behind composite-looking diffs with different canon ids (S51C was
  invisible in the F/F frame).
- **Cover-sharing is NOT a K₄ invariant**: one region is two K₄s glued
  on a triangle, split 3+2 by cover. Don't use covers as a proxy for
  tier components.
- **The loop cover is not reversal-invariant** (0/220 classes have
  cover(F)=cover(R)); `loop_ledger_probe.py cover` reads forward only.
  Name the orientation convention in every cover claim.
- **Upstream filename hex ≠ recomputed canon sha12**
  (`up-d9a28c2d8195` canon-shas to `cc4b3da4289a`). Hash12-normalize
  via FILENAMES or graph joins silently fail.
- **`data/kristan5906_web/` holds `.txt.rediscovery` files** — tools
  globbing `*.txt*` (or `ls | grep txt`) inflate that corpus 2 → 5.
  `loopswap_apply.file_map` (`endswith(".txt")`) is safe.
- **`upstream5906_structure.py` writes its committed output path
  regardless of input dirs** — running it over the 198+ clobbers the
  95-row committed file.
- **Committed `blindspot_admdiff_n7.tsv` door columns are upper
  bounds** (symdiff-min frame, not door-min: 37 vs true 34 for 1b8244).
- **Dangling-door degeneration** (demotion instrument): a door added
  at the walk end is never traversed — replay succeeds, allocation
  lies, the move silently becomes the w4 drop. Re-derive
  structure∘first-visit on every product. Also: weight-w overlap is
  n−w, not w (invisible at n=6 where n=2w — zeroed the n=7 candidate
  set silently).
- **Repeated-window walks exist at both n now** (Kristan v0005; one
  s51 demotion 873): `structure∘replay ≠ id` on them though they
  validate complete. Canon/class logic is unaffected (first-occurrence
  reading); per-string roundtrip assertions will fire.
- **`tail_all_n7.tsv` `deepest_d` is a position index** — bigger =
  shallower. Rank by `shared_perms`.
- **`rbnd_edges_n7.tsv` has 3 columns; lswap/i4a edge tables have 4**
  — extract hash12 by regex over all fields, never by column index.
- **A trailing `&` inside a run_in_background Bash call silently kills
  an xargs pool** — run pools in the foreground of the backgrounded
  call.
- **`i4a_apply.py`'s `replayed` counter counts PRECONDITIONED
  instances** (incremented before replay) — "replayed: 34, 0 edges"
  means 34 attempts all died.
- **The local ../superperm clone may sit on a PR branch** — `git pull`
  there reports the FORK's state; check upstream with
  `git fetch origin && git log origin/master`.
- **Session end ritual**: JOURNAL entry, `cargo test --release` green
  (139), clippy `-D warnings`, fmt, commit → `git pull --rebase` →
  push. When this handoff goes stale, write the successor and repoint
  CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s51/s50/s49.
3. `data/novel5906d/NOTE.md` + `data/kristan5906_web/NOTE.md` (the new
   corpora + the publication caveat); `data/loopswap/rules_n7_s51.tsv`
   + `s51_tier_edges_n7.tsv`; `analysis/counting/s51/` (demotion
   instrument + DESIGN at out/s51/demotion/DESIGN.md if present —
   regenerable); `out/s51/` scratch layout (anatomy/, kristan/,
   closure/, demotion/ — all regenerable).
4. `docs/RBND-RULE.md`; `docs/THEORY.md` §7;
   `analysis/counting/loopswap_apply.py` docstring;
   `analysis/counting/s49/README.md`.
5. `docs/SWEEP-QUEUE.md` (approvals; promotion hunt at the tail);
   `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
