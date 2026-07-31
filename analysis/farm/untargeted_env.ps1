# untargeted_env.ps1 -- farm-side environment check + idempotent setup for the
# s49 fused-pair UNTARGETED sweep.  Read-mostly: the only things it CREATES are
# the venv, the renamed interpreter, and the run root.  Safe to re-run.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\untargeted_env.ps1
#   ... -Smoke      also runs the instrument-level proof (index-cache load +
#                   a real fuse.py subcommand) -- takes a couple of minutes
#   ... -Reindex    rebuilds the caches with `fuse.py index` and diffs the
#                   hashes against the shipped ones (Mac/PC parity proof)
param([switch]$Smoke, [switch]$Reindex)
$ErrorActionPreference = "Continue"

$ROOT = "F:\superpermFarm\untargeted"
$REPO = "$ROOT\repo"
$VENV = "$ROOT\pyenv"
$PY   = "$VENV\Scripts\upyw.exe"          # renamed venv python -- see below
$FUSE = "$REPO\analysis\counting\s49\fuse.py"
$CACHE= "$REPO\out\s49\item1"
$fail = 0
function Ok  ($m) { Write-Output "  [ok]   $m" }
function Bad ($m) { Write-Output "  [FAIL] $m"; $script:fail++ }
function Note($m) { Write-Output "  ...    $m" }

Write-Output "=== untargeted farm environment  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="

# --- 1. host resources -------------------------------------------------------
Write-Output "-- host --"
$cores = [int]$env:NUMBER_OF_PROCESSORS
Ok "logical processors: $cores  (24 shards leaves $($cores-24) for the transcription service)"
if ($cores -lt 26) { Bad "fewer than 26 cores -- do not run 24 shards here" }

foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
  if ($d.Name -eq "F:\") {
    $gb = [math]::Round($d.AvailableFreeSpace/1GB,1)
    if ($gb -lt 20) { Bad "F: only $gb GB free" } else { Ok "F: free $gb GB" }
  }
}
if (Test-Path "$ROOT\meminfo.ps1") {
  . "$ROOT\meminfo.ps1"                    # WMI/systeminfo are Access-denied here
  $m = Get-FarmMem
  Ok "RAM total $($m.TotalMB) MB, available $($m.AvailMB) MB ($($m.PctFree)% free)"
  # measured footprint is ~250 MB RSS per shard -> 24 x 250 = ~6000 MB
  if ($m.AvailMB -lt 9000) { Bad "under 9 GB available -- 24 x 250 MB plus headroom does not fit" }
  else { Ok "headroom for 24 x 250 MB = 6000 MB: $([math]::Round($m.AvailMB/6000.0,1))x" }
} else { Note "meminfo.ps1 not shipped -- RAM unchecked (WMI is denied for this account)" }

# --- 2. the box must be idle -------------------------------------------------
Write-Output "-- idle check --"
$sp = @(Get-Process -Name superperm,superperm64,dlx7g,dlx7g_v21 -ErrorAction SilentlyContinue)
if ($sp.Count -gt 0) { Bad "$($sp.Count) farm engine process(es) alive -- the box is NOT idle" }
else { Ok "no superperm/dlx7g engines running" }
$ours = @(Get-Process -Name upyw -ErrorAction SilentlyContinue)
if ($ours.Count -gt 0) { Bad "$($ours.Count) upyw.exe already alive (a sweep is running -- see untargeted_status.ps1)" }
else { Ok "no upyw.exe (our shards) running" }
# informational only: these are the USER'S processes.  NEVER kill them.
# (Named $userPy, not $py: PowerShell variables are CASE-INSENSITIVE, so $py
# and $PY are the same variable -- this collision silently destroyed the
# interpreter path on first run.)
$userPy = @(Get-Process -Name python,pythonw -ErrorAction SilentlyContinue)
Note "python.exe processes on the box: $($userPy.Count)  (transcription service -- NEVER kill)"
foreach ($up in $userPy) { Note "   pid $($up.Id)  $($up.Path)" }

# --- 3. interpreter ----------------------------------------------------------
Write-Output "-- python --"
$sys = ""
try { $sys = (& py -3 --version) 2>&1 } catch { $sys = "" }
if ("$sys" -match "Python 3") { Ok "system interpreter: $sys" }
else { Bad "no system python3 -- an embeddable CPython must be staged under $ROOT" }

