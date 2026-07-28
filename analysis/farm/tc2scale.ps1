# tc2scale.ps1 -- start/backfill the Track C v2 GENERATION sweep to $TARGET live
# workers (satscale.ps1 pattern).  Idempotent and resumable: finished jobs have
# done-markers and are never re-run; claims owned by dead pids are released.
# Launches through detach.exe so workers survive ssh disconnect.
$TARGET = 20                       # <-- generation worker count, single knob
$FARM   = "F:\superpermFarm"
$ROOT   = "$FARM\trackc2"
$CMD    = "$env:SystemRoot\System32\cmd.exe"   # detach.exe cannot launch powershell.exe
                                             # directly (no console -> silent exit); cmd /c <bat> can.

New-Item -ItemType Directory -Force -Path `
  "$ROOT\claims","$ROOT\done","$ROOT\logs","$ROOT\gen","$ROOT\rows", `
  "$ROOT\results.d","$ROOT\pids","$ROOT\workers","$ROOT\wlogs" | Out-Null

# 1. release stale claims (claim file present, no done marker, owner pid dead)
$released = 0
Get-ChildItem "$ROOT\claims" -Filter *.claim -EA SilentlyContinue | ForEach-Object {
    $jid = $_.BaseName
    if (Test-Path "$ROOT\done\$jid.done") { Remove-Item $_.FullName -Force -EA SilentlyContinue; return }
    $owner = 0
    try { $owner = [int]((Get-Content $_.FullName -TotalCount 1).Trim()) } catch { $owner = 0 }
    if ($owner -eq 0 -or -not (Get-Process -Id $owner -EA SilentlyContinue)) {
        Remove-Item $_.FullName -Force -EA SilentlyContinue; $released++
    }
}

# 2. how much work is left
$jobs    = @(Get-Content "$ROOT\jobs.txt" | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") })
# generation-only counts (the done/claims dirs are shared with the eval pool)
$done    = @(Get-ChildItem "$ROOT\done"   -Filter *.done  -EA SilentlyContinue | Where-Object { $_.Name -notlike "*_evalblind.done"  }).Count
$claimed = @(Get-ChildItem "$ROOT\claims" -Filter *.claim -EA SilentlyContinue | Where-Object { $_.Name -notlike "*_evalblind.claim" }).Count
$pending = $jobs.Count - $done - $claimed
if ($pending -lt 0) { $pending = 0 }

# 3. live generation workers
$alive = 0
Get-ChildItem "$ROOT\workers" -Filter *.alive -EA SilentlyContinue | ForEach-Object {
    $wpid = 0
    try { $wpid = [int]($_.BaseName) } catch { $wpid = 0 }
    if ($wpid -gt 0 -and (Get-Process -Id $wpid -EA SilentlyContinue)) {
        if ((Get-Content $_.FullName -TotalCount 1) -like "gen*") { $alive++ }
    } else { Remove-Item $_.FullName -Force -EA SilentlyContinue }
}

$need = [math]::Min([math]::Max($TARGET - $alive, 0), $pending)
Write-Output "stale_claims_released=$released jobs=$($jobs.Count) done=$done claimed=$claimed pending=$pending gen_workers_alive=$alive target=$TARGET launching=$need"

for ($i = 0; $i -lt $need; $i++) {
    $stamp = (Get-Date -Format "HHmmss") + "_$i"
    $out = & "$FARM\detach.exe" $ROOT "$ROOT\wlogs\gw_$stamp.log" "$ROOT\wlogs\gw_$stamp.err" `
             $CMD "/c" "$ROOT\tc2runw.bat"
    Write-Output "  gen worker $i -> $out"
    Start-Sleep -Milliseconds 300
}
Write-Output "tc2scale done"
