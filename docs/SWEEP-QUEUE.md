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
- status: running (farm run `a450b50`, 24 workers, supervisor pid 10236,
  started 2026-07-29 20:17:58 local-PC time)
- result: —

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
- projected: ~2.1 h single-core from a first-300 probe (104 s) — but that
  probe is ALPHABETICAL-PREFIX biased (see Farm execution note: ×3.3 at
  anchor 450), so plan for up to ~7 h single-core; re-probe round-robin
  or run on the farm (~20–40 min on 24 cores). **Farm caveat: s30
  changed `src/tailatsp.rs` (merge machinery) — cross-compile and reship
  `superperm.exe` BEFORE any farm run of this entry.**
- approved: NO
- status: pending
- result: —

## tie-census full corpus
- spec: as probe, without `--limit`, `--out-dir data/surgery_finds`
- product: corpus-wide new-allocation tie count + reached-allocation
  histogram (S1 shell-connectivity map; SURGERY-DESIGN §8 next-step).
- projected: probe × 220 — fill in after the probe.
- approved: NO
- status: pending (blocked by probe)
- result: —
