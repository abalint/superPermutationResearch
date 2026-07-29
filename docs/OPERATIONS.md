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
