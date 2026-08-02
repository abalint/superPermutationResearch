# a0_env.ps1 -- farm-side environment + PARITY check for the s62 A0 gate sweep.
# Read-only apart from $ROOT\_a0probe.  Safe to re-run.  Exit code = failures.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\a0_env.ps1
#
# THE CHECK THAT MATTERS IS PARITY, NOT PRESENCE (s58_env.ps1's philosophy).
# Presence tells you a file arrived; it does not tell you the PC will build the
# same instance the Mac reasoned about.  So the real check here is: regenerate
# the A0 instance for every one of the six controls with the PC's own Python
# and its own copies of p1a_assume/chain7/certificate/gain1, and compare the
# sha256 of the instance TEXT against a Mac-computed constant.  One number
# covers the whole import chain, all six words, and every parsing/ordering
# assumption in between.  (It is a genuine cross-version test: the Mac runs
# CPython 3.14, this box runs 3.11.)
#
# It then RUNS the instance through dlxrun.py for 5 s.  That is deliberate and
# is not redundant with the raw engine smoke:
#   * dlxrun.py's DLX7G constant has NO ".exe" suffix (unlike paircuts.py,
#     which appends one when os.name == "nt").  It works only because Windows
#     CreateProcess appends .exe for an extensionless image name -- a real
#     assumption, and cheaper to test than to argue about.
#   * it passes --epsilon/--seed, so it proves the shipped dlx7g.exe actually
#     supports the eps=0.15 lane.  Two thirds of this sweep is that lane; a
#     build without the flag would fail 12 of 18 cells silently as ERROR rows.
#
# Windows/farm traps respected here:
#   * NO Get-CimInstance / tasklist / WMI -- they HANG or Access-deny for the
#     farm account.  Cores come from $env:NUMBER_OF_PROCESSORS, disk from
#     [System.IO.DriveInfo].
#   * $ErrorActionPreference stays "Continue": with "Stop", ANY native command
#     writing to stderr throws NativeCommandError even at rc 0.  Native calls
#     are checked via $LASTEXITCODE instead.
#   * everything this script writes goes under F:\superpermFarm\ -- never C:,
#     never F:\audioPrime.  (s58_env.ps1 used $env:TEMP; $ROOT\_a0probe keeps
#     the "F: only" rule literally true.)
#   * do NOT add `*> some.log` to the caller: PowerShell redirection writes
#     UTF-16LE and Mac-side grep then finds nothing, which is indistinguishable
#     from "pattern absent".  This script prints to stdout; let ssh carry it.
param([switch]$Full)
$ErrorActionPreference = "Continue"

$ROOT  = "F:\superpermFarm\untargeted"
$REPO  = "$ROOT\repo"
$PY    = "$ROOT\pyenv\Scripts\upyw.exe"
$DLX   = "$REPO\analysis\trackc\dlx7g.exe"
$PROBE = "$ROOT\_a0probe"
$fail  = 0
function Ok  ($m) { Write-Output "  [ok]   $m" }
function Bad ($m) { Write-Output "  [FAIL] $m"; $script:fail++ }
function Note($m) { Write-Output "  ...    $m" }

# Mac-computed reference sha256 of the A0 instance TEXT
# (p1a_assume.build_variant(extract(<word>), "A0", 0)[0]) for each of the six
# out/s59/cliff/geninst.py PANEL controls.  Computed on the Mac at ship time
# with CPython 3.14 and pinned here so a mismatch is loud rather than
# interesting.  Regenerate with the same one-liner if the chain ever changes.
$MAC_A0_SHA = @{
  "5906.up-02d771908307"   = "6cb3ae0b4db365783dc1b9a9aa064d5c30b84530ee3bc0a215ca7751b4080e3e"
  "5906.rbnd-2641d60c9d5c" = "422e1ae62c70aee9b7ae8bac018f5bb0177d8b5d3e693b09d272e6a2180959c9"
  "5906.up-331228e22360"   = "ae596eecdf25c96f49ec1c8504c5bcfe45104eb20bb32a8e6c1cb6e378b3e763"
  "5906.up-6f42b3603dac"   = "9ff75d5ccf25fb5b4a6c98a751aab0a69f18b70e263f350e26a1f33370492aaf"
  "5906.up-0a065898a821"   = "17fa05f0741b544d31f46ce4ab90243b607aead7856c0d09eece5a0625cac7df"
  "5907.up-6f2e8d9df51c"   = "7394abd33dcbf3b910eee45d1a74aa630f28d4a55e940c2cff0a42d06d81ab9e"
}
# Mac-measured instance shape, same run -- a cheap second signal that says
# WHICH control drifted if a sha ever mismatches.
$MAC_A0_SHAPE = @{
  "5906.up-02d771908307"   = "620/3228"
  "5906.rbnd-2641d60c9d5c" = "615/3173"
  "5906.up-331228e22360"   = "610/3130"
  "5906.up-6f42b3603dac"   = "600/3136"
  "5906.up-0a065898a821"   = "590/2936"
  "5907.up-6f2e8d9df51c"   = "690/4440"
}

