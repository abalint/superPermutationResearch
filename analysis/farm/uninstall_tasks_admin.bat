@echo off
REM uninstall_tasks_admin.bat -- RUN ELEVATED. Deletes the five spf_c* tasks
REM and stops any running PermutationChains processes.
setlocal
net session >nul 2>&1
if errorlevel 1 (
  echo ERROR: not elevated. Run this from an administrator command prompt.
  goto :end
)
for %%I in (0 1 2 3 4) do (
  schtasks /end /tn spf_c%%I >nul 2>&1
  schtasks /delete /tn spf_c%%I /f >nul 2>&1
  if errorlevel 1 (echo [ -- ] spf_c%%I not present) else (echo [ OK ] spf_c%%I deleted)
)
taskkill /f /im PermutationChains.exe >nul 2>&1
echo all spf_c* tasks removed and PermutationChains stopped
:end
endlocal
echo.
pause
