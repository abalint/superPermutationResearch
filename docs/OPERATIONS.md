# Operations — how long-running compute is launched, monitored, and killed

Applies to every sweep, training run, or agent task expected to exceed ~30 min,
on the Mac or the PC farm. Complements `analysis/trackc/WORKFLOW-V2.md` (Track C
pipeline stages) and `analysis/cover7/REMOTE-FARM.md` (farm safety rules).

## Pre-launch rule (non-negotiable)

Before launching anything > ~30 min, the operator (human or AI session) states:
1. **What** is being launched and why (which gate/stage it serves).
2. **Expected runtime** with the arithmetic (jobs × cap ÷ workers), and the
   bounded worst case (sum of time-limit caps).
3. **What it produces** and where it lands.
4. **The abort command.**

AI sessions: tell Andrew and get a go-ahead first. No fire-and-forget.

## Heartbeat convention (ships WITH the launch, not after)

Every run family maintains, in its run directory:
- `STATUS.txt` — overwritten at every stage boundary and after every job:
  current stage, done/total, last job's tag+verdict+nodes+secs, timestamp.
- `ledger.csv` — one append-only row per completed job:
  `tag,verdict,rc,nodes,secs,records`.
- Workers must never slurp whole logs for bookkeeping — use file sizes /
  line-count streaming. (Lesson: sweep-1's `@(Get-Content $jl).Count` on 20
  workers OOM-wedged the farm PC on 2026-07-28 — CLR 80004005, no process
  creation, manual reboot required.)

Current locations:
- Mac Track C runs: `analysis/trackc/runs/v2/genlocal/{STATUS.txt,ledger.csv}`
- Farm sweep-1: `F:\superpermFarm\trackc2\{ledger.csv,done\,logs\}`
- Farm gen2: `F:\superpermFarm\trackc2\{ledger2.csv,done2\,gen2\}`

## Monitoring

- A session-level Monitor watches the active STATUS.txt: emits stage changes,
  progress milestones, and a STALL WARNING if the heartbeat goes >35 min quiet.
- Check by hand any time:
  `cat analysis/trackc/runs/v2/genlocal/STATUS.txt`
  `ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\trackc2\tc2status.ps1"` (sweep-1; `tc2status2.ps1` for gen2)
- Farm status blackout ≠ farm working: if F:-touching commands hang >2 min but
  `cmd /c echo alive` is instant, suspect the box (memory pressure), not the
  network. Verify with `tasklist` (C:-only) before assuming progress.

## Abort commands

- Mac Track C runs: `pkill -f dlx7g` (engines only; agent tasks via TaskStop).
- Farm sweep-1: `tc2stop.ps1`; gen2: `tc2stop2.ps1` — both kill only their own
  recorded PIDs. NEVER kill python on the PC (transcription service).

## Runtime estimation cheat sheet (measured s19)

- dlx7g blind: ~300–450k nodes/s (Mac and PC comparable); probe/feature
  overhead 1.4–1.6×.
- Known tree sizes: eval chains 5/25/26/73/74/76 = 60M/200M/8.5M/23M/1.4M/12M
  nodes; open n=7 chains: ~230M nodes per 600 s (never exhaust at this budget).
- Farm waves: jobs ÷ 20 workers × cap = wall time (162 × 600 s ÷ 20 ≈ 81 min).
- 600 s open-chain run ≈ 1.1M subtree records ≈ 215 MB JSONL — mine/sample on
  the PC, never scp raw sweeps.

## tail-atsp farm harness (added 2026-07-29, s29-ops)

24-way sharded corpus sweeps of `tail-atsp` on the PC. Everything lives under
`F:\superpermFarm\tailatsp\`; scripts are committed in `analysis/farm/ta*`.

**Why:** the instrument is single-threaded and the corpus is embarrassingly
parallel — 24 cores turn a ~12 h single-core anchor-450 sweep into ~36 min,
leaving 4 cores for the transcription service (workers also run at
BELOW_NORMAL via `detach.exe`).

**Layout.** `superperm.exe` (cross-compiled, see below) · `shards\s00..s23`
(the 22,062-walk corpus, round-robin split so heavy-tail instances spread
evenly — 919–920 walks each) · `runs\<tag>\{SPEC.txt,STATUS.txt,ledger.csv,
logs\wNN.log,pids\wNN.txt,finds\wNN\,ALARM.txt}`.

**Build + ship (the PC has no Rust toolchain).** From the repo root on the Mac:
```bash
rustup target add x86_64-pc-windows-gnu     # once; needs mingw-w64 (brew)
CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER=x86_64-w64-mingw32-gcc \
  RUSTFLAGS="-C target-feature=+crt-static" \
  cargo build --release --target x86_64-pc-windows-gnu
COPYFILE_DISABLE=1 scp target/x86_64-pc-windows-gnu/release/superperm.exe \
  analysis/farm/ta*.ps1 analysis/farm/tasuper.bat transcribe:/F:/superpermFarm/tailatsp/
