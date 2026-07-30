# talaunch.ps1 -- sharded tail-atsp corpus sweep on the farm PC.
#
# The corpus (data/upstream872, 22,062 walks) is pre-split into
# F:\superpermFarm\tailatsp\shards\s00..s23 (round-robin, so heavy-tail
# instances spread evenly). One single-threaded superperm.exe per shard, so a
# 24-core sweep costs wall = single-core-time / 24. The exe is cross-compiled
# on the Mac (x86_64-pc-windows-gnu, crt-static; no Rust toolchain on the PC)
# and shipped with scp -- rebuild+reship after any src/tailatsp.rs change.
#
# Workers go through detach.exe (survive ssh disconnect, BELOW_NORMAL priority
# so the transcription service keeps its cores). The heartbeat supervisor
# (tasuper.ps1) ships WITH the launch per docs/OPERATIONS.md.
#
# usage (from anywhere on the PC):
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\tailatsp\talaunch.ps1 `
#     -Anchor 450 -MaxBlocks 50 -Workers 24
param(
  [int]$Anchor    = 450,
  [int]$MaxBlocks = 50,
  [int]$Workers   = 24,
  [string]$Tag    = "",
  [switch]$Ties,
  [int]$TieCap    = 64,
  [switch]$Merge,            # I2a: try every single same-cycle block merge too
  [switch]$Recomp,           # recomp-1: every single-cycle recomposition (subsumes merge)
  [int]$Limit     = 0        # per-shard walk cap; 0 = whole shard (sizing probes)
)
$ErrorActionPreference = "Stop"

$FARM   = "F:\superpermFarm"
$ROOT   = "$FARM\tailatsp"
$EXE    = "$ROOT\superperm.exe"
$DETACH = "$FARM\detach.exe"
$CMD    = "$env:SystemRoot\System32\cmd.exe"   # detach.exe cannot launch powershell.exe directly

if ($Tag -eq "") {
  $Tag = "a$Anchor" + "b$MaxBlocks"
  if ($Ties)       { $Tag += "-ties" }
  if ($Merge)      { $Tag += "-merge" }
  if ($Recomp)     { $Tag += "-recomp" }
  if ($Limit -gt 0){ $Tag += "-L$Limit" }
}
$run = "$ROOT\runs\$Tag"

foreach ($f in @($EXE, $DETACH, "$ROOT\tasuper.ps1", "$ROOT\tasuper.bat")) {
  if (-not (Test-Path $f)) { throw "missing prerequisite: $f" }
}

# --- the s28 duplicate-launch trap: never start on top of survivors ---------
$live = @(Get-Process -Name superperm -ErrorAction SilentlyContinue)
if ($live.Count -gt 0) {
  throw "REFUSING TO LAUNCH: $($live.Count) superperm.exe already alive. Run tastatus.ps1, then tastop.ps1."
}
if (Test-Path $run) {
  throw "REFUSING TO LAUNCH: run dir already exists ($run). Pick another -Tag."
}

New-Item -ItemType Directory -Force -Path "$run\logs","$run\pids","$run\finds" | Out-Null

# --- worklist: one shard per worker, real walk counts for the ETA -----------
$total = 0
$shards = @()
for ($i = 0; $i -lt $Workers; $i++) {
  $nn = "{0:d2}" -f $i
  $sd = "$ROOT\shards\s$nn"
  if (-not (Test-Path $sd)) { throw "missing shard $sd" }
  $c = @(Get-ChildItem $sd -File).Count
  if ($Limit -gt 0 -and $Limit -lt $c) { $c = $Limit }
  $shards += @{ nn = $nn; dir = $sd; count = $c }
  $total += $c
}

$spec = @(
  "tag:        $Tag",
  "spec:       superperm.exe tail-atsp -n 6 --dirs shards\sNN --anchor $Anchor --max-blocks $MaxBlocks" +
    $(if ($Ties) { " --ties --tie-cap $TieCap" } else { "" }) +
    $(if ($Merge) { " --merge" } else { "" }) +
    $(if ($Recomp) { " --recomp" } else { "" }) +
    $(if ($Limit -gt 0) { " --limit $Limit" } else { "" }),
  "workers:    $Workers (one shard each, BELOW_NORMAL)",
  "walks:      $total",
  "run dir:    $run",
  "finds:      $run\finds\wNN   (improvements AND new-allocation ties land here)",
  "abort:      powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\tastop.ps1 -Tag $Tag",
  "status:     powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\tastatus.ps1 -Tag $Tag",
  "launched:   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
)
$spec | Set-Content "$run\SPEC.txt"
# Columns are fixed for the life of a run file (s19 lesson: never change ledger
# column semantics mid-file). merge_* are 0 unless -Merge was passed.
"worker,shard,rc,verdict,walks,optimal,improved,skipped,ties,merge_moves,merge_improved,merge_equal,rc_moves,rc_improved,rc_eq_new,rc_eq_same,secs,finished" |
  Set-Content "$run\ledger.csv"

# --- launch ----------------------------------------------------------------
foreach ($s in $shards) {
  $nn = $s.nn
  $a = @("tail-atsp","-n","6","--dirs","$ROOT\shards\s$nn",
         "--anchor","$Anchor","--max-blocks","$MaxBlocks",
         "--out-dir","$run\finds\w$nn")
  if ($Ties)        { $a += @("--ties","--tie-cap","$TieCap") }
  if ($Merge)       { $a += @("--merge") }
  if ($Recomp)      { $a += @("--recomp") }
  if ($Limit -gt 0) { $a += @("--limit","$Limit") }

  $res = & $DETACH $ROOT "$run\logs\w$nn.log" "$run\logs\w$nn.err" $EXE @a
  $wpid = 0
  if ("$res" -match 'pid\s+(\d+)') { $wpid = [int]$Matches[1] }
  if ($wpid -eq 0) { Write-Output "  w$nn LAUNCH FAILED: $res"; continue }

  # pid + name + start time: PIDs are recycled on this box (s19 lesson), so the
  # stop script must be able to confirm identity before killing anything.
  $p = Get-Process -Id $wpid -ErrorAction SilentlyContinue
  $st = ""
  if ($p) { $st = $p.StartTime.ToString("o") }
  "$wpid`t superperm`t $st`t s$nn" | Set-Content "$run\pids\w$nn.txt"
  Write-Output "  w$nn shard s$nn walks=$($s.count) pid=$wpid"
  Start-Sleep -Milliseconds 150
}

# --- heartbeat supervisor (detached; writes its own files, never stdout) ----
$sres = & $DETACH $ROOT "$run\logs\super.log" "$run\logs\super.err" `
          $CMD "/c" "$ROOT\tasuper.bat" $Tag $Workers $total
Write-Output "supervisor -> $sres"

Write-Output ""
Write-Output ($spec -join "`n")
