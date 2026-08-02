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

## grayzel lake build — a(6)=872 Lean proof, compile + axiom audit (P0, s55)
- spec: (needs elan; toolchain auto-installs `leanprover/lean4:v4.30.0` from
  `lean-toolchain`)
  ```
  git clone https://github.com/BGray-wrl/superperm6 <workdir>/superperm6
  cd <workdir>/superperm6 && git checkout d8a932d8f61d80b0bcfc737bd0e235a8300449c4
  cd formal-verification
  lake exe cache get                     # mathlib cache, several GB download
  lake build 2>&1 | tee ../../lake-build.log
  lake env lean AxiomAudit.lean                    2>&1 | tee ../../axiom-audit-main.log
  lake env lean Section57Closure/AxiomAudit.lean   2>&1 | tee ../../axiom-audit-s57.log
  ```
  Capture ALL THREE logs verbatim — the two AxiomAudit outputs are the
  deliverable (expected axiom set: `propext, Classical.choice, Quot.sound,
  Lean.ofReduceBool` + native-eval axioms; any `sorryAx` = proof invalid),
  not just the build exit code.
- product: decides whether Grayzel's `main_theorem : IsMinimumLength 872`
  compiles — i.e. (1) the 20,300 lines type-check, (2) all 156
  `native_decide` goals evaluate true, (3) the elaborated terms are
  sorryAx-free. Statement faithfulness already verified statically (s55:
  FAITHFUL; witness independently re-verified in Python). If this build
  passes, a(6)=872 is as good as trust in the Lean compiler → 871 is dead
  and n=6 becomes calibration ground truth (NOVELTY-DESIGN P0).
- projected: hours-scale, dominated by mathlib cache download + ~8,500 build
  jobs with `maxHeartbeats 4000000` files and 156 native evaluations
  (`maxHeartbeats 0` on the witness theorem). No parallelism tuning needed
  (`lake` uses all cores). Disk: ~10 GB. Mac preferred (PC has no
  toolchain).
- heartbeat: `lake build` streams per-job progress to lake-build.log; STATUS
  = `tail -1 lake-build.log` on the usual cadence; stall = log mtime
  unchanged 30 min (native_decide jobs can legitimately run long — check
  CPU% before declaring a hang).
- abort: `pkill -f "lake build"` (child `lean` processes die with it) — on
  the PC, via the run's own abort script (see result for the as-built path).
