# untargeted_super.ps1 -- heartbeat supervisor + bounded worker pool for the
# s49 fused-pair UNTARGETED sweep.  Launched DETACHED by untargeted_run.ps1
# (never run it by hand; it writes files, not stdout).
#
# Conventions it is required to honour (docs/OPERATIONS.md):
#  * STATUS.txt overwritten every tick; ledger.csv append-only, columns FIXED
#    for the life of the file (s19: ledger column semantics must never change
#    mid-file).
#  * NEVER slurp a log into an array.  `@(Get-Content $f).Count` on 20 workers
#    OOM-wedged this box on 2026-07-28.  Every read here is an incremental
#    StreamReader seek from a remembered byte offset, capped per tick.
#  * Process identity is (pid, name, start-time), never pid alone -- Windows
#    recycles PIDs (s19: 5 of 96 stale pid files pointed at live strangers).
#    Our shards run as `upyw.exe`, a renamed copy of the venv interpreter, so
#    they can never be confused with the user's transcription `python.exe`.
#  * Detached stdout is only trustworthy when detach.exe's own handles go
#    STRAIGHT to the child (no intermediate `cmd /c ... > file`, which is what
#    produced 0-byte python logs before) and the child is unbuffered: we launch
#    upyw.exe directly and always pass -u.
#  * A shard whose STATUS heartbeat has not advanced in -StallMinutes is
#    FLAGGED (ledger STALL row + STATUS banner), never silently ignored.
#
# It takes ONE argument, the tag.  Everything else comes from the run's
# PARAMS.txt (written by untargeted_run.ps1): quoting through
# ssh -> cmd -> detach -> cmd -> powershell mangles arguments, and detach.exe
# joins argv with single spaces, so no value that might contain a space is
# ever passed on a command line.
param([Parameter(Mandatory=$true)][string]$Tag)
$ErrorActionPreference = "Continue"

$ROOT   = "F:\superpermFarm\untargeted"
$REPO   = "$ROOT\repo"
$PY     = "$ROOT\pyenv\Scripts\upyw.exe"     # renamed venv python (identity guard)
$PNAME  = "upyw"
$FUSE   = "$REPO\analysis\counting\s49\fuse.py"
$DETACH = "F:\superpermFarm\detach.exe"
$run    = "$ROOT\runs\$Tag"
$t0     = Get-Date
$PID | Set-Content "$run\super.pid"

# --- run parameters (key=value, one per line; written by untargeted_run.ps1) --
$P = @{ Shards = 24; Workers = 24; Mode = "untargeted"; Limit = 0
        DryRunMode = 0; StallMinutes = 5; Total = 10786; ExtraArgs = ""
        TickSeconds = 30; Stub = 0 }
if (Test-Path "$run\PARAMS.txt") {
  foreach ($l in (Get-Content "$run\PARAMS.txt")) {
    if ($l -match '^\s*([A-Za-z]\w*)\s*=\s*(.*?)\s*$') { $P[$Matches[1]] = $Matches[2] }
  }
}
$Shards       = [int]$P.Shards
$Workers      = [int]$P.Workers
$Mode         = [string]$P.Mode
$Limit        = [int]$P.Limit
$DryRunMode   = ([int]$P.DryRunMode -ne 0)
$StallMinutes = [int]$P.StallMinutes
$Total        = [int]$P.Total
$ExtraArgs    = [string]$P.ExtraArgs
$TickSeconds  = [int]$P.TickSeconds
$Stub         = ([int]$P.Stub -ne 0)
# The stub exercises the supervisor's mechanics (ledger / STATUS / stall
# flagging / abort) without the instrument.  It takes the same --shard/--out
# contract and writes the same STATUS heartbeat.
$TARGET = if ($Stub) { "$ROOT\untargeted_stub.py" } else { $FUSE }

# ---------------------------------------------------------------- helpers ---
# Incremental line reader: seeks to a remembered offset and returns only the
# new lines (hard-capped).  O(new bytes) time, O(cap) memory -- the anti-OOM
# discipline the s19 wedge bought us.
$offsets = @{}
function Read-New([string]$p, [int]$retain = 2000) {
  # Always streams to EOF (so the byte offset is exact and no line is ever
  # missed) but RETAINS at most $retain lines -- memory is O($retain), never
  # O(file).  This is the s19 anti-OOM contract.
  $r = @{ Count = 0; Lines = @() }
  if (-not (Test-Path $p)) { return $r }
  $keep = New-Object System.Collections.ArrayList
  try {
    $fs = [System.IO.File]::Open($p, 'Open', 'Read', 'ReadWrite')
    $start = 0
    if ($offsets.ContainsKey($p)) { $start = [int64]$offsets[$p] }
    if ($start -gt $fs.Length) { $start = 0 }        # file truncated/rewritten
    [void]$fs.Seek($start, 'Begin')
    $sr = New-Object System.IO.StreamReader($fs)
    while ($null -ne ($line = $sr.ReadLine())) {
      $r.Count++
      if ($keep.Count -lt $retain) { [void]$keep.Add($line) }
    }
    $offsets[$p] = $fs.Length        # consumed to EOF
    $sr.Close(); $fs.Close()
  } catch { }
  $r.Lines = $keep.ToArray()
  return $r
}

