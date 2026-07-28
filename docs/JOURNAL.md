# Lab journal

Newest entry first. Every working session appends an entry: what was done, what was
measured, what surprised us, what's next. This file is the "pick up where we left off"
mechanism — read it before touching code.

---

## 2026-07-28 (session 17b, overnight continuation) — census jumps 41 → **85/223 closed**: 52 chains are STRUCTURALLY uncoverable (zero-candidate column) and the farm's SAT pass missed 44 of them; merged multi-engine ledger committed; DLX sweep re-aimed at the 138 survivors

Overnight continuation of s17's Track C session, after s18's pass-1 census
landed. The local dlx7g sweep's first 37 chains held a surprise: 3 "UNSAT in
under a second" verdicts (chains 34/37/41, K=30) on chains the farm's CaDiCaL
ran 30 minutes on and left undecided. Investigation: those instances each have
a **zero-candidate column** in the canonical formulation
(`chain7.build_instance_from_chain`) — no rows can cover one orbit, so no cover
exists, unconditionally. That is s13's structural-refutation mechanism; the
farm worklist evidently never got the prefilter.

**Running the structural test over all 223 worklist chains: 52 are structurally
uncoverable** (14 × K=30, 38 × K=31; indices in
`analysis/cover7/results_n7_merged.csv`), of which **44 are new closures**
beyond CaDiCaL's 41. Merged census (`analysis/trackc/census_merge.py`, output
`analysis/cover7/results_n7_merged.csv`, precedence STRUCTURAL > UNSAT > OPEN,
any SAT surfaced loudly): **STRUCTURAL 52 + UNSAT 33 = 85/223 closed; 138 OPEN**
(5 × K=27, 19 × K=29, 30 × K=30, 84 × K=31).

**Discrepancy flagged, worth a look**: an exactly-one SAT constraint over an
empty candidate set should be instantly UNSAT, yet satworker's CaDiCaL runs
burned 30 min on structurally-dead chains. Either satworker builds its instance
by a different (more liberal) rule than `chain7` — in which case its verdicts
describe a different formulation and the encodings should be reconciled — or
its encoder skips empty columns. Next farm session should check
`satworker.py`'s instance construction against `chain7` on chain 34 before
trusting pass-2 budgets. (The structural closures themselves do not depend on
this: they are proved in the canonical formulation that all our ledger claims
use.)

**Engine-agreement datum**: within the 37 chains both engines attempted, zero
dominance either way — DLX never closed a non-structural chain CaDiCaL
couldn't, and never timed out where CaDiCaL succeeded. The two encodings
appear to hit the same wall, which sharpens s18's conclusion: the 138
survivors need a different *method* (symmetry reduction, Track C v2 column
learning, better encodings), not more budget.

**Local sweep re-aimed**: now iterating exactly the 138 open chains
(worklist mode in `census_sweep.sh`), 10-min caps (decidable chains die in
minutes — median 1.85 min in pass 1), 4 nice'd workers, resumable CSV at
`analysis/trackc/runs/census/results.csv`. Any exit-0 SAT is flagged for
validation, never auto-believed. Expected yield is modest; the point is that
no open chain goes un-attempted by the second engine family.

**Next session:** (1) tally the finished DLX sweep + rerun `census_merge.py`,
commit the updated merged CSV; (2) reconcile satworker's encoding with
`chain7` (chain 34 is the 1-second test case); (3) Track C v2 (learned column
choice) per `analysis/trackc/RESULTS-s17.md`; (4) pass 2 on the 138 survivors
should lead with symmetry reduction, the one method that ever worked at n=7.

## 2026-07-28 (session 18) — n=7 refutation pass 1 COMPLETE: 223/223 chains attempted, **41 unconditionally refuted**, 182 undecided at the 30-min budget, no SAT

The PC farm finished its first full sweep of the V₇=15 census. Ledger committed
as `analysis/cover7/results_n7_pass1.csv` (223 rows: timestamp, index, pattern,
K, Σ, engine, outcome, best_partial, minutes, pid, word_file).

| K | UNSAT / attempted | decided |
|---|---|---|
| 27 | 0 / 5 | 0% |
| 29 | 2 / 21 | 10% |
| 30 | 6 / 48 | 12% |
| 31 | **33 / 149** | 22% |
| **all** | **41 / 223** | **18%** |

**No SAT** — no candidate 5905 word from any chain.

