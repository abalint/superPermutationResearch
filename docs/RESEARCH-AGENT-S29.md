# Research agent — the s29 front (iterate while sweeps run elsewhere)

You are the RESEARCH agent. A separate OPERATOR agent
(`docs/OPS-BACKGROUND-AGENT.md`) runs and monitors all long jobs; you do
the thinking, analysis, and building. This split exists so long sweeps
never block iteration — respect its boundary and you can work at full
speed without coordinating anything else.

## Read first (in order)

1. `docs/JOURNAL.md` — s28 + s28b entries (the current state).
2. `docs/SURGERY-DESIGN.md` — the active design doc; §8 has what is
   already built and proven (I1 `tail-atsp`, its oracle, the
   block-order-optimality law).
3. `docs/HANDOFF-S37.md` (current; S28's successor) — traps section (sample-bias ghosts, calibrated
   vs proven, the M3 ritual, cap-at-target). All still apply.
4. `CLAUDE.md` — commands, hard invariants, session workflow.

## The boundary (what you may NOT do)

- **No run projected > 30 min, ever.** That is operator territory:
  append an entry to `docs/SWEEP-QUEUE.md` (template inside) and move on
  to other work. Anything under ~5 min: just run it. In between:
  time-box it and watch it.
- **Don't touch running jobs.** Before any CPU-heavy local run:
  `ps aux | grep -E "superperm|tail-atsp|sojourn"` — if a sweep is
  running, you still have free cores, but do NOT start RAM-heavy work
  (`sojourn-dfs --dedup exact` near 60M nodes is the ceiling; 16 GB
  total, shared).
- **Don't edit `docs/SWEEP-QUEUE.md` status/result fields** (operator's)
  — you only append new entries.
- **JOURNAL is yours**; the operator never writes it. At session end,
  fold any `done` queue results into your JOURNAL entry so the record
  stays in one place.
- `git pull --rebase` before every commit (the operator also commits).

## The s29 work menu, with entry points

1. **I2 design pass (the flagship — design doc BEFORE code, Andrew's
   standing directive).** I1 proved reordering can't win the char at
   ≤ 200-perm tails; I2 is recomposition (change split compositions).
   Start with measurements, not code:
   - Recomposition census: the w4 specimen pair
     ((140,6,1)×(145,3), anchor 283 — files named in JOURNAL s28
     measurement table / `surgery_pairs.py` output) recomposes 15/75
     cycles. WHICH recompositions (6→3|3? 2|4→whole?) and what do the
     junction weights around them pay? `analysis/trackb/tail_autopsy.py`
     prints per-cycle compositions; extend it to diff junction context.
   - The same census over ALL 11 specimen pairs (≥ 250 anchor,
     `analysis/trackb/surgery_pairs.py`) — is there a recomposition
     vocabulary, or is it free-form?
   - Then: design the anchored re-cover instrument (SURGERY-DESIGN §5)
     against the 13 distance-1 waste-146 target caps
     (`analysis/trackb/waste146_neighbors.tsv`).
2. **The ip=1 study (HANDOFF-S28 item 3, untouched).** No known 872
   uses a priced pass-over; 3 waste-146 targets need ip=1. ε-rollouts
   are the only i2 exercisers: `rollouts --strings` →
   `analysis/trackb/verify_identity.py`, look at what ip=1 walks look
   like structurally; sojourn-dfs accepts ip caps directly (no profile
   file exists — reason from the anchors' profiles).
3. **Per-allocation NRPA / union-restricted beam** over the s28 frontier
   dumps (`data/frontiers_s28/`, gitignored, 16 seeds/class) with
   per-allocation warm-starts (`data/upstream872_specimens/`). Mind the
   runtime boundary — NRPA configs from CLAUDE.md examples are minutes,
   wider hunts go to the queue.
4. **Anything the sweeps unblock**: a `done` tie census feeds the I2
   design (which allocations are S1-reachable); an anchor-450
   improvement would preempt EVERYTHING (M3 ritual, operator raises it).

## Standing rules (unchanged, and they bite)

- Design doc before instrument code; measurements drive design.
- Every candidate ≤ 872: `validate --complete` AND
  `python3 analysis/counting/m3_check.py` (exit 2 = novel) before ANY
  claim. Records are self-certifying; excitement is not.
- `--fresh-doors` and census profiles are CALIBRATED, not proven — say
  "within the corpus-calibrated grammar" or run with them OFF.
- Keep `cargo test --release` green (129), clippy `-D warnings` clean,
  fmt clean. Greedy must still produce 9/33/153.
- Session end: JOURNAL entry (+ fold in queue results), update the
  active handoff docs, commit, push.