if (-not (Test-Path "$VENV\Scripts\python.exe")) {
  Note "creating venv at $VENV (no admin needed; system site-packages untouched)"
  & py -3 -m venv $VENV | Out-Null
}
if (-not (Test-Path "$VENV\Scripts\python.exe")) { Bad "venv creation failed" }
else {
  # A renamed COPY of the venv interpreter.  CPython locates pyvenv.cfg by the
  # executable's DIRECTORY, not its name, so upyw.exe is a fully working venv
  # python -- and `Get-Process -Name upyw` can never match the user's
  # transcription python.  This is what makes untargeted_abort.ps1 safe.
  if (-not (Test-Path $PY)) {
    Copy-Item "$VENV\Scripts\python.exe" $PY -Force
    Note "created $PY (renamed venv interpreter -- process-identity guard)"
  }
  $v = (& $PY -c "import sys,numpy;print(sys.version.split()[0],numpy.__version__,sys.prefix)") 2>&1
  if ("$v" -match "^\d+\.\d+\.\d+ \d") {
    $p = "$v".Split(" ")
    Ok "upyw.exe: python $($p[0]), numpy $($p[1])"
    if ($p[2] -ne $VENV) { Bad "upyw.exe resolves prefix $($p[2]) -- expected $VENV" }
  } else {
    Bad "upyw.exe / numpy not usable: $v"
    Note "fix: $VENV\Scripts\python.exe -m pip install numpy   then re-run this script"
  }
}

# --- 4. shipped payload ------------------------------------------------------
Write-Output "-- payload --"
if (-not (Test-Path $FUSE)) { Bad "instrument missing: $FUSE" } else { Ok "instrument present: $FUSE" }
foreach ($c in @("relab.npy","inst_keys.npy","inst_rule.npy","inst_sigma.npy","inst_ruleids.txt","blindspot12.txt")) {
  if (Test-Path "$CACHE\$c") { Ok ("cache {0,-18} {1,10:N0} bytes" -f $c, (Get-Item "$CACHE\$c").Length) }
  else { Bad "cache missing: $CACHE\$c" }
}
$corp = 0
foreach ($d in @("upstream5906","novel5906","novel5906b","novel5906c","novel5906d","kristan5906_web","upstream5907")) {
  $n = @(Get-ChildItem "$REPO\data\$d" -Filter *.txt -EA SilentlyContinue).Count
  if ($n -eq 0) { Bad "corpus dir empty/missing: data\$d" } else { $corp += $n; Note "data\$d : $n classes" }
}
Ok "corpus files total: $corp"
foreach ($t in @("rules_n7_a256.tsv","rules_n7_a4840_gen2.tsv","rules_n7_a4840_band200.tsv",
                 "rules_n7_s48_covertwin.tsv","rules_n7_s51.tsv")) {
  if (Test-Path "$REPO\data\loopswap\$t") { Ok "rule table $t" } else { Bad "rule table missing: $t" }
}
foreach ($i in @("upstream872_canon_index.tsv","upstream5906_canon_index.tsv","novel5906_canon_index.tsv",
                 "novel5906b_canon_index.tsv","novel5906c_canon_index.tsv","novel5906d_canon_index.tsv",
                 "kristan5906_web_canon_index.tsv")) {
  if (Test-Path "$REPO\analysis\counting\$i") { Ok "canon index $i" } else { Bad "canon index missing: $i" }
}

