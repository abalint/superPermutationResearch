# status.ps1 -- farm status at scale, kept under ~40 lines of output.
#   * PROMINENTLY flags any 7_59*.txt under runs\ (a candidate record),
#   * one line per LIVE worker: dir, K, pattern, CPU minutes, RSS, last progress
#     line truncated to 60 chars,
#   * exited workers and the unstarted backlog are summarised, not listed.
# pid.txt in each run dir holds the PermutationChains pid (detach.exe launches
# the exe directly, no cmd wrapper). pattern.txt holds its nsk pattern; the five
# priority K=27 chains in c0..c4 predate pattern.txt and are labelled as such.
$farm = 'F:\superpermFarm'
$runs = Join-Path $farm 'runs'

# ---- solutions first, loudest
$sol = @(Get-ChildItem $runs -Recurse -Filter '7_59*.txt' -ErrorAction SilentlyContinue)
if ($sol) {
  Write-Output ('*' * 72)
  foreach ($s in $sol) { Write-Output ("*** CANDIDATE RECORD: {0} ({1} bytes)" -f $s.FullName, $s.Length) }
  Write-Output ('*** harvest: scp it to the Mac and validate (see README-FARM.txt)')
  Write-Output ('*' * 72)
} else { Write-Output 'no solution files yet (looking for runs\**\7_59*.txt)' }

. (Join-Path $farm 'meminfo.ps1')
$mem = Get-FarmMem

$live = @{}
foreach ($p in (Get-Process PermutationChains, PermutationChains64 -ErrorAction SilentlyContinue)) { $live[$p.Id] = $p }

$rows = @(); $exited = 0; $dirs = 0
foreach ($d in (Get-ChildItem $runs -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
  $dirs++
  $wpid = 0
  $pf = Join-Path $d.FullName 'pid.txt'
  if (Test-Path $pf) { $wpid = (Get-Content $pf -First 1 -ErrorAction SilentlyContinue) -as [int] }
  if (-not ($wpid -and $live.ContainsKey($wpid))) { $exited++; continue }
  $pat = ''
  $patF = Join-Path $d.FullName 'pattern.txt'
  if (Test-Path $patF) { $pat = (Get-Content $patF -First 1).Trim() }
  $tail = ''
  $lg = Join-Path $d.FullName 'out.log'
  if (Test-Path $lg) { $tail = ((Get-Content $lg -Tail 1 -ErrorAction SilentlyContinue) -join '') }
  if ($tail.Length -gt 60) { $tail = $tail.Substring(0, 60) }
  $rows += [pscustomobject]@{
    Dir    = $d.Name
    K      = $(if ($pat) { $pat.Length } else { 27 })
    Pat    = $(if ($pat) { $pat } else { '<K=27 priority chain, see farmlaunch.ps1>' })
    CpuMin = [math]::Round($live[$wpid].TotalProcessorTime.TotalMinutes, 1)
    WsMB   = [math]::Round($live[$wpid].WorkingSet64 / 1MB, 1)
    Tail   = $tail
  }
}

$wl = Join-Path $farm 'worklist.txt'
$total = if (Test-Path $wl) { @(Get-Content $wl | Where-Object { $_.Trim() }).Count } else { 0 }
$wdirs = @(Get-ChildItem $runs -Directory -Filter 'w*' -ErrorAction SilentlyContinue).Count
Write-Output ("LIVE {0} workers | {1} run dirs | {2} exited | worklist {3} patterns, {4} unstarted" -f `
  $rows.Count, $dirs, $exited, $total, [math]::Max(0, $total - $wdirs))
Write-Output ("RAM {0}MB free / {1}MB ({2}% free) | farm RSS {3}MB | {4} cores" -f `
  $mem.AvailMB, $mem.TotalMB, $mem.PctFree, `
  [math]::Round((($live.Values | Measure-Object WorkingSet64 -Sum).Sum / 1MB), 1), $env:NUMBER_OF_PROCESSORS)

foreach ($r in ($rows | Sort-Object Dir)) {
  Write-Output ("{0,-5} K={1} cpu={2,7}m ws={3,5}MB {4} | {5}" -f $r.Dir, $r.K, $r.CpuMin, $r.WsMB, $r.Pat, $r.Tail)
}
if ($exited) {
  Write-Output ("({0} exited run dir(s); cause in runs\<dir>\exited.txt. Run watchdog.ps1 to backfill.)" -f $exited)
}
