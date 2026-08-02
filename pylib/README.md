# `pylib/` — the tracked Python instrument layer

Created s64 P1 (2026-08-02), per `docs/REFACTOR-BRIEF.md` §3 P1.
Package home chosen by Andrew: **`pylib/` at the repo root**.

## The two rules

1. **These copies are CANONICAL.** New and tracked code imports from
   `pylib`. Every bug fix, every extension, happens here.
2. **The `out/sNN` originals are FROZEN and must stay byte-untouched.**
   They are the historical record the session REPORTs and JOURNAL
   entries cite by path. Never edit them; never "fix" them. If a
   promoted copy diverges from its origin, the divergence is stated in
   that file's provenance header and listed below.

`out/` is gitignored, so before s64 ~1,940 lines of engine-grade
instruments were one `rm -rf out/` from gone, and two of them were hard
imports of tracked, farm-launched code. That is what this package fixes.

## What lives here

### Promoted instruments (byte copies + a provenance header)

| module | promoted from | what it is |
|---|---|---|
| `lib62.py` | `out/s62/jtax/lib62.py` | s62 ledger coordinates: `first_visit_path`, `weight`, `rotc`, `lam`, `analyze_path` |
| `cover_search.py` | `out/s62/jtax/cover_search.py` | s62 D1 perfect-ride family decision engine (§6 pin) |
| `mcover_search.py` | `out/s62/jtax/mcover_search.py` | s63 supply-tight k-loop MULTI-cover engine, 742 lines (§6 pins ×3) |
| `verify_master.py` | `out/s62/jtax/verify_master.py` | the MASTER-inequality control for the two above (§6 pin) |
| `dlxrun.py` | `out/s57/proposer/dlxrun.py` | the `dlx7g` subprocess driver + three-valued verdict discipline |
| `symlib.py` | `out/s60/retrieval/symlib.py` | validated S₇×rev symmetry action (0.1 s chain-equivalence test) |
| `cutlib.py` | `out/s60/nogood/cutlib.py` | s60 no-good cut store + the ≥10×-cap re-confirmation harness |
| `anatlib.py` | `out/s61/anatomy/anatlib.py` | s61 near-miss residual anatomy (exact hypergeometric null) |
| `paircuts.py` | `analysis/counting/s58/paircuts.py` | s58 pairwise cut harvest (was tracked-adjacent but untracked) |
| `chain7.py` | `analysis/cover7/chain7.py` | kernel-parameterized n=7 instance builder + certificate assembly |
| `prefixlib.py` | `out/s59/prefix/prefixlib.py` | s59 walk-order prefix proposer core (s64 P1b; `cutlib`/`anatlib` import it) |
| `p1a_assume.py` | `out/s56/p1a/p1a_assume.py` | s56 P1a assumption extraction + restricted DLX gate (s64 P1b; `prefixlib` imports it) |

`verify_master.py` is one module beyond the brief's list: it is the
gitignored engine-grade control for `cover_search`/`mcover_search`, it is
itself a §6 pin, and promoting it is what lets the whole jtax pin block
re-run through the package.

`chain7.py` and `paircuts.py` were promoted **by copy as well** — their
originals stay in place because frozen `out/sNN` scripts import them from
those paths. New code must use the `pylib` copies.

### Consolidated utility modules (merged BY BODY, never by name)

- **`walkio.py`** — one `first_visit_path` (was 6 copies), one `renumber`
  (6), one `weight` (3), plus `first_visit_starts`, `overlap`, `rot`,
  `rotc`, `g`, `lam`, and corpus loading (`read_walk`, `class_files`,
  `strings_from_text`). Every merged body is listed in the module
  docstring with its source line. Only two real differences existed:
  `upstream5906_twocycles.py`'s `first_visit_path` took `n` from a module
  global instead of a parameter (the `(s, n)` superset is kept), and
  `build_supp_index_s51.py`'s `renumber` put `out = []` on its own line.
- **`canonical.py`** — **both** `canon` semantics under distinct names.
  `canon` was overloaded across 17 definitions in two incompatible
  meanings; `pylib` refuses to export a bare `canon`:
  - `canon_rotation(w)` — least cyclic ROTATION (kernelchain/certificate
    frame, 10 byte-identical sites), together with `door`, `tv`,
    `inverse_tv`, `loop_of`.
  - `canon_relabel_rev(s)` — `min(renumber(s), renumber(reverse(s)))`,
    the M3 relabel+reversal class representative (7 sites, including the
    `m3_check.py:75` site the brief flags as the DANGER). Changing it
    invalidates every committed `*_canon_index.tsv`.
  - `h12` / `hash12` — the 12-hex class fingerprints (12 sites). `h12`
    is the superset body (`blindspot.py`'s, which raises `SystemExit`
    naming the bad spelling; `admdiff.py`'s let an empty match raise a
    bare `IndexError`).

