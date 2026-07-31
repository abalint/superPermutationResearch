# alarmtest.ps1 -- verify the s52b alarm regex: benign summaries must NOT
# match, real events MUST. Run on the PC so the semantics are PowerShell's.
$re = '(?i)Traceback|MemoryError|^\s*!!|\*\*\*|ESCAPES\s+[1-9]|NOVEL[^:\r\n]*:\s*[1-9]'

$benign = @(
  'novel-candidate classes: 0',
  'distinct (src_class,tgt_class) pairs: 0',
  'edges written: 0 -> edges.tsv',
  'ESCAPES 0',
  'product-NOVEL: 0',
  'roundtrip-ok: 44124'
)
$real = @(
  'novel-candidate classes: 3',
  '*** NOVEL-CANDIDATE len=872 demo-872-abc.txt <- 872.up-x[F] PRO4/-1/nodoor',
  '*** DEGENERATE-DROP NOVEL len=871 drop-871-def.txt',
  'ESCAPES 2',
  'Traceback (most recent call last):',
  'MemoryError',
  'product-NOVEL: 1'
)

$fail = 0
Write-Output "--- benign (expect False) ---"
foreach ($c in $benign) {
  $m = $c -match $re
  if ($m) { $fail++ ; Write-Output "FAIL(matched) : $c" } else { Write-Output "ok            : $c" }
}
Write-Output "--- real events (expect True) ---"
foreach ($c in $real) {
  $m = $c -match $re
  if (-not $m) { $fail++ ; Write-Output "FAIL(missed)  : $c" } else { Write-Output "ok            : $c" }
}
Write-Output ""
if ($fail -eq 0) { Write-Output "ALARM REGEX OK: 0 failures" } else { Write-Output "ALARM REGEX BROKEN: $fail failures" }
