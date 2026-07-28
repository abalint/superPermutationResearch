# satscale.ps1 -- start/backfill the cover farm to $TARGET live workers.
# Idempotent: counts live satworker.py processes and launches only the shortfall.
# Workers are launched through detach.exe so they survive ssh disconnect.
$TARGET = 27                       # <-- worker count, single knob
$ROOT   = "F:\superpermFarm"
$LOGS   = "$ROOT\satlogs"
$PY     = "C:\Program Files\Python311\python.exe"

New-Item -ItemType Directory -Force -Path $LOGS, "$ROOT\results.d", "$ROOT\claims", "$ROOT\satruns", "$ROOT\workers" | Out-Null

# Count liveness markers whose pid is still running (WMI is Access-denied here).
$alive = 0
Get-ChildItem "$ROOT\workers" -Filter *.alive -ErrorAction SilentlyContinue | ForEach-Object {
    $wpid = [int]($_.BaseName)
    if (Get-Process -Id $wpid -ErrorAction SilentlyContinue) { $alive++ }
    else { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
}
$need  = [math]::Max($TARGET - $alive, 0)
Write-Output "alive=$alive target=$TARGET launching=$need"

for ($i = 0; $i -lt $need; $i++) {
    $stamp = (Get-Date -Format "HHmmss") + "_$i"
    & "$ROOT\detach.exe" $ROOT "$LOGS\w_$stamp.log" "$LOGS\w_$stamp.err" $PY "$ROOT\satworker.py" | Out-Null
    Start-Sleep -Milliseconds 250
}
Write-Output "satscale done"
