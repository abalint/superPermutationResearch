# fllaunch.ps1 -- operator entry point for the fl1577 recipe study (P4 gate).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\superpermFarm\fl1577\fllaunch.ps1 -Tag f1
#
# Pre-launch arithmetic (docs/OPERATIONS.md, restated into SPEC.txt at launch):
#   WHAT      5 LKH-3 recipes x 10 seeds on TSPLIB fl1577 (optimum 22249), 600 s
#             wall budget per cell.  Serves NOVELTY-DESIGN P4: a metaheuristic
#             recipe that cannot crack this proxy does not get n=7 CPU.
#   RUNTIME   50 cells x ~610 s actual / 25 workers = 2 exact waves = ~21 min.
#             NOTE the Mac harness's "~1.35x wall overshoot" does NOT apply to this
#             binary: on macOS LKH's GetTime() is getrusage (user+sys CPU, and
#             preprocessing is not charged), whereas the mingw build falls back to
#             clock(), which under MSVCRT is WALL time since process start.  The
#             probe (tag p2, 90 s budget) landed at Time.total = 90.00 s and 90 s
#             wall for all 5 recipes, i.e. the budget is now exact.  Bounded worst
#             case = 3 waves = ~31 min.  No cell can run unbounded regardless:
#             TOTAL_TIME_LIMIT is enforced inside LKH.
#   PRODUCES  runs\<tag>\{SPEC.txt,PARAMS.txt,STATUS.txt,ledger.tsv,ledger_wNN.tsv,
#             <cfg>_s<seed>\{lkh.par,lkh.log,row.tsv,best.tour}}
#   ABORT     flstop.ps1 -Tag <tag>  (kills only recorded pids, by process identity)
#
# -Workers 25 rather than 24: 50 cells / 25 = exactly 2 waves, which is a whole
# wave (~14 min) faster than the house-default 24.  Still leaves 3 of 28 logical
# cores, and every worker plus its LKH child runs BELOW_NORMAL via detach.exe, so
# the user's transcription service (2 python.exe -- NEVER touched) keeps priority.
# LKH on a 1577-city instance is ~40 MB resident, so 25 workers is ~1 GB of 48.
param(
  [string]$Tag     = "",
  [int]$Tlim       = 600,
  [int]$Workers    = 25,
  [int[]]$Seeds    = @(1,2,3,4,5,6,7,8,9,10),
  [string[]]$Configs = @("default","lkh3_special","gaincrit_patch","kickburst","popga"),
  [string]$Root    = "D:\superpermFarm\fl1577",
  [switch]$Force
)
$ErrorActionPreference = "Continue"

$DETACH = "F:\superpermFarm\detach.exe"
$CMD    = "$env:SystemRoot\System32\cmd.exe"
if ($Tag -eq "") { $Tag = "f$(Get-Date -Format 'MMddHHmm')" }
if ($Tag -match '\s') { throw "tag must not contain whitespace: '$Tag'" }
$RunRoot = "$Root\runs\$Tag"

# --- prerequisites ----------------------------------------------------------
foreach ($f in @($DETACH, "$Root\bin\LKH.exe", "$Root\fl1577.tsp", "$Root\flworker.ps1",
                 "$Root\flworker.bat", "$Root\flsuper.ps1", "$Root\flsuper.bat")) {
  if (-not (Test-Path $f)) { throw "missing prerequisite: $f" }
}
foreach ($c in $Configs) {
  if (-not (Test-Path "$Root\cfg\$c.par")) { throw "missing recipe fragment: $Root\cfg\$c.par" }
}
# the instance is the experiment -- pin it
$SHA = "cb473802e29b1f4190980683bd4dd16a12e7fdcf3a80d0448c52fdda27d2e5a5"
$h = (Get-FileHash "$Root\fl1577.tsp" -Algorithm SHA256).Hash.ToLower()
if ($h -ne $SHA) { throw "fl1577.tsp sha256 mismatch: $h (expected $SHA)" }

