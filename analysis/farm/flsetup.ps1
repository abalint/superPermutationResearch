# flsetup.ps1 -- one-shot toolchain + LKH build for the fl1577 recipe study on the farm PC.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\superpermFarm\fl1577\flsetup.ps1
#
# Stages (each idempotent; re-running skips what is already present):
#   1 fetch  winlibs mingw-w64 gcc zip  -> toolchain\mingw64\bin\gcc.exe
#   2 fetch  LKH-3.0.13.tgz             -> src\LKH-3.0.13\
#   3 build  LKH.exe                    -> bin\LKH.exe
#   4 smoke  LKH.exe on a tiny generated TSP instance
#
# Notes / traps (Windows C toolchain, 2026-07-31):
#   * $ErrorActionPreference stays Continue: gcc/make/tar write to stderr at
#     exit 0 and 'Stop' turns that into a thrown NativeCommandError.
#   * No path here contains a space, so nothing is quoted -- `cmd /c "exe" args
#     > "log"` silently drops the outer quotes and the redirect never fires.
#   * D: is NTFS. F: is exFAT and misbehaves for toolchains -- do not use it.
$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest progress bar is ~10x slower

$ROOT = "D:\superpermFarm\fl1577"
$TC   = "$ROOT\toolchain"
$SRC  = "$ROOT\src"
$BIN  = "$ROOT\bin"
$LOGS = "$ROOT\buildlogs"
New-Item -ItemType Directory -Force -Path $ROOT,$TC,$SRC,$BIN,$LOGS | Out-Null

function Say($m) { Write-Output ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) }

# --- stage 1: mingw-w64 -----------------------------------------------------
$GCC = "$TC\mingw64\bin\gcc.exe"
if (Test-Path $GCC) {
  Say "stage1 skip: gcc already at $GCC"
} else {
  Say "stage1: querying winlibs latest release"
  $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/brechtsanders/winlibs_mingw/releases/latest" `
                           -UseBasicParsing -TimeoutSec 120 -Headers @{ "User-Agent" = "farm" }
  $asset = $rel.assets | Where-Object { $_.name -like "*x86_64*" -and $_.name -like "*.zip" } | Select-Object -First 1
  if (-not $asset) { throw "no x86_64 zip asset in winlibs release $($rel.tag_name)" }
  $zip = "$TC\$($asset.name)"
  Say ("stage1: downloading {0} ({1} MB)" -f $asset.name, [math]::Round($asset.size/1MB,1))
  Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing -TimeoutSec 1800
  Say "stage1: extracting"
  # tar.exe (bsdtar, in-box since Win10 1803) unzips far faster than Expand-Archive
  & "$env:SystemRoot\System32\tar.exe" -xf $zip -C $TC
  if ($LASTEXITCODE -ne 0) { throw "tar extract failed rc=$LASTEXITCODE" }
  Remove-Item $zip -Force
  if (-not (Test-Path $GCC)) { throw "gcc not found after extract: $GCC" }
  Say "stage1: done -- $((& $GCC --version 2>&1)[0])"
}
$env:PATH = "$TC\mingw64\bin;$env:PATH"

