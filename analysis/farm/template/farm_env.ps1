# farm_env.ps1 -- THE farm-side environment + PARITY check.  One, parameterized
# by <Tag>_CONFIG.tsv + <Tag>_PARITY.tsv + <Tag>_MANIFEST.tsv (s64 P5).
# Read-only apart from $Root\_probe.  Safe to re-run.  Exit code = failures.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File <root>\farm_env.ps1 -Tag mc28
#   ... -Tag mc28 -Full        # also runs the parity rows marked full=1
#   ... -Tag mc28 -Root F:\superpermFarm\untargeted\s64tpl_scratch
#
# THE CHECK THAT MATTERS IS PARITY, NOT PRESENCE.  Presence tells you a file
# arrived; it does not tell you the PC will SEARCH THE SAME TREE the Mac
# reasoned about.  Our engines are deterministic (lexicographic orders, no RNG),
# so every output is an integer we can pin: node counts, cover counts, censuses.
# A mismatch means the PC would produce a DIFFERENT search -- and when the
# product of a sweep is a NEGATIVE ("the cell is empty"), a silently different
# search is the one failure mode that cannot be detected after the fact.
# DO NOT LAUNCH THROUGH A PARITY FAILURE.
#
# The parity rows live in <Tag>_PARITY.tsv (columns below), so adding an
# instrument means adding data, not another 200-line _env.ps1:
#
#   id     short label, printed
#   full   1 = only under -Full (the expensive rows)
#   script repo-relative script to run under the venv python, or @adapter
#   args   space-separated argv
#   expect a .NET regex the combined stdout+stderr must match
#   desc   what a failure means, printed on failure
#
# Rows sharing (script,args) run the engine ONCE and check several expectations.
#
# WINDOWS/FARM TRAPS RESPECTED HERE (each one cost a session):
#   * NO Get-CimInstance / tasklist / WMI -- they HANG or Access-deny for the
#     farm account.  Cores from $env:NUMBER_OF_PROCESSORS, disk from
#     [System.IO.DriveInfo], processes from Get-Process.
#   * $ErrorActionPreference stays "Continue": with "Stop", ANY native command
#     writing to stderr throws NativeCommandError even at rc 0.
#   * everything written stays under F:\superpermFarm\ -- never C:, never
#     F:\audioPrime.
#   * do NOT add `*> some.log` to the caller: PowerShell redirection writes
#     UTF-16LE and Mac-side grep then finds nothing, which is indistinguishable
#     from "pattern absent".  This prints to stdout; let ssh carry it.
#   * running the adapter's own --self-test HERE, on the target platform, is
#     what caught the s63 CRLF bug: `open(p,"w")` on Windows wrote CRLF while
#     the sha256 was accumulated over pre-translation bytes, so every shard
#     would have exited 4.  A parity script that only COMPARES NUMBERS would
#     have missed it; it was caught by running the round trip here.
param(
  [Parameter(Mandatory=$true)][string]$Tag,
  [string]$Root = "F:\superpermFarm\untargeted",
  [string]$Py   = "",
  [switch]$Full
)
$ErrorActionPreference = "Continue"

if ($Py -eq "") { $Py = "F:\superpermFarm\untargeted\pyenv\Scripts\upyw.exe" }
$REPO  = "$Root\repo"
$PROBE = "$Root\_probe"
$fail  = 0
function Ok  ($m) { Write-Output "  [ok]   $m" }
function Bad ($m) { Write-Output "  [FAIL] $m"; $script:fail++ }
function Note($m) { Write-Output "  ...    $m" }

# ------------------------------------------------------------------ config --
$cfgFile = "$Root\${Tag}_CONFIG.tsv"
$cfg = @{}
$sidefiles = @()
if (Test-Path $cfgFile) {
  foreach ($line in (Get-Content $cfgFile | Select-Object -Skip 1)) {
    if ($line.Trim() -eq "") { continue }
    $c = $line -split "`t", 2
    if ($c.Count -lt 2) { continue }
    if ($c[0] -eq "sidefile") { $sidefiles += $c[1] } else { $cfg[$c[0]] = $c[1] }
  }
}
$what    = if ($cfg.ContainsKey("what")) { $cfg["what"] } else { $Tag }
$adapter = if ($cfg.ContainsKey("adapter")) { $cfg["adapter"] } else { "" }

Write-Output "=== farm env + parity: $Tag  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
Write-Output "    $what"
Write-Output "    root: $Root"
New-Item -ItemType Directory -Force -Path $PROBE | Out-Null

