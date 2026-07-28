# tc2status.ps1 -- one-screen status of the Track C v2 sweep.  Read-only.
$ROOT = "F:\superpermFarm\trackc2"

$gen  = @(Get-Content "$ROOT\jobs.txt"     | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") }).Count
$evl  = @(Get-Content "$ROOT\evaljobs.txt" | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") }).Count

$gdone = @(Get-ChildItem "$ROOT\done" -Filter *.done -EA SilentlyContinue | Where-Object { $_.Name -notlike "*_evalblind.done" }).Count
$edone = @(Get-ChildItem "$ROOT\done" -Filter *_evalblind.done -EA SilentlyContinue).Count

$running = 0; $grun = 0; $erun = 0; $runjobs = @()
Get-ChildItem "$ROOT\claims" -Filter *.claim -EA SilentlyContinue | ForEach-Object {
    $jid = $_.BaseName
    if (Test-Path "$ROOT\done\$jid.done") { return }
    $owner = 0
    try { $owner = [int]((Get-Content $_.FullName -TotalCount 1).Trim()) } catch { $owner = 0 }
    if ($owner -gt 0 -and (Get-Process -Id $owner -EA SilentlyContinue)) {
        $running++; $runjobs += $jid
        if ($jid -like "*_evalblind") { $erun++ } else { $grun++ }
    } else { $runjobs += "$jid(STALE)" }
}

$gw = 0; $ew = 0
Get-ChildItem "$ROOT\workers" -Filter *.alive -EA SilentlyContinue | ForEach-Object {
    $wpid = 0
    try { $wpid = [int]($_.BaseName) } catch { $wpid = 0 }
    if ($wpid -gt 0 -and (Get-Process -Id $wpid -EA SilentlyContinue)) {
        if ((Get-Content $_.FullName -TotalCount 1) -like "eval*") { $ew++ } else { $gw++ }
    }
}
$engines = @(Get-Process dlx7g -EA SilentlyContinue).Count

Write-Output ("TRACK C v2 sweep  {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Output ("  generation : done {0}/{1}   running {2}   pending {3}" -f $gdone, $gen, $grun, ($gen - $gdone - $grun))
Write-Output ("  eval blind : done {0}/{1}   running {2}" -f $edone, $evl, $erun)
Write-Output ("  workers    : gen={0} eval={1} (target 20+6)  dlx7g engines running={2}  claimed-running={3}" -f $gw, $ew, $engines, $running)
if ($runjobs.Count -gt 0) { Write-Output ("  in flight  : " + ($runjobs -join " ")) }
if (Test-Path "$ROOT\ALERT.txt") { Write-Output "*** ALERT.txt PRESENT -- possible SAT candidate, validate on the Mac ***" }

$jl = @(Get-ChildItem "$ROOT\gen" -Filter *.jsonl -EA SilentlyContinue)
$mb = 0; foreach ($f in $jl) { $mb += $f.Length }
Write-Output ("  subtree logs: {0} files, {1:N1} MB in {2}\gen" -f $jl.Count, ($mb/1MB), $ROOT)

Write-Output "--- ledger tail (jid,inst,verdict,rc,nodes,maxdepth,secs,jsonl_recs,worker) ---"
if (Test-Path "$ROOT\ledger.csv") {
    Get-Content "$ROOT\ledger.csv" -Tail 14 | ForEach-Object { Write-Output ("   " + $_) }
    Write-Output ("   ledger rows = {0}" -f @(Get-Content "$ROOT\ledger.csv").Count)
} else { Write-Output "   no ledger yet" }
