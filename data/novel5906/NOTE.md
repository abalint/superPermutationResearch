# novel5906 — the first record-length classes this project has produced

s41 (2026-07-30). Eight distinct 5906 classes, each INEQUIVALENT
(relabel+reversal) to all 84 published/known classes in
`analysis/counting/upstream5906_canon_index.tsv` — the first genuinely
novel record-length superpermutations the project has generated (the
s26 hybrids were byte-identical to known community strings).

Produced by `analysis/counting/i4a_apply.py apply-sym` (I4-A mode 0,
SURGERY-DESIGN §11.6): the Kristan-seam rewrite rule R-K7 — extracted
from the (844,17)↔(843,18) cover-sharing pair, a 1|6-rotor ⟷ 2-door
local surgery — applied under symmetry conjugation (all 5040
relabelings × both walk orientations) across the 87-walk known n=7
corpus. Forward and reversed orientations of each source converge to
the same class (16 products → 8 classes).

Verification: every string passes
`cargo run --release -- validate -n 7 --file <f> --complete` and
`python3 analysis/counting/m3_check.py -n 7 <f>` reports
INEQUIVALENT-to-all-known (the M3 banner).

Structure: all are pure-w3, L = 142 distinct 2-loops (the s34
invariant EXTENDS to them), tight in the s39 loop-cover sense — and
they occupy **two allocations never before seen at n=7**:

| file | source class (upstream5906) | allocation |
|---|---|---|
| 5906.i4a-66637a3b8941.txt | 1206598d1ff0 | (839, 22) |
| 5906.i4a-c1080e26f60c.txt | 56126e7237c3 | (839, 22) |
| 5906.i4a-6a77e138ea8e.txt | 590fe2cb2c21 | (839, 22) |
| 5906.i4a-7f46c8149026.txt | 6a142cb8e27d | (839, 22) |
| 5906.i4a-29c55ed5fbf6.txt | bd458e7fc19e | (839, 22) |
| 5906.i4a-e0f3de4ca026.txt | df8c9033249e | (839, 22) |
| 5906.i4a-50d865ca7907.txt | 890b6674bd25 | (835, 26) |
| 5906.i4a-b99b1d60f13e.txt | d0b9281ca469 | (835, 26) |

Sources sit at (840,21) and (836,25): the conjugated seam move fires
OFF the Kristan shell, wherever its local context recurs. The n=7
allocation map grows 6 → 8. `m3_check -n 7` now loads the committed
supplementary index `analysis/counting/novel5906_canon_index.tsv` in
addition to the published index, so novelty claims are automatically
vs published + these discoveries (labeled "[project discovery]").