```
`crt-static` leaves only system DLL imports, so nothing else needs installing.
**Always set `COPYFILE_DISABLE=1`** when tarring/scp'ing corpus data from macOS
— bsdtar silently ships an AppleDouble `._x` twin per file (and hides them from
`tar -t`), which doubled the shard tree on first transfer and would have been
parsed as corpus records.

**Launch / status / abort** (all `powershell -NoProfile -ExecutionPolicy Bypass -File`):
```
F:\superpermFarm\tailatsp\talaunch.ps1 -Anchor 450 -MaxBlocks 50 -Workers 24 -Tag a450b50
F:\superpermFarm\tailatsp\tastatus.ps1 -Tag a450b50      # STATUS + ledger + alarm + live procs
F:\superpermFarm\tailatsp\tastop.ps1   -Tag a450b50      # abort (add -All to sweep up orphans)
```
`-Limit K` runs K walks per shard — always probe first (`-Tag probeXXX -Limit 40`)
and quote the measured rate ×1.5.

**Mode switches** (each maps to the `tail-atsp` flag of the same name, and each
is recorded in the run's SPEC.txt):

| switch | flag | what the supervisor tracks |
|---|---|---|
| `-Ties -TieCap N` | `--ties --tie-cap N` | `ties` = equal-cost orders landing in a DIFFERENT allocation |
| `-Merge` | `--merge` | `merge_moves/merge_improved/merge_equal` + `MERGE-ALLOCS.txt` |
| `-Recomp` | `--recomp` | `rc_moves/rc_improved/rc_eq_new/rc_eq_same` + `RECOMP-ALLOCS.txt` |

Ledger columns are `worker,shard,rc,verdict,walks,optimal,improved,skipped,
ties,merge_moves,merge_improved,merge_equal,rc_moves,rc_improved,rc_eq_new,
rc_eq_same,secs,finished` — fixed for the life of a run file. `rc` is always
empty: `detach.exe` discards exit codes, so an improvement is detected from the
worker's own banner/summary instead (see the alarm path below). A new mode
needs its switch in `talaunch.ps1`, its summary regex in `tasuper.ps1`, and its
counters in `tabrief.ps1`/`ta_watch.sh` — `--recomp2` (s38) is NOT wired yet.

**Progress is completed walks, not log lines.** Modes differ in how much they
print (`--recomp` emits ~3 lines per walk because it writes 2 sampled equals),
so `tasuper.ps1` counts lines ending in `block-order-optimal`. Anything that
changes that per-walk line must keep the counter honest, or long-run ETAs go
silently wrong (this bit a 5 h run before it was caught; results were never
affected, since every reported number comes from the ledger).

**A src change invalidates the shipped binary.** `superperm.exe` on the PC is
whatever was last cross-compiled; `BUILD.txt` beside it records the commit. Check
it against `git rev-parse --short HEAD` before any farm run, and reship if they
differ (s31 and s38 both changed `src/tailatsp.rs`).

**Heartbeat.** `talaunch.ps1` starts `tasuper.ps1` detached; it rewrites
`STATUS.txt` every 30 s (stage, alive workers, walks/total, rate, ETA,
improvements, per-worker memory) and appends one `ledger.csv` row per finished
worker. Session-side watch: `analysis/farm/ta_watch.sh <tag> [interval]` polls
`tabrief.ps1` and emits only alarms, deciles, crashes, stalls, unreachability.
Line counting is a streaming `StreamReader` — never `@(Get-Content …).Count`
(that is what OOM-wedged the box in s19).

**Safety properties built in.** `talaunch.ps1` refuses to start if any
`superperm.exe` is alive or the run dir exists (the s28 duplicate-launch trap);
pid files record name + start time and `tastop.ps1` refuses to kill a pid whose
process name is no longer `superperm` (the s19 PID-recycling trap); python is
never touched.

**Alarm path.** A worker finding `optimum < actual` prints
`*** IMPROVEMENT ***`, materializes + validates the walk into `finds\wNN\`, and
exits 2. Exit codes are lost through `detach.exe`, so the supervisor detects it
from the summary line instead and writes `ALARM.txt` + flags STATUS. Then:
`validate -n 6 --file <f> --complete` AND `python3 analysis/counting/m3_check.py <f>`
(exit 2 = novel) before anything is believed — see `docs/OPS-BACKGROUND-AGENT.md`.

## Farm lessons appended post-recovery (s19 late)

- **PID files do not survive a reboot**: Windows recycles PIDs; 5 of 96 stale
  pid files resolved to unrelated live processes after the s19 reboot. Any
  stop-script must verify process NAME (and ideally start time) before
  killing, and recovery must delete all pid files first.
- `tasklist`/WMI/systeminfo are Access-denied for the farm account — use
  PowerShell `Get-Process`.
- **Detached stdout is lost** (`detach.exe → cmd → redirect` yields 0-byte
  logs for python): long-running PC-side scripts must write their own
  progress/summary files (see `mine2.progress` pattern), never rely on
  stdout redirection.
- Ledger column semantics must never change mid-file (sweep-1 col 8 is line
  count in pre-fix rows, MB in post-fix rows — dedupe by last-row-per-jid and
  do not aggregate col 8 across the boundary).
