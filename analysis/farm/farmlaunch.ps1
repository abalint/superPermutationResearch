# farmlaunch.ps1 — start the five K=27 PermutationChains runs so they survive
# ssh disconnect. Mechanism: F:\superpermFarm\detach.exe (tiny C launcher, see
# detach.c) calls CreateProcess with CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS
# | CREATE_NEW_PROCESS_GROUP | BELOW_NORMAL_PRIORITY_CLASS, escaping the Windows
# OpenSSH session job object (the Windows analogue of nohup). detach.exe sets
# the working dir and append-redirects stdout/stderr itself, so the pid it
# prints (recorded in runs\c<i>\pid.txt) is the PermutationChains.exe pid.
# Re-runnable: skips a chain whose recorded pid is a live PermutationChains
# process. On (re)starting a chain, deletes its IntersectionFlags7.dat — a
# stale copy from a killed run can be truncated and makes the exe abort with
# "Error reading from file IntersectionFlags7.dat"; it is regenerated quickly.
$farm   = 'F:\superpermFarm'
$exe    = Join-Path $farm 'PermutationChains.exe'
$detach = Join-Path $farm 'detach.exe'
$pats = @(
  '666646664666466466646664666',
  '666646664664666466466646666',
  '666646646664666466466646666',
  '666646664664666466646646666',
  '666466646664664666466646666'
)

for ($i = 0; $i -lt $pats.Count; $i++) {
  $dir = Join-Path $farm "runs\c$i"
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $pidFile = Join-Path $dir 'pid.txt'
  if (Test-Path $pidFile) {
    $old = (Get-Content $pidFile -ErrorAction SilentlyContinue) -as [int]
    if ($old) {
      $p = Get-Process -Id $old -ErrorAction SilentlyContinue
      if ($p -and $p.ProcessName -like 'PermutationChains*') {
        Write-Output "c$i already running (pid $old)"; continue
      }
    }
  }
  Remove-Item (Join-Path $dir 'IntersectionFlags7.dat') -ErrorAction SilentlyContinue
  $res = (& $detach $dir (Join-Path $dir 'out.log') (Join-Path $dir 'err.log') `
            $exe 7 ("nsk" + $pats[$i]) trackPartial 2>&1) | Out-String
  if ($res -match 'pid (\d+)') {
    $exePid = [int]$Matches[1]
    Set-Content -Path $pidFile -Value $exePid
    Write-Output "c$i launched, pid $exePid  nsk$($pats[$i])"
  } else {
    Write-Output "c$i FAILED: $($res.Trim())"
  }
}
