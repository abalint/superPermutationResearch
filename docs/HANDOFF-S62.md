# Handoff — the s63+ front (fresh agent, start here)

Supersedes `HANDOFF-S61.md` (read it second — its state holds except
where amended below). Read JOURNAL s62 first. The active design doc is
still **`docs/NOVELTY-DESIGN.md`**; the j-tax frame now lives in
THEORY §7 (s56 block CORRECTED + s62 block added).

## What changed in s62 (in five sentences)

1. **MASTER**: the loop-supply bound with the ceiling —
   `length ≥ n!+(n−1)!+(n−3)+⌈S/(n−1)⌉+j+xp` (pure walks; 0 violations
   over 22,062+448+87+10 corpus walks + exhaustive n=3/4; tight on
   22,052/22,062 records) — whose corollary ladder puts the whole n=6
   868→872 j-gap at splits ≤ 15, unreachable from any record prefix.
2. **Rung 869 is PROVEN** (`j ≥ 1 ⇒ length ≥ 869` at n=6, pure walks):
   the single surviving cell at 868 is supply-tight, which rigidifies
   the walk into the perfect-ride family (24 loops exactly cover the
   120 cycles, all arc-starts determined), and the family is
   exhaustively empty (36.3M nodes; the engine re-derives a(4)=33 and
   a(5)=153 as positive controls).
3. **The mechanism stops at 869**: six v=25 cells there have supply
   slack (rigidity evaporates), NONE of the 22 O5 cells is supply-tight
   (slacks 1–14) — the O5 discharge is out of this composition's reach
   at any budget; any higher rung must price loop-supply SLACK.
4. **n=5 j-tax = 1, decided by witness** (`out/s62/jtax/witness/
   n5_j1_154.txt`, validator-green) — the queued cap-154 exhaustive is
   SUPERSEDED (queue entry says CANCEL). Ladder: n=3→3, n=4→1, n=5→1,
   n=6 ≥1 observed 874; it does not grow with n.
5. **n=7 transfer priced**: `j≥1 ∧ S≥841 ⇒ length ≥ 5906`, so any 5905
   with S ≥ 841 has j = 0 and the per-edge door law becomes a HARD
   constraint (the (844,17) family and Kristan's (843,18) qualify);
   a j≥1 5905 needs v ≤ 140, S ≤ 840, D ≥ 20.

## The work menu (s63, priority order)

1. **Andrew's queue calls** — pairwise cut store (~9 core-h, still the
   only surviving #0/#24 tool), QS-B full map (~2.5 core-h), Σ15–16
   census (~2.7 core-h). The A0 gate re-run is DONE (sweep agent,
   2026-08-01: 18/18 UNKNOWN at 600 s, citable). New: the n=6 midgame
   j-probe (s62 entry; needs mcover_search.py built + sizing re-probe
   first). The cap-154 entry is SUPERSEDED — recommend CANCEL.
2. **The (140,8,0,0,0) supply-tight cell** — the ONLY j≥1 872 cell in a
   known allocation (splits=20, D=8, v=28): a j=1 872 there is a
   28-loop multi-cover with all 140 incidences supplying — rigid,
   enumerable, the sharpest new object. Enumerating it is PART 1 of the
   queued probe; pricing supply slack in general is the theory route.
3. **Wire `S ≥ 841 ⇒ j = 0` into #0/#24** — check the chains' S first;
   if it qualifies, the per-edge door law (every door dc∧dv, every
   inter-w2 edge exactly-one) becomes a sound hard constraint on their
   instances — the first new #0/#24-relevant pruning since s57.
4. **Grammar writeup / outreach** (Grayzel, Gheorghe, Kristan) —
   Andrew's calls.

## Traps (s62 amendments; S61/S60/S59 lists apply in full)

- **THEORY §7's old `x` is two different quantities.** The identity
  needs `xp = Σ_doors(w−3)`; deficit needs `v−L`. They agree only when
  `deficit = j`. Corrected in THEORY §7; any script or derivation that
  copied `length = 843+v+j+(v−L)` is silently wrong on xp-bearing
  walks (in-corpus counterexample: `872.up-022441b7b1ff`).
- **All s62 rungs are for PURE walks** (no intra edge of weight ≥ 2 —
  every corpus walk qualifies, but state the scope with the claim).
- **Perfect-ride rigidity exists ONLY at supply-tightness** (S =
  (n−1)v). Do not try to reuse the cover-determines-arc-starts argument
  at any slack > 0 — that is exactly where it provably fails (six v=25
  cells at 869 undecided).
- **`nearcovers.py` is buggy** (undercounts covers; control 95 vs
  10,068) — do not use it; the v=25 loop-set count is UNMEASURED, so
  the midgame probe's PART 1 must be re-sized before launch.
- The A0 entry's two premise corrections (sweep agent, in-queue):
  A0 measures FINDABILITY (known-SAT by construction; a SAT is not a
  record, an UNSAT is a soundness alarm), and the "0/6 at 15 s"
  baseline never existed as artifacts.

## Key artifacts (regenerable, uncommitted)

- `out/s62/jtax/` — REPORT.md (orchestrator-filed; verdict table,
  limits, re-verification commands), LOG.md (agent trail), lib62.py,
  verify_master.py (the alarm instrument for any future j-candidate),
  cover_search.py (n-generic family enumerator), cells62.py, covers.py,
  o5_crosscheck.py, exhaust_small.py, witness/n5_j1_154.txt (+ j2).
  Full deterministic re-run ≈ 25 min (the TMAX-869 branch is 10 min of
  it); every command in REPORT §10.
- `out/s62/farm/a0g1/` — the sweep agent's A0 run (its entry owns it).
- `out/s61/anatomy/`, `out/s60/retrieval/` + `out/s60/nogood/` —
  unchanged (symlib.py, cutlib.py/confirm.py, anatlib.py reusable).
- On the farm PC: Grayzel run `D:\superpermFarm\grayzel\runs\g3` (copy
  home before any farm cleanup) — unchanged.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s62, s61, s60; `docs/HANDOFF-S61.md` for the
   state it carries.
3. `docs/THEORY.md` §7 (s56 block as corrected + s62 block).
4. `out/s62/jtax/REPORT.md`, then `out/s61/anatomy/REPORT.md`.
5. `docs/NOVELTY-DESIGN.md`, `docs/ROADMAP.md` (2026-07-31 section).
6. `docs/SWEEP-QUEUE.md` (pending entries + the s62 additions at the
   tail), `docs/OPS-BACKGROUND-AGENT.md`, `CLAUDE.md`.

Session end ritual unchanged: JOURNAL entry, `cargo test --release`
green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
→ push. When this goes stale, write the successor and repoint
CLAUDE.md + agent docs.
