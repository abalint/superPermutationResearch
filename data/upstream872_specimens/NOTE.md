# Per-allocation specimens (s27)

One community-corpus class representative per specimen-backed L0 allocation
(8 of 8), forward-renumbered to identity start — the first file per allocation
in `analysis/counting/upstream872_structure.tsv` sorted by filename. The full
22,062-class archive lives in `data/upstream872/` (gitignored, local only;
regenerate with `analysis/counting/upstream872_dump.py`).

| file | S | d3 | d4 | d5 | ip | classes in allocation |
|---|---|---|---|---|---|---|
| 872.up-00005a46cfe3.txt | 145 | 3 | 0 | 0 | 0 | 21,144 (records class) |
| 872.up-006185ae478a.txt | 143 | 5 | 0 | 0 | 0 | 470 |
| 872.up-022441b7b1ff.txt | 140 | 6 | 1 | 0 | 0 | 388 (w4 door) |
| 872.up-13f91236b67c.txt | 142 | 6 | 0 | 0 | 0 | 19 |
| 872.up-009da25acce5.txt | 135 | 9 | 2 | 0 | 0 | 18 (two w4 doors) |
| 872.up-249988a17b8a.txt | 140 | 8 | 0 | 0 | 0 | 10 |
| 872.up-00b21d05e0f4.txt | 138 | 8 | 1 | 0 | 0 | 9 |
| 872.up-6dbae421a839.txt | 141 | 7 | 0 | 0 | 0 | 4 (1\|5 and 5\|1 splits) |

Used by `tests/alloc_grammar.rs`: each specimen must replay 719/719 moves
through the sojourn grammar under its allocation's caps + census profile
(`analysis/trackb/profiles/a<S>_<d3>_<d4>_<d5>_<ip>.txt`), and the 1|5-bearing
specimen must fail under the records profile (the check has teeth). The
corpus-wide result (22,062/22,062 replay fully, ~29 s) is JOURNAL s27.
