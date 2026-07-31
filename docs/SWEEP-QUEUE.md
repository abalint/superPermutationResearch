# Sweep queue — the operator/researcher interface

The RESEARCH agent appends entries (template below). The OPERATOR
executes them top-down, fills in status/results, and never edits the
spec of a pending entry. Andrew's go-ahead is per-entry (`approved:`),
required for anything projected > 30 min. One `running` entry at a time.

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
- approved: NO
- status: pending
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
- approved: NO
- status: pending
- result: —

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
- approved: NO
- status: pending
- result: —

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
- approved: NO
- status: pending
- result: —

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
- approved: NO
- status: pending
- result: —

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
- approved: NO
- status: pending
- result: —

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
- approved: NO
- status: pending
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
- approved: NO
- status: pending
- result: —