Write-Output "=== s62 A0 gate farm environment  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
New-Item -ItemType Directory -Force -Path $PROBE | Out-Null

# --- 1. host + idleness ------------------------------------------------------
Write-Output "-- host --"
$cores = [int]$env:NUMBER_OF_PROCESSORS
Ok "logical processors: $cores  (18 shards leaves $($cores-18) for transcription)"
if ($cores -lt 20) { Bad "fewer than 20 cores -- do not run 18 shards here" }
$ours = @(Get-Process -Name upyw -EA SilentlyContinue)
if ($ours.Count -gt 0) { Bad "$($ours.Count) upyw.exe already alive (a sweep is running)" }
else { Ok "no upyw.exe (our shards) running" }
$tpy = @(Get-Process -Name python,pythonw -EA SilentlyContinue).Count
Note "python.exe on the box: $tpy  (transcription service -- NEVER kill)"
# DriveInfo, not Get-CimInstance (which hangs for this account).
$d = [System.IO.DriveInfo]::new("F")
$freeGB = [math]::Round($d.AvailableFreeSpace / 1GB, 1)
if ($freeGB -lt 5) { Bad "only $freeGB GB free on F:" } else { Ok "F: free: $freeGB GB" }

# --- 2. interpreter + engine -------------------------------------------------
Write-Output "-- interpreter + engine --"
if (-not (Test-Path $PY)) { Bad "interpreter missing: $PY (run untargeted_env.ps1 first)" }
else {
  # upyw.exe is the DELIBERATELY RENAMED venv python: the abort script matches
  # on process name, so it can never kill the transcription service's
  # python.exe.  Do not "fix" the name.
  Ok "upyw.exe present: $((& $PY -c "import sys;print(sys.version.split()[0])") 2>&1)"
}

if (-not (Test-Path $DLX)) { Bad "engine missing: $DLX (s58_ship.sh builds it; a0_ship.sh does NOT)" }
else {
  Ok "dlx7g.exe present ($((Get-Item $DLX).Length) bytes, built $((Get-Item $DLX).LastWriteTime))"
  # The whole sweep is an exit-code measurement, so prove the binary really is
  # three-valued before trusting 18 cells of verdicts.
  $pi = "$PROBE\smoke_inst.txt"
  "1 1 1 1", "0 -1 0" | Set-Content $pi -Encoding ASCII
  & $DLX $pi --time-limit 5 --max-nodes 1000 --out "$PROBE\smoke_sol.txt" 2>&1 | Out-Null
  Note "engine smoke exit code: $LASTEXITCODE (0 SAT / 2 UNSAT / 3 UNKNOWN)"
  if ($LASTEXITCODE -notin @(0,2,3)) { Bad "engine returned an unexpected exit code" }
  else { Ok "engine runs and returns a three-valued code" }
}

# --- 3. payload presence + the SECOND END of the sha256 manifest -------------
Write-Output "-- payload + manifest re-hash --"
foreach ($f in @("$ROOT\a0_shim.py",
                 "$REPO\analysis\counting\s62\a0gate.py")) {
  if (Test-Path $f) { Ok ("present {0}" -f (Split-Path $f -Leaf)) }
  else { Bad "missing: $f" }
}

$manFile = "$ROOT\A0_MANIFEST.tsv"
if (-not (Test-Path $manFile)) { Bad "missing manifest: $manFile (a0_ship.sh writes it)" }
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
  if ($mBad -eq 0 -and $mMiss -eq 0) { Ok "manifest: all $mOk file(s) byte-identical to the Mac" }
  else { Note "manifest: $mOk ok / $mBad mismatched / $mMiss missing" }
}

