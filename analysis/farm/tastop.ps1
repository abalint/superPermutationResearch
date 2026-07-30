# tastop.ps1 -- abort a sharded tail-atsp sweep.
#
# Kills ONLY processes whose pid is recorded in this run's pids\ dir AND whose
# name is still superperm (PIDs are recycled on this box -- s19 lesson: 5 of 96
# stale pid files pointed at unrelated live processes after a reboot), plus this
# run's supervisor. Never touches python (the transcription service).
#   -All : also kill any superperm.exe not in this run's pid list (orphans from
#          an earlier launch -- the s28 duplicate-run trap).
param([string]$Tag = "", [switch]$All)
$ROOT = "F:\superpermFarm\tailatsp"

if ($Tag -eq "") {
  $d = Get-ChildItem "$ROOT\runs" -Directory -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $d) { Write-Output "no runs under $ROOT\runs"; exit 0 }
  $Tag = $d.Name
}
$run = "$ROOT\runs\$Tag"
Write-Output "stopping run $Tag"

$known = @()
$killed = 0
Get-ChildItem "$run\pids" -Filter "w*.txt" -ErrorAction SilentlyContinue | ForEach-Object {
  $parts = (Get-Content $_.FullName -TotalCount 1) -split "`t"
  $wpid = 0
  try { $wpid = [int]($parts[0].Trim()) } catch { $wpid = 0 }
  if ($wpid -le 0) { return }
  $known += $wpid
  $p = Get-Process -Id $wpid -ErrorAction SilentlyContinue
  if (-not $p) { Write-Output "  $($_.BaseName) pid=$wpid already gone"; return }
  if ($p.ProcessName -ne "superperm") {
    Write-Output "  $($_.BaseName) pid=$wpid is '$($p.ProcessName)' NOT superperm -- refusing (recycled pid)"
    return
  }
  Stop-Process -Id $wpid -Force -ErrorAction SilentlyContinue
  $killed++
  Write-Output "  killed $($_.BaseName) pid=$wpid"
}

if ($All) {
  Get-Process -Name superperm -ErrorAction SilentlyContinue | Where-Object { $known -notcontains $_.Id } | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    $killed++
    Write-Output "  killed ORPHAN superperm pid=$($_.Id)"
  }
}

if (Test-Path "$run\super.pid") {
  $sp = 0
  try { $sp = [int](Get-Content "$run\super.pid" -TotalCount 1) } catch { $sp = 0 }
  if ($sp -gt 0) {
    $p = Get-Process -Id $sp -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -like "powershell*") {
      Stop-Process -Id $sp -Force -ErrorAction SilentlyContinue
      Write-Output "  killed supervisor pid=$sp"
    } else {
      Write-Output "  supervisor pid=$sp not alive (or recycled) -- skipped"
    }
  }
}

Add-Content "$run\STATUS.txt" "ABORTED by tastop.ps1 at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (killed $killed)"
Write-Output "done: killed $killed process(es). Remaining superperm.exe box-wide: $(@(Get-Process -Name superperm -ErrorAction SilentlyContinue).Count)"
