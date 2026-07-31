# s49 instruments (promoted from out/s49/ scratch)

All scripts expect to be run FROM THE REPO ROOT and write scratch/indexes under
`out/s49/item{1,2}/` (regenerable; `fuse.py index` rebuilds the 4.35M-instance
tables in ~45 s). Provenance and results: JOURNAL s49.

Item 1 — blind-spot composition chains:
- `blindspot.py`    — recompute the 12 untouched classes from the committed edge tables
- `admdiff.py`      — exact admissible-frame (rigidity-forced) edit diffs, blind × corpus
- `analyze.py`      — summary table over admdiff output
- `rulesizes.py`    — |ents_out| distribution of the 864-rule vocabulary (max = 534)
- `fuse.py`         — the fused-composite instrument (index / depth1 / depth2 modes)
- `control.py`      — positive controls (recorded-edge lookups; run before believing any 0)
- `sumset.py`       — liberal algebraic 2SUM test (δ_req ∈ Δ+Δ, direction-symmetric)
- `sizing_untargeted.py` — sizing for the queued untargeted fused sweep

Item 2 — R-BND extensions:
- `rev_census.py`        — per-walk R-BND FWD/REV multiplicity census (s48 version + --shard i k)
- `rbnd_w4.py`           — w4 door-for-boundary trade probe (forced FWD + REV, both n)
- `rbnd_w4_composite.py` — REV-w4 lift then FWD-w4 drop composite (the involution result)
