# qsb_env.ps1 -- farm-side environment + PARITY check for the s62 QS-B
# verdict-mix sweep.  Read-only apart from $ROOT\_qsbprobe.  Safe to re-run.
# Exit code = failure count.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\qsb_env.ps1
#
# THE CHECK THAT MATTERS IS PARITY, NOT PRESENCE (a0_env.ps1 / s58_env.ps1
# philosophy).  Presence tells you a file arrived; it does not tell you the PC
# will draw the same atom sets, build the same instance, or get the same
# verdict as the Mac.  This sweep's entire product is a VERDICT MIX over a
# pseudo-random sample stream, so the two things that must be identical
# cross-platform are:
#
#   1. THE SAMPLE STREAM AND THE INSTANCE IT BUILDS.  qsbsweep.draw() is
#      `random.Random(12345 + chain)` + `rng.sample(pool, k)`, and the pool is
#      `sorted({r["loop"] for r in inst["rows"]})`.  Any drift in the chain
#      build, the loop ordering, or the instance encoding silently produces a
#      DIFFERENT experiment that still looks healthy.  So the PC regenerates
#      six pinned (chain, mult, sample) instances with its own Python and its
#      own copies of chain7/p1a_assume/certificate/gain1 and compares the
#      sha256 of the instance TEXT against Mac-computed constants.  One number
#      per pin covers the whole import chain and every ordering assumption in
#      it.  (Genuine cross-version test: the Mac runs CPython 3.14, this box
#      runs 3.11.)
#   2. THE ENGINE'S VERDICT ON THOSE BYTES.  Four of the six pins are solved
#      here at epsilon = 0 and the verdict (and node count) compared with the
#      Mac's.  The refutation lane is deterministic by construction -- dlx7g
#      skips its restart machinery when epsilon == 0 -- so a differing verdict
#      or node count means a different binary or a different instance, not
#      luck.  This is the check that turns "the files copied" into "the PC is
#      running the Mac's experiment".
#
# It also exercises dlxrun.py end to end because dlxrun.py's DLX7G constant has
# NO ".exe" suffix (unlike paircuts.py, which appends one when os.name ==
# "nt").  It works only because Windows CreateProcess appends .exe for an
# extensionless image name -- a real assumption, cheaper to test than to argue
# about.  qsbsweep.py rebinds dlxrun.DLX7G to a resolved path anyway; the probe
# below deliberately does NOT, so the raw assumption is the thing under test.
#
# NOTE this sweep uses the epsilon = 0 lane ONLY, so unlike a0_env.ps1 there is
# nothing to prove about --epsilon support: dlxrun.run does not even pass the
# flag when epsilon == 0.  What must be proven instead is DETERMINISM parity,
# which is what the verdict+nodes pins do.
#
# Windows/farm traps respected here:
#   * NO Get-CimInstance / tasklist / WMI -- they HANG or Access-deny for the
#     farm account.  Cores come from $env:NUMBER_OF_PROCESSORS, disk from
#     [System.IO.DriveInfo].
#   * $ErrorActionPreference stays "Continue": with "Stop", ANY native command
#     writing to stderr throws NativeCommandError even at rc 0.  Native calls
#     are checked via $LASTEXITCODE instead.
#   * everything this script writes goes under F:\superpermFarm\ -- never C:,
#     never F:\audioPrime.
#   * do NOT add `*> some.log` to the caller: PowerShell redirection writes
#     UTF-16LE and Mac-side grep then finds nothing, which is indistinguishable
#     from "pattern absent".  This script prints to stdout; let ssh carry it.
param([switch]$Full)
$ErrorActionPreference = "Continue"

$ROOT  = "F:\superpermFarm\untargeted"
$REPO  = "$ROOT\repo"
$PY    = "$ROOT\pyenv\Scripts\upyw.exe"
$DLX   = "$REPO\analysis\trackc\dlx7g.exe"
$PROBE = "$ROOT\_qsbprobe"
$fail  = 0
function Ok  ($m) { Write-Output "  [ok]   $m" }
function Bad ($m) { Write-Output "  [FAIL] $m"; $script:fail++ }
function Note($m) { Write-Output "  ...    $m" }

