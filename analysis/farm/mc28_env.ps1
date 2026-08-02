# mc28_env.ps1 -- farm-side environment + PARITY check for the s63 v=28
# supply-tight FOREST multi-cover sweep (the (140,8,0,0,0) cell).
# Read-only apart from $ROOT\_mc28probe.  Safe to re-run.  Exit code = failures.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\mc28_env.ps1
#   ... -File ...\mc28_env.ps1 -Full     # adds the 200-cover real-branch parity (~35 s)
#
# THE CHECK THAT MATTERS IS PARITY, NOT PRESENCE (a0_env.ps1 / s58_env.ps1
# philosophy).  Presence tells you a file arrived; it does not tell you the PC
# will SEARCH THE SAME TREE the Mac reasoned about.  This engine's whole output
# is deterministic integers -- node counts, cover counts, and a (j,length)
# census -- so parity here is exact and cheap:
#
#   P1  n=4, v=3, splits=3   -> 12 covers, 2127 nodes, census
#                               {(2,36):12,(2,37):14,(3,37):14,(3,38):5,(4,38):40}
#       That census IS the independent brute-force ground truth of
#       out/s63/mcover/REPORT.md §3.2 -- so P1 is not a self-consistency check,
#       it is the PC re-deriving an externally verified answer.
#   P2  n=5, v=7, splits=4   -> 224 covers, 47,623 nodes, census
#                               {(0,153):6,(0,154):49,(1,154):50}
#       The designed-SAT multi-cover control (REPORT §3.3): it exercises the
#       FIND path -- a shard that cannot find a walk that IS there would report
#       a false negative on the real branch and nobody would know.
#   P3  the REAL branch, first 200 forest multi-covers (-Full)
#       -> 200 covers, K histogram {8:200}, 29,609,908 nodes, NO walk.
#       Covers build_mids, the forest union-find, the phi-cycle prune and the
#       arc DFS on the actual n=6 v=28 tree.  ~33 s on the Mac.
#
# A mismatch on any of these means the PC would produce a DIFFERENT search --
# and since the product of this sweep is a NEGATIVE ("the cell is empty"), a
# silently different search is the one failure mode that cannot be detected
# after the fact.  Do not launch through a parity failure.
#
# Windows/farm traps respected here:
#   * NO Get-CimInstance / tasklist / WMI -- they HANG or Access-deny for the
#     farm account (confirmed again this session: Win32_OperatingSystem ->
#     "Access denied").  Cores come from $env:NUMBER_OF_PROCESSORS, disk from
#     [System.IO.DriveInfo], processes from Get-Process.
#   * $ErrorActionPreference stays "Continue": with "Stop", ANY native command
#     writing to stderr throws NativeCommandError even at rc 0.
#   * everything written goes under F:\superpermFarm\ -- never C:, never
#     F:\audioPrime.
#   * do NOT add `*> some.log` to the caller: PowerShell redirection writes
#     UTF-16LE and Mac-side grep then finds nothing, which is indistinguishable
#     from "pattern absent".  This prints to stdout; let ssh carry it.
param([switch]$Full)
$ErrorActionPreference = "Continue"

$ROOT  = "F:\superpermFarm\untargeted"
$REPO  = "$ROOT\repo"
$PY    = "$ROOT\pyenv\Scripts\upyw.exe"
$JTAX  = "$REPO\out\s62\jtax"
$PROBE = "$ROOT\_mc28probe"
$fail  = 0
function Ok  ($m) { Write-Output "  [ok]   $m" }
function Bad ($m) { Write-Output "  [FAIL] $m"; $script:fail++ }
function Note($m) { Write-Output "  ...    $m" }

Write-Output "=== s63 mc28 forest-branch farm environment  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
New-Item -ItemType Directory -Force -Path $PROBE | Out-Null

