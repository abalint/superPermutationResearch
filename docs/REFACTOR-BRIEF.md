# REFACTOR BRIEF — clean architecture pass (prepared s63, 2026-08-02)

> **STATUS (s64, 2026-08-02): EXECUTED IN FULL — all six stages landed,
> every pin byte-identical.** Commits: P1 `0dc1fee`, P2 `a721ce6`,
> P1b `19def32` (prefixlib/p1a_assume promotion — the clean-checkout
> sim exposed a residual out/-import chain), P3 `fd786f2`, P4 `5af204c`,
> P5 `0d1c57c` + `fcb17d7`, P6 `e861bd2`. See JOURNAL s64 for the full
> reckoning and HANDOFF-S64 for carried state. Deviations from spec:
> `verify_master` promoted beyond the §3.1 list (it is a §6 pin);
> ValueEnum REJECTED in P4 (changes --help bytes; adapters kept
> single-sited); P6 found TWENTY ledger shapes, not 3. Open remainders
> are listed in JOURNAL s64 "next steps" (a0/qsb deep-parity ports, the
> four live ledger divergences, external certificate/gain1 dependency).
> §8's open questions were all answered by Andrew at session start:
> pylib/ at repo root; promoted copies canonical; PC dry-run approved
> (ran in scratch scope, farm restored idle).

**Mission (Andrew, verbatim):** "code refactor focusing on clean architecture
design that lets us continue to scale with reduced risks of new and
regression bugs."

This brief was prepared by the s63 orchestrator from a read-only survey of
the whole repo (numbers below are measured, with paths). **No refactor work
has been started.** You are the fresh agent doing it. You do NOT need the
theory stack (THEORY.md, NOVELTY-DESIGN.md) — read this brief, `CLAUDE.md`
(conventions + hard invariants), `docs/ARCHITECTURE.md`, and
`docs/OPS-BACKGROUND-AGENT.md`, then start.

## 0. The one rule that makes this refactor safe

Every engine in this repo is **deterministic** (lexicographic orders, no
RNG in the search cores). That means the acceptance bar for every stage is
**byte-identical replay of pinned runs**, not "tests still pass." A refactor
stage that changes any pinned number is wrong by definition — no judgment
calls. Fix the stage, never the pin. The pin list is §6.

Work in stages; one commit per stage; never mix a move/rename with a
behavior change in the same commit; `cargo test --release` (139 pass /
6 ignored — note some docs say "139 green", the full count is 145),
`clippy -D warnings`, `fmt` green at every commit.

## 1. Ground truth (measured 2026-08-02)

**Rust:** 13,561 lines / 22 files. `main.rs` is 2,521 lines dispatching 16
subcommands from one 1,770-line `match`. 145 `#[test]` (139 run by
default), zero unit tests in `beam.rs`, `beam2.rs`, `main.rs`,
`rollout.rs`, `greedy.rs`.

**The incremental-counter duplication (CLAUDE.md admits 3 copies; there are
5, plus a read-only 6th):**
- `Walk` (`src/walk.rs:18-56`, `advance` at 142-197) — 14 counters.
- `State` (`src/beam.rs:209-249`, `child_state` 302-360) — with the SAME
  arithmetic re-derived again inside `score_move` (~1136) and AGAIN inside
  `bucket_key` (355-372): the arcs/half_open/nearly_done rules appear 4×
  in beam.rs alone.
- `State2` (`src/beam2.rs:110-133`, advanced inline 290-311) — **drops 5 of
  the 14 counters** (`half_open, nearly_done, w2_bridges, door, long`), so
  beam2 cannot score with the deficit features or residual bound at all.
- `sojourn.rs` and `unionsearch.rs` each keep their own visited/cycle-rem
  bookkeeping (partial 4th and 5th copies).
- `model.rs` holds the feature-vector assembly order (read-only 6th).
The only automated drift defence is `tests/deficit_features.rs` (Walk vs
beam-State along a real beam path). **There is no State2 equivalent.**

**Python:** 387 files, only 94 tracked (24%). Zero packages, zero
`__init__.py`, zero automated tests (no pytest/unittest anywhere), **275
`sys.path` mutation sites**. Verification is 31 hand-run control scripts —
22 of which live in gitignored `out/`.

