# satstop.ps1 -- stop the SAT/DLX farm (workers + engines). Leaves results.csv
# and the claims dir intact, so a later satscale.ps1 resumes where it left off.
$ROOT = "F:\superpermFarm"
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output "stopping python pid $($_.Id)"; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*satworker*" } | ForEach-Object {
    Write-Output "stopping worker pid $($_.ProcessId)"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Output "sat farm stopped"