# The instrument's per-shard heartbeat: one appended line per intermediate.
# Its exact filename belongs to the instrument, so match a family.
function Find-Status([string]$dir) {
  if (-not (Test-Path $dir)) { return $null }
  $f = Get-ChildItem $dir -Filter "STATUS*" -File -EA SilentlyContinue |
       Sort-Object Length -Descending | Select-Object -First 1
  if ($f) { return $f.FullName }
  return $null
}

function Tsv-Rows([string]$p) {          # data rows (header excluded), streamed
  if (-not (Test-Path $p)) { return 0 }
  $c = 0
  try {
    $fs = [System.IO.File]::Open($p, 'Open', 'Read', 'ReadWrite')
    $sr = New-Object System.IO.StreamReader($fs)
    while ($null -ne $sr.ReadLine()) { $c++ }
    $sr.Close(); $fs.Close()
  } catch { return $c }
  if ($c -gt 0) { $c-- }
  return $c
}

function Ledger([string]$shard, [string]$ev, $pid_, [string]$pstart, $lines, $secs, $rc, [string]$note) {
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),$shard,$ev,$pid_,$PNAME,$pstart,$lines,$secs,$rc,$note" |
    Add-Content "$run\ledger.csv"
}

function Alarm([string[]]$lines) {
  $lines + @("raised: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')", "") | Add-Content "$run\ALARM.txt"
}

# ------------------------------------------------------------- shard state --
$S = @{}
for ($i = 0; $i -lt $Shards; $i++) {
  $nn = "{0:d2}" -f $i
  $S[$nn] = @{
    idx = $i; state = "PENDING"; pid = 0; pstart = ""; proc = $null
    launched = $null; lines = 0; lastAdv = $null; total = 0
    stalled = $false; rc = ""; secs = 0; note = ""; escapes = 0; sawDone = $false; declTotal = 0
    outdir = "$run\out\s$nn"; log = "$run\logs\s$nn.log"; err = "$run\logs\s$nn.err"
  }
}

# ------------------------------------------------------------------ launch --
function Launch-Shard($st) {
  $nn = "{0:d2}" -f $st.idx
  New-Item -ItemType Directory -Force -Path $st.outdir | Out-Null
  # NOTE: detach.exe joins argv with single spaces -- no path here may contain
  # a space.  That is why everything lives under F:\superpermFarm\.
  $a = @("-u", $TARGET)
  if (-not $Stub) { $a += $Mode }
  $a += @("--shard", "$($st.idx)/$Shards", "--out", $st.outdir)
  if ($Limit -gt 0) { $a += @("--limit", "$Limit") }
  if ($DryRunMode)  { $a += @("--dry-run") }
  if ($ExtraArgs -ne "") { $a += ($ExtraArgs -split "\s+") }

  # workdir = the repo mirror: fuse.py resolves its own root from __file__, but
  # the s49 family also does relative `sys.path.insert(0,'analysis/counting')`.
  $res = & $DETACH $REPO $st.log $st.err $PY @a
  $wpid = 0
  if ("$res" -match 'pid\s+(\d+)') { $wpid = [int]$Matches[1] }
  if ($wpid -eq 0) {
    $st.state = "LAUNCHFAIL"; $st.note = "detach: $res"
    Ledger "s$nn" "LAUNCHFAIL" 0 "" 0 0 "" "$res"
    return
  }
  $p = Get-Process -Id $wpid -EA SilentlyContinue
  $ps = ""
  if ($p) {
    try { $ps = $p.StartTime.ToString("o") } catch { $ps = "" }
    # Touching .Handle makes the Process object OPEN and CACHE a real OS handle.
    # Without it, .ExitCode on a process we did not start throws and every
    # shard is later scored FAIL.  detach.exe cannot report exit codes itself
    # (docs/OPERATIONS.md), so this cached handle is the ONLY honest source.
    try { $null = $p.Handle } catch { }
  }
  $st.pid = $wpid; $st.pstart = $ps; $st.proc = $p
  $st.state = "RUNNING"; $st.launched = Get-Date; $st.lastAdv = Get-Date
  # pid + name + start time: identity, not just a number (s19 recycling trap).
  "$wpid`t$PNAME`t$ps`ts$nn" | Set-Content "$run\pids\s$nn.txt"
  Ledger "s$nn" "LAUNCH" $wpid $ps 0 0 "" "shard $($st.idx)/$Shards -> $($st.outdir)"
}