**The live-fire risk:** ~1,940 lines of engine-grade instruments are
gitignored under `out/` (`lib62.py`, `cover_search.py`, `mcover_search.py`
(742 lines), `symlib.py`, `cutlib.py`, `anatlib.py`, `dlxrun.py`) — one
`rm -rf out/` from gone — and TWO of them are hard imports of tracked,
farm-launched code: `analysis/farm/mc28_shim.py:126` imports `lib62` from
`out/s62/jtax`, and `analysis/counting/s62/{qsbsweep,a0gate}.py` import
`dlxrun` from `out/s57/proposer`.

**Copy-paste utility sprawl:** `first_visit_path` (the canonical walk
parser) exists in 6 near-identical copies; `canon`/`loop_of`/`door` in 10;
`h12` in 12; three `analysis/counting/s49` files are byte-identical to
`out/s49/item1` copies while `out/s49/item1/fuse.py` (366 lines) has
**silently forked** from `analysis/counting/s49/fuse.py` (811 lines) with
no marker of which is authoritative. DANGER: `canon` is **overloaded** —
`m3_check.py:75`'s `canon` has different semantics from the
kernelchain `canon`. Do not merge by name; merge by body.

**Farm harness:** the per-instrument quartet (`ship.sh/shim.py/env.ps1/
fetch.sh`) is ~54% verbatim boilerplate by normalized line-set
intersection — ~1,400 duplicated shell/PS1 lines across a0/qsb/mc28/s58 —
while the genuinely instrument-specific payload is ~25 lines of Python.
The STATUS-heartbeat contract exists only as prose restated per shim
docstring; it is the contract both documented s52b bugs violated. All
`.ps1`/`.sh` for the four newest instrument families are **untracked**.

**Data contracts:** 4 exist; only the rollout JSONL has a single
machine-checked definition (`src/bound.rs:178-221` + one canonical reader
`ml/common.py`). The split-profile contract has a divergent hardcoded copy
(`--records-profile` table at `src/sojourn.rs:98-105`). The covers-file
contract lives only inside gitignored `mcover_search.py`. "Ledger" means
≥3 incompatible shapes across 20 files.

## 2. Why these specifically (the bug ledger says so)

Recent sessions' actual bugs, mapped to root cause:
- MRV set-of-strings nondeterminism + scratch-file race (s63 cutconvert) →
  no shared deterministic-DFS/scratch utilities, no Python tests.
- `cover_search.py` superset family (missing mid test, s63) → engine-grade
  code with no automated control suite; caught only because a second
  engine was hand-controlled against it.
- `nearcovers.py` undercount (s62) → same.
- GATE.txt escape-scan false banner, 4th site (s62/s63); stall-minutes
  mis-sizing; CRLF sha corruption; bash-3.2 `mapfile` (s63 farm) → the
  quartet boilerplate is copied, so a fix in one site reaches no others.
- "139 tests" vs 145 reality; `fuse.py` fork → no single source of truth.

The refactor's success metric is that THIS list stops growing, not
abstract cleanliness.

## 3. Staged plan (priority order; stages are independent commits)

### P1 — Promote and package the Python instrument layer (highest value/risk ratio)
Create a tracked package (suggest `pylib/` at repo root, or
`analysis/lib/`; pick one, document it in ARCHITECTURE.md):
1. Move-by-copy the engine-grade gitignored instruments into it (`lib62`,
   `cover_search`, `mcover_search`, `dlxrun`, `symlib`, `cutlib`,
   `anatlib`, plus `paircuts` and `chain7` which are tracked-adjacent).
   Leave the `out/sNN` originals byte-untouched — they are the historical
   record the session REPORTs cite. New/tracked code imports the package;
   originals become frozen snapshots.
2. One canonical `walkio` module: `first_visit_path`, `weight`,
   `renumber`, corpus loading. One `canonical` module holding BOTH canon
   semantics under distinct names (`canon_rotation`, `canon_relabel_rev`).
   Migrate the 6/10/12-site copies in TRACKED code only; leave `out/`
   history alone.
3. Kill `sys.path` hacks in tracked code (`analysis/`, `ml/`) via the
   package; `out/` history keeps its hacks.
4. Adjudicate the `fuse.py` fork explicitly (diff the 449 lines; the
   811-line `analysis/counting/s49` copy is presumptively authoritative —
   confirm against JOURNAL s49/s50 records) and mark the loser with a
   header comment pointing at the winner.
