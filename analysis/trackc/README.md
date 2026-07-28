# Track C — guided DLX engine

Spec: `docs/TRACKC-DESIGN.md` (§2 feature vector is LOCKED, §5 engine).
`dlx7g.c` is a descendant of `analysis/farm/dlx7_win.c`: same rooted exact-cover
problem, same forest machinery, same exit codes.

## Build

```bash
cd analysis/trackc && make          # cc -O2 -Wall -Wextra -o dlx7g dlx7g.c -lm
make gates                          # parity diff + n=6 baseline end-to-end
```

Single file, portable C99, no deps beyond libm. Builds warning-free on macOS.

## Instance format

```
ncols nrows nloops nchild        # nchild = n-2 (4 at n=6, 5 at n=7)
loop_id parent_code c0 .. c{nchild-1}     x nrows
```
`parent_code = -1` when the row's parent orbit is a kernel root, else the column
index of that orbit. **Row id = line order, 0-based** — the same convention as
`analysis/cover7/solve_dlx.py`'s exporter and `data/trackc/instances/*.txt`.
`nchild` is read from the header; nothing is hardcoded to 5.

## CLI

```
dlx7g <instance.txt> [--weights f] [--epsilon p] [--seed s]
      [--time-limit sec] [--max-nodes N] [--dump-features f]
      [--out f] [--first-only] [--progress-nodes N]
```

* `--weights f` — linear scorer, file format
  ```
  trackc-w1 8
  w1 w2 w3 w4 w5 w6 w7 w8 bias
  ```
  At each node, after the MRV column choice, the 8 features (§2 order) are
  computed for every active candidate row; rows are tried in **descending
  score, ties by ascending row id**. Without `--weights` the candidate order is
  plain ascending row id (the deterministic baseline).
* `--epsilon p --seed s` — with probability `p` per node the candidate order is
  a seeded shuffle instead of the scored/baseline order (deterministic given
  the seed). `p > 0` also re-enables the node-cap restart machinery (cap starts
  at 2e6 and doubles); with `p == 0` the search is a single deterministic pass,
  so restarting would be a no-op.
* `--dump-features f` — teacher-forced replay. `f` lists the row ids of a known
  cover, one per line. No search: at each node the MRV column is chosen, one
  block is printed, then the cover row covering that column is placed.
  ```
  NODE <k> col=<c>
  <rowid> <f1> ... <f8>        # %.6f, candidates ascending by row id
  ```
  `k` is 0-based. Output goes to `--out` or stdout.
* `--out f` — solution row ids (one per line) go here instead of stdout.
* `--time-limit`, `--max-nodes` — budgets (`--max-nodes` is a grand total).
* `--first-only` — accepted for interface stability; the search always returns
  the first solution.
* Progress to stderr every `--progress-nodes` (default 5,000,000) nodes or 10 s:
  `[progress] nodes=… total=… depth=… maxdepth=… elapsed=…`. The max depth ever
  reached is repeated on the final `RESULT …` line.

Exit codes: **0** solution, **2** exhausted (no rooted cover), **3** timeout /
node cap, 1 usage or setup error.

### Feature timing (load-bearing, matches the Python extractor)

All 8 features are evaluated on the DLX state **before `cover(c)` is applied**:
candidates are enumerated from the still-active column and `size[]` still counts
every candidate of `c`. `dlx7_win.c` collected candidates *after* `cover(c)`;
that pattern is deliberately not used here. `data/trackc/parity/parity_py.txt`
is the pre-cover reference (`parity_py_postcover.txt` is diagnostic only).

`static_min_child_log` (feature 7) uses the *initial* column sizes computed once
at instance load. `grounded[]` / `pending[]` are maintained on the same undo
trail as the forest state, with recursive groundedness propagation when a
grounding row is placed and full revert on backtrack.

## Driver

```bash
python3 solve_guided.py n6std --time-limit 300 --outdir out
python3 solve_guided.py n7std --weights ../../ml/models/trackc_A.txt --time-limit 3600
python3 solve_guided.py --chains ../cover7/chains_V15_s14.jsonl --index 0 --time-limit 3600
```

`solve_guided.py` rebuilds the Python instance (from the `.meta.json` `source`
field, or from an explicit chain), **re-exports it and refuses to run unless the
text matches the on-disk instance file** — a row-id mis-mapping can never be
silent. On a solution it runs `gain1.check_cover`, compiles
(`chain7.compile_chain_cover` at n=7, `gain1.assemble_certificate` +
`certificate.compile_certificate` at n=6) and then runs

```
cargo run --release -- validate -n <n> --file <word> --complete
```

from the repo root. **Success is only reported when the Rust validator passes.**
`PYTHONPATH` is set up internally (adds `extraDocs/superpermutation-examples/
scripts` and `analysis/cover7`).

Instance sources it can rebuild: `gain1.build_instance(N)`,
`chain7.standard_chain()`, and `<chains>.jsonl K=<k> entry <i>`. Instances whose
meta `source` is a bare `cert5906_*.json` path are not auto-rebuildable — pass
the chain explicitly with `--chains/--index`.

## Gate results (2026-07-27, macOS, cc -O2)

| gate | result |
|---|---|
| build | clean, `-Wall -Wextra`, no warnings |
| n=6 baseline (no weights) | SOLVED 25 rows, 21,627 nodes, 0.008 s, exit 0; `check_cover` valid |
| n=6 end-to-end | compiles to an 872 word; Rust `validate --complete` passes |
| parity `--dump-features` | 25 NODE blocks, **byte-identical** to `parity_py.txt` |
| zero weights | 25 rows, 21,627 nodes (ties ⇒ ascending row id ⇒ same as baseline) |
| non-trivial weights | 25 rows, 3,210 nodes |
| determinism | two identical invocations: 21,627 nodes both (ε=0.2 seed 7: 3,619 both) |
| nchild=5 | n7std (690×4440) `--dump-features` on a 5907 cert: 138 NODE blocks |
