# CLAUDE.md — working conventions for this repo

## What this is

Research codebase hunting for short superpermutations via heuristic search, with a
planned learned value function.

## Fresh-agent reading order

1. `docs/JOURNAL.md` (latest entry) — current state, last results, concrete next steps.
   **Fresh agent: read `docs/HANDOFF-S55.md` right after it (supersedes
   S53; s55 headlines: P0 half-adjudicated — Grayzel Lean FAITHFUL but
   all-`native_decide`, `lake build` queued; Gheorghe's frame = our
   loop-cover grammar exactly, his O5 gap localized to slack covers
   only → the slack-tax attack is ours; Kramer–Mesner |G|>2 = NO by
   theorem + measurement; fl1577 proxy built, stall reproduced,
   GAIN_CRITERION=NO recipe demoted to control; cover freeze 183 is
   orientation-canonical — fully quotiented 178), then
   `docs/NOVELTY-DESIGN.md` — the active design doc** —
   headline state: **the neighborhood/rewrite-rule program is EXHAUSTED
   at both n** (s53 K₄ hunt closes the n=7 tier at 220 — no incomplete
   simplices, vocabulary mirror-complete via S53A/S53B in
   `data/loopswap/rules_n7_s53.tsv`, zero new reachability; s52b closes
   n=6: forward i4a + full 33-rule loop-swap, blind spot untargeted-
   fused SELF-maps only, promotion trade replay-dead 0 products);
   **a(6)=872 has two independent claimed proofs** (Gheorghe 209-cell
   preliminary + Grayzel Lean zero-sorries, mid-audit) — adjudication
   is P0; **Houston's abandoned 5905 program = our chains #0/#24**
   (both OPEN; score-15 kernels, no tractable asymmetric completion
   exists anywhere) — the 138 open chains + ledger cuts are P1; the
   ranked program P0–P5 + the do-not-respend list live in
   NOVELTY-DESIGN §3/§4, with three research surveys preserved at
   `../extraDocs/2026-07-31-research-*.md`. Project shell 220 / 9
   allocations; the **s51 rule tier** and the **K₄ law** (every
   cover-sharing quadruple = complete K₄); the m3 gate covers all 220;
   `up-1b8244ba04bb` is ARITHMETICALLY blind
   (536 > 534, door 34 > 24-fused, 536 ≢ 0 mod 6) — distinct from the
   (844,17) eleven. PUBLISHED shell 218 (PRs #52 AND #53 MERGED 2026-07-31, s56). Older
   state of the world, the engine-first premise, the executable natural-move tiers
   (i4a; loop-swap = I5, 102 novel classes PR #51; R-BND boundary-trade
   tier, spec `docs/RBND-RULE.md`, whose 4 novel (843,18) classes,
   `data/novel5906c/`, are PUBLISHED via PR #52 (merged 2026-07-31) —
   published n=7 shell 218, project shell 220; vocabulary = **398 moves = 864
   directed rules across FIVE tables**, annotation covers all 864;
   graph = `lswap_sym_edges_n7_ALL_union.tsv` (2,006) +
   `rbnd_edges_n7.tsv` (32-row) — hash12-normalize before unions; the
   12-class blind spot is closed against single rules, sequential
   chains, AND fused pairs both directions (s49 depth-1/depth-2 + s50
   full sumset 0/9,456 — replay-free rigidity trick,
   `analysis/counting/s49/fuse.py`); s49 w4 theorems: w=3 forced
   (Δlen = 3 − w), no length-conserving w≥4 boundary trade; the REV-w4
   lift shells `data/lift873_n6/` + `data/lift5907_n7/` are conjugated
   copies of loop-swap structure — s50 proved lift→move→drop = move,
   zero new connectivity; the s51-era fronts — untargeted fused sweep,
   w4 demotion/promotion, `up-1b8244ba04bb` anatomy — are ALL RESOLVED
   as of s52b/s53, see HANDOFF-S53), traps, and the session-end ritual.
2. `docs/ROADMAP.md` — which phase we're in and its success ladder.
3. The active design doc named by the journal's latest entry — **currently
   `docs/NOVELTY-DESIGN.md` (s53: the P0–P5 self-derived-novelty
   program — a(6)=872 adjudication, Houston's 5905 chains, shell
   descent, cover triage, instruments-first)**; before it,
   **`docs/SURGERY-DESIGN.md` (s28 built I1 `tail-atsp`; §9 has the M-R laws;
   §10 is the compound tier: s38 built I3 `--recomp2` and §10.8 records its
   as-built truth + the oracle refutation; §11 is the OPEN FRONT — the
   loop-cover frame: s39 theorem (THEORY §7) + cover census, s40 M-4a
   (the three rigid rewrite rules, §11.6), s41 I4-A applier + as-built
   results (§11.7): 8 novel 5906 classes in 2 new allocations, PUBLISHED
   as superpermutators/superperm PR #50, merged by Houston; s44's 102
   loop-swap classes merged as PR #51 — published shell 194; next: iterate
   rule-closure on the new classes, M-4b/M-4d)**;
   `docs/RECOMB-DESIGN.md` (s26, §8 outcomes + §8.4a recalibration) for
   what closed before it, and `docs/TRACKB-DESIGN.md` for the underlying
   Track B frame (its M3/§7 carry s26 corrections inline; §2 L1 carries
   the s27 per-allocation-profile update). s27 landed the per-allocation
   grammar + the fresh-doors corpus law; s28 landed the surgery design
   (block-reordering law, natural specimens, block-ATSP prototype) and the
   per-allocation M2 pass. ARCHITECTURE.md's "Track B implementation map"
   says where each task lands in the code.
4. `docs/ARCHITECTURE.md` — code map: modules, data structures, extension points.
5. `docs/THEORY.md` — math framing; read §6 for facts not worth re-deriving.

Current state in one line: **phase 3; Track B build IN PROGRESS — s22 landed
T0 (identity verified on 806 walks, general form
`waste = (S−1) + Σ(w−2)·inter + Σ(w−1)·intra`, canonical-reading lemma), L0
ledger (`analysis/trackb/ledger_l0.csv`, 78,813 allocations, live shell
34,272, M1 PASS 66.5% via LB-869 + NEW pass-over lemma ip ≤ 4(S−120)), T1
door atlas (150 canonical edges, orbit-verified, interior-perm filter data),
and L2 sojourn DFS (`src/sojourn.rs`, `sojourn-dfs` subcommand, 3 dedup
tiers) with M2 PASS in book mode (d=10, E=16, 746k nodes, 13,527 classes;
exact tier sound only to d≈6 = 5.9M nodes; orbit dedup proven worthless —
identity start breaks symmetry); s23 landed T3 (`sojourn-dfs
--dump-frontier` + `beam --seed-file` multi-seed depth-injection,
bit-identical to `--seed-prefix` on one greedy walk;
`analysis/trackb/record_to_seed.py` turns any record into seeds), C2 PASS
(n=5 pipeline finds validated 153 — needs exact dedup + ≥64 exemplars/class;
abstraction 1/class gives 154), and the C1 verdict: **oracle PASS** (beam
re-derives a known 872 byte-identically from its own prefix at depth ≥ 450,
residual w32000+endgame; learned+stratify is the WORST completer there,
899–917 — residual bound best by 15–30 chars) but **pipeline NOT PASSED —
completion-blocked**: even from the TRUE record opening at d=14 the ceiling
is 878, and 24,214 sound d=6 class exemplars saturate it at 879 (w8000 =
w32000); the gap to 872 lives in beam completion through levels ~60–450 and
needs a policy, not width; s24 landed T2 (`Scorer::Composed` = `len +
lb(bound) + α·pred`, CLI `--bound`+`--model` composes; admissible cap
`--max-len L`, lossless, beam can die honestly): **composed residual +
0.25·linear_n6_res_boot1 lifts the pipeline 879 → 874** (robust plateau
over α/width/exemplars/jitter; the 874s escape the records class to
greedy-shape S=120), the cap is proven sound (every uncapped-872 config
still finds 872, 3.7s→0.16s at d500) and capped pipeline runs die at 872
AND 873 — with the record's own trajectory having `len+lb_residual ≤ 872`
at every step (zero slack to prune until the end), this PROVES the midgame
ranking at levels ~60–450 is the sole remaining failure; capped beam from
depth ≥450 is now a fast completion oracle for NRPA tails; s25 landed NRPA
(`src/nrpa.rs` + shared `Grammar` in sojourn.rs — one move generator for DFS
and rollouts, M2 pin reproduced exactly; softmax policy over move features,
waste prior, early-tail, record warm-start, `--collect`): n=5 control PASS
(153 in 100 rollouts with prior=1), cold-start n=6 plateaus at 883 (no
gradient across the s23 blocked zone, depth stalls ~85/450), record
warm-start (reps 20, switch 500, w8000 tail, cap 872) **re-derives 872
end-to-end at rollout 1, byte-identical to seed** — oracle-grade PASS for
the policy pipeline; M3 (independent 872) OPEN: hunt design must be cap 874
+ collect ≤872 (cap-at-target starves the gradient — twice-measured), and
the **discriminator verdict is in**: 288 rollouts × 2 seeds collect ZERO
≤873 walks besides the seed record — the shell is thin, off-line deviations
cost ≥2 chars, local policy exploration cannot reach an independent ≤872.
s26 landed structural recombination
(`docs/RECOMB-DESIGN.md`, `src/corpus.rs` + `src/recomb.rs` +
`src/unionsearch.rs`): the splice closure of our local 296-record sample is
EXACTLY 298 walks (+2 hybrids, `data/hybrids872/` — s26b: both turned out
BYTE-IDENTICAL to known community strings, see NOTE.md there); union-edge
DFS (usage-ordered, undo-based, strand pruning = lossless union-specific
prune, 4.3M nodes/s) is built and controlled, but union ENUMERATION is
intractable even for 2-record sub-corpora (blocked zone, third measurement)
— honest products are single-record controls, truncated hunts, cap-871
decision runs (also bound-blocked, JOURNAL s26); near-miss splice repair
KILLED by measurement (symdiff bimodal 0 or ≥20). **s26b/c RECALIBRATION
(read before citing any "all known 872s" claim): the community corpus
(superpermutators/superperm) holds 50,009 872s = 22,062 relabel+reversal
classes — our 296 was a 1.3% sample (290 classes, all upstream). Census
over all 22,062 (`analysis/counting/upstream872_structure.py`, archive
`data/upstream872/`, gitignored): waste identity 22,062/22,062; exactly 8
specimen-backed L0 allocations — (145,3,0,0,0)=21,144 (the records class,
95.8%), (143,5,0,0,0)=470, (140,6,1,0,0)=388, (142,6,0,0,0)=19,
(135,9,2,0,0)=18, (140,8,0,0,0)=10, (138,8,1,0,0)=9, (141,7,0,0,0)=4 —
w4-bearing 872s EXIST; 8 Vlad cells in 1:1 correspondence (his 11 tests
pass corpus-wide; s20's 'single cell' was sample bias); 545 split profiles
(grammar hard-codes 1) and split types 1|5, 5|1 exist (4 classes); the
community corpus is SPLICE-CLOSED up to symmetry (5 closure walks, all
equivalent to known).** **s27 landed the re-scope:
per-allocation grammars are DATA (`analysis/trackb/profiles/a*.txt` from the
census, `--profile-file` on sojourn-dfs/nrpa, `SplitProfile::from_file`), the
new `grammar-check` subcommand replays any string through a class grammar
(`Grammar::replay` public), and ALL 22,062 community classes replay 719/719
through their own allocation's grammar (29 s; 8 specimens committed at
`data/upstream872_specimens/`, 3 pins in `tests/alloc_grammar.rs`). NEW
corpus law (door-pricing census, `upstream872_door_pricing.py`): every
weight≥3 door in every known 872 opens an UNTOUCHED cycle (66,999/66,999) —
the opt-in `--fresh-doors` cap (calibrated, not a theorem); −10%/−20%
opening classes at exact d=6 on (145,3)/(143,5), and (143,5) exact d=6 now
completes (22M nodes, 28 s). Door placement: records-class w3 doors are
bimodal opening/endgame, extra doors of other allocations are MIDGAME
(levels ~60–450, the blocked zone); w4 strictly midgame. Waste-146 map
(`alloc_neighbors.py` → `waste146_neighbors.tsv`): every anchor is 1 unit
edit (S−1 merge or d3−1 demotion) from an open 871 allocation — all 13
distance-1 targets are s11-subregion-closed (871 must leave the certificate
grammar), and 3 distance-2 targets need ip=1, which NO known 872 uses.**
s27b re-scoped the M3 gate: `analysis/counting/m3_check.py` + committed
canonical index — every candidate ≤872 must pass it (exit 2 = novel vs all
22,062 classes up to relabel+reversal). NEXT (s28, see docs/HANDOFF-S28.md) =
cross-class surgery design (braid-diff (143,5) vs (145,3)
neighbors around the extra midgame doors), per-allocation M2 +
union-restricted BEAM, the ip=1 targets;
cheap closure probes queued: perfect-ride ATSP
(closes all 616 S=120 live classes). Track B downgraded-not-retired s20 (Vlad's preliminary
a(6)=872 claim; n=6 window unconditionally still {869..872}); n=7 5905
campaign survives (his conditional a(7) ≥ 5896 is δ≤11 vs our δ=21 bar);
Track C v2 parked on the 2.4× scoring-overhead fix; farm and Mac idle
(JOURNAL s23 is the handoff)**
— headline: **Egan−1 = 872 is optimal in the gain-one certificate grammar at n=6**
(skip-priced ledger waste = 148 − K/4 + Σskip/4 + f4 + 2f5; forced-map period 4;
absolute pivot confinement; max V = 8, all 12 optimal chains fail the cover —
exhaustive proofs). Sub-872 must leave the grammar. Tracks: **Track B** (n=6
out-of-grammar opening-first search — designed, next up), **Track A** (n=7
max-V₇ campaign — V₇ ≥ 15 + cover beats 5906), **Track C** (learned evaluator —
the thesis; deploys into Track B per TRACKB-DESIGN §5 once C1 passes).
**Track C v2 COMPLETE s19** (`docs/TRACKC2-DESIGN.md`, `analysis/trackc/RESULTS-s19.md`,
`analysis/trackc/WORKFLOW-V2.md`, `docs/OPERATIONS.md`): learned COLUMN choice built,
parity byte-clean, G2v2 formal GO in nodes (median 1.50× at Δ=0) — but the **final
verdict is wall-clock NO-GO as deployed**: feature scoring costs 2.4–2.6× per node
(solo probe 495k→208k nodes/s), so the node win nets ~0.6× in wall time. Mechanism
PROVEN (column choice shrinks exhaustion trees — impossible for rows), deployment
blocked on overhead; G1/G1b/G3 all negative (no covers at n=7, 0/6 trial closures;
the pw1 Δ=1 n6std 77-node cover did not transfer). What the model learns is K-class
CANONICALIZATION, not per-instance insight — confirmed at 53-chain diversity (pw2 ≈
pw1, cos .9996; equal-size tie-break acc stuck at .52; a separate tie-break head is
worth ~4pp, optional). Models: `ml/models/trackc2_pw1` (deployed), pw2/reg2
(artifacts). Farm corpora home at `analysis/trackc/runs/v2/farm/` (6M pairs,
9M records, 53 chains). **Next lever, in order: cut the 2.4× scoring overhead
(target ≤1.2×), then re-gate G2v2 in WALL-CLOCK, then portfolio pass-2 over the
138 open chains.** Side result s19: `--bound residual` (docs/RESIDUAL-BOUND-DESIGN.md)
— new admissible bound, arc-bound optimality theorem, door terms proven, 10,400
tablebase states 0 violations, hand-bound stratified beam **902→894**; the Hunter
q_k root strength is proven NON-localizable; `--bound` and `--model` do not compose
yet. Counting calibration in `analysis/counting/` (local rules cap at L =
n+n!+(n−1)!−2 exactly; the "all known 872s share 575/141/3" claim was
SAMPLE BIAS — s26c census: 8 multisets over 22,062 classes).
**Track C v1 landed s17** (`docs/TRACKC-DESIGN.md`, `analysis/trackc/RESULTS-s17.md`):
guided DLX row ordering works in principle (22× on n=6, real cross-n transfer) but
NO-GO on the n=7 cover gates at 60 min; v2 lever = learned column choice. Side
product: `analysis/trackc/dlx7g` is a fast third refutation engine; its census
sweep is FINISHED (all 223 chains attempted, no SAT) — ledgers committed at
`analysis/cover7/results_n7_merged.csv` (canonical, 85 closed / 138 open) and
`results_n7_dlx_sweep.csv` (raw DLX rows). No compute is running anywhere.
Prior state: —
from-scratch bests: n=6 **873** (stratified beam, ~8 s), n=7 **5913** (same config
+ `--allow-n-mismatch`, ties greedy, ~5.5 min; bar 5907). Item 3 verdict (s8): the
deficit features (`half_open`/`nearly_done`/`w2_bridges`, v2 11-feature contract)
carry the expert signal but no linear/MLP evaluator converts it — the 872 structure
needs credit *conditional on completing the weave*. Item 4 verdict (s9): the exact
endgame tablebase (`src/endgame.rs`, Held–Karp, theorem-grade, m ≤ 25) proves the
endgame door shut — the stratified config's entire w2000 frontier at r=20 completes
to ≥ 873 (unstratified ≥ 874; n=7 ≥ 5913), and every known record (296 × 872s,
3 × 5907s) plus all our 873s have provably optimal tails. The missing character is
won strictly before the last ~25 perms ⇒ all weight on **item 5** (cycle-level
moves; weave as a move, kernel as a parameter — Robin's thread reply + 5906
boundary fact; tablebase becomes the terminal solver). Expert corpus: 296 distinct
872s (`data/records872/` + `data/gain1_872s/`) — a 1.3% SAMPLE; the full
community corpus is 22,062 classes, archived at `data/upstream872/` (s26b/c),
Chaffin prefixes in `data/chaffin/`, field news in `../extraDocs/2026-07-27-urdvr-email-and-repo.md`
`../extraDocs/2026-07-28-urdvr-lean-lower-bound.md` (Lean-formalized LB:
**S(6) ≥ 869, S(7) ≥ 5888, S(8) ≥ 46103** — n=6 window now {869..872}, n=7 window
[5888, 5906]; "exitless paths are exhausted, improvement must come from the
reduction" is the stated frontier), and
`../extraDocs/2026-07-28-urdvr-lift-nge8.md` (Lean lift theorem: **S(n) ≤
Egan(n)−1 for ALL n ≥ 8**, certificate-level induction; 6→7 lift provably
fails; the 5906 record is outside his liftable grammar — mirror of our n=6
result; NO E−3 target exists in his program, so 5905 remains ours alone;
candidate DLX pruning rule in `StandardKernelHighMissingObstruction.lean`), and
`../extraDocs/2026-07-29-vlad-a6-872-claim.md` (Vlad Gheorghe's **preliminary,
for-refutation claim that a(6) = 872** — 209-cell confinement partition, both
offline verify tiers pass here, top rung at effective tier `L` with two open
soundness obligations; **we cross-validated his coordinate frame on 299 of our
words, 299/299 in cell (0,5,25,0) — but s26c re-ran the census on all 22,062
community classes: his 11 identities pass corpus-wide, and the corpus
occupies 8 cells (1:1 with the 8 L0 allocations), so the 'single cell' was
our sample bias, not his structure** (`analysis/counting/upstream872_vlad_cells.txt`);
n=6 window unconditionally still
{869..872} so **Track B is downgraded, not retired**; his conditional a(7) ≥ 5896
is δ≤11 vs our δ=21 target, so **5905 survives** — watch whether n=7 pushes past
δ≈21; tool `analysis/counting/coords_a6_872_frame.py`), and
`../extraDocs/2026-07-29-tomaz-kristan-5906-repeat.md` (Kristan: record-TYING
5906 at n=7 with a repeated permutation window — RESOLVED: the repeat is
bookkeeping, the string is **byte-identical to a simple-path reading** (a
weight-3 edge whose appended `537` re-spells a covered perm), and every
superperm string is a simple walk over first occurrences, so **simple-path
pruning is provably lossless and no search change is needed**; the string is
still genuinely new — the only known non-symmetric 5906, inequivalent to all 83
published; verify: `../extraDocs/verify_tk5906.py` +
`../extraDocs/check_corpus_5906.py` + `../extraDocs/shortcut_tk5906.py`, all
exit 0).

**Live compute (check this first if picking up cold):** a remote 28-core Windows
PC (`ssh transcribe`) hosts the n=7 refutation farm — **currently IDLE**, pass 1
complete, and the s19 Track C v2 generation sweeps (trackc2 sweep-1 162/162 +
gen2 165/165) are DONE with corpora shipped home; farm ops conventions and
hard-won lessons (OOM wedge, PID recycling, detached-stdout loss) are in
`docs/OPERATIONS.md` — read it BEFORE launching anything. Operating runbook:
`analysis/cover7/REMOTE-FARM.md`; scripts: `analysis/farm/` (trackc2 =
`tc2*.ps1`, status `tc2status.ps1` / `tc2status2.ps1`). Legacy status one-liner:
`ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\satstatus.ps1"`
(`status.ps1` is the retired PermutationChains-era reporter).
**Pass 1 is COMPLETE (s18): 223/223 chains attempted, 41 unconditionally
refuted, 182 undecided at 30 min, no SAT** — census committed at
`analysis/cover7/results_n7_pass1.csv`. Decidable chains are fast (median 1.85
min, 25/41 under 5 min), so the survivors need a better *method*, not a
bigger budget. The farm is currently IDLE. **s17b update: the merged
multi-engine census is `analysis/cover7/results_n7_merged.csv` — 85/223
closed (52 structural zero-candidate-column refutations, 44 of them missed by
the SAT pass; 33 search-UNSAT), 138 open.** Before pass 2, reconcile
satworker's encoding with `chain7` (chain 34 should be instant UNSAT; see
JOURNAL s17b).
It runs a CaDiCaL **refutation** engine; ledger
`F:\superpermFarm\results.csv`. UNSAT = a chain unconditionally closed; a SAT
would be a candidate **world record**, auto-compiled and then validated with
`validate -n 7 --file <f> --complete` before believing anything. Two hard facts
from s15: Egan's PermutationChains Windows build is BROKEN (all its earlier farm
output is void), and **no engine we have can FIND a cover even on known-SAT
control instances** — the 5907/5906 words we "compiled" were reconstructed from
published words, not discovered. Treat the farm as a refutation census, not a
route to a record.

