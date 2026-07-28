@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d F:\superpermFarm
cl /nologo /O2 /Fedetach.exe detach.c
