# superPermutationResearch

Search-based research on **minimal superpermutations**: the shortest string that contains
every permutation of `{1..n}` as a contiguous substring.

The thesis of this project: minimal-superpermutation hunting is single-player game-tree
search — a walk through the permutation overlap graph — and the frontier question is not
*whether* to do heuristic search with pruning (that's how every modern record was found),
but whether a **learned evaluation function over residual-graph structure** can prune
better than the hand-derived waste/cycle bounds. See [docs/THEORY.md](docs/THEORY.md) for
the full framing and [docs/ROADMAP.md](docs/ROADMAP.md) for the phased plan.

## Status

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
src/            Rust search core (graph, bitset, bounds/features, greedy, beam, rollouts, validator, CLI)
ml/             Python model side (numpy): linear cost-to-go baseline
data/           generated JSONL corpora (gitignored)
tests/          acceptance tests pinned to the proven optima
docs/THEORY.md  problem formulation, cycle structure, lower bound, value-net plan
docs/ROADMAP.md phased plan with checkboxes
docs/JOURNAL.md dated lab notebook — read this first when resuming work
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