# --- 4. PARITY: the PC rebuilds the Mac's A0 instances (the real check) ------
Write-Output "-- A0 instance parity --"
if ((Test-Path $PY) -and (Test-Path "$REPO\out\s56\p1a\p1a_assume.py")) {
  Push-Location $REPO
  $p = "$PROBE\a0probe.py"
  # Written as a SHIPPED-style file, never echoed through cmd: quoting through
  # ssh -> cmd -> powershell eats characters (the s58 vcvars lesson).
  @(
    'import os, sys, hashlib',
    'REPO = os.path.abspath(".")',
    'sys.path.insert(0, os.path.join(REPO, "out", "s56", "p1a"))',
    'sys.path.insert(0, os.path.join(REPO, "out", "s57", "proposer"))',
    'sys.path.insert(0, os.path.join(REPO, "analysis", "cover7"))',
    'sys.path.insert(0, os.path.join(REPO, "..", "extraDocs", "superpermutation-examples", "scripts"))',
    'import p1a_assume as P',
    'import dlxrun',
    'PANEL = [',
    '  ("5906.up-02d771908307",   "data/upstream5906/5906.up-02d771908307.txt"),',
    '  ("5906.rbnd-2641d60c9d5c", "data/novel5906c/5906.rbnd-2641d60c9d5c.txt"),',
    '  ("5906.up-331228e22360",   "data/upstream5906/5906.up-331228e22360.txt"),',
    '  ("5906.up-6f42b3603dac",   "data/upstream5906/5906.up-6f42b3603dac.txt"),',
    '  ("5906.up-0a065898a821",   "data/upstream5906/5906.up-0a065898a821.txt"),',
    '  ("5907.up-6f2e8d9df51c",   "data/upstream5907/5907.up-6f2e8d9df51c.txt"),',
    ']',
    'first = None',
    'for base, wp in PANEL:',
    '    ex = P.extract(os.path.join(REPO, wp))',
    '    txt, rowmap, fixed, nc, nr, npool = P.build_variant(ex, "A0", 0)',
    '    print("A0SHA", base, hashlib.sha256(txt.encode()).hexdigest(), str(nc) + "/" + str(nr), flush=True)',
    '    if first is None:',
    '        first = txt',
    'r = dlxrun.run(first, time_limit=5.0, tag="a0env", outdir=sys.argv[1], epsilon=0.15, seed=1)',
    'print("DLXRUN", r["verdict"], round(r["seconds"], 2), r["rc"], flush=True)',
    'print("PROBE_OK", flush=True)'
  ) | Set-Content $p -Encoding ASCII
  $out = (& $PY -u $p $PROBE) 2>&1
  Pop-Location
  $seen = 0
  foreach ($line in $out) {
    $s = "$line"
    if ($s -match '^A0SHA (\S+) (\w+) (\S+)') {
      $base = $Matches[1]; $sha = $Matches[2]; $shape = $Matches[3]
      $seen++
      if (-not $MAC_A0_SHA.ContainsKey($base)) { Bad "PARITY unknown control in probe output: $base"; continue }
      if ($sha -eq $MAC_A0_SHA[$base]) { Ok "PARITY $base  sha == Mac  ($shape cols/rows)" }
      else {
        Bad "PARITY $base sha MISMATCH: PC=$sha Mac=$($MAC_A0_SHA[$base])"
        if ($shape -ne $MAC_A0_SHAPE[$base]) { Note "  shape also differs: PC=$shape Mac=$($MAC_A0_SHAPE[$base])" }
        else { Note "  shape MATCHES ($shape) -- drift is in content/ordering, not the word file" }
      }
    }
    elseif ($s -match '^DLXRUN (\S+) (\S+) (\S+)') {
      $v = $Matches[1]
      Note "dlxrun 5 s probe on control #1, epsilon=0.15: verdict=$v secs=$($Matches[2]) rc=$($Matches[3])"
      if ($v -in @("SAT","UNSAT","UNKNOWN")) {
        Ok "dlxrun reaches the engine and the eps lane works (extensionless DLX7G resolves on Windows)"
        if ($v -eq "SAT") { Write-Output "  *** A0 SAT IN A 5 s PROBE -- stop and gate this on the Mac ***" }
      }
      else { Bad "dlxrun returned $v -- engine path or --epsilon support is broken (12 of 18 cells are the eps lane)" }
    }
    elseif ($s -match '^PROBE_OK') { Ok "import chain resolves farm-side" }
    else { Note $s }
  }
  if ($seen -ne 6) { Bad "PARITY only $seen of 6 controls reported (probe died early -- see the lines above)" }
}
else { Bad "cannot run the parity probe (interpreter or p1a_assume.py missing)" }

New-Item -ItemType Directory -Force -Path "$ROOT\runs" | Out-Null
Write-Output ""
if ($fail -eq 0) { Write-Output "A0 ENV OK -- 0 failures" }
else { Write-Output "A0 ENV NOT READY -- $fail failure(s) above" }
exit $fail
