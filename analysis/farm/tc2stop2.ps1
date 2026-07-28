# tc2stop2.ps1 -- stop ONLY the Track C v2.1 GEN2 sweep.
# Kills exactly the pids THIS sweep recorded: engine pids in trackc2\pids2\*.pid
# (process name must be dlx7g_v21) and worker pids in trackc2\workers2\*.alive
# (process name must be powershell).  It NEVER enumerates python or any other
# process class -- the user's transcription service and F:\audioPrime must not
# be touched (analysis/cover7/REMOTE-FARM.md).  Sweep-1's pids/ and workers/ are
# never read, so a running sweep-1 is unaffected.
# Done-markers and ledger2 are left intact, so tc2scale2.ps1 resumes cleanly.
$ROOT = "F:\superpermFarm\trackc2"

$killed = 0
Get-ChildItem "$ROOT\workers2" -Filter *.alive -EA SilentlyContinue | ForEach-Object {
    $wpid = 0
    try { $wpid = [int]($_.BaseName) } catch { $wpid = 0 }
    $p = if ($wpid -gt 0) { Get-Process -Id $wpid -EA SilentlyContinue } else { $null }
    if ($p -and $p.ProcessName -eq "powershell") {
        Write-Output "stopping gen2 worker pid $wpid"
        Stop-Process -Id $wpid -Force -EA SilentlyContinue; $killed++
    }
    Remove-Item $_.FullName -Force -EA SilentlyContinue
}
Get-ChildItem "$ROOT\pids2" -Filter *.pid -EA SilentlyContinue | ForEach-Object {
    $jid = $_.BaseName
    $epid = 0
    try { $epid = [int]((Get-Content $_.FullName -TotalCount 1).Trim()) } catch { $epid = 0 }
    $p = if ($epid -gt 0) { Get-Process -Id $epid -EA SilentlyContinue } else { $null }
    if ($p -and $p.ProcessName -eq "dlx7g_v21") {
        Write-Output "stopping gen2 engine pid $epid ($jid)"
        Stop-Process -Id $epid -Force -EA SilentlyContinue; $killed++
    }
    Remove-Item $_.FullName -Force -EA SilentlyContinue
}
# release claims for jobs that never finished, so a rerun picks them up
Get-ChildItem "$ROOT\claims2" -Filter *.claim -EA SilentlyContinue | ForEach-Object {
    if (-not (Test-Path ("$ROOT\done2\" + $_.BaseName + ".done"))) {
        Remove-Item $_.FullName -Force -EA SilentlyContinue
    }
}
Write-Output "tc2stop2 done; $killed process(es) stopped (only gen2-owned pids)"
