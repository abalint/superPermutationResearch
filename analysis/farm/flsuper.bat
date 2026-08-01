@echo off
REM %1 = run tag.  See flworker.bat for why this .bat shim exists.
powershell -NoProfile -ExecutionPolicy Bypass -File D:\superpermFarm\fl1577\flsuper.ps1 -Tag %1
