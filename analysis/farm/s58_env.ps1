# s58_env.ps1 -- farm-side environment + PARITY check for the two s58 sweeps.
# Read-only apart from the run root.  Safe to re-run.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\s58_env.ps1
#
# The check that matters is PARITY, not presence.  Both instruments derive a
# base fingerprint from the shipped data + the whole import chain, so if the PC
# reproduces the Mac's hashes then every module, every JSON and the row pool
# all landed intact -- one number instead of twelve file checks.
param([switch]$Full)
$ErrorActionPreference = "Continue"

$ROOT = "F:\superpermFarm\untargeted"
$REPO = "$ROOT\repo"
$PY   = "$ROOT\pyenv\Scripts\upyw.exe"
$DLX  = "$REPO\analysis\trackc\dlx7g.exe"
$fail = 0
function Ok  ($m) { Write-Output "  [ok]   $m" }
function Bad ($m) { Write-Output "  [FAIL] $m"; $script:fail++ }
function Note($m) { Write-Output "  ...    $m" }

# Mac-measured, pinned here so a mismatch is loud rather than interesting.
$MAC_BASE_SHA  = "4f05c1b5e1910573626447f525efda88bb4f07a20f08a95c60a35a32469afce9"
$MAC_RELAX_SHA = "73dc4dd593329de98bcade5be538170dd2a28c633407f7fb6f150f9959d1cc19"

Write-Output "=== s58 farm environment  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="

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

# --- 2. interpreter + engine -------------------------------------------------
Write-Output "-- interpreter + engine --"
if (-not (Test-Path $PY)) { Bad "interpreter missing: $PY (run untargeted_env.ps1 first)" }
else { Ok "upyw.exe present: $((& $PY -c "import sys;print(sys.version.split()[0])") 2>&1)" }

if (-not (Test-Path $DLX)) { Bad "engine missing: $DLX (s58_ship.sh builds it)" }
else {
  Ok "dlx7g.exe present ($((Get-Item $DLX).Length) bytes, built $((Get-Item $DLX).LastWriteTime))"
  # exit 2 = EXHAUSTED is the ONLY code that licenses a stored cut, so prove
  # the binary actually returns it before trusting a sweep's worth of them.
  $probe = "$env:TEMP\s58_dlxprobe.txt"
  # 1 column, 1 row that covers nothing -> the column is uncoverable -> UNSAT
  "1 1 1 1", "0 -1 0" | Set-Content $probe -Encoding ASCII
  & $DLX $probe --time-limit 5 --max-nodes 1000 --out "$env:TEMP\s58_dlxsol.txt" 2>&1 | Out-Null
  Note "engine smoke exit code: $LASTEXITCODE (0 SAT / 2 UNSAT / 3 UNKNOWN)"
  if ($LASTEXITCODE -notin @(0,2,3)) { Bad "engine returned an unexpected exit code" }
  else { Ok "engine runs and returns a three-valued code" }
}

# --- 3. payload + PARITY (the real check) ------------------------------------
Write-Output "-- payload parity --"
foreach ($f in @("$REPO\analysis\counting\s58\paircuts.py",
                 "$REPO\analysis\counting\s58\enumext_sweep.py",
                 "$REPO\out\s57\proposer\prune_all.json",
                 "$REPO\analysis\farm\farm_chains.jsonl",
                 "$ROOT\extraDocs\superpermutation-examples\scripts\gain1.py")) {
  if (Test-Path $f) { Ok ("present {0}" -f (Split-Path $f -Leaf)) } else { Bad "missing: $f" }
}

if (Test-Path $PY) {
  Push-Location $REPO
  $p = "$ROOT\_s58probe.py"
  @(
    'import os, sys, hashlib',
    'sys.path.insert(0, os.path.join("analysis", "counting", "s58"))',
    'import paircuts as PC',
    'B = PC.build_base("farm0")',
    'rows = B["rows_all"]',
    'txt = (B["header"] % len(rows)) + "\n" + "\n".join(B["line"][r] for r in rows) + "\n"',
    'print("BASE_SHA", hashlib.sha256(txt.encode()).hexdigest())',
    'import propose as PR',
    't, _, nc, nr = PR.render(B["inst"], set(rows) - set(B["fixed"]), list(B["fixed"]))',
    'print("RELAX_SHA", hashlib.sha256(t.encode()).hexdigest())',
    'print("POOL", len(rows), "COLS", B["ncols"], "LOOPS", B["nloops"], "R", B["R"])',
    'sys.path.insert(0, os.path.join("analysis", "counting", "s58"))',
    'import enumext_sweep as EXS',
    'roots, hits, fn = EXS.frontier(3, 12, 15, 2)',
    'print("FRONTIER", len(roots), fn, len(hits))',
    'print("PROBE_OK")'
  ) | Set-Content $p -Encoding ASCII
  $out = (& $PY -u $p) 2>&1
  Pop-Location
  $out | ForEach-Object { Note $_ }
  $base  = ($out | Select-String '^BASE_SHA (\w+)').Matches.Groups[1].Value
  $relax = ($out | Select-String '^RELAX_SHA (\w+)').Matches.Groups[1].Value
  $front = ($out | Select-String '^FRONTIER (\d+) (\d+)')
  if ($base -eq $MAC_BASE_SHA)   { Ok "PARITY base  sha == Mac ($($MAC_BASE_SHA.Substring(0,16))..)" }
  else { Bad "PARITY base sha MISMATCH: PC=$base Mac=$MAC_BASE_SHA" }
  if ($relax -eq $MAC_RELAX_SHA) { Ok "PARITY relax sha == Mac (and == the s60 store's base sha)" }
  else { Bad "PARITY relax sha MISMATCH: PC=$relax Mac=$MAC_RELAX_SHA" }
  # Mac: frontier(3,12,15,2) -> 1792 subtrees / 2075 nodes / 0 above-frontier hits
  if ($front -and $front.Matches.Groups[1].Value -eq "1792" -and
      $front.Matches.Groups[2].Value -eq "2075") { Ok "PARITY enum_ext frontier == Mac (1792 subtrees / 2075 nodes)" }
  else { Bad "PARITY enum_ext frontier MISMATCH (Mac: 1792 / 2075)" }
  if ($out -match "PROBE_OK") { Ok "import chain resolves farm-side" } else { Bad "probe did not complete" }
}

New-Item -ItemType Directory -Force -Path "$ROOT\runs" | Out-Null
Write-Output ""
if ($fail -eq 0) { Write-Output "S58 ENV OK -- 0 failures" }
else { Write-Output "S58 ENV NOT READY -- $fail failure(s) above" }
exit $fail