Acceptance: a pinned-run suite (§6 Python pins) passes with imports
resolved through the package; `git grep "sys.path" analysis/ ml/` shrinks
to ~0; nothing under `out/` modified.

### P2 — A real Python test suite (converts existing controls, writes none from scratch)
pytest + a `tests_py/` tree. The 31 existing control/oracle scripts are
already the tests — wrap them: fast ones (< ~30 s: m3_check self-checks,
verify_master witnesses, scope/doorlaw checks, paircuts oracle,
brute_tight n=4 census-equality, mcover control tier (a) n=4/n=5) as
default suite; slow ones behind `-m slow`. Pin the §6 Python numbers as
asserts. Add the missing determinism guard: run any DFS-style instrument
twice under two `PYTHONHASHSEED`s and assert byte-identical output (the
s63 cutconvert lesson, generalized). Wire a single `make check` /
`scripts/check.sh` that runs cargo tests + fast pytest.
Acceptance: `pytest` green locally from a clean checkout; documented in
CLAUDE.md commands block.

### P3 — Unify the Rust incremental state (highest risk — best guarded)
One `SearchState` (or extend `Walk`) owning the 14 counters + all update
rules, consumed by beam/beam2/sojourn/unionsearch; `score_move`/
`bucket_key` read cached values instead of re-deriving. beam2's `State2`
gains the 5 missing counters (this UNLOCKS deficit/residual scoring in
beam2 — but do NOT enable any new scoring in this refactor; parity first).
Extend the `deficit_features.rs` drift test to cover State2 and sojourn.
Respect the existing perf constraint: beam scores candidates in O(1)
without cloning (CLAUDE.md conventions) — the shared state must not
regress node throughput more than noise (benchmark: stratified beam n=6
~8 s; greedy n=6 sub-second).
Acceptance: §6 Rust pins byte-identical INCLUDING node counts; test count
does not decrease; a State2 drift test exists.

### P4 — Decompose `main.rs`
16 match arms → `src/cli/<command>.rs` modules (mechanical); delete the
hand-mirrored `BoundArg`/`DedupArg` enums in favor of clap `ValueEnum` on
the library types. Acceptance: identical `--help` output per subcommand
(snapshot before/after), §6 pins unchanged.

### P5 — One farm harness template
Single parameterized `ship.sh`/`fetch.sh`/`env.ps1` + a config file per
instrument (tag, target, payload manifest, alarm additions, stall
minutes); shims collapse to the measured ~25-line adapter + shared
STATUS-emitter module (`pylib/farmstatus.py`) that encodes the heartbeat
contract ONCE (tab format, declared-total, alarm-regex-safe printing,
work-based tick). Port mc28 (the newest, most complex) as the proving
instrument; a0/qsb configs follow. Track ALL farm scripts in git.
Acceptance: `mc28_env.ps1 -Full`-equivalent parity + a `-DryRun` smoke on
the PC reproduce the s63 results (24/24 DONE, escape scan 0); the s52b
alarm regex test still passes; OPS-BACKGROUND-AGENT.md updated to point
at the template.

### P6 — Write the contracts down
A `docs/CONTRACTS.md` (or ARCHITECTURE.md section) with normative
definitions: rollout JSONL (link the serde struct), split-profile (and
eliminate the divergent hardcoded `--records-profile` table by loading the
committed profile file), covers-file v1 (promote its spec out of
mcover_search's docstring), farm STATUS heartbeat (now backed by the P5
emitter), ledger shapes (name the three, stop pretending they are one).
Acceptance: every contract names its single authoritative
definition-in-code; ARCHITECTURE.md gains the missing `analysis/`+`out/`
section (survey table from this brief is a starting point).

## 4. Explicit non-goals
- No algorithm/feature changes, no new search capabilities, no scoring
  changes (P3 explicitly defers enabling beam2 deficit scoring).
- No edits to anything under `out/sNN/` (frozen history), `data/`,
  or the theory docs.
- No renaming of CLI flags or JSONL fields (models and scripts depend on
  them; JSONL back-compat is a CLAUDE.md hard invariant).
