# tasuper.ps1 -- heartbeat supervisor for a sharded tail-atsp sweep.
#
# Launched detached by talaunch.ps1. Writes STATUS.txt (overwritten every tick)
# and appends one ledger.csv row per finished worker, per docs/OPERATIONS.md.
# NEVER slurps a log into an array (the s19 OOM wedge was
# `@(Get-Content $jl).Count` on 20 workers) -- line counting is a streaming
# StreamReader, improvement detection is Select-String.
param(
  [Parameter(Mandatory=$true)][string]$Tag,
  [Parameter(Mandatory=$true)][int]$Workers,
  [Parameter(Mandatory=$true)][int]$Total,
  [int]$TickSeconds = 30
)
$ErrorActionPreference = "Continue"
$ROOT = "F:\superpermFarm\tailatsp"
$run  = "$ROOT\runs\$Tag"
$t0   = Get-Date
$PID | Set-Content "$run\super.pid"

# Progress = COMPLETED WALKS, not log lines. --recomp prints ~3 lines per walk
# (and --ties more), so a raw line count read 3x high and sent PCT past 100%
# with a nonsense ETA. Every solved walk emits exactly one line ending in
# "block-order-optimal", so count those -- still one streaming pass, O(1) memory.
function Count-Walks([string]$p) {
  if (-not (Test-Path $p)) { return 0 }
  $c = 0
  try {
    $fs = [System.IO.File]::Open($p, 'Open', 'Read', 'ReadWrite')
    $sr = New-Object System.IO.StreamReader($fs)
    while ($null -ne ($line = $sr.ReadLine())) {
      if ($line.EndsWith("block-order-optimal")) { $c++ }
    }
    $sr.Close(); $fs.Close()
  } catch { return $c }
  return $c
}

$ledgered = @{}
$deadTicks = @{}          # grace period: a worker's last append may not be flushed yet
$improveTotal = 0
$tieTotal = 0
$mergeMovesTotal = 0
$mergeImpTotal = 0
$mergeEqTotal = 0
$mergeAllocs = @{}      # corpus-wide merged-allocation histogram (the I2a product)
$rcMovesTotal = 0
$rcImpTotal = 0
$rcEqNewTotal = 0
$rcEqSameTotal = 0
$rcAllocs = @{}         # recomposed-allocation histogram (the recomp-1 product)
$r2SolvedTotal = 0
$r2ImpTotal = 0
$r2EqNewTotal = 0
$r2EqSameTotal = 0
$r2LambdaTotal = 0
$r2Allocs = @{}         # compound-allocation histogram (the recomp2/I3 product)
$seamTotal = 0          # *** KRISTAN SEAM FOUND *** banners
$lastExit = "-"

