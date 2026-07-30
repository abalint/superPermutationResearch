# The natural 2-compound pairs (s36 M-2b; SURGERY-DESIGN §10.6)

The only minimal 2-compounds nature exhibits — the same object mirrored,
bridging the two largest S1-disconnected shells (145,3) <-> (143,5) via
two merges + two door promotions on cycles 126354 (2|4 <-> 6) and
123654 (3|3 <-> 6):

- `872.up-55088ebb4107.txt` (145,3)  x  `872.up-d141177d85e1.txt` (143,5)
- `872.up-00c66faaa43f.txt` (145,3)  x  `872.up-138d980ad903.txt` (143,5)

Copied from the (gitignored) full archive `data/upstream872/` so the
`--recomp2` natural-compound oracle (tests in src/tailatsp.rs) is
runnable from a clean clone. A-side part depths (55088ebb4107): 126354
at 181-184 (prefix at anchors >= 450, entry 354126) + 569-570; 123654
at 571-573 + 718-720 — the compound is reachable at anchor 520 WITH
single prefix-part extraction (all non-extracted parts sit >= 569).
