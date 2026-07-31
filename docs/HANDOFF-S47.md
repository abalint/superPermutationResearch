# Handoff — the s48+ front (fresh agent, start here)

Supersedes `HANDOFF-S46.md`. Read JOURNAL s47 (R-BND + the 4 novel
classes, the synthesizer negative, the 397-object recount), s46 (band
closure, cover-twin discovery), s45 (gen-2 closure negative); this is
the two-page version with entry points and traps.

## State of the world in nine sentences

1. **The premise is engine-first** (ROADMAP "Premise", Andrew
   2026-07-29): build the best superpermutation engine; records and
   record-shell structure validate the engine.
2. **A record is a TIGHT LOOP COVER** (s39 theorem, THEORY §7). The
   published n=7 shell is **194 classes / 8 allocations** (upstream
   `superpermutators/superperm` at `235a074`); the PROJECT shell is
   **198**: s47 found **4 novel 5906 classes, all at (843,18) —
   Kristan's allocation, previously a single class** —
   `data/novel5906c/`, CANDIDATES, unpublished, publication is
   Andrew's decision.
3. **The move that found them is R-BND** (`docs/RBND-RULE.md`,
   `analysis/counting/rbnd.py`): the boundary/door unit trade — the
   n=6 R-unit lifted to n=7 — an i4a-style rigid rule WITH a
   re-rooting action. Derived from s46's conjugated cover twins;
   oracle 3/3; the twin trade is a 2-step path through (843,18), not
   an edge. n=6's full 22,062-class archive is CLOSED under it.
4. **Rigidity theorem** (proven twice, independently): a 9-column rule
   replays from the source walk's start perm, which forces the
   relabeling uniquely — there is NO relabel freedom in that frame.
   Any move needing a different frame needs an explicit re-rooting
   component (R-BND has one; the 9-column format cannot carry one —
   and never add a 10th column, the format is load-bearing).
5. **Rule synthesis is TOTAL, hence vacuous**: an oracle-passing
   9-column rule exists for EVERY ordered class pair (120/120 random
   controls, s47). Reach means something only for rules extracted
   elsewhere. Do not build "synthesize a rule to X" instruments.
6. **The vocabulary is 397 distinct moves** (862 directed canonical
   ids under S₇×ι×τ; annotation
   `data/loopswap/rule_annotation_n7.tsv`). The census edge-set
   partition equals the symmetry partition exactly. s46's 240 band
   rules are genuinely new (622 → 281 objects, +116). Within the
   loop-swap tables S₇×ι×τ is complete; cross-TIER "same move" needs
   the carrier-level product test (the R-K7/a23d identity is a
   target-frame class-level fact, NOT a rule symmetry).
7. **Every closure claim is REOPENED over the 198**: the 862 rules,
   i4a/R-K7, and the tail-conjugacy census were proven fixed points
   over the 194 and have not seen the 4 new classes. R-BND itself is
   at fixed point (gen-2 sweep included its products).
8. **The blind spot is 12** (was 14; the twin pair connected through
   novel class `e9623244f6b1`) and it is METRIC: min admissible
   entry-diff ≥ 432 for untouched vs median 48 / max 384 for touched
   — zero overlap. Nothing single-rule can cross that gap; the only
   live idea is composition chains through intermediates.
9. Working modes: anything > 30 min goes through `docs/SWEEP-QUEUE.md`
   (Andrew approves per-entry — don't launch, don't nag); heavy
   tool-loop work is delegated to **Opus subagents** (Andrew
   2026-07-30); the orchestrator verifies gates itself, synthesizes,
   and writes docs. s47 also proved the value of cross-wiring parallel
   agents mid-flight (item 2's frame result was forwarded to item 1
   and became the derivation's key).

## The work menu (in priority order)

1. **Re-close the 198.** Sweep the 862 loop-swap vocabulary +
   conjugated i4a/R-K7 over a corpus including `data/novel5906c/`;
   extend the tail-conjugacy census; re-run the conjugated-cover
   census over 198 (new cover twins? `conjcover_all.py` in
   `out/s46/item3/` is the tool). Marginal corpus is ~2% — size with
   --dry-run, shard at ≤12k rule-entries, should fit the 30-min box.
   Also: do R-BND ∘ loop-swap composites escape the (843,18) pocket?
2. **Publication decision** on `data/novel5906c/` (Andrew's call; PR
   prep against superpermutators/superperm is ready work — follow the
   PR #50/#51 pattern, `m3_check` novelty language only after a fresh
   upstream pull).
3. **R-BND extensions**: census where the REV variants fire (their
   preconditions are NOT universal, unlike FWD); boundary trades at
   w≥4 doors; iterate R-BND between loop-swap generations.
4. **Blind-spot composition chains**: 12 classes, nearest touched
   neighbors 36–74 loops away; single rules provably can't reach
   (metric law) — search short composite paths through intermediates.
5. **Pending approvals, unchanged**: n=6 expanded sweep (SWEEP-QUEUE,
   ~2 h); n=6 forward conjugated i4a R-sweep (~100 min); n=6 recomp2
   520/450 bands.
6. **Still open, untouched**: run-losing-pair fine anatomy; M-4b/M-4d;
   ip=1; per-allocation NRPA/beam; Track C v2's 2.4× overhead cut.

## Traps (s47 additions first; each older one has bitten at least once)

- **The 4 novel classes are UNPUBLISHED candidates** — never call the
  published shell 198; upstream novelty claims still require a fresh
  `git pull` in `../superperm` first. m3_check's index now includes
  them (198), so re-finding them exits 0, not 2.
- **Closure language**: "closed under X" now means over the 194
  UNLESS the sweep included novel5906c — say which corpus explicitly.
- **R-BND's 9-column encoding is strictly weaker than the rule** (a
  w3 door has 6 relabel-classes; only start-preserving variants
  execute faithfully; the literal twin composite dies 6/6). Use
  `rbnd.py`'s intrinsic modes, not the TSV, for real sweeps.
