# untargeted_run.ps1 -- launch the 24-way s49 fused-pair UNTARGETED sweep on
# the farm PC.  This is the operator entry point; the pool itself is managed by
# the detached supervisor (untargeted_super.ps1), which ships WITH the launch
# as docs/OPERATIONS.md requires.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\untargeted_run.ps1 -Tag u1
#   ... -Limit 4          smoke test: 4 intermediates per shard
#   ... -DryRun           sizing only (instrument's --dry-run)
#   ... -Workers 8        bounded pool smaller than the shard count
#   ... -Stub             supervise 24 trivial python stubs instead of the
#                         instrument (mechanics test -- see untargeted_stub.py)
#
# Pre-launch arithmetic (docs/OPERATIONS.md, non-negotiable, restated in
# SPEC.txt).  AS-BUILT sizing, which is far smaller than the SWEEP-QUEUE
# projection (that was sizing_untargeted.py's 33 h single-core / 1.4 h at
# 24-way): ~81 min single-core TOTAL across all 24 shards, largest shard ~6 min
# solo; replay 0.73 ms, rescan 0.11 s; 184 MB RSS per shard measured.  So 24
# shards => a few minutes wall and ~4.4 GB of 48 GB.  The 250 MB/shard used in
# the RAM check below is the conservative figure.  4 cores are left for the
# user's transcription service and every shard runs BELOW_NORMAL (detach.exe).
# Because most shards finish in minutes, the stall window defaults to 5 min:
# a silent STATUS for that long means dead, not slow.  Abort command below.
param(
  [string]$Tag          = "",
  [int]$Shards          = 24,
  [int]$Workers         = 24,
  [string]$Mode         = "untargeted",   # the fuse.py subcommand
  [int]$Limit           = 0,
  [switch]$DryRun,
  [int]$StallMinutes    = 5,     # as-built: most shards finish in minutes
  [int]$Total           = 10786,          # projected intermediates, corpus-wide
  [string]$ExtraArgs    = "",             # verbatim passthrough to fuse.py
  [int]$TickSeconds     = 30,
  [switch]$Stub,                          # supervise stubs, not the instrument
  [switch]$Force                          # skip the idle refusal (never routine)
)
$ErrorActionPreference = "Stop"

$ROOT   = "F:\superpermFarm\untargeted"
$REPO   = "$ROOT\repo"
$PY     = "$ROOT\pyenv\Scripts\upyw.exe"
$FUSE   = "$REPO\analysis\counting\s49\fuse.py"
$DETACH = "F:\superpermFarm\detach.exe"
$CMD    = "$env:SystemRoot\System32\cmd.exe"

if ($Tag -eq "") {
  $Tag = "u$(Get-Date -Format 'MMddHHmm')"
  if ($Limit -gt 0) { $Tag += "L$Limit" }
  if ($DryRun)      { $Tag += "dry" }
  if ($Stub)        { $Tag += "stub" }
}
# detach.exe joins argv with single spaces -> nothing downstream may contain one
if ($Tag -match '\s') { throw "tag must not contain whitespace: '$Tag'" }
$run = "$ROOT\runs\$Tag"

# --- prerequisites ----------------------------------------------------------
$need = @($DETACH, $PY, "$ROOT\untargeted_super.ps1", "$ROOT\untargeted_super.bat")
if (-not $Stub) { $need += $FUSE } else { $need += "$ROOT\untargeted_stub.py" }
foreach ($f in $need) { if (-not (Test-Path $f)) { throw "missing prerequisite: $f" } }

# --- refusals (the s28 duplicate-launch trap) -------------------------------
$live = @(Get-Process -Name upyw -ErrorAction SilentlyContinue)
if ($live.Count -gt 0 -and -not $Force) {
  throw "REFUSING TO LAUNCH: $($live.Count) upyw.exe already alive. Run untargeted_status.ps1, then untargeted_abort.ps1."
}
if (Test-Path $run) { throw "REFUSING TO LAUNCH: run dir already exists ($run). Pick another -Tag." }

# RAM headroom: 24 shards x ~250 MB measured, plus the OS and the user's
# transcription service.  WMI is Access-denied for this account, so this uses
# the GlobalMemoryStatusEx P/Invoke in meminfo.ps1.
if (Test-Path "$ROOT\meminfo.ps1") {
  . "$ROOT\meminfo.ps1"
  $m = Get-FarmMem
  $needMB = $Workers * 250 + 2000
  Write-Output "RAM: $($m.AvailMB) MB available of $($m.TotalMB) MB; this run wants ~$needMB MB"
  if ($m.AvailMB -lt $needMB -and -not $Force) {
    throw "REFUSING TO LAUNCH: only $($m.AvailMB) MB available, need ~$needMB MB. (-Force to override.)"
  }
}

