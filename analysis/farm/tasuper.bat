@echo off
REM detach.exe cannot launch powershell.exe directly (no console -> silent exit);
REM cmd /c <bat> can. Args: %1=Tag %2=Workers %3=Total
powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\tailatsp\tasuper.ps1 -Tag %1 -Workers %2 -Total %3
