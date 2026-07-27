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
//! * [`walk`] — incremental walk state shared by all searchers;
//! * [`greedy`] — the deterministic greedy baseline (achieves the known
//!   optima 9 / 33 / 153 for `n = 3, 4, 5`);
//! * [`beam`] — width-limited best-first (beam) search scored by
//!   `length + lower bound` or a learned value function;
//! * [`model`] — learned cost-to-go models (linear / MLP) loaded from
//!   JSON files produced by the Python training side;
//! * [`rollout`] — epsilon-greedy rollout generator emitting JSONL
//!   training records for a future learned value function;
//! * [`validate`] — a sliding-window superpermutation validator.

pub mod beam;
pub mod bitset;
pub mod bound;
pub mod graph;
pub mod greedy;
pub mod model;
pub mod rollout;
pub mod validate;
pub mod walk;
