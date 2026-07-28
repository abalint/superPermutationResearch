# watchdog.ps1 -- one self-healing pass over the farm, safe to run repeatedly.
#   1. farmlaunch.ps1 restarts any of the five priority K=27 chains that died,
#   2. farmscale.ps1 backfills freed slots from worklist.txt up to its TARGET,
#   3. a timestamped line is appended to F:\superpermFarm\watchdog.log.
#
# Deliberately NOT scheduled: this account is a standard user (no schtasks, no
# elevation). Call it from the Mac on whatever cadence you like:
#   ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\watchdog.ps1"
#
# Safety valve: farmscale.ps1 refuses to start workers below its $MINFREEPCT
# free-RAM floor; this script logs free RAM every pass so memory pressure
# building over days is visible in watchdog.log.
$farm = 'F:\superpermFarm'
$log  = Join-Path $farm 'watchdog.log'
. (Join-Path $farm 'meminfo.ps1')

$before = @(Get-Process PermutationChains, PermutationChains64 -ErrorAction SilentlyContinue).Count

$out = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $farm 'farmlaunch.ps1') 2>&1
$out += & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $farm 'farmscale.ps1') 2>&1

$after  = @(Get-Process PermutationChains, PermutationChains64 -ErrorAction SilentlyContinue).Count
$mem    = Get-FarmMem
$declined = if (($out | Out-String) -match 'DECLINED') { ' DECLINED(low-RAM)' } else { '' }
$sol = @(Get-ChildItem (Join-Path $farm 'runs') -Recurse -Filter '7_59*.txt' -ErrorAction SilentlyContinue).Count
$solTxt = if ($sol) { "  *** $sol SOLUTION FILE(S) ***" } else { '' }

$line = "{0}  alive_before={1} alive_after={2} started={3} ramFree={4}MB/{5}MB ({6}%){7}{8}" -f `
  (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $before, $after, ($after - $before), `
  $mem.AvailMB, $mem.TotalMB, $mem.PctFree, $declined, $solTxt
Add-Content -Path $log -Value $line
Write-Output $line
