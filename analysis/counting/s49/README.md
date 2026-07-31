# s49 instruments (promoted from out/s49/ scratch)

All scripts expect to be run FROM THE REPO ROOT and write scratch/indexes under
`out/s49/item{1,2}/` (regenerable; `fuse.py index` rebuilds the 4.35M-instance
tables in ~45 s). Provenance and results: JOURNAL s49.

Item 1 — blind-spot composition chains:
- `blindspot.py`    — recompute the 12 untouched classes from the committed edge tables
- `admdiff.py`      — exact admissible-frame (rigidity-forced) edit diffs, blind × corpus
- `analyze.py`      — summary table over admdiff output
- `rulesizes.py`    — |ents_out| distribution of the 864-rule vocabulary (max = 534)
- `fuse.py`         — the fused-composite instrument (index / depth1 / depth2 /
  **untargeted** modes).  s52 added `untargeted`: the escape sweep.  One shard =
  one (blind class, orientation), 24 shards; per edit-preconditioned r1 the whole
  4,354,560-instance table is rescanned against the intermediate F', every
  surviving r2 is applied, each fused product is replayed ONCE and canon-gated
  against the **220-class project shell** (m3_check's n=7 index + every
  SUPPLEMENTARY index).  In-shell = a rediscovery edge row; out-of-shell at
  length ≤ 5906 = an ESCAPE (banner + written string; still owes m3_check -n 7
  and the Rust validator).  `--dry-run` sizes a shard, `--limit N` truncates it,
  `--control --src <class> [--target <class>]` runs the same machinery from a
  non-blind anchor, `--verify-scan` cross-checks the early-exit precondition scan
  against the all-columns reference.  Two corrections to the depth1/depth2 scan
  live here: doors_in is validated POST-removal (32 of the 864 rules reuse a door
  exit and could never fire before), and the scan narrows column-by-column with
  early exit (7.5 s → 0.11 s per rescan, same instance set).
- `control.py`      — positive controls (recorded-edge lookups; run before believing any 0)
- `sumset.py`       — liberal algebraic 2SUM test (δ_req ∈ Δ+Δ, direction-symmetric)
- `sizing_untargeted.py` — sizing for the queued untargeted fused sweep

Item 2 — R-BND extensions:
- `rev_census.py`        — per-walk R-BND FWD/REV multiplicity census (s48 version + --shard i k)
- `rbnd_w4.py`           — w4 door-for-boundary trade probe (forced FWD + REV, both n)
- `rbnd_w4_composite.py` — REV-w4 lift then FWD-w4 drop composite (the involution result)