New-Item -ItemType Directory -Force -Path "$run\logs","$run\pids","$run\out" | Out-Null

# --- the supervisor's parameters, as a FILE (never as mangled argv) ---------
@(
  "Shards=$Shards",
  "Workers=$Workers",
  "Mode=$Mode",
  "Limit=$Limit",
  "DryRunMode=$(if ($DryRun) { 1 } else { 0 })",
  "StallMinutes=$StallMinutes",
  "Total=$Total",
  "ExtraArgs=$ExtraArgs",
  "TickSeconds=$TickSeconds",
  "Stub=$(if ($Stub) { 1 } else { 0 })"
) | Set-Content "$run\PARAMS.txt"

$cmdline = "$PY -u $FUSE $Mode --shard <i>/$Shards --out $run\out\sNN"
if ($Stub) { $cmdline = "$PY -u $ROOT\untargeted_stub.py --shard <i>/$Shards --out $run\out\sNN" }
if ($Limit -gt 0) { $cmdline += " --limit $Limit" }
if ($DryRun)      { $cmdline += " --dry-run" }
if ($ExtraArgs -ne "") { $cmdline += " $ExtraArgs" }

$spec = @(
  "tag:         $Tag",
  "what:        s49 item1 fused-pair UNTARGETED sweep on the 12-class blind spot",
  "             (docs/SWEEP-QUEUE.md '## fused-pair UNTARGETED sweep on the blind spot';",
  "              canon gate must target the 220-class project shell -- s51 re-scope)",
  "spec:        $cmdline",
  "workdir:     $REPO   (repo-root mirror; the s49 family does relative",
  "             sys.path.insert(0,'analysis/counting'), so cwd matters)",
  "interpreter: $PY  (renamed venv python -- process-identity guard so aborting",
  "             this sweep can never touch the transcription service's python.exe)",
  "shards:      $Shards, pool $Workers concurrent, BELOW_NORMAL via detach.exe",
  "runtime:     AS-BUILT ~81 min single-core TOTAL over all $Shards shards (largest",
  "             shard ~6 min solo) => minutes of wall clock at $Workers-way. There is no",
  "             per-shard time cap in the instrument, so the bounded worst case is",
  "             open-ended -- that is what the ${StallMinutes}m stall flag is for.",
  "footprint:   184 MB RSS/shard measured; budgeted at 250 => ~$($Workers * 250) MB of 48 GB",
  "produces:    $run\out\sNN\  (stats.tsv, edges.tsv, summary.tsv, STATUS heartbeat)",
  "escapes:     STATUS rows tagged ESCAPE / MIDESCAPE / SHORTER are the target",
  "             event; the supervisor raises ALARM.txt on each one",
  "ledger:      $run\ledger.csv (append-only)   live table: $run\TABLE.csv",
  "stall flag:  a shard with no STATUS advance for ${StallMinutes}m is flagged, not ignored",
  "status:      powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\untargeted_status.ps1 -Tag $Tag",
  "ABORT:       powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\untargeted_abort.ps1 -Tag $Tag",
  "fetch:       bash analysis/farm/untargeted_fetch.sh $Tag      (on the Mac)",
  "gate:        every candidate goes through validate -n 7 --complete AND",
  "             python3 analysis/counting/m3_check.py -n 7 <f>  (exit 2 = novel)",
  "launched:    $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
)
$spec | Set-Content "$run\SPEC.txt"

# Ledger columns are FIXED for the life of this file (s19 lesson: never change
# ledger column semantics mid-file).  One append-only row per state EVENT;
# the live per-shard table is TABLE.csv, rewritten each tick.
"ts,shard,event,pid,pname,pstart,lines,secs,rc,note" | Set-Content "$run\ledger.csv"

# --- detach the supervisor (it owns the pool and does all the launching) ----
$sres = & $DETACH $REPO "$run\logs\super.log" "$run\logs\super.err" `
          $CMD "/c" "$ROOT\untargeted_super.bat" $Tag
Write-Output "supervisor -> $sres"
if ("$sres" -notmatch 'pid\s+\d+') { throw "supervisor failed to detach: $sres" }

Write-Output ""
Write-Output ($spec -join "`n")
