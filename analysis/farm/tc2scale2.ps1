# tc2scale2.ps1 -- start/backfill the Track C v2.1 GEN2 sweep to $TARGET live
# workers (tc2scale.ps1 pattern).  Idempotent and resumable: finished jobs have
# done-markers in done2\ and are never re-run; claims owned by dead pids are
# released.  Launches through detach.exe so workers survive ssh disconnect.
# Uses ONLY the gen2 state dirs -- sweep-1's pool is never read or written.
$TARGET = 20                       # <-- gen2 worker count, single knob
$FARM   = "F:\superpermFarm"
$ROOT   = "$FARM\trackc2"
$CMD    = "$env:SystemRoot\System32\cmd.exe"   # detach.exe cannot launch powershell.exe
                                               # directly (no console -> silent exit); cmd /c <bat> can.

New-Item -ItemType Directory -Force -Path `
  "$ROOT\claims2","$ROOT\done2","$ROOT\logs2","$ROOT\gen2","$ROOT\rows2", `
  "$ROOT\results2.d","$ROOT\pids2","$ROOT\workers2","$ROOT\wlogs2" | Out-Null

# 1. release stale claims (claim file present, no done marker, owner pid dead)
$released = 0
Get-ChildItem "$ROOT\claims2" -Filter *.claim -EA SilentlyContinue | ForEach-Object {
    $jid = $_.BaseName
    if (Test-Path "$ROOT\done2\$jid.done") { Remove-Item $_.FullName -Force -EA SilentlyContinue; return }
    $owner = 0
    try { $owner = [int]((Get-Content $_.FullName -TotalCount 1).Trim()) } catch { $owner = 0 }
    if ($owner -eq 0 -or -not (Get-Process -Id $owner -EA SilentlyContinue)) {
        Remove-Item $_.FullName -Force -EA SilentlyContinue; $released++
    }
}

# 2. how much work is left
$jobs    = @(Get-Content "$ROOT\jobs2.txt" | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") })
$done    = @(Get-ChildItem "$ROOT\done2"   -Filter *.done  -EA SilentlyContinue).Count
$claimed = @(Get-ChildItem "$ROOT\claims2" -Filter *.claim -EA SilentlyContinue).Count
$pending = $jobs.Count - $done - $claimed
if ($pending -lt 0) { $pending = 0 }

# 3. live gen2 workers
$alive = 0
Get-ChildItem "$ROOT\workers2" -Filter *.alive -EA SilentlyContinue | ForEach-Object {
    $wpid = 0
    try { $wpid = [int]($_.BaseName) } catch { $wpid = 0 }
    if ($wpid -gt 0 -and (Get-Process -Id $wpid -EA SilentlyContinue)) { $alive++ }
    else { Remove-Item $_.FullName -Force -EA SilentlyContinue }
}

$need = [math]::Min([math]::Max($TARGET - $alive, 0), $pending)
Write-Output "stale_claims_released=$released jobs=$($jobs.Count) done=$done claimed=$claimed pending=$pending gen2_workers_alive=$alive target=$TARGET launching=$need"

for ($i = 0; $i -lt $need; $i++) {
    $stamp = (Get-Date -Format "HHmmss") + "_$i"
    $out = & "$FARM\detach.exe" $ROOT "$ROOT\wlogs2\g2w_$stamp.log" "$ROOT\wlogs2\g2w_$stamp.err" `
             $CMD "/c" "$ROOT\tc2runw2.bat"
    Write-Output "  gen2 worker $i -> $out"
    Start-Sleep -Milliseconds 300
}
Write-Output "tc2scale2 done"