## The ONE sanctioned bootstrap

Scripts run as plain files from arbitrary depths, so Python puts the
*script's* directory on `sys.path`, never the repo root. Each entry
script therefore carries exactly one line, identical everywhere:

```python
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
```

Depth-independent, cwd-independent, and the only `sys.path` text left in
`analysis/` + `ml/`. Everything after it goes through the package:

```python
import pylib
pylib.add_paths("analysis/counting")   # repo-relative, idempotent
pylib.add_legacy_paths()               # prefixlib / p1a_assume / certificate
from pylib.walkio import first_visit_path, weight
from pylib.canonical import canon_relabel_rev
```

Still reached through `pylib.add_legacy_paths()`: `certificate` /
`gain1`, which live **outside this repo** in the sibling
`../extraDocs/superpermutation-examples/scripts` checkout — a hard
external dependency of the entire n=7 stack (`chain7` imports
`certificate`). `prefixlib` and `p1a_assume` were promoted in s64 P1b
(closing the last `rm -rf out/` code risk); the out/ homes remain listed
only as DATA paths (`controls.pkl`, `prune_all.json`, `positives.pkl`
are regenerable session artifacts, not code).

## Divergences from the frozen originals

Import mechanics only — never instrument logic. All four are stated in
the file's own provenance header:

- `symlib.py`, `cutlib.py`, `anatlib.py`, `paircuts.py`, and (s64 P1b)
  `prefixlib.py`, `p1a_assume.py`: the originals computed
  `REPO = abspath(HERE/../../..)` from three levels down. `pylib/` sits
  one level under the repo root, so those lines became
  `REPO = os.path.dirname(HERE)`, and `HERE` was added to each module's
  own path list so the promoted `chain7`/`dlxrun`/`symlib`/`prefixlib`/
  `p1a_assume` copies win over the frozen ones. `cutlib`/`anatlib` keep
  `S59`/`PREFIX` as data-only paths (no longer on `sys.path`).

Nothing else changed. `lib62`, `cover_search`, `mcover_search`,
`verify_master`, `dlxrun` and `chain7` are byte-identical to their
origins apart from the header comment block.

## The `fuse.py` fork — ADJUDICATED (s64 P1)

**Winner: `analysis/counting/s49/fuse.py` (811 lines). The 366-line
`out/s49/item1/fuse.py` is a superseded s49-era snapshot.**

Evidence:

- The full diff is 445 added lines and **exactly 2 removed** (`def
  main():` and `    main()`, both re-spelled inside larger blocks). The
  tracked copy is a strict superset.
- Everything added is the s52 `untargeted` mode: `file_map`,
  `walk_arrays`, `check_plans`, `DIRS220`, `RECORD`, plus the
  `untargeted --shard i/24` CLI. JOURNAL s52 records that mode being
  built ("`fuse.py untargeted` built + controlled"); JOURNAL s52b
  records it being *run* on the farm ("fused-pair untargeted (7.4 min,
  farm `u1`) … 4,713,880 fused pairs"). The out/ copy predates all of
  it.
- CLAUDE.md's reading order cites `analysis/counting/s49/fuse.py` by
  path for the s49/s50 blind-spot closure.

No marker comment was added to the loser: `out/` stays byte-untouched.
The verdict is recorded here, in the s64 P1 commit message, and in the
JOURNAL. `fuse.py` was **not** promoted into `pylib/` — it is a
mode-driven sweep instrument, not a shared library, and it was already
tracked and canonical where it sits.

(Unrelated, noticed while diffing: `analysis/counting/s49/sumset.py`
(186 lines) has also drifted from `out/s49/item1/sumset.py` (177). Same
direction — the tracked copy is the later one — but it was not part of
this stage's mandate and was not adjudicated in depth.)

## Not a distribution

No `pyproject.toml`, no `setup.py`, no version. Nothing is installed;
consumers are scripts inside this repo. Adding a build system would buy
nothing and add a failure mode.
