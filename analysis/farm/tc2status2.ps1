# tc2status2.ps1 -- one-screen status of the Track C v2.1 GEN2 sweep.  Read-only.
$ROOT = "F:\superpermFarm\trackc2"

$jobs = @(Get-Content "$ROOT\jobs2.txt" | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") }).Count
$done = @(Get-ChildItem "$ROOT\done2" -Filter *.done -EA SilentlyContinue).Count

$running = 0; $runjobs = @()
Get-ChildItem "$ROOT\claims2" -Filter *.claim -EA SilentlyContinue | ForEach-Object {
    $jid = $_.BaseName
    if (Test-Path "$ROOT\done2\$jid.done") { return }
    $owner = 0
    try { $owner = [int]((Get-Content $_.FullName -TotalCount 1).Trim()) } catch { $owner = 0 }
    if ($owner -gt 0 -and (Get-Process -Id $owner -EA SilentlyContinue)) { $running++; $runjobs += $jid }
    else { $runjobs += "$jid(STALE)" }
}

$gw = 0
Get-ChildItem "$ROOT\workers2" -Filter *.alive -EA SilentlyContinue | ForEach-Object {
    $wpid = 0
    try { $wpid = [int]($_.BaseName) } catch { $wpid = 0 }
    if ($wpid -gt 0 -and (Get-Process -Id $wpid -EA SilentlyContinue)) { $gw++ }
}
$engines = @(Get-Process dlx7g_v21 -EA SilentlyContinue).Count

Write-Output ("TRACK C v2.1 GEN2 sweep  {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Output ("  gen2     : done {0}/{1}   running {2}   pending {3}" -f $done, $jobs, $running, ($jobs - $done - $running))
Write-Output ("  workers  : gen2={0} (target 20)  dlx7g_v21 engines running={1}" -f $gw, $engines)
if ($runjobs.Count -gt 0) { Write-Output ("  in flight: " + ($runjobs -join " ")) }
if (Test-Path "$ROOT\ALERT.txt") { Write-Output "*** ALERT.txt PRESENT -- possible SAT candidate, validate on the Mac ***" }

$jl = @(Get-ChildItem "$ROOT\gen2" -Filter *.jsonl -EA SilentlyContinue)
$mb = 0; $mx = 0; $mxn = ""
foreach ($f in $jl) { $mb += $f.Length; if ($f.Length -gt $mx) { $mx = $f.Length; $mxn = $f.Name } }
Write-Output ("  logs     : {0} files, {1:N1} MB total, largest {2:N1} MB ({3})" -f $jl.Count, ($mb/1MB), ($mx/1MB), $mxn)

Write-Output "--- ledger2 tail (jid,inst,verdict,rc,nodes,maxdepth,secs,probes,probe_recs,probe_nodes,mb,worker) ---"
if (Test-Path "$ROOT\ledger2.csv") {
    Get-Content "$ROOT\ledger2.csv" -Tail 10 | ForEach-Object { Write-Output ("   " + $_) }
    Write-Output ("   ledger2 rows = {0}" -f @(Get-Content "$ROOT\ledger2.csv").Count)
} else { Write-Output "   no ledger2 yet" }
