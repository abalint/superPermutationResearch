# CONTRACTS — the repo's data formats, normatively

Written s64 P6 (`docs/REFACTOR-BRIEF.md` §3 P6). This file is **normative**:
where it and a comment elsewhere disagree, the *authority named here* wins,
and the comment is the bug.

Every contract below names **one authoritative definition-in-code**. That is
the whole point. Before s64 four contracts existed and only one of them
(rollout JSONL) had a single machine-checked definition; the split-profile
had a forked copy in Rust, the covers-file spec lived in a gitignored
docstring, the farm heartbeat existed only as prose restated per shim, and
"ledger" named at least twenty mutually incompatible shapes.

Rule of thumb for adding a contract: if two pieces of code must agree on
bytes, one of them owns the definition and the other reads it. If neither
can, a `#[test]`/pytest that asserts them equal is the minimum acceptable
substitute — see §2, which is exactly that case.

| # | contract | authority | consumers |
|---|---|---|---|
| 1 | Rollout JSONL | `src/bound.rs::Features` (serde) | `ml/common.py` (the only reader) |
| 2 | Split profile | `analysis/trackb/profiles/*.txt` + `SplitProfile::from_file` | `sojourn-dfs`, `nrpa`, `grammar-check` |
| 3 | Covers file v1 | `pylib/mcover_search.py` (`read_covers`/emit block) | mc28 farm harness, every shard |
| 4 | Farm STATUS heartbeat | `pylib/farmstatus.py` | every farm adapter; `untargeted_super.ps1` reads it |
| 5 | "Ledger" | **twenty distinct shapes** — see §5; there is no unified authority and none should be invented | per-shape |

---

## 1. Rollout JSONL

**Authority: `struct Features` in `src/bound.rs` (the serde
`Serialize`/`Deserialize` derive).** The single canonical reader is
`ml/common.py::load`. `docs/ARCHITECTURE.md` §"Rollout JSONL schema" carries
the field table; it is documentation *of* the struct, not a second
definition.

- One JSON object per line, serialized by `serde_json` **in field
  declaration order**. Field order in the struct is therefore part of the
  observable format.
- Per rollout exactly `n!` lines: the start state at `step: 0`, then one per
  `advance`.
- Rollout `i` uses `StdRng::seed_from_u64(seed.wrapping_add(i))` — same seed
  ⇒ byte-identical file (pinned by `rollouts_deterministic_and_consistent`).
- `cost_to_go` is backfilled once the rollout ends: `final_len −
  len_so_far`, so the last line of each rollout has `cost_to_go: 0` and
  `r: 0`.
- Writers: `rollout::run_rollouts` / `run_rollouts_guided` /
  `log_trajectory` (the last is what `greedy --log` and `beam --log` emit —
  byte-identical to an ε=0 rollout, pinned by
  `log_trajectory_matches_epsilon0_rollout`).

### The back-compat invariant (restated — it is a CLAUDE.md hard invariant)

> **Rollout JSONL schema changes must be backward compatible or
> version-bumped — trained models depend on this format.**

What that means mechanically, given how `Features` is derived:

- **Adding** a field is allowed **only** with `#[serde(default)]`, so files
  written before the field parse as 0. Every post-phase-1 field already does
  this: `arcs`, `succ1_unvisited`, `half_open`, `nearly_done`,
  `w2_bridges`.
- **Removing or renaming** a field breaks `Deserialize` on every existing
  corpus (the non-defaulted fields are required) and is forbidden without an
  explicit version marker.
- **Reordering** fields changes the bytes of every newly written file. Old
  files still parse, so this is legal, but it is a gratuitous pin break —
  don't.
