# tastatus.ps1 -- on-demand status of a sharded tail-atsp sweep. Read-only and
# cheap (no log slurping): prints the supervisor's STATUS.txt, the ledger tail,
# any ALARM, and a live process cross-check in case the supervisor itself died.
param([string]$Tag = "")
$ROOT = "F:\superpermFarm\tailatsp"

if ($Tag -eq "") {
  $d = Get-ChildItem "$ROOT\runs" -Directory -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $d) { Write-Output "no runs under $ROOT\runs"; exit 0 }
  $Tag = $d.Name
}
$run = "$ROOT\runs\$Tag"
Write-Output "=== run $Tag ==="
if (Test-Path "$run\STATUS.txt") { Get-Content "$run\STATUS.txt" }
else { Write-Output "(no STATUS.txt yet)" }

$live = @(Get-Process -Name superperm -ErrorAction SilentlyContinue)
Write-Output "live superperm.exe (box-wide): $($live.Count)"
$sp = 0
if (Test-Path "$run\super.pid") { try { $sp = [int](Get-Content "$run\super.pid" -TotalCount 1) } catch { $sp = 0 } }
$spAlive = $false
if ($sp -gt 0) {
  $p = Get-Process -Id $sp -ErrorAction SilentlyContinue
  if ($p -and $p.ProcessName -like "powershell*") { $spAlive = $true }
}
Write-Output "supervisor pid=$sp alive=$spAlive   (if false while workers live, the heartbeat is stale)"

if (Test-Path "$run\ALARM.txt") {
  Write-Output ""
  Write-Output "!!!!!!!!!! ALARM PRESENT !!!!!!!!!!"
  Get-Content "$run\ALARM.txt"
}
$f = @(Get-ChildItem "$run\finds" -Recurse -File -ErrorAction SilentlyContinue)
Write-Output "find files: $($f.Count)"

Write-Output ""
Write-Output "=== ledger (last 8) ==="
if (Test-Path "$run\ledger.csv") { Get-Content "$run\ledger.csv" -Tail 8 }
