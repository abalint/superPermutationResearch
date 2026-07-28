# bench56.ps1 -- Egan's own published benchmarks on the Windows build
$b = "F:\superpermFarm\bench"
Remove-Item -Recurse -Force $b -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $b | Out-Null
foreach ($t in @(@("5",""), @("6",""), @("6","ffc"))) {
  $n = $t[0]; $opt = $t[1]
  $d = Join-Path $b ("n" + $n + $opt)
  New-Item -ItemType Directory -Force -Path $d | Out-Null
  Push-Location $d
  $sw = [Diagnostics.Stopwatch]::StartNew()
  if ($opt -eq "") { & "F:\superpermFarm\PermutationChains.exe" $n > out.log 2>&1 }
  else             { & "F:\superpermFarm\PermutationChains.exe" $n $opt > out.log 2>&1 }
  $sw.Stop()
  $sols = (Select-String -Path out.log -Pattern "Found SOLUTION" -AllMatches).Count
  Write-Output ("n=" + $n + " opt='" + $opt + "' exit=" + $LASTEXITCODE + " solutions=" + $sols + " secs=" + [math]::Round($sw.Elapsed.TotalSeconds,1))
  Pop-Location
}