- No farm launches. P5's PC-side verification is env-check + dry-run only,
  and only if the farm is idle (check with Andrew's queue first).

## 5. Hard invariants (from CLAUDE.md — restated because they gate every stage)
- Greedy min-weight + lex tie-break MUST produce 9/33/153 (n=3/4/5).
- Lower bounds stay admissible; beam dedup requires score = pure function
  of `(cur, visited, len)` (`(front, back, visited, len)` in beam2).
- Every produced string passes the validator before being reported.
- Rollout JSONL changes must be back-compatible or version-bumped.
- Incremental features maintainable in O(1)/O(n) per expansion.

## 6. The pin list (byte-identical before/after every stage)

Rust (run each, record before-values once, diff after):
```
cargo run --release -- greedy -n 5            # 153
cargo run --release -- greedy -n 6            # 873
cargo run --release -- beam -n 4 --width 512  # 33
cargo run --release -- beam -n 5 --width 2000 # 153
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1 --stratify --strat-quota 4 --strat-bucket 1   # 873, ~8s
cargo run --release -- beam2 -n 5 --width 2000
cargo run --release -- sojourn-dfs -n 6 --class 143,5,0,0,0 --profile-file analysis/trackb/profiles/a143_5_0_0_0.txt --depth 6 --dedup exact --fresh-doors --max-nodes 30000000   # node count must match exactly
cargo test --release   # 139 pass / 6 ignored; count must not decrease
```
Capture full stdout (lengths AND node/level counts) to files and `diff`.

Python (fast, all deterministic):
```
python3 out/s62/jtax/cover_search.py 4 40 --jmin 0                      # 320 nodes, {0:33,...}
python3 out/s62/jtax/mcover_search.py 4 40 --v 2 --splits 0 --jmin 0 --prune legacy --no-mids   # 320 nodes
python3 out/s62/jtax/mcover_search.py 5 155 --v 6 --splits 0 --jmin 0 --prune legacy --no-mids  # 964,317 nodes, a(5)=153
python3 out/s62/jtax/mcover_search.py 4 38 --v 3 --splits 3 --jmin 0    # census {(2,36):12,(2,37):14,(3,37):14,(3,38):5,(4,38):40}
python3 out/s62/jtax/verify_master.py 5 out/s63/mcover/mc_n5_v7_s4_j0_153.txt out/s63/mcover/mc_n5_v7_s4_j1_154.txt   # ALL PASS
python3 out/s63/chains/scope_check.py    # words=177 impure=0 prediction_failures=0
python3 out/s63/chains/doorlaw_check.py  # doors=3122 inter_w2=145979, 0 violations
python3 out/s63/chains/singleton_pass.py farm0 --workers 7   # 54 deleted, fixpoint pass 2
python3 analysis/counting/m3_check.py data/upstream872_specimens/872.up-6dbae421a839.txt  # known, NOT novel
```
(When P1 promotes these into the package, the pins run against the
package copies with identical numbers.)

Heavier optional gates (run once at the end): the 36,304,934-node n=6
TMAX-868 mcover/cover_search parity pair (~2×2.5 min), and
`brute_tight.py 4 38` (41,591,451 nodes, ~35 s).

## 7. Suggested session structure for the refactor agent
1. Read: this brief → CLAUDE.md → ARCHITECTURE.md → OPS-BACKGROUND-AGENT.md.
2. Capture ALL §6 before-pins to `out/s64/refactor/pins_before/`.
3. Execute stages in order (P1, P2 first — they carry the most bug-risk
   reduction per hour and cannot break the Rust core at all). P3 only
   with the pins green twice in a row. P4–P6 as time allows; each stage
   is independently valuable and independently committable.
4. Each stage: implement → run relevant pins + full test suite → commit
   with a stage-scoped message → JOURNAL entry line.
5. Session end: JOURNAL s64 entry, update this brief (strike completed
   stages, note deviations), HANDOFF-S64 if the front moved, ritual
   commit/push.

## 8. Open questions to surface to Andrew (do not decide unilaterally)
- Package name/location (`pylib/` vs `analysis/lib/`) — cosmetic but
  permanent.
- Whether promoted instruments should REPLACE their `out/` originals in
  future sessions' usage (recommended: yes, via CLAUDE.md note) or
  coexist indefinitely.
- Whether P5's PC-side dry-run can run during the day (farm is idle but
  Andrew holds runs; a dry-run writes only to a scratch tag — ask first).
- The `fuse.py` fork adjudication if the JOURNAL record is ambiguous.
