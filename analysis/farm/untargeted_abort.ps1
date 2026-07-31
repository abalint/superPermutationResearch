# untargeted_abort.ps1 -- abort a fused-pair UNTARGETED sweep, cleanly.
#
# SAFETY, in order of importance:
#  1. It never kills anything named `python`.  The user's transcription
#     service runs I:\transcribe\.venv\Scripts\python.exe and
#     C:\Program Files\Python311\python.exe (REMOTE-FARM.md: "NEVER kill python
#     processes indiscriminately on this box").  Our shards are `upyw.exe`, a
#     renamed copy of our own venv interpreter, precisely so that this script
#     can be exact.
#  2. It kills only PIDs recorded in this run's pids\ dir, and only after
#     confirming the process NAME and START TIME still match what was recorded
#     (s19 lesson: Windows recycles PIDs -- 5 of 96 stale pid files resolved to
#     unrelated live processes after a reboot).
#  3. It signals the supervisor first via an ABORT flag file, so the supervisor
#     writes its own terminal ledger row instead of being shot mid-write.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\untargeted_abort.ps1
#   ... -Tag u1     a specific run (default: most recent)
#   ... -All        also kill any upyw.exe NOT in this run's pid list (orphans
#                   from an earlier launch -- the s28 duplicate-run trap)
#   ... -Wait N     seconds to let the supervisor notice the flag (default 5)
param([string]$Tag = "", [switch]$All, [int]$Wait = 5)
$ROOT  = "F:\superpermFarm\untargeted"
$PNAME = "upyw"

if ($Tag -eq "") {
  $d = Get-ChildItem "$ROOT\runs" -Directory -EA SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $d) { Write-Output "no runs under $ROOT\runs"; exit 0 }
  $Tag = $d.Name
}
$run = "$ROOT\runs\$Tag"
if (-not (Test-Path $run)) { Write-Output "no such run: $run"; exit 1 }
Write-Output "aborting run $Tag"

# 1. tell the supervisor to stop backfilling the pool
"aborted by untargeted_abort.ps1 at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Set-Content "$run\ABORT"
Start-Sleep -Seconds $Wait

# 2. kill our shards, identity-checked
$known = @(); $killed = 0; $refused = 0
Get-ChildItem "$run\pids" -Filter "s*.txt" -EA SilentlyContinue | ForEach-Object {
  $parts = (Get-Content $_.FullName -TotalCount 1) -split "`t"
  $wpid = 0
  try { $wpid = [int]($parts[0].Trim()) } catch { $wpid = 0 }
  if ($wpid -le 0) { return }
  $known += $wpid
  $recStart = if ($parts.Count -ge 3) { $parts[2].Trim() } else { "" }
  $p = Get-Process -Id $wpid -EA SilentlyContinue
  if (-not $p) { Write-Output "  $($_.BaseName) pid=$wpid already gone"; return }
  if ($p.ProcessName -ne $PNAME) {
    Write-Output "  $($_.BaseName) pid=$wpid is '$($p.ProcessName)' NOT $PNAME -- REFUSING (recycled pid)"
    $refused++; return
  }
  if ($recStart -ne "") {
    $nowStart = ""
    try { $nowStart = $p.StartTime.ToString("o") } catch { $nowStart = "" }
    if ($nowStart -ne "" -and $nowStart -ne $recStart) {
      Write-Output "  $($_.BaseName) pid=$wpid start-time mismatch ($nowStart vs $recStart) -- REFUSING (recycled pid)"
      $refused++; return
    }
  }
  Stop-Process -Id $wpid -Force -EA SilentlyContinue
  $killed++
  Write-Output "  killed $($_.BaseName) pid=$wpid"
}

# 3. orphans (only ever upyw -- never python)
if ($All) {
  Get-Process -Name $PNAME -EA SilentlyContinue | Where-Object { $known -notcontains $_.Id } | ForEach-Object {
    Stop-Process -Id $_.Id -Force -EA SilentlyContinue
    $killed++
    Write-Output "  killed ORPHAN $PNAME pid=$($_.Id)"
  }
}

# 4. the supervisor last, so it can finish its terminal write
if (Test-Path "$run\super.pid") {
  $sp = 0
  try { $sp = [int](Get-Content "$run\super.pid" -TotalCount 1) } catch { $sp = 0 }
  if ($sp -gt 0) {
    $p = Get-Process -Id $sp -EA SilentlyContinue
    if ($p -and $p.ProcessName -like "powershell*") {
      Stop-Process -Id $sp -Force -EA SilentlyContinue
      Write-Output "  killed supervisor pid=$sp"
    } else { Write-Output "  supervisor pid=$sp not alive (or recycled) -- skipped" }
  }
}

$ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$ts,-,ABORT,0,$PNAME,,0,0,,killed=$killed refused=$refused" | Add-Content "$run\ledger.csv"
Add-Content "$run\STATUS.txt" "ABORTED by untargeted_abort.ps1 at $ts (killed $killed, refused $refused)"

$rem = @(Get-Process -Name $PNAME -EA SilentlyContinue).Count
$tpy = @(Get-Process -Name python,pythonw -EA SilentlyContinue).Count
Write-Output "done: killed $killed, refused $refused (recycled pids)."
Write-Output "remaining upyw.exe box-wide: $rem      python.exe (transcription, untouched): $tpy"
