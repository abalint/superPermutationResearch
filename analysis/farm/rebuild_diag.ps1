# rebuild_diag.ps1 -- does a non-optimised / GS-off rebuild pass Egan's n=5 smoke test?
$log = "F:\superpermFarm\rebuild_diag.log"
"=== rebuild diag $(Get-Date) ===" | Out-File $log
cmd /c "call `"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat`" >nul 2>&1 && cd /d F:\superpermFarm && cl /nologo /Od /FePC_Od.exe superperm\PermutationChains\PermutationChains.c >> $log 2>&1"
cmd /c "call `"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat`" >nul 2>&1 && cd /d F:\superpermFarm && cl /nologo /O2 /GS- /FePC_GSoff.exe superperm\PermutationChains\PermutationChains.c >> $log 2>&1"
foreach ($exe in @("PC_Od.exe","PC_GSoff.exe")) {
  $d = "F:\superpermFarm\bench\$exe"
  Remove-Item -Recurse -Force $d -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  Push-Location $d
  & "F:\superpermFarm\$exe" 5 > out.log 2>&1
  $code = $LASTEXITCODE
  $files = (Get-ChildItem $d -Filter "5_*.txt" | Measure-Object).Count
  $sols  = (Select-String -Path out.log -Pattern "Found SOLUTION" -AllMatches -ErrorAction SilentlyContinue).Count
  Write-Output "$exe n=5 exit=$code solutionFiles=$files solutions=$sols"
  Pop-Location
}
