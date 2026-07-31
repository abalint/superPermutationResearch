# pysweep_run.ps1 -- GENERIC launcher for any Python instrument that honours
# the farm supervisor's contract (--shard i/N, --out, STATUS heartbeat).
#
# Supersedes copy-pasting promote_run.ps1 per instrument. The supervisor
# (untargeted_super.ps1) is already generic via its s52b `Target` PARAM; this
# is the matching generic front end.
#
#   ... -File pysweep_run.ps1 -Tag i4a1 -Target i4a_shim.py -Mode apply-sym `
#       -Total 44124 -ExtraArgs "--dirs data/upstream872 --only fwd"
#
#   ... -File pysweep_run.ps1 -Tag ls1 -Target lswap_shim.py -Mode apply-sym `
#       -Total 0 -ExtraArgs "--rules data/loopswap/rules_n6_a360.tsv --dirs data/upstream872"
#
# -Total is the CORPUS-WIDE unit count, used only as the supervisor's fallback
# when a shard has not yet declared its own (the shims declare exact totals, so
# the fallback rarely matters -- pass 0 if unknown).
#
# ExtraArgs is split on whitespace and appended AFTER --shard/--out, so any
# instrument that reads positionals from argv[0..2] needs a shim (see
# promote_shim.py's header for that story).
param(
  [Parameter(Mandatory=$true)][string]$Tag,
  [Parameter(Mandatory=$true)][string]$Target,   # script name under $ROOT
  [string]$Mode         = "",                    # bare subcommand token, or ""
  [int]$Shards          = 24,
  [int]$Workers         = 24,
  [int]$Limit           = 0,
  [switch]$DryRun,
  [int]$StallMinutes    = 10,   # presize passes can be quiet for minutes
  [int]$Total           = 0,
  [string]$ExtraArgs    = "",
  [int]$TickSeconds     = 30,
  [int]$MBPerShard      = 400,
  [string]$What         = "python farm sweep",
  [switch]$Force
)
$ErrorActionPreference = "Stop"

$ROOT   = "F:\superpermFarm\untargeted"
$REPO   = "$ROOT\repo"
$PY     = "$ROOT\pyenv\Scripts\upyw.exe"
$TGT    = "$ROOT\$Target"
$DETACH = "F:\superpermFarm\detach.exe"
$CMD    = "$env:SystemRoot\System32\cmd.exe"

if ($Tag -match '\s') { throw "tag must not contain whitespace: '$Tag'" }
$run = "$ROOT\runs\$Tag"

foreach ($f in @($DETACH, $PY, "$ROOT\untargeted_super.ps1",
                 "$ROOT\untargeted_super.bat", $TGT)) {
  if (-not (Test-Path $f)) { throw "missing prerequisite: $f" }
}

$live = @(Get-Process -Name upyw -ErrorAction SilentlyContinue)
if ($live.Count -gt 0 -and -not $Force) {
  throw "REFUSING TO LAUNCH: $($live.Count) upyw.exe already alive. Run untargeted_status.ps1, then untargeted_abort.ps1."
}
if (Test-Path $run) { throw "REFUSING TO LAUNCH: run dir already exists ($run). Pick another -Tag." }

if (Test-Path "$ROOT\meminfo.ps1") {
  . "$ROOT\meminfo.ps1"
  $m = Get-FarmMem
  $needMB = $Workers * $MBPerShard + 2000
  Write-Output "RAM: $($m.AvailMB) MB available of $($m.TotalMB) MB; this run wants ~$needMB MB"
  if ($m.AvailMB -lt $needMB -and -not $Force) {
    throw "REFUSING TO LAUNCH: only $($m.AvailMB) MB available, need ~$needMB MB. (-Force to override.)"
  }
}

New-Item -ItemType Directory -Force -Path "$run\logs","$run\pids","$run\out" | Out-Null

@(
  "Shards=$Shards",
  "Workers=$Workers",
  "Mode=$Mode",
  "Limit=$Limit",
  "DryRunMode=$(if ($DryRun) { 1 } else { 0 })",
  "StallMinutes=$StallMinutes",
  "Total=$(if ($Total -gt 0) { $Total } else { $Shards })",
  "ExtraArgs=$ExtraArgs",
  "TickSeconds=$TickSeconds",
  "Stub=0",
  "Target=$Target"
) | Set-Content "$run\PARAMS.txt"

$cmdline = "$PY -u $TGT $Mode --shard <i>/$Shards --out $run\out\sNN"
if ($Limit -gt 0) { $cmdline += " --limit $Limit" }
if ($DryRun)      { $cmdline += " --dry-run" }
if ($ExtraArgs -ne "") { $cmdline += " $ExtraArgs" }

$spec = @(
  "tag:         $Tag",
  "what:        $What",
  "spec:        $cmdline",
  "target:      $TGT",
  "workdir:     $REPO   (repo-root mirror; instrument dirs resolve relative to it)",
  "interpreter: $PY  (renamed venv python -- process-identity guard so aborting",
  "             this sweep can never touch the transcription service's python.exe)",
  "shards:      $Shards, pool $Workers concurrent, BELOW_NORMAL via detach.exe",
  "footprint:   budgeted $MBPerShard MB/shard",
  "produces:    $run\out\sNN\  (instrument TSVs + STATUS heartbeat)",
  "stall flag:  a shard with no STATUS advance for ${StallMinutes}m is flagged, not ignored",
  "NOTE:        lswap_shim.py runs the instrument's own --dry-run FIRST to get an",
  "             exact per-shard total; that presize pass is SILENT on STATUS for",
  "             its duration, which is why -StallMinutes defaults to 10 here.",
  "status:      powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\untargeted_status.ps1 -Tag $Tag",
  "ABORT:       powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\untargeted_abort.ps1 -Tag $Tag",
  "fetch:       bash analysis/farm/untargeted_fetch.sh $Tag      (on the Mac)",
  "gate:        n=6 products -> validate -n 6 --complete + m3_check.py <f>",
  "             n=7 products -> validate -n 7 --complete + m3_check.py -n 7 <f>",
  "launched:    $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
)
$spec | Set-Content "$run\SPEC.txt"

"ts,shard,event,pid,pname,pstart,lines,secs,rc,note" | Set-Content "$run\ledger.csv"

$sres = & $DETACH $REPO "$run\logs\super.log" "$run\logs\super.err" `
          $CMD "/c" "$ROOT\untargeted_super.bat" $Tag
Write-Output "supervisor -> $sres"
if ("$sres" -notmatch 'pid\s+\d+') { throw "supervisor failed to detach: $sres" }

Write-Output ""
Write-Output ($spec -join "`n")
