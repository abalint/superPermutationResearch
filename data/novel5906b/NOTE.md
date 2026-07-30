# novel5906b — the s44 loop-swap discoveries (102 novel 5906 classes)

**UNPUBLISHED — Andrew decides if/when to publish.** Novelty gated
against the CURRENT published corpus (92 classes = 84 upstream +
Kristan + the 8 s41 discoveries merged as PR #50) AND our own
archives; re-verify against upstream before any publication step.

s44 (2026-07-30). 102 distinct 5906 classes, each INEQUIVALENT
(relabel+reversal) to all 92 published classes and to each other —
12.75× the s41 discovery event, produced by the FIRST executable rule
of the s43 loop-swap tier, iterated to its closure fixed point
(60 from the published corpus, +34 from those, +8 from those, +0).

Produced by `analysis/counting/loopswap_apply.py apply-sym` (I5): the
entry-level loop-swap rule `ab88abce72ba` — a pure 4-loop swap (24
entries removed, 24 added, ZERO door edits), extracted from the single
shallow-tier tail-conjugate pair `5906.up-a235b0e09b6c ~
5906.up-abe33e328763` (409 shared perms, below the s43 deep-tier
500-perm cut) — applied under symmetry conjugation (all 5040
relabelings × both orientations) across the 92-class published corpus,
then iterated on each round's new classes. The deep-tier rules
produced only rediscovery edges; ALL 102 novels came from this ONE
shallow-tier rule (602/602 provenance rows).

Verification: every string passes
`cargo run --release -- validate -n 7 --file <f> --complete` and
`python3 analysis/counting/m3_check.py -n 7 <f>` exits 2 (novel).

Structure: allocation is preserved per-source (the rule is
door-identical), so the 102 land in FIVE known allocations —
(844,17)×82, (838,23)×12, (839,22)×4, (840,21)×3, (842,19)×1. No new
allocation. Closure: iterating the 81-rule loop-swap vocabulary
frontier-by-frontier reaches its FIXED POINT at iteration 4
(60→34→8→0); conjugated R-K7 over all 102 is also closed — it relates
6 of them to each other (4 undirected internal edges), none back to
the old corpus. The record shell is now 194 classes (92 published +
102 here) across the same 8 allocations.

Provenance: `provenance.tsv` (source class, rule, orientation per
product). Canon index: `analysis/counting/novel5906b_canon_index.tsv`
(registered in m3_check SUPPLEMENTARY — the M3 gate now covers these).
