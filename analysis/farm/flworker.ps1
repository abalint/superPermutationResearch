# flworker.ps1 -- PowerShell port of out/s55/fl1577/run_fl1577.sh for the farm PC.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File flworker.ps1 -Tag <tag> -Worker 03
#
# Launched by fllaunch.ps1 through detach.exe -> flworker.bat (BELOW_NORMAL, no
# console).  Nothing but the tag and a two-digit worker id ever crosses a command
# line; the cell list lives in runs\<tag>\cells\wNN.txt and the budget in
# runs\<tag>\PARAMS.txt (detach.exe joins argv with single spaces, so anything
# containing a space or a comma must not be an argument -- house rule).
#
# One worker owns a list of (config,seed) cells and runs them sequentially.  It
# writes its OWN ledger shard (ledger_wNN.tsv): there is no shared append across
# 25 processes, deliberately -- Windows has no atomic append, and the s19 lesson
# says supervisors, not workers, do bookkeeping.  flsuper.ps1 concatenates the
# shards into runs\<tag>\ledger.tsv.
#
# TSV COLUMNS AND ACCOUNTING ARE COPIED VERBATIM FROM run_fl1577.sh so the rows
# drop straight in beside out/s55/fl1577/runs*/ledger.tsv:
#   config seed best gap gap_pct secs runs successes cracked trials logfile
#     gap     = best - 22249      cracked = 1 iff best == 22249
#     best    = last "Cost.min = N", else min "Run n: Cost = M", else min "* n: Cost = M"
#     trials  = last "Trials = N" (0 if unparsed)
# Budget semantics are also copied: RUNS = 1000 and MAX_TRIALS = 1000000 by
# default, so a single chained-LK run consumes the whole TOTAL_TIME_LIMIT rather
# than exiting early on MAX_TRIALS (the s55 "incomparable budgets" trap).
#
# ONE DELIBERATE DIVERGENCE from the bash harness: the bash version appends the
# fragment after its own defaults and relies on LKH's last-keyword-wins parsing.
# Here, any keyword the fragment defines is simply NOT emitted by the harness, so
# a recipe like popga (which MUST set a finite MAX_TRIALS/TIME_LIMIT for the
# genetic layer to engage at all) does not depend on undocumented parser order.
# Harness-owned keywords are refused outright if a fragment tries to set them.
param(
  [string]$Tag     = "",
  [string]$Worker  = "00",
  [string]$Root    = "D:\superpermFarm\fl1577"
)
$ErrorActionPreference = "Continue"

$OPTIMUM  = 22249
$RUNS_V   = 1000
$TRIALS_V = 1000000
$HARNESS_OWNED = @("PROBLEM_FILE","OPTIMUM","SEED","TOUR_FILE","TOTAL_TIME_LIMIT","STOP_AT_OPTIMUM")

try { (Get-Process -Id $PID).PriorityClass = "BelowNormal" } catch { }

if ($Tag -eq "") { throw "-Tag required" }
$RunRoot = "$Root\runs\$Tag"
$CfgDir  = "$Root\cfg"
$Lkh     = "$Root\bin\LKH.exe"
$Problem = "$Root\fl1577.tsp"

$params = @{}
foreach ($l in (Get-Content "$RunRoot\PARAMS.txt")) {
  if ($l -match '^\s*(\w+)\s*=\s*(.+?)\s*$') { $params[$Matches[1]] = $Matches[2] }
}
$Tlim = [int]$params["Tlim"]

$shard = "$RunRoot\ledger_w$Worker.tsv"
$prog  = "$RunRoot\progress\w$Worker.txt"
New-Item -ItemType Directory -Force -Path "$RunRoot\progress" | Out-Null
function Note($m) {
  ("{0} w{1} {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ss"), $Worker, $m) | Set-Content $prog
}

$list = @()
foreach ($l in (Get-Content "$RunRoot\cells\w$Worker.txt")) {
  if ($l.Trim() -eq "") { continue }
  $p = $l.Trim() -split '\s+'
  $list += ,@($p[0], [int]$p[1])
}
Note "start cells=$($list.Count) tlim=$Tlim pid=$PID"
"$PID $((Get-Process -Id $PID).StartTime.ToString('o'))" | Set-Content "$RunRoot\pids\w$Worker.txt"