# manifest cross-check (catches truncated transfers and AppleDouble twins)
if (Test-Path "$ROOT\MANIFEST.tsv") {
  $bad = 0; $n = 0
  Get-Content "$ROOT\MANIFEST.tsv" | Select-Object -Skip 1 | ForEach-Object {
    $f = $_ -split "`t"
    if ($f.Count -lt 3) { return }
    $n++
    $p = Join-Path $REPO ($f[2] -replace "/", "\")
    if (-not (Test-Path $p)) { $bad++; return }
    if ((Get-Item $p).Length -ne [int64]$f[1]) { $bad++ }
  }
  if ($bad -eq 0) { Ok "manifest: $n files present at the expected size" }
  else { Bad "manifest: $bad of $n files missing or wrong size" }
  $ad = @(Get-ChildItem $REPO -Recurse -Filter "._*" -EA SilentlyContinue).Count
  if ($ad -gt 0) { Bad "$ad AppleDouble '._*' files in the payload -- reship with COPYFILE_DISABLE=1" }
  else { Ok "no AppleDouble '._*' twins" }
} else { Note "no MANIFEST.tsv -- payload integrity unchecked" }

New-Item -ItemType Directory -Force -Path "$ROOT\runs" | Out-Null

# --- 5. instrument-level proof ----------------------------------------------
if ($Smoke -and (Test-Path $PY)) {
  Write-Output "-- smoke (cwd = $REPO) --"
  Push-Location $REPO
  # (a) imports + cache load: proves numpy, the sibling-module path insert, the
  #     rule tables, the corpora and the on-disk index all resolve farm-side.
  $probe = "$ROOT\_envprobe.py"
  @(
    'import os, sys, time',
    'sys.path.insert(0, os.path.join("analysis", "counting"))',
    'sys.path.insert(0, os.path.join("analysis", "counting", "s49"))',
    't0 = time.time()',
    'import fuse',
    'from i4a_apply import replay, structure',
    'from loop_ledger_probe import first_visit_path',
    'from m3_check import SUPPLEMENTARY, canon, load_index',
    'print("R      =", fuse.R)',
    'print("OUT    =", fuse.OUT)',
    'relab = fuse.relab_table(); print("relab  =", relab.shape, relab.dtype)',
    'rules = fuse.load_rules(); print("rules  =", len(rules))',
    'k, ri, si, ids = fuse.load_index()',
    'print("index  =", len(k), "instances,", len(ids), "rule ids, sorted:", bool((k[1:] >= k[:-1]).all()))',
    'names, W = fuse.load_corpus()',
    'print("corpus =", len(names), "classes,", len(W), "class-orientations")',
    'blind = [l.strip() for l in open(os.path.join(fuse.OUT, "blindspot12.txt")) if l.strip()]',
    'print("blind  =", len(blind))',
    'B = blind[0]',
    'sst, sf, sd = W[(B, "F")]',
    'print("blind0 =", B, "start", sst, "|flat|", int(sf.sum()), "doors", int((sd >= 0).sum()))',
    'src = None',
    'for d in fuse.DIRS:',
    '    p = os.path.join(fuse.R, d, B)',
    '    if os.path.exists(p): src = open(p).read().strip(); break',
    'E, D, st = structure(first_visit_path(src, 7))',
    't1 = time.time()',
    'w, why = replay(E, D, st, 7)',
    'dt = time.time() - t1',
    'print("replay =", len(w), "chars in", round(dt*1000), "ms;", why, "; byte-identical to source:", w == src)',
    'assert w == src, "replay did not reproduce the source walk"',
    'import hashlib',
    'idx = load_index(os.path.join("analysis", "counting", "upstream5906_canon_index.tsv"))',
    'for s in SUPPLEMENTARY[7]:',
    '    idx.update(load_index(os.path.join("analysis", "counting", s)))',
    'print("canon  =", len(idx), "known n=7 classes in the gate (s51 re-scope wants 220)")',
    'sha = hashlib.sha256(canon(src).encode()).hexdigest()',
    'print("gate self-test (a known class must NOT look novel):", sha in idx)',
    'assert sha in idx, "canon gate failed to recognise a corpus class"',
    'print("TOTAL  =", round(time.time() - t0, 1), "s")',
    'print("SMOKE_OK")'
  ) | Set-Content $probe -Encoding ASCII
  & $PY -u $probe
  if ($LASTEXITCODE -ne 0) { Bad "smoke probe exit $LASTEXITCODE" } else { Ok "smoke probe exit 0" }

  # (b) a REAL fuse.py subcommand end to end.  depth1 is the cheap committed
  #     mode; S49_SOURCES trims it to one blind class so this is a minute, not
  #     an hour.  Proves argv dispatch, the index lookup path and TSV writing.
  Get-Content "$CACHE\blindspot12.txt" -TotalCount 1 | Set-Content "$CACHE\_smoke_src.txt" -Encoding ASCII
  $env:S49_SOURCES = "$CACHE\_smoke_src.txt"
  & $PY -u $FUSE depth1
  if ($LASTEXITCODE -ne 0) { Bad "fuse.py depth1 exit $LASTEXITCODE" } else { Ok "fuse.py depth1 exit 0 (1 blind class)" }
  Remove-Item Env:\S49_SOURCES -EA SilentlyContinue
  Pop-Location
}

# --- 6. optional: rebuild the caches and prove Mac/PC parity ----------------
if ($Reindex -and (Test-Path $PY)) {
  Write-Output "-- reindex parity (cwd = $REPO) --"
  # Hash the .npy caches byte-for-byte, but normalise newlines on the text one:
  # build_index() writes inst_ruleids.txt in TEXT mode, so the PC rebuild is
  # CRLF and the Mac's is LF -- 864 extra bytes, identical content.  It is read
  # back with .read().split(), so this difference is functionally invisible.
  function CacheHash([string]$p) {
    if ($p -like "*.txt") {
      $t = [IO.File]::ReadAllText($p).Replace("`r`n", "`n")
      $h = [Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::ASCII.GetBytes($t))
      return ([BitConverter]::ToString($h) -replace '-','')
    }
    return (Get-FileHash $p -Algorithm SHA256).Hash
  }
  $before = @{}
  foreach ($c in @("inst_keys.npy","inst_rule.npy","inst_sigma.npy","inst_ruleids.txt")) {
    if (Test-Path "$CACHE\$c") { $before[$c] = CacheHash "$CACHE\$c" }
  }
  Push-Location $REPO
  & $PY -u $FUSE index
  $rc = $LASTEXITCODE
  Pop-Location
  if ($rc -ne 0) { Bad "fuse.py index exit $rc" } else { Ok "fuse.py index exit 0" }
  foreach ($c in @($before.Keys)) {
    $now = CacheHash "$CACHE\$c"
    if ($now -eq $before[$c]) { Ok "parity $c : PC rebuild == Mac-shipped cache (newline-normalised for .txt)" }
    else { Bad "parity $c : PC rebuild DIFFERS from the Mac-shipped cache" }
  }
}

Write-Output ""
if ($fail -eq 0) { Write-Output "ENV OK -- 0 failures" }
else { Write-Output "ENV NOT READY -- $fail failure(s) above" }
exit $fail