# --- 1. host + idleness ------------------------------------------------------
Write-Output "-- host --"
$cores = [int]$env:NUMBER_OF_PROCESSORS
Ok "logical processors: $cores"
$wantShards = if ($cfg.ContainsKey("shards")) { [int]$cfg["shards"] } else { 0 }
if ($wantShards -gt 0 -and $cores -lt ($wantShards + 2)) {
  Bad "only $cores cores for $wantShards shards -- re-size before launching (leave >= 2 for the transcription service)"
}
# Process NAME, never a command-line match: a `pgrep -f`-style test matches the
# monitor's own command line.  upyw.exe is the deliberately renamed venv python
# (process-identity guard) so this can never see the transcription service.
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
if (-not (Test-Path $Py)) { Bad "interpreter missing: $Py (run untargeted_env.ps1 first)" }
else {
  $ver = (& $Py -c "import sys;print(sys.version.split()[0])") 2>&1
  Ok "upyw.exe present: $ver"
}

# --- 3. payload + the SECOND END of the sha256 manifest ----------------------
Write-Output "-- payload + manifest re-hash --"
$manFile = "$Root\${Tag}_MANIFEST.tsv"
if (-not (Test-Path $manFile)) { Bad "missing manifest: $manFile (farm_ship.sh writes it)" }
else {
  $rows = @(Get-Content $manFile | Select-Object -Skip 1)
  $mOk = 0; $mBad = 0; $mMiss = 0
  foreach ($line in $rows) {
    if ($line.Trim() -eq "") { continue }
    $c = $line -split "`t"
    if ($c.Count -lt 4) { continue }
    $want = $c[0].ToLower(); $rel = $c[3]
    $p = Join-Path $Root $rel
    if (-not (Test-Path $p)) { $mMiss++; Bad "manifest: MISSING $rel"; continue }
    $got = (Get-FileHash $p -Algorithm SHA256).Hash.ToLower()
    if ($got -eq $want) { $mOk++ }
    else { $mBad++; Bad "manifest: SHA MISMATCH $rel  PC=$($got.Substring(0,16)).. Mac=$($want.Substring(0,16)).." }
  }
  if ($mBad -eq 0 -and $mMiss -eq 0) { Ok "manifest: $mOk files re-hash identical to the Mac" }
}
foreach ($sf in $sidefiles) {
  $p = "$Root\$sf"
  if (Test-Path $p) { Ok ("side file present: {0} ({1:N0} bytes)" -f $sf, (Get-Item $p).Length) }
  else { Bad "side file missing: $sf (shards that require it will refuse)" }
}

# --- 4. PARITY: the PC re-derives externally verified answers ----------------
$parFile = "$Root\${Tag}.parity.tsv"
if (-not (Test-Path $parFile)) {
  Note "no parity spec ($parFile) -- presence-only verification, which is WEAK"
} else {
  Write-Output "-- parity (deterministic outputs; the check that matters) --"
  $cache = @{}
  foreach ($line in (Get-Content $parFile)) {
    if ($line.Trim() -eq "" -or $line.StartsWith("#")) { continue }
    $c = $line -split "`t"
    if ($c.Count -lt 5) { continue }
    $id = $c[0]; $isFull = ($c[1] -eq "1"); $script = $c[2]
    $argstr = $c[3]; $expect = $c[4]
    $desc = if ($c.Count -ge 6) { $c[5] } else { "" }
    if ($isFull -and -not $Full) {
      if (-not $cache.ContainsKey("skip:$id")) {
        Note "$id skipped (parity row is full=1) -- re-run with -Full before the launch"
        $cache["skip:$id"] = $true
      }
      continue
    }
    $target = if ($script -eq "@adapter") { "$Root\$adapter" } else { "$REPO\$($script -replace '/','\')" }
    $key = "$target|$argstr"
    if (-not $cache.ContainsKey($key)) {
      if (-not (Test-Path $target)) {
        Bad "$id : script not on the box: $target"
        $cache[$key] = "SCRIPT-MISSING"
      } else {
        $eargs = @($argstr -split '\s+' | Where-Object { $_ -ne "" })
        $t0 = Get-Date
        $out = & $Py -u $target @eargs 2>&1
        $el = [int]((Get-Date) - $t0).TotalSeconds
        $cache[$key] = ($out -join "`n")
        $cache["secs:$key"] = $el
        Note "$id ran in ${el}s : $script $argstr"
      }
    }
    $text = $cache[$key]
    if ($text -match $expect) { Ok "$id $desc" }
    else { Bad "$id $desc -- expected /$expect/ ; THE PC WOULD BEHAVE DIFFERENTLY. Do not launch." }
  }
}

Write-Output ""
if ($fail -eq 0) { Write-Output "ENV OK -- 0 failures" }
else { Write-Output "*** ENV FAILURES: $fail -- DO NOT LAUNCH ***" }
exit $fail