$i = 0
foreach ($cell in $list) {
  $i++
  $name = $cell[0]; $seed = $cell[1]
  $frag = "$CfgDir\$name.par"
  if (-not (Test-Path $frag)) { Note "MISSING FRAGMENT $frag"; continue }

  $rundir = "$RunRoot\${name}_s$seed"
  New-Item -ItemType Directory -Force -Path $rundir | Out-Null
  $par = "$rundir\lkh.par"
  $log = "$rundir\lkh.log"

  # fragment = non-comment, non-blank lines; collect the keywords it defines
  $fragLines = @(Get-Content $frag | Where-Object { $_ -notmatch '^\s*#' -and $_.Trim() -ne "" })
  $fragKeys  = @($fragLines | ForEach-Object { ($_ -split '=')[0].Trim().ToUpper() })
  foreach ($k in $fragKeys) {
    if ($HARNESS_OWNED -contains $k) { throw "fragment $frag sets harness-owned keyword $k" }
  }

  $pl = New-Object System.Collections.ArrayList
  [void]$pl.Add("PROBLEM_FILE = $Problem")
  [void]$pl.Add("OPTIMUM = $OPTIMUM")
  if ($fragKeys -notcontains "RUNS")       { [void]$pl.Add("RUNS = $RUNS_V") }
  [void]$pl.Add("SEED = $seed")
  if ($fragKeys -notcontains "MAX_TRIALS") { [void]$pl.Add("MAX_TRIALS = $TRIALS_V") }
  if ($fragKeys -notcontains "TIME_LIMIT") { [void]$pl.Add("TIME_LIMIT = $Tlim") }
  [void]$pl.Add("TOTAL_TIME_LIMIT = $Tlim")
  [void]$pl.Add("STOP_AT_OPTIMUM = YES")
  [void]$pl.Add("TOUR_FILE = $rundir\best.tour")
  [void]$pl.Add("# ---- recipe fragment: $frag ----")
  foreach ($l in $fragLines) { [void]$pl.Add($l) }
  $pl | Set-Content $par

  Note "cell $i/$($list.Count) $name s$seed RUNNING"
  $t0 = Get-Date
  & $Lkh $par *> $log
  $rc = $LASTEXITCODE
  $secs = [int]((Get-Date) - $t0).TotalSeconds

  # --- parse, verbatim precedence order from run_fl1577.sh ------------------
  $best = $null
  $m = @(Select-String -Path $log -Pattern 'Cost\.min = (\d+)')
  if ($m.Count -gt 0) { $best = [int]$m[-1].Matches[0].Groups[1].Value }
  if ($null -eq $best) {
    $m = @(Select-String -Path $log -Pattern '^Run \d+: Cost = (\d+)')
    if ($m.Count -gt 0) { $best = ($m | ForEach-Object { [int]$_.Matches[0].Groups[1].Value } | Measure-Object -Minimum).Minimum }
  }
  if ($null -eq $best) {
    $m = @(Select-String -Path $log -Pattern '^\* \d+: Cost = (\d+)')
    if ($m.Count -gt 0) { $best = ($m | ForEach-Object { [int]$_.Matches[0].Groups[1].Value } | Measure-Object -Minimum).Minimum }
  }

  $succ = 0
  $m = @(Select-String -Path $log -Pattern 'Successes/Runs = (\d+)')
  if ($m.Count -gt 0) { $succ = [int]$m[-1].Matches[0].Groups[1].Value }
  # trials: the bash harness's 'Trials = (\d+)' is a substring match that also hits
  # the echoed parameter block (BACKBONE_TRIALS/MAX_TRIALS/POPMUSIC_TRIALS), so it
  # reports POPMUSIC_TRIALS = 1 whenever LKH echoes its parameters -- which this
  # Windows build does and the Mac logs did not (hence trials=0 in the s55 ledgers).
  # Take LKH's own summary line instead, which is what the column documents.
  $trials = 0
  $m = @(Select-String -Path $log -Pattern 'Trials\.max = (\d+)')
  if ($m.Count -gt 0) { $trials = [int]$m[-1].Matches[0].Groups[1].Value }
  else {
    $m = @(Select-String -Path $log -Pattern '^Trials = (\d+)')
    if ($m.Count -gt 0) { $trials = [int]$m[-1].Matches[0].Groups[1].Value }
  }

  if ($null -eq $best) {
    $bestS = "NA"; $gap = "NA"; $gappct = "NA"; $cracked = 0
    Note "cell $i/$($list.Count) $name s$seed WARN no cost parsed rc=$rc"
  } else {
    $bestS = "$best"
    $g = $best - $OPTIMUM
    $gap = "$g"
    $gappct = "{0:F4}" -f (100.0 * $g / $OPTIMUM)
    $cracked = 0; if ($g -eq 0) { $cracked = 1 }
  }

  $row = "$name`t$seed`t$bestS`t$gap`t$gappct`t$secs`t$RUNS_V`t$succ`t$cracked`t$trials`t$log"
  $row | Set-Content "$rundir\row.tsv"
  Add-Content -Path $shard -Value $row
  Note "cell $i/$($list.Count) $name s$seed DONE best=$bestS gap=$gap secs=$secs cracked=$cracked"
}
Note "FINISHED $($list.Count) cells"
