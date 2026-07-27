//! Admissible lower bound on remaining characters, and the feature
//! record logged by the rollout generator.
//!
//! # The bound
//!
//! Let `r` be the number of unvisited permutations and `k` the number of
//! rotation cycles (1-cycles) that still contain at least one unvisited
//! permutation. Every unvisited permutation must be reached by some edge,
//! and every edge has weight ≥ 1, so at least `r` characters remain.
//!
//! Weight-1 edges never leave a rotation cycle (the weight-1 successor is
//! the left rotation, which by definition lies in the same cycle). Hence
//! each of the `k` cycles containing unvisited work — except possibly the
//! cycle the walk currently occupies — must at some point be *entered*
//! via an edge of weight ≥ 2, paying at least one character beyond the
//! one-per-permutation minimum. This gives the admissible bound
//!
//! ```text
//! lb = r + k − [current cycle still has unvisited permutations]
//! ```
//!
//! which never overestimates the true remaining cost.

use serde::{Deserialize, Serialize};

/// Admissible lower bound on the number of characters still to append.
///
/// * `r` — unvisited permutation count;
/// * `k` — cycles with ≥ 1 unvisited permutation;
/// * `current_cycle_has_unvisited` — whether the cycle containing the
///   walk's current permutation still has unvisited members.
///
/// Returns `r + k − [current_cycle_has_unvisited]` (0 when `r == 0`).
#[inline]
pub fn lower_bound(r: usize, k: usize, current_cycle_has_unvisited: bool) -> usize {
    debug_assert!(!(current_cycle_has_unvisited && k == 0));
    r + k - usize::from(current_cycle_has_unvisited)
}

/// One training record for the future learned value function.
///
/// Emitted (one JSON line per visited step) by the rollout generator;
/// `cost_to_go` is filled in retroactively once the rollout's final
/// length is known: `cost_to_go = final_len − len_so_far`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Features {
    /// Number of symbols.
    pub n: u32,
    /// Steps taken so far (= permutations visited − 1; the start state
    /// is step 0).
    pub step: u32,
    /// Unvisited permutation count `r`.
    pub r: u32,
    /// Cycles with at least one unvisited permutation (`k`).
    pub cycles_remaining: u32,
    /// Cycles with *all* `n` members unvisited.
    pub intact_cycles: u32,
    /// Unvisited members of the current permutation's cycle.
    pub current_cycle_remaining: u32,
    /// Characters emitted so far.
    pub len_so_far: u32,
    /// Characters the rollout actually needed from here to completion.
    pub cost_to_go: u32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lower_bound_basic() {
        // Terminal state: nothing remains.
        assert_eq!(lower_bound(0, 0, false), 0);
        // One perm left in the current cycle: exactly one char (a
        // rotation step) may suffice.
        assert_eq!(lower_bound(1, 1, true), 1);
        // One perm left in a *different* cycle: ≥ 2 chars.
        assert_eq!(lower_bound(1, 1, false), 2);
    }
}
