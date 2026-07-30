# tabrief.ps1 -- one machine-readable line for a sharded tail-atsp run, for the
# session-level monitor (analysis/farm/ta_watch.sh). Cheap: reads STATUS.txt
# (written by tasuper.ps1) plus a live process count; never touches worker logs.
param([string]$Tag = "")
$ROOT = "F:\superpermFarm\tailatsp"
if ($Tag -eq "") {
  $d = Get-ChildItem "$ROOT\runs" -Directory -EA SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $d) { Write-Output "ERR no-runs"; exit 0 }
  $Tag = $d.Name
}
$run = "$ROOT\runs\$Tag"
if (-not (Test-Path "$run\STATUS.txt")) { Write-Output "ERR no-status TAG=$Tag"; exit 0 }

$stage="?"; $alive=-1; $done=-1; $total=-1; $pct=-1; $imp=-1; $ties=-1; $fin=-1; $eta="?"
$mimp=0; $meq=0
foreach ($l in Get-Content "$run\STATUS.txt") {
  if ($l -match 'stage:\s+(\S+)\s+\((\d+)/(\d+)\s+workers') { $stage=$Matches[1]; $alive=[int]$Matches[2] }
  if ($l -match 'walks:\s+(\d+)/(\d+)\s+\(([\d\.]+)%\)')     { $done=[int]$Matches[1]; $total=[int]$Matches[2]; $pct=[double]$Matches[3] }
  if ($l -match 'eta=(\S+)')                                  { $eta=$Matches[1] }
  if ($l -match 'improvements:\s+(\d+)\s+new-allocation ties:\s+(\d+)') { $imp=[int]$Matches[1]; $ties=[int]$Matches[2] }
  if ($l -match 'finished:\s+(\d+)/')                         { $fin=[int]$Matches[1] }
  if ($l -match 'merge \(I2a\):\s+(\d+) improved .* (\d+) equal-cost') { $mimp=[int]$Matches[1]; $meq=[int]$Matches[2] }
}
$age = [int]((Get-Date) - (Get-Item "$run\STATUS.txt").LastWriteTime).TotalSeconds
$live = @(Get-Process -Name superperm -EA SilentlyContinue).Count
$alarm = 0
if (Test-Path "$run\ALARM.txt") { $alarm = 1 }
Write-Output "TAG=$Tag STAGE=$stage ALIVE=$alive LIVE=$live WALKS=$done/$total PCT=$pct IMP=$imp TIES=$ties MIMP=$mimp MEQ=$meq FIN=$fin ETA=$eta AGE=$age ALARM=$alarm"
