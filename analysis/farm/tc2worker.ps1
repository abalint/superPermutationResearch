# tc2worker.ps1 -- Track C v2 GENERATION worker (parameterless; REMOTE-FARM.md rules).
# Claims jobs from jobs.txt via atomic claim files, runs dlx7g.exe, writes a
# done-marker + a per-job result row.  Idempotent: finished jobs are skipped.
# Never touches any process it did not itself start.
$ROOT = "F:\superpermFarm\trackc2"
$JOBS = "$ROOT\jobs.txt"
$EXE  = "$ROOT\dlx7g.exe"
$me   = $PID

New-Item -ItemType Directory -Force -Path `
  "$ROOT\claims","$ROOT\done","$ROOT\logs","$ROOT\gen","$ROOT\rows", `
  "$ROOT\results.d","$ROOT\pids","$ROOT\workers" | Out-Null
Set-Content -Path "$ROOT\workers\$me.alive" -Value ("gen " + (Get-Date -Format o))

$lines = @(Get-Content $JOBS | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") })

foreach ($line in $lines) {
    $p     = $line.Split("|")
    $jid   = $p[0].Trim()
    $inst  = $p[1].Trim()
    $extra = $p[2].Trim()
    if (Test-Path "$ROOT\done\$jid.done") { continue }

    # atomic claim: CreateNew throws if another worker got here first
    $claim = "$ROOT\claims\$jid.claim"
    try {
        $fs = [System.IO.File]::Open($claim, [System.IO.FileMode]::CreateNew,
                                     [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $sw = New-Object System.IO.StreamWriter($fs)
        $sw.WriteLine("$me")
        $sw.Close(); $fs.Close()
    } catch { continue }
    if (Test-Path "$ROOT\done\$jid.done") { Remove-Item $claim -Force -EA SilentlyContinue; continue }

    $eargs = @("$ROOT\inst\$inst", "--out", "$ROOT\rows\$jid.rows")
    if ($extra -ne "") { $eargs += ($extra -split "\s+") }
    $log = "$ROOT\logs\$jid.log"
    $err = "$ROOT\logs\$jid.err"
    $t0  = Get-Date
    $rc  = -1
    try {
        $proc = Start-Process -FilePath $EXE -ArgumentList $eargs -NoNewWindow -PassThru `
                  -WorkingDirectory $ROOT -RedirectStandardOutput $log -RedirectStandardError $err
        $null = $proc.Handle   # PS quirk: caches the handle so .ExitCode is populated
        Set-Content -Path "$ROOT\pids\$jid.pid" -Value $proc.Id
        $proc.WaitForExit()
        $rc = $proc.ExitCode
        if ($null -eq $rc) { $rc = -1 }
    } catch {
        Set-Content -Path "$err" -Value ("LAUNCH FAILED: " + $_.Exception.Message)
    }
    $secs = [int]((Get-Date) - $t0).TotalSeconds

    $verdict = "ERROR-$rc"
    switch ($rc) { 0 { $verdict = "SAT-CANDIDATE" } 2 { $verdict = "EXHAUSTED" } 3 { $verdict = "TIMEOUT" } }
    $nodes = ""; $maxd = ""
    if (Test-Path $err) {
        $rl = @(Select-String -Path $err -Pattern "^RESULT " -EA SilentlyContinue)
        if ($rl.Count -gt 0) {
            $t = $rl[-1].Line
            # the engine's own RESULT line is authoritative; rc is the fallback
            if ($t -match "^RESULT (\w+)")  { $verdict = $Matches[1] }
            if ($t -match "nodes=(\d+)")    { $nodes = $Matches[1] }
            if ($t -match "maxdepth=(\d+)") { $maxd  = $Matches[1] }
        }
    }
    if ($verdict -eq "SOLVED") { $verdict = "SAT-CANDIDATE" }
    $jl = "$ROOT\gen\$jid.jsonl"
    $recs = 0
    # size in MB, not a line count: slurping the ~200MB JSONL into a PS array
    # x20 workers is what OOM-wedged the box on 2026-07-28 (see OPERATIONS.md)
    if (Test-Path $jl) { $recs = [math]::Round((Get-Item $jl).Length / 1MB, 1) }
    $row = "$jid,$inst,$verdict,$rc,$nodes,$maxd,$secs,$recs,$me"

    Set-Content -Path "$ROOT\results.d\$jid.csv" -Value $row
    for ($k = 0; $k -lt 100; $k++) {
        try {
            $lf = [System.IO.File]::Open("$ROOT\ledger.csv", [System.IO.FileMode]::Append,
                                         [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
            $lw = New-Object System.IO.StreamWriter($lf)
            $lw.WriteLine($row); $lw.Close(); $lf.Close(); break
        } catch { Start-Sleep -Milliseconds 100 }
    }
    Set-Content -Path "$ROOT\done\$jid.done" -Value $row
    Remove-Item $claim -Force -EA SilentlyContinue
    if ($verdict -eq "SAT-CANDIDATE") {
        Add-Content -Path "$ROOT\ALERT.txt" -Value "SAT CANDIDATE $jid -- validate on the Mac before believing"
    }
}

Remove-Item "$ROOT\workers\$me.alive" -Force -EA SilentlyContinue