## Commands

```bash
cargo test --release                 # acceptance tests are pinned to proven optima (9/33/153)
cargo clippy -- -D warnings
cargo fmt
cargo run --release -- greedy -n 5
cargo run --release -- beam -n 5 --width 2000
cargo run --release -- rollouts -n 5 --count 200 --epsilon 0.15 --seed 0 --out out.jsonl
cargo run --release -- validate -n 5 <string>

# TRACK B (s22) — waste-identity verifier, L0 ledger, door atlas, sojourn DFS:
python3 analysis/trackb/verify_identity.py <files with superperm strings>   # T0; exit 0 = general identity holds
python3 analysis/trackb/enumerate_l0.py                                     # regenerates ledger_l0.csv + M1 stats
cargo run --release -- atlas -n 6 > raw.tsv && python3 analysis/trackb/door_atlas.py raw.tsv  # T1 verify + canonical TSV
cargo run --release -- rollouts -n 6 --count 100 --epsilon 0.15 --seed 0 --out f.jsonl --strings f.strings  # rollout strings for T0
# L2 opening DFS on the records' class; --dedup exact = sound (d<=6), abstraction+--exemplars = book mode (M2 config):
cargo run --release -- sojourn-dfs -n 6 --class 145,3,0,0,0 --records-profile --depth 10 --dedup abstraction --exemplars 16
# s27 per-allocation grammars: profile files are census data (regenerate with upstream872_structure.py
# --profiles-dir); --fresh-doors = corpus law (all heavy doors open untouched cycles), calibrated not proven:
cargo run --release -- sojourn-dfs -n 6 --class 143,5,0,0,0 --profile-file analysis/trackb/profiles/a143_5_0_0_0.txt --depth 6 --dedup exact --fresh-doors --max-nodes 30000000
# grammar-check: replay strings through a class grammar (forward-renumbers; exit 0 iff all replay fully):
cargo run --release -- grammar-check -n 6 --class 141,7,0,0,0 --profile-file analysis/trackb/profiles/a141_7_0_0_0.txt data/upstream872_specimens/872.up-6dbae421a839.txt
python3 analysis/counting/upstream872_door_pricing.py data/upstream872     # door-position/freshness census (s27 law)
python3 analysis/trackb/alloc_neighbors.py                                  # waste-146 targets vs the 8 anchors
# M3 gate (s27b): EVERY candidate <=872 goes through this + the Rust validator before any claim.
# Exit 2 = novel vs all 22,062 known classes (relabel+reversal); index is committed, no archive needed:
python3 analysis/counting/m3_check.py <candidate.txt>
# T3 (s23) — frontier seed dump + multi-seed completion beam (C1/C2 pipeline; residual is the best completion bound):
cargo run --release -- sojourn-dfs -n 6 --class 145,3,0,0,0 --records-profile --depth 6 --dedup exact --dump-frontier f.tsv --dump-per-class 16
cargo run --release -- beam -n 6 --width 8000 --seed-file f.tsv --bound residual --endgame 20 --endgame-top 400
python3 analysis/trackb/record_to_seed.py data/records872/872.0053cad.txt 6 450 > seed.txt  # any string -> seed line(s); 0 = full path
# T2 (s24) — composed scorer (best completion config, pipeline 874) + admissible cap (lossless; may report NO completion):
cargo run --release -- beam -n 6 --width 8000 --seed-file f.tsv --bound residual --model ml/models/linear_n6_res_boot1.json --alpha 0.25
cargo run --release -- beam -n 6 --width 8000 --seed-file seed.txt --bound residual --max-len 872
# NRPA (s25, src/nrpa.rs) — nested policy adaptation over the sojourn grammar, capped-beam tail finish.
# --prior biases rollouts toward cheap moves (essential); --early-tail completes in-grammar dead-ends with
# the unconstrained tail beam (essential in the records class — without it every random rollout dies):
cargo run --release -- nrpa -n 5 --class 60,10,0,0,10 --level 2 --iters 10 --switch-depth 40 --tail-width 1000 --prior 1   # control: finds 153
# record warm-start hunt (s25 verdict config): cap 874 keeps the gradient alive, collect catches any <=872;
# reps 20 re-derives the seed 872 at rollout 1 (cold start plateaus at 883 — don't bother without --warm-start):
cargo run --release -- nrpa -n 6 --class 145,3,0,0,0 --records-profile --level 2 --iters 12 --switch-depth 500 --tail-width 8000 --max-len 874 --prior 3 --early-tail --warm-start data/records872/872.0053cad.txt --warm-reps 20 --collect 872 --seed 3

# s28 surgery instrument I1 — tail block-ATSP (docs/SURGERY-DESIGN.md §4/§8; src/tailatsp.rs).
# Exact block-order optimization of every walk tail; anchor adapts deeper until <= --max-blocks.
# optimum < actual = 871 candidate (auto-materialized+validated, exit 2; STILL run m3_check).
# Corpus law (s28): ALL 22,062 classes are block-order-optimal at anchor >= 585:
cargo run --release -- tail-atsp -n 6 --dirs data/upstream872 --anchor 585 --quiet
# --ties collects equal-cost orders landing in a DIFFERENT allocation (oracle: re-derives the
# (142,6) partner of the committed pair at data/surgery_specimens/ from its (143,5) side):
cargo run --release -- tail-atsp -n 6 --dirs data/surgery_specimens --anchor 580 --ties --out-dir out/
# s30 I2a — --merge tries every single same-cycle block merge (the S-1 unit edit) exactly:
# shorter = 871 candidate (exit 2, M3 ritual); equal length = new 872 at S-1 (always a new
# allocation; every merge-eq-* through m3_check). Law: anchor >= 585 has ZERO merge completions:
cargo run --release -- tail-atsp -n 6 --dirs data/upstream872 --anchor 520 --max-blocks 40 --merge --quiet --out-dir data/surgery_finds
# s31 recomp-1 — --recomp tries EVERY single-cycle recomposition (all arc-partitions of each
# tail cycle; subsumes --merge, ~1300 moves/walk, ~5 s/walk at anchor 585). Same-allocation
# equal-cost completions are ~48% of moves and (sampled) all equivalent-to-known:
cargo run --release -- tail-atsp -n 6 --dirs data/upstream872 --anchor 585 --recomp --quiet --out-dir out/

# s38 I3 --recomp2 (SURGERY-DESIGN §10.8) — PAIR recompositions on two distinct tail
# cycles under T1 (combined net ∈ {−2,−1,0}) + T2 (no size-1 part in the moved cycle's
# composition), plus single prefix-part extraction of straddling cycles. Shorter =
# candidate (exit 2, M3 ritual); equal-length new-allocation = written; n=7
# (844,17)↔(843,18) equal = KRISTAN SEAM banner; every find is Λ-checked (loop-relation
# tripwire). --recomp2-tight = nets −2/−1 only (~4× cheaper); --recomp2-wide = T2 off.
# Measured: ~370 s/walk @520 n=6 (full nets), ~90 s/walk @4840 n=7. s38 verdict: the
# natural 2-compound is NOT reachable this way (extraction is +6-lossy) — the compound
# tier lives in midgame ORDER; this instrument's product is the closure negative:
cargo run --release -- tail-atsp -n 6 --dirs data/upstream872 --anchor 520 --max-blocks 42 --recomp2 --recomp2-tight --quiet --out-dir data/surgery_finds
cargo run --release -- tail-atsp -n 7 --dirs data/upstream5906,data/upstream5907 --anchor 4840 --max-blocks 56 --recomp2 --quiet --out-dir data/surgery_finds

# s33 n=7 corpus (committed: data/upstream5906 = 84 known 5906 classes incl. Kristan's,
# data/upstream5907 = 3 urdvr 5907s; rebuild: analysis/counting/upstream5906_dump.py).
# The whole instrument ladder is n-generic — anchor bands scale by perm count
# (4905/5040 ~ n=6's 585/720; 4840 ~ 520; 4770 ~ 450). s33 laws: block-order-optimal
# at all 3 bands; 0 cross-allocation ties; 0 equal-cost merges (stricter than n=6);
# recomp-closed at 4905 (199,391 moves, 49% equal-cost, all rediscoveries):
cargo run --release -- tail-atsp -n 7 --dirs data/upstream5906,data/upstream5907 --anchor 4905 --recomp --quiet --out-dir data/surgery_finds
python3 analysis/counting/upstream5906_structure.py    # L0 census: 6 pure-w3 allocations, Kristan's (843,18) alone
# M3 gate is n-generic since s33 — EVERY n=7 candidate <=5906 goes through it. The index
# covers ALL published data: s34 decoded the twoCycles files (annotations, not solutions):
python3 analysis/counting/m3_check.py -n 7 <candidate.txt>
# s34 2-loop laws (upstream5906_twocycles.py re-verifies, exit 0): every known 5906 uses
# EXACTLY 142 distinct 2-loops (all 6 allocations, Kristan incl.), 5907s use 143, and
# length = 5764 + #2loops on all 87 — a 5905 in this frame is a 141-2-loop cover:
python3 analysis/counting/upstream5906_twocycles.py

# s39 loop-count THEOREM (THEORY §7): length >= n!+(n-1)!+(n-3)+Λ for every pure walk;
# records = tight loop covers. loop_ledger_probe verifies the theorem terms per walk,
# stress-tests the sign on random walks, and censuses used-loop COVERS (the near-perfect
# class invariant whose only collisions are the natural edit boundaries + Kristan seam):
python3 analysis/counting/loop_ledger_probe.py walk 6 data/upstream872_specimens/*.txt
python3 analysis/counting/loop_ledger_probe.py cover 7 data/upstream5906
python3 analysis/counting/loop_ledger_probe.py random 4 3000 1 4

# s40 M-4a — anatomy of the cover-sharing pairs (the three rigid rewrite rules,
# SURGERY-DESIGN §11.6) + coarse rule-context census over the n=6 archive:
python3 analysis/counting/m4a_pair_anatomy.py            # all 13 pairs, exit 0 = verified
python3 analysis/counting/m4a_pair_anatomy.py scan       # carrier counts by allocation

# s41 I4-A mode 0 — the rewrite-rule applier (§11.7). oracle = re-derive all 13
# pairs byte-identically; apply = literal rules; apply-sym = all n! relabelings ×
# both orientations, products canon-gated inline (novel classes written+bannered,
# rediscoveries become edges of the natural-move graph). THIS is what produced the
# 8 published novel 5906s (data/novel5906/, PR #50). --only fwd/rev filters:
python3 analysis/counting/i4a_apply.py oracle
python3 analysis/counting/i4a_apply.py apply-sym data/upstream5906 data/novel5906 --out out/
python3 analysis/counting/i4a_apply.py apply-sym data/upstream872 --only rev --out out/
# n=7 novelty gate covers published + our discoveries (two committed indexes):
python3 analysis/counting/m3_check.py -n 7 <candidate.txt>

# s43 tail-conjugacy detector — the non-census signal (JOURNAL s43, HANDOFF-S43):
# inequivalent classes sharing literal relabel-conjugate traversal suffixes. Anchored
# census is O(N); --pairs annotates vs the natural-move graph; --all = full pairwise
# null distribution (n=7-sized corpora only); --deep binary-searches deepest shares:
python3 analysis/counting/tail_conjugacy_census.py -n 7 data/upstream5906 data/novel5906 --anchor 4840 --pairs out/pairs.tsv
python3 analysis/counting/tail_conjugacy_census.py -n 6 data/upstream872 --anchor 180 --pairs out/pairs_n6.tsv
python3 analysis/counting/tail_conjugacy_census.py -n 7 data/upstream5906 data/novel5906 --all out/all_n7.tsv
# pair anatomy in theorem coordinates (aligned frame; doors/rotors/loops diff) +
# relabel-canonical swap signatures (equal = same rigid move; committed censuses
# at data/tailconj/tail_swap_sigs_n{6,7}.tsv — n=6: 14 rules, top two 46+20 pairs):
python3 analysis/counting/tail_pair_anatomy.py -n 6 out/pairs_n6.tsv --dirs data/upstream872 --min-perms 400 --signature --sig-out sigs.tsv

# s44 I5 — the loop-swap applier (JOURNAL s44; the s43 tier made executable).
# extract: literal entry-replacement rules from tail-conjugate pairs (aligned frame),
# deduped over n! relabelings -> rule table TSV (committed at data/loopswap/).
# oracle: re-derive every anatomized pair byte-identically (1,300/1,300 s44).
# apply-sym: conjugated sweep, inverted-index fast path, products canon-gated inline
# (novel -> written+bannered, STILL m3_check them; rediscoveries -> edge TSVs).
# This produced the 102 novel 5906s in data/novel5906b/ (fixed point 60→34→8→0):
python3 analysis/counting/loopswap_apply.py oracle
python3 analysis/counting/loopswap_apply.py extract -n 7 data/tailconj/tail_all_n7.tsv --min-perms 256 --rules-out out/rules_n7.tsv
python3 analysis/counting/loopswap_apply.py apply-sym -n 7 --rules data/loopswap/rules_n7_a256.tsv --dirs data/upstream5906,data/novel5906,data/novel5906b --out out/products
python3 analysis/counting/loopswap_apply.py apply-sym -n 6 --rules data/loopswap/rules_n6_a360.tsv --dirs data/upstream872 --out out/p6 --dry-run  # sizing (no replays)
# s45: at gen-2 scale (604 rules, data/loopswap/rules_n7_a4840_gen2.tsv) a single
# apply-sym process needs ~8-9 GB and OOMs -> SHARD BY RULE at <=12k rule-entries
# per shard (exact: canonical rules have disjoint relabeled-instance sets), one
# --out dir per shard, then union the edge TSVs. Always --dry-run to size first.
# s46: the sub-256 band added 240 rules (vocabulary 862, data/loopswap/rules_n7_a4840_band200.tsv);
# the 194-class shell is CLOSED under all 862 loop-swap rules AND the i4a tier (0 novel).
# Graph analyses use data/loopswap/lswap_sym_edges_n7_ALL_union.tsv (2,003 undirected edges).

# s26 structural recombination (docs/RECOMB-DESIGN.md; src/recomb.rs + src/unionsearch.rs):
cargo run --release -- recomb -n 6 --dirs data/records872,data/gain1_872s --emit-dir data/hybrids872   # 0.25s; pins: 298 closure walks, 2 hybrids
# union-edge DFS — enumeration mode truncates at any feasible budget (design §8.2); --tt = decision/optimality mode:
cargo run --release -- union-dfs -n 6 --dirs data/records872,data/gain1_872s --cap 872 --bound residual --out-dir data/union_finds --max-nodes 200000000
cargo run --release -- union-dfs -n 6 --dirs data/records872,data/gain1_872s --cap 871 --bound residual --tt

# CURRENT BEST FROM SCRATCH — stratified learned beam, validated 873 (n=6), ~8 s (phase-3 item 1, JOURNAL s7):
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1 --stratify --strat-quota 4 --strat-bucket 1
# learned-score beam without stratification (phase 2) plateaus at 874 with the canonical boot1 model:
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1
# diversified restart (deterministic jitter; ε=0 is bit-identical to no jitter; anti-composes with --stratify):
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --jitter 0.03 --jitter-seed 7
# rung-1 seeded hybrid — a second, distinct 873 (n=6), ~2 s (three 873s known: greedy's, this, the stratified):
cargo run --release -- beam -n 6 --width 2000 --seed-prefix 350 --model ml/models/linear_n6_boot1.json --alpha 1
# two-ended (deque) beam, phase-3 item 2 probe (NO-GO but kept in-tree; arc2 bound by default, --model for transfer):
cargo run --release -- beam2 -n 5 --width 2000
# rung-1 mechanisms (all compose):
cargo run --release -- beam -n 6 --width 2000 --seed-prefix 120          # greedy-prefix seeding (0 = plain)
cargo run --release -- rollouts -n 6 --count 200 --epsilon 0.05 --seed 0 --model ml/models/linear_n6_boot1.json --alpha 1 --out out.jsonl  # model-guided
python3 ml/fit_linear.py data/roll_n6_*.jsonl --residual --export m.json # residual target (beam adds lb_arc back)

# exact endgame tablebase (phase-3 item 4, JOURNAL s9) — verdicts are theorems:
cargo run --release -- endgame -n 6 --greedy --remaining 24            # optimal completion of a prefix (also --file <s.txt>; m <= 25, RAM ~2^m)
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --alpha 1 --stratify --strat-quota 4 --strat-bucket 1 --endgame 20 --endgame-top 200  # exact-solve top frontier states at r=20

# record autopsy tooling (JOURNAL s5):
cargo run --release -- trace -n 6 --file data/records872/872.0053cad.txt --model ml/models/linear_n6_boot1.json --alpha 1 --score-log scores.tsv
cargo run --release -- beam -n 6 --width 2000 --model ml/models/linear_n6_boot1.json --cutoff-log cutoffs.tsv  # per-level prune thresholds

# training side (numpy only; see docs/ARCHITECTURE.md "ml/" section):
python3 ml/fit_linear.py data/roll_n6_*.jsonl
python3 ml/predict_check.py ml/models/linear_n6_boot1.json data/roll_n6_*.jsonl
```