- **Swap-signature equality is a carrier invariant, not a move
  invariant** (identical rewrite, two s43 signatures on the twins).
- **Quote the vocabulary as 397 objects** (862 directed ids); the
  τ-collision table is `data/loopswap/tau_collision_classes_n7.tsv`.
- **`out/s47/item3/out/SUMMARY.txt` prints "REVERSAL MAP: BROKEN" —
  false alarm**: the banner counts any walk-wise failure; the 13
  failures are exactly the repeat-window walks (181/194 + 13 = all).
- **Use `lswap_sym_edges_n7_ALL_union.tsv` for loop-swap graph
  analyses** — R-BND edges are a separate tier in
  `data/loopswap/rbnd_edges_n7.tsv`; don't fold tiers silently.
- **`canon_rule` quotients by S₇ only** — and `revquot_audit.py`'s
  numpy canonicalizer does 862 rules in 42 s; never pay the ~72-min
  naive loop again.
- **Replay-kill worsens with depth** (98.6–99.998% across s47's
  sweeps). Never project yields from precondition counts.
- **SHARDING IS MANDATORY for n=7 apply-sym at scale**: ≤12,000
  rule-entries per shard; always `--dry-run` first (three sessions
  running, dry-run-exact every time).
- **Extraction/synthesis from a closed corpus returns closure**; and
  synthesis is TOTAL (s47) — reach claims need externally-derived
  rules.
- **The `oracle` CLI mode only runs `DEFAULT_SETS`**; drivers call
  `run_extract(..., do_oracle=True)`; memoize `canon_rule`.
- **Rule TSVs are 9-column s44 format — never add a 10th column.**
- **KNOWN-EDGE annotation hides rules from re-extraction** — union
  rule tables when you want the full vocabulary.
- **m3_check ritual**: EVERY candidate ≤5906 (n=7) or ≤872 (n=6) goes
  through `m3_check.py` + the Rust validator before any novelty
  language; the orchestrator re-runs gates itself, agents' word is
  not enough. Only Andrew decides publications.
- **Launch protocol**: > 30 min projected ⇒ SWEEP-QUEUE + Andrew's
  per-entry approval; < 5 min just run; between, time-box and watch.
  No `timeout(1)` on this Mac — background-launch and poll the PID.
- **The n=7 corpus now spans FOUR dirs** (`data/upstream5906` +
  `data/novel5906` + `data/novel5906b` + `data/novel5906c`);
  published union = 194, project union = 198.
- **Doc drift**: SURGERY-DESIGN §10.8 over §10.4; §11.6/§11.7
  as-built for I4-A; JOURNAL s44–s47 as-built for I5;
  `docs/RBND-RULE.md` as-built for R-BND.
- **Tight ≠ only; block ceiling binds at n=7; farm binary staleness;
  cap-at-target starves NRPA; equal-cost flood semantics; calibrated ≠
  proven; tautology check before celebrating a law** — all unchanged.
- **Session end ritual**: JOURNAL entry, `cargo test --release` green
  (139), clippy `-D warnings`, fmt, commit → `git pull --rebase` →
  push. When this handoff goes stale, write the successor and repoint
  CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s47/s46/s45.
3. `docs/RBND-RULE.md` (the new tier, incl. the rigidity theorem and
   per-pair anatomy); `docs/THEORY.md` §7;
   `analysis/counting/loopswap_apply.py` docstring (I5 as-built);
   `docs/SURGERY-DESIGN.md` §11 (loop-cover frame, i4a, M-4a).
4. `data/loopswap/` (rule tables, edge censuses, the annotation
   TSVs; ALL_union = loop-swap graph, rbnd_edges_n7 = R-BND tier);
   `data/novel5906c/NOTE.md`; `data/tailconj/`; `out/s47/` (scratch:
   anatomies, oracles, sweeps, calibration, audit — gitignored,
   regenerable).
5. `docs/SWEEP-QUEUE.md` (approvals); `docs/OPS-BACKGROUND-AGENT.md`.
6. `CLAUDE.md` (commands; hard invariants).
