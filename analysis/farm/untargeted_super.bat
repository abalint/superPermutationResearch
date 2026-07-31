@echo off
REM detach.exe cannot launch powershell.exe directly (no console -> silent
REM exit); cmd /c <bat> can.  %1 = run tag; every other parameter lives in
REM F:\superpermFarm\untargeted\runs\%1\PARAMS.txt so nothing with a space
REM ever crosses a command line (detach.exe joins argv with single spaces).
powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\untargeted_super.ps1 -Tag %1