Always benchmark and search in `--release`; debug builds are ~50× slower in the hot loop.

## Hard invariants — do not break

- Greedy with min-weight + lexicographic tie-break MUST produce 9, 33, 153 for n=3,4,5.
  If a graph/ordering refactor changes these numbers, the refactor is wrong.
- The lower bound must stay **admissible** (never exceed true remaining cost) — beam
  pruning correctness and any future branch-and-bound depend on it.
- Every produced string must pass the validator before being reported as a result.
- Rollout JSONL schema changes must be backward compatible or version-bumped — trained
  models depend on it.

## Conventions

- Symbols are `1..=n` as u8, rendered as ASCII digits.
- Ranks are lexicographic (Lehmer). Cycle = weight-1 rotation class, `(n−1)!` of them.
- New search features must be maintainable incrementally (O(1) or O(n) per expansion) —
  anything O(n!) per node is a non-starter at n ≥ 6.
- `beam.rs` does NOT reuse `walk.rs` — it keeps its own `State` counters so candidates
  score in O(1) without cloning, and `beam2.rs` keeps a third copy (`State2`, the deque
  searcher). Any new incremental feature must be maintained in `Walk::advance` AND the
  beam's `State`/`score_move` — and in beam2's `State2` if beam2 should score with it
  (see ARCHITECTURE.md, extension points). Also note: beam dedup assumes the score is a
  pure function of `(cur, visited, len)` (`(front, back, visited, len)` in beam2) — a
  learned evaluator must preserve that or the keep-first dedup argument breaks.
- Every working session ends by appending a dated entry to `docs/JOURNAL.md` and, if
  results changed, updating the README results table.

## Session workflow for AI agents

1. Read `docs/JOURNAL.md` (latest entry) → know where we left off.
2. Do the work; keep `cargo test --release` green.
3. Update JOURNAL.md (+ README results if applicable), commit with a descriptive message.
4. **Hand off to a fresh agent.** Every session ends with the repo cold-start
   ready: the JOURNAL entry must carry concrete next steps, and when the front
   has moved enough that `docs/HANDOFF-S<N>.md` is stale (menu items done, new
   traps, corpus/state changed), refresh it — write `HANDOFF-S<new>.md`
   superseding the old one and repoint the reading orders here and in the agent
   docs. Assume the next session starts from zero context.
