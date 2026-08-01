# flstatus.ps1 -- operator status for the fl1577 recipe study.
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\superpermFarm\fl1577\flstatus.ps1 -Tag f1
param([string]$Tag = "", [string]$Root = "D:\superpermFarm\fl1577", [switch]$Ledger)
$ErrorActionPreference = "Continue"
if ($Tag -eq "") { throw "-Tag required" }
$RunRoot = "$Root\runs\$Tag"
if (Test-Path "$RunRoot\STATUS.txt") { Get-Content "$RunRoot\STATUS.txt" } else { "no STATUS.txt at $RunRoot" }
""
$live = @(Get-Process -Name LKH -EA SilentlyContinue)
$cpu = 0.0; foreach ($p in $live) { $cpu += $p.CPU }
$rss = 0;   foreach ($p in $live) { $rss += $p.WorkingSet64 }
"live LKH : {0}   RSS {1} MB   cpu-seconds {2:F0}" -f $live.Count, [int]($rss/1MB), $cpu
"python.exe on the box : {0}   (the user's transcription service -- NOT ours, NEVER kill)" -f `
  @(Get-Process -Name python -EA SilentlyContinue).Count
if (Test-Path "$RunRoot\ALARM.txt") { ""; "!!!!!!!!!! ALARM.txt !!!!!!!!!!"; Get-Content "$RunRoot\ALARM.txt" }
if ($Ledger -and (Test-Path "$RunRoot\ledger.tsv")) { ""; "--- ledger ---"; Get-Content "$RunRoot\ledger.tsv" }
