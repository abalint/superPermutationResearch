# tc2gate.ps1 -- BUILD GATE (docs/TRACKC2-DESIGN.md sec.8 risk 4).
# The Windows binary, blind on chain 26's instance, MUST print
#   RESULT EXHAUSTED nodes=8548527
# Anything else and NOTHING may be launched from this build.
$ROOT = "F:\superpermFarm\trackc2"
$EXE  = "$ROOT\dlx7g.exe"
$err  = "$ROOT\gate_wl026.err"
$log  = "$ROOT\gate_wl026.log"
Remove-Item $err,$log -Force -EA SilentlyContinue
$t0 = Get-Date
$p = Start-Process -FilePath $EXE -ArgumentList @("$ROOT\inst\wl_026.txt","--time-limit","3600") `
       -NoNewWindow -PassThru -WorkingDirectory $ROOT -RedirectStandardOutput $log -RedirectStandardError $err
$null = $p.Handle          # PS quirk: caches the handle so .ExitCode is populated
$p.WaitForExit()
$rc = $p.ExitCode
$secs = [int]((Get-Date) - $t0).TotalSeconds
$line = (Select-String -Path $err -Pattern "^RESULT " | Select-Object -Last 1).Line
Write-Output "rc=$rc secs=$secs"
Write-Output "stderr RESULT line: $line"
$nodes = ""
if ($line -match "nodes=(\d+)") { $nodes = $Matches[1] }
if ($rc -eq 2 -and $nodes -eq "8548527") {
    Write-Output "BUILD GATE PASS  chain 26 EXHAUSTED nodes=8548527"
} else {
    Write-Output "BUILD GATE FAIL  expected rc=2 nodes=8548527, got rc=$rc nodes=$nodes -- DO NOT LAUNCH"
}