- The Python side is length-dispatched, not name-dispatched: `ml/common.py`
  defines `FEATURE_ORDER_V1` (8) and `FEATURE_ORDER` (11, v2 = v1 + the
  three deficit-distribution columns), and a model consumes exactly the
  first `len(feature_order)` entries. So the *feature* contract extends
  append-only in lockstep with the JSONL contract, and committed 8-feature
  models keep scoring bit-identically (pinned in `src/model.rs`'s tests).

Corollary the refactor stages lived by: `--bound`/`--model` flag names and
JSONL field names are not renameable (`docs/REFACTOR-BRIEF.md` §4).

## 2. Split profile (the per-allocation L1 grammar)

**Authority: the committed census files `analysis/trackb/profiles/a*.txt`,
parsed by `SplitProfile::from_file` in `src/sojourn.rs`.**

A split profile is the set of allowed **per-cycle part compositions** for one
L0 allocation: which ways a rotation cycle's `n` members may be split into
maximal same-cycle runs. It is *data*, produced by the s27 corpus census
(`analysis/counting/upstream872_structure.py --profiles-dir`) as the union of
compositions observed over that allocation's community classes.

### File format

```
# n=6 allocation S=145 d3=3 d4=0 d5=0 ip=0 — union of compositions over 21144 community classes (s27 census)
2 2 2
2 4
3 3
4 2
6
```

- One composition per line, part lengths **space-separated**.
- `#` starts a comment (to end of line); blank lines skipped.
- Every part must be in `1..=n` and the parts must **sum to n**; violations
  are a hard parse error naming the line number.
- Duplicate compositions are dropped (first occurrence wins).
- An empty result is an error.
- **Listing order is not observable.** Every consumer of
  `SplitProfile::allowed` quantifies over it with `any` (`part_ok`,
  `open_part_ok`) or `min` (`min_more_parts`). Two files with the same
  composition *set* in different orders produce byte-identical searches.

### The eight committed profiles

`analysis/trackb/profiles/` holds one file per specimen-backed n=6 L0
allocation (s26c census): `a145_3_0_0_0` (the records class, 21,144
classes), `a143_5_0_0_0`, `a142_6_0_0_0`, `a141_7_0_0_0`, `a140_8_0_0_0`,
`a140_6_1_0_0`, `a138_8_1_0_0`, `a135_9_2_0_0`. The filename encodes
`S_d3_d4_d5_ip`.

### `--records-profile` vs `--profile-file` (de-forked, s64 P6)

Both flags land in `cli::load_profile`. They differ **on purpose**:

- `--profile-file PATH` — the user named a file. A bad path or a bad
  composition is a **hard error** (`exit 1`, message from `from_file`).
  Paths are plain cwd-relative, unchanged since s27.
- `--records-profile` — the user named *no* file, so this flag must not be
  able to fail at file IO. It resolves through
  `SplitProfile::records_n6_loaded()`, which loads
  `analysis/trackb/profiles/a145_3_0_0_0.txt` — located first cwd-relative,
  then by walking up from the running executable, so the release binary
  finds the repo from any working directory — and **falls back to the
  compiled-in constant `SplitProfile::records_n6()`** if the file cannot be
  found or parsed. Out-of-repo invocations therefore behave exactly as they
  did before s64.

Until s64 P6 `--records-profile` had **only** the compiled-in table, forked
from the census file that defines the same object. The fork is now pinned
shut by `src/sojourn.rs`'s
`records_n6_constant_equals_committed_profile_file`, which asserts constant
== file as composition sets (and that `records_n6_loaded()` agrees). If you
edit `a145_3_0_0_0.txt`, that test fails until you edit the constant to
match — which is the intended cost of changing a contract.

**Verdict of the s64 P6 equality check: the two agreed.** Constant
`[[6],[2,4],[3,3],[4,2],[2,2,2]]`; file `[[2,2,2],[2,4],[3,3],[4,2],[6]]`.
Equal as sets, different listing order, and listing order is provably
unobservable (above). All three `--records-profile` pins (exact-tier d=6 at
the 5M cap, the M2 book-mode d=10 run — 746,107 nodes / 13,527 classes —
and `grammar-check` over the 8 committed specimens) are byte-identical
before and after, from the repo root, from `/tmp`, and from an isolated
copy of the binary with no repo above it.

The other three `SplitProfile::records_n6()` call sites are all `#[cfg(test)]`
fixtures (`src/sojourn.rs`, `src/nrpa.rs`) and deliberately keep using the
constant directly.

## 3. Covers file v1 (`mcover-covers v1`)

**Authority: `pylib/mcover_search.py` — the emit block inside `run()`
(`--emit-covers`) and `read_covers`/`iter_covers` (`--covers-file`).**
Promoted out of a gitignored docstring by s64 P1/P6; the frozen
`out/s62/jtax/mcover_search.py` original is history, not authority.

### Why it exists

Stride-sharding the multi-cover **enumeration** makes every shard re-walk
the whole enumeration tree: `N` shards do `N ×` the enumeration for `1 ×`
the search. (This is the s63 stride-sharding trap; count-only sizing does
not reveal it.) So the stream is enumerated **once**, written to a file,
shipped, and each shard consumes a slice of the *file*. Shards then have
exactly equal line counts instead of equal-in-expectation ones.

### Format

```
# mcover-covers v1 n=<N> v=<V> splits=<S> forest=<0|1>
<int> <int> ... <int>
<int> <int> ... <int>
...
# total <NLINES>
# sha256 <hex digest of the body bytes>
```

- **Header**: a comment line whose first token is `mcover-covers`, followed
  by the version and `k=v` tokens. A consumer passes its own `n/v/splits/
  forest` as `expect=` and any mismatch fails verification (with a
  `*** COVERS FILE MISMATCH ***` line).
- **Body**: one multi-cover per line, loop ids as space-separated ints,
  **in enumeration order**. Line index *is* the enumeration index, which is
  what makes `--covers-file --stride K --offset O` agree cover-for-cover
  with an in-process `--stride K --offset O` run.
- **Trailer**: `# total N` (the body line count) and `# sha256 <hex>`.
- **The sha256 is over the BODY BYTES ONLY** — the cover lines including
  their trailing `\n`, not the header or trailer. This lets a shard prove it
  holds the emitter's stream before processing a single line.
- **LF, always.** The file is opened `newline=""` so a `"\n"` is one LF byte
  on Windows too. s63 lost a farm pre-flight to exactly this: Windows text
  mode wrote CRLF while the digest was accumulated over the pre-translation
  bytes, so every shard would have exited 4. (Same rule as
  `farmstatus.open_lf`; see §4 clause 9.)
- Reading skips `#` lines and blank lines.

### Verification and failure

`read_covers` returns `(hdr, nlines, ok, sha_got, sha_want, declared_total)`
with `ok = (sha_want == sha_got) and (declared_total == nlines)` and all
`expect=` header keys matching. A consumer that gets `ok = False` prints
`*** COVERS FILE FAILED VERIFICATION -- refusing to run ***` and **exits 4**.
Exit 4 is the covers-file verdict; do not reuse it.

- `--emit-covers` **requires `--stride 1`** — the file is the whole stream;
  shard when *consuming*, never when emitting.
- The mc28 farm harness depends on all of this: `analysis/farm/mc28_shim.py`
  (and its P5 port `analysis/farm/template/mc28_adapter.py`) makes
  `--covers-file` **required**, re-verifies the shipped file's sha on the PC
  before any search, and self-tests the emit→shard→union round trip at n=5
  (`v=7, splits=4`, 7 shards) so that the per-shard line counts provably sum
  to the declared total.

## 4. Farm STATUS heartbeat

**Authority: `pylib/farmstatus.py` (s64 P5). Pinned by
`tests_py/test_farmstatus.py`.** The *reader* is the supervisor
`analysis/farm/untargeted_super.ps1` (and `untargeted_status.ps1`), which is
unchanged and generic; `farmstatus.py` is the client side of its protocol,
derived from that supervisor **as built** (its docstring carries the line
refs). If the supervisor changes, this module changes.

Before s64 this contract existed only as prose, restated and drifted per
shim docstring — and **both documented s52b farm bugs are violations of it**
(a heartbeat whose row unit differed from its declared total, and a healthy
`… : 0` summary line that matched the supervisor's alarm scan and bannered
all 24 shards).

The nine clauses, in brief — read the module docstring for the full text:

1. **File.** The heartbeat is a file whose name starts with `STATUS`, in the
   shard's `--out` directory. **Append-only and line-buffered**: the
   supervisor reads incrementally and a killed shard must leave its history
   on disk.
2. **Progress rows.** A row counts as progress iff it contains a
   tab-delimited `<i>/<n>` **field** — `\t(\d+)/(\d+)\t`. The supervisor
   counts *rows* and reads the declared total from `<n>`; it never reads
   `<i>`. Two consequences: the field needs a tab on **both** sides (so it
   can never be the last field), and **the row count and `<n>` must be in
   the same unit**.
3. **Work-based tick.** The caller ticks REAL WORK (`FarmStatus.work()`);
   the emitter converts units → rows and derives `declared_rows` from the
   same `tick`, so units cannot drift from the declared total. A tick is
   also a stall decision: one row every `tick × per-unit-seconds`, and
   `-StallMinutes` must exceed that gap.
4. **Non-progress rows must not look like progress.** DONE/ESCAPE/note rows
   carry no `i/n` field. Enforced structurally: every writer strips tabs and
   newlines out of caller text, so a note can never manufacture a field
   boundary.
5. **Terminal row.** `<ts>\tDONE\t<summary>` sets the supervisor's `sawDone`
   — the strong completion verdict (`verdict-by=STATUS-DONE` beats
   `verdict-by=heartbeat`). Emit it **even on failure**; put the rc in the
   summary.
6. **Escape rows.** `<ts>\t(ESCAPE|MIDESCAPE|SHORTER)\t<detail>` is the
   supervisor's alarm channel: it raises `ALARM.txt` and banners STATUS.
   This is the row a *find* writes, and it is not a progress row.
7. **Alarm-regex-safe stdout.** The supervisor scans new stdout with
   `(?i)Traceback|MemoryError|^\s*!!|\*\*\*|ESCAPES\s+[1-9]|NOVEL[^:\r\n]*:\s*[1-9]`.
   A healthy shard must be **structurally incapable** of matching it:
   `safe_print()` raises `AlarmContractError` on any line that would,
   `banner()` is the one sanctioned way to match on purpose, and
   `check_summary()` makes "diff a new instrument's terminal summary against
   the alarm regex" executable.
8. **Products.** `untargeted_status.ps1` counts **every `*.txt`** under the
   run's `out\` tree and banners them as ESCAPE CANDIDATES — so a scratch
   `.txt` is a false find (four recurrences through s63). Notes go to `.md`
   (`gate_md()` refuses a `.txt` name). A `.tsv` whose name matches
   `(?i)stat` is row-counted as a product and `(?i)edge` as rediscoveries;
   anything else must match neither.
9. **Newlines.** Every file is opened `newline=""` so `"\n"` is one LF byte
   on Windows too (`open_lf`). Same s63 lesson as §3.

Plus one schema the adjudicator depends on: `FarmStatus.finish()` writes the
**canonical per-shard stats row** `STATS_HEADER = (shard, shards,
units_done, units_declared, finds, secs, rc)`, which is what makes
`analysis/farm/template/farm_fetch.sh` generic — one adjudicator can check
"every shard rc 0, every shard has a DONE row, the per-shard unit counts SUM
to the declared total" for any instrument. Instrument-specific numbers go in
a **second** TSV whose name matches neither `(?i)stat` nor `(?i)edge`.

The harness that consumes all of this is `analysis/farm/template/`
(`farm_ship.sh`, `farm_fetch.sh`, `farm_env.ps1`, `farmlayout.py`, one
`<tag>_adapter.py`, `configs/<tag>.conf`); see its `README.md` and
`docs/OPS-BACKGROUND-AGENT.md`.

## 5. "Ledger" — twenty shapes, no unification

The word "ledger" in this repo names **twenty mutually incompatible on-disk
shapes** across ~110 files, plus two things called a ledger that are not a
data shape at all (the brief's "≥3 shapes across 20 files" was an
undercount; surveyed s64 P6, every header below read from the file or the
emitter). They are **not** one format, they have no common key, and this
section does **not** unify them. It names them so that nobody writes a
"generic ledger reader" again, and so that a new ledger can be checked
against the list before it becomes the fifteenth.

Two facts about the list that are themselves findings:

- **Only 4 of the 20 have a named column constant** (`satworker.HEADER`,
  `flsuper.$HEADER`, `a0gate.LEDGER_COLS`, `a0gate.STAT_COLS`). The rest are
  inline literals, five of them duplicated across files — which is why §5.6
  exists.
- **7 of the 20 authorities are UNTRACKED** — they live in gitignored
  `out/sNN/` (`express.py`, `prefix_propose.py`, `gate2.py`,
  `run_gradient.py`, `qsb.py`, `gzrun.ps1`) or in gitignored
  `analysis/trackc/runs/` (`status.sh`, `record.sh`). s64 P1/P1b closed the
  `rm -rf out/` risk for engine-grade *code*; it did **not** close it for
  these *shape definitions*. Nothing tracked currently depends on them, so
  this is recorded rather than fixed — but a new instrument must not add to
  the list.

### 5.1 Structural / mathematical

| name | shape | authority | canonical instance |
|---|---|---|---|
| **`LEDGER-L0-CLASS`** | CSV+header, 11 cols: `S,d3,d4,d5,d6,ip,waste,length,status,closure,notes` | `analysis/trackb/enumerate_l0.py` (the dict literal feeding `csv.DictWriter`) | `analysis/trackb/ledger_l0.csv`, 34,272 rows |
| **`LEDGER-SOJOURN-FRONTIER`** | TSV, `#`-commented header, 8 cols: `class_key(32 hex) len s d3 d4 d5 ip path(comma-joined ranks)` | `src/cli/sojourn_dfs.rs` (`--dump-frontier` writer); in-memory packing is `sojourn::pack_ledger` | `data/frontiers_s28/f_*.tsv`, 6 files |
| **`LEDGER-EXPRESSIBILITY`** | JSON (not JSONL). Two sub-shapes: a 221-record corpus **array** (13 fields) and a per-word object (22 fields) | `out/s57/express/express.py` (both `--ledger-out` and `ledger()`) | `out/s57/express/ledger_all.json` |
| *(`loop_ledger_probe`)* | **no shape** — `analysis/counting/loop_ledger_probe.py` prints its ledger quantities (`S, D, W, splits, σ, L, deficit, x, runs, Φ, v, j`) to stdout and serializes nothing | — | — |

Seam worth knowing: `ledger_l0.csv` carries `d6`, but its canonical reader's
key tuple is `FIELDS = ["S","d3","d4","d5","ip"]`
(`analysis/trackb/alloc_neighbors.py`), which filters `d6 != 0` separately.
The two are not interchangeable keys.

`LEDGER-EXPRESSIBILITY`'s per-word `ledger()` is **forked**:
`pylib/p1a_assume.py`'s version lacks `pivot_breaks`/`gen_doors` and
hardcodes `law_2loop == 142`, while `out/s57/express/express.py`'s adds them
and uses `142 if len == 5906 else 143`. `express.py` carries an explicit
cross-check that the two agree on their shared fields; the s57 copy is the
later one.

### 5.2 n=7 chain census (four shapes, all `analysis/cover7/`, all keyed on `index`)

| name | cols | authority | instance |
|---|---|---|---|
| **`CENSUS-PASS1`** | 11: `timestamp,index,pattern,K,Sigma,engine,outcome,best_partial,minutes,worker_pid,word_file` | `analysis/farm/satworker.py` — `HEADER` **named constant**. This is also the schema of the live farm ledger `F:\superpermFarm\results.csv` | `results_n7_pass1.csv` (223 rows) |
| **`CENSUS-DLX-SWEEP`** | 8: `index,pattern,K,Sigma,verdict,nodes,maxdepth,seconds` | `analysis/trackc/census_sweep.sh` | `results_n7_dlx_sweep.csv` (142 rows) |
| **`CENSUS-MERGED`** | 8: `index,pattern,K,Sigma,verdict,zero_candidate_columns,cadical_pass1,dlx_sweep` | `analysis/trackc/census_merge.py` | `results_n7_merged.csv` (223 rows) — **the canonical census** |
| **`CENSUS-SCOPED`** | 15: `CENSUS-MERGED` + `V,chain_frame,cover_language_scope,verdict_scope,corpus_in_frame,corpus_total,corpus_frame_fraction` | **none — no generator exists in the repo** | `results_n7_scoped.csv` (223 rows) |

Two traps, both live:

- `CENSUS-DLX-SWEEP` ends with a **non-CSV sentinel row**,
  `SWEEP COMPLETE Tue Jul 28 07:05:32 MDT 2026`. `census_merge.py` skips it
  with `if not (r["index"] or "").isdigit(): continue`. A reader that
  forgets will crash or miscount.
- `CENSUS-SCOPED` was produced ad hoc in s57 and **the committed CSV is its
  only definition** — `corpus_frame_fraction` appears nowhere else in the
  repo. It is nonetheless cited normatively by CLAUDE.md for the 188/221
  frame-scoped claim. Treat the file as the authority and say so; do not
  regenerate it without writing the generator.

### 5.3 Farm run ledgers (operational — seven shapes)

| name | shape | authority |
|---|---|---|
| **`FARM-SHARD-EVENT`** | CSV+header, 10: `ts,shard,event,pid,pname,pstart,lines,secs,rc,note`; append-only, one row per `LAUNCH`/`DONE`/`FAIL`/`ABORT` | `analysis/farm/untargeted_run.ps1` (carries the "columns are FIXED for the life of this file (s19 lesson)" comment) — but hardcoded identically in `pysweep_run.ps1`, `promote_run.ps1` and re-spelled as a banner in `untargeted_status.ps1` |
| *(sibling)* **`FARM-TABLE`** | CSV+header, 9: `shard,pid,start,last_heartbeat,lines,total,state,rc,escapes`; a **live snapshot rewritten wholesale**, not append-only | `analysis/farm/untargeted_super.ps1` |
| **`FARM-STAGE-EVENT`** | CSV+header, 10: `ts,stage,event,pid,pstart,rc,secs,log_lines,log_bytes,note` | `out/grayzel_lake_build/farm-scripts/gzrun.ps1`. Deliberately near-`FARM-SHARD-EVENT` and **incompatible with it** |
| **`FARM-TAILATSP-WORKER`** | CSV+header, **18 or 23** cols (see below) | `analysis/farm/talaunch.ps1` (23-col, current) |
| **`FARM-TC2-JOB`** | **headerless** CSV, 9 fields (`ledger.csv`) or 12 (`ledger2.csv`) | `analysis/farm/tc2worker.ps1` / `tc2worker2.ps1`; column *names* exist only inside `tc2status.ps1`/`tc2status2.ps1` print strings |
| **`FARM-LKH-CONFIGSEED`** | **TSV**+header, 11: `config seed best gap gap_pct secs runs successes cracked trials logfile` | `analysis/farm/flsuper.ps1` — `$HEADER` **named constant** |
| **`TRACKC-JOB`** | CSV+header, **5 or 6** cols (see below) | `analysis/trackc/runs/v2/genlocal/status.sh` (6-col) |

Three live divergences, recorded rather than fixed:

- **`FARM-TAILATSP-WORKER` is three-way inconsistent.** The committed
  instance `data/farm_finds/a585recomp/ledger.csv` and `docs/OPERATIONS.md`
  both show 18 columns; the generator `analysis/farm/talaunch.ps1` writes
  **23**, inserting `r2_solved,r2_improved,r2_eq_new,r2_eq_same,
  r2_lambda_bad` before `secs`. The generator is authoritative for new runs;
  the committed file is an s31-era artifact. (`rc` is always empty by
  design — `detach.exe` discards exit codes.)
- **`FARM-TC2-JOB` field 8 has two different units under one name.**
  `tc2worker.ps1` writes **size in MB**; `tc2evalworker.ps1` writes a JSONL
  **line count**. This is deliberate (the line count OOM-wedged the farm,
  `docs/OPERATIONS.md`) and it is exactly why the column has no name in any
  file.
- **`TRACKC-JOB` has three spellings**: `genlocal/status.sh` writes
  `tag,verdict,rc,nodes,secs,jsonl_records`; `gates/record.sh` writes
  `tag,verdict,rc,nodes,secs`; `docs/OPERATIONS.md` documents
  `tag,verdict,rc,nodes,secs,records`. The doc matches neither
  implementation.

### 5.4 Provenance / trial ledgers

| name | shape | authority |
|---|---|---|
| **`LEDGER-A0-PROVENANCE`** | TSV+header, 25 cols (`stage,ts,idx,shard,control,group,word_path,lane,epsilon,seed,time_limit,max_nodes,verdict,reading,seconds,inst_sha256,anchor_bytecheck,sol_rows,validated,length,identical_to_source,sub5906,validator,word_file,result_line`); append-per-cell | `analysis/counting/s62/a0gate.py` — `LEDGER_COLS` **named constant** |
| *(sibling)* **`LEDGER-A0-STATS`** | TSV+header, a **different** 25 cols | same file — `STAT_COLS`. Must not be conflated with the above |
| **`LEDGER-GRADIENT-TRIALS`** | TSV+header, 19 cols: `stage,control,group,R,noise,pool,mult,cols,rows,lane,epsilon,seed,time_limit,verdict,seconds,nodes,attempts,maxdepth,result_line` | `out/s59/cliff/run_gradient.py`; instance `out/s59/cliff/trials.tsv` |
| **`LEDGER-QSB-TRIALS`** | TSV+header, 16 cols | `out/s59/cliff/qsb.py`; instance `out/s59/cliff/qsb_trials.tsv` |

`LEDGER-A0-PROVENANCE` is designed to **join onto**
`LEDGER-GRADIENT-TRIALS` via `stage` — they share
`stage,lane,epsilon,seed,time_limit,verdict,seconds` and agree on nothing
else. That is the only intentional cross-ledger join in the repo.
`word_path` is confined to the A0 provenance TSV on purpose, so the
supervisor's alarm regex (§4 clause 7) never scans it.

### 5.5 JSONL ledgers

| name | shape | authority |
|---|---|---|
| **`LEDGER-PREFIX-JSONL`** | JSONL, 11 fields, `event` always `"PREFIX"`: `event,spec,m,mode,depth,verdict,raw,seconds,res_rows,tried,elapsed` | `out/s59/prefix/prefix_propose.py`; 22 files under `out/s59/prefix/` |
| **`LEDGER-PREFIX-CELL`** | JSONL, 20 fields, one line per gate cell | `out/s59/prefix/gate2.py`; `gate2_m{20,25,30}.jsonl` |

`LEDGER-PREFIX-CELL`'s last field, `ledger`, is a **string holding the path
of the corresponding `LEDGER-PREFIX-JSONL` file** — the only cross-shape
pointer in the repo, and easy to misread as a nested record. Readers of
`LEDGER-PREFIX-JSONL` must tolerate blank lines and zero-byte files (both
occur in the committed-adjacent set).

Also named but not a data shape: `out/s60/nogood/LEDGER.txt` is a
**hand-written prose command ledger** (fixed-width `step | command | wall s
| cores` plus budget accounting and instance sha256s). No generator, no
delimiter, cited as a deliverable by that session's REPORT.

### 5.6 Rules for the twenty-first ledger

1. **Name the shape.** Add it to this section with its authority *before*
   the first file is written.
2. **The column list is a named constant in exactly one place.** Four of
   the twenty manage this (`satworker.HEADER`, `flsuper.$HEADER`,
   `a0gate.LEDGER_COLS/STAT_COLS`); the four-way duplication of
   `FARM-SHARD-EVENT`'s columns (`untargeted_run.ps1`, `pysweep_run.ps1`,
   `promote_run.ps1`, and again as a banner in `untargeted_status.ps1`) is
   what the rule exists to prevent.
