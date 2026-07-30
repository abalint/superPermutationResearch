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

function Count-Lines([string]$p) {
  if (-not (Test-Path $p)) { return 0 }
  $c = 0
  try {
    $fs = [System.IO.File]::Open($p, 'Open', 'Read', 'ReadWrite')
    $sr = New-Object System.IO.StreamReader($fs)
    while ($null -ne $sr.ReadLine()) { $c++ }
    $sr.Close(); $fs.Close()
  } catch { return $c }
  return $c
}

$ledgered = @{}
$deadTicks = @{}          # grace period: a worker's last append may not be flushed yet
$improveTotal = 0
$tieTotal = 0
$lastExit = "-"

while ($true) {
  $alive = 0; $doneWalks = 0; $memSum = 0; $memMax = 0
  $aliveList = @()

  for ($i = 0; $i -lt $Workers; $i++) {
    $nn = "{0:d2}" -f $i
    $log = "$run\logs\w$nn.log"
    $doneWalks += (Count-Lines $log)

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
      $verdict = "OK"
      if ($sum -eq "")   { $verdict = "NO-SUMMARY" }   # crashed / killed mid-shard
      if ($imp -gt 0)    { $verdict = "IMPROVEMENT" }
      $rc = ""
      $improveTotal += $imp
      $tieTotal     += $ties
      $ledgered[$nn] = $true
      "w$nn,s$nn,$rc,$verdict,$walks,$opt,$imp,$skip,$ties,$secs,$(Get-Date -Format 'HH:mm:ss')" |
        Add-Content "$run\ledger.csv"
      $lastExit = "w$nn $verdict walks=$walks improved=$imp ties=$ties secs=$secs"
      if ($imp -gt 0) {
        @("*** ALARM: $imp block-order IMPROVEMENT(S) = 871 CANDIDATE(S) ***",
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
    "worker mem:   sum=$memSum MB  max=$memMax MB",
    "finished:     $($ledgered.Count)/$Workers   last: $lastExit",
    "alive:        $($aliveList -join ' ')",
    "updated:      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
  )
  if ($improveTotal -gt 0) { $lines = @("*** ALARM: $improveTotal IMPROVEMENT(S) -- see ALARM.txt ***") + $lines }
  $lines | Set-Content "$run\STATUS.txt"

  if ($alive -eq 0 -and $ledgered.Count -ge $Workers) {
    Add-Content "$run\STATUS.txt" "ALLDONE at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') after $('{0:n1}m' -f ($elapsed/60))"
    break
  }
  Start-Sleep -Seconds $TickSeconds
}
