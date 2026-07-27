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

**Phase 1 complete** — Rust search core: overlap graph, greedy baseline, beam search with
an admissible cycle-counting lower bound, validator, and an epsilon-greedy rollout
generator that emits JSONL training data for the phase-2 value net.

### Known targets vs. this repo's results

| n | proven/best known | greedy (this repo) | beam (this repo) |
|---|---|---|---|
| 3 | 9 (proven) | 9 | 9 |
| 4 | 33 (proven) | 33 | **33** (width 512, 0.007 s) |
| 5 | 153 (proven) | 153 | **153** (width 2000, 0.19 s) |
| 6 | 872 (best known; lower bound 867) | 873 | 890 (width 2000, 4.5 s)¹ |
| 7 | 5906 (best known; lower bound 5884) | — | — |
| 8 | 46204 (Raudvere, Jul 2026)² | — | — |

¹ Honest data point: at n=6 the hand-bound beam is currently *worse* than greedy — the
admissible cycle bound stops discriminating between states at this size. This is
precisely the gap the phase-2 learned evaluator is meant to close.

² Verified by the Superpermutators group on 2026-07-26 — one shorter than Egan's
construction, and notably **tree-structured** (standard kernel + 833 two-cycle
extensions). Reported same-day, independently checked: n=9 at 408,965 and n=10 at
4,037,046 (W. Echols), each one below Egan's formula; write-up pending.

Greedy with min-weight/lexicographic tie-breaking reproduces the classic
sum-of-factorials construction (9, 33, 153, 873, …). Beating 872 at n=6 or 5906 at n=7
is the long-term goal; phase 1 only has to *recover the known optima for n ≤ 5*.

## Quickstart

```bash
cargo test --release          # includes hard assertions: greedy == 9 / 33 / 153
cargo run --release -- info -n 5
cargo run --release -- greedy -n 5
cargo run --release -- beam -n 5 --width 2000
cargo run --release -- rollouts -n 5 --count 200 --epsilon 0.15 --seed 0 --out rollouts_n5.jsonl
cargo run --release -- validate -n 5 <string>
```

## Repo layout

```
src/            Rust search core (graph, bitset, bounds/features, greedy, beam, rollouts, validator, CLI)
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
