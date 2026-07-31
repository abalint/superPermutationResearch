# untargeted_status.ps1 -- one screen of the fused-pair UNTARGETED sweep.
# READ-ONLY and cheap: prints what the supervisor already computed (STATUS.txt,
# TABLE.csv, ledger tail) plus a live process cross-check in case the
# supervisor itself died.  It never scans a log -- the s19 OOM wedge was a
# status-side `@(Get-Content $log).Count` on 20 workers.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\untargeted_status.ps1
#   ... -Tag u1        a specific run (default: most recent)
#   ... -Full          also print every ledger row and the per-shard table
param([string]$Tag = "", [switch]$Full)
$ROOT = "F:\superpermFarm\untargeted"

if ($Tag -eq "") {
  $d = Get-ChildItem "$ROOT\runs" -Directory -EA SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $d) { Write-Output "no runs under $ROOT\runs"; exit 0 }
  $Tag = $d.Name
}
$run = "$ROOT\runs\$Tag"
if (-not (Test-Path $run)) { Write-Output "no such run: $run"; exit 1 }

Write-Output "=== untargeted run $Tag   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
if (Test-Path "$run\STATUS.txt") { Get-Content "$run\STATUS.txt" }
else { Write-Output "(no STATUS.txt yet -- supervisor may not have ticked)" }

# --- live cross-check: our shards are `upyw`, never `python` ----------------
$live = @(Get-Process -Name upyw -EA SilentlyContinue)
$memSum = 0; foreach ($p in $live) { try { $memSum += [math]::Round($p.WorkingSet64/1MB) } catch { } }
Write-Output ""
Write-Output "live upyw.exe box-wide: $($live.Count)   RSS sum $memSum MB"
$tpy = @(Get-Process -Name python,pythonw -EA SilentlyContinue).Count
Write-Output "python.exe on the box : $tpy   (the user's transcription service -- NOT ours, NEVER kill)"

$sp = 0
if (Test-Path "$run\super.pid") { try { $sp = [int](Get-Content "$run\super.pid" -TotalCount 1) } catch { $sp = 0 } }
$spAlive = $false
if ($sp -gt 0) {
  $p = Get-Process -Id $sp -EA SilentlyContinue
  if ($p -and $p.ProcessName -like "powershell*") { $spAlive = $true }
}
Write-Output "supervisor pid=$sp alive=$spAlive   (false while shards live => STATUS.txt is STALE, not the run)"

# --- per-shard table (the supervisor's live snapshot) ------------------------
if (Test-Path "$run\TABLE.csv") {
  $rows = Import-Csv "$run\TABLE.csv"
  $byState = $rows | Group-Object state | Sort-Object Name
  Write-Output ""
  Write-Output ("shards by state: " + (($byState | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join "  "))
  # NOTE the parentheses: `Write-Output "x" + $arr` parses as two statements and
  # prints a stray "+" followed by the array, one element per line.
  $stalled = @($rows | Where-Object { $_.state -eq "STALLED" })
  if ($stalled.Count -gt 0) {
    Write-Output ("*** STALLED: " + (($stalled | ForEach-Object { "$($_.shard)(pid $($_.pid), last $($_.last_heartbeat), $($_.lines) lines)" }) -join "  "))
  }
  $bad = @($rows | Where-Object { $_.state -in @("FAIL","LAUNCHFAIL") })
  if ($bad.Count -gt 0) {
    Write-Output ("*** FAILED : " + (($bad | ForEach-Object { "$($_.shard)(rc=$($_.rc))" }) -join "  "))
  }
  if ($Full) {
    Write-Output ""
    $rows | Format-Table -AutoSize | Out-String -Width 200 | Write-Output
  } else {
    # compact one-line-per-shard progress bar
    Write-Output ""
    $line = ""
    foreach ($r in $rows) {
      $t = [int]$r.total; $l = [int]$r.lines
      $p = if ($t -gt 0) { [math]::Min(100, [int](100.0 * $l / $t)) } else { 0 }
      $mark = switch ($r.state) { "DONE" { "+" } "FAIL" { "!" } "LAUNCHFAIL" { "!" } "STALLED" { "?" } "PENDING" { "." } default { "" } }
      $line += ("{0}{1,3}% " -f $mark, $p)
      if ($line.Length -ge 78) { Write-Output ("  " + $line); $line = "" }
    }
    if ($line -ne "") { Write-Output ("  " + $line) }
    Write-Output "  (+ done, ! failed, ? stalled, . pending; -Full for the table)"
  }
}

# --- products ---------------------------------------------------------------
$statRows = 0; $edgeRows = 0; $prod = 0
Get-ChildItem "$run\out" -Recurse -File -Filter *.tsv -EA SilentlyContinue | ForEach-Object {
  # line count without slurping: streamed reader
  $c = 0
  try {
    $fs = [System.IO.File]::Open($_.FullName, 'Open', 'Read', 'ReadWrite')
    $sr = New-Object System.IO.StreamReader($fs)
    while ($null -ne $sr.ReadLine()) { $c++ }
    $sr.Close(); $fs.Close()
  } catch { }
  if ($c -gt 0) { $c-- }
  if ($_.Name -match "(?i)edge") { $edgeRows += $c } elseif ($_.Name -match "(?i)stat") { $statRows += $c }
}
$prod = @(Get-ChildItem "$run\out" -Recurse -File -Filter *.txt -EA SilentlyContinue).Count
Write-Output ""
Write-Output "products: stats rows=$statRows   edge rows=$edgeRows (rediscoveries)   .txt product files=$prod"
if ($prod -gt 0) {
  Write-Output "*** $prod product .txt file(s) written -- these are ESCAPE CANDIDATES. Gate them:"
  Write-Output "    cargo run --release -- validate -n 7 --file <f> --complete"
  Write-Output "    python3 analysis/counting/m3_check.py -n 7 <f>     (exit 2 = novel vs the 220)"
}

if (Test-Path "$run\ALARM.txt") {
  Write-Output ""
  Write-Output "!!!!!!!!!! ALARM.txt !!!!!!!!!!"
  Get-Content "$run\ALARM.txt" -Tail 30
}

Write-Output ""
Write-Output "=== ledger (ts,shard,event,pid,pname,pstart,lines,secs,rc,note) ==="
if (Test-Path "$run\ledger.csv") {
  if ($Full) { Get-Content "$run\ledger.csv" } else { Get-Content "$run\ledger.csv" -Tail 12 }
} else { Write-Output "(no ledger yet)" }
