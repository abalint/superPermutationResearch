@echo off
REM Build dlx7g.exe for the s58 sweeps from the REPO source, into the s58 repo
REM mirror -- deliberately NOT into F:\superpermFarm\trackc2, whose dlx7g.c is a
REM different version (sha 99E791E3.. vs the repo's B25EBE9B..) and whose exe
REM other tooling still points at.  The cut store's soundness is the claim
REM "this engine exhausted the tree", so it must be the engine the Mac-side
REM oracle validated.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d F:\superpermFarm\untargeted\repo\analysis\trackc
cl /nologo /O2 /Fedlx7g.exe /Fodlx7g_s58.obj dlx7g.c
