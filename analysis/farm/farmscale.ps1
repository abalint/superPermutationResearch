# farmscale.ps1 -- parameterless, idempotent, re-runnable scheduler that fills
# the box up to $TARGET live PermutationChains workers from worklist.txt.
#
#   Run it as many times as you like. Each run:
#     * counts live PermutationChains processes (including the five priority
#       K=27 chains in runs\c0..c4, which it never touches),
#     * marks worker dirs whose process has exited,
#     * starts the next not-yet-attempted worklist patterns via detach.exe
#       until the live count reaches $TARGET.
#
# Worker dirs are runs\w<NNN> where NNN is the pattern's 0-based line number in
# worklist.txt, so "dir exists" == "pattern already attempted". A pattern is
# never started twice: PermutationChains is fully deterministic, so re-running a
# chain that already finished or already died just reproduces the same result.
# To deliberately retry one, delete its runs\w<NNN> directory and re-run this.
#
# --------------------------------- knobs ---------------------------------
$TARGET      = 27     # desired total live PermutationChains processes (28 cores)
$MINFREEPCT  = 15     # refuse to start new workers below this % free RAM
# -------------------------------------------------------------------------

$farm     = 'F:\superpermFarm'
$runs     = Join-Path $farm 'runs'
$detach   = Join-Path $farm 'detach.exe'
$worklist = Join-Path $farm 'worklist.txt'

# Prefer the 64 MB-stack build (build64.bat) for new workers; fall back to the
# original 1 MB-stack binary if it has not been built.
$exe = Join-Path $farm 'PermutationChains64.exe'
if (-not (Test-Path $exe)) { $exe = Join-Path $farm 'PermutationChains.exe' }

foreach ($f in @($detach, $worklist, $exe)) {
  if (-not (Test-Path $f)) { Write-Output "MISSING: $f"; exit 1 }
}
New-Item -ItemType Directory -Force -Path $runs | Out-Null

# ---- RAM safety valve (WMI/CIM/systeminfo/Get-Counter are all denied for this
# ---- standard-user account, so meminfo.ps1 P/Invokes GlobalMemoryStatusEx).
. (Join-Path $farm 'meminfo.ps1')
$mem = Get-FarmMem
Write-Output ("RAM: {0}MB free of {1}MB ({2}% free)" -f $mem.AvailMB, $mem.TotalMB, $mem.PctFree)

$patterns = @(Get-Content $worklist | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
Write-Output ("worklist: {0} patterns; TARGET={1}; exe={2}" -f $patterns.Count, $TARGET, (Split-Path $exe -Leaf))

# ---- census of live processes and of existing worker dirs
$livePids = @{}
foreach ($p in (Get-Process PermutationChains, PermutationChains64 -ErrorAction SilentlyContinue)) { $livePids[$p.Id] = $p }
$liveCount = $livePids.Count

$attempted = @{}     # pattern -> dir name, for every dir ever created
foreach ($d in (Get-ChildItem $runs -Directory -ErrorAction SilentlyContinue)) {
  $pf = Join-Path $d.FullName 'pattern.txt'
  if (Test-Path $pf) { $attempted[(Get-Content $pf -First 1).Trim()] = $d.Name }

  # mark exited workers (w* only; farmlaunch.ps1 owns the c* chains)
  if ($d.Name -like 'w*') {
    $pidFile = Join-Path $d.FullName 'pid.txt'
    $exited  = Join-Path $d.FullName 'exited.txt'
    if ((Test-Path $pidFile) -and -not (Test-Path $exited)) {
      $wpid = (Get-Content $pidFile -First 1 -ErrorAction SilentlyContinue) -as [int]
      if (-not ($wpid -and $livePids.ContainsKey($wpid))) {
        $tail = ''
        $log = Join-Path $d.FullName 'out.log'
        if (Test-Path $log) { $tail = (Get-Content $log -Tail 1 -ErrorAction SilentlyContinue) }
        Set-Content -Path $exited -Value ("exited by {0}; last: {1}" -f (Get-Date -Format s), $tail)
        Write-Output ("{0} exited (pid {1})" -f $d.Name, $wpid)
      }
    }
  }
}
# (The five priority K=27 chains in runs\c0..c4 need no exclusion here: the
# worklist holds only the K=29/30/31 tiers, so their patterns cannot collide.)

$need = $TARGET - $liveCount
Write-Output ("live={0} target={1} need={2}" -f $liveCount, $TARGET, $need)
if ($need -le 0) { Write-Output 'at or above target; nothing to start'; exit 0 }

if ($mem.PctFree -lt $MINFREEPCT) {
  Write-Output ("DECLINED to start workers: only {0}% RAM free (< {1}% floor)" -f $mem.PctFree, $MINFREEPCT)
  exit 0
}

# ---- start the next unattempted patterns
$started = 0
for ($i = 0; $i -lt $patterns.Count -and $started -lt $need; $i++) {
  $pat = $patterns[$i]
  if ($attempted.ContainsKey($pat)) { continue }
  $name = 'w{0:d3}' -f $i
  $dir  = Join-Path $runs $name
  if (Test-Path $dir) { continue }          # dir exists == already attempted

  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Set-Content -Path (Join-Path $dir 'pattern.txt') -Value $pat
  # a truncated IntersectionFlags7.dat left by a killed run makes the exe abort
  # instantly ("Error reading from file"); it is cheap to regenerate.
  Remove-Item (Join-Path $dir 'IntersectionFlags7.dat') -ErrorAction SilentlyContinue

  $res = (& $detach $dir (Join-Path $dir 'out.log') (Join-Path $dir 'err.log') `
            $exe 7 ("nsk" + $pat) trackPartial 2>&1) | Out-String
  if ($res -match 'pid (\d+)') {
    Set-Content -Path (Join-Path $dir 'pid.txt') -Value ([int]$Matches[1])
    Write-Output ("{0} launched pid {1}  K={2} nsk{3}" -f $name, $Matches[1], $pat.Length, $pat)
    $attempted[$pat] = $name
    $started++
    Start-Sleep -Milliseconds 250          # stagger IntersectionFlags7.dat builds
  } else {
    Write-Output ("{0} FAILED: {1}" -f $name, $res.Trim())
    Set-Content -Path (Join-Path $dir 'exited.txt') -Value ("launch failed: " + $res.Trim())
  }
}
Write-Output ("started {0} worker(s); live now {1}" -f $started, ($liveCount + $started))
