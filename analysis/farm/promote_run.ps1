# promote_run.ps1 -- launch the n=6 full-corpus PROMOTION hunt (w3->w4,
# dlen = 0) on the farm PC.  SWEEP-QUEUE '## n=6 full-corpus PROMOTION hunt'.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\promote_run.ps1 -Tag p1
#   ... -Limit 4     smoke test: 4 walks per shard
#   ... -DryRun      sizing only (per-shard walk/orientation counts)
#
# This reuses the s52 untargeted supervisor unchanged except for its new
# `Target` PARAM (s52b, additive, default preserves fuse.py behaviour).  The
# instrument is driven through promote_shim.py, NOT directly: demotion.py reads
# its positionals from argv[0..2] and writes no STATUS heartbeat, so it cannot
# satisfy the supervisor's contract on its own.  See promote_shim.py's header.
#
# Pre-launch arithmetic (docs/OPERATIONS.md, non-negotiable).  MEASURED on the
# Mac at 0.5 s/walk (2 walks in 1.0 s, matching the queue entry's 0.555 s/walk
# 200-walk round-robin sample): 22,062 walks = 44,124 orientations; at 24 shards
# that is ~920 walks/shard ~= 8.5 min solo => ~9 min wall.  The single-core
# figure the queue quotes is ~3.4 h.
#
# RAM: demotion.py loads the full 22,062-class canon index per shard, so this is
# heavier than the untargeted sweep's 184 MB.  Budgeted at 400 MB/shard here;
# the -DryRun pass reports the real figure before the live run.
#
# ALARM TEXT CAVEAT: the shared supervisor's banner says "validate -n 7" and
# "m3_check.py -n 7".  This is an n=6 hunt.  The correct gate is
#   cargo run --release -- validate -n 6 --file <f> --complete
#   python3 analysis/counting/m3_check.py <f>          (exit 2 = novel)
# promote_shim.py writes exactly that into GATE.txt in every shard out dir.
param(
  [string]$Tag          = "",
  [int]$Shards          = 24,
  [int]$Workers         = 24,
  [string]$Mode         = "promote",
  [int]$Limit           = 0,
  [switch]$DryRun,
  [int]$StallMinutes    = 5,
  [int]$Total           = 44124,          # 22,062 walks x 2 orientations
  [string]$ExtraArgs    = "",
  [int]$TickSeconds     = 30,
  [int]$MBPerShard      = 400,
  [switch]$Force
)
$ErrorActionPreference = "Stop"

$ROOT   = "F:\superpermFarm\untargeted"
$REPO   = "$ROOT\repo"
$PY     = "$ROOT\pyenv\Scripts\upyw.exe"
$SHIM   = "$ROOT\promote_shim.py"
$DEMO   = "$REPO\analysis\counting\s51\demotion.py"
$CORPUS = "$REPO\data\upstream872"
$DETACH = "F:\superpermFarm\detach.exe"
$CMD    = "$env:SystemRoot\System32\cmd.exe"

if ($Tag -eq "") {
  $Tag = "p$(Get-Date -Format 'MMddHHmm')"
  if ($Limit -gt 0) { $Tag += "L$Limit" }
  if ($DryRun)      { $Tag += "dry" }
}
if ($Tag -match '\s') { throw "tag must not contain whitespace: '$Tag'" }
$run = "$ROOT\runs\$Tag"

# --- prerequisites ----------------------------------------------------------
foreach ($f in @($DETACH, $PY, "$ROOT\untargeted_super.ps1",
                 "$ROOT\untargeted_super.bat", $SHIM, $DEMO)) {
  if (-not (Test-Path $f)) { throw "missing prerequisite: $f" }
}
if (-not (Test-Path $CORPUS)) { throw "missing corpus: $CORPUS" }
$nw = @(Get-ChildItem $CORPUS -Filter *.txt -File).Count
if ($nw -lt 22062 -and -not $Force) {
  throw "corpus incomplete: $nw of 22062 walks in $CORPUS (re-ship, or -Force)"
}
Write-Output "corpus: $nw walks in $CORPUS"

# --- refusals (the s28 duplicate-launch trap) -------------------------------
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
  "Total=$Total",
  "ExtraArgs=$ExtraArgs",
  "TickSeconds=$TickSeconds",
  "Stub=0",
  "Target=promote_shim.py"
) | Set-Content "$run\PARAMS.txt"

$cmdline = "$PY -u $SHIM $Mode --shard <i>/$Shards --out $run\out\sNN"
if ($Limit -gt 0) { $cmdline += " --limit $Limit" }
if ($DryRun)      { $cmdline += " --dry-run" }
if ($ExtraArgs -ne "") { $cmdline += " $ExtraArgs" }

$spec = @(
  "tag:         $Tag",
  "what:        n=6 full-corpus PROMOTION hunt (w3->w4, dlen = 0)",
  "             (docs/SWEEP-QUEUE.md '## n=6 full-corpus PROMOTION hunt')",
  "             s51 proved no KNOWN 872 can be a promotion product, so every",
  "             product of this sweep is a NOVEL 872 class BY CONSTRUCTION.",
  "spec:        $cmdline",
  "shim:        promote_shim.py -> demotion.py promote 6 data/upstream872",
  "             (demotion.py reads argv[0..2] positionally and writes no STATUS",
  "              heartbeat; the shim supplies both.  It does NOT alter results.)",
  "workdir:     $REPO   (repo-root mirror; dirs are resolved relative to it)",
  "interpreter: $PY  (renamed venv python -- process-identity guard so aborting",
  "             this sweep can never touch the transcription service's python.exe)",
  "shards:      $Shards, pool $Workers concurrent, BELOW_NORMAL via detach.exe",
  "corpus:      $nw walks x 2 orientations = $Total units, round-robin j %% k == i",
  "runtime:     MEASURED 0.5 s/walk => ~920 walks/shard ~= 8.5 min solo,",
  "             ~9 min wall at $Workers-way.  (Queue's single-core figure: ~3.4 h.)",
  "footprint:   budgeted $MBPerShard MB/shard (full 22,062-class canon index per",
  "             shard); -DryRun reports the real figure",
  "produces:    $run\out\sNN\  (edges.tsv, promote_stats_sNN.tsv, STATUS, GATE.txt,",
  "             and demo-/drop-/prod- product .txt files)",
  "events:      product .txt files + '*** NOVEL-CANDIDATE' / '*** DEGENERATE-DROP",
  "             NOVEL' banners on stdout; the supervisor raises ALARM.txt on those",
  "GATE (n=6!): the supervisor's ALARM text is n=7 boilerplate -- ignore it here:",
  "             cargo run --release -- validate -n 6 --file <f> --complete",
  "             python3 analysis/counting/m3_check.py <f>   (exit 2 = novel)",
  "             Each shard out dir carries GATE.txt saying the same.",
  "ledger:      $run\ledger.csv (append-only)   live table: $run\TABLE.csv",
  "stall flag:  a shard with no STATUS advance for ${StallMinutes}m is flagged, not ignored",
  "status:      powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\untargeted_status.ps1 -Tag $Tag",
  "ABORT:       powershell -NoProfile -ExecutionPolicy Bypass -File $ROOT\untargeted_abort.ps1 -Tag $Tag",
  "fetch:       bash analysis/farm/untargeted_fetch.sh $Tag      (on the Mac)",
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