# --- 1. host + idleness ------------------------------------------------------
Write-Output "-- host --"
$cores = [int]$env:NUMBER_OF_PROCESSORS
Ok "logical processors: $cores"
if ($cores -lt 26) { Bad "fewer than 26 cores -- re-size the shard count before launching" }
$ours = @(Get-Process -Name upyw -EA SilentlyContinue)
if ($ours.Count -gt 0) { Bad "$($ours.Count) upyw.exe already alive (a sweep is running)" }
else { Ok "no upyw.exe (our shards) running" }
$tpy = @(Get-Process -Name python,pythonw -EA SilentlyContinue).Count
Note "python.exe on the box: $tpy  (transcription service -- NEVER kill)"
$d = [System.IO.DriveInfo]::new("F")
$freeGB = [math]::Round($d.AvailableFreeSpace / 1GB, 1)
if ($freeGB -lt 5) { Bad "only $freeGB GB free on F:" } else { Ok "F: free: $freeGB GB" }

# --- 2. interpreter ----------------------------------------------------------
Write-Output "-- interpreter --"
if (-not (Test-Path $PY)) { Bad "interpreter missing: $PY (run untargeted_env.ps1 first)" }
else {
  # upyw.exe is the DELIBERATELY RENAMED venv python: the abort script matches
  # on process name, so it can never kill the transcription service's
  # python.exe.  Do not "fix" the name.
  $ver = (& $PY -c "import sys;print(sys.version.split()[0])") 2>&1
  Ok "upyw.exe present: $ver"
  # math.comb (3.8+) is used by the closed-form Z count in enum_multicovers
  $cb = (& $PY -c "from math import comb;print(comb(10,3))") 2>&1
  if ("$cb" -eq "120") { Ok "math.comb available" } else { Bad "math.comb missing/odd: $cb" }
  Note "the engine is pure stdlib -- no numpy, no compiled engine, nothing to build"
}

# --- 3. payload presence + the SECOND END of the sha256 manifest -------------
Write-Output "-- payload + manifest re-hash --"
foreach ($f in @("$ROOT\mc28_shim.py",
                 "$JTAX\mcover_search.py", "$JTAX\cover_search.py",
                 "$JTAX\lib62.py")) {
  if (Test-Path $f) { Ok ("present {0}" -f (Split-Path $f -Leaf)) }
  else { Bad "missing: $f" }
}

$manFile = "$ROOT\MC28_MANIFEST.tsv"
if (-not (Test-Path $manFile)) { Bad "missing manifest: $manFile (mc28_ship.sh writes it)" }
else {
  $rows = @(Get-Content $manFile | Select-Object -Skip 1)
  $mOk = 0; $mBad = 0; $mMiss = 0
  foreach ($line in $rows) {
    if ($line.Trim() -eq "") { continue }
    $c = $line -split "`t"
    if ($c.Count -lt 4) { continue }
    $want = $c[0].ToLower(); $rel = $c[3]
    $p = Join-Path $ROOT $rel
    if (-not (Test-Path $p)) { $mMiss++; Bad "manifest: MISSING $rel"; continue }
    $got = (Get-FileHash $p -Algorithm SHA256).Hash.ToLower()
    if ($got -eq $want) { $mOk++ }
    else { $mBad++; Bad "manifest: SHA MISMATCH $rel  PC=$($got.Substring(0,16)).. Mac=$($want.Substring(0,16)).." }
  }
  if ($mBad -eq 0 -and $mMiss -eq 0) { Ok "manifest: $mOk/$($mOk) files re-hash identical to the Mac" }
}

# --- 4. PARITY: the PC re-derives externally verified answers ----------------
Write-Output "-- parity (deterministic node counts + censuses) --"
function Run-Engine([string[]]$eargs, [int]$secs) {
  $o = & $PY -u "$JTAX\mcover_search.py" @eargs 2>&1
  return ($o -join "`n")
}

# P1 -- n=4 (v=3,splits=3): the brute-force ground truth of REPORT §3.2
$p1 = Run-Engine @("4","38","--v","3","--splits","3","--jmin","0")
$p1cen = '{(2, 36): 12, (2, 37): 14, (3, 37): 14, (3, 38): 5, (4, 38): 40}'
if ($p1 -match 'total=12\b')            { Ok "P1 covers 12" }        else { Bad "P1 cover count wrong" }
if ($p1 -match 'walk nodes=2127\b')     { Ok "P1 nodes 2127" }       else { Bad "P1 node count wrong (tree differs!)" }
if ($p1 -match [regex]::Escape($p1cen)) { Ok "P1 census == brute force" } else { Bad "P1 census != brute-force truth" }

