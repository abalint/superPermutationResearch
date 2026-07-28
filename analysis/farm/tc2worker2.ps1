# tc2worker2.ps1 -- Track C v2.1 GEN2 (pairwise/probe) worker.
# Parameterless (REMOTE-FARM.md rules).  Same claim/done/ledger protocol as
# tc2worker.ps1, but every piece of state lives in its OWN directory so the
# in-flight sweep-1 pool (claims/ done/ gen/ ledger.csv) is untouched:
#   jobs2.txt  claims2/  done2/  logs2/  gen2/  rows2/  pids2/  workers2/
#   results2.d/  ledger2.csv        engine: dlx7g_v21.exe
# Never touches any process it did not itself start.
$ROOT = "F:\superpermFarm\trackc2"
$JOBS = "$ROOT\jobs2.txt"
$EXE  = "$ROOT\dlx7g_v21.exe"
$me   = $PID

New-Item -ItemType Directory -Force -Path `
  "$ROOT\claims2","$ROOT\done2","$ROOT\logs2","$ROOT\gen2","$ROOT\rows2", `
  "$ROOT\results2.d","$ROOT\pids2","$ROOT\workers2" | Out-Null
Set-Content -Path "$ROOT\workers2\$me.alive" -Value ("gen2 " + (Get-Date -Format o))

$lines = @(Get-Content $JOBS | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") })

foreach ($line in $lines) {
    $p     = $line.Split("|")
    $jid   = $p[0].Trim()
    $inst  = $p[1].Trim()
    $extra = $p[2].Trim()
    if (Test-Path "$ROOT\done2\$jid.done") { continue }

    # atomic claim: CreateNew throws if another worker got here first
    $claim = "$ROOT\claims2\$jid.claim"
    try {
        $fs = [System.IO.File]::Open($claim, [System.IO.FileMode]::CreateNew,
                                     [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $sw = New-Object System.IO.StreamWriter($fs)
        $sw.WriteLine("$me")
        $sw.Close(); $fs.Close()
    } catch { continue }
    if (Test-Path "$ROOT\done2\$jid.done") { Remove-Item $claim -Force -EA SilentlyContinue; continue }

    $eargs = @("$ROOT\inst\$inst", "--out", "$ROOT\rows2\$jid.rows")
    if ($extra -ne "") { $eargs += ($extra -split "\s+") }
    $log = "$ROOT\logs2\$jid.log"
    $err = "$ROOT\logs2\$jid.err"
    $t0  = Get-Date
    $rc  = -1
    try {
        $proc = Start-Process -FilePath $EXE -ArgumentList $eargs -NoNewWindow -PassThru `
                  -WorkingDirectory $ROOT -RedirectStandardOutput $log -RedirectStandardError $err
        $null = $proc.Handle   # PS quirk: caches the handle so .ExitCode is populated
        Set-Content -Path "$ROOT\pids2\$jid.pid" -Value $proc.Id
        $proc.WaitForExit()
        $rc = $proc.ExitCode
        if ($null -eq $rc) { $rc = -1 }
    } catch {
        Set-Content -Path "$err" -Value ("LAUNCH FAILED: " + $_.Exception.Message)
    }
    $secs = [int]((Get-Date) - $t0).TotalSeconds

    $verdict = "ERROR-$rc"
    switch ($rc) { 0 { $verdict = "SAT-CANDIDATE" } 2 { $verdict = "EXHAUSTED" } 3 { $verdict = "TIMEOUT" } }
    $nodes = ""; $maxd = ""; $probes = ""; $precs = ""; $pnodes = ""
    if (Test-Path $err) {
        $rl = @(Select-String -Path $err -Pattern "^RESULT " -EA SilentlyContinue)
        if ($rl.Count -gt 0) {
            $t = $rl[-1].Line
            # the engine's own RESULT line is authoritative; rc is the fallback
            if ($t -match "^RESULT (\w+)")  { $verdict = $Matches[1] }
            if ($t -match "nodes=(\d+)")    { $nodes = $Matches[1] }
            if ($t -match "maxdepth=(\d+)") { $maxd  = $Matches[1] }
        }
        $al = @(Select-String -Path $err -Pattern "probes=" -EA SilentlyContinue)
        if ($al.Count -gt 0) {
            $t = $al[-1].Line
            if ($t -match "probes=(\d+)")      { $probes = $Matches[1] }
            if ($t -match "probe_recs=(\d+)")  { $precs  = $Matches[1] }
            if ($t -match "probe_nodes=(\d+)") { $pnodes = $Matches[1] }
        }
    }
    if ($verdict -eq "SOLVED") { $verdict = "SAT-CANDIDATE" }
    $jl = "$ROOT\gen2\" + ($jid -replace "^g2_","") + ".jsonl"
    $mb = 0
    if (Test-Path $jl) { $mb = [math]::Round((Get-Item $jl).Length / 1MB, 1) }
    $row = "$jid,$inst,$verdict,$rc,$nodes,$maxd,$secs,$probes,$precs,$pnodes,$mb,$me"

    Set-Content -Path "$ROOT\results2.d\$jid.csv" -Value $row
    for ($k = 0; $k -lt 100; $k++) {
        try {
            $lf = [System.IO.File]::Open("$ROOT\ledger2.csv", [System.IO.FileMode]::Append,
                                         [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
            $lw = New-Object System.IO.StreamWriter($lf)
            $lw.WriteLine($row); $lw.Close(); $lf.Close(); break
        } catch { Start-Sleep -Milliseconds 100 }
    }
    Set-Content -Path "$ROOT\done2\$jid.done" -Value $row
    Remove-Item $claim -Force -EA SilentlyContinue
    if ($verdict -eq "SAT-CANDIDATE") {
        Add-Content -Path "$ROOT\ALERT.txt" -Value "SAT CANDIDATE $jid (gen2) -- validate on the Mac before believing"
    }
}

Remove-Item "$ROOT\workers2\$me.alive" -Force -EA SilentlyContinue