**What the 41 are worth.** Each is an unconditional refutation: CaDiCaL UNSAT at
0 cuts over the exact-cover encoding, with **no symmetry assumption**, so it
rules out *every* cover of that chain — asymmetric ones included. That is
strictly stronger than the published negatives in this area, which come from
symmetry-reduced searches (Egan's 2SYMM route). And the column is
cross-validated: s16's patched PermutationChains, an independent engine on an
independent encoding, agreed with our verdicts on 6/6 chains sampled.

**Solve-time structure — decisive for pass 2.** UNSAT times: min 0.02, median
**1.85**, max 32.17 minutes; **25 of 41 landed under 5 minutes**. So decidable
chains are overwhelmingly *fast*, and the 182 timeouts are not "nearly done" —
they are qualitatively harder, not marginally slower. Raising the budget alone
will therefore yield little: a 4× budget would likely convert only the handful
near the 30-min boundary. Difficulty also tracks K inversely (K=31 decides 22%
of the time, K=27 zero of five) — consistent with lower-K chains having more row
freedom and hence bigger search spaces.

**Reading.** Pass 1 closes 18% of the penalty-≤16 space at n=7 unconditionally.
The remaining 182 need a better method, not more minutes — exactly the gap
Track C v1 identified from the other direction (s17: guided row ordering is a
22× win at n=6 but a NO-GO on the n=7 cover gates; the open lever is learned
*column* choice). Two engines, two sessions, same conclusion: n=7 cover decision
needs a structural improvement, not more compute.

**Next:** (1) pass 2 aimed at *method*, not budget — learned column choice
(Track C v2), symmetry-reduced encodings where chains admit them, or s17's
`dlx7g` as a third opinion on the survivors; (2) the 41 refutations plus s11's
n=6 theorem are enough to draft the write-up; (3) send the s16 fopen/`FILE*`
patch upstream to Egan.

## 2026-07-27 (session 17) — Track C v1 built end-to-end and gated: learned row ordering inside DLX works (22× on n=6) but does NOT crack the n=7 cover instances at 60 min; row order proven irrelevant to UNSAT under MRV; a local DLX census sweep opened as a third refutation engine

Track C (the thesis — learned evaluator inside the cover search) went from zero
code to a fully gated v1 in one session. Spec: **`docs/TRACKC-DESIGN.md`**
(locked 8-feature vector, pre-`cover(c)` timing, holdout design); results:
**`analysis/trackc/RESULTS-s17.md`**; code: `analysis/trackc/` (instances.py,
replay.py, `dlx7g.c`, solve_guided.py, census_sweep.sh), `ml/fit_cover_rank.py`,
models `ml/models/trackc_model{A,B,N6}.*`. Built by parallel subagents against
the locked spec; every cross-language boundary gated.

**What was built (all gates green):**
- **Corpus**: 296/296 n=6 record words extract to certificates and replay
  (`extract_certificate` → map to `gain1.build_instance(6)` rows →
  `check_cover`), plus 3/3 5907 and 11/11 5906 certs → **9,150 teacher-forced
  decisions / 21,423 (pos, neg) sibling pairs** over 12 exported instances
  (`data/trackc/instances/`, incl. the 5 open K=27 chains).
- **Engine**: `dlx7g` — guided descendant of the farm's C DLX: variable child
  count (n=6 and n=7 instances), incremental `grounded[]`/`pending[]` forest
  features on the undo trail, `--weights` linear row ordering, ε-restart
  diversification, `--dump-features` parity mode. **Python↔C feature parity is
  byte-clean** (the one boundary that could silently poison everything).
- **Trainer**: numpy pairwise RankNet (s8 architecture), standardization folded
  into exported weights; two honest holdout models (A: n6+5906, gates on 5907;
  B: n6+5907, gates on the 5906 K=18 chain).

**The positive result: the mechanism works.** On the n=6 standard instance
(known-SAT), learned ordering cuts nodes-to-first-cover **21,627 → 961 (22.5×,
model B)**. And cross-n transfer is real: a model trained ONLY on n=6 ranks
n=7 cover rows at 0.746 pair accuracy (chance 0.51). The certificate-level
features do carry structure across n — the thing item 3's walk-level features
never did.

**The honest negative: G1/G1b NO-GO.** On the two held-out known-SAT n=7 gates
(standard K=5, 690×4440, R=138; and the real 5906's K=18 chain, R=124), guided
and blind alike: 6/6 TIMEOUT at 60 min, max depth ~112/138 and ~98/124,
depth differences noise-level, ~600–790M nodes per run. Top-1 ≈ 0.62–0.68 per
node compounds to ~0 over a 138-deep all-correct descent — a static linear
ranker over local features cannot bridge the n=7 plateau. Per the design's
gate criteria the K=27 record attack (G3) was NOT triggered.

**A structural theorem-lite from G2**: with the column rule fixed (MRV), row
ordering permutes the DFS but the exhaustion tree is the *same node set* —
verified byte-identical node counts (60,037,516 and 8,548,527) blind vs guided
on two refuted chains. Row ordering is purely a time-to-first-solution lever;
**UNSAT economy needs learned COLUMN choice** — the top v2 lever.

**Bonus, possibly the sleeper result: dlx7g is a fast third refutation
engine.** It exhausted farm chain 5 (K=29) in 8 min and chain 26 (K=30) in
64 s locally — fresh independent confirmations of the CaDiCaL+Egan verdicts,
DLX encoding, third engine family. A **local census sweep** over the 218
unclaimed-by-us worklist chains is now running (`census_sweep.sh`, 4 workers,
30-min caps, resumable, results → `analysis/trackc/runs/census/results.csv`;
any exit-0 SAT candidate is flagged for validation, never auto-believed).
Check it before starting new compute on this machine.

**v2 levers recorded in RESULTS-s17.md**: (1) learned column choice, (2)
dead-end mining (off-path training), (3) value-based restarts, (4) CDCL
phase/branching biasing from the same model, (5) MLP. Dead v1 features:
`min_child_sz_log` (zero within-node variance under MRV — the chosen column is
everyone's child and the global min); `grounds_pending` weak-negative in
teacher-forced data.

**Next session:** (1) read `analysis/trackc/runs/census/results.csv` — the
sweep verdict tally (UNSATs close census chains; cross-check against the
remote farm's ledger); (2) Track C v2: learned column choice is the highest-EV
lever, dead-end mining second; (3) the farm patch upstream to Egan (s16)
remains unsent.

## 2026-07-27 (session 16) — two real upstream bugs found and patched in PermutationChains (not a stack overrun at all); the refutation census is now CROSS-VALIDATED by an independent engine (6/6 agree); one earlier claim retracted

**Root cause of the broken Windows build — two genuine defects in
`PermutationChains.c`, both invisible on macOS** (patch + upstream write-up:
`analysis/cover7/PermutationChains-fopen-fix.patch`, 3 lines):

1. **Invalid `fopen` mode strings `"wa"` / `"aa"`** (3 sites). BSD libc reads
   only the leading character and ignores the rest, so macOS behaves as
   intended. The Microsoft UCRT validates the whole string, trips the
   invalid-parameter handler, and calls `__fastfail(FAST_FAIL_INVALID_ARG)` —
   which raises **0xC0000409, the same status as a `/GS` stack-cookie
   failure**. That is why it misreported as a stack overrun and why `/Od`,
   `/GS-` and larger stacks all changed nothing. Reduced 12-line repro on the
   PC reproduces 0xC0000409 exactly under `cl /O2`. (glibc/mingw are a third
   case: they return NULL and the program exits via its own error path.)
2. **A dropped assignment**: the second `fopen`'s result is discarded, so `f`
   still points at the twoCycles stream `fclose`d three lines earlier ⇒ the
   NULL check tests the wrong pointer, `printSuperPerm` writes to a closed
   `FILE*`, `fclose` double-closes, and the real stream leaks once per solution
   (42,288 times at n=6). Undefined behaviour, masked on macOS only because BSD
   libc recycles the `FILE` slot and hands the stale pointer the new file.

With the patch, **native MSVC builds and works** (mingw-w64 too; the two
binaries are byte-identical in output). Gate on Windows: `5` → **6**,
`5 nsk444` → **6**, `6 ffc` → **36** (Egan's documented number), all exit 0 with
solution files written. The full `6` → 42,288 counts are still grinding
(~7.7k/42,288 at last look) — not a defect: F: does **48 ms per file
open/close** and Egan reopens two files per solution. Verdict any time via
`F:\superpermFarm\gate6verdict.ps1`. ASan/UBSan were unusable (sanitized
binaries hang in dyld init on this macOS) and could not have caught defect 2
anyway — `FILE` is not malloc-tracked.

**The result that matters: our refutation census is independently
cross-validated. 6 of 6 chains agree, 0 disagreements.** Egan's plain mode is a
complete DFS with sound pruning, so it is a true independent oracle for our
CaDiCaL UNSATs: chains 5, 25 (K=29) and 26, 43 (K=30) exhausted with 0
solutions, exit 0; chains 33, 35 (K=30) were rejected as structurally unviable
before search. Windows and macOS traces are byte-identical bar one
`sizeof(long)` line. Two independent engines, two independent encodings, same
verdicts — the UNSAT column of `results.csv` can be trusted.

**RETRACTION (s13 NOTES).** "PermutationChains asym coverFirst on chain 0: DXL
reached minColsLeft=0 — EXACT COVERS OF CHAIN 0 EXIST … process then died
silently" is **wrong on both counts**. `coverFirst` does not crash: chain 0
completes with exit 0 and zero solutions. And `minColsLeft=0` refers to the
cover-first *reduced* subproblem at depth 93, not a 141-size cover. There is no
evidence that chain 0 has a cover.

**Farm state:** 27 CaDiCaL workers, 60/223 claimed, ledger 6 UNSAT + 27
TIMEOUT-KILLED. Roughly 80% of chains exceed the 30-minute budget, so the first
pass will be a partial census; the sensible follow-up is a longer-budget second
pass over the survivors, or a better encoding.

**Next session:** (1) `results.csv` census tally; (2) send the patch upstream to
Egan — it is a live defect for anyone building his code on Windows; (3) Track C
(learned ordering) remains the one lever aimed at the instances both engines
time out on.

## 2026-07-27 (session 15) — the positive control paid for itself: the Windows PermutationChains binary was BROKEN (all its farm output void); no engine can *find* a known cover; farm re-aimed as a validated refutation engine (first real UNSATs)

A correctness session. Everything here follows from insisting on a positive
control before believing a negative.

**The control failed, then the binary failed.** Pointing the farm's engine at the
standard K=5 kernel — which provably HAS covers (the known 5907s are built from
it; our ledger's 143 = 138 rows + 5 loops matched exactly) — it ran 9 minutes,
reached PCsolSize 121/143 and exited empty. Chasing that, the agent ran Egan's
own smoke tests: **`PermutationChains.exe 5` and `6` exit `0xC0000409`
(STATUS_STACK_BUFFER_OVERRUN) with zero solution files**, under `/O2`, `/Od`, and
`/O2 /GS-` alike, while the identical source under clang on the Mac gives the
correct 6 and 42,288 solutions. ⇒ **Every chain that farm ever reported as
"finished" is void — those chains were never searched.** (This also retro-
explains s14's "orderly exits" and the Mac's mid-line truncations: a latent
memory bug, caught by MSVC's stack cookie, tolerated by clang.) The
PermutationChains farm was stopped.

**What the modes actually are** (source-read, for the record): `searchPC` (plain)
IS a complete DFS with only sound pruning — so an exhaust *would* be a genuine
refutation, if the binary worked. `trackPartial` is print-only. `coverFirst` is a
DLX pre-pass. `stabiliser/limStab/symmPairs/littleGroup/blocks/fullSymm` are
symmetry reductions. **Egan's n=7 recipe was `7 fullSymm limStab ffc`** — a
4-cycle kernel *plus symmetry* (762 solutions, ~30 min); he never claims plain
mode completes at n=7. The `nsk` path was verified faithful (`nsk444` ≡ default
at n=5 → 6 solutions; `nsk5555` ≡ default at n=6 → 42,288).

**The hard, honest negative: nothing we have can FIND a cover.** Control gate on
two known-SAT instances (standard K=5; the real 5906's K=18 chain), three
engines — CaDiCaL, Python DLX, C DLX — **none found a cover in > 45 min each**.
The 5907/5906 words this project "compiled and validated" in s13 were
**reconstructed from published words, not discovered**; that claim is corrected
here. These instances are simply hard, and Egan needed symmetry reduction to
crack them at all.

**Farm re-aimed as a refutation engine.** `satworker.py` (CaDiCaL over the
exact-cover encoding) runs because its **UNSAT direction is validated** (K=29
chain UNSAT in 33 s CaDiCaL / 49 s kissat, at 0 cuts = unconditional), and any
SAT would be auto-compiled and validated before being believed. 27 workers,
**30-min per-chain budget** (fixes s14's permanent queue stall — 193 of 218
chains had never started), atomic `O_CREAT|O_EXCL` claims, write-once row files
rebuilt into `F:\superpermFarm\results.csv`. Worklist 223 (5 K=27 first).
**First real outcomes: 3 UNSAT** (0.11–1.96 min each), 30/223 claimed.

**Reading.** The farm's realistic product is now a *census of refutations*
narrowing where a 5905 could hide — not a record. Combined with s11's n=6
theorem, the shape of a paper is "Egan−1 is optimal in the gain-one class at
n=6, and here is how much of the n=7 penalty-≤16 space is closed." The record
itself, if it is reachable at all, needs the search to get smarter — symmetry
reduction (Egan's own lever) or Track C's learned ordering — not more cores.

**Next session:** (1) read `results.csv` — how much of the 223 is closed; (2)
consider a symmetry-reduced encoding (the one lever known to work at n=7); (3)
Track C / Track B remain the research lines.

## 2026-07-27 (session 14) — the search moved to a 28-core PC (27 workers, 96% CPU, survives disconnect); two "crash" diagnoses refuted; the real open question is whether an orderly finish REFUTES a chain

Infrastructure session, plus one reinterpretation that may matter more than the
compute. Operating runbook: **`analysis/cover7/REMOTE-FARM.md`**; scripts:
**`analysis/farm/`**. Both are written for an agent with no memory of this work.

**The farm moved off the laptop.** Windows PC (`ssh transcribe`, 28 cores, 48 GB,
standard user, **not** admin). Everything lives on `F:\superpermFarm`; C: is
nearly full and `F:\audioPrime` (a separate production app) is off-limits.
Persistence was the whole problem: Windows OpenSSH kills its session's process
tree, WMI process creation is denied, and `schtasks` can only register
"Interactive only" tasks without stored credentials. Solved as a plain user with
**`detach.exe`** (`analysis/farm/detach.c`) — `CreateProcess` with
`CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP |
BELOW_NORMAL_PRIORITY_CLASS`, opening its own log handles and restricting
inheritance to exactly those three (otherwise the child inherits sshd's pipes and
every ssh call hangs). Verified by a marker process surviving a full disconnect.
An optional admin installer (SYSTEM tasks, `/sc ONSTART`, for reboot survival)
exists but was deliberately **not** run — more privilege than the job needs.

**Scaled to 27 workers / 96.2% CPU** (`farmscale.ps1`, backfilling scheduler
against a 218-pattern worklist, K=29 → K=30 → K=31; the 5 K=27 chains run
untouched at top priority). RAM is not the binding resource: 4.4 MB peak per
worker against 37 GB free, so cores bind (cap arithmetic and a 15%-free valve
are in the script anyway). `watchdog.ps1` does one backfill pass per call and
logs free RAM; it is called from the Mac, not scheduled (non-admin).
**Validation gate passed before any launch**: `gen_worklist.py` derives the
KernelFinder `nsk` patterns from the census (ride length `((j−k) mod 6)+1`) and
refuses to emit a worklist unless it reproduces the five known K=27 strings
exactly. Nuance found there: the published tier counts (5/21/48/149) only
reproduce if the **terminal loop is allowed a partial ride** — with a forced full
terminal ride the census is 5/21/40/141.

**Two "crash" diagnoses refuted by measurement, in sequence** (recorded so nobody
re-runs them): *stack overflow* — `searchPC`'s frame is 128 bytes over ~141
levels, peak stack under 100 KB; a 64 MB rebuild (`dumpbin`-verified) changed
nothing. *OOM* — 4.4 MB RSS against 37 GB free. What the logs actually show is an
**orderly exit**: a complete final line with trailing newline after the
`PCsolSize=…` best-partial dump, 0-byte stderr. Three K=29 chains "finished" in
~1 CPU-minute. (The mid-line truncation seen earlier on the *Mac* was genuine
memory pressure there — 13 solvers on a laptop — which is what sent the second
diagnosis down the wrong path.)

**THE OPEN QUESTION, and the session's real deliverable.** If the engine's plain
mode is exhaustive, then a chain finishing without a solution **refutes** it (no
rooted cover ⇒ no 5905 from that chain) — and the farm is a refutation engine
producing publishable negatives at ~1 CPU-minute per K=29 chain, which would
close large parts of the census fast. If the mode is bounded/heuristic, finishing
means only "this strategy gave up" and refutes nothing. **Positive control
launched** (`runs\ctrl`, standard K=5 kernel `nsk66666`, which provably HAS
covers — it is how the known 5907s were built): at last check it was climbing
normally (PCsolSize 121 of target 143). If it finds a cover, orderly completion
elsewhere is meaningful; if it also completes empty, every "finished" chain means
nothing. **Do not characterize any chain as refuted until this control returns.**

**Still no 5905.** Nothing about sessions 10–13's proven results changed.

**Next session:** (1) read the control's verdict first — it decides whether the
farm's finishes are refutations or noise, and hence what the whole campaign has
produced; (2) `watchdog.ps1` periodically to backfill; (3) if finishes ARE
refutations, tally which chains are eliminated and re-aim at the remaining
tiers + the pen ≥ 17 census; (4) Track C (learned ordering) and Track B (n=6
871 hunt) remain the unstarted research lines.

## 2026-07-27 (session 13) — record attempt round 1: no 5905 yet, but the formalization is proven record-capable (real 5906s parse as V₇=10 partial-ride certificates and recompile validated); 5904 closed at pen≤16; the open question reduced to concrete instances

One mega-thread (the cover agent; 2.4 h). Pipeline in **`analysis/cover7/`**;
engines were left running — check `pgrep -f "PermutationChains 7 nsk"`.

**The validation that matters most.** The actual 5906 record words exist on the
superpermutators GitHub (urdvr's tree never had them). Our
`extract_certificate` **accepts them as partial-ride certificates at exactly
V₇ = 10** — K=18/Σ=8, K=20/Σ=10, K=24/Σ=14 variants — precisely as the ledger
priced the 5906 sight unseen in s10, and the pipeline **recompiles a
cargo-validated 5906** from the extracted certificate. Positive controls also
rebuild the standard instance byte-identically and compile a validated 5907.
The formalization provably expresses record-class words end-to-end; nothing
about the framework is a toy.

**Census corrected and completed** (cross-validated against Egan's KernelFinder
after a diff caught 16 missed terminal-partial-ride chains): V₇=15 cost-3-only
= 5×K=27 / 21×K=29 / 48×K=30 / 149×K=31 (+1581 at K=32/33); **mixed-cost chains
don't exist at penalty ≤ 16**; V₇=20 = 4 chains.

**Search outcomes.** The wall is exact-cover existence, not rootedness (it
never engaged): all 4 V₇=20 chains structurally uncoverable ⇒ **5904 closed at
pen ≤ 16**; one K=29 chain proven UNSAT (CaDiCaL + kissat); 662 chains refuted
by zero-candidate columns; **all 8 palindromic K≤31 chains have no
2-fold-symmetric cover** — Egan's 2SYMM method (the only method that ever
produced a nonstandard n=7 record) provably cannot give 5905 from pen≤16
kernels. OPEN: the 5 K=27 chains (3 distinct up to reversal) and most K=30/31 —
CDCL/MILP/DLX stall for hours both ways; Egan's own engine gets deepest
(129/141 2-cycles) before a reproducible crash.

**Reading.** 5905 is neither found nor excluded — it now hinges on a handful of
named instances, and the failure mode (solvers stall, no refutation) means the
answer is genuinely hard, not obviously empty. This is also exactly the search
regime Track C was designed for (learned row/column ordering inside DLX at the
570-column scale where blind heuristics stall). Next moves recorded in
`analysis/cover7/README.md`: coverFirst crash fix, multi-day CDCL on the three
distinct K=27s (UNSATs would close Σ=12), the 916 open K=32/33, pen≥17 census,
cube-and-conquer on skipped-orbit columns.

## 2026-07-27 (session 12) — n=6 proof independently verified (clean-room Rust, all claims agree); n=7 campaign: V₇=15/20 kernels EXIST and are row-count-feasible — 5905/5904 now hinges on the rooted cover

Two threads, both landed. Sharing decision (Andrew): hold the n=6 result until
stronger confirmation (✅ this session) AND a positive finding to lead with —
the n=7 cover attempt (launched at session end) and Track B's 871 hunt are the
candidates.

**Thread 1 — clean-room verification: every claim AGREES (commit `f8603d3`).**
`src/cert.rs` (~900 lines + 8 tests) reimplements the n=6 kernel-chain proof
from the mathematical definitions alone — the agent was barred from reading the
Python campaign, extraDocs, and the result docs. `cert-verify -n 6` (1.4 s)
prints a per-claim verdict table: C1 forced map = permutation with 180 cycles
all length 4 ✓; C2 pivot confinement, entry-landing automatic ✓; C3 max V = 8
via exhaustive B&B (0.98 s, 15.8M nodes), exactly 12 chains, same (K,Σ,f4)
census ✓; C4 zero covers for all 12 — strengthened: no exact cover exists even
before rootedness — with the standard-kernel positive control finding a rooted
25-row cover ✓; C5 ledger ✓. `docs/RESULT-gain1-optimality-n6.md` upgraded to
"independently verified". Conventions worth remembering: door(s,5) = door(s,6)
identically at n=6; cost-6 strictly dominated.

**Thread 2 — n=7 max-V₇ campaign (`analysis/kernelchain7/`).** Gates: the three
known 5907s trace to standard-kernel certificates from raw strings (census
4182/853/4 — the kernel really is the K=5 standard chain, all three, up to
relabeling); the 5906 census prices to V₇=10 exactly. Structure: forced-map
period **5 = n−2** on all 5040 states (mirrors 4 = n−2 at n=6 — conjecture: the
forced period is n−2 generally, which would make the standard kernel the
skip-free maximum at every n); pivot confinement at all costs; **skip-1 lemma**
(720/720): skip-1 hops land on the preceding loop of their own forced 5-cycle,
so net-positive deviations cost ≥ 2 skip ⇒ **proven V₇ ≤ 74**, and the naive
signatures (K=18,Σ=3)/(K=24,Σ=4) are empty. Search (complete B&B infeasible at
n=7): **V₇ = 15 chains are plentiful** (100 enumerated; sample: K=27, Σ=12 =
standard-kernel prefix + six skip-2 deviations, R=114, 2662 eligible rows —
count-feasible); **V₇ = 20 exists** (4 found; K=46, Σ=26, R=94, 1545 eligible);
best heuristic V₇ = 36 (beam; would be waste 855 if coverable — but high-K
optima are already count-infeasible, echoing n=6). Ledger: V₇=15 ⇒ **5905**,
V₇=20 ⇒ **5904**. The 5906 word itself is not distributed anywhere in the urdvr
tree (kernel extraction impossible for now).

**The decisive open question is now singular: does any V₇ ≥ 15 chain admit a
rooted exact cover?** A yes, compiled and validated, is a world record. Odds
look materially better than n=6's refutation: the V₇=15 chains are low-K
(structure close to the standard kernel, which IS coverable), with 20×+ more
eligible rows than needed, whereas n=6's fatal chains rode 20–22 of a 24-loop
class. Next: kernel-parameterized DLX (urdvr's compiler is kernel-generic;
`build_instance` is the only standard-bound piece) over the 100 V₇=15 chains +
the 4 V₇=20s, forest pruning on, compile any solution via their certificate.py,
validate with our validator, price via the ledger.

**Also next: Track B design** (the n=6 871 hunt — sojourn-level out-of-grammar
search; sharpened fact from this session: every inter-orbit w2 is necessarily a
w2x edge, so Track B's freedom is purely structural: non-laminar nesting,
sojourn patterns outside {2,3,4,6}, w3/w4 placement — budget X + #w3 + 2#w4 +
3#w5 = 27 vs the records' 28).

## 2026-07-27 (session 11) — item 5 step 2 executed to a proof: Egan−1 = 872 is OPTIMAL in the gain-one grammar at n=6 (kernel door closed, any hop cost); n=7 becomes the in-grammar attack; n=6 sub-872 must leave the grammar

Continuation of s10, same day. Three probe rounds (one subagent, kept alive across
rounds) answered s10's "whole game" question — negatively, with exhaustive proofs.
Scripts committed to **`analysis/kernelchain/`** (self-contained stdlib Python;
gate-validated); design note revised in place (`docs/ITEM5-DESIGN.md` §3–4).

**Round 1 (relation + gate + first search).** Hop relation extracted from
certificate.py/liftcheck.py and validated: the standard kernel's three hops are
recovered as the *unique* options per pair. Findings: every loop has cost-3
out-degree exactly 5; **cost-3 hops preserve the pivot** (6 disjoint 24-loop
classes, orbit-disjointness automatic in-class); the strict full-ride relation has
**period exactly 4** from all 720 (loop, entry) states — K=8 strict is impossible,
and this is *why* the standard kernel has n−2 = 4 loops. Liberal (nsk-style
partial-ride) chains reach K=8..24 abundantly — but partial rides skip orbits.

**Round 2 (the skip-priced ledger — correction to s10's headline).** Skipped
kernel orbits must be bought back by rows: **waste = 148 − K/4 + Σskip/4**
(+f4 + 2f5 for cost-4/5 hops), so liberal K=8 lands back at 872 and the 871
target became K − Σskip − 4f4 − 8f5 ≥ 8 (minimal: K=12, Σskip=4). Exhaustive
answer: **K=12/Σ=4 does not exist; K=16/Σ=8 does not exist; max K−Σ = 8 only at
K=22/Σ=14** (6 chains, one per pivot class, relabelings of one) — and those die
on rows: 24 non-root orbits need 6 row loops, only 2 exist. Standard-kernel
sanity under the skip formula: all skips 0, waste 147 ✓.

**Round 3 (mixed costs — closing the last door).** My cross-pivot hypothesis was
*refuted*: a door of any cost ends with the pivot symbol (analytic +
computational), so pivot confinement is absolute at every hop cost. B&B over
costs 3–6 (complete, ~30 s): **max V = 8, exactly 12 ledger-optimal chains**
(the 6 old K=22s plus 6 new K=20/Σ=8 with one skip-0 cost-4 hop that resets the
period-4 cycle for free). **All 12 fail the rooted exact cover** (0 covers;
checker validated by re-finding the known 25-row cover under the standard
kernel, ~11 s). V=12 (⇒ 870) unreachable.

**Theorem (combined): in the gain-one certificate grammar — complete rows, hops
of any cost — length 871 is unreachable at n=6. Egan−1 = 872 is optimal in the
class; the standard kernel is a proven optimum, not a convention.** Incomplete
rows are strictly waste-positive (fewer children per split), so they tie 872 at
best. This answers Robin's nonstandard-kernel suggestion at n=6 with a proof,
and explains why the record has stood.

**Also derived (general, no grammar assumption): waste = (S−1) + #w3 + 2#w4 +
3#w5** for any tight walk with S sojourns — the bridge from the grammar theorems
to general search (an 871 needs e.g. S=144 with three w3s).

**Steering (user checkpoint this session): keep the novel bet central.** Recorded
in the design note §5: the chain campaign was scouting (tiny spaces, complete
search, ended in proofs — ML would have been decoration); the learned bet is
load-bearing where spaces explode. Re-centered plan, three tracks
(`ITEM5-DESIGN.md` §4):
- **Track A (in-grammar, n=7)**: port kernelchain to n=7 (840 loops; period and
  pivot structure unknown) — max V₇ campaign; V₇ ≥ 15 with a feasible cover
  beats 5906 (5905); the 5906's own kernel is a known-good seed. Cover search is
  large ⇒ first real deployment of Track C.
- **Track B (out-of-grammar, n=6)**: sojourn-level search for S−1+#w3+... = 146
  outside the certificate class; also the right frame for impossibility lemmas
  that could extend the proven floor toward 872.
- **Track C (the thesis)**: learned evaluator over partial certificates/sojourn
  plans — 296 records as labeled certificates, prefixes as positives, DLX
  dead-ends as negatives; s8 anchored ranker as baseline architecture.

**Next session: Track A** (n=7 port: period, max V₇, chain census — the decisive
computable question), and Track B's state/move design note.

## 2026-07-27 (session 10) — item 5 opened and designed: records are exactly K=4 certificates; waste = 148 − K/4 ⇒ an 8-loop kernel chain + 20-row cover = 871; design note committed

Two parallel subagent threads (cycle-level trace of the record corpus; formal
digest of the urdvr certificate machinery), then synthesis. The outputs interlock
so cleanly that item 5's design collapsed from "big open-ended build" to a
three-step attack on one finite combinatorial question. Full design:
**`docs/ITEM5-DESIGN.md`** (the session's product — this entry is the summary).

**Thread A — cycle-level trace of all 296 872s (script in scratchpad,
`cycletrace/cycletrace.py`, regenerable).** The record grammar is *exact*, zero
exceptions across 296 walks: 145 sojourns each; the transition alphabet is two
letters — 141 × `w2x` (every single w2 in every record is the cross-cycle
P[2:]+P[1]+P[0] edge; in-cycle w2 never occurs) + 3 × w3 (always to fresh cycles,
always at sojourn index ≡ 0 mod 5); sojourn lengths ∈ {2,3,4,6} only; splits only
2+4 / 3+3 / 4+2 / 2+2+2 with doubles + 2·triples = 25 always; interruption nesting
is laminar in 296/296 (depth up to 16 — the "tree-like" lore is true but deep, not
shallow); interruption gaps have ≡ 4 mod 5 sojourns with every gap cycle fully
completed. Contrast: greedy's 873 and our stratified 873 are cycle-level
*identical* (120 clean length-6 sojourns, no nesting) — the record trick is
swapping 15 w3 + 4 w4 + 1 w5 exits for 25 nested w2x detour-and-returns.

**Thread B — urdvr machinery digest (file:line-pinned).** Marked loop = pivot +
5-necklace, its 5 splices are w2x edges linking 5 cycles; oriented row = loop +
parent choice = exactly our detour (enter from parent, ride 4 children fully,
return); kernel = K orbit-disjoint loops chained by K−1 cost-3 hops
(T3(p)=T2(q)); certificate = kernel + rooted exact cover by rows; the walk-replay
exact-once condition is the only true correctness invariant. Load-bearing
discoveries: the certificate *compiler* is already kernel-generic (only
`build_instance`/`ladder`/`gain1c` hard-code K = n−2), it even anticipates
"nsk-style partial rides"; the n=7 5906 census (20 loops, 19 T3, 822 T2, 5
incomplete groups) identifies it as a K=20 certificate with concessions; and
rootedness/exact-cover are correctness conditions (rootless rows are never opened
by the walk), while {kernel size, row completeness, hop cost} are the class
restrictions — the doors to sub-Egan−1.

**Synthesis — the waste ledger (verified against every known data point).**
Hyperedge-forest counting gives waste = m + 118 (m = total loops, n=6), and with
complete rows m = 30 − K/4, so **waste = 148 − K/4, K ≡ 0 mod 4**: K=4 → 872
(= Egan−1, the 141/3 census of all 296 records), K=8 → **871 = world record**,
K=24 → 867 (the grammar floor lands exactly on the proven lower bound). Cross-n:
K=5 at n=7 → 5907 (exactly the urdvr words); perfect K=20 → 5904, and the actual
5906 is that certificate paying 2 chars of concessions — so **large kernel chains
provably exist at n=7**, and even repairing the 5906's five incomplete groups
would beat the record. Every relaxation (mixed-cost hop, partial ride) is priced
in the ledger; search never leaves proof-grade waste accounting.

**Execution plan (in the design note, each step with go/no-go):**
1. `src/cert.rs`: marked loop / oriented row / kernel-parameterized certificate +
   generalized W1–W7 checker + walk compiler. Gate: 296/296 records round-trip as
   K=4 certificates; the three 5907s parse at n=7; ledger machine-verified.
2. Kernel-chain search: enumerate the T3(p)=T2(q) pair relation on the 144 marked
   loops; DFS for K=8 orbit-disjoint chains. **This is the whole game at n=6** — a
   finite, fully checkable existence question nobody has answered.
3. Rooted-cover DLX over surviving kernels (adapt urdvr's Python `build_instance`
   first — the compiler is already generic; Rust port only if the probe lives).
   Any cover ⇒ compile ⇒ validate ⇒ 871.
4. Only if dry: priced relaxations (partial rides, mixed-cost hops), and the n=7
   K=20 attack seeded from the 5906's own extracted kernel.

Anti-goal carried forward (s8): no static rewarding of row-like shapes in
move-level beams — this searches the certificate space directly.

**Next session: step 1 (`src/cert.rs`) and step 2 (the K=8 chain question).** If
step 2 answers "no chain exists at cost 3", the ledger immediately prices the
fallbacks; if "yes", step 3 is a bounded DLX run from a known-good codebase.

## 2026-07-27 (session 9) — item 4 executed: exact endgame tablebase built; metric met, but the endgame door is proven shut (873/874/5913 all locked before the last 25 perms; every known record's tail is optimal)

Single thread this session: build ROADMAP item 4 end-to-end, then use it to convert
the standing "endgame is already solved" belief into theorems.

**Built (commit `cf257b9`).** `src/endgame.rs`: Held–Karp DP over
`(subset of remaining, last perm)` — `solve_endgame(g, cur, remaining)` returns the
provably minimal completion cost plus a witness order. Exactness is not heuristic:
the overlap distance satisfies the triangle inequality, so passing through visited
perms never helps and the optimal completion is exactly the optimal Hamiltonian path
on the remaining set (proof sketch in the module docs — every verdict below is a
theorem). `u16` table, `2^m·m` entries; practical ceiling `MAX_REMAINING = 25`
(~1.7 GB, ~7 s); m=20 is 40 MB / ~0.12 s. Two integrations: (1) `beam --endgame m
--endgame-top K` snapshots the top-K frontier states at r=m (pure instrumentation —
search bit-identical, pinned by test), exact-solves each post-hoc, and maps final
beam states back to their snapshot ancestors so each state's exact total is compared
against *its own* beam completion (the ROADMAP metric, measured per state); prints
the improved validated string if any exact total beats the beam. (2) `endgame`
subcommand: exact-complete a prefix of greedy or any traced string. Tests: brute-force
oracle (suffix + arbitrary sets), full n=4 solve from identity **= 33 exactly** (the
proven optimum, now an internal consistency theorem), greedy-n=5-prefix + exact
endgame = 153 with validation, snapshot purity + dominance (exact ≤ own descendant,
≥ global optimum). 81 tests green, clippy/fmt clean.

**Frontier experiments — metric MET, top never moves.** Config = the canonical
stratified 873 (boot1 α=1, w2000, quota 4, bucket 1) unless noted:

| run | best exact total | exact beats own descendant | beats beam result |
|---|---|---|---|
| n=6 strat, m=20, top=2000 (full frontier) | **873** (rank #0) | 7/2000 (max gain 3) | 0 |
| n=6 strat, m=24, top=64 | 873 (rank #0) | 4/64 (max 3) | 0 |
| n=6 unstrat boot1 (874 plateau), m=20, top=2000 | **874** (rank #0) | 11/2000 (max 4) | 0 |
| n=7 strat transfer (5913), m=20, top=200 | **5913** (rank #0) | 8/200 (max 4) | 0 |
| n=5 cycle-bound w2000, m=15, top=50 | 154* | 4/50 (max 4) | 0 |

(*n=5: the eventual 153-winner's ancestor sat below score-rank 64 at r=15 — top-64
missed it; top=width captures it, integration test pins this.) The go/no-go metric
("any frontier state whose exact endgame beats the heuristic one by ≥ 1 char") is
formally met at every n — but the gains live mid-frontier on states with no winning
future; the score-rank-0 state's heuristic completion was *already optimal* in every
single configuration.

**Theorems (the session's real product).**
1. **The stratified config's entire width-2000 frontier at r=20 completes to
   ≥ 873** — no endgame play of any kind reaches 872 from this beam; the record is
   lost before level 700.
2. **The unstratified boot1 frontier at r=20 completes to ≥ 874** — the
   873-vs-874 stratification difference is decided strictly before r=20.
3. **Optimal tails everywhere**: greedy's 873, the stratified 873, the seeded 873,
   and the record 872 all have provably optimal last-**25** tails (m=25 at the RAM
   ceiling; exact saves 0). s6's "no endgame deviation from greedy's basin ever
   saves a character" is now theorem-grade at 25-from-end.
4. **All 296 known 872s** (100 community + 196 gain1) have optimal last-20 tails —
   no known record hides a sub-872 completion (the free-world-record lottery ticket
   came up empty, exhaustively).
5. **All three urdvr n=7 5907s** have optimal last-22 tails — same story one size up.

**Reading.** Item 4 is done as a *finding* mechanism and the answer is a clean
negative-with-teeth: s5's "the endgame is already solved" is now proven, uniformly,
at n=5/6/7, for our walks and for every known record. Everything that separates 873
from 872 happens in the opening/midgame — exactly where s8 put it. The tablebase's
lasting value is as **infrastructure**: item 5's cycle-level searcher should call it
as a terminal solver (once ≤ ~20 perms remain, finish provably optimally — the last
~20 plies of any future search are free and exact), and any "nothing beats X from
this state" claim below m=25 is now one CLI call. If theorem depth beyond 25 is ever
needed, a DFS branch-and-bound completion prover (arc bound, no 2^m table) is the
natural extension — noted, not built.

**Next session (item 5, the big build — all steering weight now here):**
- Cycle-level (super-node) move space over the 120 rotation cycles; the 2-cycle
  weave as a *move* (s8: statically rewarding the shape is exploitable), kernel as a
  *parameter* (Robin: sub-Egan−1 lives outside the standard kernel; at n=6, Egan−1 =
  872 IS the record, so a closing nonstandard-kernel word is a world record).
- Start from the urdvr certificate machinery (W1–W7 checks, trade vocabulary, DLX
  exact cover) + our learned ordering; anytime DFS with the admissible waste-budget
  test (budget 147), endgame tablebase as terminal solver.
- Cheap first step: formalize the cycle-graph state (which cycles entered/left where,
  live w2 bridges) and enumerate legal weave-moves from a mid-walk record state — the
  move vocabulary falls out of tracing the 298 872s at the cycle level.

## 2026-07-27 (session 8) — item 3 executed: deficit features carry the expert signal, but no linear/MLP evaluator converts it (873 stands); n=7 from-scratch baseline 5913; field news (Robin: kernels; Theo: paint-waste)

Three threads again: n=7 probe, feature implementation, training/evaluation campaign.
Item 3's verdict is a clean partial: **the features work, the evaluator class is the
ceiling.** No sub-873; steering weight moves to items 4–5.

**Features landed (commit `ead4c8a`).** `half_open` (cycles with 1–2 visited) and
`nearly_done` (1–2 unvisited) now in `Walk` + JSONL; new **`w2_bridges`** = count of
unvisited cross-cycle weight-2 edges joining two partially-visited cycles (each perm
has exactly one cross-cycle w2 successor `P[2..]+P[1]+P[0]` — a bijection — so the
count is O(1)-amortized incremental via `Graph::w2_bridges_delta`, shared by Walk,
beam, and guided rollouts). Model contract is append-only length-dispatched:
`FEATURE_ORDER` (8) vs `FEATURE_ORDER_V2` (11); old models score bit-identically
(pinned to the exact bit pattern; stratified 873 reproduces byte-identical). beam2
skips the new features by design (documented NO-GO probe). 76 tests green. **The
feature does what the s5 autopsy demanded**: tracing a record vs our stratified 873,
midgame (steps 250–450) mean `w2_bridges` is 1.9 (max 7) vs **identically 0.0** on
every greedy-shaped walk; `half_open` 3.3 vs 0.3.

**Expert corpus tripled (prep for the campaign).** urdvr's `gain1.py search` is a
0.09 s/word mass generator: 200 seeds → 198 distinct 872s, **196 new** vs the known
corpus → `data/gain1_872s/` (gitignored). ("New" = byte-distinct; equivalence-class
status under relabel/reverse symmetry unchecked — urdvr's `equiv_check.py` can
classify if it ever matters. And to be explicit: these are *generated* by urdvr's
construction, not found by our search — our search floor remains 873.) With records872 + the 2 urdvr words: **298
distinct 872s**. Chaffin per-waste optimal prefixes downloaded to `data/chaffin/`
(599 files incl. all `Chaffin_6_W_<w>` exhaustive lists; unused this session —
`trace` requires complete strings — kept for a future prefix loader). Traced corpus:
596 expert trajectories (298 + 298 reverse-**and-relabel**; plain reversal doesn't
start at identity, so relabeling is mandatory), 429k rows, plus fresh v2 rollout/
trajectory corpora. **Trap documented: all pre-`ead4c8a` JSONL (including the
misleadingly named `boot_n6_elite925_v2.jsonl`) has the new fields zero-defaulted —
never train the new features on it.**

**Campaign (commit `a68d068`: `ml/fit_rank.py` + `beam --allow-n-mismatch`): NO-GO
on sub-873, with sharp structure.** 10 models × α × quota × width, 186 validated n=6
runs:

- **Best overall: 873, only from boot1 ⊕ β·rank pre-blends (β 0.05–1) — and every
  one is byte-identical to `data/result_stratified_873.txt`.** The rank direction
  never flips a single boot1 decision at any surviving β, any width to 32000: the
  873→872 gap is unreachable by *any reweighting in this feature basis* (extends
  s6's conclusion from 8 features to 11).
- **Population-contrast training is exploitable** — the session's most important
  negative mechanism: scorers trained to separate expert from background states turn
  `w2_bridges`/`half_open` into a classifier, and the beam then *manufactures*
  bridge-rich junk with no record future (expert+rollout OLS mix: 1765; pure
  rankers: fail the n=5 gate at every α, and their beams collapse record survival
  719→264 because junk out-ranks records on the ranker's own scale). Credit for
  structure must be conditional on being able to use it — a static linear map can't
  express that.
- **The anchored (residual) ranker is the honest signal-carrier**: pairwise ranker
  on `cost_to_go − lb_arc` (RankNet-style logistic loss, 89.8% held-out pair
  accuracy; standardized `w2_bridges` coef −3.33 = strongest expert discriminator)
  is the best standalone expert-informed scorer (888 @ w2000, beats arc's 891) and
  produces the **first-ever nonzero midgame rank-wins** (records winning the
  stratified window at 10/484 levels 118–601, vs 0 for boot1 and all blends). The
  features are real; linear/MLP over them is the ceiling.
- n=5 gate lesson: it screens *breakage*, not *poison* (expmix passed the gate at
  all α, then beamed 1765 at n=6).

**n=7 from-scratch baseline established: 5913, stratified learned beam — the n=6
story reproduces one size up.** Hand bounds are terrible (cycle 6180, arc 6130 @
w2000 — far worse than greedy, unlike n=6); the n=6-trained boot1 model transfers
with zero retraining (5970); stratification (quota 4 or 8) closes exactly to
**5913** at w2000 (~5.5 min) and w8000 (~21 min, same string) — a distinct string
from greedy's with the *identical* weight histogram (4320/600/96/18/4/1). Quota
response shifts (quota 1, a winner at n=6, gives 5961). The rank-blend transfers no
improvement (5913). Bar to beat: **5907** (urdvr words). `--allow-n-mismatch` now
enables cross-n model runs.

**Field news (documented in `../extraDocs/2026-07-27-urdvr-email-and-repo.md`).**
(1) **Robin's reply**: proving indefinite lifting would give the long-conjectured
Egan−1 upper bound; and — the actionable half — the gain-one machinery should be
adapted to **nonstandard kernels**, "as we were able to do for n=7" (the 5906).
Independent confirmation of our s7 boundary note: sub-Egan−1 means leaving the
standard-kernel move space, and item 5's cycle-level design must *parameterize the
kernel*. At n=6, Egan−1 = 872 IS the record, so any closing nonstandard-kernel word
there is a world record. (2) **Theo H.**: claims (opinion, no mechanism) that even
the 5906's nonstandard-kernel savings lift indefinitely — filed as
conjecture-on-conjecture; posted `paint_waste.cpp` (archived + compiled at
`../extraDocs/theo-paint-waste/`, copyleft): an analyzer emitting
`[clean_run_length:source_index]` pairs per waste symbol — his dirty-window counts
match our waste accounting exactly (record 872: 147 waste, max dirty run 2).

**Next session (item 4, with item 5's design brief sharpened):**
- **Exact endgame tablebase** (ROADMAP item 4): DP over (remaining subset, cur) for
  ≤ ~25–30 remaining perms; bolt onto beam/stratified frontier states. Metric: any
  frontier state whose exact endgame beats the heuristic one by ≥ 1 char. Also turns
  "nothing beats 873 from greedy's basin" claims into theorems.
- **Item 5 design note (from this session + Robin)**: cycle-level move space must
  (a) make the 2-cycle weave a *move*, not a feature to reward — the campaign proved
  rewarding the shape statically is exploitable; (b) parameterize the kernel. The
  urdvr certificate machinery (W1–W7 checks, trade vocabulary) is the starting
  formalization; its DLX search + our learned ordering is the unplayed combination.
- Cheap follow-ups: rank-corpus prefix loader for Chaffin positives (if item 4/5
  need an opening prior); n=7 expert trace (the three 5907s) once any n=7-aware
  scorer exists.

## 2026-07-27 (session 7) — phase 3 opens: stratified beam GO (from-scratch 873); two-ended beam NO-GO (evaluation, not ordering); field news: urdvr repo (Egan−1 at n=11–13, n=7 5907s)

Three parallel subagent threads: roadmap items 1 and 2 (implement + sweep each), plus
documentation of a new community email/repo. Both probes returned decisive answers,
and they converge.

**Item 1 — stratified beam: GO, both metrics met (commit `83724ac`).** New beam
`State` counters `half_open` (cycles with 1–2 visited members — the structure records
keep alive) and `nearly_done` (1–2 unvisited), O(1)-incremental. Frontier bucketed by
`(intact/B, half_open/B, nearly_done/B)`; selection reserves up to `--strat-quota`
best candidates per occupied bucket, then fills the width in global score order. Score
function untouched (admissibility/dedup arguments unchanged); off-mode pinned
bit-identical by test. Results (boot1 α=1; unstratified baseline 874 everywhere):

- **From-scratch n=6 = 873, validated** — the first sub-874 without prefix seeding.
  `beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1 --stratify
  --strat-quota 4 --strat-bucket 1` (~8 s; also quotas 1/5/6/8 at w2000; quota 4 holds
  at w8000/32000). String saved to `data/result_stratified_873.txt`; independently
  reproduced bit-identical. Distinct from greedy's 873 and the seeded 873.
- **Record survival transformed**: fraction of record-trajectory states inside the
  kept window at levels 118–601 goes **0.15% → 99.55%** (quota 4:1); 96/100 records
  are never outside the window at any level (baseline: 100/100 pruned by level 118).
  First-prune level for the remaining 4: 288–380 (was median 62).
- Quota response is sharply non-monotone (2–3 catastrophic at 897–904; 1 and 4–8 give
  873; 12–32 degrade); fine buckets beat coarse (default 32:4 stays at 874). Jitter
  and seed-prefix both *anti-compose* with stratification; arc bound + stratification
  is worse than plain arc (reserved width is wasted without a discriminative scorer).
- **The surprise that matters: the winning 873 is greedy-shaped** (600/96/18/4/1
  weight histogram, heavy moves at steps ≡ 0 mod 30), not record-shaped. Record-like
  states now survive the whole walk yet never win — selection is fixed, and what
  remains between 873 and 872 is *evaluation*.

**Item 2 — two-ended (deque) beam: NO-GO, clean negative (commit `5fbee1c`).** New
`beam2` subcommand: state `(front, back, visited)`, append-successor/prepend-
predecessor moves, weight-graded predecessor lists (`Preds`, exact mirror of succs),
mirrored features, dedup on `(front, back, visited)`, and the two-ended arc bound
`lb_arc2 = max(r, r + arcs − [succ1(back) unvisited] − [pred1(front) unvisited])`
with proof sketch in `src/bound.rs` and oracle-tested admissibility along arbitrary
deque walks. Recovers 33/153 (n=5 needs width ≥ ~1000, where the winning 153 uses 44
prepends — real two-ended optima exist). n=6 from scratch: arc2 scoring **899/898/897**
at w2000/8000/32000 — *worse* than one-ended arc (891), because the deque squares
state variety per level (same visited set × many (front,back) pairs) and the flat
bound can't rank the extras. The learned model transferred into the new move space
lands **exactly on the 874 plateau** (w2000 and w8000, a different 874 string, only 6
prepends); jitter forcing 220–364 prepends moves arc2 only 899 → 892. Per the roadmap
criterion: **the blindness is evaluation, not decision order** — item 5's future case
rests on structural moves, not ordering freedom. Side-find: a width-1 beam reproduces
greedy's 873 under both bounds (previously unrecorded).

**Convergent read.** Fix selection (item 1): record states survive but never win. Fix
ordering (item 2): nothing changes. Both point at evaluation — the scorer cannot
recognize record-shaped midgames — which is exactly items 3 (deficit-distribution
features + expert-rank training) and 4 (exact endgame tablebase). Item 1 also moves
the baseline: the from-scratch bar is now 873, and stratification is the default
harness for any future scorer test.

**Field news (email from urdvr, 2026-07-27) — documented in
`../extraDocs/2026-07-27-urdvr-email-and-repo.md`, repo cloned to
`../extraDocs/superpermutation-examples/`.** New words + generator code
(github.com/urdvr/superpermutation-examples). All claimed lengths are exactly
**Egan−1** (n! + (n−1)! + (n−2)! + (n−3)! + n − 4): n=11 43,948,807; n=12
522,910,088; n=13 6,749,568,009 (n=13 word not yet distributed — no GitHub release).
We verified every distributed word: n=6/7 via our validator, n=8–12 via an
independent Lehmer-rank bitset checker. n=11/12 are new records by our ledger.
Contents relevant to us: **2 new 872s** (from-scratch DLX search, not in our 100),
**three n=7 words at 5,907** (first known with the standard 5-loop kernel; record is
5,906), 4–6 words each at n=8–10 (Raudvere/Echols originals + perturbed variants).
Construction: Egan−1 ⇔ a "gain-one" certificate (T1/T2/T3-only walk, standard kernel,
oriented complete-2-cycle exact cover forming a forest rooted in the kernel); three
modes — exact-cover search (DLX), perturbation (destroy ~30% of rows and rebuild),
and lifting n→n+1 (verified 9→13; **6→7 provably fails**; search-and-verify, no
induction proof). Author caveats recorded verbatim: generator evolved without
rigorous notes, may not reproduce exactly; lifting "usually (but not always?)" works.
**Discrepancy to raise on the thread: the email mentions Williams words in the repo,
but none exist in the tree, releases, or branches.**

Phase-3 implications of the repo: (a) real expert fuel for item 3 — the n=7 5907s
break our 5913 threshold, the new 872s extend the n=6 corpus, and `gain1.py search`
is a seconds-fast mass generator of fresh n=6 records; (b) for item 5, the repo *is*
a worked cycle-level move vocabulary (row destruction/rebuild, anchored trades,
trap-loop bans) with `liftcheck.py`'s W1–W7 as a machine-checkable "record-shaped"
predicate; (c) boundary fact: the 5,906 record **fails** the gain-one structure
(nonstandard kernel), so beating 5,906 means leaving that move space — gain-one is a
ceiling, not a ladder.

**Next session (item 3, with the new fuel):**
- Deficit-distribution features (count of cycles with exactly 1–2 visited members —
  `half_open` is already maintained in beam State; add the 2-cycle-adjacency stat and
  wire both into `Features`/JSONL + the model contract).
- Rank training: expert states (100+2 records via `trace`, Chaffin optimal prefixes,
  optionally mass-generated gain1 872s) above rollout states at equal level; reverse-
  relabel augmentation. Metric: record states *win* the stratified window, then beam
  length < 873.
- Cheap parallel probe: run the phase-2 scorer + stratification at n=7 for a first
  baseline (greedy 5913; new sub-target 5907 from the urdvr words).

## 2026-07-27 (session 6) — rung 1 achieved: validated 873 via greedy-prefix + learned endgame; residual and guided-loop attacks plateau at 874; PHASE 2 COMPLETE

Three parallel sweep campaigns over the s4 mechanisms (one subagent each), run
concurrently with the s5 record autopsy. Two clean negatives and one breakthrough.

**Attack 1 — residual targets: negative, 874 everywhere.** Residual models
(`cost_to_go − lb_arc` labels) on the boot1 recipe: `linear_n6_res_boot1` (held-out
RMSE 25.1 in absolute space vs lb_arc's 92.7), `mlp_n6_res_boot1` (21.6), plus a
raw-ε-greedy-corpus control. Results: linear res_boot1 → **874** at α ∈ {0.25, 0.5}
for every width 2000–32000; α=1 → 875, α=2 → 1104 (the residual correction is
calibrated — pushing it harder now *degrades*); MLP → 874 (α ∈ {0.25, 0.5}); raw
corpus → 899–1640 (still poison regardless of target formulation). Jitter portfolio
(18 runs): 15× 874, 3× 875, never 873. n=5 gate passed by all models. Lesson-4
reconfirmed sharply: best RMSE ever trained here (21.6), identical beam result.
Label engineering is ruled out as the path to 873.

**Attack 2 — model-guided rollouts (closed loop): negative, 874 everywhere, with a
diagnosis.** The guided ε=0 policy scores **exactly 873 on all 50 probe rollouts** —
the model has memorized the greedy corridor — but is *more brittle off-path* than the
hand heuristic (ε=0.01: min 906 vs the hand policy's 873; worse at every ε > 0). Two
full guided rounds (search → relabel → retrain, ~325k + 217k rows, incl. fresh beam
trajectories): every retrained model (`linear_n6_guided1`, `_res`, `_mix`, `guided2`)
beams **874 at every α ∈ {0.5, 1, 2} and width ∈ {2000, 8000, 32000}**. Notable
non-replication: mixing guided with old boot corpora was harmless (874, vs s3's
880–1532 catastrophes) — s3's mixing failures were across *behaviorally different*
policies; guided-ε ≈ hand-ε here, so the mix is benign. Closing the loop cannot
escape a basin when the policy generating the data is the basin.

**Attack 3 — greedy-prefix seeding: rung 1 achieved, validated 873.**
`beam -n 6 --width 2000 --seed-prefix 350 --model ml/models/linear_n6_boot1.json
--alpha 1` → **873 in ~2 s**, validated complete (720/720) and independently
reproduced; string saved to `data/result_prefix_873.txt`. Full depth→length picture
(w2000):

| depth | 0 | 60–345 | 350 | 360–718 |
|---|---|---|---|---|
| boot1 α=1 | 874 | 875–876 | **873** | 873 |
| arc bound | 891 | 888–876 | — | 873 from 476 (band 476–480 non-monotone) |

Key numbers: the cliff is **sharp at depth 350 of 719 (~49% of the walk)** — 345 gives
876, 350 gives 873, no intermediate lengths, zero variance under jitter (32 runs) or
width (8000/32000). Shallow seeding actively *hurts* (60–345 → 875–876, worse than
unseeded 874): the model's midgame fights greedy's line rather than approximating it.
Deep prefixes (660–718, w32000, both scorers) → all exactly 873: **no endgame
deviation from greedy's basin ever saves a character**; the 872nd character must be
won in the first half. The blend0.075 model shows a seeding pathology (878 at depths
350/355 — worse than its own unseeded 874). Side-findings: the winning 873 is *not*
greedy's string (first divergence at char 440); blend0.075 is pre-blended — its
coefficients are already `0.075·model + 0.925·lb_arc`, so it runs with `--alpha 1`
(s3's "blend α=0.075" describes the training mix, not a CLI flag).

**Convergent picture (this session + s5 autopsy).** The seeding cliff at ~350 and the
autopsy's prune window (every 872 record excluded from the beam's score window from
level ~62–118 to ~601, by up to ~68 chars) agree: opening/midgame policy is the whole
game, the endgame is already solved by our scorer. The records' fixed signature
(575/141/3 weight profile — leave 1-cycles early via w2, weave them closed later) is
exactly what the k/intact features penalize, because no rollout corpus ever shows it
paying off. 874 → 873 fell to forcing the opening; 873 → 872 requires *generating*
record-like midgame states, which no reweighting of the current 8 features will do.

**Phase 2 verdict: complete.** Exit criterion met (s3), rung 1 met (this session,
hybrid greedy-prefix + learned-endgame beats both parents from scratch). Rung 2 (872)
is out of reach of the phase-2 design point — move to phase 3.

**Next session (phase 3 opening), concretely:**
- **Cycle-level move space**: super-node search over rotation cycles that *plans* the
  2-cycle weave (which cycles to leave half-open, where to spend the three w3 moves —
  records put them at steps ≡ 0 mod 30) instead of discovering it move-by-move.
- **Deficit-distribution features**: count of cycles with exactly 1–2 visited members,
  2-cycle adjacency between partially-visited cycles — the autopsy showed these
  separate record midgames from rollout midgames at equal (r, level).
- **Imitation corpus, free**: `data/records872/` (100 distinct validated 872s +
  fetch recipe, JOURNAL s5) can be traced to `Features` JSONL — expert
  demonstrations the rollout corpora structurally lack. A model trained to *rank
  record states above rollout states* at equal level is the cheapest test that the
  new features carry the signal.
- Infrastructure is ready: `trace` (first-visit trajectory + per-step beam-exact
  scores), `beam --cutoff-log` (prune thresholds), `--seed-prefix` (basin forcing)
  compose for any future what-does-the-beam-lose analysis.

## 2026-07-27 (session 5) — record autopsy: traced 100 community 872s; our scorer prunes every record path by level ≈62, midgame k/intact features are the blind spot

**Question answered this session: what do actual 872-length solutions do that our
searches prune, and at what depth / by what margin does the beam discard them?**

**Built.** (1) `trace` subcommand (`src/trace.rs`): `trace -n 6 --file s.txt
[--model m.json --alpha a | --bound cycle|arc] [--log f.jsonl] [--score-log f.tsv]` —
extracts a string's first-visit rank trajectory (sliding window), replays it through a
`Walk` (replay_len == input_len certifies tightness), prints the move-weight histogram
and weight ≥ 3 positions, optionally emits the `Features` JSONL and per-step
beam-exact scores (`score_state` mirrors `score_move`'s fixed-point arithmetic, so
scores compare exactly with cutoff logs). (2) `beam --cutoff-log f.tsv`
(`beam_search_cutoffs`): one TSV line per level — `level, kept, best_score,
worst_kept_score` (the pruning threshold); pure instrumentation, bit-identical search
(pinned by test). 5 new tests (26 total green), clippy/fmt clean. Corpus: 100 community
872 records + 873-tight/-egan downloaded to `data/records872/` (gitignored; all 100
validate complete and trace tight: replay 872, 720 visits, identity start).

**1 — Structure.** Move-weight histograms (719 moves each):

| walk | w1 | w2 | w3 | w4 | w5 |
|---|---|---|---|---|---|
| greedy 873 | 600 | 96 | 18 | 4 | 1 |
| our beam 874 (boot1 α=1, w2000) | 600 | 89 | 30 | 0 | 0 |
| **every one of the 100 records** | **575** | **141** | **3** | 0 | 0 |
| 873-egan | 571 | 148 | 0 | 0 | 0 |

All 100 records share the identical histogram: 25 fewer w1 and ~50 more w2 than
greedy/beam, exactly three w3 moves, never w4+. The 3 w3 moves sit at multiples of 30:
{630,660,690} (29 records), {30,60,90} (26), {30,60,690} (25), {30,660,690} (20).
Weight spend is uniform across the walk (~24–25 extra chars per 120-step bucket) —
records pay w2 steadily instead of finishing cycles and paying w3+ resets.

**2 — Divergence.** First visit-index where a record's rank sequence leaves greedy's
path: min 2, p25 28, median 62, p75 92, max 118 (only 8 distinct values:
{2,28,32,58,62,88,92,118}); 16 records leave the very first cycle after just one w1
move (weight pattern 1,2,… vs greedy's 1,1,1,1,1,2). Our beam-874 path shares greedy's
first 78 visits, so divergence vs beam874 is the same distribution capped at 78.

**3 — Prune depth (headline).** Scoring each record trajectory with the canonical
scorer (linear_n6_boot1, α=1) against `beam -n 6 --width 2000 --cutoff-log` per-level
thresholds: **all 100 records are pruned; first-prune level min 4 / p25 28 / median 62
/ p75 92 / max 118** — the beam discards every record branch inside the first ~16% of
the walk. Margin at first prune: 0.2–7.1 chars (median 5.5). Mid-walk the exclusion is
enormous: from level 118 to 601 **zero** record states score within the kept window
(per-record worst margin: median 68, max 114 chars). Records re-enter the window at
level ≥ 602 and by level 700 they'd *win* it (record score 863.9 vs cutoff 872.5) —
the endgame ranking is fine; the beam just can't generate those states. Width 32000
barely moves anything (median first-prune 62 → 62; the same 874). Under the arc bound
(w2000): median first-prune 90, margin always exactly 1 char — the bound is flat, not
wrong. Anchors: our own 874 path is never pruned (sanity, frac-within 1.0); greedy's
873 path survives to level 243 with worst margin 1.47. Caveat: this is a
necessary-condition analysis — the beam must also *generate* a state (parent must
survive), so true prune depth ≤ measured.

**4 — Feature gap.** Model residual (pred − actual cost-to-go) along trajectories:
the model overestimates record states by ~+129 chars in the opening vs +115 on its own
beam path (+9 delta), and the gap *widens* through the midgame — delta peaks at
**+52 chars around steps 290–430** — closing to +6 by the end. Feature-level cause (at
step 300, records mean vs beam874): intact 65.9 vs 69, k 73.8 vs 70, lb_arc 492 vs 488
— records look "worse" on every feature the model has, yet their actual cost-to-go is
*lower* (504.8 vs 506). With coefficients k +3.92 and intact −9.30, those two features
alone account for ~+44 of the +49 midgame prediction gap. The model reads "many
touched-but-unfinished cycles" as expensive; records deliberately keep ~4 more cycles
half-open (the 2-cycle weave) and close them later at cost ≈ the greedy-style walk —
structure the 8 features cannot see.

**Synthesis (steers phase 3).**
1. The 874 plateau is a *policy* gap, not a tie-break gap: every 872 lies outside the
   beam's score window from level ~62–118 onward by up to ~68 chars mid-walk. No
   width/jitter/restart tweak of the current scorer can recover them (32000 ≈ 2000).
2. The records' signature is fixed and known: 575/141/3 weight profile, w2 moves
   spread uniformly, exactly three w3 "super-moves" at steps ≡ 0 (mod 30). Our
   searches' signature (600 w1) means "always finish the current cycle" — the single
   biggest behavioral difference is leaving 1-cycles early via w2.
3. The learned model *actively* penalizes record-like states (k up, intact down ⇒
   pred up), because its training corpus (greedy-flavored rollouts) never shows that
   half-open-cycle structure paying off — label bias, not model capacity.
4. Concrete feature gap: at equal (r, level), records differ in *how* the unvisited
   mass is arranged across cycles (many cycles at small deficit vs few at large). A
   feature capturing the deficit distribution (e.g. count of cycles with exactly 1–2
   visited members, or 2-cycle adjacency stats between partially-visited cycles)
   would separate record midgames from rollout midgames.
5. Endgame is already solved by our scorer (records would top the beam from level
   ~640 on) — effort should go to opening/midgame policy, e.g. phase-3 cycle-level
   search that *plans* the 2-cycle weave instead of discovering it move by move.

Artifacts (scratchpad, regenerable): per-record trace logs/score TSVs, cutoff logs
for w2000/w32000 (model) and w2000 (arc), analysis scripts. Data in `data/records872/`
(gitignored), fetch commands in this entry's session transcript; re-download via
raw.githubusercontent.com from superpermutators/superperm `superpermutations/6/872/`.
Note: `data/873-tight.txt` is a multi-string file (comment + several 873s), not a
single superperm; `873-egan.txt` is a single string.

## 2026-07-27 (session 4) — rung-1 attack mechanisms implemented (residual targets, guided rollouts, prefix seeding); sweeps pending

**Built all three mechanisms from s3's "next session" list.** Implementation only —
no experiments run; a follow-up session/agents will do the sweeps.

1. **Residual training targets.** `ml/fit_linear.py` / `ml/train_mlp.py` take
   `--residual`: the label becomes `cost_to_go − lb_arc` and the exported JSON gains
   `"target": "residual"` (absent/`"absolute"` = old behavior; old model files load
   unchanged via serde default). Rust side: `Model::target()` / `is_residual()`;
   `score_move`'s `Scorer::Learned` arm scores residual models as
   `len + lb_arc + α·pred` — the admissible anchor is now in the label, per s3
   lesson 1. `lb_arc` is a pure function of `(cur, visited)`, so the dedup argument
   is untouched. Reported Python metrics stay in absolute space for comparability.
2. **Model-guided rollouts.** `rollouts --model m.json --alpha a`
   (`run_rollouts_guided`, `Guide`): the exploit move becomes the argmin of
   `len + w + α·predict(child features)` (+ child `lb_arc` for residual models) over
   unvisited successors; ties keep the sorted (weight, suffix) order. Child features
   are computed in O(1) from the walk's counters (`child_features`, mirror of the
   beam's `score_move`; parent intact count scanned once per step). Epsilon branch
   and RNG stream untouched ⇒ same seed still byte-identical; JSONL schema unchanged.
3. **Greedy-prefix seeding.** `beam --seed-prefix <depth>` (`beam_search_seeded`):
   replays the first `depth` greedy moves through the beam's own `State` counter
   updates (arena seeded with the prefix chain), then runs the remaining
   `n! − 1 − depth` levels. Depth 0 is bit-identical to the plain beam; depth must be
   `< n! − 1` (CLI errors politely). Composes with `--model/--alpha/--jitter/--bound`.

**Checks.** `cargo test --release` green (23 unit + 17 integration, 6 new tests:
residual-zero-model ≡ arc-bound beam at n=4/5; guided rollouts deterministic +
absolute-lb_arc ≡ residual-zero move-for-move; seed-prefix 0 identity, deep prefix
(117/119 at n=5) still valid, mid prefix (60) at n=5/w2000 still 153). Clippy/fmt
clean. Smokes: `beam -n 5 --width 2000 --seed-prefix 50` → 153 (0.12 s);
`rollouts -n 5 --count 5 --epsilon 0.1 --seed 0 --model ml/models/linear_n5_boot1.json`
→ mean 195.2 / min 179; residual linear fit on `data/roll_n5_e0.05_s0.jsonl`
(held-out RMSE 6.49 vs lb_arc's 23.40) beams 153 at n=5/w2000; ε=0 rollouts guided by
that residual model hit 153 on all 5 rollouts. `ml/predict_check.py` now adds `lb_arc`
back for residual models so its metrics stay absolute.

**Next session (the actual rung-1 sweeps, n=6):**
- Train residual linear/MLP on the boot corpora (`data/boot_n6_*.jsonl`); beam sweep
  α ∈ {0.25, 0.5, 1}, widths 2000–32000 — does the residual anchor beat blend-0.075?
- Generate a guided-rollout corpus (ε ∈ {0.01, 0.05}, boot1/blend0.075 as guide),
  retrain, re-beam — the properly closed search → relabel → retrain loop.
- Seed-prefix scan at n=6: depth ∈ {60, 120, …, 700} × {arc bound, boot1 model},
  looking for where the learned beam diverges from greedy's 873 basin.

## 2026-07-27 (session 3) — learned score in beam: 874; phase-2 exit criterion met; 874 is a hard plateau

**Built: learned value function wired end-to-end** (committed as `6c8140f`).
`ml/` trains linear (numpy OLS) and MLP (2×64, numpy, Adam) predictors and exports
JSON; `src/model.rs` loads them; beam scores candidates `len + α·predict(features)`
in O(1) per expansion via `--model m.json --alpha a`. Score stays a pure function of
`(cur, visited, len)`, so keep-first dedup survives. n=5 gate: every model config
still finds 153.

**Headline: n=6 = 874, validated — minimum phase-2 exit criterion met.** First hit by
a bound-blended linear model (blend α=0.075) at width 2000 in 6.2 s; also hit by
`linear_n6_boot1` (α anywhere in [0.5, 2]). Beats the hand-bound beam at equal
wall-clock *and* at 4× its wall-clock (890 @ w2000; 883 @ w8000/18 s). One character
from rung 1 (greedy's 873), two from the record (872).

**874 is a hard plateau.** ~60-run sweep (two subagents): ~15 scorers — linear/MLP ×
{raw, bound-blend, bootstrap round 1/2, elite-only, trajectory-only, corpus mixes} —
widths 500–128 000, all converge on exactly 874. Ledger lessons, in order of value:

1. **The admissible anchor is non-negotiable.** Pure learned score (no bound term)
   cliffs to 1600+. Blending or bootstrapping *on top of* `lb_arc` is what works.
2. **Label quality beats model capacity.** Strong-policy bootstrap data (ε ≤ 0.05
   rollouts + beam trajectory relabels) lets even the linear model learn the 874
   floor; the MLP on the same data does no better (and much slower: ~220 s/run).
3. **Corpus mixing is catastrophic in both directions** (mixed-ε or round-1+round-2
   blends: 880–1532). Second-round elite corpora are too narrow and hurt.
4. **Held-out RMSE is uncorrelated with beam quality** once the floor is in — the
   best-RMSE model ever trained here beams at 887–1532. Models must be selected by
   beam result, full stop.

**Built: deterministic score jitter** (uncommitted until this session's commit).
`--jitter <eps> --jitter-seed <s>`: Zobrist hash of the visited set, maintained
incrementally, gives every candidate a pure-function-of-`(cur, visited)` offset in
`[0, eps)` — dedup argument intact, bit-identical to plain beam when off. Purpose:
diversified restart portfolios to shake the last character loose.

**Negative result, and a clean one: jitter cannot break 874.** Five portfolios,
~120 runs (session was cut by an accidental close after portfolio B; C re-run and
harvested this session):

| portfolio | model | jitter ε | runs | best |
|---|---|---|---|---|
| A | blend0.075 | 0.25–2.0 | 48 | 877 (most 884–891) |
| A2 | blend0.075 | 0.01–0.12 | 48 | 874 (never 873) |
| W4000 | boot1 @ w4000 | 2.0 | 5 | 874 (jittered: 877+) |
| B | boot1, elite1 blends | 0.01/0.06 | 48 | 874 (boot1 only) |
| C | mlp_boot1_blend0.25 | 0.01–0.06 | 3 | 874 |

Small jitter reproduces 874 repeatedly; larger jitter only degrades. Read: the
models all steer into the same basin and the remaining character is *structural* —
874 is not a tie-breaking accident we can restart our way out of.

**Status vs. the ladder:** exit criterion ✅; rung 1 (873) open — needs a new idea,
not more restarts; rungs 2–3 likely need phase 3's cycle-level move space (LKH-style
local improvement / tree-like constructions are what actually set records).

**Next session, concretely:**
- **Residual targets:** train on `cost_to_go − lb_arc` instead of raw cost-to-go —
  the model then only has to learn the *correction*, and the anchor is built into
  the label, not just the score blend.
- **Model-guided rollouts:** generate the next corpus with the learned score as the
  rollout policy (current corpora are ε-greedy on *hand* heuristics), closing the
  search → relabel → retrain loop properly.
- **Greedy-prefix seeding:** start beams from greedy prefixes of varying depth —
  873's basin provably exists; find where the learned beam diverges from it.
- Housekeeping: `ml/models/` sweep artifacts are untracked by design (only canonical
  models committed); `data/` corpora regenerable from logged seeds.

## 2026-07-27 (session 2) — arc features + arc bound; corpus; linear baseline beats hand bounds

**Built: weight-1 arc features, incrementally maintained.** Arcs = connected components
of the *unvisited* perms under weight-1 (rotation) edges — the refinement of cycles into
maximal unvisited runs. O(1) maintenance per move in both `Walk::advance` and the beam's
`State` (new `Graph::pred1` inverse-rotation table). `Features` gained `arcs` and
`succ1_unvisited` (`#[serde(default)]`, so old JSONL still parses). A from-scratch
recount oracle test pins the incremental update.

**Built: the arc bound — provably tighter, admissible.** Every arc must be first-entered
by a weight ≥ 2 edge except the one headed by `succ1(cur)`, so
`lb_arc = r + arcs − [succ1(cur) unvisited]` is admissible and dominates the cycle bound
pointwise (proof sketch in `src/bound.rs` docs; admissibility + dominance asserted along
greedy trajectories in tests). Beam takes `--bound cycle|arc`.

**Negative result worth keeping: the tighter bound does NOT help beam.** n=6:

| width | cycle | arc |
|---|---|---|
| 500 | 894 | 894 |
| 2000 | 890 | 891 |
| 8000 | 883 | 888 |

Beam is not A*: a pointwise-tighter admissible bound reorders the frontier but still
doesn't *predict*, and empirically ranks slightly worse. This kills the "just tighten
the hand bound" alternative and sharpens the phase-2 thesis — the evaluator must be a
predictor, not a bound. (`--bound` default stays `cycle`.)

**Built: trajectory logging.** `greedy --log f.jsonl` and `beam --log f.jsonl` replay
the final path through a `Walk` and emit the same JSONL records as rollouts
(`rollout::log_trajectory`; `BeamResult` now carries `path`). Test pins ε=0 rollout ≡
logged greedy trajectory, byte-identical.

**Corpus generated** (`data/`, gitignored): n=5 ε ∈ {.05,.15,.30} × seeds {0,1000} ×
400 = 2400 rollouts (288k records; ε=.05 hit the optimum 153); n=6 same ε, seed 0,
150 each = 450 rollouts (324k records); plus greedy/beam trajectory logs for both n.

**Linear baseline: the features carry real signal.** `ml/fit_linear.py` (numpy OLS,
held-out split by rollout, features + both hand bounds + bias):

| n | predictor | held-out RMSE | MAE | R² |
|---|---|---|---|---|
| 5 | lb_cycle | 51.7 | 42.3 | 0.36 |
| 5 | lb_arc | 51.5 | 42.1 | 0.36 |
| 5 | linear | **17.8** | 13.2 | **0.92** |
| 6 | lb_cycle | 428.1 | 352.5 | **0.05** |
| 6 | lb_arc | 426.3 | 350.5 | 0.06 |
| 6 | linear | **133.0** | 95.6 | **0.91** |

The n=6 row is the money quote: the hand bounds explain ~5% of cost-to-go variance —
a quantitative restatement of "beam prunes blind at n=6" — while a *linear* model over
six cheap features explains 91%. Escalation to GBT/MLP is justified per plan.

**Caveats to carry forward.** (1) Labels are behavior-policy returns (ε-greedy), not
optimal cost-to-go — mixed-ε corpora inflate variance-explained; the bootstrap loop
(search → relabel → retrain) is what fixes label quality. (2) RMSE 133 at n=6 is far
too coarse to steer 872-vs-890 endgames yet; what matters first is *ranking* frontier
states better than the bounds do.

**Next session, concretely:**
- Wire a learned score into beam: `score = len + α·predict(features)` with batch
  evaluation per level; keep the score a pure function of `(cur, visited, len)` so the
  dedup argument survives. Start with the linear model (its coefficients are just a dot
  product — no Python in the loop), sweep α and width at n=5 (must still find 153), then
  first learned-score n=6 runs vs the 873/890 baselines (success ladder rung 1).
- GBT baseline on the same corpus (sklearn if available) to see how much nonlinearity
  buys over linear before committing to an MLP.
- Remaining feature from the plan: residual cycle-graph degree stats (2-cycle adjacency
  between rotation cycles) — needs a cheap incremental formulation.

## 2026-07-27 — handoff prep; gap analysis; phase-2 success ladder

**Docs pass for fresh-agent handoff.** Added `docs/ARCHITECTURE.md` (code map: modules,
data structures, CLI data flow, JSONL schema, phase-2 extension points) so nobody has
to reverse-engineer `src/`. Reading order for a fresh agent is in CLAUDE.md.

**Gap analysis — where greedy stands vs. targets.** Greedy is provably the
sum-of-factorials construction, so:

| n | greedy | best known | gap | proven lower bound | gap to LB |
|---|---|---|---|---|---|
| 3–5 | 9 / 33 / 153 | same | 0 | same | 0 |
| 6 | 873 | 872 | 1 | 867 | 6 |
| 7 | 5913 (formula; not yet run) | 5906 | 7 | 5884 | 29 |

Consequences: (1) n ≤ 5 is a correctness harness only — greedy is already optimal
there, so no learning signal about *beating* anything exists below n=6. (2) The
phase-2 evaluator's bar is n=6.

**Phase-2 success ladder** (in order; each rung is a real milestone):
1. Learned-score beam **matches greedy (873)** at n=6 — currently hand-bound beam is
   17 chars worse (890 at width 2000), so this is not trivial.
2. Beam **finds 872** at n=6 (matches the record).
3. Anything **< 872** is a world record; anything ≥ 868 disproven only by exhaustion,
   so 867–871 is genuinely open territory.

**Next session, concretely:**
- Generate a large labeled corpus: `rollouts` at n=5 and n=6 with a few epsilons +
  seeds; also log states along greedy and beam trajectories (needs a small code
  addition — see ARCHITECTURE.md extension points).
- Fit a *linear* regressor on the existing features first; compare its cost-to-go
  RMSE against the hand bound's error on held-out rollouts. Only escalate to GBT/MLP
  if linear shows the features carry signal.
- Add residual-graph features next: cheap-edge connected components and residual
  cycle-graph degree stats, maintained incrementally in the walk state.

## 2026-07-26 — project start; phase 1 built

**Context.** Project born from a conversation about treating superpermutation
construction as chess-style game-tree search: permutations as nodes, added-length as
edge weight, heuristic evaluation + pruning instead of exhaustive enumeration. That
framing turns out to be the established one (ATSP on the overlap graph; Houston's 872
came from LKH). The genuinely open angle we're betting on: a *learned* cost-to-go
evaluator over residual-graph features instead of hand-derived bounds. Full framing in
THEORY.md.

**Decisions made.**
- Rust for the search core; JSONL boundary to a future Python model side; no GPU
  assumptions (small MLP over engineered features is the design point).
- Testbed discipline: n=4/5 (proven optima 33/153) are the correctness harness; n=6 is
  the first real hunting ground (best known 872, lower bound 867).
- Beam state tracks per-cycle remaining counts so the admissible bound
  `lb = r + k − [current cycle live]` is O(1) incremental.
- Weight-n "jump" edges kept out of adjacency lists; searches use an explicit fallback
  to the lowest-ranked unvisited perm so states can't dead-end.

**Built.** Graph (lex rank/unrank, weight-1..n−1 successor lists, 1-cycle decomposition),
deterministic greedy, level-synchronous beam with arena path reconstruction + dedup,
validator, epsilon-greedy rollout generator emitting `(features, cost_to_go)` JSONL,
CLI (`info`/`greedy`/`beam`/`rollouts`/`validate`), acceptance tests pinned to 9/33/153.

**Results.**
- All tests green (`cargo test --release`: 14 unit + 7 integration), clippy/fmt clean.
- Greedy: 9 / 33 / 153 / 873 for n=3..6 — exactly the sum-of-factorials construction,
  as required. All outputs validator-complete.
- Beam recovers the proven optima: n=4 → 33 (width 512, 0.007 s); n=5 → 153 (width
  2000, 0.19 s). **Phase-1 exit criterion met.**
- Surprise / key finding: at n=6, beam (width 2000) gives **890 — worse than greedy's
  873**. The admissible cycle bound `r + k − [cur]` stops discriminating between beam
  states at this size: most frontier states share nearly identical bounds, so the beam
  effectively prunes blind. This is the cleanest possible motivation for phase 2 — the
  evaluator, not the search loop, is the binding constraint.
- Rollouts (n=5, 200 runs, ε=0.15, seed 0): mean 214.85, min 178, 24 000 JSONL records.
  Plenty of spread between optimal (153) and mean — good label variance for regression.

**Same-day field news (Superpermutators Google Group, 2026-07-26).** Raudvere posted an
n=8 superpermutation of length **46204** — one below Egan's construction — verified by
Houston, who identified it as *tree-like*: standard kernel + 833 two-cycle extensions.
Echols followed with independently-checked n=9 (408,965) and n=10 (4,037,046)
candidates, each −1 vs. Egan. Two takeaways for us: (1) the cycle-level tree
representation planned for phase 3 is exactly the structure setting records right now;
(2) the community corpus lives at https://github.com/superpermutators/superperm — use
it for validation targets and known-solution features. Thread + Houston's extension
tree saved locally in `../extraDocs/` (outside the repo).

**Next session.**
- Start phase 2 feature engineering: residual cycle-graph degree stats and cheap-edge
  connected components, maintained incrementally.
- Generate a large n=4/5 rollout corpus; fit a linear regressor first and compare its
  cost-to-go error against the hand bound before reaching for a net.
