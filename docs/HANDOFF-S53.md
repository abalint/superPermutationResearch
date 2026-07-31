# Handoff — the s54+ front (fresh agent, start here)

Supersedes `HANDOFF-S51.md`. Read JOURNAL s53 (the strategy pivot:
K₄ vein mined out, a(6)=872 claimed twice, Houston's abandoned 5905
program = our chains #0/#24, the P0–P5 ranked program) and s52b (the
four sweep closures), then s51/s50/s49 for the closure proofs. The
active design doc is now **`docs/NOVELTY-DESIGN.md`** — read it in
full; it IS the roadmap.

## State of the world in twelve sentences

1. **The neighborhood/rewrite-rule program is EXHAUSTED at both n**,
   proven from the inside: n=7 tier closed at 220 classes (s53 K₄
   hunt — 14 residual cover groups resolved, no incomplete simplices,
   no admissible unit diffs on the 3 tier-free groups) and n=6 archive
   closed under forward i4a + the full 33-rule loop-swap table, the
   blind spot closed under the untargeted fused tier (all survivors
   SELF-maps), the promotion trade replay-dead corpus-wide (s52b: the
   can't-lose M3 hunt won nothing). New classes need external seeds
   or a new object.
2. **The vocabulary is mirror-complete**: S53A/S53B
   (`data/loopswap/rules_n7_s53.tsv`) are the reversal-mirrors of
   S51A/S51C — oracle 40/40, edges set-identical to their originals,
   zero new reachability. 886 committed directed rule ids total.
3. **a(6) = 872 has TWO independent claimed proofs** (Gheorghe
   209-cell, preliminary, O5 = the open gap; Grayzel end-to-end
   Lean 4/mathlib zero-sorries, mid-audit, different reduction). If
   either holds, 871 is dead and n=6 becomes calibration ground truth.
   Adjudicating this is **P0**.
4. **Houston's abandoned 5905 program is our Track A**: his two
   score-15 kernels (Feb 2019, never decided by anyone) are chains
   **#0 and #24** of `analysis/cover7/results_n7_merged.csv`, both
   OPEN; the field's engines have no tractable asymmetric-completion
   mode; the 138 open chains + our ledger/2-loop-law cuts are **P1**.
5. **Field provenance corrected (Andrew called it)**: LKH-at-n=7 was
   configured by Houston in the repo's first commit (2018-01) with
   zero results ever posted; KernelFinder+PermutationChains ARE
   Houston's kernel program, executed by Egan; Concorde failed at n=6
   twice; Chaffin died 2023-03 at waste 122 (not 116).
6. The strategy synthesis + three preserved research reports:
   `docs/NOVELTY-DESIGN.md` +
   `../extraDocs/2026-07-31-research-*.md`. Diagnosis in one line:
   the record+1 plateau is a tie plateau; every surveyed neighborhood
   escape came from searching a smaller structured space; refutation
   beats optimization near the optimum; do NOT respend on §4's closed
   list.
7. **The project shell is 220 classes / 9 allocations**; PUBLISHED
   still 194 — PR #52 (4× novel5906c) and PR #53 (20× novel5906d)
   both open upstream (checked s53). On merge: flip NOTE.md files,
   counts 194→198→218, per the /community-pr skill.
8. **The Python farm harness is proven for four instruments**
   (fuse/demotion/i4a/loopswap via shims + `pysweep_run.ps1`, s52b/c);
   future sweeps at either n default to the PC. Still HELD: n=6
   recomp2 520 band (the 450 band is a proven NO — non-terminating
   instances).
9. The 12-class blind spot survives everything (single rules, chains,
   targeted+untargeted fused, full sumset); `up-1b8244ba04bb` is
   arithmetically out of reach (536 > 534, 34 > 24, 536 ≢ 0 mod 6).
   Closed front — only a new tier/object reopens it.
10. Kristan's two unpublished (842,19) classes remain his to publish
    (`data/kristan5906_web/`, publication caveat in NOTE.md); the
    K₄ law says his future finds land inside existing record covers.
11. Working modes unchanged: >30 min ⇒ SWEEP-QUEUE spec + Andrew's
    launch agent (NOTHING launches from an analysis session); heavy
    tool-loops ⇒ Opus subagents; the orchestrator re-verifies every
    load-bearing claim before it enters the docs.
12. n=6 window {869..872} (Lean LB) pending P0; n=7 window
    [5888, 5906], target 5905 = δ21, alive and now the sole record
    front.

## The work menu (priority order — tracks NOVELTY-DESIGN §3)

1. **P0 — adjudicate a(6)=872** (~1 day): Grayzel statement-
   faithfulness audit (`lake build` = launch-agent item) + Gheorghe O5
   attack with the loop-cover/door grammar + the s=25/B=4 ledger
   cross-check on Houston's witness.
2. **P5 instruments** (cheap, in-session, do before any engine buy):
   fl1577 proxy benchmark; Aut groups of our known classes
   (decides Kramer–Mesner); 873-shell local-optima network;
   PatternBoost data-shape check on the 22,062.
3. **P1 — chains #0/#24 first**: wire the s34 2-loop law (5905 ⇔ 141
   2-loop cover), waste identity, fresh-doors, door-pricing into the
   DLX/SAT chain engines as cuts; then exact VLSN
   (Balas–Simonetti/corridor) and local-branching certificates;
   then Garner's full sub-5907 kernel enumeration (LAUNCH).
