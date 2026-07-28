@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d F:\superpermFarm\trackc2
cl /nologo /O2 /Fedlx7g.exe dlx7g.c