# Is the recorded process still OURS?  name AND start time must match.
function Still-Ours($st) {
  if ($st.pid -le 0) { return $false }
  $p = Get-Process -Id $st.pid -EA SilentlyContinue
  if (-not $p) { return $false }
  if ($p.ProcessName -ne $PNAME) { return $false }
  if ($st.pstart -ne "") {
    try { if ($p.StartTime.ToString("o") -ne $st.pstart) { return $false } } catch { }
  }
  return $true
}

# ------------------------------------------------------------------- loop ---
$aborted = $false
while ($true) {
  if (Test-Path "$run\ABORT") { $aborted = $true }

  # backfill the bounded pool
  $running = @($S.Values | Where-Object { $_.state -eq "RUNNING" }).Count
  if (-not $aborted) {
    foreach ($nn in ($S.Keys | Sort-Object)) {
      if ($running -ge $Workers) { break }
      if ($S[$nn].state -eq "PENDING") { Launch-Shard $S[$nn]; if ($S[$nn].state -eq "RUNNING") { $running++ }; Start-Sleep -Milliseconds 200 }
    }
  }

  $now = Get-Date
  $alive = 0; $doneLines = 0; $totalKnown = 0; $memSum = 0; $memMax = 0
  $edgeRows = 0; $statRows = 0; $stalledList = @(); $aliveList = @(); $escTotal = 0

  foreach ($nn in ($S.Keys | Sort-Object)) {
    $st = $S[$nn]
    if ($st.state -eq "PENDING") { continue }

    # --- progress: the instrument's own STATUS heartbeat, read incrementally
    $sf = Find-Status $st.outdir
    if ($sf) {
      $new = Read-New $sf
      if ($new.Count -gt 0) {
        $st.lastAdv = $now
        if ($st.stalled) {
          $st.stalled = $false
          Ledger "s$nn" "RESUME" $st.pid $st.pstart $st.lines ([int]($now - $st.launched).TotalSeconds) "" "heartbeat advanced again"
        }
        # As-built STATUS lines (fuse.py run_untargeted):
        #   <ts>\t<class>[<orient>]\t<i>/<n>\t...     one per intermediate
        #   <ts>\tESCAPE|MIDESCAPE|SHORTER\t<name>    the events we are hunting
        #   <ts>\tDONE\t<summary>                     terminal
        # The i/n field gives the shard's own total, which beats splitting the
        # corpus-wide projection evenly.
        foreach ($l in $new.Lines) {
          # Count ONLY the progress rows as intermediates: the terminal DONE row
          # (and any ESCAPE row) is a STATUS line too, so `$new.Count` overcounts
          # by one per shard and the tally reads 96/72 instead of 72/72.  These
          # must stay in the SAME units as declTotal or the percentage lies.
          if ($l -match "`t(\d+)/(\d+)`t") { $st.lines++; $st.declTotal = [int]$Matches[2] }
          if ($l -match "`t(MIDESCAPE|ESCAPE|SHORTER)`t") {
            $st.escapes++
            Alarm @("*** SHARD s$nn $($Matches[1]) ***", $l,
                    "out: $($st.outdir)",
                    "THIS IS THE EVENT THE SWEEP EXISTS TO FIND. Gate it before believing anything:",
                    "  cargo run --release -- validate -n 7 --file <f> --complete",
                    "  python3 analysis/counting/m3_check.py -n 7 <f>    (exit 2 = novel vs the 220)")
          }
          if ($l -match "`tDONE`t") { $st.sawDone = $true }
        }
      }
    }
    # The instrument's own declared total always wins.  Keeping it in a separate
    # field matters: a shard that had not yet written STATUS on the first tick
    # would otherwise be pinned to the fallback estimate forever.
    $st.total = if ($st.declTotal -gt 0) { $st.declTotal }
                else { [int][math]::Ceiling($Total / [double]$Shards) }
    $doneLines += $st.lines; $totalKnown += $st.total; $escTotal += $st.escapes

    # --- product counters (generic: whatever TSVs the instrument writes)
    if (Test-Path $st.outdir) {
      foreach ($f in (Get-ChildItem $st.outdir -Filter "*.tsv" -File -EA SilentlyContinue)) {
        if ($f.Name -match "(?i)edge")      { $edgeRows += (Tsv-Rows $f.FullName) }
        elseif ($f.Name -match "(?i)stat")  { $statRows += (Tsv-Rows $f.FullName) }
      }
    }

    # --- alarm scan on the new stdout only (escapes / novel classes)
    # Alarm scan on the new stdout only.  It must NOT match the instrument's
    # normal per-shard summary, which always contains the literal "ESCAPES 0"
    # -- an earlier version did, and bannered all 24 healthy shards.  Escapes
    # are counted precisely from the tagged STATUS rows above; this scan exists
    # for hard errors and for the instrument's own "!!  DEPTH-1 ESCAPE" banner.
    foreach ($l in (Read-New $st.log).Lines) {
      if ($l -match '(?i)Traceback|MemoryError|^\s*!!|\*\*\*|ESCAPES\s+[1-9]|\bNOVEL\b') {
        if ($l -match '(?i)Traceback|MemoryError') {
          Alarm @("*** SHARD s$nn ERROR ***", $l, "log: $($st.log)")
        } else {
          Alarm @("*** SHARD s$nn BANNER ***", $l,
                  "log: $($st.log)   out: $($st.outdir)",
                  "Gate before believing anything: cargo run --release -- validate -n 7 --file <f> --complete",
                  "AND python3 analysis/counting/m3_check.py -n 7 <f>  (exit 2 = novel).")
        }
      }
    }

    if ($st.state -ne "RUNNING") { continue }

    # --- liveness + identity
    if (Still-Ours $st) {
      $alive++; $aliveList += "s$nn"
      $p = $st.proc
      if ($p) { try { $p.Refresh(); $ws = [math]::Round($p.WorkingSet64/1MB); $memSum += $ws; if ($ws -gt $memMax) { $memMax = $ws } } catch { } }
      # --- stall detection: heartbeat frozen while the process is still alive
      if ($null -ne $st.lastAdv -and ($now - $st.lastAdv).TotalMinutes -ge $StallMinutes -and -not $st.stalled) {
        $st.stalled = $true; $stalledList += "s$nn"
        Ledger "s$nn" "STALL" $st.pid $st.pstart $st.lines ([int]($now - $st.launched).TotalSeconds) "" "no STATUS advance for $([int]($now - $st.lastAdv).TotalMinutes)m"
        Alarm @("*** SHARD s$nn STALLED ***",
                "no STATUS heartbeat advance for $([int]($now - $st.lastAdv).TotalMinutes) minutes (threshold $StallMinutes)",
                "pid $($st.pid) is still alive.  Inspect $($st.log) / $($st.outdir) before killing anything.")
      }
      if ($st.stalled) { $stalledList += "s$nn" }
    } else {
      # terminal.  detach.exe cannot report an exit code, but the supervisor
      # held a live handle since launch, so .ExitCode is readable here.
      $rc = "?"
      try {
        if ($st.proc) { $st.proc.Refresh(); if ($st.proc.HasExited) { $rc = [int]$st.proc.ExitCode } }
      } catch { $rc = "?" }
      $st.rc = $rc
      $st.secs = if ($st.launched) { [int]($now - $st.launched).TotalSeconds } else { 0 }
      $errLen = 0
      if (Test-Path $st.err) { $errLen = (Get-Item $st.err).Length }

      # Verdict.  An unreadable exit code must NOT be scored as failure (that
      # would flag all 24 shards); fall back to the shard's own evidence --
      # did its heartbeat reach the shard total?
      $howto = "rc"
      if ($rc -is [int]) {
        $ok = ($rc -eq 0)
      } else {
        # fall back to the instrument's own terminal marker, then to progress
        $howto = if ($st.sawDone) { "STATUS-DONE" } else { "heartbeat" }
        $ok = ($st.sawDone -or ($st.total -gt 0 -and $st.lines -ge $st.total))
      }
      $st.state = if ($ok) { "DONE" } else { "FAIL" }
      Ledger "s$nn" $st.state $st.pid $st.pstart $st.lines $st.secs $rc "verdict-by=$howto stderr=${errLen}B lines=$($st.lines)/$($st.total)"
      if (-not $ok) {
        Alarm @("*** SHARD s$nn EXITED rc=$rc (verdict by $howto) ***",
                "heartbeat reached $($st.lines) of $($st.total) intermediates",
                "log: $($st.log)", "err: $($st.err) ($errLen bytes)")
      }
    }
  }

  # --------------------------------------------------------------- reports --
  $doneShards  = @($S.Values | Where-Object { $_.state -eq "DONE" }).Count
  $failShards  = @($S.Values | Where-Object { $_.state -in @("FAIL","LAUNCHFAIL") }).Count
  $pendShards  = @($S.Values | Where-Object { $_.state -eq "PENDING" }).Count
  $elapsed     = ($now - $t0).TotalSeconds
  $rate = 0.0; $eta = "?"
  if ($elapsed -gt 30 -and $doneLines -gt 0) {
    $rate = [math]::Round($doneLines / $elapsed, 3)
    if ($rate -gt 0) { $eta = "{0:n1}m" -f ([math]::Max($totalKnown - $doneLines, 0) / $rate / 60) }
  }
  # Capped at 100: the heartbeat may carry a header/summary line beyond the
  # per-intermediate ones, and a >100% progress figure reads as a broken run.
  $pct = 0.0
  if ($totalKnown -gt 0) { $pct = [math]::Min(100.0, [math]::Round(100.0 * $doneLines / $totalKnown, 1)) }
  $stage = "RUNNING"
  if ($aborted) { $stage = "ABORTING" }
  elseif ($alive -eq 0 -and $pendShards -eq 0) { $stage = "ALLDONE" }

  # live table -- exactly the columns the operator asked for, rewritten each
  # tick (the append-only history is ledger.csv).
  $tbl = @("shard,pid,start,last_heartbeat,lines,total,state,rc,escapes")
  foreach ($nn in ($S.Keys | Sort-Object)) {
    $st = $S[$nn]
    $lh = if ($st.lastAdv) { $st.lastAdv.ToString("HH:mm:ss") } else { "-" }
    $ss = if ($st.launched) { $st.launched.ToString("HH:mm:ss") } else { "-" }
    $state = if ($st.stalled -and $st.state -eq "RUNNING") { "STALLED" } else { $st.state }
    $tbl += "s$nn,$($st.pid),$ss,$lh,$($st.lines),$($st.total),$state,$($st.rc),$($st.escapes)"
  }
  $tbl | Set-Content "$run\TABLE.csv"

  $lines = @(
    "untargeted fused-pair sweep -- tag=$Tag  mode=$Mode",
    "stage:        $stage   shards: $alive running / $doneShards done / $failShards failed / $pendShards pending  (of $Shards, pool=$Workers)",
    "intermediates:$doneLines/$totalKnown ($pct%)   rate=$rate/s   elapsed=$('{0:n1}m' -f ($elapsed/60))   eta=$eta",
    "products:     stats rows=$statRows   edge rows=$edgeRows (rediscoveries)   ESCAPES=$escTotal",
    "shard mem:    sum=$memSum MB  max=$memMax MB  (projection: 24 x ~250 MB)",
    "alive:        $($aliveList -join ' ')",
    "stalled:      $(if ($stalledList.Count) { ($stalledList | Select-Object -Unique) -join ' ' } else { 'none' })  (threshold ${StallMinutes}m)",
    "run dir:      $run",
    "abort:        powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\untargeted_abort.ps1 -Tag $Tag",
    "updated:      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
  )
  if ($escTotal -gt 0) { $lines = @("*** $escTotal ESCAPE(S) -- the sweep's target event. See ALARM.txt and gate every one. ***") + $lines }
  if (Test-Path "$run\ALARM.txt") { $lines = @("*** ALARM.txt PRESENT -- read it before trusting this run ***") + $lines }
  if ($stalledList.Count -gt 0)   { $lines = @("*** $(($stalledList | Select-Object -Unique).Count) SHARD(S) STALLED ***") + $lines }
  $lines | Set-Content "$run\STATUS.txt"

  if ($aborted -and $alive -eq 0) {
    Add-Content "$run\STATUS.txt" "ABORTED at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') after $('{0:n1}m' -f ($elapsed/60))"
    break
  }
  if (-not $aborted -and $alive -eq 0 -and $pendShards -eq 0) {
    Add-Content "$run\STATUS.txt" "ALLDONE at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') after $('{0:n1}m' -f ($elapsed/60))  ($doneShards ok, $failShards failed)"
    Ledger "-" "ALLDONE" 0 "" $doneLines ([int]$elapsed) "" "$doneShards ok / $failShards failed"
    break
  }
  Start-Sleep -Seconds $TickSeconds
}
