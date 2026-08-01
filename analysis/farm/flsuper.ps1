# flsuper.ps1 -- supervisor/heartbeat for the fl1577 recipe study (docs/OPERATIONS.md).
# Started detached by fllaunch.ps1.  Every tick it:
#   * concatenates the per-worker ledger shards into runs\<tag>\ledger.tsv (header
#     + all rows; shards are append-only and worker-private, so this is safe)
#   * rewrites runs\<tag>\STATUS.txt: stage, done/total, cracked_total, per-recipe
#     breakdown, live worker count + aggregate CPU seconds, ETA
#   * exits when every cell has a row or every worker process is gone
# Liveness is CPU-seconds-based, not log-mtime: a quiet LKH is still working.
param(
  [string]$Tag  = "",
  [string]$Root = "D:\superpermFarm\fl1577",
  [int]$TickSeconds  = 30,
  [int]$StallMinutes = 25
)
$ErrorActionPreference = "Continue"
if ($Tag -eq "") { throw "-Tag required" }
$RunRoot = "$Root\runs\$Tag"
$HEADER = "config`tseed`tbest`tgap`tgap_pct`tsecs`truns`tsuccesses`tcracked`ttrials`tlogfile"

$params = @{}
foreach ($l in (Get-Content "$RunRoot\PARAMS.txt")) {
  if ($l -match '^\s*(\w+)\s*=\s*(.+?)\s*$') { $params[$Matches[1]] = $Matches[2] }
}
$total   = [int]$params["Cells"]
$workers = [int]$params["Workers"]
$tlim    = [int]$params["Tlim"]
$start   = Get-Date
$lastN   = -1
$lastChange = Get-Date

while ($true) {
  $rows = @()
  foreach ($f in (Get-ChildItem "$RunRoot\ledger_w*.tsv" -EA SilentlyContinue)) {
    $rows += @(Get-Content $f.FullName | Where-Object { $_.Trim() -ne "" })
  }
  # ledger.tsv is rewritten wholesale each tick -- column semantics are fixed
  # for the life of the file (s19 lesson), only rows are ever added.
  @($HEADER) + $rows | Set-Content "$RunRoot\ledger.tsv"

  $done = $rows.Count
  if ($done -ne $lastN) { $lastN = $done; $lastChange = Get-Date }

  $cracked = @($rows | Where-Object { ($_ -split "`t")[8] -eq "1" }).Count
  $byCfg = @{}
  foreach ($r in $rows) {
    $c = ($r -split "`t")[0]
    if (-not $byCfg.ContainsKey($c)) { $byCfg[$c] = @(0,0,999999) }  # done, cracked, bestgap
    $byCfg[$c][0]++
    if (($r -split "`t")[8] -eq "1") { $byCfg[$c][1]++ }
    $g = ($r -split "`t")[3]
    if ($g -ne "NA" -and [int]$g -lt $byCfg[$c][2]) { $byCfg[$c][2] = [int]$g }
  }

  $live = @(Get-Process -Name LKH -EA SilentlyContinue)
  $cpu = 0.0; foreach ($p in $live) { $cpu += $p.CPU }
  $liveW = @(Get-Process -Name powershell -EA SilentlyContinue).Count

  $elapsed = ((Get-Date) - $start).TotalMinutes
  $eta = "n/a"
  if ($done -gt 0 -and $done -lt $total) {
    $eta = "{0:F0} min" -f ($elapsed / $done * ($total - $done))
  }
  $stage = if ($done -ge $total) { "ALLDONE" } elseif ($live.Count -eq 0 -and $done -gt 0) { "DRAINING" } else { "RUNNING" }

  $out = New-Object System.Collections.ArrayList
  [void]$out.Add("=== fl1577 recipe study   tag=$Tag ===")
  [void]$out.Add("stage:      $stage   elapsed={0:F1}m   eta=$eta" -f $elapsed)
  [void]$out.Add("cells:      $done / $total done   workers=$workers   tlim=${tlim}s")
  [void]$out.Add("CRACKED_TOTAL: $cracked      (cracked = 1 iff best == 22249)")
  [void]$out.Add("live LKH:   $($live.Count)   aggregate cpu-seconds {0:F0}" -f $cpu)
  [void]$out.Add("")
  [void]$out.Add("per-recipe   done  cracked  best_gap")
  foreach ($k in ($byCfg.Keys | Sort-Object)) {
    # NB the -f expression MUST be parenthesised: inside a .Add(...) call the commas
    # of the format-argument list are otherwise parsed as extra method arguments,
    # so Add() throws and (under $ErrorActionPreference=Continue) the row silently
    # vanishes -- which is exactly what happened on the first s1 run.
    [void]$out.Add(("  {0,-16} {1,4}  {2,7}  {3,8}" -f $k, $byCfg[$k][0], $byCfg[$k][1], $byCfg[$k][2]))
  }
  [void]$out.Add("")
  $quiet = ((Get-Date) - $lastChange).TotalMinutes
  if ($quiet -gt $StallMinutes -and $stage -eq "RUNNING") {
    [void]$out.Add("*** STALL WARNING: ledger unchanged for {0:F0} min ***" -f $quiet)
    "$(Get-Date -Format o) ledger unchanged {0:F0} min, live LKH={1}, cpu={2:F0}" -f $quiet, $live.Count, $cpu |
      Add-Content "$RunRoot\ALARM.txt"
  }
  [void]$out.Add("run dir:    $RunRoot")
  [void]$out.Add("ABORT:      powershell -NoProfile -ExecutionPolicy Bypass -File $Root\flstop.ps1 -Tag $Tag")
  [void]$out.Add("updated:    $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
  $out | Set-Content "$RunRoot\STATUS.txt"

  if ($done -ge $total) { break }
  if ($live.Count -eq 0 -and $elapsed -gt 3) {
    # every worker gone but cells missing -- record it and stop
    if ($done -lt $total) {
      "$(Get-Date -Format o) all LKH gone with $done/$total cells done" | Add-Content "$RunRoot\ALARM.txt"
    }
    break
  }
  Start-Sleep -Seconds $TickSeconds
}
"DONE $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Add-Content "$RunRoot\STATUS.txt"
