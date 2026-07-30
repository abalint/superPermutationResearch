# Handoff: the s28 front → now the s29 front

**Updated end of s28b (2026-07-29).** Items 1 (surgery design) and 2
(per-allocation M2 pass) are DONE, and instrument I1 is BUILT and swept —
read JOURNAL s28/s28b and `docs/SURGERY-DESIGN.md` (§8 has the build
outcomes: tie oracle passed across an allocation boundary; NEW law — all
22,062 classes block-order-optimal at anchors ≥ 585 and ≥ 520). The s29
front is now split across TWO agent roles: long runs (anchor-450 sweep,
tie census) live in `docs/SWEEP-QUEUE.md` and are executed/monitored by
an operator agent per `docs/OPS-BACKGROUND-AGENT.md`; iteration (I2
design pass, ip=1 study, per-allocation NRPA/beam over
`data/frontiers_s28/`) continues in parallel per
`docs/RESEARCH-AGENT-S29.md`. Fresh agents: read the doc for YOUR role.
Items below kept for the traps section, which still applies verbatim.

Written at the end of s27b (2026-07-29) for a fresh agent. Read
`docs/JOURNAL.md` s27/s27b first; this note only adds the entry points and
the traps. `CLAUDE.md` has the reading order, commands, and hard invariants.

## Where things stand, in five sentences

Every known n=6 872 (22,062 community classes) lives in one of **8
specimen-backed L0 allocations**, and s27 shipped per-allocation grammars
(caps + census profile files) that replay the ENTIRE corpus 719/719 —
plus a new corpus law (`--fresh-doors`: heavy doors only ever open
untouched cycles, 66,999/66,999). An 871 must live in an open waste-146
allocation, and every anchor is ONE unit edit away from one (13 distance-1
targets; all have their certificate-grammar subregion closed, so the 871
there is out-of-grammar — consistent with s19). The blocked zone is still
the blocked zone: beam (s23), policy (s25), and exhaustive DFS (s26) all
fail through midgame levels ~60–450, and the extra doors of the non-records
allocations sit exactly there. The community corpus is splice-closed
(s26b), so nothing new comes from recombining known walks verbatim —
the remaining move is **surgery**: cycle-level edits that change a walk's
allocation. The M3 gate is now `analysis/counting/m3_check.py` — every
candidate ≤872 must pass it (exit 2 = novel) before any claim.

## The four s28 items, with entry points

1. **Cross-class surgery design (the flagship — design doc BEFORE code,
   Andrew's standing directive).** Question: what does a real 872 look
   like around a door edit? The 470-class (143,5) allocation pays for 2
   extra midgame w3 doors vs the records class; diff pairs across
   allocations at the walk level. Inputs that already exist:
   `analysis/counting/upstream872_door_pricing.tsv` (every door event:
   depth, exit-part, freshness), `src/recomb.rs::Braid` (scales to the
   full corpus, 16 s), `data/upstream872/` (local archive; regenerate via
   `analysis/counting/upstream872_dump.py` if missing). Open design
   choice: braid-diff cross-allocation pairs (do (143,5) and (145,3)
   walks even share states?) vs door-site excision + capped-beam repair
   (s26 killed NEAR-MISS repair for same-allocation pairs — symdiff
   bimodal 0/≥20 — but cross-allocation repair around a KNOWN door site
   is a different, untested question).
2. **Per-allocation M2 pass (cheap, unblocked).** Exact d=6 exhaustion +
   frontier dumps for the 6 untested allocations, with `--fresh-doors`:
   `cargo run --release -- sojourn-dfs -n 6 --class <S,d3,d4,d5,ip>
   --profile-file analysis/trackb/profiles/a<...>.txt --depth 6 --dedup
   exact --fresh-doors --max-nodes 60000000 --dump-frontier f.tsv
   --dump-per-class 16`. (145,3) and (143,5) are measured (JOURNAL s27);
   expect ~20–30 s each at d=6. Then per-allocation NRPA warm-starts
   (specimens in `data/upstream872_specimens/`) and seeded beams.
3. **The ip=1 targets.** (135,9,1,0,1), (138,8,0,0,1), (140,6,0,0,1) are
   871-capable, 2 edits from w4-bearing anchors, and OUTSIDE the
   s11-closed subregion — but no known 872 uses a priced skip (i2 never
   fires corpus-wide). Study what ip=1 walks look like: ε-rollouts are
   the only exercisers (`rollouts --strings`, then
   `analysis/trackb/verify_identity.py`); sojourn-dfs accepts these caps
   directly (no profile file exists — start with `--records-profile`-less
   runs or derive a profile hypothesis from the anchor's).
4. **Track hygiene, already done — don't redo:** M3 gate re-scoped
   (s27b), corpus census (s26c), splice closure (s26b), profile
   validation (s27).

## Traps a fresh agent will hit

- **Sample-bias ghosts.** Any note phrased "all known 872s ..." that
  predates s26c was calibrated on a 1.3% sample. The corrected picture is
  ONLY in JOURNAL s26b/s26c/s27 and the census TSVs. When in doubt,
  recount against `data/upstream872/` (or the committed TSVs).
- **`--fresh-doors` and the profiles are CALIBRATED, not proven.** Any
  exhaustion/impossibility claim made with them must say "within the
  corpus-calibrated grammar". Lossless claims need them OFF.
- **`data/upstream872/` is gitignored** (22,062 files, local). If absent:
  `analysis/counting/upstream872_dump.py` rebuilds it from a sparse clone
  of github.com/superpermutators/superperm. The committed artifacts
  (`upstream872_structure.tsv`, `upstream872_alloc_profiles.tsv`,
  `upstream872_door_pricing.tsv`, `upstream872_canon_index.tsv`,
  `data/upstream872_specimens/`) cover most analyses without it.
- **Cap-at-target starves NRPA** (twice-measured): hunt at `--max-len
  874 --collect 872`, never cap 872.
- **The launch protocol is a hard rule** (docs/OPERATIONS.md): anything
  >~30 min needs Andrew's go-ahead, a stated runtime/product/abort, and a
  heartbeat. The farm (`ssh transcribe`) is idle; read OPERATIONS.md
  before touching it.
- **Any candidate ≤872 goes through `python3
  analysis/counting/m3_check.py <file>` (exit 2 = novel) AND `cargo run
  --release -- validate -n 6 --file <f> --complete` before being
  believed.** Records are self-certifying; excitement is not.

## Session-end ritual

Append a dated JOURNAL entry (what was done/measured/surprised/next),
update README results if lengths changed, keep `cargo test --release`
green (115 tests) and clippy `-D warnings` clean, commit, push. Update or
delete THIS file when the s28 front moves.