4. **P2 — n=6 shell-descent pilot**: unseeded diverse 873/874 corpus
   → census vs the 8 record allocations → length-reducing stack →
   m3. Size, then SWEEP-QUEUE. (n=7 version gated on unseeded
   5907/5908 entry — currently impossible, from-scratch best 5913.)
5. **P3 — cover-level boardstate triage prototype** (n=6): sample
   partial 2-loop covers, exact-arithmetic triage, diversity archive.
6. **PR watch** (#52, #53) + Andrew's standing calls (Kristan
   outreach; grammar-of-5906s publication — recommendation stands
   regardless of 5905).

## Traps (s53 additions first; s51/s50 lists still apply — read them)

- **Research-agent "X was never tried" claims are unreliable** — two
  failed against primary sources in one session. Demand positive
  citations; verify via the community repo + `gh api` before docs.
- **`../superperm` is a SHALLOW clone** — `git log` there collapses
  all history to the fetched commit. Provenance =
  `gh api repos/superpermutators/superperm/commits?path=…`. (It may
  also sit on a PR branch — both traps at once.)
- **Kristan filenames carry no hash12** — edge joins vs hash-keyed
  tables silently drop them; map via
  `analysis/counting/kristan5906_web_canon_index.tsv`
  (v0004=9f233e21883b, v0005=df2adfa160ec).
- **Concurrent sessions take session numbers** — check `git log` for
  the highest sN before naming artifacts/entries (this session
  renamed s52→s53 artifacts pre-commit). `out/s52/` belongs to the
  operator sessions; `out/s53/` to this one.
- **Do not delete `logs/` or any products dir without `lsof +D`/`ps`
  first** (s52b: a concurrent delete nearly killed a 17-min run at
  its final write); a missing `.pid` makes a healthy job look dead.
- **Monitor regexes must not alarm on zero-count summaries**
  (`NOVEL…: 0`, `ESCAPES 0` — bitten twice); diff a new instrument's
  terminal summary against the alarm regex before farm runs. Stall
  detection keys on WALKS-unchanged, not heartbeat age.
- **Sum dry-runs from FULL output** (a `tail -20` truncation produced
  a bogus 2.6× sizing in s52b); farm shards run ~2× a Mac 2-walk
  extrapolation.
- The **minimal-frame orientation trap** (s51) did real work again in
  s53: S53C-analogues hide in F/F frames — always minimize over all
  four src/tgt orientation combos.
- **Session end ritual**: JOURNAL entry, `cargo test --release`
  green (139), clippy `-D warnings`, fmt, commit → `git pull
  --rebase` → push. When this handoff goes stale, write the successor
  and repoint CLAUDE.md + agent docs.

## Reading order for a cold start

1. This file.
2. `docs/NOVELTY-DESIGN.md` (the active design doc — the P0–P5
   program and the do-not-respend list).
3. `docs/JOURNAL.md` s53, s52b, s52, s51.
4. `../extraDocs/2026-07-31-research-superperm-field.md` (the field
   state: proofs, provenance, the 5905 kernels), then the game-solving
   and math-records reports as needed per program item.
5. `analysis/cover7/results_n7_merged.csv` (chains #0/#24 = Houston's
   5905 kernels); `data/loopswap/rules_n7_s53.tsv`;
   `out/s53/k4hunt/group_verdicts.tsv` (regenerable).
6. `docs/SWEEP-QUEUE.md` (s52b results folded; recomp2 520 HELD);
   `docs/OPS-BACKGROUND-AGENT.md`; `CLAUDE.md` (commands; hard
   invariants).
