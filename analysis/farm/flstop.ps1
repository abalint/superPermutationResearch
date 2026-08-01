# flstop.ps1 -- abort the fl1577 recipe study.  Kills LKH.exe processes and the
# recorded worker/supervisor powershells ONLY, verifying process identity first
# (the s19 PID-recycling trap: pid files do not survive a reboot).
# python.exe is NEVER touched -- it is the user's transcription service.
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\superpermFarm\fl1577\flstop.ps1 -Tag f1
param([string]$Tag = "", [string]$Root = "D:\superpermFarm\fl1577", [switch]$All)
$ErrorActionPreference = "Continue"
if ($Tag -eq "" -and -not $All) { throw "-Tag required (or -All to sweep orphan LKH processes)" }
$RunRoot = "$Root\runs\$Tag"

$killed = 0
foreach ($p in @(Get-Process -Name LKH -EA SilentlyContinue)) {
  # only ever kill LKH.exe, and only ours (the study binary lives under $Root)
  $path = try { $p.Path } catch { "" }
  if ($All -or $path -like "$Root*") { Stop-Process -Id $p.Id -Force -EA SilentlyContinue; $killed++ }
}
Write-Output "killed $killed LKH process(es)"

if (Test-Path "$RunRoot\pids") {
  foreach ($f in (Get-ChildItem "$RunRoot\pids\*.txt")) {
    $parts = (Get-Content $f.FullName) -split ' ',2
    $pid_ = [int]$parts[0]
    $p = Get-Process -Id $pid_ -EA SilentlyContinue
    if ($null -eq $p) { continue }
    if ($p.ProcessName -ne "powershell") { Write-Output "pid $pid_ is now '$($p.ProcessName)' -- NOT killing (recycled)"; continue }
    if ($parts.Count -gt 1) {
      $want = try { [datetime]::Parse($parts[1]) } catch { $null }
      if ($want -and [math]::Abs(($p.StartTime - $want).TotalSeconds) -gt 5) {
        Write-Output "pid $pid_ start time mismatch -- NOT killing (recycled)"; continue
      }
    }
    Stop-Process -Id $pid_ -Force -EA SilentlyContinue
    Write-Output "killed worker powershell pid $pid_"
  }
}
Write-Output "python.exe left alone: $(@(Get-Process -Name python -EA SilentlyContinue).Count) process(es)"
