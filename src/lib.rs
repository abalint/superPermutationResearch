//! `superperm` — infrastructure for superpermutation search research.
//!
//! A *superpermutation* on `n` symbols is a string over the alphabet
//! `{1, …, n}` that contains every permutation of the `n` symbols as a
//! contiguous substring. Minimal lengths are known for small `n`:
//! `n = 3 → 9`, `n = 4 → 33`, `n = 5 → 153`; for `n = 6` the best known
//! is 872 and minimality is open beyond `n = 5`.
//!
//! Searching for short superpermutations is equivalent to finding a short
//! Hamiltonian-style walk in a weighted directed graph whose vertices are
//! the `n!` permutations and whose edge weight from `P` to `Q` is the
//! number of characters that must be appended to a string ending in `P`
//! so that it ends in `Q` (i.e. `n` minus the length of the maximal
//! overlap of a suffix of `P` with a prefix of `Q`).
//!
//! This crate (phase 1 of the research effort) provides:
//!
//! * [`graph`] — the permutation overlap graph with Lehmer-code
//!   rank/unrank, sorted successor lists, and rotation-cycle labeling;
//! * [`bitset`] — a small fixed-size bitset used for visited sets;
//! * [`bound`] — an admissible lower bound on remaining characters plus a
//!   serializable [`bound::Features`] record for ML training data;
//! * [`lb_residual`] — the residual-graph admissible lower bound
//!   (`docs/RESIDUAL-BOUND-DESIGN.md`): minimum-in-edge, intact-class
//!   and dead-door terms, dominating the cycle and arc bounds;
//! * [`state`] — the shared incremental search state: one definition of
//!   every counter update rule, consumed by [`walk`], [`beam`],
//!   [`beam2`], [`sojourn`] and [`unionsearch`] (s64 P3);
//! * [`walk`] — incremental walk state shared by all searchers;
//! * [`greedy`] — the deterministic greedy baseline (achieves the known
//!   optima 9 / 33 / 153 for `n = 3, 4, 5`);
//! * [`beam`] — width-limited best-first (beam) search scored by
//!   `length + lower bound` or a learned value function;
//! * [`beam2`] — two-ended (deque) beam search: moves append a
//!   successor of the string's back or prepend a predecessor of its
//!   front, scored by the admissible two-ended arc bound (phase 3's
//!   decision-order probe);
//! * [`endgame`] — exact endgame tablebase: Held–Karp DP giving the
//!   provably optimal completion once ≤ ~25 permutations remain
//!   (phase-3 item 4);
//! * [`corpus`] — record corpus loading (traced, validated, deduped)
//!   shared by the s26 recombination probes (`docs/RECOMB-DESIGN.md`);
//! * [`cert`] — clean-room verifier for the n = 6 gain-one kernel-chain
//!   certificate: rebuilds marked loops, hops, chains, and covers from
//!   the mathematical definitions alone and re-checks claims C1–C5
//!   (`cert-verify` subcommand);
//! * [`model`] — learned cost-to-go models (linear / MLP) loaded from
//!   JSON files produced by the Python training side;
//! * [`rollout`] — epsilon-greedy rollout generator emitting JSONL
//!   training records for a future learned value function;
//! * [`recomb`] — record-pair splice closure over the braid state-DAG
//!   (s26 Probe R1, `docs/RECOMB-DESIGN.md` §4);
//! * [`unionsearch`] — exhaustive bound-capped DFS inside the corpus
//!   edge union (s26 Probe R3 / §7 tour-merge, RECOMB-DESIGN §5);
//! * [`trace`] — first-visit trajectory extraction from existing
//!   superpermutation strings (e.g. community records) plus beam-exact
//!   state scoring for prune-depth analysis;
//! * [`validate`] — a sliding-window superpermutation validator.

pub mod beam;
pub mod beam2;
pub mod bitset;
pub mod bound;
pub mod cert;
pub mod corpus;
pub mod endgame;
pub mod graph;
pub mod greedy;
pub mod lb_residual;
pub mod model;
pub mod nrpa;
pub mod recomb;
pub mod rollout;
pub mod sojourn;
pub mod state;
pub mod tailatsp;
pub mod trace;
pub mod unionsearch;
pub mod validate;
pub mod walk;
