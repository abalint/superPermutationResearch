@echo off
REM ===================================================================
REM install_tasks_admin.bat  --  RUN FROM AN ELEVATED PROMPT ("Run as administrator")
REM
REM Registers five SYSTEM scheduled tasks spf_c0..spf_c4, one per superperm
REM search chain, /sc ONSTART /f so they run with nobody logged on AND restart
REM automatically after a reboot (these are multi-day runs). Then starts them.
REM Self-contained: it writes the per-chain run.bat files itself.
REM
REM Uninstall with: F:\superpermFarm\uninstall_tasks_admin.bat  (also elevated)
REM ===================================================================
setlocal
set FARM=F:\superpermFarm
set EXE=%FARM%\PermutationChains.exe

if not exist "%EXE%" (
  echo ERROR: %EXE% not found. Aborting.
  goto :end
)

net session >nul 2>&1
if errorlevel 1 (
  echo ERROR: not elevated. Right-click cmd.exe and choose "Run as administrator", then re-run this file.
  goto :end
)

REM --- If the standard-user farm is currently running, stop it so the SYSTEM
REM --- tasks do not duplicate work in the same directories.
taskkill /f /im PermutationChains.exe >nul 2>&1

call :chain 0 666646664666466466646664666
call :chain 1 666646664664666466466646666
call :chain 2 666646646664666466466646666
call :chain 3 666646664664666466646646666
call :chain 4 666466646664664666466646666

echo.
echo Done. Check status with:  schtasks /query /tn spf_c0 /v /fo list
echo Logs: %FARM%\runs\c0..c4\out.log
goto :end

REM ------------------------------------------------------------------
:chain
set I=%1
set PAT=%2
set DIR=%FARM%\runs\c%I%
if not exist "%DIR%" mkdir "%DIR%"

REM A stale/truncated IntersectionFlags7.dat from a killed run makes the exe
REM abort with "Error reading from file IntersectionFlags7.dat"; it is cheap
REM to regenerate, so remove it on install.
if exist "%DIR%\IntersectionFlags7.dat" del /q "%DIR%\IntersectionFlags7.dat"

REM (re)create the per-chain runner. start /belownormal /b /wait keeps the
REM machine responsive and keeps the task's process tree alive while it runs.
REM (F: is an external SSD; at ONSTART it may not be mounted yet, so wait for it.)
> "%DIR%\run.bat" echo @echo off
>>"%DIR%\run.bat" echo set /a tries=0
>>"%DIR%\run.bat" echo :waitdrive
>>"%DIR%\run.bat" echo if exist "%EXE%" goto ready
>>"%DIR%\run.bat" echo set /a tries+=1
>>"%DIR%\run.bat" echo if %%tries%% GEQ 60 exit /b 1
>>"%DIR%\run.bat" echo ping -n 6 127.0.0.1 ^>nul
>>"%DIR%\run.bat" echo goto waitdrive
>>"%DIR%\run.bat" echo :ready
>>"%DIR%\run.bat" echo cd /d "%DIR%"
>>"%DIR%\run.bat" echo start "spf_c%I%" /belownormal /b /wait "%EXE%" 7 nsk%PAT% trackPartial ^>^> out.log 2^>^> err.log

schtasks /delete /tn spf_c%I% /f >nul 2>&1
schtasks /create /tn spf_c%I% /tr "\"%DIR%\run.bat\"" /sc ONSTART /ru SYSTEM /rl HIGHEST /f >nul 2>&1
if errorlevel 1 (
  echo [FAIL] spf_c%I% : schtasks /create failed
  goto :eof
)
schtasks /run /tn spf_c%I% >nul 2>&1
if errorlevel 1 (
  echo [WARN] spf_c%I% : created but /run failed ^(it will still start at next boot^)
  goto :eof
)
echo [ OK ] spf_c%I% created and started  ^(nsk%PAT%^)
goto :eof

:end
endlocal
echo.
pause
