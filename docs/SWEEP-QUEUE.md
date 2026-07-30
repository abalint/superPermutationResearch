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
- projected: unmeasured; tie collection weakens B&B pruning (strict-only)
  so this may be much slower than the plain sweep — that is what the
  probe measures. Abort the probe itself if it passes 15 min.
- approved: NO (probe is < 30 min tier, but Andrew declined the first
  launch attempt s28b — confirm with him before running anything here).
- status: pending
- result: —

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

## tie-census full corpus
- spec: as probe, without `--limit`, `--out-dir data/surgery_finds`
- product: corpus-wide new-allocation tie count + reached-allocation
  histogram (S1 shell-connectivity map; SURGERY-DESIGN §8 next-step).
- projected: probe × 220 — fill in after the probe.
- approved: NO
- status: pending (blocked by probe)
- result: —
