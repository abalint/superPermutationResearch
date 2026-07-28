# tc2stop.ps1 -- stop ONLY the Track C v2 sweep.
# Kills exactly the pids this sweep recorded: engine pids in trackc2\pids\*.pid
# and worker pids in trackc2\workers\*.alive.  It NEVER enumerates python or any
# other process class -- the user's transcription service and F:\audioPrime must
# not be touched (see analysis/cover7/REMOTE-FARM.md).
# Done-markers and ledger are left intact, so tc2scale.ps1 resumes cleanly.
$ROOT = "F:\superpermFarm\trackc2"

$killed = 0
Get-ChildItem "$ROOT\workers" -Filter *.alive -EA SilentlyContinue | ForEach-Object {
    $wpid = 0
    try { $wpid = [int]($_.BaseName) } catch { $wpid = 0 }
    $p = if ($wpid -gt 0) { Get-Process -Id $wpid -EA SilentlyContinue } else { $null }
    if ($p -and $p.ProcessName -eq "powershell") {
        Write-Output "stopping worker pid $wpid"
        Stop-Process -Id $wpid -Force -EA SilentlyContinue; $killed++
    }
    Remove-Item $_.FullName -Force -EA SilentlyContinue
}
Get-ChildItem "$ROOT\pids" -Filter *.pid -EA SilentlyContinue | ForEach-Object {
    $jid = $_.BaseName
    $epid = 0
    try { $epid = [int]((Get-Content $_.FullName -TotalCount 1).Trim()) } catch { $epid = 0 }
    $p = if ($epid -gt 0) { Get-Process -Id $epid -EA SilentlyContinue } else { $null }
    if ($p -and $p.ProcessName -eq "dlx7g") {
        Write-Output "stopping engine pid $epid ($jid)"
        Stop-Process -Id $epid -Force -EA SilentlyContinue; $killed++
    }
    Remove-Item $_.FullName -Force -EA SilentlyContinue
}
# release claims for jobs that never finished, so a rerun picks them up
Get-ChildItem "$ROOT\claims" -Filter *.claim -EA SilentlyContinue | ForEach-Object {
    if (-not (Test-Path ("$ROOT\done\" + $_.BaseName + ".done"))) {
        Remove-Item $_.FullName -Force -EA SilentlyContinue
    }
}
Write-Output "tc2stop done; $killed process(es) stopped (only sweep-owned pids)"
