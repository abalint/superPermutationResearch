# flbuild.ps1 -- build LKH-3.0.13 into D:\superpermFarm\fl1577\bin\LKH.exe with the
# winlibs mingw-w64 toolchain fetched by flsetup.ps1, then smoke-test it.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\superpermFarm\fl1577\flbuild.ps1
#
# Two portability patches are needed and only two:
#   (a) SRC\GetTime.c hard-#defines HAVE_GETRUSAGE and then includes <sys/resource.h>,
#       which mingw-w64 does not ship.  The file already carries a clock()-based
#       fallback for exactly this case, so we flip the #define to #undef.
#       CONSEQUENCE, worth knowing: on Windows LKH's clock() is WALL time, whereas
#       the getrusage path on macOS/Linux measures user+sys CPU.  For single-threaded
#       LKH the two are within noise, but TIME_LIMIT / TOTAL_TIME_LIMIT are therefore
#       wall-clock limits on this binary.
#   (b) CFLAGS must keep -D$(TREE_TYPE) (= -DTWO_LEVEL_TREE).  Overriding CFLAGS on
#       the make command line silently drops it and the tree-representation code
#       compiles to nothing coherent.  -fcommon is already in upstream CFLAGS.
$ErrorActionPreference = "Continue"

$ROOT   = "D:\superpermFarm\fl1577"
$TC     = "$ROOT\toolchain\mingw64\bin"
$LKHDIR = "$ROOT\src\LKH-3.0.13"
$BIN    = "$ROOT\bin"
$LOGS   = "$ROOT\buildlogs"
New-Item -ItemType Directory -Force -Path $BIN,$LOGS | Out-Null
$env:PATH = "$TC;$env:PATH"

function Say($m) { Write-Output ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) }

# --- patch (a) --------------------------------------------------------------
$gt = "$LKHDIR\SRC\GetTime.c"
$txt = Get-Content $gt -Raw
if ($txt -match '(?m)^#define HAVE_GETRUSAGE') {
  ($txt -replace '(?m)^#define HAVE_GETRUSAGE', '#undef HAVE_GETRUSAGE  /* mingw-w64: no sys/resource.h */') |
    Set-Content $gt -NoNewline
  Say "patched GetTime.c: HAVE_GETRUSAGE -> undef (clock() fallback)"
} else {
  Say "GetTime.c already patched"
}

# --- build ------------------------------------------------------------------
Set-Location "$LKHDIR\SRC"
Remove-Item "$LKHDIR\SRC\OBJ\*.o" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path "$LKHDIR\SRC\OBJ" | Out-Null
$blog = "$LOGS\build.log"
$CF = "-O3 -Wall -IINCLUDE -DTWO_LEVEL_TREE -g -fcommon"
Say "make CFLAGS=$CF"
& "$TC\mingw32-make.exe" -j 8 CC=gcc "CFLAGS=$CF" *> $blog
$rc = $LASTEXITCODE
Say "make rc=$rc"

$exe = @("$LKHDIR\LKH.exe", "$LKHDIR\LKH", "$LKHDIR\SRC\LKH.exe") |
       Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) {
  Say "NO BINARY -- first 40 error lines:"
  Get-Content $blog | Select-String -Pattern "error|Error|fatal" | Select-Object -First 40 |
    ForEach-Object { Say ("  " + $_.Line.Trim()) }
  throw "build failed rc=$rc"
}
Copy-Item $exe "$BIN\LKH.exe" -Force
$warn = (Get-Content $blog | Select-String -Pattern "warning:").Count
Say ("built {0} ({1} bytes, {2} warnings)" -f "$BIN\LKH.exe", (Get-Item "$BIN\LKH.exe").Length, $warn)

# --- smoke ------------------------------------------------------------------
$sm = "$ROOT\smoke"
New-Item -ItemType Directory -Force -Path $sm | Out-Null
# 8 cities on a 4x2 unit grid; the optimal tour is the perimeter, cost exactly 10.
@("NAME : smoke8","TYPE : TSP","DIMENSION : 8","EDGE_WEIGHT_TYPE : EUC_2D",
  "NODE_COORD_SECTION","1 0 0","2 1 0","3 2 0","4 3 0","5 3 1","6 2 1","7 1 1","8 0 1","EOF") |
  Set-Content "$sm\smoke8.tsp"
@("PROBLEM_FILE = $sm\smoke8.tsp","RUNS = 3","SEED = 1","TRACE_LEVEL = 1",
  "TOUR_FILE = $sm\smoke8.tour") | Set-Content "$sm\smoke8.par"
& "$BIN\LKH.exe" "$sm\smoke8.par" *> "$sm\smoke8.log"
Say "smoke8 rc=$LASTEXITCODE"
Get-Content "$sm\smoke8.log" | Select-String -Pattern "Cost\.min|Cost\.max|Successes|Time\.total" |
  ForEach-Object { Say ("  " + $_.Line.Trim()) }
Say "  (expected Cost.min = Cost.max = 10)"

Say "BUILD COMPLETE"
