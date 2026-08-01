# Handoff — the s62+ front (fresh agent, start here)

Supersedes `HANDOFF-S60.md` (read it second — its state holds except
where amended below; S59 for what it carries from s57/s56). Read
JOURNAL s61 first. The active design doc is still
**`docs/NOVELTY-DESIGN.md`** (self-contained since s60).

## What changed in s61 (in four sentences)

1. **The near-miss residual anatomy question (S60 menu item 2) is
   ANSWERED** (`out/s61/anatomy/REPORT.md`): the "best foreign packing
   dies on a 0–1-candidate residual" phenomenon is **generic row
   geometry plus one exact mechanism, no tool, no evidence** — a
   residual admits a row only if some non-kernel loop has ≥5 of its 6
   orbits inside it, and the exact hypergeometric expectation for a
   10-column residual is ~1.4e-06 (a fifth-power law), so small
   residuals are dead whatever produced them.
2. Where residuals are large the observed candidate counts run
   100×–1,254× ABOVE the exact null, and the source is identified
   precisely: **orphan columns** (images of the source chain's roots —
   the only supply of usable loops, mostly images of A's kernel loops)
   vs **≤4-column debris** from failed mapped rows; since
   `placed ≤ R_B − ⌈orphans/5⌉`, **maximising overlap minimises
   orphans and thereby destroys the only structure that could finish
   the residual** — on #0 the two symmetries that bury all 100 of A's
   roots are exactly the two s60 maximizers, so the 112/114 near-miss
   and the zero-candidate death are one event.
3. The counting bound (U(S) = #usable loops ≥ |S|/5) is a **sound
   theorem** (0 violations over 60,390 real-cover prefixes, slack 0–1
   in the endgame) but **useless as a search rule**: in 360 random
   descents it never fired before a free DLX dead column (0 wins, 23
   ties). No rule is proposed.
4. The s60 trap is upgraded: **a foreign-mapped packing near-miss is
   anti-evidence** — high overlap and unfinishable residual follow
   from the same root-burial. #0/#24 unchanged, OPEN / UNKNOWN.

## The work menu (s62, priority order)

1. **Andrew's queue calls** — unchanged: four pending `approved: NO`
   entries (pairwise cut store ~9 core-h, the only surviving #0/#24
   tool; A0 gate re-run ~90 min LOCAL; QS-B full map ~2.5 core-h;
   Σ15–16 census ~2.7 core-h) plus the self-negating full no-good
   harvest entry. Launches belong to Andrew's launch agent.
2. **j-tax closure** (S56 menu item 3, unchanged): n=5 cap-154
   exhaustive (queued), n=6 midgame probe design, the 868→872 gap.
3. **Grammar writeup / outreach** (Grayzel, Gheorghe, Kristan) —
   Andrew's calls.

(The S60 menu's item 2 is done; nothing new was added — s61 closed a
question without opening a front.)

## Traps (s61 amendments; S60/S59 lists apply in full)

- **Near-miss trap upgraded from empirical to explained:** don't just
  refuse to cite packing near-misses as evidence — know that the
  best-overlap packings are *structurally guaranteed* dead residuals
  (orphan-minimisation). Any future "X% of a cover maps over"
  observation should be decomposed orphan/debris before any excitement
  (`out/s61/anatomy/anatlib.py` does it in one call).
- The counting bound U ≥ |S|/5 is a one-line sanity refuter for any
  proposed residual/packing — fine as a CHECK, but do not build a
  search rule on it (measured strictly dominated by free DLX
  propagation, 0/360).
- s61's headline numbers are on the FULL instances; `pruned` rows
  inherit s57's soundness, not re-audited (unchanged).

## Key artifacts (regenerable, uncommitted)

- `out/s61/anatomy/` — anatlib.py (exact hypergeometric null, m-vector,
  orphan/debris provenance decomposition; imports s60's symlib.py),
  5 probe scripts, logs/JSONs, REPORT.md (orchestrator-filed; full
  re-run ≈ 19 s, deterministic, seeds recorded).
- `out/s60/retrieval/` + `out/s60/nogood/` — unchanged from S60
  (symlib.py, cutlib.py/confirm.py are the reusable pieces).
- On the farm PC: Grayzel run `D:\superpermFarm\grayzel\runs\g3`
  (copy home before any farm cleanup) — unchanged.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s61, s60, s59; `docs/HANDOFF-S60.md` for the full
   s60 state it carries.
3. `out/s61/anatomy/REPORT.md`, then `out/s60/retrieval/REPORT.md` and
   `out/s60/nogood/REPORT.md`.
4. `docs/NOVELTY-DESIGN.md`, `docs/ROADMAP.md` (2026-07-31 section).
5. `docs/SWEEP-QUEUE.md` (four pending `approved: NO` entries),
   `docs/THEORY.md` §7, `docs/OPS-BACKGROUND-AGENT.md`, `CLAUDE.md`.

Session end ritual unchanged: JOURNAL entry, `cargo test --release`
green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
→ push. When this goes stale, write the successor and repoint
CLAUDE.md + agent docs.
