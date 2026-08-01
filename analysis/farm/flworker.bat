@echo off
REM detach.exe cannot launch powershell.exe directly (no console -> silent exit);
REM cmd /c <bat> can.  %1 = run tag, %2 = two-digit worker id.  Nothing else
REM crosses the command line (detach.exe joins argv with single spaces).
powershell -NoProfile -ExecutionPolicy Bypass -File D:\superpermFarm\fl1577\flworker.ps1 -Tag %1 -Worker %2