# --- stage 2: LKH-3.0.13 source --------------------------------------------
$LKHDIR = "$SRC\LKH-3.0.13"
if (Test-Path "$LKHDIR\SRC\LKHmain.c") {
  Say "stage2 skip: source already at $LKHDIR"
} else {
  $tgz = "$SRC\LKH-3.0.13.tgz"
  $urls = @(
    "http://webhotel4.ruc.dk/~keld/research/LKH-3/LKH-3.0.13.tgz",
    "http://akira.ruc.dk/~keld/research/LKH-3/LKH-3.0.13.tgz"
  )
  $ok = $false
  foreach ($u in $urls) {
    Say "stage2: fetching $u"
    try {
      Invoke-WebRequest -Uri $u -OutFile $tgz -UseBasicParsing -TimeoutSec 600
      if ((Get-Item $tgz).Length -gt 100000) { $ok = $true; break }
    } catch { Say "stage2: $u failed -- $($_.Exception.Message)" }
  }
  if (-not $ok) { throw "could not fetch LKH-3.0.13.tgz from any mirror" }
  $h = (Get-FileHash $tgz -Algorithm SHA256).Hash.ToLower()
  Say ("stage2: got {0} bytes sha256={1}" -f (Get-Item $tgz).Length, $h)
  & "$env:SystemRoot\System32\tar.exe" -xzf $tgz -C $SRC
  if ($LASTEXITCODE -ne 0) { throw "tar -xzf failed rc=$LASTEXITCODE" }
  if (-not (Test-Path "$LKHDIR\SRC\LKHmain.c")) { throw "unexpected archive layout under $SRC" }
  Say "stage2: done"
}

# --- stage 3: build ---------------------------------------------------------
if (Test-Path "$BIN\LKH.exe") {
  Say "stage3 skip: $BIN\LKH.exe exists"
} else {
  Say "stage3: building (mingw32-make)"
  Set-Location "$LKHDIR\SRC"
  $blog = "$LOGS\build.log"
  # -fcommon: LKH declares several globals without extern in headers (pre-gcc10 style).
  # -std=gnu17 + -fpermissive: gcc>=14 promotes implicit decls / int-conversion to errors.
  # -D_CRT_SECURE_NO_WARNINGS + -DFIXED_SEED harmless; -O3 matches upstream Makefile.
  $mk = "$TC\mingw64\bin\mingw32-make.exe"
  & $mk -j 8 CC=gcc "IFLAGS=-I. -IINCLUDE" `
     "CFLAGS=-O3 -Wall -IINCLUDE -g -fcommon -std=gnu17 -fpermissive -Wno-implicit-function-declaration -Wno-int-conversion -Wno-incompatible-pointer-types -D_CRT_SECURE_NO_WARNINGS" `
     *> $blog
  $rc = $LASTEXITCODE
  Say "stage3: make rc=$rc (log $blog)"
  $exe = @("$LKHDIR\LKH.exe", "$LKHDIR\LKH", "$LKHDIR\SRC\LKH.exe", "$LKHDIR\SRC\LKH") |
         Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $exe) { throw "build produced no binary (rc=$rc) -- read $blog" }
  Copy-Item $exe "$BIN\LKH.exe" -Force
  Say "stage3: done -> $BIN\LKH.exe"
}

# --- stage 4: smoke ---------------------------------------------------------
Say "stage4: smoke test"
$sm = "$ROOT\smoke"
New-Item -ItemType Directory -Force -Path $sm | Out-Null
# 8-city instance on a 4x2 grid: optimal tour is the perimeter, length 10.
@(
  "NAME : smoke8", "TYPE : TSP", "DIMENSION : 8", "EDGE_WEIGHT_TYPE : EUC_2D",
  "NODE_COORD_SECTION",
  "1 0 0", "2 1 0", "3 2 0", "4 3 0", "5 3 1", "6 2 1", "7 1 1", "8 0 1",
  "EOF"
) | Set-Content "$sm\smoke8.tsp"
@(
  "PROBLEM_FILE = $sm\smoke8.tsp", "RUNS = 1", "TRACE_LEVEL = 1", "TOUR_FILE = $sm\smoke8.tour"
) | Set-Content "$sm\smoke8.par"
& "$BIN\LKH.exe" "$sm\smoke8.par" *> "$sm\smoke8.log"
Say "stage4: LKH rc=$LASTEXITCODE"
Get-Content "$sm\smoke8.log" | Select-String -Pattern "Cost\.min|Cost\.avg|Lower bound|Time\.total" | ForEach-Object { Say ("  " + $_.Line.Trim()) }
Say "SETUP COMPLETE"