# ---------------------------------------------------------------- THE PINS --
# Mac-computed reference values, CPython 3.14, this repo state, at ship time.
# Each row is  chain|mult|sample|k|cols/rows|sha256(instance text)|verdict|nodes
# with verdict/nodes empty where the pin is sha-only (the two `full` pins are
# sha-only on purpose: their verdict is a TIMEOUT and therefore budget- and
# machine-dependent, so pinning it would be pinning noise).
# The four solved pins were chosen to be CHEAP and DECIDED: all four are
# structural refutations that exhaust in a handful of nodes, so this check
# costs well under a second while still proving the engine agrees byte-for-byte
# on what it is refuting.
$PINS = @(
  "0|3.00|0|342|570/1627|dce10b09c8ca99a30d739a4a0608a3be790b914a1eaa5a540c47f5aa62cb5e95|UNSAT|1",
  "0|4.25|2|484|570/2329|44a6f1e1b311befac7ad7c0343196628ece9b846e6b36dbc410eed303efc10d6|UNSAT|4",
  "0|full|0|557|570/2662|a954fcf7cbb1056b8084f4f915b85eece54b68a5ecba8b78acf4b96ffbba627b||",
  "24|3.00|0|336|560/1516|5c612551a1c20dff0c36129153bed394b75d018ea8e211bec7255c2901986dcd|UNSAT|1",
  "24|4.50|0|504|560/2329|6b27b8c89e5c0fc5be074718b4551c56e2434ee37e3d03ef1fee9bc7e2a2bd56|UNSAT|2",
  "24|full|0|542|560/2517|28aff12c5bafcbddfc0aad37399ac6c68a13bb50244d805caf20adc09b4c24d0||"
)
# Mac-measured chain shape, same run -- a cheap second signal that says WHICH
# stage drifted if a sha ever mismatches (chain build vs draw vs encoding).
$MAC_SHAPE = @{ "0" = "R=114 pool=557"; "24" = "R=112 pool=542" }

Write-Output "=== s62 QS-B farm environment  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
New-Item -ItemType Directory -Force -Path $PROBE | Out-Null

# --- 1. host + idleness ------------------------------------------------------
Write-Output "-- host --"
$cores = [int]$env:NUMBER_OF_PROCESSORS
Ok "logical processors: $cores  (24 shards leaves $($cores-24) for transcription)"
if ($cores -lt 26) { Bad "fewer than 26 cores -- do not run 24 shards here" }
$ours = @(Get-Process -Name upyw -EA SilentlyContinue)
if ($ours.Count -gt 0) { Bad "$($ours.Count) upyw.exe already alive (a sweep is running)" }
else { Ok "no upyw.exe (our shards) running" }
$tpy = @(Get-Process -Name python,pythonw -EA SilentlyContinue).Count
Note "python.exe on the box: $tpy  (transcription service -- NEVER kill)"
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

if (-not (Test-Path $DLX)) { Bad "engine missing: $DLX (s58_ship.sh builds it; qsb_ship.sh does NOT)" }
else {
  Ok "dlx7g.exe present ($((Get-Item $DLX).Length) bytes, built $((Get-Item $DLX).LastWriteTime))"
  # The whole sweep is an exit-code measurement, so prove the binary really is
  # three-valued before trusting thousands of cells of verdicts.
  $pi = "$PROBE\smoke_inst.txt"
  "1 1 1 1", "0 -1 0" | Set-Content $pi -Encoding ASCII
  & $DLX $pi --time-limit 5 --max-nodes 1000 --out "$PROBE\smoke_sol.txt" 2>&1 | Out-Null
  Note "engine smoke exit code: $LASTEXITCODE (0 SAT / 2 UNSAT / 3 UNKNOWN)"
  if ($LASTEXITCODE -notin @(0,2,3)) { Bad "engine returned an unexpected exit code" }
  else { Ok "engine runs and returns a three-valued code" }
}

# --- 3. payload presence + the SECOND END of the sha256 manifest -------------
Write-Output "-- payload + manifest re-hash --"
foreach ($f in @("$ROOT\qsb_shim.py",
                 "$REPO\analysis\counting\s62\qsbsweep.py",
                 "$REPO\analysis\farm\farm_chains.jsonl")) {
  if (Test-Path $f) { Ok ("present {0}" -f (Split-Path $f -Leaf)) }
  else { Bad "missing: $f" }
}

$manFile = "$ROOT\QSB_MANIFEST.tsv"
if (-not (Test-Path $manFile)) { Bad "missing manifest: $manFile (qsb_ship.sh writes it)" }
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

