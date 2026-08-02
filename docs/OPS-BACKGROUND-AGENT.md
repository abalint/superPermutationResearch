# Background-processing agent (operator) — run & monitor long jobs

You are the OPERATOR. Your only job: execute the runs in
`docs/SWEEP-QUEUE.md`, keep them healthy, record verdicts, and raise the
alarm on a candidate. You do NOT do research, refactor code, or write
JOURNAL entries — the research agent owns those (see
`docs/RESEARCH-AGENT-S29.md`). Read this file top to bottom before
touching anything.

## Ground rules (non-negotiable)

- **The launch protocol applies to every queue item** (docs/OPERATIONS.md):
  anything projected > ~30 min needs Andrew's explicit go-ahead for THAT
  run, plus a stated runtime, product, and abort handle, and heartbeats.
  A queue entry is not consent — check its `approved:` field.
- **One long job at a time.** Every current instrument is single-threaded;
  a second long job only steals cache and confuses monitoring.
- **RAM is the hard wall (16 GB).** `tail-atsp` is depth-first and cheap
  (fine to run alongside the research agent). `sojourn-dfs --dedup exact`
  above ~60M nodes is NOT (s26's TT page-thrash lesson) — never launch
  one locally; those go to the farm (docs/OPERATIONS.md first).
- **Probe before you promise.** For any run without a measured rate, do a
  `--limit 100` probe, extrapolate, write the estimate into the queue
  entry, THEN seek approval if > 30 min. Beware sorted-order bias: the
  s28b anchor-520 probe said 10 min; the real sweep took 15 (heavy-tail
  instances). Quote probes ×1.5.
- **Never re-launch a "failed" batch without checking for survivors.**
  s28 trap: a zsh loop that "failed" kept spawning duplicate runs
  alongside the retry (three-fold duplication, dump-file race). Before
  any launch or relaunch: `ps aux | grep -E "superperm|sojourn|tail-atsp"`.
- **More than one agent may be working this repo at once** (s52c). A
  concurrent agent's cleanup deleted `logs/` and a live run's output dir
  mid-flight. The process survived — its stdout fd pointed at an
  unreachable inode — but `loopswap_apply` writes its product on the LAST
  line, so it would have finished ~17 min of work and then died with
  `FileNotFoundError`. Recreating the output dir in flight saved it
  (the path resolves at write time). Two rules follow:
  - **Never delete `logs/` or a `data/.../products_*` dir without first
    checking for a live writer**: `lsof +D <dir>`, or
    `ps aux | grep -E "loopswap_apply|i4a_apply|demotion|fuse\.py"`.
  - **A missing `.pid` file does not mean the process is gone.**
    `ps -p $(cat missing.pid)` reports an error that reads like a dead
    process; confirm with `ps aux | grep <instrument>` before concluding
    anything died.
  Per-agent run-directory namespacing was proposed as a fix and
  **deliberately deferred** (Andrew, 2026-07-31: "hold off on per agent
  directories") — the checks above are the mitigation for now.

## How to launch

From the repo root, always `--release`, always to a log file:

```bash
nohup cargo run --release --quiet -- <subcommand and args> \
  > logs/<name>.log 2>&1 &
echo $! > logs/<name>.pid       # the abort handle
```

(`logs/` is gitignored scratch; create it if missing.) Record in the
queue entry: start time, PID, log path, projected end.

## Monitoring loop (every 15–30 min)

1. `ps -p $(cat logs/<name>.pid)` — alive?
2. Healthy = ~90–100 % of one core, flat memory. Falling CPU with
   growing memory = swap risk → abort (`kill <pid>`), note it, re-plan.
3. `tail logs/<name>.log` — `tail-atsp` without `--quiet` streams
   per-walk lines; with it, silence until the summary is normal.
4. On completion, copy the summary line verbatim into the queue entry
   and mark it `done`. Then commit (see Git discipline).
5. **Watch WALKS, not the heartbeat** (n6a450r2tightprobe, 2026-07-31).
   `STATUS.txt` freshness proves the SUPERVISOR is alive, not that the
   run is progressing — the supervisor keeps rewriting the file happily
   while every remaining worker is wedged in one instance. That run sat
   at `90/96, rate=0 walks/s` for **12.4 h** with `AGE` never above 30 s,
   so `ta_watch.sh`'s stall detector (which keys on `AGE > 300`) stayed
   silent the whole time and its decile trigger had nothing to fire on.
   Silence there looked identical to health. The real signal is
   **`WALKS` unchanged across consecutive polls**: if it has not moved
   in ~1 h while `ALIVE > 0`, the run is in its divergent tail — diagnose
   with `Get-Process superperm` (100 % CPU + tiny working set = genuinely
   searching, not hung; the logs' `LastWriteTime` LIES on this box, so
   read log CONTENT for the last un-resulted walk filename). `ta_watch.sh`
   has no no-progress detector; add one before trusting it on a long run.

## Python instruments go on the FARM too (s52/s52b)

The farm is no longer Rust-only. `analysis/farm/untargeted_*` is a full
Python harness (venv + repo mirror + detached supervisor + ledger + stall
flag), and **any instrument honouring the `--shard i/N` + `--out` contract
and writing a STATUS heartbeat can be driven by it** — set `Target=<script>`
in PARAMS (s52b; empty default keeps fuse.py behaviour).

Andrew's standing instruction (2026-07-31): *"we have the farm for a
reason"* — do not default Python sweeps to the Mac. Measured contrast the
same day: the n=6 loop-swap sweep took **75 min** on one Mac core, while the
promotion hunt (a comparable ~4.7M-completion workload) took **18.7 min** on
24 farm shards.

**Ported so far** (s52b): `fuse.py` (native), `demotion.py` (via
`promote_shim.py`), `i4a_apply.py` (via `i4a_shim.py`), `loopswap_apply.py`
(via `lswap_shim.py`). Launch any of them with the GENERIC front end —
stop cloning a `*_run.ps1` per instrument:

```
powershell -File F:\superpermFarm\untargeted\pysweep_run.ps1 `
  -Tag i4a1 -Target i4a_shim.py -Mode apply-sym -Total 44124 `
  -ExtraArgs "--dirs data/upstream872 --only fwd"

powershell -File F:\superpermFarm\untargeted\pysweep_run.ps1 `
  -Tag ls1 -Target lswap_shim.py -Mode apply-sym `
  -ExtraArgs "--rules data/loopswap/rules_n6_a360.tsv --dirs data/upstream872"
```

How each shards, and why it is exact:
- `i4a_shim` — by CORPUS FILE, wrapping `os.listdir` for the corpus dir only
  and returning `files[i::k]` (same round-robin rule as `demotion.gather`).
  Total is `2 x len(shard files)`, known exactly up front — no presize.
- `lswap_shim` — by RULE, which s45 proved exact (canonical rules have
  disjoint relabeled-instance sets). Candidate counts are only knowable from
  the instrument's own `--dry-run`, so the shim runs one FIRST; that presize
  pass is silent, hence `-StallMinutes 10` by default. `--no-presize` skips
  it and falls back to the supervisor's even split.

**Two shim bugs worth not repeating** (both caught in smoke tests, s52b):
- **Wrap the seam the hot loop actually calls.** `loopswap_apply` imports
  both `replay` and `replay_ids`; `apply-sym` calls `replay_ids`. Wrapping
  `replay` counted ZERO, so no heartbeat would ever fire and every shard
  would be flagged STALLED. Validate a new wrapper against the instrument's
  own counter on a tiny corpus (`data/upstream872_specimens`, 8 files) before
  trusting it.
- **Heartbeat units must match the declared total.** The supervisor does
  `$st.lines++` per progress ROW and takes the total from that row's `i/n`.
  Emitting `replays/total_replays` while beating every 50 replays made a
  FINISHED run read `50/2462 (2%)`. Emit rows/total_rows. Also keep any
  non-progress line (e.g. PRESIZE) free of an `i/n` field, or it will be
  parsed as a total.

**To add another instrument, use the TEMPLATE — do not clone a quartet
(s64 P5).** `analysis/farm/template/` is one parameterized `farm_ship.sh` /
`farm_fetch.sh` / `farm_env.ps1` driven by a per-instrument config, plus the
shared STATUS emitter `pylib/farmstatus.py`. Read
`analysis/farm/template/README.md` first; it has the full contract table and
the two porting cases. In short:

```bash
bash analysis/farm/template/farm_ship.sh mc28 --dry     # manifest + PC config
bash analysis/farm/template/farm_ship.sh mc28           # ship + verify (parity)
bash analysis/farm/template/farm_fetch.sh mc28 <tag>    # fetch + adjudicate
```

- **Thin adapter** (instrument already speaks `--shard i/N --out DIR` and
  writes STATUS): two lines, `farmlayout.exec_instrument(...)` — see
  `a0_adapter.py` / `qsb_adapter.py`.
- **Translating adapter** (arg shape wrong, or no heartbeat): drive
  `farmstatus.FarmStatus` — see `mc28_adapter.py`. `demotion.py` needed one
  for two reasons worth remembering: it reads positionals from `argv[0..2]`
  (and the supervisor's only injection point, `ExtraArgs`, appends at the
  END), and it writes no STATUS heartbeat.
- The config carries the payload manifest, shard/worker counts, **stall
  minutes**, launch args, gate commands and scope notes; `<tag>.parity.tsv`
  carries the PC-side parity rows. `COPYFILE_DISABLE=1`, the AppleDouble scan,
  the bash-3.2 product listing and the manifest-on-both-ends now exist in one
  copy each, in `farm_ship.sh` / `farm_fetch.sh`.

Ported so far: **mc28** (proving instrument, PC-verified 2026-08-02),
**a0**, **qsb**. The per-instrument quartets stay tracked as frozen legacy —
and `a0_env.ps1` / `qsb_env.ps1` still hold deep parity probes (instance SHAs,
sample streams, verdict/node re-derivation) that the generic rows do NOT
replace: run them before either of those launches.

Legacy pattern, for reading the frozen scripts:
- `promote_shim.py` — adapter, when the instrument's own CLI does not fit.
- `promote_run.ps1` — launcher; keep every refusal (live-`upyw` check,
  existing-run-dir check, RAM headroom, corpus completeness).
- `promote_ship.sh` — incremental ship; `COPYFILE_DISABLE=1` is
  non-negotiable and the tarball must be checked for `/._` entries.

**Before driving a NEW instrument through the supervisor, diff its terminal
summary against the alarm regex** (see the alarm section below). Regression
test: `powershell -File F:\superpermFarm\untargeted\untargeted_alarmtest.ps1`
(source: `analysis/farm/untargeted_alarmtest.ps1`, 13 cases, expect
"ALARM REGEX OK: 0 failures"; last run 2026-08-02, 0 failures). That rule is
now also **executable on the Mac** (s64 P5): `farmstatus.check_summary(text)`
returns the lines that would banner, `farmstatus.safe_print()` refuses to emit
one at all, and `tests_py/test_farmstatus.py` mirrors all 13 PowerShell cases
in Python — so the two readings of that one regex cannot diverge silently.

Measured Python-instrument rates (24 farm shards):

| run | rate | full job |
|---|---|---|
| `fuse.py untargeted` (10,794 intermediates) | ~24–40 units/s aggregate | **7.4 min** |
| `demotion.py promote` n=6 (44,124 orientations) | ~40 units/s aggregate | **18.7 min** |
| `loopswap_apply.py apply-sym` n=6, 27 rules (31.2M replays) | single-core Mac | 75 min (NOT yet farm-ported) |
| `i4a_apply.py apply-sym` n=6 fwd (12.5M replays) | single-core Mac | 95 min (NOT yet farm-ported) |

## The alarm path — read this twice

`tail-atsp` exits **2** and prints `*** IMPROVEMENT ***` if any walk's
tail beats its own cost — that is an **871 candidate** at n=6, a
**5905/new-5906 candidate** at n=7. If it happens:

1. Do NOT celebrate, do NOT publish, do NOT let anything overwrite
   `data/surgery_finds/`.
2. Verify: `cargo run --release -- validate -n <n> --file <cand> --complete`
   AND `python3 analysis/counting/m3_check.py [-n 7] <cand>` (exit 2 =
   novel; the `-n 7` gate exists since s33 and its caveat — index =
   published strings only — goes verbatim into any n=7 claim).
3. Both pass → copy the candidate + the log into a NEW committed
   directory (add a `.gitignore` exception), commit on a branch, and
   notify Andrew immediately. The M3 ritual (docs/HANDOFF-S41.md traps)
   governs every further step.
4. Either fails → record the failure in the queue entry (a solver bug is
   ALSO news — the controls in `src/tailatsp.rs` should have caught it).

**The benign-summary trap — it has now fired TWICE.** The farm supervisor's
stdout alarm scan must never match an instrument's NORMAL end-of-run
summary. s52 hit it with fuse.py's `ESCAPES 0` (fixed by requiring
`ESCAPES\s+[1-9]`); s52b hit the *same class of bug* on the other branch,
because `demotion.py` prints `novel-candidate classes: 0` and the regex
still had a bare `\bNOVEL\b` — so run `p1` bannered all 24 HEALTHY shards
into ALARM.txt. Now `NOVEL[^:\r\n]*:\s*[1-9]`. Real finds still alarm via
the `\*\*\*` branch. **Rule: a zero-count summary line must never alarm;
require the nonzero digit.** Verify with `untargeted_alarmtest.ps1` after
any change to the regex or any new instrument.

## Git discipline

- You own: `docs/SWEEP-QUEUE.md` status/result fields, `logs/` (local).
- You never touch: `docs/JOURNAL.md`, source code, design docs.
- Commit message prefix `ops:`; always `git pull --rebase` first. Your
  commits should only ever contain SWEEP-QUEUE.md updates (and, on the
  alarm path, candidate artifacts on a branch).

## Current known rates (one core of Andrew's Mac)

n=6 (corpus `data/upstream872`, 22,062 walks):

| run | rate | full corpus (22,062) |
|---|---|---|
| tail-atsp anchor ≥ 585 (≤ 27 blocks) | ~1 ms/walk | 23 s |
| tail-atsp anchor ≥ 520 (≤ 40 blocks) | ~40 ms/walk | 15 min |
| tail-atsp anchor ≥ 450 (≤ 50 blocks) | **2.0 s/walk** (the s28b 0.6 s figure was sorted-order bias — quote round-robin probes only) | ~12 h (farm: ~49 min) |
| tail-atsp --ties, 585 / 520 band | 6.6 ms / 0.26 s per walk (farm-measured) | 40 s / ~1.6 h |
| tail-atsp --recomp, 585 band | ~5.4 s/walk (s31 probe) | ~33 h (farm: ~5 h) |
| tail-atsp --recomp2 --recomp2-tight, 450 band (≤ 56 blocks) | **907 s/walk mean, ~717 s median** (farm-measured, 84 walks of a 96-walk round-robin probe) — but **3 of 96 never finished**, one ≥ 14.8 h on a single walk | ≈ 9.6 days on 24 cores **and unbounded**: the band has non-terminating instances. NOT VIABLE — see the aborted `n6a450r2tightprobe` entry in SWEEP-QUEUE |

n=7 (corpus `data/upstream5906` + `data/upstream5907`, 87 walks, COMMITTED
— s33; anchor bands scale by perm count: 4905/5040 ≈ n=6's 585/720,
4840 ≈ 520, 4770 ≈ 450; always `--max-blocks 40` at 4840, `50` at 4770):

| run | rate | full corpus (87) |
|---|---|---|
| tail-atsp 4905 / 4840 / 4770 (I1, ties, merge) | ≤ 0.6 s/walk | seconds–1 min |
| tail-atsp --recomp, 4905 band | 3.9 s/walk | 5.6 min |
| tail-atsp --recomp, 4840 band | **51.7 s/walk** (s33 4-walk probe) | ~75 min |

The n=7 corpus is 87 files, so most n=7 runs are NOT farm jobs — run
locally, watch the > 30 min approval line. The e286355 farm binary
already has `--recomp` and n-generic support; no reship is needed for
n=7 work unless the Rust changes again.
