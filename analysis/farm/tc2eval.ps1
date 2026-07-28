# tc2eval.ps1 -- launch/backfill the Track C v2 EVAL blind baselines (G2v2).
# 6 chains, blind, --time-limit 3600 --mrv-stats, stderr captured.  One worker
# per job; idempotent (done-markers + stale-claim release).  Runs alongside the
# generation sweep: 6 here + tc2scale's 20 = 26 <= the 27-worker cap.
$FARM   = "F:\superpermFarm"
$ROOT   = "$FARM\trackc2"
$CMD    = "$env:SystemRoot\System32\cmd.exe"   # detach.exe cannot launch powershell.exe
                                             # directly (no console -> silent exit); cmd /c <bat> can.

New-Item -ItemType Directory -Force -Path `
  "$ROOT\claims","$ROOT\done","$ROOT\logs","$ROOT\rows", `
  "$ROOT\results.d","$ROOT\pids","$ROOT\workers","$ROOT\wlogs" | Out-Null

Get-ChildItem "$ROOT\claims" -Filter *.claim -EA SilentlyContinue | ForEach-Object {
    $jid = $_.BaseName
    if ($jid -notlike "*_evalblind") { return }
    if (Test-Path "$ROOT\done\$jid.done") { Remove-Item $_.FullName -Force -EA SilentlyContinue; return }
    $owner = 0
    try { $owner = [int]((Get-Content $_.FullName -TotalCount 1).Trim()) } catch { $owner = 0 }
    if ($owner -eq 0 -or -not (Get-Process -Id $owner -EA SilentlyContinue)) {
        Remove-Item $_.FullName -Force -EA SilentlyContinue
        Write-Output "released stale claim $jid"
    }
}

$jobs    = @(Get-Content "$ROOT\evaljobs.txt" | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") })
$done    = @(Get-ChildItem "$ROOT\done" -Filter *_evalblind.done -EA SilentlyContinue).Count
$claimed = @(Get-ChildItem "$ROOT\claims" -Filter *_evalblind.claim -EA SilentlyContinue).Count
$pending = $jobs.Count - $done - $claimed
if ($pending -lt 0) { $pending = 0 }

$alive = 0
Get-ChildItem "$ROOT\workers" -Filter *.alive -EA SilentlyContinue | ForEach-Object {
    $wpid = 0
    try { $wpid = [int]($_.BaseName) } catch { $wpid = 0 }
    if ($wpid -gt 0 -and (Get-Process -Id $wpid -EA SilentlyContinue)) {
        if ((Get-Content $_.FullName -TotalCount 1) -like "eval*") { $alive++ }
    }
}
$need = [math]::Min([math]::Max($jobs.Count - $alive, 0), $pending)
Write-Output "eval jobs=$($jobs.Count) done=$done claimed=$claimed pending=$pending eval_workers_alive=$alive launching=$need"

for ($i = 0; $i -lt $need; $i++) {
    $stamp = (Get-Date -Format "HHmmss") + "_$i"
    $out = & "$FARM\detach.exe" $ROOT "$ROOT\wlogs\ev_$stamp.log" "$ROOT\wlogs\ev_$stamp.err" `
             $CMD "/c" "$ROOT\tc2rune.bat"
    Write-Output "  eval worker $i -> $out"
    Start-Sleep -Milliseconds 400
}
Write-Output "tc2eval done"