# --- 4. PARITY: the PC redraws the Mac's samples and re-solves them ----------
Write-Output "-- sample-stream / instance / verdict parity --"
if ((Test-Path $PY) -and (Test-Path "$REPO\analysis\counting\s62\qsbsweep.py")) {
  Push-Location $REPO
  $p = "$PROBE\qsbprobe.py"
  # Written as a SHIPPED-style file, never echoed through cmd: quoting through
  # ssh -> cmd -> powershell eats characters (the s58 vcvars lesson).
  # It imports the INSTRUMENT and calls its own draw()/k_of(), so this tests
  # the code that will actually run, not a re-implementation of it.
  @(
    'import hashlib, os, re, sys',
    'REPO = os.path.abspath(".")',
    'sys.path.insert(0, os.path.join(REPO, "analysis", "counting", "s62"))',
    'import qsbsweep as Q',
    'import p1a_assume as P',
    'import dlxrun',
    'PINS = [(0, 3.0, 0, 1), (0, 4.25, 2, 1), (0, "full", 0, 0),',
    '        (24, 3.0, 0, 1), (24, 4.5, 0, 1), (24, "full", 0, 0)]',
    'cache = {}',
    'for chain, m, s, solve in PINS:',
    '    ch = Q.load_chain(cache, chain)',
    '    inst, R, pool = ch["inst"], ch["R"], ch["pool"]',
    '    k = Q.k_of(m, R, len(pool))',
    '    atoms = Q.draw(chain, pool, k, s + 1)[s]',
    '    rows = [r for r in inst["rows"] if r["loop"] in atoms]',
    '    txt = P.instance_text(inst["columns"], rows, set(inst["roots"]))',
    '    sha = hashlib.sha256(txt.encode()).hexdigest()',
    '    v = n = "-"',
    '    if solve:',
    '        r = dlxrun.run(txt, time_limit=20.0, tag="qsbenv", outdir=sys.argv[1], epsilon=0.0, seed=0)',
    '        v = r["verdict"]',
    '        mm = re.search(r"nodes=(\d+)", r["result_line"] or "")',
    '        n = mm.group(1) if mm else "-"',
    '    print("PIN %s|%s|%d|%d|%d/%d|%s|%s|%s" % (chain, Q.mult_label(m), s, k,',
    '          len(inst["columns"]), len(rows), sha, v, n), flush=True)',
    '    print("SHAPE %s R=%d pool=%d" % (chain, R, len(pool)), flush=True)',
    'print("PROBE_OK", flush=True)'
  ) | Set-Content $p -Encoding ASCII
  $out = (& $PY -u $p $PROBE) 2>&1
  Pop-Location

  $want = @{}
  foreach ($row in $PINS) { $c = $row -split '\|'; $want["$($c[0])|$($c[1])|$($c[2])"] = $c }
  $seen = 0
  foreach ($line in $out) {
    $s = "$line"
    if ($s -match '^PIN (.+)$') {
      $c = $Matches[1] -split '\|'
      $key = "$($c[0])|$($c[1])|$($c[2])"
      $seen++
      if (-not $want.ContainsKey($key)) { Bad "PARITY unknown pin in probe output: $key"; continue }
      $w = $want[$key]
      $tagtxt = "chain#$($c[0]) mult=$($c[1]) sample=$($c[2])"
      if ($c[5] -eq $w[5]) {
        Ok "PARITY $tagtxt  instance sha == Mac  (k=$($c[3]) $($c[4]) cols/rows)"
      } else {
        Bad "PARITY $tagtxt instance sha MISMATCH: PC=$($c[5].Substring(0,16)).. Mac=$($w[5].Substring(0,16)).."
        if ($c[4] -ne $w[4]) { Note "  shape also differs: PC=$($c[4]) Mac=$($w[4]) -- the CHAIN BUILD or the draw drifted" }
        else { Note "  shape MATCHES ($($c[4])) -- drift is in content/ordering, not in k or the row count" }
      }
      if ($w[6] -ne "") {
        if ($c[6] -eq $w[6]) {
          Ok "PARITY $tagtxt  verdict $($c[6]) == Mac (nodes PC=$($c[7]) Mac=$($w[7]))"
          if ($c[7] -ne $w[7]) { Note "  node counts differ -- same verdict, different search; report it, do not launch blind" }
        } else {
          Bad "PARITY $tagtxt VERDICT MISMATCH: PC=$($c[6]) Mac=$($w[6]) -- the refutation lane is deterministic, so this is a different engine or a different instance"
        }
      }
    }
    elseif ($s -match '^SHAPE (\S+) (.+)$') {
      if ($MAC_SHAPE[$Matches[1]] -ne $Matches[2]) {
        Bad "chain #$($Matches[1]) shape PC=$($Matches[2]) Mac=$($MAC_SHAPE[$Matches[1]])"
      }
    }
    elseif ($s -match '^PROBE_OK') { Ok "import chain resolves farm-side and dlxrun reached the engine" }
    else { Note $s }
  }
  if ($seen -ne 6) { Bad "PARITY only $seen of 6 pins reported (probe died early -- see the lines above)" }
}
else { Bad "cannot run the parity probe (interpreter or qsbsweep.py missing)" }

New-Item -ItemType Directory -Force -Path "$ROOT\runs" | Out-Null
Write-Output ""
if ($fail -eq 0) { Write-Output "QSB ENV OK -- 0 failures" }
else { Write-Output "QSB ENV NOT READY -- $fail failure(s) above" }
exit $fail
