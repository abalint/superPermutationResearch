# Handoff — the s65+ front (fresh agent, start here)

Supersedes `HANDOFF-S63.md` (read it second — its research state holds in
full; s64 changed the CODEBASE, not the math). Read JOURNAL s64 first.
The active design doc is still `docs/NOVELTY-DESIGN.md` for theory;
`docs/CONTRACTS.md` is new and normative for every data format.

## What changed in s64 (in five sentences)

1. **The REFACTOR-BRIEF was executed in full** — eight commits
   (`0dc1fee`…`e861bd2`), every stage gated on byte-identical replay of
   the 25-pin baseline at `out/s64/refactor/pins_before/`, zero pin
   deviations, tests 139→148 Rust + 0→86 pytest.
2. **Python now lives in tracked `pylib/`** (CANONICAL; out/ originals
   frozen), with one `first_visit_path`, both `canon` semantics under
   distinct names, one sanctioned sys.path bootstrap, a real pytest
   suite (`tests_py/`, fast tier <~1 min, `-m slow` for the 36.3M-node
   parity pair), and `scripts/check.sh` as the one-command gate.
3. **The Rust incremental state is unified in `src/state.rs`**
   (CycleState/SearchState, drift-tested in every engine); beam2 now
   MAINTAINS all 14 counters (deficit/residual scoring there is
   unlocked but deliberately NOT enabled); main.rs is 112 lines over 16
   `src/cli/` modules.
4. **The farm harness is one template** (`analysis/farm/template/` +
   per-instrument configs; `pylib/farmstatus.py` encodes the 9-clause
   STATUS contract once, pytest-mirrored); mc28 ported byte-parity,
   PC-verified in Andrew's approved scratch-only dry-run (24/24 DONE,
   0 escapes, farm restored idle, nothing launched).
5. **`docs/CONTRACTS.md` is the new normative source** for rollout
   JSONL / split-profile / covers-file v1 / farm STATUS / the twenty
   (not three) ledger shapes, with four live divergences and two
   structural risks recorded; `--records-profile` is de-forked (file
   is authority, proven-equal compiled fallback, drift-pinned test).

## The work menu (s65, priority order)

1. **Tonight's launch call (Andrew)** — B/A/D/C on the (140,8,0,0,0)
   cell. The local N_forest(28) emit was STILL RUNNING at s64 close:
   5,626,776 covers and counting, no trailer yet
   (`out/s63/mcover/covers_v28_forest.txt`). At D pricing
   (N×0.325 s/24) 6M ≈ 22.6 h farm wall — strengthens B
   (rigidity-specialized DFS, 10–100× on the 94% term). If B: it
   REQUIRES the ≥200k-cover census-equality control vs generic DFS
   before any negative is trusted. The mc28 harness is idle-ready in
   BOTH forms (frozen s63 quartet AND the s64 template port —
   byte-parity proven; use the template, fall back to frozen on any
   doubt).
2. **beam2 deficit/residual scoring** — unlocked by P3 (counters
   maintained + drift-tested), cheap experiment, was explicitly out of
   refactor scope. Success bar: does composed scoring move beam2's
   902/894-era numbers? Keep the purity invariant (score = pure fn of
   (front, back, visited, len)).
3. Loose ends (all small, all recorded): a0/qsb deep-parity + fetch
   rollups not yet template-ported (run the frozen `*_env.ps1` before
   either launches); the four live ledger divergences (CONTRACTS.md
   §5) — fix emitters or docs; CENSUS-SCOPED has no in-repo generator
   yet CLAUDE.md cites it.
4. Research fronts: unchanged from HANDOFF-S63 (#0/#24 have no
   surviving sound tool; the j-front's remaining target is the
   (140,8,0,0,0) cell, menu item 1).

## Traps (s64 additions; S63/S62/S61/S60 lists apply in full)

- **Pin via `./target/release/superperm`, never `cargo run`** — cargo's
  stderr preamble is not byte-stable. The timing normalizer lives in
  `pins_before/MANIFEST.md`.
- **The sys.path hygiene guard scans TRACKED files only** — run
  `scripts/check.sh` AFTER `git add`, or a new file's violation
  surfaces one commit late (it did, `fcb17d7`).
- **Do not merge the two `canon` semantics by name**
  (`pylib/canonical.py` refuses to export a bare `canon`; keep it so).
- **ValueEnum on library types changes --help bytes** (doc comments
  leak into "Possible values") — the BoundArg/DedupArg mirrors are
  deliberate; don't "clean them up" without re-snapshotting help.
- **`cargo clippy --all-targets` is NOT the repo gate** and fails on
  two pre-existing test-code nits (tailatsp.rs:1422, unionsearch.rs:483);
  the gate is `cargo clippy -- -D warnings`, which is clean.
- Fix Python bugs in `pylib/`, NEVER in `out/sNN` (frozen history).
  New instruments: config + adapter on the template, not a new quartet.

## Key artifacts

- `out/s64/refactor/pins_before/` — the 25-pin baseline + MANIFEST
  (regenerable, uncommitted; the pytest suite carries the same numbers
  as committed asserts, so losing it costs nothing).
- `pylib/` (committed) — canonical instruments; `tests_py/` (committed)
  — the suite; `analysis/farm/template/` (committed) — the harness;
  `docs/CONTRACTS.md` (committed) — data contracts.
- Farm PC: touched ONLY by the approved scratch dry-run, both scratch
  dirs removed, verified idle at 33 root files. Runs still HELD until
  tonight per Andrew.

## Reading order for a cold start

1. This file, then JOURNAL s64.
2. CLAUDE.md (conventions — pylib rules + state.rs invariants are new),
   `docs/CONTRACTS.md` for any data format question.
3. If working the launch: HANDOFF-S63 menu item 2 + JOURNAL s63 §6 +
   `out/s63/mcover/REPORT.md` §6/§9 + SWEEP-QUEUE (decision trail).
4. Theory stack unchanged: THEORY.md §7, NOVELTY-DESIGN.md.

Session end ritual unchanged EXCEPT the counts: `scripts/check.sh`
green (= cargo test --release 148/6 + pytest 83 fast), clippy
`-D warnings`, fmt, JOURNAL entry, commit → `git pull --rebase` → push.
When this goes stale, write the successor and repoint CLAUDE.md + agent
docs.
