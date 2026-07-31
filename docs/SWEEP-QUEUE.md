# Sweep queue — the operator/researcher interface

The RESEARCH agent appends entries (template below). The OPERATOR
executes them top-down, fills in status/results, and never edits the
spec of a pending entry. Andrew's go-ahead is per-entry (`approved:`),
required for anything projected > 30 min. One `running` entry at a time.

## Execution order (set by Andrew, 2026-07-31) — ALL FOUR COMPLETE

Andrew queued these four on 2026-07-31 and approved them as a block. All ran
and all closed the same day; see each entry's `result:` for the numbers.

| # | entry | where | wall | outcome |
|---|---|---|---|---|
| 1 | n=6 I4-A conjugated sweep, FORWARD | Mac | 95 min | CLOSED — 12.46M replays, 0 novel; fwd edge set = the s41 rev set reversed EXACTLY (0 fwd-only, 0 rev-only) |
| 2 | fused-pair UNTARGETED, blind spot | **farm `u1`** | 7.4 min | CLOSED — 4,713,880 fused pairs, 0 escapes; all 10,942 survivors are SELF-maps |
| 3 | n=6 loop-swap, EXPANDED rule table | Mac | 75 min | CLOSED — 31,174,285 replays, 0 novel; 21,916 directed / 6,231 undirected edges |
| 4 | n=6 full-corpus PROMOTION hunt | **farm `p1`** | 18.7 min | REPLAY-DEAD — 4,716,847 completions, 100 % killed, 0 products |

