@echo off
REM build64.bat -- build PermutationChains64.exe: same source as
REM PermutationChains.exe but with a 64 MB stack reserve (/F67108864 = 0x4000000).
REM
REM History: a big stack was first thought to be the fix for workers dying
REM silently at depth 122-127 of 141 two-cycles; that diagnosis was RETRACTED
REM (searchPC's frame is ~128 bytes, so 141 levels is <20 KB -- 1 MB was never
REM the constraint). The build is kept anyway as free safety margin.
REM
REM It deliberately writes a NEW file name rather than overwriting
REM PermutationChains.exe: the five priority K=27 chains hold that binary open,
REM so overwriting it would require killing them. New workers use this one.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d F:\superpermFarm
cl /nologo /O2 /F67108864 /FePermutationChains64.exe /FoPermutationChains64.obj superperm\PermutationChains\PermutationChains.c
if errorlevel 1 (echo BUILD FAILED & exit /b 1)
echo ==== dumpbin stack (want 4000000 = 64MB reserve) ====
dumpbin /headers PermutationChains64.exe | findstr /i "stack"
echo ==== old binary for comparison ====
dumpbin /headers PermutationChains.exe | findstr /i "stack"
