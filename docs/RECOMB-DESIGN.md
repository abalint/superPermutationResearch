# Structural recombination (s26) — record-pair splicing + corpus-edge union search

**Status (2026-07-29, s26): DESIGN COMPLETE, feasibility-measured; implementation
split across two modules (`src/recomb.rs`, `src/unionsearch.rs`) on the shared
corpus loader `src/corpus.rs`. This is the M3 front after the s25 discriminator
verdict.**

## 1. Why this, why now

The s25 discriminator (JOURNAL 2026-07-29) closed the "tune exploration harder"
alternative: 288 NRPA rollouts warm-started from a record collect ZERO ≤873
completions other than the seed itself. Single- or few-move deviations from a
record cost ≥ 2 chars. An independent ≤872 is a **coordinated multi-move
object**, so the search moves from policy jitter to structural moves over the
record corpus itself:

- (a) record-pair splicing (crossover at shared search states),
- (b) the TRACKB-DESIGN §7 tour-merge (LKH import: search the union of elite
  tours' edges),
- (c) cross-class surgery (cycle-level edits that change the L0 allocation).

This doc designs (a) and (b) to verdict, and delivers a budgeted first step
toward (c) (`--free` edges, §5.3). Full surgery is designed AFTER the union
verdict is in — its result determines where new edges are worth pricing.

## 2. Feasibility measurements (drive every decision below)

Script: `analysis/trackb/recomb_feasibility.py` (pure Python, reads
`data/records872/` + `data/gain1_872s/`, ~2 min). Corpus = 296 byte-distinct
872s. All numbers machine-checked 2026-07-29:

1. **Shared states are common.** 6,434 (visited-set, current-perm) states are
   occupied by ≥ 2 byte-distinct records — at every depth band, including the
   blocked zone (per-100-perm histogram
   `{0:1911, 100:855, 200:164, 300:100, 400:44, 500:627, 600:2531, 700:202}`).
   Every one is a zero-cost crossover: prefix(A)+suffix(B) is legal.
2. **All shared states are equal-length.** Across all 6,434 collisions the
   prefix-length spread is 0 — no free improvement by splicing (expected: a
   length difference at a shared state would contradict both being 872s only
   if the *shorter* prefix's record completed worse; measured anyway: none).
3. **The braid barely reconverges.** The state-DAG over all record paths
   (172,521 states, 172,816 edges, **one single terminal state** — all 296
   records end at the same final perm with the same last move) has exactly
   **298** root→terminal paths. Splice-closure = corpus + **2 new hybrid
   872s**. Splicing alone is nearly barren.
4. **Near-miss repair is dead.** At matched (current-perm, depth), cross-record
   visited-set symmetric difference is bimodal: 0 or ≥ 20 perms (10,826 pairs
   at 0; 63 pairs in 1..19; 50,045 at ≥ 20). There is no population of
   "2–3 perms off" states to repair with a capped beam. **KILLED from the
   design** (was next-steps item (a)-repair).
5. **The union graph is tiny.** Union of all first-visit edges used by any
   record: **1,279 edges over 720 nodes; out-degree ≤ 2** (histogram
   `{0:1, 1:159, 2:560}`; weights 700×w1, 576×w2, 3×w3). An exhaustive
   bound-capped DFS restricted to corpus edges is tractable — this is the §7
   tour-merge, and it is the main probe. The out-degree-0 node is the common
   terminal of measurement 3.

Consequences:

- The splice probe (R1) shrinks to a cheap deterministic enumeration: build the
  braid DAG, emit the 2 hybrids, keep the machinery (it re-runs on every corpus
  growth — hybrids and union finds feed back in).
- The union probe (R3) is where new 872s can exist: the union graph contains
  every splice-closure walk **plus all novel interleavings of record edges with
  never-before-seen intermediate states**. Naive path count is astronomically
  large (Σ log10(outdeg) ≈ 169), so the search stands on the admissible bound +
  cap, transposition dedup, and the braid evidence that record edges are
  extremely constrained.
- The record-bandit warm-start pass (s25 next-steps) is **deprioritized**: the
  union DFS explores the corpus neighborhood deterministically and exhaustively
  rather than stochastically; run the bandit only if R3 is somehow intractable.

## 3. Shared infrastructure — `src/corpus.rs` (built with this doc)

```rust
pub struct CorpusRecord { pub name: String, pub string: String, pub trace: Trace }
pub fn load_corpus(g: &Graph, dirs: &[&Path]) -> Result<Vec<CorpusRecord>, String>
```

Deterministic (sorted per-dir file order), skips non-record files (any char
outside `'1'..=('0'+n)`, e.g. `_filelist.txt`), rejects untight or incomplete
strings (`replay_len != input_len` or `path.len() != n!` is an **error**, not a
skip — a corrupt record file must fail loudly), dedups byte-identical strings
(first name wins). Both probes take `--dirs a,b,c` and call this.

## 4. Probe R1 — splice closure (`src/recomb.rs`, CLI `recomb`) — Agent A

Build the braid DAG exactly as measured: node = (visited-bitset, cur), edges =
consecutive record steps, layered by popcount (strictly increasing ⇒ DAG, no
cycle handling). Then:

1. Count root→terminal paths (u128; overflow = hard error with message — the
   count is a pin, not a big-number exercise).
2. Enumerate all paths (only feasible BECAUSE the count is small; refuse to
   enumerate above `--max-walks`, default 100,000, with a clear message).
3. Rebuild each path's string via `Walk` replay; validate
   (`validate::validate`, complete + length == weight-sum + n); drop
   byte-identical matches against the input corpus; emit survivors to
   `--emit-dir` as `<len>.h-<sha1-7>.txt` plus a `provenance.tsv`
   (hybrid name, segment list: source record + step range per segment).
4. Stats to stdout: states, edges, terminals, junction count (states with ≥2
   distinct successor edges... report both in- and out-junctions), closure
   count, new-hybrid count, per-depth-band junction histogram.

**Pins (integration test, `data/records872` + `data/gain1_872s`):** 296 records
load; DAG = 172,521 states / 172,816 edges / 1 terminal; closure count = 298;
exactly 2 new hybrids, both validate at 872. Unit tests on synthetic n=5
mini-corpora (e.g. corpus = {greedy-153} → 1 state-path, 0 hybrids).

Re-run protocol: whenever the corpus grows (union finds, future records), re-run
with all dirs; the closure can only grow.

## 5. Probe R3 — union-edge exhaustive search (`src/unionsearch.rs`, CLI `union-dfs`) — Agent B

### 5.1 Core

Adjacency: for each node, the union of corpus first-visit edges out of it,
sorted by (weight, rank) for determinism. DFS over `Walk` from rank 0 (all
records start at the identity):

- Prune when `len + lb > cap` (`--cap`, required; `--bound cycle|residual`,
  default cycle — measure both; residual is stronger and slower).
- On `walk.done()`: validate, dedup by string (HashSet of hashes + full-string
  confirm), write each distinct find ≤ cap to `--out-dir` (same naming as R1)
  and log length + count.
- `--max-nodes N` guard (default 200M): on hit, STOP and print
  `verdict: TRUNCATED` (vs `verdict: COMPLETE`). Only COMPLETE runs support
  claims. Stats: nodes expanded, bound prunes, dead-ends (no union successor
  unvisited... note a node's union successors may all be visited — that's a
  dead end unless free edges remain), completions, max depth reached, wall time.

### 5.2 Transposition mode (`--tt`)

Exact-key HashMap (visited-bitset bytes, cur) → best len seen; prune revisits
with `len >= stored`. **Sound for decision/optimality claims** ("no walk ≤ cap
exists", "shortest in-union walk is L"): any completion from a state costs the
same regardless of prefix, so the surviving minimal-length visit preserves
reachability of every length ≤ any pruned visit's completions. **NOT sound for
enumeration counts** (equal-length distinct walks through a shared state are
collapsed). The tool must print which claim its configuration supports:
enumeration mode (no `--tt`) → "all distinct walks ≤ cap"; `--tt` → "existence/
optimality only". `--tt-max E` caps table entries (default 100M); when full,
stop inserting but keep probing — still sound, just weaker pruning; report
saturation in stats.

### 5.3 Free edges (`--free k`, `--free-w w`, default w=2) — surgery-lite

At each state, besides union edges, allow off-union graph successors of weight
≤ w, spending one of k credits per walk. k=0 (default) = pure tour-merge.
k=1,2 price the first genuinely new doors conditional on record structure
everywhere else — the budgeted bridge toward cross-class surgery, and the only
mode that can produce a fully independent (out-of-union) find. Branching grows
sharply (each node has ~n−1 w≤2 off-union successors); keep k ≤ 2 and rely on
the cap.

### 5.4 Controls and pins

- **C-U0 (n=5, unit test):** corpus = {greedy 153 string}; union graph = its
  own 119 edges; enumeration cap 153 → COMPLETE with exactly 1 find, the
  string itself, validated. Cap 152 → COMPLETE, 0 finds.
- **C-U1 (n=6 smoke, integration test, must stay < 60 s):** both dirs, cap
  872, `--max-nodes` small (pick so the test is fast); must re-find ≥ 1
  corpus record before truncation. (If even the smoke run completes, pin the
  count.)
- **C-U2 (production, run after merge, bounded):** enumeration, cap 872,
  max-nodes 200M. COMPLETE ⇒ the exact census of 872s inside the record edge
  set — every find beyond the 298 splice-closure walks is a **structurally
  new interleaving**, i.e. a coordinated multi-move object of exactly the
  kind the discriminator says M3 requires.
- **C-U3 (production):** `--tt`, cap 871, both bounds. COMPLETE + 0 finds ⇒
  **lemma: no ≤871 superpermutation exists using only record first-visit
  edges** — the first structural exclusion for the waste-146 hunt, and it
  sharpens where an 871's new edges must live. A find ⇒ world record, validate
  before believing anything (CLAUDE.md invariant).
- **C-U4 (production, only after C-U2/C-U3 verdicts):** `--free 1` then
  `--free 2` at cap 871 with `--tt`, max-nodes ladder.

### 5.5 M3 semantics after this build

- Any C-U2 find not byte-identical to corpus ∪ splice-closure = **M3
  candidate** (in-union independent 872). Confirm: `trace` it, check weight
  multiset (expected: forced to 575/141/3 — only 3 w3 edges exist in the
  union) and s20 coordinate cell; re-run R1 with it added (splice-closure
  growth measures how connected it is to the old corpus).
- A C-U4 find with a genuinely new edge = full M3 PASS and more (out-of-union
  structure).
- C-U2 COMPLETE with 0 non-closure finds + C-U3 COMPLETE with 0 finds =
  **M3-union verdict NEGATIVE**: the record edge set is exhausted; an
  independent ≤872 requires new doors ⇒ all remaining weight goes to
  cross-class surgery design (next design doc) with C-U3's exclusion as its
  first constraint.

## 6. Build & compute protocol

- Implementation: two Opus agents in parallel git worktrees — Agent A: §4
  (`recomb.rs` + CLI + tests); Agent B: §5 (`unionsearch.rs` + CLI + tests).
  Both build on `corpus.rs` (committed with this doc). Repo invariants apply:
  `cargo test --release` green, clippy `-D warnings` clean, fmt clean, every
  emitted string validated, bound stays admissible (union restriction only
  REMOVES successors; lb over the full graph remains admissible — removing
  edges can only increase true remaining cost).
- Agent-run controls stay < 10 min each. Production runs (C-U2..C-U4) are
  launched from the merged main tree with `--max-nodes` sized to < 30 min
  wall; anything projected longer follows OPERATIONS.md (pre-announce,
  heartbeat, abort command) per the standing launch protocol.

## 7. Anti-goals

- No near-miss splice repair (measurement 4: the population doesn't exist).
- No stochastic exploration in this probe (NRPA/bandit) until the
  deterministic union census is in — exhaustive beats sampled on a 1,279-edge
  graph.
- No unbounded runs; no claims from TRUNCATED runs; no enumeration claims from
  `--tt` runs.
- No new scorer machinery — this probe needs only the existing admissible
  bounds.