- approved: **YES (Andrew, 2026-07-31 — "build the tool chain on the pc and
  run the sweeps on the pc, do not run anything on the mac")**. RETARGETED
  from Mac to the farm PC: the Mac is running the live s56 P1a chain-solving
  campaign at ~full CPU (load avg ~7-8/8), so both this and the fl1577 study
  move to the (idle, 28-core) farm PC. Toolchain (elan/lake/lean) does not
  exist there yet and must be built as part of this launch.
- status: **done** — farm PC, tag `g3`, 2026-07-31 13:14:52 → 15:18:26 local
  (**123.6 min**, of which `lake build` itself was 7,143 s / 119 min).
  Toolchain: elan 4.2.3, Lean 4.30.0, Lake 5.0.0, installed fresh on the PC
  this session. Repo pinned at `d8a932d` as specced. Verified independently
  (orchestrator, not just the agent's own report): `grep -i sorry` over all
  three fetched logs = 0 hits; `lake-build.log` tail confirms
  `Build completed successfully (8518 jobs)` with `[8517/8518]` as the last
  numbered job; `STATUS.txt`/`ALARM.txt` both fetched and consistent with the
  agent's narrative (see below). Logs: `out/grayzel_lake_build/{lake-build.log,
  axiom-audit-main.log,axiom-audit-s57.log,STATUS.txt,ALARM.txt,ledger.csv,
  SPEC.txt}` on the Mac (gitignored scratch); farm side
  `D:\superpermFarm\grayzel\` (repo + toolchain) and
  `D:\superpermFarm\grayzel\runs\g3\logs\` (this run's logs).
- result: **THE PROOF COMPILES CLEAN. `main_theorem : IsMinimumLength 872`
  type-checks with ZERO `sorryAx`, ZERO errors, 57 cosmetic-only warnings
  (unused mathlib linter nits).** `lake exe cache get` pulled mathlib
  8,459/8,459 files from cache; all 44 of the project's own modules (27
  `Superperm6/` + 13 `Section57Closure/`) were elaborated fresh in this run,
  not cached. Every one of the 38 audited declarations (20 in
  `AxiomAudit.lean`, 18 in `Section57Closure/AxiomAudit.lean`) depends on
  exactly `propext, Classical.choice, Quot.sound` plus its own
  `native_decide` evaluation axioms — including **`main_theorem` itself**
  (3 core + 99 native axioms) and both halves of the bound
  (`no_hamiltonian_route_of_weight_at_most_865` /
  `lower_bound_from_boundary`, 97 native axioms each). Static scan of all 44
  project files: 0 `sorry`/`admit`/`axiom`/`unsafe`/`@[extern]`/
  `@[implemented_by]`/`debug.skipKernelTC`; the only non-default `set_option`s
  are heartbeat/recursion-depth/profiler knobs, with `maxHeartbeats 0` used
  exactly once, on `witness_isSuperpermutation` — reproduces the s55 static
  audit now with a real compile behind it.
  - **One correction to the s55 expected-axiom-set text.** `Lean.ofReduceBool`
    does not appear anywhere — Lean 4.30's `native_decide` no longer routes
    through one global axiom; it emits a separately-named axiom per
    declaration (e.g. `Superperm6.witness_isSuperpermutation._native
    .native_decide.ax_1_1`, 574 such axioms total in the main audit, 170 in
    s57). Same trust surface in kind (compiler-trusted native evaluation,
    not kernel-trusted), itemized differently than s55 anticipated.
  - Witness cross-check: `Witness.lean` embeds `data/superperm6_872_clean.txt`
    (sha `c3edd395…0ff6dff2`) via `include_str`; the agent independently
    re-verified it on the Mac (872 chars, all 720 permutations of `123456`
    present) and confirmed `Witness.olean`/`Main.olean` were both freshly
    built this run — `main_theorem` really does depend on the file we think
    it does, not a stale cached artifact.
  - **False-positive stall, for the record (matches the OPERATIONS.md
    liveness lesson):** `ALARM.txt` fired at 45 min of flat log size during
    the `lake build` stage; CPU on the `lean.exe` child was pinned at 100%
    the whole time (one `native_decide` module ran silent for ~55 min,
    accumulating 3,111 CPU-seconds). Not a hang — `native_decide` at
    `maxHeartbeats 0` can legitimately go quiet for a long time. Recommend
    60–75 min stall threshold if this class of job is re-run.
  - **Farm/Windows-toolchain traps worth keeping** (new, this session):
    `F:\` is exFAT (no hard links, no ownership records) — elan and git both
    misbehave there; toolchain work must go on an NTFS volume (`D:\` used
    here, 993→239 GB free after). `cmd /c "exe" args > "log" 2>&1` silently
    strips the outer quotes and the redirect never fires — don't quote when
    no farm path has spaces. `$ErrorActionPreference='Stop'` + any native
    command writing to stderr (git always does) throws `NativeCommandError`
    even at rc=0 — run native calls under `Continue`, check `$LASTEXITCODE`.
    `Get-CimInstance` HANGS (not just denies) for the farm account — use
    `[System.IO.DriveInfo]` / `$env:NUMBER_OF_PROCESSORS` instead. Lake
    5.0.0 has no `-j`/`--jobs` flag at all.
  - **Bottom line: a(6)=872's minimality now has a machine-checked, 0-sorry
    Lean proof, independently built and audited on our own hardware — not
    just a hand-verified statement.** Combined with Gheorghe's independent
    209-cell preliminary proof (s55), this is the strongest evidence yet
    that 871 is dead. Trust surface is exactly what s55 said: compiler
    trust in Lean's native evaluator for every finite fact, both bounds
    included — a different kind of trust than kernel-checked arithmetic,
    but a real, reproducible compile, not an announced-and-unexamined claim.
    NOVELTY-DESIGN P0 update and JOURNAL entry to follow.

## fl1577 recipe study — P4 gate (P5a instrument, s55)
- spec: harness `out/s55/fl1577/run_fl1577.sh` (LKH-3.0.13 at
  `out/s55/fl1577/bin/LKH`, instance sha256 `cb473802…`, optimum 22249).
  5 recipes × 10 seeds at 600 s/cell, 8-way parallel:
  ```
  cd out/s55/fl1577
  for cfg in cfg/*.par; do for s in 1 2 3 4 5 6 7 8 9 10; do
    echo "$(basename $cfg .par) $cfg 600 $s runs_study"; done; done \
    | xargs -P 8 -n 5 ./run_fl1577.sh
  ```
  Recipe set (finalize cfg/ fragments at launch): `default` (control),
  `lkh3_special` (known stall-at-+5 control), `gaincrit_patch` (control —
  s55 smoke showed it 40-60x WORSE than default; re-run under the fixed
  MAX_TRIALS harness), + two escape-oriented candidates chosen from the
  LKH-3 parameter surface (kick/perturbation- or population-based; NOT
  gain-criterion-off variants).
- product: which (if any) recipe cracks fl1577 (hits 22249) — the P4 gate:
  recipes that can't crack the proxy don't get n=7 CPU. Success column =
  `cracked` in `runs_study/ledger.tsv`; headline = `cracked_total > 0`.
- projected: 50 cells x ~810 s actual (LKH overshoots the 600 s budget
  ~1.35x, measured s55) / 8-way = ~85 min hard-bounded on the Mac
  (single-threaded per cell; binary is Mac-built — farm would need a
  Windows LKH rebuild, not worth it at this scale).
- heartbeat: `runs_study/STATUS.txt` rewritten after every cell (stage /
  last cell / done N / cracked_total / ts) + append-only
  `runs_study/ledger.tsv`; stall = ledger row count unchanged for 20 min.
  ALARM-REGEX CHECK (s52b trap): harness emits no NOVEL/ESCAPES strings;
  ledger `cracked` column is 0/1 — do not alarm on `cracked 0` rows.
- abort: `pkill -f 'out/s55/fl1577/bin/LKH'` (matches only this study's
  binary path) — on the PC, via the run's own abort script (see result).
- approved: **YES (Andrew, 2026-07-31 — same instruction as the grayzel
  entry above)**. RETARGETED from Mac to the farm PC (idle, 28 cores) —
  the existing `out/s55/fl1577/bin/LKH` binary is Mac-built (arm64
  Mach-O) and does not run on Windows, so the PC needs its own LKH-3.0.13
  build as part of this launch; the 2 missing escape-oriented recipes
  (kick/perturbation- or population-based) also get finalized at launch
  time per the original spec.
- status: **done** — farm PC. Toolchain: LKH-3.0.13 built natively from
  source (winlibs mingw-w64 gcc 16.1.0, no admin/winget needed) at
  `D:\superpermFarm\fl1577\bin\LKH.exe`, 6 s build, sha256 `a3e378ab…`.
  Source fetched straight from `webhotel4.ruc.dk` (up, unlike the Heidelberg
  TSPLIB mirror JOURNAL s55 flagged as down). Study `s1`: 50 cells, 25
  workers of 28 cores, BELOW_NORMAL, **20.0 min wall**. Ancillary control
  `c1` (`restartctl`, 10 cells): 10 min. Verified independently
  (orchestrator): `ledger_all.tsv`'s per-recipe cracked counts match the
  agent's table exactly; **I recomputed tour length from raw fl1577.tsp
  coordinates myself** for 4 sampled `.tour` files (TSPLIB EUC_2D nint
  rounding) — `default_s3`/`default_s10`/`popga_s4` all independently
  recompute to exactly 22249, `lkh3_special_s1` to exactly 22254 (the known
  stall value) — the crack is real, not a logging artifact. Recipe files at
  `data/../out/s55/fl1577/cfg/{kickburst,popga,restartctl}.par` (committed
  location: `out/s55/fl1577/cfg/`, gitignored scratch but kept for re-runs).
  Full artifacts: `out/fl1577_pc_study/` (ledgers, 50 `lkh.log`+`row.tsv`
  per cell, 4 sampled `.tour` files, harness scripts, build log).
- result: **fl1577 IS CRACKABLE — comprehensively — which inverts the P4
  gate's premise.** `cracked_total = 24/50` (cracked = best == 22249):

  | recipe | cracked/10 | min gap | median gap | note |
  |---|---|---|---|---|
  | `default` (stock LKH, control) | **4** | 0 | 12 | — |
  | `lkh3_special` (published-stall control) | **4** | 0 | 5 | reproduces the +5 stall on the other 6 |
  | `gaincrit_patch` (control, demoted s55) | **0** | 17 | 38 | confirms s55: much worse than stock |
  | `kickburst` (new: KICKS=3, KICK_TYPE=6) | **6** | 0 | 0 | perturbation escape |
  | `popga` (new: POPULATION_SIZE=12 + finite per-run budget) | **10** | 0 | 0 | recombination escape, fastest (median 11.9s to optimum) |
  | `restartctl` (ancillary: popga minus population) | **5** | 0 | 0 | isolates restart-alone from recombination |

  - **The headline is not "which recipe wins" — it's that the CONTROL
    passes.** Stock LKH cracks fl1577 4/10 at a 600s single-core budget.
    The published "LKH 0/10 at 22254" result (Ochoa–Veerapen 2018,
    verified against primaries at s55) is a **budget artifact**: the
    published runs used `MAX_TRIALS = DIMENSION` (short, per-run-capped),
    not a sustained single 600s chained-LK run. So "cracks fl1577" is now
    a very weak P4 filter — failing it still disqualifies a recipe
    (`gaincrit_patch` did), but passing it says little. **P4 recipes
    should be re-gated on time-to-optimum or a harder (shorter) budget**,
    where the recipes visibly separate (popga median 11.9s vs default's
    30.5s vs lkh3_special's 201.4s).
  - **popga's 10/10 needed the ancillary control to interpret.** popga's
    finite per-run budget (`MAX_TRIALS=1577 TIME_LIMIT=15`) is itself a
    restart mechanism (~40 runs/cell) independent of recombination —
    `restartctl` (same budget, no population) isolates that: **5/10**.
    So **ERX recombination roughly doubles the crack rate over bare
    restarts (5/10 → 10/10)**, and drives by far the fastest
    time-to-optimum. The population/recombination mechanism is carrying
    real, measurable weight — not just "more restarts help."
  - **kickburst (6/10) is a genuine second escape mechanism**, distinct
    from restarting (it makes ONE long run, no `MAX_TRIALS` cap) — a
    strong-kick (k=6 double-bridge x3/trial) chained-LK run beats both
    stock LKH and the published stall recipe.
  - Design notes worth keeping: both new recipes are individually
    documented inline in their `.par` files with the mechanism, the
    LKH-3 source lines that gate it (`ChooseInitialTour.c:38` for kicks,
    `LKHmain.c:154` for `STOP_AT_OPTIMUM`'s population-only early exit),
    and — for popga — an explicit trap noted and dodged (without a finite
    per-run budget the genetic layer never engages and `POPULATION_SIZE`
    silently no-ops).
  - **Toolchain/measurement traps for future PC LKH work:** the Windows
    build's `TIME_LIMIT`/`TOTAL_TIME_LIMIT` measure true wall time
    (MSVCRT `clock()`), NOT the ~1.35× overshoot the Mac harness measured
    (macOS/Linux `getrusage` excludes preprocessing) — **do not apply the
    1.35× factor to PC sweep sizing.** Overriding LKH's `CFLAGS` on the
    make line drops `-DTWO_LEVEL_TREE` silently (wrong tree type) unless
    re-added explicitly. PowerShell `*>` redirection writes UTF-16LE —
    Mac-side grep/Python silently found zero matches until logs were
    converted to UTF-8 (indistinguishable from "pattern absent"). The
    generic `Trials = (\d+)` regex substring-matches LKH's echoed
    `MAX_TRIALS`/`POPMUSIC_TRIALS` parameter lines — use LKH's own
    `Trials.max` summary line instead (this also explains why the
    original Mac s55 ledger showed `trials=0`: those logs never echoed
    parameters). `secs` is not comparable across recipes — only `popga`
    (and anything else gating `STOP_AT_OPTIMUM` on population) exits
    early on cracking; every other recipe burns the full 600s regardless.
  - **Next step this opens, not yet run:** re-gate the two winning
    recipes (popga, kickburst) at a much shorter per-cell budget (e.g.
    60-90s) where stock LKH and the controls are expected to fail more
    often, to get a real discriminating signal before spending n=7 CPU —
    Andrew's call on whether/when to queue that.

## pairwise cut store, chain #0 (s57 REPORT §8.3 — the next sound tool)
- spec: adapt `out/s57/proposer/propose.py`'s capped refutation probe to
  enumerate row PAIRS on the pruned #0 instance
  (`out/s57/proposer/inst_lr_farm0.txt`, 2346 rows): for each pair (i,j),
  assert both rows, propagate/refute at the s57 cap (10⁶ nodes ≈ 0.012 s);
  a refuted pair is a reusable sound no-good ("not both i and j in any
  cover"). Shard 24-way by i on the farm (Python sweeps run on the farm —
  Andrew, 2026-07-31); harness build step required first (mirror the
  `fl*`/`ta*` house style in `analysis/farm/`). REFUTATION LANE ONLY
  (ε=0) — no-goods must be unconditional.
- product: a committed no-good store for #0 (and, if cheap, #24) that any
  later witness/refutation run can load; the sound row-shrink route
  toward the ≲1500-row target (HANDOFF-S57 menu item 2). Singleton cuts
  saturated at s57 (4 forced rows, −12%); pairs are the unexplored layer.
- projected: ~2.7M pairs × 0.012 s ≈ **9 core-hours** on #0 (s57 REPORT
  §8.3 figure, from measured singleton probe rate); ~24 min wall on 24
  farm cores + harness build. Round-robin probe first per house rule —
  pair probes may not price like singleton probes.
- approved: **YES — go-ahead given OUTSIDE this file and never recorded** (same
  gap as `ex1` and `n6a450r2tightprobe`; third occurrence). Probe `pcprobe1`
  and full run `pc1` both executed 2026-08-01 overnight while the entry read
  `approved: NO / status: pending`. Reconstructed by the sweep runner
  2026-08-01. **Record the approval when you give it.**
- status: **done** — farm run `pc1`, 24 shards, 2026-08-01 → 01:22:16,
  **184.4 min wall / 72.93 core-hours**, 24 ok / 0 failed, 0 errors, no ALARM.
  Preceded by round-robin probe `pcprobe1` (24 shards, 3.8 min). Verified
  independently 2026-08-01 (`out/s58/analysis_pc1/`).
  - Build note above is **WRONG on two counts, corrected here.** (a) It says to
    reuse `out/s60/nogood/confirm.py`/`cutlib.py` as the verification harness —
    **do not.** Those render via the `propose.py` RELAXATION, whose fingerprint
    is the relax sha `73dc4dd5…`, not this store's base sha `4f05c1b5…`; the
    assert fails outright, and semantically relaxation-UNSAT implies
    fixed-column-UNSAT but **not the reverse**, so following the note literally
    manufactures false soundness alarms on sound cuts. (b) The "re-confirm at
    ≥10× cap" clause was **already implemented inside the instrument** —
    `paircuts.py --reconfirm-mult` defaults to 10 — so the pass it demands ran
    inline on every cut, and there is no separate artifact to look for.
- result: **The store is SOUND — fully verified, not sampled — and it is also
  nearly worthless: its entire instance-reduction product is 54 row deletions
  that a 9.3-second local singleton pass reproduces exactly.**
  Ledger: 2,350 rows, 2,760,075 pairs (= C(2350,2) exactly), 101,513
  structural skips, 2,658,562 probed, **147,561 no-goods**, 2,511,001 UNKNOWN,
  0 errors, 0 duplicate cuts, single `base_sha` across all 24 shards.
  - **Soundness, established four ways.** (1) **All 147,561 cuts re-confirmed**
    in fresh processes at cap 2,000,000 = **1000× the probe cap** (100× the
    mandated 10×): 147,561/147,561 UNSAT, 0 failures, 0.43 core-hours local —
    population, not sample. (2) **Node counts are IDENTICAL** for all 147,561
    cuts between the Windows farm run and the macOS re-run — the stronger check,
    since verdict-matching alone would pass even if two engines disagreed about
    the tree. (3) The reduction is machine-checked on the real target: `kill[r]`
    is exactly the conflict set for all 2,350 rows, no stored cut is
    structurally conflicting, and forcing is exact — giving the theorem that
    exit 2 means "no cover contains both". (4) A **solver-free independent
    prover** (dead-column + unit propagation, ignoring dlx7g entirely) proves
    20,708 cuts with no search — and the 20,300 it closes at round 1 are
    **exactly** the 20,300 dlx7g exhausted in 1 node.
  - **Positive controls: 0 violations, three ways.** Rows {0,21,690,691} are
    unit-propagated into every cover of #0, and none of their 6 pairs appears in
    the store (a real control on an OPEN chain). Instrument-level on a
    known-cover chain: 323,536 probes, 11,008 cuts, **0 violations** vs all 131
    known covers. Oracle at scale: PASS, 0 failures, including 1,200 pairs drawn
    from real covers, 0 refuted.
  - **No jackpot, provably:** `probed = nogoods + unknown` exactly with
    `errors = 0`, so the SAT count is identically zero — every probe accounted
    for. Corroborated by 0 JACKPOT files, 0 ALARM, 0 stderr bytes, all rc=0.
  - **The usefulness verdict is blunt: it bought ~9 seconds of unique product.**
    Coverage is 5.35% of all pairs; **91.0% of pairs are UNKNOWN — nothing was
    learned about them.** Sound propagation to a fixpoint deletes **54 rows and
    nothing else** (fixpoint at round 2, **no cascade**): 2,350 → 2,296 alive,
    −2.30%, closing 6.4% of the gap to the ≲1500-row target. **Every one of the
    54 comes from a pair `(f,x)` with `f` one of the 4 already-forced rows —
    i.e. logically a SINGLETON refutation.** Running the singleton layer in the
    same fixed-column render: 2,350 probes, **the identical 54 rows**, 5.4 s
    wall / 30.9 core-seconds; to a fixpoint 9.3 s. **72.93 core-hours vs 9.3
    seconds for the same result — a ~28,000× cost ratio.**
  - **What IS genuinely new**, and it is untested: after the 54 dead rows are
    removed, 120,878 of the cuts (81.9%) reference a row the store itself proves
    is in no cover. The residual is **26,683 live cuts** over 2,296 rows = +23.2
    forbidden partners per row on top of 84.7 structural conflicts, a **+27%
    forward-checking pruning increase**. Unlike s60's 8-row cuts these DO fire
    (6× over s60's own 50%-hit-rate bar). Whether +27% converts into a DECIDED
    instance is completely untested.
  - **A bigger cap will not help — do not run one.** 4,000 random UNKNOWN pairs
    re-probed at 100× cap: **0 newly refuted, 0 SAT, 100% still UNKNOWN**, at 24×
    the cost. Rule-of-three 95% bound ⇒ ≤0.075% refutation rate ⇒ at most ~1,880
    further cuts from all 2.51M UNKNOWNs, for ~980 core-hours / 41 h wall on 24
    farm cores.
- **THE REUSABLE FINDING is not the store — it is the RENDER.** s57's claim that
  the singleton layer "saturated" is **render-relative**: it saturated in the
  `propose.py` relaxation, which forces a row by DELETING its child columns and
  thereby relaxes the first-visit ordering. `paircuts.py`'s fixed-column render
  holds columns fixed and deletes only conflicting rows, keeping the ordering
  constraint intact — strictly stronger, and at the same 2,000-node cap it
  refutes **54 more rows in 31 core-seconds**. Cheap next move, no farm, no
  approval needed at that price: a fixed-column singleton pass on chain #24 and
  the `ctrlgroup*` pool.
- **SIZING LESSON — the house rule worked and was then ignored.** Projected 9
  core-hours from an s57 SINGLETON rate measured on a Mac; realized 72.93, an
  **8.1× overrun**. But `pcprobe1` predicted **71.7 core-hours — within 1.7% of
  realized** — and that number was evidently never multiplied through into a
  re-sizing decision before launch. Two concrete rules: (1) **quote wall/probe,
  not the instrument's `secs_per_probe`** — the latter times only the dlx7g
  subprocess and misses everything else, a 1.08× gap on macOS but **4.9× on the
  farm**; the apparent "13× slower than local" is really 2.7× platform + 4.9×
  metric mismatch. (2) **Price the file-write, not the search.** `paircuts.py`
  writes a 57,547-byte instance file and spawns a fresh process **per probe**,
  to run a search of median depth **7 nodes** — **78.5% of the 72.93 core-hours
  went to writing instance files** (77.55 ms of the 98.75 ms wall per probe, vs
  0.58 ms on macOS). At these node counts the engine is free and I/O is
  everything.

## extended-census Σ15–16 sweep (5-block frame at the 5905-relevant scores)
- spec: `out/s57/express/enum_ext.py` (the 5-block extended enumerator,
  oracle-exact vs the census at Σ≤12 and Σ≤14) run at target V=15/16,
  pmax=16, ≤2 pivot excursions — sharded by search root on the farm.
  Harness build step required (no farm wrapper exists yet; same pattern
  as above). Exact spec of shard key: whatever enum_ext.py's outermost
  loop iterates (verify before sharding — untested claim).
- product: does the 5-block frame (generalized cost-3 doors) add ANY
  chains beyond the 26 known at the 5905-relevant scores? Closes or
  extends the s57 exhaustion (Σ≤14: 88.8M nodes, EXHAUSTED, 26 chains,
  0 excursions). A new chain at Σ15–16 would be a new 5905/5906 route
  candidate feeding the cover pipeline.
- projected: ~5×10⁹ nodes (s57 estimate) at the measured Σ≤14 rate
  (88,834,046 nodes / 169.9 s ≈ 523k nodes/s on a Mac core) ≈ **2.7
  core-hours**; minutes-to-~1 h wall on the farm depending on shard
  balance. Rate is Mac-measured — probe on a PC core before quoting wall
  time.
- approved: **YES — but the go-ahead was given OUTSIDE this file and never
  recorded here** (the same bookkeeping gap as `n6a450r2tightprobe`). Farm run
  `ex1` executed 2026-08-01 ~07:15 → 07:19 and the entry still read
  `approved: NO / status: pending` for six hours afterwards. Found and
  reconstructed by the sweep runner 2026-08-01 while checking what to run next
  — a re-run would have been launched on top of a completed sweep. **Record the
  approval when you give it.**
- status: **done — CLOSED by three runs, and closable as written.** `ex1`
  (`--target 15`) ran 2026-08-01 07:15:47 → 07:19:29 and was PARTIAL: the spec
  says **"target V=15/16"** but only target 15 was launched, which
  systematically drops 16 census chains (see result). The sweep runner found
  this 2026-08-01 and closed it the same day with two follow-ons:

  | run | target | terminal skip | nodes | chains | gen/pivbreak | wall |
  |---|---|---|---|---|---|---|
  | `ex1` | 15 | 0 | 540,659,889 | 238 | 27 / 27 | 3.7 min |
  | `ex2` | 16 | 1 | 540,660,629 | 54 | 0 / 0 | 3.7 min |
  | `ex3` | 17 | 2 | 540,660,819 | 16 | 0 / 0 | 3.7 min |

  All three 24 shards, 24 ok / 0 failed, **every shard EXHAUSTED**, 62,425
  subtrees each. Total cost **11.1 min wall / ~2.0 core-hours**. Artifacts
  `out/s58/farm/ex{1,2,3}/`, analysis `out/s58/analysis_ex1/`.
- result: **The census is confirmed exhaustive in its own frame at Σ≤16 — 0 new
  IN-FRAME chains — and 27 chains at the 5905 score exist OUTSIDE the frame,
  which no tool in this repo can currently turn into a cover instance.**
  62,425 subtrees, 540,659,889 nodes, 238 chains, 27 pivbreak, 27 gen.
  - **Coverage is real, and the STATUS line that says otherwise is a display
    artifact.** `STATUS.txt` reads `intermediates 4824/62425 (7.7%)`, which
    looks like a truncated run. It is not: `enumext_sweep.py:224` throttles
    heartbeats to `len(mine)//200`, so every shard writes exactly 201 ticks —
    24 × 201 = 4,824 exactly. Every shard ends `DONE … EXHAUSTED`. Verified
    the hard way as well: the depth-5 frontier rebuilds locally to 62,425
    roots / 0 above-frontier hits, round-robin `k % 24` sums to exactly
    62,425, and **five shards (13, 17, 18, 19, 22) were re-run from scratch
    locally and are byte-identical to the farm's output.**
    **TRAP: do not read this supervisor's percentage as coverage for any
    instrument that throttles its heartbeat.**
  - **The 238 chains:** 207 are rediscoveries of census chains
    (`results_n7_merged.csv`: 131 OPEN / 47 STRUCTURAL / 29 UNSAT), including
    all 26 s57 chains. 31 are not in the census — 24 at Σ≤16 (all outside the
    frame) and 7 at Σ=17 (an incomplete by-catch band, see below).
    **0 new in-frame chains at Σ≤16**, which upgrades the s57 exhaustion
    (Σ≤14) by two Σ steps for terminal-skip-0 chains.
  - **The 27 outside-frame chains, and why "27 gen" and "27 pivbreak" are the
    SAME 27:** exactly 5,040 of 20,160 extended hops are pivot-preserving and
    they are precisely the reversal door, so a generalized block always
    changes pivot and leaving pivot 7 always requires one. Not a coincidence —
    a property of the move table. All 27 have K + R = 141, i.e. **all sit at
    the 5905 score**; 24 are in the exhaustively-swept band. Shapes:
    out-and-back excursions of length 1 (×12) or 2 (×10), plus 5 chains that
    TERMINATE on a non-pivot-7 loop. Only blocks `(2,0,1)` and `(0,2,1)` are
    ever used.
  - **Nothing is gateable, and the ALARM banner's ritual does not apply.** The
    run emitted no word and no solution file — only chain path tuples. A chain
    is a kernel skeleton; turning one into a word needs the exact-cover
    instance BUILT and SOLVED, which is the open step (85 closed / 138 open
    across the census). The `validate -n 7 --complete` + `m3_check` text in
    ALARM.txt is boilerplate emitted verbatim by `untargeted_super.ps1:289`
    for any `***` line. **Nothing was gated because there was nothing to
    gate.** What is established is exactly: 27 chains at the 5905 score exist
    outside the frame and survive the free structural test. Not a cover, not a
    candidate word.
  - **No existing tool can build an instance for them.** `chain7.verify_chain`
    asserts pivot-homogeneity AND the reversal door; s57's
    `express.verify_chain_ext` relaxes the pivot assert but still demands
    `t == certificate.door(s,c)`. All 27 fail both (211/238 pass both,
    27/238 fail both — checked directly).
  - **A systematic gap, proven per-chain THEN closed: the target-15 run misses
    16 census chains.** Indices 35, 38, 42, 49, 56, 64, 67, 73, 78, 79, 81,
    152, 160, 195, 207, 222 (7 OPEN / 5 STRUCTURAL / 4 UNSAT). All 16 have a
    terminal loop riding only 5 orbits (13 chains) or 4 (3 chains).
    `kf2chain.py:29` permits a terminal skip; `enumext_sweep.is_hit` requires
    `K − Σ_hops == target` with the terminal treated as a FULL ride — so the
    census's V counts the terminal skip and enum_ext's does not, differing by
    exactly that skip. Each of the 16 was replayed on the sweep's own `expand`
    relation: all 16 reachable, full terminal ride legal in all 16, `is_hit`
    True at `target = 15 + skip` and False at 15.
    **`ex2` and `ex3` recovered all 16 at EXACTLY the predicted target** — 13
    skip-1 chains by target 16, 3 skip-2 chains (160, 195, 222) by target 17,
    with **zero terminal-skip mismatches across all 223 census matches**. That
    per-chain agreement, not the headcount, is what confirms the V-convention
    diagnosis. Tables: `missed16.tsv`, `missed16_RESOLVED.tsv`.
  - **UNION RESULT (ex1 ∪ ex2 ∪ ex3): 223/223 census chains recovered, 0
    missing.** 308 distinct chains total, 0 cross-run duplicates (structurally
    forced — a fixed chain has one `K − Σ_hops` so it can satisfy only one
    target). **0 new IN-FRAME chains at Σ≤16; 24 new OUTSIDE-FRAME**, all at
    the 5905 score. That is the entry's product question answered: yes, the
    5-block frame adds chains, exactly 24, and every one needs BOTH a
    generalized door AND a pivot excursion.
  - **The 54 non-census chains from ex2/ex3 are NOT a novelty claim.** All 41
    (ex2) sit at K=32 and all 13 (ex3) at K=33 — outside the census's K≤31
    band, so "not in `results_n7_merged.csv`" is trivially true and carries no
    information. `analysis/cover7/NOTES.md:43` already records **+392 K=32 and
    +1189 K=33 known from Egan's KernelFinder**, so these are very likely a
    subset of a known population. **UNDETERMINED-novelty, most likely known** —
    the patterns are not stored anywhere in this repo (only `KernelFinder.c`),
    so it could not be checked. Do not cite them as new.
  - **THIRD OCCURRENCE of the terminal-skip trap, and it was already written
    down.** `analysis/cover7/NOTES.md:41` says verbatim: "223 chains at K<=31
    (terminal partial rides included — **my initial enum missed 16**)". An
    earlier enumeration in this project missed the SAME 16 chains;
    `enum_ext.py` then reintroduced the identical blind spot; and the s57
    oracle passed only because all 26 chains at Σ≤14 happen to have skip 0.
    **Read NOTES.md before writing an enumerator.**
  - **CONVENTION TRAP for the next agent:** `enum_ext`'s `target` = census V +
    terminal skip. Nothing in `enum_ext.py` or `enumext_sweep.py` says so, and
    the s57 oracle passed only because all 26 chains at Σ≤14 happen to have
    terminal skip 0. Reconcile the two V conventions in writing before
    trusting any cross-comparison.
  - Σ=17 rows are **incomplete by-catch**, not a census: the `ssum > pmax`
    prune is applied at expansion, so Σ=17 hits reachable only through a Σ=17
    parent are missed.
  - **Sizing fact worth keeping: `--target` is COST-NEUTRAL.** Subtree 1 of
    shard 0 costs 35,066,249 / 35,066,735 / 35,066,857 / 35,066,879 nodes at
    target 15/16/17/20. `--pmax` dominates entirely. So each additional target
    sweep costs what the whole run cost: ~540M nodes ≈ 40 core-min ≈ **4 min
    wall on 24 farm cores**. The `--max-break 2` cap IS binding (12 of the 27
    saturate it), so ≥3-excursion chains are UNKNOWN, and max_break=3 is
    unmeasured — probe before quoting.
- open gaps, explicitly UNKNOWN (not negatives): chains where a *skipped*
  terminal orbit was ridden elsewhere are unreachable at ANY target (no census
  chain is of this species, but the extended frame permits it — needs an
  instrument change to even measure); conditional block B4 (`p1p0p2`) is still
  absent from enum_ext's move table (s57 flagged this, still true); ≥3 pivot
  excursions; and whether any of the 27 admits a cover (the free structural
  test refutes none of them, which is evidence in neither direction — 131 of
  the 207 rediscovered census chains are OPEN under exactly the same test).
- next, sized (NOT run, needs approval). **(1) is one instrument edit that
  strictly dominates three more sweeps — do that, not the target ladder.**
  The required terminal ride is DETERMINED by the node, not by a parameter:
  `r = 21 − K + ssum`, hit iff `1 ≤ r ≤ 6` and the first `r` orbits from the
  arrival are unridden; emit `terminal_skip = 6 − r`. That reproduces targets
  15–20 **in a single pass** and simultaneously admits the G2 species that no
  `--target` value can reach (chains where a skipped terminal orbit was ridden
  elsewhere). Cost is unchanged — target is cost-neutral — so **~540M nodes,
  ~40 core-min, ~4 min wall**, replacing 3 sweeps and closing a gap they
  cannot. Requires a small edit to `enumext_sweep.py` (not made; the analysis
  agent was scoped read-only). Then: (2) Σ=17 closure at `--pmax 17`,
  budget ~1.5–2 G nodes/sweep, probe first; (4) `--max-break 3`, unmeasured,
  probe first. **Non-farm prerequisite for the real prize:** extend the door
  check in `express.verify_chain_ext` (`t == door(s,c)` → `t ∈ legal_blocks(s)`)
  so the 27 become buildable — one line, but the honest gate is round-tripping
  s57's 33 out-of-frame corpus words through the extended builder (~half a day
  with validation). Only then is (5) worthwhile: run the 27 through the real
  refutation pipeline at s18 budget ≈ 27 × 30 min ≈ 14 core-hours farm.

## QS-B full realizer verdict-mix map, chains #0/#24 (s59 item 4 follow-on)
- spec: `out/s59/cliff/qsb.py` extended — multipliers 3.0, 3.25, 3.5, 3.75,
  4.0, 4.25, 4.5, 4.75, full on chains #0 and #24, N=200 samples/cell, TL
  30 s, REFUTATION LANE (ε=0) only: the product is a decision-rate and
  UNSAT-fraction curve, and only ε=0 can report the UNSAT fraction soundly.
  Sampling stream must stay `random.Random(12345+idx)` so cells stay
  comparable to s56/s59. Shard by (chain, mult); a SAT is a 5905 → stop,
  `p1a_assume.confirm_sat`, `cargo run --release -- validate -n 7 --file
  <abspath> --complete`, and `analysis/counting/m3_check.py -n 7 <abspath>`,
  all green before any claim.
- product: the curve NOVELTY-DESIGN §6.0/§6.4 actually needs ("what fraction
  of a generator's output can the realizer DECIDE?") as a function of the
  precision a proposer achieves, replacing the single ~100/s scalar.
- projected: 2 chains × 9 mults × 200 samples; measured s59 mean 0.006 s at
  ≤3×R, 0.2 s at 4.0×R, 4.8 s at 4.8×R → ~2.5 core-hours dominated by the
  top three cells; ~7 min wall on 24 farm cores. Round-robin probe first per
  house rule — high-mult cells may not price like low-mult cells.
- approved: **YES (Andrew, 2026-08-01 — "continue with the next item in the
  queue running on the farm")**. Recorded BEFORE launch this time.
- status: **done** — probe `qsbp1` (18 cells × 10, 1.7 min) then full run
  `qsb1`, 24 shards, 2026-08-01 → 14:24:17, **17.7 min wall**, 24 ok / 0 failed,
  3,600/3,600 units, no ALARM. New instrument
  `analysis/counting/s62/qsbsweep.py` + `analysis/farm/qsb_{ship.sh,shim.py,
  env.ps1,fetch.sh}` on the generic Python farm path. Artifacts
  `out/s62/farm/qsb{p1,1}/`.
- result: **The realizer's decision rate decays smoothly from 1.00 to 0.00
  across 3.0–4.9×R, and at BOTH open chains' own full pool it is exactly
  0.000 — NOVELTY-DESIGN §6.4's realizer clause fails where it matters, now at
  full resolution. 0 SAT in 3,600 draws.**

  | ×R | 3.00 | 3.25 | 3.50 | 3.75 | 4.00 | 4.25 | 4.50 | 4.75 | full |
  |---|---|---|---|---|---|---|---|---|---|
  | #0 decided | 1.000 | 1.000 | 1.000 | 1.000 | 0.995 | 0.885 | 0.640 | 0.295 | **0.000** (4.886) |
  | #24 decided | 1.000 | 1.000 | 1.000 | 1.000 | 0.975 | 0.705 | 0.325 | 0.095 | **0.000** (4.839) |

  Totals: n=3,600, **SAT=0**, UNSAT=2,583, UNKNOWN=1,017. Every decided draw is
  UNSAT — the engine never found a cover of a sampled sub-pool at any size.
  - **It is a smooth sigmoid, NOT the "sharp cliff" earlier work implied.** 50%
    decided at **~4.60 ×R** (#0) and **~4.38 ×R** (#24) by linear interpolation.
    Both chains' own pools sit 0.28 / 0.45 ×R PAST that crossing — which is the
    quantitative form of "these chains are out of reach of this instrument".
  - **Confirms and sharpens s59** (which measured TL 5 s, N=30–100): decisions/s
    fall 53.05 → 0.03 on #0, a **1,768× collapse**, against s59's ~900×. The
    direction and the mechanism hold; the magnitude was understated.
  - **A SAT here WOULD have been a world record** — both chains have K+R=141 and
    length = 5764 + #2-loops with #2-loops pinned at K+R, so any cover compiles
    to a **5905**. Verified from the instrument's own chain arithmetic
    (27+114 and 29+112). The shard was built to stop and banner on one. None
    occurred.
  - **UNKNOWN is a timeout, not a negative.** 1,017 draws are undecided at 30 s;
    they say nothing about whether those sub-pools admit covers.
- spec defects found in this entry BEFORE launch, all corrected in the as-built
  instrument (the entry text above is left as written for the record):
  1. **`mult = full` is degenerate.** `k = |pool|` makes every draw the WHOLE
     pool, so "N=200 samples" is **1 distinct atom set** — 200 identical
     deterministic runs at ε=0, ~1.7 core-hours of duplicate work per chain.
     Verified directly: 1 distinct set over 200 draws at `full`, 200 distinct at
     every other multiplier. The instrument keeps all 200 sample rows (the
     statistic is unaffected) but solves each distinct set once — 3,248 real
     solver calls for 3,600 draws. Note the dedup is PER-SHARD under unit-level
     round-robin, so `full` cost 24 solves (one per shard), not 1.
  2. **The ~2.5 core-hour / ~7 min projection was extrapolated from TL 5 s
     data** and is low: probe-measured 5.87 core-hours / 14.7 min wall,
     realized 17.7 min.
  3. **"Shard by (chain, mult)" would idle half the farm.** Cell cost spans four
     orders of magnitude (0.019 s to 30 s mean), so 18 cell-shards means the
     wall is set by one shard while the rest finish in seconds. Unit-level
     round-robin instead — every shard gets 1/N of every cell, so all finish
     together and each shard is its own round-robin probe.
  4. **"decisions/s" is a time-limit artifact and should not be the headline.**
     Cost is bimodal, not a rising mean: every UNSAT exhausts in ~0.016 s
     (median unchanged across ALL multipliers — 0.016 s at 3.0×R and at 4.5×R),
     while undecided draws burn the full budget. So the mean rises only because
     the UNKNOWN fraction rises. **The sound product is the decided fraction**,
     which is what the table above reports.
  5. Seconds are not comparable to s59's: `qsb.py` ran cells under an internal
     `ThreadPoolExecutor(max_workers=3)`; shards here are single-threaded.
     Verdicts are comparable (deterministic lane, byte-identical instances).

## A0 gate re-run at 120 s, both lanes (s60 menu item 2 — LOCAL, not farm)
- spec: re-run the s56 A0 baseline ("cover from the chain alone, no atom
  assumptions" — JOURNAL s56 §1's "0/6") on the six s56 panel control
  instances at TL ≥ 300 s, BOTH lanes (ε=0 and ε=0.15 via
  `out/s57/proposer/dlxrun.py`), 1 seed ε=0 + 2 seeds ε=0.15 per cell.
  Instances regenerated via `out/s59/cliff/geninst.py` conventions and
  byte-checked against s56 where applicable. Every run row appended to a
  trials.tsv ledger (stage tag `a0_120`); verdicts three-valued, a timeout
  is UNKNOWN, never a negative result. Heartbeat: STATUS file updated
  per-run + ledger append (OPERATIONS.md conventions); abort =
  `pkill -f dlxrun`.
- product: replaces the LAST uncorrected 15 s budget artifact in the repo —
  currently the most citation-dangerous line ("no engine finds a cover from
  the chain alone", out/s59/cliff/REPORT.md §7 flags it). Either the field
  fact survives at a real budget (citable at last) or a control chain
  completes from the chain alone and the A-ladder premise changes.
- projected: 6 instances × 3 runs × ≤300 s ≈ **≤ 90 min at 3 cores local
  Mac** (cliff REPORT §7 sizing). No farm needed.
- approved: **YES (Andrew, 2026-08-01 — "build the system to make number one run
  on pc with sub agents then run it")**. RETARGETED from local Mac to the farm
  PC per the standing instruction ("run the sweeps on the pc, do not run
  anything on the mac", 2026-07-31; "we have the farm for a reason"). Two
  deviations from the spec above, both recorded before launch:
  - **TL 600 s, not 120 s.** The entry's TITLE says 120 s while its own spec
    body says "TL ≥ 300 s"; the s59 REPORT §7 sizing that produced it also says
    ≥300 s. 600 s satisfies the spec's floor with margin, and at 18 cells on 28
    cores the extra budget is free in WALL time (~10-12 min either way) while
    making a surviving UNKNOWN materially more citable. Taking the larger
    budget is the conservative choice for a run whose product is a negative.
  - **abort is NOT `pkill -f dlxrun`** (that is the local-Mac form). On the farm
    it is `untargeted_abort.ps1 -Tag <tag>`, which uses the pid+name+start-time
    process-identity guard so an abort can never kill the transcription
    service's python.
- status: **done** — farm run `a0g1`, 18 shards / 18 workers, 2026-08-01
  12:52:22 → 13:02:36 PC time, **10.2 min wall / 3.00 core-hours**, 18 ok /
  0 failed / 0 stalled, **no ALARM.txt**. New instrument
  `analysis/counting/s62/a0gate.py` + `analysis/farm/a0_{ship.sh,shim.py,
  env.ps1,fetch.sh}`, driven through the existing generic Python farm path
  (`pysweep_run.ps1` + `untargeted_super.ps1`) — no new supervisor was
  written. Artifacts: `out/s62/farm/a0g1/` (18 stats rows + 18 ledger rows +
  per-cell instance/solution files).
- result: **18/18 UNKNOWN at 600 s in BOTH lanes — the field fact survives a
  40× budget increase, and is citable at last.** Verdict mix: refutation
  (ε=0) 6 cells SAT=0 UNSAT=0 UNKNOWN=6; witness (ε=0.15, 2 seeds) 12 cells
  SAT=0 UNSAT=0 UNKNOWN=12. Every cell ran the full 600.0 s (min=max=600.0 —
  none decided early), for **6,809,758,292 nodes** total.
  - **THE PREMISE OF THIS ENTRY NEEDED TWO CORRECTIONS, both found before
    launch and both load-bearing.**
    1. **A0 is known-SAT BY CONSTRUCTION, so this gate measures FINDABILITY,
       never existence.** Verified from source two ways: `reduce_instance`
       with no fixed rows and no atom filter is the identity (nothing is
       deleted), and `p1a_assume.extract` *asserts* every row of the source
       word's cover is present in the instance (`cert row {key} absent from
       instance rows`). So a cover provably exists in all six. Consequences
       the entry did not state: a SAT would be a findability event and **NOT
       a new record** — the chain pins `length = 5764 + (K+R)`, so any cover
       compiles to a word the same length as its source — and an **UNSAT
       would be a soundness CONTRADICTION**, not a result. The instrument
       alarms on UNSAT for that reason. (Both harness scripts initially
       carried the overclaim "on the 5906 controls a SAT is a 5905
       CANDIDATE"; corrected in all three sites before launch.)
    2. **The "0/6 at 15 s" being corrected was ITSELF unbacked.** A grep of
       all of `out/s56/` finds exactly ONE surviving A0 record anywhere:
       `out/s56/p1a/probe_gate.json`, one control, `--time-limit 30`,
       UNKNOWN, 13,719,552 nodes. **Five of the six controls have no A0
       artifact at any budget, and the one that does was run at 30 s, not
       15 s.** So "six 15 s UNKNOWNs" was a reconstruction, and the 15 s
       figure should not be cited either. This run produces the first
       per-control A0 ledger that has ever existed.
  - **The one control with an s56 number, measured head to head:**

    | | nodes | maxdepth | verdict |
    |---|---|---|---|
    | s56, 30 s | 13,719,552 | 83 | UNKNOWN |
    | s62, 600 s (ε=0) | 383,881,216 | 93 | UNKNOWN |

    20× the budget buys **28× the nodes and +10 depth** — and still no
    decision. The instance is byte-identical between the two runs (sha256
    `6cb3ae0b4db3…`, checked against the committed s56 file), so this is a
    like-for-like comparison, not a re-derivation.
  - **How far the search actually gets** (best maxdepth over the 3 cells vs
    the cover size the chain requires):

    | control | R = need | depths (ref/wit/wit) | % of cover |
    |---|---|---|---|
    | 5906.up-02d771908307 | 124 | 93 / 92 / 93 | 75.0% |
    | 5906.rbnd-2641d60c9d5c | 123 | 84 / 87 / 87 | 70.7% |
    | 5906.up-331228e22360 | 122 | 83 / 87 / 84 | 71.3% |
    | 5906.up-6f42b3603dac | 120 | 85 / 91 / 85 | 75.8% |
    | 5906.up-0a065898a821 | 118 | 93 / 94 / 93 | 79.7% |
    | 5907.up-6f2e8d9df51c | 138 | 110 / 102 / 108 | 79.7% |

    Every control stalls at **70–80% of a cover it is guaranteed to
    contain**. The last ~25-30% of the descent is where the whole difficulty
    lives — consistent with the A1 contrast in the same s56 file, where
    supplying the true atom pool drops the instance 3,228 → 664 rows and it
    goes SAT in **0.01 s / 166 nodes**.
  - **The witness lane buys nothing**, a third independent confirmation of
    the s59 lane correction: 8 restart attempts (ε=0.15) reach the same
    depth band as 1 deterministic attempt (ε=0), and on two of six controls
    the ε=0 cell reaches the DEEPEST point of the three. Restarts are not
    automatically better — do not assume they are.
  - **Sizing was as predicted and the prior was right.** A0 sits at
    **4.92–5.73 ×R**, while s59 measured this instance family as
    SAT-reachable only to 2.69–3.50 ×R, with throughput collapsing ~900×
    between 3.0 and 4.8 ×R. 18 UNKNOWNs was the honest expectation before
    launch and was stated as such. The product is not a surprise; it is the
    difference between "we did not look" and "we looked hard", which is
    exactly what makes the line quotable.
  - **What may now be said, and what may not.** SAY: "at 600 s per cell,
    both lanes, no engine we have finds a cover from the chain alone on any
    of the six controls — 18/18 undecided, 6.8e9 nodes, best descent 70–80%
    of the required cover." DO NOT SAY: "no cover exists from the chain
    alone" (a cover provably exists), or anything sourced to the 15 s
    figure. The instrument writes the reading into every row verbatim:
    `nothing-learned (budget exhausted; NOT a negative result)`.
  - **Provenance is closed end to end.** All six A0 instances regenerate
    byte-identically on the Mac; the farm reproduces all six sha256s
    (across a CPython 3.14 → 3.11 jump); 13 payload files byte-identical
    both ends; the 18 cells partition 0..17 exactly; and the farm-solved
    instance for the anchor control is byte-exactly the committed s56 file.
- ops notes (three generic traps, two of them NEW):
  1. **A fourth false-alarm site, in a NEW place.** `untargeted_status.ps1`
     banners `.txt` files under the run out dir as "ESCAPE CANDIDATES", and
     it counted this instrument's 18 `work/inst_*.txt` DLX *input* files as
     18 escapes. The three previously-documented instances of this trap
     (fuse.py `ESCAPES 0`, demotion.py `novel-candidate classes: 0`, and the
     s52b supervisor scan) were all in the **stdout** scan of
     `untargeted_super.ps1`, which was fixed; this one is in the **status
     reporter** and counts **FILES, not log lines**, so that fix does not
     reach it. Harmless here (no ALARM.txt; the supervisor's own scan was
     clean) but it would bury a real product file. **Fix before the next
     Python sweep: exclude a `work\` subdir from the status reporter's
     product counter, or keep scratch out of the run dir.**
  2. **A control word path can self-banner.** One panel control lives in
     `data/novel5906c/`, and that path printed next to a timestamp genuinely
     matches the supervisor's `NOVEL[^:\r\n]*:\s*[1-9]` branch. The
     instrument prints base names only, behind a rewrite guard on every
     print. **Any instrument touching `data/novel*` has this problem.**
  3. **`-StallMinutes 20`, not the default 10.** One shard = one cell here,
     so a healthy shard is legitimately silent for the whole 600 s solve
     plus instance build; at the default every shard would have been flagged
     STALL. Sharding finer than the heartbeat granularity is what creates
     this — check the ratio before launching.
  - Harness defect for the record: `a0_ship.sh`'s manifest omitted the s56
    anchor file `out/s56/p1a/inst_5906.up-02d771908307_A0_0.txt`, so the
    farm-side byte-check degraded to `anchor-file-absent` on 3 cells (it
    records the degradation rather than passing silently — correct
    behaviour). Recovered after the fact by hashing: the solved instance
    matches the committed s56 file exactly. **Add the anchor to the manifest
    if this is re-run.**
  - Also fixed pre-launch: the instrument's first draft wrote a `3/3` field
    on its terminal `DONE` STATUS row, which the supervisor would have
    counted as a fourth progress row (tally `4/3`) — the s52b progress-tally
    defect re-manifesting in new code. Terminal/event rows now carry no
    `\t<d>/<d>\t` field.
- next (NOT run, needs approval): the natural follow-on is an A-ladder
  gradient — A0 is 4.9–5.7×R and A1 (true atom pool, ~1.4×R) is SAT in
  0.01 s, so the interesting object is where between them the cliff sits.
  `AP` at graded noise already exists in `p1a_assume` and `geninst.py`
  regenerates that whole family, so this is instrument-free. It would give
  the row-count-vs-findability curve that NOVELTY-DESIGN §6.4 wants, at
  roughly the cost of this run per band.

## full no-good harvest of the s59 prefix-refutation stream, #0/#24 (s60 pilot verdict attached)
- spec: `out/s60/nogood/harvest.py --spec farm{0,24} --check-from 6
  --step-cap 0.2 --m 30 --beam 24 --mode score`, sharded by seed, one shard
  per core; every rc 2 greedily minimized by one deletion pass
  (`cutlib.minimize`, drop kept ONLY on rc 2 within the cap — a timeout is
  never a cut), then EVERY surviving cut re-confirmed in a fresh process at
  a ≥ 10× cap (`confirm.py`, mandatory: minimization lands cuts at the cap
  boundary — 8.7–29% of pilot cuts exhaust above the harvest cap).
  Refutation lane only, ε = 0, deterministic; store = JSONL antichain keyed
  by the base-instance sha256. Ledger per shard.
- product: a persistent sound no-good store over the s59 stream (~31,026
  refutations) for chains #0 and #24.
- projected: 31,026 refutations × 2.41 s measured minimization cost =
  **20.8 core-hours** (12.8 with the measured 31–46% in-run subsumption
  skip); ~55 min wall on 24 farm cores. Yield ~31k cuts of mean 8.2 rows
  (measured pilot: 22.9 and 21.3 cuts/min/core, shrink 1.71× / 2.04×,
  0 soundness violations vs 131 known covers).
- approved: NO
- status: pending — **and the s60 pilot recommends NOT approving it as
  specified** (`out/s60/nogood/REPORT.md`): the consuming side was
  measured — 3,599 fresh legal prefixes on three chains hit a
  115/107/47-cut store ZERO times, and P(random 30-prefix ⊇ fixed 8-set)
  = 2.6e-16, so ~10¹⁵ cuts of this length are needed before the store
  prunes anything it did not itself generate. 20.8 core-hours buys an
  asset with no measured consumer. Redirect the budget to the PAIRWISE
  cut store (entry above, ~9 core-hours): at size 2 the same 50% hit rate
  needs 4.4e3 cuts — twelve orders of magnitude cheaper per cut — and
  pairs are consumable as instance reductions, which 8-row sets are not
  (dlx7g has no clause facility).
- **UPDATE 2026-08-01 — the recommended REDIRECT TARGET has now been run, and
  it is spent.** The pairwise cut store this entry defers to was executed as
  farm run `pc1` (72.93 core-hours, 147,561 sound size-2 cuts). Its verified
  product as an instance reduction is **54 row deletions, reproducible by a
  9.3-second local singleton pass** — see that entry's result. So the s60
  argument "size-2 cuts are the cheap consumable layer" was RIGHT that they
  fire (the live store clears s60's own 50%-hit bar by 6×) and WRONG that
  firing converts into reduction: 81.9% of the cuts reference rows the store
  itself proves dead, and the sound propagation closure hits a fixpoint at
  round 2 with no cascade. **The recommendation against this entry therefore
  stands and STRENGTHENS — but the redirect it offered is no longer available.**
  If the no-good direction is revisited at all, the open question is whether
  the residual 26,683 live pairwise cuts convert +27% forward-checking pruning
  into a DECIDED instance; that is untested and costs nothing to test locally.
  Read alongside `qsb1`: at these chains' own pool size the realizer decides
  0.000 of draws at 30 s, so the margin any pruning layer must close is large.
- result: —

## n=6 midgame j-probe — supply-tight multi-cover sweep (levels 60–450) (s62)
- spec:
    # PART 1 (sound global negative, no seeds — the supply-tight corner)
    python3 out/s62/jtax/cover_search.py 6 870 --jmin 1        # v=24 branch, ~5 core-h
    python3 out/s62/jtax/mcover_search.py 6 872 --v 28 --splits 20 --jmin 1
    python3 out/s62/jtax/mcover_search.py 6 872 --v 27 --splits 15 --jmin 1
    python3 out/s62/jtax/mcover_search.py 6 872 --v 26 --splits 10 --jmin 1
    python3 out/s62/jtax/mcover_search.py 6 872 --v 25 --splits  5 --jmin 1
    # mcover_search.py = cover_search.py generalized from exact covers to
    # k-loop MULTI-covers with prescribed cycle multiplicities — TO BE BUILT
    # (~150 lines; the DFS is unchanged, only the arc-start table becomes an
    # assignment enumerated over the excess incidences). ~1 day agent work,
    # no compute.
    # PART 2 (honest sampling frame, midgame, existing machinery)
    for L in 60 180 300; do
      python3 analysis/trackb/record_to_seed.py <walk> 6 $L > out/s62/seed_$L.txt
      cargo run --release -- sojourn-dfs -n 6 --class 140,8,0,0,0 \
        --profile-file analysis/trackb/profiles/a140_8_0_0_0.txt \
        --depth 6 --dedup exact --dump-frontier out/s62/f_$L.tsv
      cargo run --release -- beam -n 6 --width 8000 --seed-file out/s62/f_$L.tsv \
        --bound residual --max-len 873 --endgame 20 --endgame-top 400
    done
- product: PART 1 is a SOUND NEGATIVE on the supply-tight corner of every
  j>=1 cell at length <= 872 — including the ONLY j>=1 872 cell in a known
  allocation ((140,8,0,0,0): splits=20, D=8, v=28, supply-tight; see
  out/s62/jtax/REPORT.md §5). A j>=1 walk <= 872 either lives there or has
  loop-supply slack >= 1 — the precise residual obligation for the next
  mechanism. PART 2 is explicitly a SAMPLING frame, not a negative: it
  measures whether any j>=1 structure is reachable in the blocked zone
  (levels 60–450) from non-record allocations. Any completion <= 873 is
  scored with out/s62/jtax/verify_master.py; if j >= 1 it is a
  first-of-species event. Rationale for this shape: tail re-completion from
  record prefixes (splits 25) is excluded <= 871 by MASTER for free — the
  live cells are low-splits/high-D, unreachable from any record prefix.
- projected: PART 1: cover_search growth measured x29 nodes per +1 char
  (3.63e7 nodes / 21.5 s at TMAX 868; 1.06e9 / 605 s at 869, single-core
  Mac, ~1.75e6 nodes/s) => TMAX 870 v=24 branch ~3.1e10 nodes ~5 core-h.
  Multi-cover branch counts UNMEASURED (the s62 nearcovers.py sizer is
  buggy and was discarded) — re-probe with --count-only before launch and
  quote a round-robin rate, not a first-K rate (OPERATIONS.md). Working
  budget: 8–30 core-h, 8-way => 1–4 h wall. PART 2 cut to 2 allocations
  ((140,8),(135,9,2)) x 3 anchors => ~7 core-h.
- alarm paths: any candidate <= 872 -> validate --complete THEN m3_check
  (exit 2 = novel = M3 event, banner + stop). Any PART 1 solution at all is
  a first materialized j>=1 walk below 874 -> stop and report. Any
  verify_master.py violation (exit 1) is a THEORY-level alarm -> stop
  everything.
- approved: **YES (Andrew, 2026-08-01 — "we should be using the PC as much as
  possible, there is nothing running on it, these are like 15 minute runs over
  there")** — recorded at approval time. Scope of the approval as given: FARM
  execution (the PC), covering PART 1 once mcover_search.py passes its positive
  controls and the count-only sizing re-probe lands within ~2× the 8–30 core-h
  working budget (if sizing blows past that, come back before launching).
  PART 2 rides under the same approval but launches only after PART 1's sizing
  is in hand (it needs the Rust binary — confirm the farm path can host it or
  run PART 2 locally and say so in the run record).
- status: **sizing DONE (s63, 2026-08-01) — PART 1 as specced NOT launched
  (sizing ≥ ~1,240 core-h, 20×+ past the 60 core-h stop threshold, so per the
  approval scope it comes back to Andrew); line 1 of PART 1 (v=24 @ TMAX 870)
  was instead RUN TO COMPLETION locally: 3,405,635,896 nodes, 1.57 core-h,
  NO walk — a complete negative killing the supply-tight v=24 cells at
  868/869/870. RESHAPE recommended** (drop v=25/v=26 at ≥290/≥752 core-h;
  rebuild v=28 around the new forest law — see out/s63/mcover/REPORT.md §6/§9:
  the (140,8,0,0,0) cell forces the loop-cycle incidence graph to be a FOREST,
  cutting the branch to ~N_forest(28) × 0.178 s ≥ 10 core-h; N_forest(28)
  count-to-completion in flight). mcover_search.py BUILT and two-tier
  controlled (node-for-node vs cover_search.py incl. the 36,304,934-node s62
  negative; census-exact vs an independent n=4 brute force; validated n=5
  multi-cover witnesses). NOTE: cover_search.py measured to search a strict
  SUPERSET family (missing door-mid test) — harmless to every s62 claim (all
  negatives/unmoved minima) but any future FIND from it needs re-checking;
  mcover_search.py has the test on by default.
- result: supply-tight v=24 j≥1 family EMPTY to length 870 (n=6, pure walks);
  PART 1 as-specced sizing ≥ ~1,240 core-h (lower bound); reshaped
  forest-restricted v=28 branch pending N_forest(28) count + Andrew's call
- **RESHAPE approval (Andrew, 2026-08-01, recorded at decision time):
  v=28 FOREST branch ONLY** — launch on the farm once the N_forest(28)
  count-to-completion confirms the branch fits ~2× the 8–30 core-h budget
  (count in flight, orchestrator-local). The v=27 forest+1 branch and the
  v=24 @ TMAX 871 extension were offered and NOT selected — do not launch
  them. Alarm paths unchanged from the spec (any solution = first-of-species
  j≥1 walk ≤ 872 in the (140,8,0,0,0) cell = M3 ritual + stop; any
  verify_master exit 1 = THEORY alarm).
- **TWO-STEP amendment (Andrew, 2026-08-01, second decision, recorded at
  decision time).** The 2 h count PARTIALed at N_forest(28) ≥ 939,294 (78%
  of the 1.2M gate), and the stride-sharded farm shape would duplicate the
  full ≥2 h enumeration in every DFS shard (the stride filter skips
  processing, not enumeration — a sizing defect in the original shape).
  Offered: two-step rebuild / launch-tonight-as-is / hold. **Andrew chose
  TWO-STEP**: (1) add `--emit-covers` / `--covers-file` modes to
  mcover_search.py (enumerate ONCE locally — which also yields the exact
  N_forest(28) — ship the cover file, shards process balanced slices with
  zero duplicated enumeration; controls mandatory, file sha-verified both
  ends, fetch adjudication sums against the file's own total); (2) launch
  when the exact N gives a statable wall: N ≤ ~1.2M (≈ ≤4.5 h wall at 24
  shards, farm per-cover ~0.325 s = 1.91× Mac) → launch under the standing
  approval; N > 1.2M → back to Andrew. mc28 harness v1 (stride shape) is
  built, PC-verified, dry-run-proven — being reworked to the covers-file
  shape; its two pre-flight catches (GATE.txt escape-scan trap; bash-3.2
  mapfile silently emptying the find list in fetch) are recorded in the s63
  mcover addendum.
- **GATE RAISED (Andrew, 2026-08-01, third decision, recorded at decision
  time).** The emit crossed 1.2M covers with the enumeration still running —
  the original gate failed early as designed. Offered: raise gate to 3M /
  launch at any N / hold. **Andrew chose RAISE TO 3M**: auto-launch
  overnight on emit completion if N_forest(28) ≤ 3,000,000 (wall =
  N × ~0.325 s / 24 shards ≤ ~11.3 h; ≤ ~270 farm core-h); if N > 3M, back
  to Andrew with the exact number. Covers-file design keeps cost strictly
  linear so the commitment is bounded and statable up front.
- **HOLD (Andrew, 2026-08-02 morning, recorded at decision time): "I want to
  hold off on the runs until tonight."** No farm launch before tonight; the
  local emit continues to completion for the exact N (info only). The
  reshape menu (B: rigidity-specialized DFS, 10–100× on the 94% term,
  ~4–8 h agent work, needs ≥200k-cover census-equality control; A:
  tree-sharded enumeration, ~2–4 h, composes with B; D: as-specced ~14.6 h
  wall at N=4M; C: reversal-only symmetry, ≤2×, low value) is priced in the
  s63 mcover addendum — decision deferred to tonight with exact N in hand.
- **3M GATE BREACHED (2026-08-02 ~00:30): N_forest(28) > 3,063,413 with the
  enumeration still running — NO LAUNCH, farm untouched.** The emit
  continues to completion (one local core; exact N is the morning decision
  input). The old ×29-style intuition failed twice on this branch (206k at
  600 s → 939k at 2 h → >3M at ~5.5 h; the enumeration rate varies 45–380
  covers/s by subtree). Pending Andrew: launch at exact N (wall =
  N × 0.325/24 s: 4M ≈ 15 h, 6M ≈ 22.6 h), a reshaped
  tree-sharded/no-file variant, or hold. The mc28 covers-file harness
  remains built, sha-matched, dry-run-proven, idle-ready either way.

## n=5 cap-154 exhaustive (j-tax decider) — SUPERSEDED 2026-08-01 (s62)
- spec: out/s56/slacktax/slack_dfs -n 5 --cap 154 --shards 64
  --splitdepth 12 --shard $i   (i = 0..63, 8 concurrent)
- product: WAS "decides the n=5 j-tax (1 vs 2)". SUPERSEDED:
  out/s62/jtax/witness/n5_j1_154.txt is a validated length-154 j=1 n=5
  superpermutation (Rust validator: 154, 120/120, complete;
  loop_ledger_probe: j=1, deficit=1, V1/V2/V3 true). With s56's cap-153
  exhaustive (1.6e9 nodes, 8 shards, 0 aborts, all walks <=153 tight/j=0)
  the n=5 J-TAX IS EXACTLY 1. The run would only re-confirm it.
- projected: ~40 min 8-way. TRAP (carried from S56): shard imbalance at
  splitdepth 8 — the n=5 tree is front-loaded and a depth-8 split makes the
  last worker run ~5x the mean; splitdepth 12 is the calibrated value.
- approved: NO
- status: **CANCELLED (Andrew, 2026-08-01 — chose "Cancel" over keeping it
  for the two nice-to-have byproducts; recorded at decision time)**
- result: n=5 j-tax = 1 (witness, s62). If run anyway, the only remaining
  products are (a) the exhaustive COUNT of j>=1 walks at 154 and (b) a
  cross-check of cover_search.py against slack_dfs.c at n=5 — both
  nice-to-have, neither decision-relevant.

## s64 refactor P5 — farm-PC env-check + dry-run smoke (scratch tag only) — APPROVED 2026-08-02
- spec: P5 of docs/REFACTOR-BRIEF.md — verify the unified farm harness
  template by an env-check + `-DryRun` smoke on the PC, writing ONLY to a
  scratch tag (mc28-template parity: 24/24 DONE, escape scan 0, per s63).
  No real compute, no products, farm otherwise untouched.
- product: parity evidence that the template harness reproduces the s63
  mc28 dry-run behavior before a0/qsb configs are ported.
- approved: YES (Andrew, 2026-08-02, daytime dry-run explicitly OK'd while
  runs are HELD until tonight; recorded at decision time). Also decided:
  package home = pylib/ at repo root; promoted package copies become
  CANONICAL for future sessions (out/ originals frozen as history).
- status: **DONE 2026-08-02** — template config `mc28` deployed to scratch
  `F:\superpermFarm\untargeted\s64tpl_scratch`, `farm_env.ps1 -Full` ENV OK 0
  failures (P3 real branch 29,609,908 nodes, K={8:200}), dry smoke `runs\s64tpl`
  **24/24 DONE, ESCAPES=0, .txt products 0**, alarmtest 0 failures; both scratch
  dirs removed, farm restored, no compute launched.
