# Handoff — the s64+ front (fresh agent, start here)

Supersedes `HANDOFF-S62.md` (read it second — its state holds except where
amended below). Read JOURNAL s63 first. The active design doc is still
`docs/NOVELTY-DESIGN.md`; **if your session is the refactor, your brief is
`docs/REFACTOR-BRIEF.md` and you can skip the theory docs entirely.**

## What changed in s63 (in five sentences)

1. **HANDOFF-S62 menu item 3 is closed as a general negative**: `j ≡ 0`
   identically in the chain7 frame, so no j-based rung can EVER prune a
   chain instance (S(#0)=834, S(#24)=832, 0 of 223+130 chains reach
   S ≥ 841; the door law is a theorem there, 0 violations on 3,122 doors /
   145,979 inter-w2 edges). Keep the corollary: `V=15 ⟺ length 5905`,
   supply slack = Σ.
2. **The pc1 store's residual questions are answered**: the fixed-column
   singleton layer generalizes (37 rows on #24, 70/40/20 on ctrlgroups,
   0 oracle violations) but the 26,683 live cuts buy only a constant
   ~1.2–1.4× (branching 3.48 vs 3.53) — they will never decide #0/#24.
3. **`mcover_search.py` is built and two-tier controlled**, a NEW rung
   landed (supply-tight v=24 j≥1 family EMPTY to length 870 — 3.4e9 nodes,
   complete, re-verified byte-identically), and a NEW law landed:
   `K = (v−splits) + 2s` with `K = v−splits ⟺ G* is a forest`, forcing the
   (140,8,0,0,0) cell to 8-tree-component forests.
4. **The j-probe launch was correctly refused three times** (as-specced
   ≥1,240 core-h; 1.2M gate failed early; raised 3M gate failed early) —
   `N_forest(28) > 4.2M and still counting` at session close; enumeration
   is 5.6% of cost, per-cover DFS 94.4%.
5. **Andrew's standing decisions** (all recorded in SWEEP-QUEUE at decision
   time): PC-first for compute; runs HELD until tonight (2026-08-02); the
   reshape menu B > A > D > C awaits his call with exact N; cap-154
   CANCELLED; next session task = the **code refactor**
   (`docs/REFACTOR-BRIEF.md`), docs prepared s63, no work started.

## The work menu (s64, priority order — set by Andrew)

1. **The refactor** (`docs/REFACTOR-BRIEF.md`) — clean architecture pass so
   the repo scales with fewer new/regression bugs. Andrew's instruction
   verbatim: "code refactor focusing on clean architecture design that
   lets us continue to scale with reduced risks of new and regression
   bugs." Docs-first task for a fresh agent; the brief carries scope,
   invariants, staging, and verification bars.
2. **Tonight's launch call** — B/A/D/C on the (140,8,0,0,0) cell (see
   JOURNAL s63 §6 and `out/s63/mcover/REPORT.md` §6/§9 + the agent
   addendum pricing in SWEEP-QUEUE). Exact `N_forest(28)` lands when the
   local emit finishes (`out/s63/mcover/covers_v28_forest.txt`, trailer
   `# total N` + `# sha256`). The mc28 harness is shipped, sha-matched,
   dry-run-proven, idle-ready. If B is chosen: it needs a ≥200k-cover
   census-equality control against the generic DFS before any negative is
   trusted.
3. Remaining queue: nothing else pending approval; #0/#24 have no
   surviving sound tool (pairwise cuts measured non-converting s63).

## Traps (s63 amendments; S62/S61/S60/S59 lists apply in full)

- **Stride-sharding an enumerative engine duplicates the FULL enumeration
  per shard** — the stride filter skips processing, not enumeration.
  Count-only sizing does not reveal this; price it explicitly. The
  covers-file design (emit once, process slices) is the fix and is built.
- **Sizing intuitions failed twice on the forest family** (206k @ 600 s →
  939k @ 2 h → >4.2M @ 13 h; rate swings 45–380/s by subtree). Never
  extrapolate an enumeration from a prefix rate; run counts to completion
  or gate on crossing thresholds.
- **cover_search.py searches a strict SUPERSET** (no door-mid test): its
  negatives are sound, its minima checked unmoved — but never trust a
  FIND from it; use mcover_search.py (mid test on by default).
- **The discarded cutconvert ladder's "compounding 1.28×/level" is an
  artifact** (hash-seed nondeterminism + scratch race, both fixed) — do
  not cite it; the clean number is a constant 1.15–1.4×.
- Windows CRLF corrupts sha-stamped emitted files (`newline=""` fix in
  place); bash-3.2 has no `mapfile` (macOS fetch scripts); `pgrep -f`
  matches your own monitor's command line — wait on PIDs; buffered stdout
  loses a killed process's total — tee or flush progress lines.
- **Farm per-core is 1.91× slower than the Mac** on this workload — quote
  target-platform rates in sizings.

## Key artifacts (regenerable, uncommitted)

- `out/s63/chains/` — REPORT.md (orchestrator-filed, verification appendix
  §7), LOG.md, instruments (scope_check, doorlaw_check, singleton_pass,
  cutconvert, probe_reduced), JSON ledgers.
- `out/s63/mcover/` — REPORT.md (verification appendix §12), LOG.md,
  brute_tight/zcount/kstruct, validated n=5 multi-cover witnesses, logs/,
  and (when the emit lands) `covers_v28_forest.txt` + exact N.
- `out/s62/jtax/mcover_search.py` — the engine (sha `77d2b8dd…` after the
  file-mode addition), lives with its s62 family.
- `analysis/farm/mc28_{ship.sh,shim.py,env.ps1,fetch.sh}` — idle-ready
  harness; fetch adjudicates rc+DONE+sha+sum-to-total and auto-runs the
  three-gate ritual (validate/m3/verify_master) on any product.
- Farm PC: untouched by s63 (only two dry-smoke dirs under mc28 tags).

## Reading order for a cold start

1. This file. If refactoring: `docs/REFACTOR-BRIEF.md` next, then CLAUDE.md
   conventions, and stop — you don't need the theory stack.
2. `docs/JOURNAL.md` s63, s62; `docs/HANDOFF-S62.md` for carried state.
3. `out/s63/mcover/REPORT.md`, `out/s63/chains/REPORT.md`.
4. `docs/THEORY.md` §7; `docs/NOVELTY-DESIGN.md`; `docs/SWEEP-QUEUE.md`
   (the j-probe entry now carries Andrew's full five-decision trail).

Session end ritual unchanged: JOURNAL entry, `cargo test --release` green
(139), clippy `-D warnings`, fmt, commit → `git pull --rebase` → push.
When this goes stale, write the successor and repoint CLAUDE.md + agent
docs.
