# superPermutationResearch

Search-based research on **minimal superpermutations**: the shortest string that contains
every permutation of `{1..n}` as a contiguous substring.

The thesis of this project: minimal-superpermutation hunting is single-player game-tree
search — a walk through the permutation overlap graph — and the frontier question is not
*whether* to do heuristic search with pruning (that's how every modern record was found),
but whether a **learned evaluation function over residual-graph structure** can prune
better than the hand-derived waste/cycle bounds. See [docs/THEORY.md](docs/THEORY.md) for
the full framing and [docs/ROADMAP.md](docs/ROADMAP.md) for the phased plan.

> **Founding thought (2026-07-26, preserved verbatim):** *"What if we view it as a game
> where the goal is to create the shortest superpermutation by taking turns picking nodes
> down a tree — and then use an evaluation system similar to chess engines to decide what
> the next best move is?"*
>
> Everything since is that sentence maturing, not being replaced: the beam scorers are the
> evaluation function, the endgame tablebase is literally the chess analogue (exact play
> once ≤ 25 perms remain), and Track C deploys the same idea one level up — the "moves"
> become certificate/cover decisions (which column to branch on in the DLX game tree),
> where an ordering can never cost correctness, only time.

## Status

**Latest (session 25, 2026-07-29): NRPA.** The policy layer prescribed by the
s24 verdict is built (`src/nrpa.rs` + a shared `Grammar` move generator in
`src/sojourn.rs`): softmax policy over move features, nested adaptation,
capped-beam tail finish, waste prior, early-tail, record warm-start, and a
≤L completion collector. Controls: n=5 finds 153 (100 rollouts); a record's
path replays 499/499 moves in-grammar. The headline: **cold-start NRPA
plateaus at 883** (no learnable gradient across the completion-blocked
midgame), but **warm-starting the policy from a known record carries rollouts
to depth 500 and the full pipeline re-derives that 872 end-to-end, validated,
byte-identical** — the policy machinery passes at oracle grade. The M3 gate
(a ≤872 byte-distinct from all 296 known) is still open, and the
same-session discriminator sharpened it: 288 warm-started rollouts collect
**zero** walks ≤873 other than the seed record itself — the shell around a
record is thin, and an independent ≤872 must be a coordinated multi-move
object, out of reach of local policy exploration. Hunt design lesson
(measured twice): a cap at exactly the target kills every rollout and the
gradient with it — hunt at cap 874, collect at ≤872. Next: structural
recombination (record-pair splicing, tour-merge, cross-class surgery), a
cheap bandit pass over the 296 warm-start records, and a warm-depth
curriculum. Full story: `docs/JOURNAL.md` s25.

**Prior (sessions 22–24, 2026-07-29): the Track B build.** The opening-first
sojourn-level machinery is up: the general waste identity is machine-verified on 806
walks (`analysis/trackb/verify_identity.py`), the L0 allocation ledger is built with
two closure lemmas (M1 passed at 66.5%; new pass-over lemma `ip ≤ 4(S−120)`), the
door atlas is orbit-verified (150 canonical edges), the canonical opening DFS
(`src/sojourn.rs`) exhausts the records' class to depth 10 in book mode (M2 passed),
and the completion machinery is wired end to end: frontier seed dumps
(`--dump-frontier`), multi-seed beam injection (`beam --seed-file`), scorer
composition (`--bound` + `--model`), and an admissible length cap (`--max-len`,
lossless, proven sound). Controls: **C2 passed** (the n=5 pipeline finds a validated
153); **C1 oracle passed** (the beam re-derives a known 872 byte-identically from its
own prefix at depth ≥ 450) but the **pipeline control is not yet passed** — best 874
via composed scoring (879 → 874, the first productive learned signal on completion),
with the remaining 2 chars *proven* to be a midgame ranking failure at levels ~60–450
(the record's own line has zero admissible-cap slack until the end, so no bound, cap,
or width can fix selection there). Next: NRPA policy rollouts, then the frontier
bandit → M3. Full story: `docs/JOURNAL.md` s22–s24.

**Prior (session 19, 2026-07-28):** Track C v2 (learned DLX column choice) built and
fully gated in one day — the mechanism is proven (1.50× median node reduction on
held-out refutation chains; learned *row* order provably cannot shrink these trees),
deployment is blocked on a 2.4× feature-scoring overhead (wall-clock NO-GO as-is).
Side results: a new admissible residual bound (`--bound residual`) improves the
hand-bound stratified beam **902 → 894** at equal width with 10,400
tablebase-verified admissibility samples and an optimality theorem for the old arc
bound; field lower bounds moved to **S(6) ≥ 869 / S(7) ≥ 5888** (urdvr/Hunter, Lean).
Full story: `docs/JOURNAL.md` s19, `analysis/trackc/RESULTS-s19.md`.

**Phases 1–2 complete; phase 3 underway (items 1–4 done)** — Rust search core:
overlap graph, greedy baseline, beam search with selectable admissible bounds, a
learned scorer, and per-structural-class width reservation (`--stratify`), a
two-ended deque beam (`beam2`), validator, (model-guided) rollout generator,
trajectory logging, greedy-prefix beam seeding, record-autopsy tooling
(`trace`, `--cutoff-log`), and an exact endgame tablebase (`endgame`,
`beam --endgame`: provably optimal completions once ≤ 25 perms remain).
Phase-2 outcome: the learned-score beam beats the hand-bound beam decisively at n=6
(874 vs 890 at equal wall-clock), and a greedy-prefix + learned-endgame hybrid reaches
a validated **873** — matching greedy via a different string, rung 1 of the success
ladder. An autopsy of 100 community 872-length records shows why 872 needs more: every
record path was pruned by the unstratified scorers within the first ~16% of the walk
(the phase-3 stratified beam fixes survival, not winning — see footnote 3; records leave
rotation cycles early via weight-2 moves and weave them closed later — structure the
current features actively penalize), while the endgame is already solved. See
[docs/JOURNAL.md](docs/JOURNAL.md) sessions 5–6.

### Known targets vs. this repo's results

| n | proven/best known | greedy (this repo) | beam, hand bound | beam, learned score |
|---|---|---|---|---|
| 3 | 9 (proven) | 9 | 9 | — |
| 4 | 33 (proven) | 33 | **33** (width 512, 0.007 s) | — |
| 5 | 153 (proven) | 153 | **153** (width 2000, 0.19 s) | **153** (width 2000) |
| 6 | 872 (best known; lower bound 867) | 873 | 890 (width 2000, 4.5 s)¹ | **873 from scratch** (stratified beam, ~8 s; also via greedy-prefix 350 hybrid, ~2 s)³ |
| 7 | 5906 (best known; lower bound 5884) | 5913 | 6130 (arc, width 2000)⁴ | **5913 from scratch** (stratified beam + n=6 model transfer, ~5.5 min)⁴ |
| 8 | 46204 (Raudvere, Jul 2026)² | — | — | — |

¹ Honest data point: at n=6 the hand-bound beam is currently *worse* than greedy — the
admissible cycle bound stops discriminating between states at this size. This is
precisely the gap the phase-2 learned evaluator is meant to close. A provably tighter
admissible bound (the arc bound, `--bound arc`) does **not** help: 891 at width 2000,
888 at width 8000 — tighter bounding ≠ better frontier ranking.

² Verified by the Superpermutators group on 2026-07-26 — one shorter than Egan's
construction, and notably **tree-structured** (standard kernel + 833 two-cycle
extensions). Reported same-day, independently checked: n=9 at 408,965 and n=10 at
4,037,046 (W. Echols), each one below Egan's formula; write-up pending.

³ Validated strings. Current best from scratch: `beam -n 6 --width 2000 --model
ml/models/linear_n6_boot1.json --alpha 1 --stratify --strat-quota 4 --strat-bucket 1`
→ **873** in ~8 s (phase-3 stratified beam: width reserved per deficit-profile bucket
so record-like states aren't crowded out; JOURNAL s7). Without stratification the
learned beam plateaus at 874 (~20 scorers, widths 500–128 000, ~150 jittered
restarts — JOURNAL s3/s6), still beating the hand-bound beam decisively (890 at equal
wall-clock; 4× the time for even 883) — the phase-2 exit criterion. 873 also comes
from the hybrid `--seed-prefix 350` (~2 s, JOURNAL s6). Three distinct 873s are now
known (greedy's, the seeded, the stratified). 872 needs evaluation, not search
mechanics: record-like states survive the stratified beam end-to-end but never win
the window, and a two-ended (deque) move space lands on the same 874 plateau
(`beam2`, JOURNAL s7) — hence phase-3 items 3–4 (deficit features + expert-rank
training, endgame tablebase). Item 3's verdict (JOURNAL s8): the deficit features
(`w2_bridges` et al.) provably carry the record signal, but no linear/MLP scorer over
them converts it — statically rewarding the record shape is exploitable by the beam —
so the effort moves to the exact endgame tablebase (item 4) and cycle-level moves
(item 5). Item 4's verdict (JOURNAL s9): the tablebase proves the endgame door is
closed — the stratified config's *entire* width-2000 frontier at 20-remaining
completes to ≥ 873 (unstratified: ≥ 874), and every known 872 has a provably
optimal last-20 tail — so the missing character must be won before the last ~25
perms, squarely in item 5's territory.

⁴ n=7, JOURNAL s8: hand bounds collapse (cycle 6180, arc 6130 at width 2000 — far
worse than greedy's 5913); the n=6-trained linear model transfers with zero
retraining (5970), and stratification closes exactly to **5913** (validated; a
distinct string from greedy's with the identical move-weight histogram — the n=6
"winner is greedy-shaped" phenomenon, one size up). Run via `--allow-n-mismatch`.
Bar to beat: 5907 (three community words, urdvr 2026-07-27); record 5906.

Greedy with min-weight/lexicographic tie-breaking reproduces the classic
sum-of-factorials construction (9, 33, 153, 873, …). Beating 872 at n=6 or 5906 at n=7
is the long-term goal; phase 1 only has to *recover the known optima for n ≤ 5*.

**Current front (2026-07): the certificate campaign.** Beyond the beam story above,
the project moved to the gain-one certificate grammar: at n=6, **Egan−1 = 872 is
proven optimal in the grammar** (`docs/RESULT-gain1-optimality-n6.md`); at n=7, the
V₇=15 kernel-chain census (any covered chain ⇒ a record 5905) stands at **85/223
chains refuted, 138 open** after a two-engine pass (`analysis/cover7/
results_n7_merged.csv`), and **Track C** — a learned row-ordering evaluator inside
the DLX cover search — is built and gated (`docs/TRACKC-DESIGN.md`,
`analysis/trackc/RESULTS-s17.md`). **Current implementation: Track B** — the n=6
out-of-grammar, opening-first sojourn-level search (`docs/TRACKB-DESIGN.md`,
designed 2026-07-29; class ledger + canonical opening exhaustion + bandit/NRPA
rollouts + tablebase tails, gated by a re-find-a-known-872 positive control).
Build s22–s24 (2026-07-29): the waste identity is machine-verified in its
fully general form (`analysis/trackb/verify_identity.py`), the L0 allocation
ledger is built with two closure lemmas (66.5% closed — M1 passed; new
pass-over capacity lemma `ip ≤ 4(S−120)`), the w≥3 door atlas is
orbit-verified (150 canonical edges), the sojourn-level opening DFS
(`src/sojourn.rs`) exhausts the records' class to depth 10 in book mode
(M2 passed; sound exhaustion reaches depth ~6), and the T3/T2 completion
machinery is live (frontier seed dumps → multi-seed beam injection →
composed bound+model scoring → admissible `--max-len` cap). Gate status:
C2 passed (n=5 pipeline finds 153); C1 oracle passed (a known 872
re-derived byte-identically from its own depth-≥450 prefix); C1 pipeline
open at **874** (879 → 874 via composition) with the residual failure
isolated to midgame ranking at levels ~60–450. s25 built that midgame's
policy layer — NRPA over the sojourn grammar — and its warm-started form
re-derives a known 872 end-to-end through policy + grammar + capped tail;
M3 (an *independent* ≤872) is the open gate, next attacked via
neighborhood diversity, a bandit over the 296 warm-start records, and a
warm-depth curriculum.
Session-by-session state: `docs/JOURNAL.md`
(read newest entry first); agent conventions: `CLAUDE.md`.

## Quickstart

```bash
cargo test --release          # includes hard assertions: greedy == 9 / 33 / 153
cargo run --release -- info -n 5
cargo run --release -- greedy -n 5
cargo run --release -- beam -n 5 --width 2000
cargo run --release -- beam -n 6 --width 2000 --bound arc --log traj.jsonl
cargo run --release -- rollouts -n 5 --count 200 --epsilon 0.15 --seed 0 --out rollouts_n5.jsonl
cargo run --release -- validate -n 5 <string>
python3 ml/fit_linear.py data/roll_n5_*.jsonl   # linear cost-to-go baseline vs hand bounds
```

## Repo layout

```
src/            Rust search core (graph, bitset, bounds/features, greedy, beam, sojourn DFS, rollouts, validator, CLI)
ml/             Python model side (numpy): linear cost-to-go baseline
analysis/       campaign tooling + committed ledgers (trackb/ = waste identity, L0 ledger, door atlas)
data/           generated JSONL corpora (gitignored)
tests/          acceptance tests pinned to the proven optima
docs/THEORY.md  problem formulation, cycle structure, lower bound, value-net plan
docs/ROADMAP.md phased plan with checkboxes
docs/JOURNAL.md dated lab notebook — read this first when resuming work
docs/TRACKB-DESIGN.md  active design doc: opening-first Track B search (the next implementation)
CLAUDE.md       working conventions for AI-assisted sessions
```

## Stack rationale

- **Rust** for the search core: the hot loop is bitmask operations and small-array
  shuffling at millions of node expansions per second, and phase 3 wants fearless
  multi-core parallelism. `lto` + single codegen unit in release.
- **JSONL** as the boundary between search and learning: rollout data is plain
  feature/cost-to-go records, so the phase-2 model side (Python/PyTorch or similar)
  stays fully decoupled from the search engine.
- **No GPU assumptions.** The intended value net is small (an MLP over ~dozens of
  residual-graph features); CPU batch inference is the design point.

## Background / prior art

- OEIS [A180632](https://oeis.org/A180632) — minimal superpermutation lengths.
- Robin Houston, *Tackling the Minimal Superpermutation Problem* ([arXiv:1408.5108](https://arxiv.org/abs/1408.5108)) — found 872 for n=6 via ATSP/LKH, disproving the sum-of-factorials conjecture.
- Anonymous 4chan poster, Houston, Pantone, Vatter — the `n! + (n−1)! + (n−2)! + n − 3` lower bound.
- Greg Egan, [Superpermutations](https://www.gregegan.net/SCIENCE/Superpermutations/Superpermutations.html) — n=7 record (5906) and the `n! + (n−1)! + (n−2)! + (n−3)! + n − 3` construction.
- [superpermutators/superperm](https://github.com/superpermutators/superperm) — the community corpus of known superpermutations and distributed search (Chaffin method) that proved 153 optimal for n=5.
- July 2026 developments (Superpermutators Google Group): [Raudvere's n=8, 46204](https://github.com/urdvr/superpermutation-examples/blob/main/superpermutation-8-46204.raw.txt) — tree-like, kernel + 2-cycle extensions; [Echols' n=9/n=10 candidates](https://github.com/WilliamEchols/superpermutations), each −1 vs. Egan's construction.

## License

MIT
