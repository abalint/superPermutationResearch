# novel5906d — the 20 s51 K₄-tier classes (PUBLISHED as PR #53; provenance caveat below)

**STATUS: PUBLISHED** — merged into superpermutators/superperm master
2026-07-31 (17:52Z) as
**PR #53** (https://github.com/superpermutators/superperm/pull/53, branch
`abalint:twenty-new-5906s-two-profiles`), with the Kristan-derivation credit
note in the PR body (his two source solutions deliberately excluded — they
are his to publish). Upstream master `77dc0d1` carries all 20 (verified by
tree diff s56, together with PR #52's four: 24 files added). Published shell
194 → 218 (both PRs merged the same day).

20 record-tying n=7 5906 classes discovered 2026-07-31 (s51) by applying the s51
rule tier (`data/loopswap/rules_n7_s51.tsv`: unit rules R-K7 / S51A / S51C of
shape (0,1,2,1) + their three 2-unit composites S51B / S51D / S51E, each with
reverses — 12 directed rules) conjugated over the 198-class project shell plus
Kristan's two unpublished classes (`data/kristan5906_web/`). Fixed point at
generation 2 in both sweeps; the 220-class shell is closed under this tier at
depth 1, and the old 864-rule vocabulary adds no edges from the new classes into
the 198 shell (25-shard marginal sweeps, both pools).

All 20: validator-complete (5906, 5040/5040), m3-inequivalent to the 198 at
discovery time, allocations 16×(838,23) + 4×(834,27) — **(834,27) is the ninth
known 5906 allocation; no previously known string occupied it.** 2-loop law
holds (142) on all. None touches the 12-class blind spot or `up-1b8244ba04bb`.

Geometric law (verified 10/10): every cover-sharing quadruple of the 220 shell
is a complete K₄ in the natural-move graph whose six undirected edges are
exactly the six s51 rules — three unit rules starring out of an OLD 198-shell
anchor class, the three composites forming the opposite triangle. Edge table:
`data/loopswap/s51_tier_edges_n7.tsv` (172 directed, hash12-normalized).

**PUBLICATION CAVEAT (read before any PR):** the s51 rules were extracted from
the admissible-frame diffs of Tomaz Kristan's UNPUBLISHED strings V0004/V0005
(posted on his website / shared by email, never submitted to
superpermutators/superperm — see `data/kristan5906_web/NOTE.md`). These 20
derived classes are this project's discoveries, but the tier's existence traces
to his strings; Andrew decides publication and should coordinate credit with
Kristan (his two classes are HIS to publish). Supplementary m3 indexes:
`analysis/counting/novel5906d_canon_index.tsv` +
`kristan5906_web_canon_index.tsv` (project shell now 220 = 198 + his 2 + these
20; PUBLISHED shell 218 since 2026-07-31 — his 2 remain the only unpublished
classes in the project shell).

Files: `5906.s51-<canon-sha12>.txt`, regenerable from the committed rule table +
corpora via `analysis/counting/loopswap_apply.py apply-sym` (run-twice
byte-agreement demonstrated; see JOURNAL s51).