3. **Header or headerless is a decision, not a default** — and per *shape*,
   not per file. `FARM-LKH-CONFIGSEED` currently has both (aggregate files
   with a header, per-worker shards without).
4. **Append-only vs rewritten-wholesale must be stated**, because it
   determines what a killed worker leaves behind (`FARM-SHARD-EVENT` is
   append-only; its sibling `FARM-TABLE` is not).
5. **No sentinel rows.** `CENSUS-DLX-SWEEP`'s `SWEEP COMPLETE …` line is
   the standing counter-example. Completion belongs in a separate marker
   file, or in a STATUS `DONE` row (§4 clause 5).
6. **If a shape has no generator, say so in this file** and treat the
   committed instance as the authority (`CENSUS-SCOPED`).

---

## Appendix: what is NOT a contract

- **Session REPORT numbers** (`out/sNN/*/REPORT.md`) are frozen prose about
  a run, not a schema.
- **`out/sNN/` file layout** is frozen history. Nothing may depend on its
  shape going forward; the code that used to live there was promoted into
  `pylib/` in s64 P1 (`pylib/README.md`).
- **`--help` text** is not a contract, but it *is* pinned
  (`out/s64/refactor/pins_before/help_*.txt`) precisely so that refactors
  cannot change it by accident. Changing it deliberately means re-pinning.
</content>
