# farmstop.ps1 — stop the WHOLE farm: every PermutationChains* solver plus the
# pids recorded in runs\*\pid.txt. Covers both binaries — the five priority
# K=27 chains run PermutationChains.exe, the scaled workers started by
# farmscale.ps1 run PermutationChains64.exe (see build64.bat).
# After this, farmlaunch.ps1 + farmscale.ps1 (or just watchdog.ps1) restart
# everything; already-attempted patterns are not retried.
$farm = 'F:\superpermFarm'
Get-Process PermutationChains, PermutationChains64 -ErrorAction SilentlyContinue | ForEach-Object {
  Write-Output ("stopping " + $_.ProcessName + " pid " + $_.Id)
  Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
foreach ($d in (Get-ChildItem (Join-Path $farm 'runs') -Directory -ErrorAction SilentlyContinue)) {
  $pidFile = Join-Path $d.FullName 'pid.txt'
  if (Test-Path $pidFile) {
    $wpid = (Get-Content $pidFile -ErrorAction SilentlyContinue) -as [int]
    if ($wpid -and (Get-Process -Id $wpid -ErrorAction SilentlyContinue)) {
      Write-Output ("stopping wrapper pid " + $wpid + " (" + $d.Name + ")")
      Stop-Process -Id $wpid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
  }
}
Write-Output 'farm stopped'