# P2 -- n=5 (v=7,splits=4): the designed-SAT control; exercises the FIND path
$p2 = Run-Engine @("5","154","--v","7","--splits","4","--jmin","0")
$p2cen = '{(0, 153): 6, (0, 154): 49, (1, 154): 50}'
if ($p2 -match 'total=224\b')           { Ok "P2 covers 224" }       else { Bad "P2 cover count wrong" }
if ($p2 -match 'walk nodes=47623\b')    { Ok "P2 nodes 47,623" }     else { Bad "P2 node count wrong (tree differs!)" }
if ($p2 -match [regex]::Escape($p2cen)) { Ok "P2 census (SAT path)" } else { Bad "P2 census wrong -- the FIND path differs" }

# P2b -- the shim's own translation + partition self-test
$st = (& $PY -u "$ROOT\mc28_shim.py" --self-test 2>&1) -join "`n"
if ($st -match 'SELF-TEST OK') { Ok "shim self-test (stride partition + engine smoke)" }
else { Bad "shim self-test FAILED" }

# P3 -- the REAL branch, first 200 forest covers (~33 s on the Mac)
if ($Full) {
  Write-Output "-- parity (real branch, 200 forest covers; ~35 s) --"
  $t0 = Get-Date
  $p3 = Run-Engine @("6","872","--v","28","--splits","20","--jmin","1",
                     "--forest","--max-covers","200")
  $el = [int]((Get-Date) - $t0).TotalSeconds
  if ($p3 -match 'total=200\b')                 { Ok "P3 covers 200" } else { Bad "P3 cover count wrong" }
  if ($p3 -match 'histogram K: \{8: 200\}')     { Ok "P3 all K=8 (forest law holds on the PC)" }
  else { Bad "P3 phi-cycle histogram wrong -- the forest constraint differs" }
  if ($p3 -match 'walk nodes=29609908\b')       { Ok "P3 nodes 29,609,908" }
  else { Bad "P3 node count wrong -- THE PC WOULD SEARCH A DIFFERENT TREE. Do not launch." }
  if ($p3 -match 'NO walk in the supply-tight') { Ok "P3 no walk in the first 200" } else { Bad "P3 unexpected verdict" }
  Note "P3 wall: ${el}s (Mac: 33 s) -- scale the shard-time estimate by ${el}/33"
} else {
  Note "P3 (real-branch parity) skipped -- re-run with -Full before the launch"
}

# --- 5. the COVER STREAM: present, verifies, and the consume path works ------
Write-Output "-- cover stream --"
$CF = "$ROOT\covers_v28_forest.txt"
if (-not (Test-Path $CF)) {
  Bad "cover stream missing: $CF (mc28_ship.sh ships it; shards REQUIRE it)"
} else {
  $len = (Get-Item $CF).Length
  Ok ("cover stream present: {0:N0} bytes" -f $len)
  # A thin stride slice: proves the PC verifies the file's body sha256 and can
  # drive the identical prepare/DFS path from it.  Stride 100000 keeps it to a
  # handful of covers (seconds) while exercising every line of the read path.
  $p4 = Run-Engine @("6","872","--v","28","--splits","20","--jmin","1",
                     "--forest","--covers-file",$CF,"--stride","100000",
                     "--offset","0")
  if ($p4 -match 'VERIFIED=True')  { Ok "cover stream body sha256 + total VERIFY on the PC" }
  else { Bad "cover stream FAILED verification on the PC -- do not launch" }
  if ($p4 -match 'histogram K: \{8:') { Ok "covers-file consume path drives the DFS (all K=8)" }
  else { Bad "covers-file consume path did not produce the expected phi-cycle histogram" }
  if ($p4 -match 'NO walk in the supply-tight') { Ok "thin slice: no walk" }
  else { Note "thin slice produced a FIND -- read it, that is the target event" }
}

Write-Output ""
if ($fail -eq 0) { Write-Output "ENV OK -- 0 failures" }
else { Write-Output "*** ENV FAILURES: $fail -- DO NOT LAUNCH ***" }
exit $fail