while ($true) {
  $alive = 0; $doneWalks = 0; $memSum = 0; $memMax = 0
  $aliveList = @()

  for ($i = 0; $i -lt $Workers; $i++) {
    $nn = "{0:d2}" -f $i
    $log = "$run\logs\w$nn.log"
    $doneWalks += (Count-Walks $log)

    $wpid = 0
    $pf = "$run\pids\w$nn.txt"
    if (Test-Path $pf) {
      $parts = (Get-Content $pf -TotalCount 1) -split "`t"
      try { $wpid = [int]($parts[0].Trim()) } catch { $wpid = 0 }
    }
    $p = $null
    if ($wpid -gt 0) { $p = Get-Process -Id $wpid -ErrorAction SilentlyContinue }
    # PID recycling guard: only count it as ours if it is still a superperm.exe
    if ($p -and $p.ProcessName -eq "superperm") {
      $alive++
      $aliveList += "w$nn"
      # in-flight equal-cost count: the worker's merge SUMMARY only exists once
      # it exits, so read its per-walk lines to keep MEQ live during the run
      $liveEq += @(Select-String -Path $log -SimpleMatch "merge-equal 872 at S-1:" -ErrorAction SilentlyContinue).Count
      $ws = [math]::Round($p.WorkingSet64 / 1MB)
      $memSum += $ws
      if ($ws -gt $memMax) { $memMax = $ws }
    }
    elseif (-not $ledgered.ContainsKey($nn)) {
      # finished (or died): harvest its summary line exactly once
      $sum = ""
      if (Test-Path $log) {
        $m = @(Select-String -Path $log -SimpleMatch "tail-atsp:" -ErrorAction SilentlyContinue)
        if ($m.Count -gt 0) { $sum = $m[$m.Count-1].Line }
      }
      if (-not $deadTicks.ContainsKey($nn)) { $deadTicks[$nn] = 0 }
      $deadTicks[$nn] = $deadTicks[$nn] + 1
      # no summary yet on the first sighting = probably an unflushed append, not a
      # crash; give it one more tick before writing a NO-SUMMARY row.
      if ($sum -eq "" -and $deadTicks[$nn] -lt 2) { continue }
      $walks=0; $opt=0; $imp=0; $skip=0; $ties=0; $secs=0.0
      if ($sum -match '(\d+) walks, (\d+) block-order-optimal, (\d+) improved, (\d+) skipped, (\d+) new-allocation ties \(([\d\.]+)s\)') {
        $walks=[int]$Matches[1]; $opt=[int]$Matches[2]; $imp=[int]$Matches[3]
        $skip=[int]$Matches[4]; $ties=[int]$Matches[5]; $secs=[double]$Matches[6]
      }
      # I2a (--merge): the extra summary line, plus its per-allocation histogram.
      $mMoves=0; $mImp=0; $mEq=0
      if (Test-Path $log) {
        $ml = @(Select-String -Path $log -SimpleMatch "merge (I2a):" -ErrorAction SilentlyContinue)
        if ($ml.Count -gt 0 -and $ml[$ml.Count-1].Line -match 'merge \(I2a\): (\d+) moves tried, (\d+) improved \(871 candidates\), (\d+) equal-cost') {
          $mMoves=[int]$Matches[1]; $mImp=[int]$Matches[2]; $mEq=[int]$Matches[3]
        }
        foreach ($al in @(Select-String -Path $log -SimpleMatch "merged allocation" -ErrorAction SilentlyContinue)) {
          if ($al.Line -match 'merged allocation \(([^)]*)\): (\d+)') {
            $k = "(" + $Matches[1] + ")"
            if (-not $mergeAllocs.ContainsKey($k)) { $mergeAllocs[$k] = 0 }
            $mergeAllocs[$k] = $mergeAllocs[$k] + [int]$Matches[2]
          }
        }
      }
      $mergeMovesTotal += $mMoves; $mergeImpTotal += $mImp; $mergeEqTotal += $mEq

      # recomp-1 (--recomp): same shape, one more counter (same-allocation equals)
      $rMoves=0; $rImp=0; $rEqNew=0; $rEqSame=0
      if (Test-Path $log) {
        $rl = @(Select-String -Path $log -SimpleMatch "recomp-1 (I2a):" -ErrorAction SilentlyContinue)
        if ($rl.Count -gt 0 -and $rl[$rl.Count-1].Line -match 'recomp-1 \(I2a\): (\d+) moves tried, (\d+) improved \(871 candidates\), (\d+) equal-cost 872s in NEW allocations, (\d+) equal-cost same-allocation') {
          $rMoves=[int]$Matches[1]; $rImp=[int]$Matches[2]; $rEqNew=[int]$Matches[3]; $rEqSame=[int]$Matches[4]
        }
        foreach ($al in @(Select-String -Path $log -SimpleMatch "recomposed allocation" -ErrorAction SilentlyContinue)) {
          if ($al.Line -match 'recomposed allocation \(([^)]*)\): (\d+)') {
            $k = "(" + $Matches[1] + ")"
            if (-not $rcAllocs.ContainsKey($k)) { $rcAllocs[$k] = 0 }
            $rcAllocs[$k] = $rcAllocs[$k] + [int]$Matches[2]
          }
        }
      }
      $rcMovesTotal += $rMoves; $rcImpTotal += $rImp
      $rcEqNewTotal += $rEqNew; $rcEqSameTotal += $rEqSame

      # recomp2 (I3, s38): pair compounds. Three things can fire here -- an
      # improvement, the Kristan seam, and a loop-relation (Lambda) violation,
      # which means a solver bug or a counterexample to the s35 law. All three
      # are alarms; the seam and Lambda are NOT exit-2 conditions in the tool,
      # so they must be detected from the banners.
      $r2Solved=0; $r2Imp=0; $r2EqNew=0; $r2EqSame=0; $r2Lambda=0; $seam=0
      if (Test-Path $log) {
        $r2l = @(Select-String -Path $log -SimpleMatch "recomp2 (I3):" -ErrorAction SilentlyContinue)
        if ($r2l.Count -gt 0 -and $r2l[$r2l.Count-1].Line -match '(\d+) exact re-solves .*?, (\d+) improved \(candidates\), (\d+) equal-cost in NEW allocations, (\d+) equal-cost same-allocation, (\d+) loop-relation violations') {
          $r2Solved=[int]$Matches[1]; $r2Imp=[int]$Matches[2]
          $r2EqNew=[int]$Matches[3]; $r2EqSame=[int]$Matches[4]; $r2Lambda=[int]$Matches[5]
        }
        $seam = @(Select-String -Path $log -SimpleMatch "*** KRISTAN SEAM FOUND ***" -ErrorAction SilentlyContinue).Count
        foreach ($al in @(Select-String -Path $log -SimpleMatch "compound allocation" -ErrorAction SilentlyContinue)) {
          if ($al.Line -match 'compound allocation \(([^)]*)\): (\d+)') {
            $k = "(" + $Matches[1] + ")"
            if (-not $r2Allocs.ContainsKey($k)) { $r2Allocs[$k] = 0 }
            $r2Allocs[$k] = $r2Allocs[$k] + [int]$Matches[2]
          }
        }
      }
      $r2SolvedTotal += $r2Solved; $r2ImpTotal += $r2Imp; $r2EqNewTotal += $r2EqNew
      $r2EqSameTotal += $r2EqSame; $r2LambdaTotal += $r2Lambda; $seamTotal += $seam

      $verdict = "OK"
      if ($sum -eq "")   { $verdict = "NO-SUMMARY" }   # crashed / killed mid-shard
      if ($imp -gt 0)    { $verdict = "IMPROVEMENT" }
      if ($mImp -gt 0)   { $verdict = "MERGE-IMPROVEMENT" }
      if ($rImp -gt 0)   { $verdict = "RECOMP-IMPROVEMENT" }
      if ($r2Imp -gt 0)  { $verdict = "RECOMP2-IMPROVEMENT" }
      if ($seam -gt 0)   { $verdict = "KRISTAN-SEAM" }
      if ($r2Lambda -gt 0) { $verdict = "LAMBDA-VIOLATION" }
      $rc = ""
      $improveTotal += $imp
      $tieTotal     += $ties
      $ledgered[$nn] = $true
      "w$nn,s$nn,$rc,$verdict,$walks,$opt,$imp,$skip,$ties,$mMoves,$mImp,$mEq,$rMoves,$rImp,$rEqNew,$rEqSame,$r2Solved,$r2Imp,$r2EqNew,$r2EqSame,$r2Lambda,$secs,$(Get-Date -Format 'HH:mm:ss')" |
        Add-Content "$run\ledger.csv"
      $lastExit = "w$nn $verdict walks=$walks improved=$imp ties=$ties merge_eq=$mEq secs=$secs"
      if ($mergeAllocs.Count -gt 0) {
        $ml2 = @("merged-allocation histogram (equal-cost 872s at S-1, summed over finished workers)")
        foreach ($k in ($mergeAllocs.Keys | Sort-Object)) { $ml2 += ("  {0}  {1}" -f $k, $mergeAllocs[$k]) }
        $ml2 += "total equal-cost: $mergeEqTotal   moves tried: $mergeMovesTotal   updated: $(Get-Date -Format 'HH:mm:ss')"
        $ml2 | Set-Content "$run\MERGE-ALLOCS.txt"
      }
      if ($rcAllocs.Count -gt 0) {
        $rl2 = @("recomposed-allocation histogram (equal-cost 872s in NEW allocations, summed over finished workers)")
        foreach ($k in ($rcAllocs.Keys | Sort-Object)) { $rl2 += ("  {0}  {1}" -f $k, $rcAllocs[$k]) }
        $rl2 += "new-alloc equals: $rcEqNewTotal   same-alloc equals: $rcEqSameTotal   moves tried: $rcMovesTotal   updated: $(Get-Date -Format 'HH:mm:ss')"
        $rl2 | Set-Content "$run\RECOMP-ALLOCS.txt"
      }
      if ($r2Allocs.Count -gt 0) {
        $r2l2 = @("compound-allocation histogram (equal-cost in NEW allocations, summed over finished workers)")
        foreach ($k in ($r2Allocs.Keys | Sort-Object)) { $r2l2 += ("  {0}  {1}" -f $k, $r2Allocs[$k]) }
        $r2l2 += "new-alloc equals: $r2EqNewTotal   same-alloc equals: $r2EqSameTotal   re-solves: $r2SolvedTotal   updated: $(Get-Date -Format 'HH:mm:ss')"
        $r2l2 | Set-Content "$run\RECOMP2-ALLOCS.txt"
      }
      if ($seam -gt 0 -or $r2Lambda -gt 0) {
        $hdr = '*** '
        if ($seam -gt 0)     { $hdr += "KRISTAN SEAM ($seam) " }
        if ($r2Lambda -gt 0) { $hdr += "LOOP-RELATION VIOLATION ($r2Lambda) " }
        $hdr += '***'
        @($hdr,
          "worker w$nn shard s$nn -- log: $run\logs\w$nn.log",
          "A seam = the first n=7 cross-allocation compound. A loop-relation",
          "violation = solver bug OR a counterexample to the s35 law: STOP and",
          "report before drawing any conclusion from this run.",
          "found: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')") | Add-Content "$run\ALARM.txt"
      }
      if ($imp -gt 0 -or $mImp -gt 0 -or $rImp -gt 0 -or $r2Imp -gt 0) {
        @("*** ALARM: $imp block-order + $mImp MERGE + $rImp RECOMP + $r2Imp RECOMP2 IMPROVEMENT(S) = CANDIDATE(S) ***",
          "worker w$nn shard s$nn",
          "log:   $run\logs\w$nn.log",
          "finds: $run\finds\w$nn",
          "DO NOT let anything overwrite the finds dir.",
          "Gate: validate -n 6 --file <f> --complete AND analysis/counting/m3_check.py <f> (exit 2 = novel).",
          "found: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')") | Add-Content "$run\ALARM.txt"
      }
    }
  }

  $elapsed = ((Get-Date) - $t0).TotalSeconds
  $rate = 0.0; $eta = "?"
  if ($elapsed -gt 5 -and $doneWalks -gt 0) {
    $rate = [math]::Round($doneWalks / $elapsed, 2)
    if ($rate -gt 0) {
      $rem = [math]::Max($Total - $doneWalks, 0) / $rate
      $eta = "{0:n1}m" -f ($rem / 60)
    }
  }
  $pct = 0.0
  if ($Total -gt 0) { $pct = [math]::Round(100.0 * $doneWalks / $Total, 1) }
  $stage = "RUNNING"
  if ($alive -eq 0) { $stage = "ALLDONE" }

  $lines = @(
    "tail-atsp sharded sweep -- tag=$Tag",
    "stage:        $stage ($alive/$Workers workers alive)",
    "walks:        $doneWalks/$Total ($pct%)   rate=$rate walks/s   elapsed=$('{0:n1}m' -f ($elapsed/60))   eta=$eta",
    "improvements: $improveTotal        new-allocation ties: $tieTotal",
    "merge (I2a):  $mergeImpTotal improved (871 cands)   $($mergeEqTotal + $liveEq) equal-cost 872s at S-1   $mergeMovesTotal moves tried   allocs=$($mergeAllocs.Count)",
    "recomp-1:     $rcImpTotal improved (871 cands)   $rcEqNewTotal equal-cost in NEW allocs   $rcEqSameTotal same-alloc equals   $rcMovesTotal moves tried   allocs=$($rcAllocs.Count)",
    "recomp2 (I3): $r2ImpTotal improved   $r2EqNewTotal equal-cost in NEW allocs   $r2EqSameTotal same-alloc equals   $r2SolvedTotal re-solves   SEAM=$seamTotal   LAMBDA_BAD=$r2LambdaTotal",
    "worker mem:   sum=$memSum MB  max=$memMax MB",
    "finished:     $($ledgered.Count)/$Workers   last: $lastExit",
    "alive:        $($aliveList -join ' ')",
    "updated:      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
  )
  if (($improveTotal + $mergeImpTotal + $rcImpTotal + $r2ImpTotal + $seamTotal + $r2LambdaTotal) -gt 0) {
    $lines = @("*** ALARM: $($improveTotal + $mergeImpTotal + $rcImpTotal + $r2ImpTotal) improvement(s), $seamTotal seam(s), $r2LambdaTotal loop-relation violation(s) -- see ALARM.txt ***") + $lines
  }
  $lines | Set-Content "$run\STATUS.txt"

  if ($alive -eq 0 -and $ledgered.Count -ge $Workers) {
    Add-Content "$run\STATUS.txt" "ALLDONE at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') after $('{0:n1}m' -f ($elapsed/60))"
    break
  }
  Start-Sleep -Seconds $TickSeconds
}
