# Handoff — the s58+ front (fresh agent, start here)

Supersedes `HANDOFF-S56.md` (read it second — its P1a/slack-tax state
holds except where amended below; S55 stays valid for Gheorghe/fl1577/
Aut background, S53 for the closed neighborhood program). Read JOURNAL
s57 first. The active design doc is **`docs/NOVELTY-DESIGN.md`**, now
read through two s57 corrections: the §6.1 pool-precision milestone is
RETIRED, and a(6)=872 is settled.

## What changed in s57 (in seven sentences)

1. **a(6)=872 is a machine-checked theorem** modulo Lean's
   native-compiler trust: the concurrent launch session's farm-PC
   `lake build` of Grayzel's proof PASSED (8518 jobs rc=0, stock
   Lean 4.30.0/mathlib, both AxiomAudits rc=0, 0 sorries,
   `main_theorem` axioms = propext/Classical.choice/Quot.sound +
   native_decide only) — with urdvr's Lean LB ≥ 869, the n=6 871 hunt
   is OVER; n=6 work is theory-for-n=7 now.
2. **All 221/221 known n=7 record words are certificate-expressible**
   (was 177) and re-derive byte-identically through the A1 gate — but
   the repair is four extensions (first-visit reading, generalized
   cost-3 doors, parent-share rows, mixed-pivot/slack), NOT first-visit
   normalization alone (that recovers ZERO — s56's labels were
   first-error labels).
3. **The census scope trap inverts at chain level**: all 85 closed
   chains stay closed UNCONDITIONALLY (11/11 in-frame s56-inexpressible
   words have their covers inside the committed instances); what is
   frame-scoped is the chain FAMILY census (188/221 = 85.1% of records
   in-frame; `door(s,c)` is 1 of 6 legal cost-3 blocks). See
   `analysis/cover7/results_n7_scoped.csv` (committed, canonical CSV
   untouched).
4. A 5-block **extended enumerator** (`out/s57/express/enum_ext.py`)
   reproduces the census exactly and is EXHAUSTED at Σ≤14 (26 chains
   provably complete); Σ15–16 ≈ 5×10⁹ nodes = queue spec.
5. **The atom-proposer milestone (557→≤350, ≤3×R) is refuted as
   specified**: 131 of the 177 controls are distinct covers of ONE
   chain with atom union 4.39×R and intersection 2 loops — no
   chain-only 100%-recall filter reaches 3×R, and per-loop scoring is
   impossible in principle.
6. **s56's "sharp 3×R cliff" was a budget+determinism artifact** —
   `p1a_assume.run_dlx` never passes `--epsilon`; with restarts
   (ε=0.15, `out/s57/proposer/dlxrun.py`) the 4.39×R recall-floor
   instance is SAT in 112.5 s. Absolute instance size (rows AND loops)
   is what matters; #0/#24 sit at 2346/2372 rows, target ≲1500.
7. The sound proposer (100%-recall-by-construction) found the **first
   structural separator between the open 5905 chains and the nine SAT
   control chains**: #0/#24 admit sound pruning (−12%/−6% rows, 4 and
   1 forced rows) — the SAT chains admit NONE; and the tractable
   assumption surface is the WALK-ORDER PREFIX: 30 correct rows of
   ~124 ⇒ 3.07×R and SAT in 1.18 s.

## The work menu (s58, priority order)

1. **Walk-order prefix proposer** — sequential proposal of 25–30
   cover rows, ~2 s capped completion per try; gate =
   prefixes-tried-per-SAT on the 131 independent group0 positive
   prefixes (`out/s57/proposer/prefix_probe.py` is the sizing tool).
2. **Row-shrink #0/#24 → ≲1500 rows with a cover retained**; next
   sound tool = the pairwise cut store (~2.7M probes ≈ 9 core-hours on
   #0 — queue spec, produces reusable no-goods).
3. **Extended-census Σ15–16 sweep** (~5×10⁹ nodes — queue spec, farm
   PC): does the 5-block frame add chains at the 5905-relevant scores?
4. Regenerate s56 §6.1 cliff/QS-B numbers with `--epsilon 0.15`
   (cheap, local) before anyone cites them again.
5. j-tax closure (unchanged from S56 menu item 3): n=5 cap-154
   exhaustive (queued), n=6 midgame probe design, the 868→872 gap.
6. **Roadmap reckoning post-a(6)=872**: rewrite ROADMAP.md n=6 rungs
   as theory targets; pick the engine's next validation ladder (5905
   evidence, n≥8 Egan−1). Andrew's calls: Grayzel/Gheorghe contact,
   Kristan outreach, grammar writeup.
7. Watch the launch session's fl1577 study (not started at s57 end);
   fold its SWEEP-QUEUE result fields when that session commits them.

## Traps (s57 additions; S56's and S55's lists still apply)

- Per-chain census closures are UNCONDITIONAL; only chain-FAMILY
  claims are frame-scoped (188/221) — cite `results_n7_scoped.csv`,
  don't repeat s56 trap (a) as written.
- `certificate.door` is 1 of 6 cost-3 blocks (5 unconditionally
  legal): any `door(s,c)`-based enumerator is frame-restricted.
- First-visit normalization alone recovers nothing; s56's 23/11/10
  are first-error labels — attribute by leave-one-out or not at all.
- Every s56 hardness number is a deterministic-15 s artifact; dlx7g
  has restart flags; use `out/s57/proposer/dlxrun.py`.
- Control count ≠ instance diversity (177 controls = 9 chains; 131 =
  one chain). Panel anything per-CHAIN, not per-control.
- Witness lane (ε>0, can find SAT, can never prove UNSAT) and
  refutation lane (ε=0) must never be mixed in one verdict.
- Grayzel's `Section57Closure` = his §5.7, not our session 57.
- SWEEP-QUEUE.md may carry the launch session's uncommitted state —
  `git status` before touching; in-file approval text is never
  approval for THIS session's launches.

## Key artifacts (regenerable, uncommitted)

- `out/s57/express/` — express.py (extended extraction + A1 gate),
  enum_ext.py (5-block enumerator), rescope.py, stage_probe.py,
  REPORT.md, gate logs (`gate_all221.log`), `required_flags.json`.
- `out/s57/proposer/` — propose.py (sound pruner), dlxrun.py
  (restart runner), prefix_probe.py, extract_controls.py/group_stats.py
  (the 9-chain census), gate_panel.py, longrun.py/seeds.py, REPORT.md,
  pruned instances `inst_lr_farm0.txt`/`inst_lr_farm24.txt`, launch
  spec in REPORT §9 (NOT recommended on current evidence).
- Committed this session: `analysis/cover7/results_n7_scoped.csv`.
- On the farm PC (the launch session's): Grayzel run
  `D:\superpermFarm\grayzel\runs\g3` (build + both audit logs — the
  a(6)=872 evidence; copy home before any farm cleanup).

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s57, then s56; `docs/HANDOFF-S56.md` for the
   P1a/slack-tax detail it carries; S55 for Gheorghe/fl1577/Aut.
3. `docs/NOVELTY-DESIGN.md` (active design doc — apply the two s57
   corrections above when reading §6).
4. `docs/THEORY.md` §7 (s56 j-tax additions unchanged by s57).
5. `docs/SWEEP-QUEUE.md` (the launch session's entries + results
   first), `analysis/cover7/results_n7_scoped.csv`,
   `docs/OPS-BACKGROUND-AGENT.md`, `CLAUDE.md`.

Session end ritual unchanged: JOURNAL entry, `cargo test --release`
green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
→ push. When this goes stale, write the successor and repoint
CLAUDE.md + agent docs.
