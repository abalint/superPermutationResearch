# tc2gate_v21.ps1 -- BUILD GATE for the v2.1 binary dlx7g_v21.exe.
# (a) blind on chain 26 MUST print RESULT EXHAUSTED nodes=8548527 (design sec.8 risk 4)
# (b) a small probe run on chain 82 must emit JSONL with "shash" and "probe" keys
# Read-only w.r.t. the in-flight sweep-1: separate binary, separate output paths.
$ROOT = "F:\superpermFarm\trackc2"
$EXE  = "$ROOT\dlx7g_v21.exe"
$err  = "$ROOT\gate21_wl026.err"
$log  = "$ROOT\gate21_wl026.log"
Remove-Item $err,$log -Force -EA SilentlyContinue

$t0 = Get-Date
$p = Start-Process -FilePath $EXE -ArgumentList @("$ROOT\inst\wl_026.txt","--time-limit","3600") `
       -NoNewWindow -PassThru -WorkingDirectory $ROOT -RedirectStandardOutput $log -RedirectStandardError $err
$null = $p.Handle
$p.WaitForExit()
$rc = $p.ExitCode
$secs = [int]((Get-Date) - $t0).TotalSeconds
$line = (Select-String -Path $err -Pattern "^RESULT " | Select-Object -Last 1).Line
Write-Output "GATE-A rc=$rc secs=$secs"
Write-Output "GATE-A stderr RESULT: $line"
$nodes = ""
if ($line -match "nodes=(\d+)") { $nodes = $Matches[1] }
if ($rc -eq 2 -and $nodes -eq "8548527") {
    Write-Output "GATE-A PASS  chain 26 EXHAUSTED nodes=8548527"
} else {
    Write-Output "GATE-A FAIL  expected rc=2 nodes=8548527, got rc=$rc nodes=$nodes -- DO NOT LAUNCH"
}

# ---- GATE B: probe smoke on wl_082 -------------------------------------
$jl   = "$ROOT\gate21_wl082.jsonl"
$errB = "$ROOT\gate21_wl082.err"
$logB = "$ROOT\gate21_wl082.log"
Remove-Item $jl,$errB,$logB -Force -EA SilentlyContinue
$t1 = Get-Date
$pb = Start-Process -FilePath $EXE -ArgumentList @("$ROOT\inst\wl_082.txt",
        "--col-epsilon","0.15","--col-seed","1","--probe-rate","0.02","--probe-cap","20000",
        "--time-limit","600","--log-subtrees",$jl) `
       -NoNewWindow -PassThru -WorkingDirectory $ROOT -RedirectStandardOutput $logB -RedirectStandardError $errB
$null = $pb.Handle
$pb.WaitForExit()
$rcB = $pb.ExitCode
$secsB = [int]((Get-Date) - $t1).TotalSeconds
$lineB = (Select-String -Path $errB -Pattern "^RESULT " | Select-Object -Last 1).Line
Write-Output "GATE-B rc=$rcB secs=$secsB"
Write-Output "GATE-B stderr RESULT: $lineB"
$att = (Select-String -Path $errB -Pattern "probe" | Select-Object -Last 1).Line
Write-Output "GATE-B attempt line: $att"
if (Test-Path $jl) {
    $sz = (Get-Item $jl).Length
    $all = @(Get-Content $jl)
    $n = $all.Count
    $bad = 0; $withShash = 0; $withProbe = 0
    foreach ($l in $all) {
        try { $o = $l | ConvertFrom-Json } catch { $bad++; continue }
        if ($o.PSObject.Properties.Name -contains "shash") { $withShash++ }
        if ($o.PSObject.Properties.Name -contains "probe") { $withProbe++ }
    }
    Write-Output ("GATE-B jsonl bytes={0} records={1} parse_fail={2} with_shash={3} with_probe={4}" -f $sz,$n,$bad,$withShash,$withProbe)
    Write-Output ("GATE-B first record: " + $all[0])
    $pr = $all | Where-Object { $_ -like '*"probe"*' } | Select-Object -First 1
    Write-Output ("GATE-B first probe record: " + $pr)
    if ($bad -eq 0 -and $n -gt 0 -and $withShash -eq $n -and $withProbe -gt 0) {
        Write-Output "GATE-B PASS  all records parse, all carry shash, probe records present"
    } else {
        Write-Output "GATE-B FAIL"
    }
} else { Write-Output "GATE-B FAIL  no jsonl written" }