Four independent closure negatives. The two farm runs went through the s52
Python harness (#4 via the new `promote_shim.py` adapter); the two Mac runs
predate the decision to move Python work to the PC — **run future Python
sweeps on the farm** (Andrew, 2026-07-31: "we have the farm for a reason").

**HELD: n=6 recomp2, 520 band** — "hold off on n=6 recomp2 for now"
(Andrew, 2026-07-31). Do not launch. Its sibling 450-band run was aborted
the same day for non-termination; before this one is reconsidered it needs
a round-robin probe and a per-walk timeout, not its current single-walk
projection.

Ordering is not consent: every entry carries its own `approved:` field and
the > 30 min launch protocol applies to each individually.

Entry template:

```
## <short name>
- spec: <exact command, from repo root>
- product: <what the run proves/produces>
- projected: <runtime estimate and how it was obtained>
- approved: NO | YES (Andrew, <date>)
- status: pending | probing | running (pid, started) | done | aborted
- result: <verbatim summary line + verdict>
```

## Farm execution (added 2026-07-29 s29-ops) — prefer this over the Mac

`tail-atsp` is single-threaded, so the 22,062-walk corpus shards perfectly:
the farm PC runs 24 shards on 24 of its 28 cores, turning a ~12 h single-core
sweep into ~36 min. Details, scripts and the alarm path: `docs/OPERATIONS.md`
§"tail-atsp farm harness". Two things a fresh operator must know:

- The PC has **no Rust toolchain**. The binary is cross-compiled on the Mac
  (`x86_64-pc-windows-gnu`, mingw-w64 linker, `crt-static` → only system DLLs)
  and scp'd to `F:\superpermFarm\tailatsp\superperm.exe`. **Rebuild and reship
  after any change to `src/tailatsp.rs` or `src/corpus.rs`.**
- Quote every farm rate from a **round-robin** probe, never the first-K files:
  the s28b "0.6 s/walk at anchor 450" was alphabetical-prefix bias; the true
  corpus mean is 2.0 s/walk (3.3×).

---

## anchor-450 sweep (block-order-optimality frontier, third band)
- spec: `cargo run --release --quiet -- tail-atsp -n 6 --dirs data/upstream872 --anchor 450 --max-blocks 50 --quiet --out-dir data/surgery_finds`
  — RUN ON THE FARM INSTEAD, 24-way sharded (see "Farm execution" below):
  `powershell -File F:\superpermFarm\tailatsp\talaunch.ps1 -Anchor 450 -MaxBlocks 50 -Workers 24 -Tag a450b50`
- product: extends the s28b law ("every known 872 is block-order-optimal")
  to ~270-perm tails, or finds an 871 candidate (exit 2 → alarm path).
- projected: **REVISED — the s28b 3.5 h figure was sorted-order bias.** A
  24×40-walk round-robin probe (`runs\probe450`, 960 walks, 0 improvements)
  measured **2.0 s/walk**, not 0.6 → single-core full corpus is ~12 h. On 24
  farm cores: 22,062 walks at ~10.2 walks/s aggregate ≈ **36 min** wall
  (heavy-tail shards may push the last worker to ~1 h).
- approved: YES (Andrew, 2026-07-29 — "pick up the background execution work
  that needs to be done. make sure it runs on the pc and you monitor it")
- status: **done** (farm run `a450b50`, 24 workers, 2026-07-29 20:17:58 →
  21:06:53 PC time, 48.8 min wall / 13.9 core-hours)
- result: **0 improvements over the full corpus.** Ledger sum over 24 workers:
  `22,062 walks, 22,062 block-order-optimal, 0 improved, 0 skipped, 0 ties`
  (verdicts OK:24, no finds, no alarm; slowest worker 2,921 s vs 2,091 s mean).
  **Nothing was skipped** — the adaptive anchor solved every walk, so this is
  the whole corpus, not a solvable subset. NEW LAW (third band, same
  fixed-decomposition caveat): every known 872 class is block-order-optimal at
  anchor ≥ 450 / ≤ 50 blocks, i.e. across its last ~270 perm visits. With
  s28b (≥ 585, ≥ 520) and s9 (tablebase-optimal ≤ 25-perm tails), reordering
  cover blocks is now dead as a route to 871 out to ~270 perms — the missing
  char must RECOMPOSE cycles (I2/I2a), which is what the merge entry tests.

## tie-census probe (are allocation shells S1-connected?)
- spec: `cargo run --release --quiet -- tail-atsp -n 6 --dirs data/upstream872 --anchor 585 --ties --tie-cap 256 --limit 100 --quiet`
- product: rate measurement for the full tie census + first sample of
  new-allocation tie frequency. (Ties = equal-cost reorderings; those
  landing in a different L0 allocation measure how connected the
  allocation shells are under S1 alone — does (144,4) or any ip=1
  target EVER appear?)
- projected: **MEASURED — the fear was wrong.** Farm probe `probe585ties`
  (24×40 = 960 walks): 6.3 core-s = **6.6 ms/walk**, only 4.7× the plain
  anchor-585 sweep, not the 100× that "tie collection weakens B&B pruning"
  suggested. Deeper band `probe520ties` (960 walks): 247 core-s =
  **0.26 s/walk**, 6.4× the plain anchor-520 sweep.
- approved: YES (Andrew, 2026-07-30 — "run it")
- status: **done** (both bands, farm runs `probe585ties` / `probe520ties`)
- result: 585 band: 960 walks, 0 ties. 520 band: 960 walks, **1 new-allocation
  tie** — so the deeper band is where the question lives, and the full census
  below was run at both.

## I2a merge sweep, anchor 520 (full corpus)
- spec: `cargo run --release --quiet -- tail-atsp -n 6 --dirs data/upstream872 --anchor 520 --max-blocks 40 --merge --quiet --out-dir data/surgery_finds`
- product: extends the s30 merge law to ~200-perm tails. Any "MERGE
  IMPROVEMENT" banner = an 871 candidate (exit 2 → m3_check + validate,
  alarm path). Equal-cost 872s at S−1 are also written (`merge-eq-*`)
  and each goes through m3_check — a NOVEL class (exit 2) or a first
  872 in an unoccupied allocation would be an M3-class event. The
  300-walk probe already found 1 equal-cost 872 (a rediscovery of the
  committed specimen pair's partner class — pipeline proven in the
  wild).
- projected: **MEASURED on the farm** — round-robin probe `probe520merge`
  (24×40 = 920 walks scored, 979 core-s) gives **1.06 s/walk** on a PC core,
  22 merge moves tried per walk. The entry's first-300 figure implied
  0.35 s/walk, so the alphabetical bias here is ~1.9× (it was 3.3× at anchor
  450 — always re-probe round-robin). Full corpus: ~6.5 core-hours → ~16 min
  mean, **~25 min wall** on 24 cores (a450b50's slowest/mean imbalance was
  1.4×). Farm caveat handled: `superperm.exe` recross-compiled and reshipped
  from clean `c0c64e9` with a BUILD.txt provenance stamp.
- approved: YES (Andrew, 2026-07-29 — "the md doc has been updated to add full
  anchor-520 merge sweep in SWEEP-QUEUE.md run it when this operation is
  finished")
- status: **done** (farm run `a520b40merge`, 24 workers, 2026-07-29 21:11:14 →
  21:34:59 PC time, 23.7 min wall / 7.5 core-hours — the 25 min projection held)
- result: **0 merge improvements over the full corpus; exactly ONE equal-cost
  872 at S−1, and it is a rediscovery.** Ledger sum over 24 workers:
  `22,062 walks, 22,062 block-order-optimal, 0 improved, 0 skipped` plus
  `488,350 merge moves tried, 0 improved (871 candidates), 1 equal-cost 872 at
  S-1` (verdicts OK:24, no alarm, 0 skipped). The one find,
  `merge-eq-872.up-0105a4b77ce8-1`, passed both gates: validator says complete
  872, and `m3_check.py` returns **exit 0 — EQUIVALENT to known class
  872.up-b020caf20414**. That is the (142,6) partner of the committed specimen
  pair, re-derived from its (143,5) side: the s28b tie oracle's result reached
  again by the merge move, from the full corpus rather than a hand-picked
  anchor. So the merged-allocation histogram over 22,062 classes is a single
  cell, `(142,6,0,0): 1`. **The S−1 merge move, applied exhaustively to every
  known 872's last ~200 perm visits, reaches no 871 and no NOVEL 872** — it
  only re-finds the one edit nature already performed. Extends the s30
  anchor-≥585 merge law (240,874 moves, zero completions) to ~200-perm tails at
  2× the move count.
  Copy of the find + gate output: `data/farm_finds/a520b40merge/`.

## recomp-1 sweep, anchor 585 (full corpus)
- spec: `cargo run --release --quiet -- tail-atsp -n 6 --dirs data/upstream872 --anchor 585 --recomp --quiet --out-dir data/surgery_finds`
- product: closes the single-edit tier at the 585 band: every alternative
  arc-partition of every tail cycle (subsumes merge; adds splits,
  repartitions, entry rotations, 1|5 arcs), re-solved exactly. Any
  RECOMP IMPROVEMENT = 871 candidate (exit 2, alarm path). Equal-cost
  finds in NEW allocations are written (`recomp-eq-*`); same-allocation
  equals are ~48% of moves (dense shell) and sampled 2/walk
  (`recomp-sameeq-*`) — m3-check a random subsample only (a 60-sample
  local check was 100% equivalent-to-known). s31 local evidence (138
  walks, ~175k moves): 0 improvements, 0 new-allocation equals.
- projected: **MEASURED** — round-robin probe `probe585recomp` (24×25 = 600
  walks, 7,695 core-s) gives **12.8 s/walk**, 2.4× the entry's alphabetical
  5.4. Full corpus = 78 core-hours → ~3.3 h mean, **~4.5–5 h wall** on 24
  cores at the 1.4× shard imbalance measured on a450b50. Probe itself:
  763,546 moves, 0 improvements, 0 new-allocation equals, 367,292
  same-allocation equals (48% — the dense shell, as s31 said). Binary
  reshipped from clean `e286355` (BUILD.txt provenance on the PC).
- approved: YES (Andrew, 2026-07-30, after being given the ~5 h figure)
- status: **done** (farm run `a585recomp`, 24 workers, 2026-07-30 06:15:18 →
  09:45:35 PC time, **210.2 min wall / 78.3 core-hours**; slowest worker 210.0
  min vs 195.8 mean = 1.07× imbalance, the best balance of any sweep so far)
- result: **The single-edit tier is CLOSED at the 585 band.** Ledger sum over
  24 workers: `22,062 walks, 22,062 block-order-optimal, 0 improved, 0 skipped`
  plus `27,873,361 recomp moves tried, 0 improved (871 candidates), 0
  equal-cost 872s in NEW allocations, 13,441,109 equal-cost same-allocation`
  (verdicts OK:24, no alarm, 0 candidate files, 0 `recomp-eq-*` files).
  - **28 million single-cycle recompositions — every alternative arc-partition
    of every tail cycle of every known 872 — produce no 871 and no walk in any
    new allocation.** This subsumes the merge result (`a520b40merge`) and the
    tie result (`a520ties`/`a585ties`) as the general single-edit statement at
    this band.
  - The shell is dense but **degenerate**: 48.2% of moves (13.4M) land at equal
    cost, yet an M3 gate over a **random 200-file sample** of the 44,124
    emitted same-allocation equals (2/walk sampling, all 24 workers covered)
    returns **200/200 valid 872 and EQUIVALENT TO KNOWN — and in every one of
    the 200, equivalent to its OWN source class**, not to some other known
    class. So the equal-cost neighbourhood reachable by one recomposition is
    huge in move count but collapses to a single point in class space (up to
    relabel+reversal). Caveat, stated plainly: that is a 200-sample of a
    2-per-walk sample: it is strong evidence, not exhaustion.
  - Sample + gate output: `data/farm_finds/a585recomp_sample/` (200 files,
    `m3_check` exit 0).
- next: the same instrument at a deeper anchor is the open question. Scaling
  the measured 12.8 s/walk at 585 by the plain-sweep ratio 520/585 (≈ 25×)
  puts a 520-band recomp sweep near **2,000 core-hours ≈ 3.5 days even on 24
  cores** — so it needs either a cheaper move filter or a sampled corpus, not
  a bigger budget.

## tie-census full corpus
- spec: as probe, without `--limit`, `--out-dir data/surgery_finds`
- product: corpus-wide new-allocation tie count + reached-allocation
  histogram (S1 shell-connectivity map; SURGERY-DESIGN §8 next-step).
- projected: 585 band ~150 core-s (<1 min wall); 520 band ~5,700 core-s
  (~6 min wall on 24 cores).
- approved: YES (Andrew, 2026-07-30 — "run it")
- status: **done** — farm runs `a585ties` (0.5 min wall) and `a520ties`
  (5.6 min wall / 1.8 core-hours), both 24 workers, 0 skipped, no alarm.
- result: **The allocation shells are S1-disconnected except for the one edge
  nature already made.**
  - anchor ≥ 585: `22,062 walks, 22,062 block-order-optimal, 0 improved,
    0 skipped, 0 new-allocation ties`. Expected in hindsight and nearly
    vacuous: the one tie known to exist (the s28b oracle) sits at anchor 580,
    just BELOW this cut — which is why the deeper band was run.
  - anchor ≥ 520 / ≤ 40 blocks: `22,062 walks, 0 improved, 0 skipped,
    **1 new-allocation tie**`. The single tie is
    `872.up-0105a4b77ce8` (143,5,0,0) → **(142,6,0,0)**, and it gates as a
    rediscovery: validator complete 872, `m3_check` **exit 0 — equivalent to
    known class 872.up-b020caf20414**. That is the committed specimen pair
    again, found from the full corpus instead of a hand-picked anchor.
  - So the reached-allocation histogram over 22,062 classes is one cell with
    one member. **(144,4) is never reached; no ip=1 target is ever reached** —
    consistent with "no known 872 uses a priced skip". Read alongside the
    `a520b40merge` result, this is the same conclusion by a second, independent
    move type: S1 reordering AND the S−1 merge each produce exactly one
    cross-allocation product corpus-wide, and it is the same known pair.
  - Copy of the find + gate output: `data/farm_finds/a520ties/`.
- next band (NOT run — needs approval, > 30 min tier): ties at anchor 450 /
  ≤ 50 blocks. Extrapolating the 6.4× tie overhead onto the measured 2.0
  s/walk plain rate gives ~13 s/walk → **~3.5–4 h wall even on 24 cores**.

## n=7 recomp, 4840 band (~200-perm tails) — first deep n=7 recomposition sweep
- spec: `cargo run --release --quiet -- tail-atsp -n 7 --dirs data/upstream5906,data/upstream5907 --anchor 4840 --max-blocks 40 --recomp --quiet --out-dir data/surgery_finds`
- product: extends the s33 n=7 recomposition-closure law from the 4905 band
  (~136-perm tails, 199,391 moves, closed) to ~200-perm tails; alarm paths:
  any improvement = 5905/5906-candidate (exit 2 → validate + `m3_check -n 7`),
  any new-allocation equal = first instrument-created n=7 cross-allocation
  walk (the Kristan-seam watch: does (844,17)→(843,18) ever appear?).
- projected: measured 4-walk probe = 51.7 s/walk → ~75 min single-core. Farm
  (12-way shard of the 87-walk corpus): **actual 47.3 s/walk, 68.6 core-min,
  slowest worker 9.5 min** — the estimate held (no sorted-order bias here,
  since 87 files is effectively the whole corpus either way).
- approved: YES (Andrew, 2026-07-30 — "run the three cheap ones back to back")
- status: **done** (farm run `n7a4840recomp`, 12 workers, 2026-07-30)
- result: **0 improvements, 0 new-allocation equals — the n=7 recomposition
  closure law extends from ~136-perm tails to ~200-perm tails.** Ledger sum
  over 12 workers: `87 walks, 87 block-order-optimal, 0 improved, 0 skipped`
  plus `297,232 recomp moves tried, 0 improved (5905/5906 candidates), 0
  equal-cost in NEW allocations, 144,092 equal-cost same-allocation`
  (verdicts OK:12, no alarm). The Kristan-seam watch is negative at this band:
  **(844,17)→(843,18) never appears.** Same-allocation equal rate is 48.5%
  (144,092/297,232) — within a whisker of the n=6 figure (48.2% in
  `a585recomp`), so the dense-but-degenerate shell is not an n=6 artifact.
  Corpus note: run over the combined 87-walk corpus (84 × 5906 + 3 × 5907).
- ops note: the supervisor crashed at startup on this run (a PowerShell parse
  error in freshly-added recomp2 banner code — nested double quotes inside an
  interpolated string). The WORKERS were unaffected and completed normally;
  only STATUS/ledger aggregation was lost, and it was rebuilt afterwards by
  re-running `tasuper.ps1` against the finished logs. Fix + a mandatory
  post-ship parse check are in `docs/OPERATIONS.md`.

## n=7 deep-seam probe: merge+ties at anchor 4600 (~440-perm tails)
- spec: probe first: `cargo run --release --quiet -- tail-atsp -n 7 --dirs data/upstream5906 --anchor 4600 --max-blocks 60 --merge --ties --tie-cap 256 --limit 8 --quiet --out-dir data/surgery_finds`
- product: the s33 negative (0 equal-cost merges, 0 cross-allocation ties at
  4905/4770 bands) says the (844,17)↔(843,18) Kristan unit-trade — the n=7
  analog of the n=6 natural pair — is NOT realizable in the last ~270 perms.
  This probes whether it (or any S1/S−1 shell edge) appears by ~440 perms.
- projected: **MEASURED** — 12-walk round-robin probe (`n7a4600seam`): mean
  **59.1 s/walk**, slowest 422.7 s. Far under the 5 min/walk stop threshold,
  so the full corpus was swept too (`n7a4600seamfull`): 57.6 core-min,
  **16.6 min wall** on 12 workers.
- approved: YES (Andrew, 2026-07-30 — "run the three cheap ones back to back")
- status: **done** (probe `n7a4600seam` 12 walks, then full `n7a4600seamfull`
  87 walks; both 12 workers, 0 skipped, no alarm)
- result: **The Kristan unit-trade does not appear at this band either.** Full
  corpus: `87 walks, 87 block-order-optimal, 0 improved, 0 skipped, 0
  new-allocation ties` plus `2,954 merge moves, 0 improved, 0 equal-cost`. No
  S1 tie and no S−1 merge anywhere in the n=7 corpus produces a
  cross-allocation walk; (844,17)↔(843,18) stays unrealized.
- **IMPORTANT caveat — the band is NOT what the anchor says.** Every walk hit
  the `--max-blocks 60` ceiling, so the adaptive anchor cut DEEPER than
  requested: observed anchors 4629–4689 against the requested 4600, i.e. tails
  of ~350–410 perms, not the ~440 the entry's title claims. At n=7 the block
  ceiling, not the anchor, is what binds. Reaching a true 440-perm tail needs
  ~70–80 blocks, which is a different (and much more expensive) exact-solve
  regime — so "merge+ties are closed to ~440 perms" is NOT yet supported; what
  is supported is ~410.

## n=7 recomp2, 4840 band — I3 pair-compound closure over the whole n=7 corpus
- spec: `cargo run --release --quiet -- tail-atsp -n 7 --dirs data/upstream5906,data/upstream5907 --anchor 4840 --max-blocks 56 --recomp2 --quiet --out-dir data/surgery_finds`
- product: the first pair-compound (I3) closure statement at n=7 —
  extends the s33 recomp-1 closure to 2-compounds under T1 (net −2..0)
  + T2 (vocabulary) + single prefix-part extraction. Alarm paths: any
  improvement = 5905/5906 candidate (exit 2 → validate + `m3_check -n
  7`); any equal-length (844,17)↔(843,18) = the KRISTAN SEAM (the
  instrument banners it); any other new-allocation equal = first n=7
  cross-allocation compound. Λ-tripwire violations are bannered too —
  drop everything if one appears (solver bug or first counterexample
  to the s35 loop-count relation).
- projected: s38 single-walk probe implied ~2.2 h single-core. Farm actual
  (12 workers, reshipped binary from clean `bdc9625`): **71.4 core-min,
  8.5 min wall**, slowest worker 8.4 min — 1.6× faster per walk than the
  single-walk probe implied (49 s/walk vs 89), because the probe walk was an
  unusually wide 33-block instance.
- approved: YES (Andrew, 2026-07-30 — "run the three cheap ones back to back")
- status: **done** (farm run `n7a4840recomp2`, 12 workers, 0 skipped, no alarm)
- result: **The pair-compound tier is CLOSED at n=7 — and unlike every earlier
  tier, its equal-cost shell is EMPTY.** Ledger sum over 12 workers:
  `87 walks, 87 block-order-optimal, 0 improved, 0 skipped` plus
  `7,321,635 exact re-solves, 0 improved (candidates), 0 equal-cost in NEW
  allocations, 0 equal-cost same-allocation, 0 loop-relation violations`
  (verdicts OK:12). All three tripwires silent: no 5905/5906 candidate, **no
  KRISTAN SEAM**, and **no Λ violation** — so the s35 loop-count relation
  survives 7.3M independent exact re-solves, which is the strongest evidence
  it has.
  - Funnel, summed over the corpus: **1,574,583,671 raw pairs → 9,673,573
    post-T1 (0.61%) → 7,321,635 exact re-solves**, from 189 extraction
    candidates. Net split −2/−1/0 = 49,735 / 943,145 / 6,328,755.
  - **The contrast with recomp-1 is the finding.** Single recompositions have
    a dense equal-cost shell — 48.5% of moves at n=7 (`n7a4840recomp`), 48.2%
    at n=6 (`a585recomp`). Pair compounds have **zero** equal-cost outcomes in
    7.3M exact re-solves. Compounding two recompositions does not explore a
    wider equal-cost plateau; it leaves the plateau entirely and strictly
    costs. That is consistent with the s38 §10.6 refutation (the natural
    2-compound prices +6 over equal) and sharpens it: at this band the
    compound tier is not merely closed to improvements, it is closed to
    equality.

## n=6 recomp2, 520 band (full corpus) — farm, tight first
- spec (tight pass, S−1 family only): `cargo run --release --quiet -- tail-atsp -n 6 --dirs data/upstream872 --anchor 520 --max-blocks 42 --recomp2 --recomp2-tight --quiet --out-dir data/surgery_finds`
  — then, if Andrew wants the d3−1 family too, the same without
  `--recomp2-tight` (~4× the cost).
- product: corpus-wide pair-compound closure at the 520 band (the band
  where the single tie and the merge completion live). Same alarm
  paths as above at n=6 (871 candidate / new-allocation equal / Λ).
- projected: s38 single-walk probe (A side, 41 blocks, FULL nets):
  367.5 s/walk, 111,216 solves — single-walk, so treat as
  order-of-magnitude only (round-robin probe REQUIRED before the farm
  commit, per the a450b50 lesson). Full corpus full-T1 ≈ 2,250
  core-hours ≈ **3.9 days wall on 24 cores**; `--recomp2-tight` cuts
  solves ~4× (27.5k/walk measured split) → ≈ **1 day wall**. Farm
  binary MUST be reshipped first (s38 changed `src/tailatsp.rs`).
  **Caveat added 2026-07-31:** this projection descends from a SINGLE-walk
  probe, and the 450-band sibling run proved this instrument has
  non-terminating instances at 54 blocks with no block-count predictor.
  Treat "≈ 1 day wall" as unvalidated until a round-robin probe says
  otherwise, and do not launch without a per-walk timeout.
- approved: NO
- status: **pending — HELD** (Andrew, 2026-07-31: "hold off on n=6 recomp2
  for now"). Do not launch; see the execution-order block at the top.
- result: —

## n=6 recomp2, 450 band — probe only, then decide
- spec: `cargo run --release --quiet -- tail-atsp -n 6 --dirs data/upstream872 --anchor 450 --max-blocks 56 --recomp2 --recomp2-tight --quiet --out-dir data/surgery_finds --limit <probe>`
- product: the compound band closest to anchored reach of the compound
  tier (54-block instances — the exact-B&B working edge). The s38
  verdict (§10.8) says the natural compound is NOT expressible even
  here, so this band's value is the negative sweep + any novel finds.
- projected: s38 single-walk probes at FULL nets were killed
  unfinished (> 10 and > 12 solver-minutes without completing one
  54-block walk) — full-net full-corpus is off the table;
  `--recomp2-tight` + round-robin probe sizes the real cost before
  any decision.
- approved: NO **on this entry** — the run was nonetheless launched
  2026-07-30 13:38:36 as `n6a450r2tightprobe` (96-walk round-robin
  probe, 24 workers × 4 walks). The go-ahead was given outside this
  file and never recorded here; the entry sat `pending` for the whole
  15 h of the run. Bookkeeping gap, noted at abort.
- status: **aborted** (farm run `n6a450r2tightprobe`, 24 workers,
  2026-07-30 13:38:36 → `ABORTED by tastop.ps1 at 2026-07-31 05:55:24
  (killed 3)`; 90/96 walks, 21/24 shards; Andrew's call after the
  no-progress diagnosis below)
- result: **the decision this entry asked for is NO — the 450-band
  recomp2 sweep is not viable as specced.** Zero on every alarm path
  over 4,892,204 recomp2 re-solves: `IMP=0 TIES=0 MIMP=0 MEQ=0 RIMP=0
  REQN=0 REQS=0 R2IMP=0 R2EQN=0 SEAM=0 LAMBDA=0 ALARM=0`.
  - **Rate (21 finished shards, 84 walks, 76,223.8 s total):** mean
    **907 s/walk**, median ~717 s/walk; shard times 890.8 s → 10,170.8 s
    (w08 13:53:48 → w21 16:28:37). Extrapolated to the 22,062-class
    archive: ≈ 5,560 core-hours ≈ **9.6 days wall on 24 cores** — and
    that figure is a floor, because it counts only walks that finish.
  - **Three walks did not finish.** w09/w12/w14 each entered one walk
    and stayed there: last ledger row 16:28:37, then `rate=0 walks/s`
    for **12.4 h** until the abort. Not a hang and not swap — each
    straggler held 54,705 s CPU at ~100 % of a core with a 7 MB
    working set, i.e. genuinely searching. w09's log pins the
    instance: `872.up-009579d4b6ec.txt` (anchor=451 blocks=54),
    entered ~14:03, no result line after **~14.8 h**.
  - **Block count does not predict divergence** (new trap): the same
    worker cleared `872.up-001636390089.txt` at **54 blocks** in
    239.9 s and `872.up-00658203dd95.txt` at 51 blocks in 664.3 s,
    then stalled indefinitely on another **54-block** instance. The
    exact-B&B edge at this band is instance-structural, not a block
    threshold — so no `--max-blocks` setting makes this band safe.
  - Confirms and sharpens the s38 record (§10.8): `--recomp2-tight`
    bought its ~4× and still did not make these instances terminate.
  - If this band is ever revisited, it needs a per-walk wall-clock
    cap in the instrument (skip-and-log on timeout), not a bigger
    farm. The 6 unswept walks are the only gap in an otherwise
    all-zero 90-walk sample.

## n=6 I4-A conjugated sweep, FORWARD directions (full archive) — local, ~90 min
- spec: `python3 analysis/counting/i4a_apply.py apply-sym data/upstream872 --only fwd --out data/i4a_products_sym_fwd`
  (the rev directions ran s41 — see JOURNAL; fwd = R-compound-fwd +
  R-unit-fwd, the promiscuous-precondition directions that dominate
  runtime: 500-walk round-robin probe measured 278 ms/walk total with
  fwd replays ~99% of cost → full archive ≈ 100 min single-core
  local Python; RAM trivial).
- product: closure of the known n=6 corpus under the SYMMETRY-
  CONJUGATED forward rules (rotor→door direction: (145,3)→(143,5) and
  (143,5)→(142,6) plus off-shell firings). At n=7 the analogous sweep
  produced 8 NOVEL classes in 2 never-seen allocations
  (data/novel5906/) — the n=6 fwd sweep is the same question for the
  (143,5)/(142,6) shells. Alarm paths: any product shorter than 872
  (exit banner, M3 ritual), any NOVEL class (auto-written + bannered;
  gate with m3_check afterward as a double-check).
- projected: ≈ 100 min local single-core (probe-calibrated,
  round-robin). No farm, no reship. Heartbeats per the launch
  protocol if run by the operator.
- approved: **YES (Andrew, 2026-07-31 — "queue the n=6 I4-A job" first of
  four, execution-order block at top)**
- status: **done** (2026-07-31, ~95 min wall, single-core local, pid 31753,
  log `logs/i4a_fwd_n6.log`, exit 0, no alarm). Launch note for the next
  operator: run it with `python3 -u` — without it Python block-buffers the
  redirected stdout and the job is invisible for its entire runtime.
- result: **the n=6 archive is CLOSED under the conjugated FORWARD rules —
  and the forward directions add ZERO connectivity over the s41 reverse
  sweep.** Verbatim tail:
  ```
  R-compound-fwd:edge: 16      R-compound-fwd:replayed: 6209164
  R-unit-fwd:edge: 4           R-unit-fwd:replayed: 6254549
  20 directed edges (20 undirected) -> data/i4a_products_sym_fwd/i4a_sym_edges.tsv
  corpus CLOSED under the conjugated rule vocabulary (no novel classes)
  ```
  - **12,463,713 replays over all 22,062 classes × 720 relabelings × both
    orientations → 0 NOVEL, 0 SHORTER.** No product files written at all;
    the out dir contains only the edge TSV.
  - **The edge set is the reverse sweep's, reversed — exactly.** Comparing
    `data/i4a_products_sym_fwd/i4a_sym_edges.tsv` against the s41
    `..._rev/i4a_sym_edges.tsv` with source/target swapped: 20 shared, **0
    fwd-only, 0 rev-only**. The rule/count split matches too (16
    R-compound + 4 R-unit in both). So the natural-move graph of the known
    n=6 corpus is precisely these 20 undirected edges, now confirmed
    independently from both directions.
  - **Answers the entry's question with a NO.** It asked whether the
    promiscuous forward directions would yield novel (143,5)/(142,6)
    classes the way the n=7 analogue produced 8 novel 5906s. They do not.
    The n=6/n=7 asymmetry stands and sharpens: a 22,062-class corpus has
    exhausted its own move-closure in BOTH directions, while n=7's
    84-class corpus was not closed under even one seam move.
  - Directional note: fwd firing is not rarer than rev (6.21M vs 6.25M
    replays — near-identical), so the closure is not a precondition
    artifact. The rules fire constantly and always land on known classes.

## n=6 loop-swap conjugated sweep, EXPANDED rule table (30 shallow-tier rules) — local, ~2 h
- spec: `python3 analysis/counting/loopswap_apply.py apply-sym -n 6 --rules data/loopswap/rules_n6_a360.tsv --dirs data/upstream872 --out data/loopswap/products_n6_expanded --skip-rules 9a9c0f8835c0,47c49d109d2f,7a94c5053e55`
- product: closure (or novel n=6 classes) under the 30 loop-swap rules
  extracted from the shallow tail-conjugacy tiers (≥360 shared perms)
  that are NOT covered by the already-swept 3 deep rules (those ran s44
  local: 7.0M replays, 0 novel, 9,654 edges). At n=7 the expanded-table
  sweep produced **60 novel 5906 classes from one shallow-tier rule** —
  this is the same question at n=6, where the corpus is 240× bigger and
  the deep tier alone was closed. Alarm paths: any product < 872 (M3
  ritual, drop everything); any NOVEL class (auto-written + bannered,
  re-gate with m3_check).
- projected: dry-run MEASURED (s44): 31,174,285 candidate replays for
  the 30 rules (vs 7.0M for the deep 3, which took ~20 min end-to-end
  local). At the measured ~5.8k replays/s: ~90 min replay + ~8 min
  index build ≈ **~2 h local single-core**; RAM ~1.5 GB (fits beside
  normal work). Two rules dominate (5.6M candidates each — the 5-entry
  atoms); `--skip-rules` can defer them for a 3× cheaper first pass if
  preferred.
- approved: **YES (Andrew, 2026-07-31)** — third in the execution-order
  block; started ahead of the fused-pair item because that one is
  build-blocked (see its entry).
- status: **running** (pid in `logs/lswap_n6_expanded.pid`, launched
  2026-07-31 ~07:55, log `logs/lswap_n6_expanded.log`, abort = `kill $(cat
  logs/lswap_n6_expanded.pid)`). Two operator notes:
  - **`--dry-run` prints `0 directed edges / corpus CLOSED`.** That is a
    SIZING ARTIFACT — dry-run executes no replays. Do not read a dry-run
    tail as a closure result.
  - **This instrument prints nothing between setup and the final
    summary** (no periodic progress line, unlike `i4a_apply.py`), so log
    silence is EXPECTED and a log-stall detector cries wolf here. Judge
    health from the process: ~90–100 % of one core at flat RSS.
- result: **the n=6 archive is CLOSED under the conjugated loop-swap
  vocabulary — 0 novel, 0 shorter.** ~75 min wall (07:55 → 09:10),
  single-core, exit 0, no alarm. Verbatim tail:
  ```
  replayed:      31,174,285      replay-killed: 31,150,727  (99.924%)
  edge:              23,542      self-edge:            16
  21916 directed edges (6231 undirected) -> data/loopswap/products_n6_expanded/lswap_sym_edges_n6.tsv
  corpus CLOSED under the conjugated loop-swap vocabulary
  ```
  - 31.17M conjugated replays over 20,400 distinct instances; 99.92 %
    die at replay, and the 23,542 survivors are all rediscoveries —
    they resolve to a **21,916-directed / 6,231-undirected** edge set
    among known classes, plus 16 self-edges. Zero products left the
    known shell.
  - Scale contrast worth keeping: this n=6 natural-move graph has 6,231
    undirected edges against the n=7 union's 2,006 — the n=6 corpus is
    both closed AND densely interconnected, while n=7 stays sparse and
    open. Same asymmetry the I4-A fwd sweep found from the other side.
  - **SIZING CORRECTION (operator error, recorded so it is not
    repeated).** The pre-launch note here claimed "12,053,443 candidate
    replays, a 2.6× cut from `--skip-rules`". That was wrong: it came
    from summing a `tail -20`-TRUNCATED dry-run listing — only 17 of the
    27 rule lines were visible. The true figure is the 31,174,285 above,
    i.e. **`--skip-rules` bought no measurable cut at this scale** and
    the s44 projection of 31.17M was exactly right. Sum a dry run from
    the full output, never from a tail.
  - **Scope, corrected.** The rule table has **33** data rows, not 30, and
    the run's own log carries 31 `replayed:` lines (30 per-rule + 1 total).
    So this sweep covered **30 of 33** rules — not the "27 of 30" first
    recorded here, which mis-stated both numbers.
    The 3 excluded by `--skip-rules`
    (`9a9c0f8835c0,47c49d109d2f,7a94c5053e55`) are **s44's 3 deep rules,
    already swept on 2026-07-30** — the flag was avoiding a redundant
    re-run, not deferring work. Re-running them (entry below) reproduced
    s44's edge file byte-identically. **So closure under the FULL 33-rule
    table holds: 30 here + 3 at s44, 0 novel in both.** An earlier caveat
    on this entry claimed a 27/30 or 30/33 coverage hole; withdrawn.
  - Sizing of those 3, for the record: **6,966,546 candidates**
    (47c49d109d2f 5,660,452 + 9a9c0f8835c0 1,134,102 + 7a94c5053e55
    171,992). Counter-intuitively the CHEAP-looking rule dominates —
    `47c49d109d2f` has only 5 `ents_out` against 9a9c…'s 15 and 7a94…'s
    20, and fewer required entries means a LESS restrictive precondition,
    hence far more candidates. **Do not rank loop-swap rule cost by entry
    count — invert it.**
  - The two tiers' edge sets are **DISJOINT**: union 41,224 = 21,916 (these
    30 rules) + 19,308 (s44's deep 3), overlap **0**.

## n=6 loop-swap, the 3 DEFERRED rules (completes the 33-rule table) — local, ~20 min
- spec: `python3 -u analysis/counting/loopswap_apply.py apply-sym -n 6 --rules data/loopswap/rules_n6_deferred3.tsv --dirs data/upstream872 --out data/loopswap/products_n6_deferred3`
  (`rules_n6_deferred3.tsv` = the 3 rows `--skip-rules` deferred from the
  33-row `rules_n6_a360.tsv`: `9a9c0f8835c0,47c49d109d2f,7a94c5053e55`.)
- product: closes the gap left by the expanded sweep, which covered 30 of 33
  rules. Only with this does "the n=6 archive is closed under the FULL
  expanded loop-swap vocabulary" become an earned claim. Alarm paths: any
  product < 872 (M3 ritual), any NOVEL class.
- projected: dry-run MEASURED (full output, not a tail): **6,966,546
  candidates**, 1,620 conjugated instances — 22 % on top of the 30-rule
  sweep's 31.17M. At that sweep's ~6,930 replays/s ⇒ ~17 min replay +
  ~3 min index build ≈ **20 min single-core**.
- approved: YES (Andrew, 2026-07-31 — "do the 3 deferred loop swap rules")
- status: **done** (local, pid 84070, 2026-07-31 09:44 → 09:58, ~14 min)
- result: **THE PREMISE OF THIS ENTRY WAS WRONG — there was no gap. The 3
  "deferred" rules ARE s44's 3 deep rules, already swept on 2026-07-30.**
  `--skip-rules` in the expanded spec was excluding already-done work, not
  postponing unfinished work, and the operator (me) misread it as a
  coverage hole.
  - Proof: this run's `lswap_sym_edges_n6.tsv` is **byte-identical** to the
    committed `data/loopswap/lswap_sym_edges_n6.tsv` — same sha256
    `d459c78e9fdd…`, 19,308 directed edges both. s44's commit describes
    exactly this: the n=6 vocabulary "collapse[s] to 3 directed n=6 rules"
    and its conjugated sweep was "CLOSED (0 novel, 7.0M replays)"; our
    dry-run measured 6,966,546 candidates for the same 3. 19,308 directed
    = 2 × s44's reported 9,654 undirected. All consistent.
  - **So "closed under the FULL 33-rule expanded table" was already earned
    before today**: 30 rules (s52b expanded sweep) + 3 rules (s44) = 33,
    0 novel in both. The caveat previously recorded on the expanded entry
    is withdrawn.
  - What the run DID buy, and it is worth having: a **cross-session,
    cross-day byte-exact reproducibility control**. Same instrument, new
    process, one day later, different session — identical sha256. The repo
    prizes run-twice byte-agreement; this is run-twice across sessions.
  - **New structural fact:** the two tiers' edge sets are **DISJOINT**.
    Union = 41,224 = 19,308 + 21,916 exactly, **overlap 0**. The deep-3
    and the 30 shallow rules touch entirely different (source, target)
    class pairs — they are not two views of one relation.
  - Cost of the misread: ~14 min of local compute and one wrong caveat in
    the expanded entry. **Lesson: before treating a `--skip-rules` /
    `--only` exclusion as a coverage gap, check whether the excluded work
    already has a committed artifact.** `git log -- <artifact>` answers it
    in one command.

## lifted-873 loop-swap control (n=6, w4-bearing 873 shell) — local, ~10 min + small patch
- spec: patch `run_apply_sym`'s hardcoded `record = 872 if n == 6 else 5906`
  into a parameter (`--record 873`), then:
  `python3 analysis/counting/loopswap_apply.py apply-sym -n 6 --record 873 --rules data/loopswap/rules_n6_a360.tsv --dirs data/lift873_n6 --out out/s49/item2/lswap873`
- product: does the loop-swap tier MOVE inside the w4-bearing 873 shell
  (448 classes materialized by s49's R-BND REV-w4 lift)? If it does,
  FWD-w4 drop-back (Δlen = −1) from a moved 873 is a candidate bridge to
  a DIFFERENT 872 class — the s49 lift-and-drop composite is an
  involution only because nothing moves at the top of the lift.
  NOTE: without the `--record` patch every 873 product is silently
  discarded as "longer" and the run reports a vacuous 0 edges.
- projected: dry-run-exact (s49): 33 directed rules, 22,020 conjugated
  instances, 896 walk-orientations, 740,455 replays ≈ **~10 min** at the
  measured n=6 replay rate.
- approved: YES (Andrew, 2026-07-31 — "run the first two on the Mac, the PC is in use")
- status: done (s50, 2026-07-31; 66 s wall, not ~10 min)
- result: **THE LOOP-SWAP TIER MOVES INSIDE THE 873 SHELL.** Dry-run-exact:
  740,455 replays projected = 740,455 executed (33 rules, 22,020 instances,
  896 walk-orientations); 739,803 replay-killed (99.91%), 652 surviving
  products, all length 873, **zero ≤872 products (no alarm)**. Every one of
  the 652 is another class of the 448-shell — **0 new shell classes, so the
  873 shell is CLOSED under the 33-rule n=6 loop-swap vocabulary** — and
  **0 self-edges**: 332 directed class pairs / 388 (src,tgt,rule) triples /
  166 undirected pairs over 214 of the 448 classes, 86 components, largest
  14, from 15 of the 33 rules. Contrast with lift-and-drop's 824/824
  self-edges: the shell is a genuine intermediate. Artifacts:
  `out/s50/lswap873/` (214 product files + provenance),
  `out/s50/lswap873_shell_edges_n6.tsv`, `out/s50/lift873_n6_canon_index.tsv`.
  Note: the instrument's inline gate indexes only ≤-record classes, so at
  --record 873 in-shell rediscoveries land in the NOVEL bucket and the
  self/edge/new split is recovered by post-processing the provenance TSV
  against a canon index of the 448.
  **STEP 5 composite** (`rbnd_w4.py 6 data/lift873_n6`, ~40 s): 816 FWD-w4
  survivors, all 872, 0 NOVEL, 0 ≤871; drop map single-valued on 446/448 →
  219 distinct 872 landings. All 332 lift→move→drop rows land on a
  DIFFERENT 872: 230 ordered / 115 undirected 872↔872 bridges over 118
  classes. 66 were already edges of the committed 3-rule s44 n=6 graph;
  a targeted direct control (the 14 responsible rules over the 118 involved
  872 classes, 44,257 replays, 5 s — `out/s50/ctl872_out/`) re-found the
  other **49/49 directly at 872**. So the composite adds ZERO connectivity
  at n=6 as well: lift→move→drop = move.

## lifted-5907 loop-swap sweep (n=7, first w4-bearing 5907 shell) — local sharded, ~49 min (extrapolated; dry-run first)
- spec: same `--record` patch, then
  `python3 analysis/counting/loopswap_apply.py apply-sym -n 7 --record 5907 --rules <862 tables + rules_n7_s48_covertwin.tsv> --dirs data/lift5907_n7 --out out/s49/item2/lswap5907`
  — 12 shards at ≤12k rule-entries each (mandatory), `--dry-run` first.
- product: the only route the project has into w4-bearing n=7 structure
  (232 classes in six previously unoccupied d4=1 allocations). A
  loop-swap move inside the 5907/w4 shell followed by FWD-w4 (Δlen = −1)
  lands back at 5906 on a possibly different class — exactly the
  composite-chain shape the blind-spot front needs, and the only known
  move family that leaves the (842,19)–(843,18)–(844,17) pocket's
  length band at all.
- projected: EXTRAPOLATED, not measured — s48's marginal sweep was 4
  sources → 4,374 replays (~1,094/source); 232 sources ≈ 254,000
  replays ≈ **~49 min** at the measured n=7 replay rate. Over the
  30-min bar. Run the sharded `--dry-run` first to replace this estimate.
- approved: YES (Andrew, 2026-07-31 — "run the first two on the Mac, the PC is in use")
- status: done (s50, 2026-07-31; dry 19 min + live 15.5 min wall, 12 shards, J=4)
- result: **THE LOOP-SWAP TIER MOVES INSIDE THE 5907 SHELL TOO — AND THE
  DROP-BACK COMPOSITE BUYS NOTHING.** Dry-run sizing MEASURED (01:24:36→
  01:43:38): 284,080 replays over 4,352,040 conjugated instances / 464
  walk-orientations (+12% on the 254,000 extrapolation — projection stood,
  no re-approval needed). Live (01:45:01→02:00:34, worker pool J=4)
  **284,080 replays — dry-run-exact, shard by shard**; 274,580 replay-killed
  (96.66%), 9,500 products, **all length 5907, zero ≤5906 (no alarm)**.
  All 9,500 are among the 232 — **0 new shell classes (the 5907 shell is
  CLOSED under the 864-rule vocabulary)** — and **0 self-edges**: 7,590
  directed class pairs / 8,156 (src,tgt,rule) triples / 3,795 undirected
  over 220 of 232 classes, 13 components, largest 144, from 517 of the 864
  rules. Vocabulary = out/s50/rules_n7_union864.tsv (s48's vetted 862 +
  the 2 covertwin rules; rules_n7_rbnd.tsv excluded).
  **STEP 5 composite** (`rbnd_w4.py 7 data/lift5907_n7`): 289 FWD-w4
  survivors, all 5906, 0 NOVEL, 0 ≤5905; drop map single-valued on 220/232
  → 128 distinct 5906 landings. Composite over the 7,512 shell pairs whose
  both ends drop: 7,462 land on a DIFFERENT 5906 (50 land on the same),
  giving **3,328 ordered / 1,664 undirected 5906↔5906 bridges over 118
  classes — and ALL 1,664 are ALREADY edges of the known n=7 natural-move
  graph (0 new), with the 12-class blind spot untouched.** Same verdict at
  n=6 after a targeted control: 115/115 composite bridges are direct-tier
  edges of the same rules (49 looked "new" only against the committed
  3-rule s44 graph; a 14-rule direct sweep over the 118 involved 872s
  re-found 49/49). **Conclusion: the REV-w4 lift is a conjugation of the
  loop-swap tier, not an escape from it — lift→move→drop = move.**
  Artifacts: `out/s50/live7/` (12 shard dirs), `out/s50/lswap5907_shell_edges_n7.tsv`,
  `out/s50/drop5907/`, `out/s50/lswap5907_composite_5906_bridges.tsv`,
  `out/s50/composite_5906_bridges_undirected.tsv`, `out/s50/lift5907_n7_canon_index.tsv`.

## fused-pair UNTARGETED sweep on the blind spot (s49 item1) — ~33 h single-core / ~4.2 h 8-way / ~1.4 h farm
- spec: `python3 analysis/counting/s49/fuse.py untargeted --shard <i>/24` (mode
  to be added to the committed instrument: for each edit-preconditioned r1
  instance on a blind class-orientation, rescan the 4,354,560-instance table
  against the intermediate F', apply each surviving r2, replay ONCE, canon-gate
  inline; shard = one (blind class, orientation) per shard, 24 shards).
  Rebuild indexes first: `python3 analysis/counting/s49/fuse.py index` (~45 s).
- product: the ONE remaining live idea in the loop-swap tier — a fused pair
  escaping a blind class to a class OUTSIDE the 198 (targeted fusion into the
  198 is already closed exactly, s49: 0/9,456 at depth 1, 0/4,249,684 at
  depth 2). Otherwise the closure negative "the 12-class blind spot is closed
  under all ~4.8M fused pairs of the 864-rule vocabulary".
- projected: all measured (s49, analysis/counting/s49/sizing_untargeted.py):
  10,786 intermediates; precondition rescan 7.5 s each → 22.5 h; mean 448
  preconditioned r2 instances per intermediate → 4.83M fused pairs; replay
  8 ms → 10.7 h. TOTAL ~33 h single-core; 8-way Mac ~4.2 h wall; 24-way farm
  ~1.4 h. RSS ~250 MB/shard (measured). Optional 3× cut: prefilter on the
  tightness identity |flat| + #doors = 861 before replay.
- approved: **YES (Andrew, 2026-07-31), farm mode chosen** — second in the
  execution-order block.
- status: **done** — farm run `u1`, 24 shards, 2026-07-31 08:37:14 →
  08:44:38, **7.4 min wall**, 24 ok / 0 failed / 0 stalled, no alarm.
  Artifacts fetched to `out/s52/untargeted_farm/u1/` (24 shard dirs, 72
  TSVs, 0 product .txt).
  *(This entry was briefly marked BLOCKED by the operator on the grounds
  below; Andrew then BUILT both missing pieces — the `untargeted` mode in
  `fuse.py` and a full Python farm harness, `analysis/farm/untargeted_*`.
  The blockers are historical, kept for the record:*
  1. *the mode did not exist in `fuse.py` (now at line 650);*
  2. *the farm had no Python path — no interpreter, no repo mirror, no
     supervisor. The new harness supplies all three.)*
- result: **the 12-class blind spot is CLOSED under the untargeted
  fused-pair tier — and the closure is total, not marginal.** Aggregated
  from the 24 shard `stats.tsv` (10,794 rows, one per intermediate):
  ```
  r2_instances    4,713,880     replays        4,713,880
  replay_killed   4,702,938     (99.768%)
  self_edges         10,942     rediscoveries          0
  longer                  0     escapes                0
  ```
  - **Every fused pair was replayed** — `replays == r2_instances`, so
    nothing was sampled away or lost to a budget cap.
  - **Every survivor is a self-map.** All 10,942 replays that survived
    landed back on their OWN source class: zero reached even a different
    *known* class, let alone escaped the shell. The tier does not merely
    fail to escape, it fails to move at all.
  - Sizing check: 4.71M fused pairs vs the s49 projection of 4.83M — 2.4%
    under, so `sizing_untargeted.py` was sound.
  - **The optional prefilter is worthless here:** `prefilter_pass ==
    r2_instances` exactly (4,713,880 of 4,713,880), so the tightness
    identity `|flat| + #doors = 861` rejects NOTHING at this stage. The
    projected "optional 3× cut" does not exist — do not budget for it.
  - Wall-clock note for future Python farm entries: the as-built harness
    did in **7.4 min** what this entry projected at 1.4 h farm / 4.2 h
    8-way / 33 h single-core. Projections made before the harness existed
    should be re-derived, not trusted.
  - Per HANDOFF-S51 this was the ONE remaining live idea in the loop-swap
    tier for the blind spot. It is now spent; the blind spot survives
    single rules, sequential chains, fused pairs (targeted AND
    untargeted), and the full sumset.
- historical blockers (resolved by Andrew's build, kept for the record):
  1. **The instrument does not exist yet.** `analysis/counting/s49/fuse.py`
     dispatches exactly `index` / `depth1` / `depth2`; the string
     "untargeted" appears 0 times in the file. This entry's own spec says
     the mode is "to be added to the committed instrument" — so this is a
     BUILD task first, and it belongs to the research agent (s51 lists the
     untargeted fused sweep as its front), not to an operator launch.
  2. **The farm has no Python harness.** `~1.4 h on 24-way` is a
     compute-time arithmetic from `sizing_untargeted.py`, not evidence of a
     runnable path: the existing farm harness ships a cross-compiled
     `superperm.exe` plus PowerShell supervisors and knows nothing about
     Python instruments, corpora, or shard dirs. Farm mode needs that
     harness built (ship Python + the s49 caches + a supervisor/ledger),
     which is itself a chunk of work.
  Recommended: build the mode, run the 24-shard split, and only then decide
  farm-vs-8-way — an 8-way Mac run at ~4.2 h needs no new farm plumbing at
  all and may beat farm-with-setup on wall clock.
- s51 re-scope (JOURNAL s51 §5, HANDOFF-S51 menu item 3): the sweep is
  PROVABLY VACUOUS for `up-1b8244ba04bb` within the 198 (min entry-diff 536 >
  vocabulary max 534; min door-edit 34 > 24 fused; 536 ≡ 2 mod 6) — the
  remaining value is escape OUTSIDE the shell, and the canon gate must now
  target the **220-class project shell** (supplementary indexes
  `novel5906d_canon_index.tsv` + `kristan5906_web_canon_index.tsv`, already
  wired into m3_check). The approval above predates both this re-scope and
  the farm-mode blocker; the re-scoped run (8-way Mac ~4.2 h vs
  farm-with-setup) needs Andrew's re-approval before launch.
- status update (2026-07-31, live session s52): **BUILD CLAIMED by the live
  research session** — the `untargeted` mode is being implemented here (Opus
  subagent, canon gate vs the 220, controls + dry-run sizing before any
  launch). Sweep runner: do NOT write a competing implementation.
- **MODE BUILT + VERIFIED (2026-07-31 s52).** `fuse.py untargeted --shard
  i/24 [--out DIR] [--dry-run] [--limit N] [--prefilter] [--verify-scan]
  [--no-gate-intermediate]` + `--control` mode. Canon gate = 220 (m3_check
  index + all supplementary). Positive control PASS (strict depth-2 chain
  lswap-25804d565b10 →1d66c35e4a35→ →0d491f159886→ up-e94d2b57a7d4, both
  steps matching documented edge rule ids; orchestrator re-ran
  independently, FOUND incl. --prefilter). Dry-run 24/24 shards: 10,794
  intermediates (+8 vs sizing: the door-exit-reuse post-removal
  convention fix), 4,713,880 fused pairs (−2.4%: sizing's 448 mean was an
  8-sample estimate; true 436.7); orchestrator re-ran shard 2
  independently, identical. **RE-SIZED: the 33 h projection is dead —
  early-exit column narrowing cuts the rescan 7.5 s → 0.11 s (verified
  identical vs all-columns reference 12/12) and true replay cost is
  0.73 ms (99.8% die early). Measured: ~81 min single-core, ~28–31 min
  8-way Mac, RSS 184 MB/shard.** Notes: `--prefilter` is PROVABLY VACUOUS
  for this vocabulary (all 864 rules net-zero in |entries|+|doors| — the
  spec's "3× cut" does not exist; flag kept for non-net-zero tiers).
  Intermediate canon-gating ON by default (closes the 4th orientation
  combo via the s46/s50 shell-closure sweeps; MIDESCAPE bannered).
  Latent s49 wart (does NOT weaken published negatives — the s50 sumset
  is precondition-free): depth1/depth2/sizing test `doors[e] == -1`
  pre-removal, so 32 door-exit-reuse rules never fired as r1 there;
  committed depth-2 counts undercount by the same +8. Andrew to decide:
  annotate or re-run.
- **Andrew re-confirmed FARM mode (2026-07-31): "build it for the PC farm."**
  A second agent is building the farm Python harness (ship script +
  24-way PowerShell supervisor + ledger/STATUS/stall detection + status/
  abort/fetch scripts, per OPERATIONS.md conventions).
- **LAUNCH OWNERSHIP: Andrew's queue manager launches this — NOT the
  research session, NOT its subagents.**
- **STATUS: READY (2026-07-31 s52). Farm package shipped and verified
  end-to-end; farm idle; nothing launched.** Harness:
  `analysis/farm/untargeted_{ship.sh,env.ps1,run.ps1,super.ps1,super.bat,
  status.ps1,abort.ps1,fetch.sh,stub.py}`. Package at
  `F:\superpermFarm\untargeted\` (repo mirror + venv `pyenv\Scripts\
  upyw.exe` — renamed interpreter so abort can NEVER kill the user's
  transcription python; identity = pid+name+start-time; recycled-pid
  refusal tested live). 308 files / 160 MB, sha256 manifest both ends.
  Farm-side proof: caches load byte-identical (index rebuild matches Mac,
  CRLF-only diff in ruleids.txt, functionally invisible), gate = 220,
  depth1 control matches committed s49, `--shard 0/24 --dry-run` = 458
  r1 / 198,631 r2 (exact Mac numbers), `--limit 5` real run clean.
  Supervisor: 24-shard pool + backfill, captured stdout (detach.exe →
  upyw -u, no cmd redirect), append-only ledger.csv + TABLE.csv snapshot,
  5-min stall alarm (tested against a live-but-frozen shard), exit codes
  real (.Handle cached at launch), escape detection off tagged STATUS
  rows (NOT log text — `ESCAPES 0` in normal summaries is a landmine for
  text-matching monitors). Expected full run: ~81 min single-core total ⇒
  minutes wall at 24-way (largest shard ~6 min solo on M1); ~184 MB/shard
  (~4.4 GB, box has 38 GB free); BELOW_NORMAL priority, 4 cores left for
  transcription. Queue-manager commands:
  `ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\untargeted\untargeted_run.ps1 -Tag u1"`
  (launch; `-DryRun`/`-Limit N`/`-Workers K` available),
  `...untargeted_status.ps1` (status; `-Tag`/`-Full`),
  `...untargeted_abort.ps1` (abort),
  `bash analysis/farm/untargeted_fetch.sh u1` (fetch →
  out/s52/untargeted_farm/u1/). On completion: any ESCAPE/MIDESCAPE
  string still owes `m3_check.py -n 7` + `validate -n 7 --complete`.
- **Supervisor defects caught BY the 24-shard smoke tests (s52, fixed).**
  Recorded because both are generic monitor traps, not one-off typos, and
  because the READY block above was written against the pre-fix supervisor:
  1. **Healthy shards raised ALARM.txt.** The alarm scan matched the
     instrument's own normal per-shard summary line, so smoke3 bannered all
     24 good shards. A monitor that alarms on success is worse than none —
     a real ESCAPE would have been buried in 24 lines of noise. Escapes are
     now counted only off tagged STATUS rows; the log scan is reserved for
     hard errors (`Traceback`/`MemoryError`) and the instrument's own `!!`
     banner. This is the same landmine the block above names (`ESCAPES 0`
     matching a text monitor) — it was live in the shipped code.
  2. **The progress tally mixed units.** `$st.lines` counted every STATUS
     row, including each shard's terminal `DONE`, against a `declTotal` of
     intermediates only ⇒ 96/72; and a shard that had not yet written
     STATUS on the first tick stayed pinned to the evenly-split fallback
     forever ⇒ 96/519. Fixed by counting only progress-tagged rows and by
     holding the instrument's declared total in its own field. At 10,794
     intermediates the old form would have hit "100%" ~0.2% early with a
     correspondingly inflated rate and ETA.
  Final verification after both fixes (smoke6, 24 shards, `-Limit 3`):
  **24 DONE, 0 failed, rc=0, ESCAPES=0, no ALARM.txt, intermediates
  72/72 (100%)**; `untargeted_env.ps1` re-run ENV OK, 0 failures.
  `cargo test --release` 139 green. Farm left idle.
- result: —

## liberal sumset, FULL coverage (s49 item1) — ~84 min single-core / ~11 min 8-way
- spec: `python3 analysis/counting/s49/sumset.py run 0` (sharded 8-way by blind
  class; indexes from `fuse.py index`).
- product: extends the precondition-free, direction-symmetric negative
  "δ_req ∉ Δ+Δ" from the 1,200 nearest (blind, frame, target) triples to ALL
  9,456. Subsumes BOTH directions of strict fused composition (Δ = −Δ verified
  0/864), so a full 0 closes fused depth 2 for the blind spot completely, in
  both directions, with no precondition assumption.
- projected: 0.53 s/triple measured × 9,456 = 84 min single-core; 8-way ~11 min
  wall. RSS ~250 MB/shard.
- approved: YES (Andrew, 2026-07-31 — "run the full sum set too, just not the untargeted fuses sweep")
- status: done (s50, 2026-07-31; 4 shards × 3 blind classes, 35m48s wall on a loaded box)
- result: **0 hits / 9,456 triples (FULL coverage: 12 blind × 197 targets ×
  4 frames) — δ_req ∉ Δ+Δ everywhere.** Controls PASS (depth-1 200/200;
  NEW sumset 2-step-path control 12/12 — the s49-cited control was never
  committed as code; it exists now: `analysis/counting/s49/sumset_control.py`).
  All 1,200 s49 rows reproduced identically. **Fused depth-2 is CLOSED for
  the blind spot, both directions, precondition-free.** Min |EO_req| over all
  9,456 = 216 (nothing closer than the s49 nearest set — the isolation is
  structural). Product: `data/loopswap/blindspot_sumset_n7_full.tsv`;
  `sumset.py` gained S49_SOURCES/S49_TAG sharding.

## n=6 full-corpus PROMOTION hunt (w3→w4, Δlen = 0) — every product is an M3 event
- spec: `python3 analysis/counting/s51/demotion.py promote 6 data/upstream872 --shard i/8 --out out/s51/demotion/promfull_i` (i = 0..7, xargs -P pool),
  then union the `edges.tsv` shards and `m3_check.py` + `validate -n 6 --complete` every product.
- product: s51 proved all 866 w4 doors in the 415 known w4-bearing 872 classes
  have every demotion gate closed (three independent gates + brute-force-verified
  enumeration completeness), so NO known 872 can be a promotion product — any
  product of this sweep is a NOVEL 872 class by construction. The 419 w4-bearing
  + (141,7) carriers are already done (9,395 admissible completions, 100%
  replay-killed, 0 products); this entry is the remaining ~21,600 pure-w3 walks.
- projected: ~3.4 h single-core (measured 0.555 s/walk on a 200-walk (145,3)
  round-robin sample); ~26 min 8-way on the Mac (more with foreign compute).
  Deterministic; run-twice byte-agreement demonstrated on every s51 run.
- approved: **YES (Andrew, 2026-07-31)** — fourth in the execution-order
  block.
- status: **done** — farm run `p1`, 24 shards, 2026-07-31 09:01 → 09:20,
  **18.7 min wall**, 24 ok / 0 failed / 0 stalled. Run on the FARM, not the
  Mac (Andrew: "we have the farm for a reason"). Instrument pinned at
  `demotion.py` sha256 `15be935b5bed…` before shipping. Artifacts:
  `out/s52/untargeted_farm/p1/`. Driven through the s52 Python farm harness
  by a new adapter — `analysis/farm/promote_shim.py` (+ `promote_run.ps1`,
  `promote_ship.sh`, and an additive `Target` PARAM in
  `untargeted_super.ps1`). The shim supplies demotion.py's positional argv
  and the STATUS heartbeat; it does not touch results.
- result: **the w3→w4 promotion trade is REPLAY-DEAD across the entire n=6
  corpus — 4,716,847 admissible completions, 100 % killed, 0 products.**
  Aggregated from all 24 shard logs:
  ```
  carrier-orientations         44,124      roundtrip-ok        44,124  (100%)
  admissible-completions    4,716,847      branch-P         4,716,847
  replay-killed             4,716,847      (100%)
    kill:w2 target          4,293,514      (91.0%)
    kill:entry revisited      423,333      ( 9.0%)
  novel-candidate classes           0      product files            0
  ```
  - **Coverage is exact, not sampled:** per-shard stats sum to 22,062
    walks / 44,124 orientations = the whole archive, with shard indices
    summing to 276 (= 0+…+23, so all 24 distinct — no gap, no
    double-count).
  - **The zero is not an instrument failure:** `roundtrip-ok` is
    44,124/44,124 — every source walk was re-derived byte-exactly before
    any edit was attempted. A broken instrument fails there first.
  - **Only two kill mechanisms exist**, and they partition the space:
    91 % die because the promoted door's target is w2-entered, 9 %
    because the edit revisits an entry. Nothing else ever fires.
  - Confirms the s51 prediction (HANDOFF-S51: the w4 demotion trade is
    "structurally infeasible at n=6 record level"). The promotion
    direction was a **can't-lose M3 hunt** — every product would have been
    a novel 872 by construction — and it is empty. Can't-lose, and won
    nothing.
  - **TRAP (operator error — cost a false alarm; fix below).** All 24
    HEALTHY shards raised `ALARM.txt`. Cause: `demotion.py`'s normal
    end-of-run summary prints the literal `novel-candidate classes: 0`,
    and the supervisor's stdout scan matches `\bNOVEL\b`. This is the SAME
    trap `untargeted_super.ps1` already documents for fuse.py's
    "ESCAPES 0" line — that one was fixed with `ESCAPES\s+[1-9]`; the
    NOVEL branch needed the same treatment and did not get it.
    **Before driving any NEW instrument through this supervisor, diff its
    terminal summary against the alarm regex.**
  - Runtime note: 18.7 min vs my ~9 min pre-launch estimate (sized from a
    2-walk Mac sample at 0.5 s/walk; farm cores are slower per-core and 24
    shards contend for memory bandwidth). Queue's single-core figure was
    ~3.4 h, so the farm still bought ~11×.
