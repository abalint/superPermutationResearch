# satstatus.ps1 -- one-screen status of the n=7 cover farm.
$ROOT = "F:\superpermFarm"
$CSV  = "$ROOT\results.csv"

$rec = @(Get-ChildItem "$ROOT\satruns" -Recurse -Filter "candidate_*.txt" -ErrorAction SilentlyContinue)
if ($rec.Count -gt 0) {
    Write-Output "*** CANDIDATE WORD FILES PRESENT - VALIDATE ON THE MAC ***"
    foreach ($f in $rec) { Write-Output ("    {0}  {1} bytes" -f $f.FullName, $f.Length) }
} else {
    Write-Output "no candidate word files yet"
}

$alive = 0
Get-ChildItem "$ROOT\workers" -Filter *.alive -ErrorAction SilentlyContinue | ForEach-Object {
    if (Get-Process -Id ([int]$_.BaseName) -ErrorAction SilentlyContinue) { $alive++ }
}
$py     = @(Get-Process python -ErrorAction SilentlyContinue).Count
$claims = @(Get-ChildItem "$ROOT\claims" -Filter *.claim -ErrorAction SilentlyContinue).Count
$total  = @(Get-Content "$ROOT\sat\farm_chains.jsonl").Count
Write-Output ("workers={0} python_procs={1} claimed={2}/{3}" -f $alive, $py, $claims, $total)

$mem = & "$ROOT\meminfo.ps1" 2>$null
if ($mem) { Write-Output $mem }

if (Test-Path $CSV) {
    $rows = @(Import-Csv $CSV)
    Write-Output ("ledger rows = {0}" -f $rows.Count)
    $rows | Group-Object outcome | Sort-Object Count -Descending | ForEach-Object {
        Write-Output ("   {0,-16} {1}" -f $_.Name, $_.Count) }
    Write-Output "--- last 12 ---"
    $rows | Select-Object -Last 12 | ForEach-Object {
        Write-Output ("   idx={0,-4} K={1,-3} {2,-16} {3,7} min" -f $_.index, $_.K, $_.outcome, $_.minutes) }
} else {
    Write-Output "no ledger yet"
}