# --- refusals ---------------------------------------------------------------
$liveLkh = @(Get-Process -Name LKH -EA SilentlyContinue)
if ($liveLkh.Count -gt 0 -and -not $Force) {
  throw "REFUSING TO LAUNCH: $($liveLkh.Count) LKH process(es) already alive (the s28 duplicate-launch trap). Run flstatus.ps1, then flstop.ps1."
}
if ((Test-Path $RunRoot) -and -not $Force) { throw "REFUSING TO LAUNCH: run dir exists ($RunRoot). Pick another -Tag." }
$free = [math]::Round(([System.IO.DriveInfo]::new("D:\")).AvailableFreeSpace/1GB,1)
if ($free -lt 5) { throw "REFUSING TO LAUNCH: only $free GB free on D:" }

# --- plan -------------------------------------------------------------------
$cells = @()
foreach ($c in $Configs) { foreach ($s in $Seeds) { $cells += "$c $s" } }
# round-robin over workers so no worker gets a whole recipe (a slow recipe would
# otherwise serialize onto one core and stretch the last wave)
New-Item -ItemType Directory -Force -Path $RunRoot,"$RunRoot\cells","$RunRoot\pids","$RunRoot\progress","$RunRoot\logs" | Out-Null
for ($w = 0; $w -lt $Workers; $w++) {
  $id = "{0:D2}" -f $w
  $mine = @()
  for ($i = $w; $i -lt $cells.Count; $i += $Workers) { $mine += $cells[$i] }
  $mine | Set-Content "$RunRoot\cells\w$id.txt"
}

@("Tag=$Tag", "Tlim=$Tlim", "Workers=$Workers", "Cells=$($cells.Count)") | Set-Content "$RunRoot\PARAMS.txt"

$spec = @(
  "tag:         $Tag",
  "what:        fl1577 recipe study -- LKH-3 metaheuristic recipes vs TSPLIB fl1577",
  "             (docs/SWEEP-QUEUE.md '## fl1577 recipe study'; NOVELTY-DESIGN P4 gate).",
  "instance:    $Root\fl1577.tsp  sha256 $SHA  optimum 22249",
  "binary:      $Root\bin\LKH.exe  (LKH-3.0.13, mingw-w64 gcc 16.1.0, built on this PC)",
  "recipes:     $($Configs -join ', ')",
  "seeds:       $($Seeds -join ',')",
  "budget:      TOTAL_TIME_LIMIT = $Tlim s per cell (WALL on this build -- clock() fallback)",
  "cells:       $($cells.Count)   workers: $Workers (BELOW_NORMAL)",
  "projected:   ceil($($cells.Count)/$Workers) waves x ~$([int]($Tlim*1.02)) s = ~$([int]([math]::Ceiling($cells.Count/$Workers)*$Tlim*1.02/60)) min",
  "success:     cracked = 1 iff best == 22249; headline = cracked_total over all cells",
  "ledger:      $RunRoot\ledger.tsv  (config seed best gap gap_pct secs runs successes cracked trials logfile)",
  "heartbeat:   $RunRoot\STATUS.txt  (rewritten every 30 s by flsuper.ps1)",
  "abort:       powershell -NoProfile -ExecutionPolicy Bypass -File $Root\flstop.ps1 -Tag $Tag",
  "launched:    $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  by $env:USERNAME on $env:COMPUTERNAME"
)
$spec | Set-Content "$RunRoot\SPEC.txt"
$spec | ForEach-Object { Write-Output $_ }

# --- launch -----------------------------------------------------------------
# detach.exe signature is: detach.exe <workdir> <stdout-file> <stderr-file> <command> [args...]
# (detached stdout is unreliable anyway -- workers write their own progress files).
for ($w = 0; $w -lt $Workers; $w++) {
  $id = "{0:D2}" -f $w
  if (@(Get-Content "$RunRoot\cells\w$id.txt").Count -eq 0) { continue }
  & $DETACH $RunRoot "$RunRoot\logs\w$id.out" "$RunRoot\logs\w$id.err" $CMD /c "$Root\flworker.bat" $Tag $id
  Start-Sleep -Milliseconds 250
}
Start-Sleep -Seconds 3
& $DETACH $RunRoot "$RunRoot\logs\super.out" "$RunRoot\logs\super.err" $CMD /c "$Root\flsuper.bat" $Tag
Start-Sleep -Seconds 5
Write-Output ""
Write-Output "launched: $(@(Get-Process -Name LKH -EA SilentlyContinue).Count) LKH alive"
Write-Output "STATUS:   powershell -NoProfile -ExecutionPolicy Bypass -File $Root\flstatus.ps1 -Tag $Tag"
