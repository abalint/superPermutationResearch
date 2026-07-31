# novel5906c — the s47 R-BND discoveries (4 novel 5906 classes)

**STATUS: PUBLISHED** — merged into superpermutators/superperm master
2026-07-31 (17:52Z) as
[PR #52](https://github.com/superpermutators/superperm/pull/52)
(branch `four-new-5906s-843-18` on the abalint fork, files
`superpermutations/7/7_5906_derived_<hash12>.txt`; upstream master
`77dc0d1` carries all four, verified by tree diff s56). Published
shell 194 → 198 (→ 218 with PR #53, merged the same day).

Four length-5906 n=7 superpermutation classes, all at allocation
**(843,18)** — the allocation where Kristan's class previously sat
alone in the published 194-class shell. Produced in s47 by **R-BND**,
the boundary/door unit trade (the R-unit lift to n=7), derived from the
three (842,19)↔(844,17) conjugated cover twins discovered in s46.
Spec: `docs/RBND-RULE.md`; instrument: `analysis/counting/rbnd.py`;
edges/provenance: `data/loopswap/rbnd_edges_n7.tsv`,
`data/loopswap/rbnd_provenance_n7.tsv`.

Gates (all re-run by the orchestrating session, not just the agent):
- upstream re-pulled first (`superperm` at `235a074`, unchanged);
- `m3_check -n 7` exit 2 vs all 194 published classes (before these
  were indexed) — pairwise inequivalent by canonical sha256;
- Rust `validate -n 7 --complete` = true, length 5906, on all four;
- all tight (deficit 0), pure-w3, L = 142.

File naming: `5906.rbnd-<first 12 hex of relabel+reversal canonical
sha256>.txt`, matching the `5906.i4a-*` / `5906.lswap-*` conventions.
Canonical index: `analysis/counting/novel5906c_canon_index.tsv`
(loaded by `m3_check` as a supplementary index).

Graph effect: `e9623244f6b1` connects BOTH blind-spot cover twins
(`up-8b8c8916a24a`, `up-dab493384582`) — previously zero edges in the
whole union graph — so the genuinely-isolated set drops 14 → 12.
