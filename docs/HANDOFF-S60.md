# Handoff — the s61+ front (fresh agent, start here)

Supersedes `HANDOFF-S59.md` (read it second — its state holds except
where amended below; S57 for the a(6)=872 theorem and expressibility,
S56 for P1a/slack-tax detail). Read JOURNAL s60 first. The active
design doc is **`docs/NOVELTY-DESIGN.md`** — as of s60 it is
self-contained again: the three s57/s59 corrections (pool-precision
milestone retired, prefix milestone refuted, QS-B curve replacing the
~100/s scalar) are folded into §6.0/§6.1/§6.4 in the text proper.

## What changed in s60 (in five sentences)

1. **Prefix RETRIEVAL is closed as a verified negative**
   (`out/s60/retrieval/REPORT.md`): zero strict conjugacies — no
   element of G = S₇×{1,rev} (10,080, exhaustive) maps the group0
   chain onto #0/#24 (positive control correctly returns 2) — and the
   relaxed whole-cover-into-instance census is provably uninformative:
   the 85 refuted census chains outscore the 138 open ones on median,
   and #0's rank-1 near-miss (112/114 mapped rows) dies exactly, on
   10 residual columns with ZERO candidate rows in the whole instance.
2. With pool guessing (s57), prefix guessing (s59), and prefix lookup
   (s60) all dead, **the #0/#24 front is row-shrink ONLY** — and s60
   resolved the row-shrink fork too.
3. **The no-good harvest is BUILT, SOUND, and REUSABILITY-NEGATIVE**
   (`out/s60/nogood/REPORT.md`): 269 minimized cuts, 100%
   re-confirmed, 0 violations against the 131 known covers — but
   prefix refutations minimize to ~8 rows and an 8-row cut fires on
   0 of 3,599 fresh prefixes (P ≈ 2.6e-16; ~10¹⁵ cuts for a 50% hit
   rate), so the full 20.8 core-hour harvest is recommended AGAINST
   as specified; **the pairwise cut store is the only surviving
   #0/#24 tool** (size-2 cuts: ~4.4e3 suffice, consumable as instance
   reductions).
4. Reusable assets from the negatives: `out/s60/retrieval/symlib.py`
   (validated G-action; 0.1 s "is this chain equivalent to one
   already refuted?" test) and `out/s60/nogood/cutlib.py`/`confirm.py`
   (cut semantics + the mandatory ≥10×-cap re-confirmation harness
   for the pairwise store).
5. SWEEP-QUEUE now holds **four** pending `approved: NO` entries:
   pairwise cut store (~9 core-h farm, s60-annotated with build
   notes), A0 gate re-run (~90 min LOCAL, spec complete — the last
   uncorrected 15 s artifact), QS-B full verdict-mix map (~2.5
   core-h farm), Σ15–16 extended census (~2.7 core-h farm); plus the
   full no-good harvest entry that recommends against itself.

## The work menu (s61, priority order)

1. **Andrew's queue calls** — sharpened by s60: the pairwise cut
   store is now the only #0/#24 tool; the A0 re-run unblocks citing
   the s56 baseline. Launches belong to Andrew's launch agent.
2. **Near-miss residual anatomy** (retrieval REPORT §8, cheap,
   pencil-first): on every chain, open and refuted alike, the best
   relabeled-cover packing dies on a residual with 0–1 candidate
   rows. If that has a proof behind it, it may be a new sound pruning
   rule; if not, it is a fact about the row geometry worth stating.
3. **j-tax closure** (unchanged from S56 menu item 3): n=5 cap-154
   exhaustive (queued), n=6 midgame probe design, the 868→872 gap.
4. **Grammar writeup / outreach** (Grayzel, Gheorghe, Kristan) —
   Andrew's calls.

## Traps (s60 additions; S59's list applies in full)

- **Cap-boundary cuts:** greedy minimization drives every no-good to
  the cap boundary by construction — re-running at the harvest cap is
  a coin flip (11/60 first-pass failures in the pilot). Any minimized
  cut must be re-confirmed in a fresh process at ≥10× the probe cap
  before storing (`confirm.py`; `confirmed_*.jsonl` carries each
  cut's own exhaustion time — `refute_s` in `cuts_*.jsonl` is the
  PARENT's time, a naming trap).
- **Row-signature retrieval is vacuous by transitivity:** G acts
  transitively on the 5,040-row universe, so "∃g: g(r)=r′" is always
  true. Only per-g joint statistics (whole-cover concentration under
  ONE symmetry) carry information — and even those rank coverless
  chains above open ones. Do not resurrect retrieval with a fancier
  signature.
- **A packing near-miss is not evidence:** 112/114 mapped rows with
  an exactly-UNSAT residual is the TYPICAL shape on refuted chains
  too. Never cite L1-census concentration as progress on #0/#24.
- The s60 cuts for #0/#24 are relative to s57's pruned instances
  (soundness inherited from s57, not re-audited); the control cuts
  are unconditional (raw instance).
- The A0 "0/6" remains uncitable until the queued re-run happens
  (S59 trap, still live).

## Key artifacts (regenerable, uncommitted)

- `out/s60/retrieval/` — symlib.py + 7 probe scripts, npz censuses
  (10,080 × 131 per target), sweep.tsv (223 chains), REPORT.md
  (orchestrator-filed; full re-run ≈ 24 s).
- `out/s60/nogood/` — cutlib.py, harvest.py, confirm.py + 5 audit
  scripts, cut stores (`confirmed_*.jsonl` = the usable ones),
  LEDGER.txt, REPORT.md (orchestrator-filed; §6 = the projection the
  queue entry cites).
- `out/s59/prefix/`, `out/s59/cliff/`, `out/s57/proposer/` — still
  the reference implementations (dlxrun.py remains the mandatory
  runner; prefixlib.py is imported by both s60 pilots).
- On the farm PC: Grayzel run `D:\superpermFarm\grayzel\runs\g3`
  (copy home before any farm cleanup) — unchanged from S59.

## Reading order for a cold start

1. This file.
2. `docs/JOURNAL.md` s60, s59, s58, s57; `docs/HANDOFF-S59.md` for
   what it carries from s57/s56.
3. `out/s60/retrieval/REPORT.md` and `out/s60/nogood/REPORT.md` (the
   two current primary sources), then `out/s59/prefix/REPORT.md` §6/§9
   and `out/s59/cliff/REPORT.md`.
4. `docs/NOVELTY-DESIGN.md` (now self-contained), `docs/ROADMAP.md`
   (the 2026-07-31 dated section).
5. `docs/SWEEP-QUEUE.md` (four pending `approved: NO` entries),
   `docs/THEORY.md` §7, `docs/OPS-BACKGROUND-AGENT.md`, `CLAUDE.md`.

Session end ritual unchanged: JOURNAL entry, `cargo test --release`
green (139), clippy `-D warnings`, fmt, commit → `git pull --rebase`
→ push. When this goes stale, write the successor and repoint
CLAUDE.md + agent docs.
