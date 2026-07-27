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
//!
//! # The arc bound (strictly at least as strong)
//!
//! Refine cycles into *arcs*: the connected components of the unvisited
//! permutations under weight-1 (rotation) edges. A fully-unvisited cycle
//! is one circular component; a partially-visited cycle splits into
//! maximal runs of consecutive unvisited rotations. Let `a` be the number
//! of arcs (`a ≥ k`, since every cycle with unvisited work holds ≥ 1 arc).
//!
//! Whenever the walk first enters an arc, the entered permutation's
//! weight-1 predecessor is either (i) inside the arc and unvisited — but
//! the walk only ever stands on visited permutations, so the entry edge
//! cannot be that weight-1 edge — or (ii) already visited, and the walk
//! can never stand on it again (each step lands on a *new* permutation),
//! **except** when it is the walk's current permutation itself. The only
//! arc that can be entered by a weight-1 edge is therefore the one headed
//! by `succ1(cur)`, and only if that permutation is unvisited. Every
//! other arc's first entry pays weight ≥ 2 — one character beyond the
//! one-per-permutation minimum — on `a` distinct entry edges:
//!
//! ```text
//! lb_arc = r + a − [succ1(cur) is unvisited]
//! ```
//!
//! Since `a ≥ k` and `succ1(cur)` unvisited implies the current cycle has
//! unvisited members, `lb_arc ≥ lb` pointwise, and both are admissible.
//!
//! # The two-ended (deque) arc bound
//!
//! In the two-ended searcher a state is `(front, back, visited, len)`:
//! the string built so far realizes a walk `front → … → back` over the
//! visited permutations, and a move either APPENDS an unvisited
//! successor of `back` (back moves onto it) or PREPENDS an unvisited
//! predecessor of `front` (front moves onto it), paying the edge weight
//! in characters either way. Three facts drive the bound:
//!
//! 1. every move visits exactly one new permutation at cost ≥ 1, so at
//!    least `r` characters remain;
//! 2. `back` changes only by appends, always onto a *newly* visited
//!    permutation — so the sequence of `back` values over time is
//!    duplicate-free: once `back` leaves a permutation it can never be
//!    `back` again. Symmetrically for `front` and prepends;
//! 3. the only weight-1 append visits `succ1(back)`; the only weight-1
//!    prepend visits `pred1(front)`.
//!
//! Fix the current state's arcs (weight-1 components of the unvisited
//! set) and consider any future completion. Inside one open arc
//! `a₁ →₁ … →₁ a_m`, a weight-1 append visiting `a_j` requires
//! `back = pred1(a_j)` at that moment: for `j > 1` that means `a_{j−1}`
//! was itself just appended (weight-1 appends chain *forward* along the
//! arc), and for `j = 1` it requires `back = pred1(a₁)` — a permutation
//! that is visited *now*, so by fact 2 this is only possible if it is
//! the current `back`, i.e. the arc is headed by `succ1(back)`.
//! Symmetrically, a weight-1 prepend visiting `a_j` requires
//! `front = succ1(a_j)`: weight-1 prepends chain *backward*, and
//! starting the chain at `j = m` requires the arc to be tailed by
//! `pred1(front)` with `front` unchanged since now. A circular arc (a
//! fully unvisited cycle) has `pred1` and `succ1` unvisited for every
//! member, so no weight-1 move can make its *first* visit at all.
//!
//! Hence every arc — except possibly the one headed by `succ1(back)`
//! and the one tailed by `pred1(front)` — receives at least one visit
//! by a move of weight ≥ 2, i.e. ≥ 1 character above the
//! one-per-permutation minimum, and these extra characters lie on
//! distinct moves (a move visits one permutation, which lies in one
//! arc). Note the exceptions are real arcs when their indicators fire:
//! `succ1(back)` unvisited has `pred1(succ1(back)) = back` visited, so
//! it heads an arc; `pred1(front)` unvisited has `front` visited, so it
//! tails one. This yields the admissible bound
//!
//! ```text
//! lb_arc2 = max(r, r + a − [succ1(back) unvisited] − [pred1(front) unvisited])
//! ```
//!
//! The `max` with the trivial bound `r` covers the one case where the
//! two subtractions overcount: both indicators firing on the *same* arc
//! (headed by `succ1(back)` and tailed by `pred1(front)`), which can be
//! consumed entirely by weight-1 moves from both ends but is still only
//! one arc. With the prepend side permanently dead (`pred1(front)`
//! visited forever, as in an append-only walk) this reduces exactly to
//! `lb_arc`; at a start state with `front = back` both indicators fire
//! and the bound sits one below the one-ended value — the price of not
//! yet knowing which end the walk will grow from.

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

/// Arc-refined admissible lower bound (see module docs).
///
/// * `r` — unvisited permutation count;
/// * `arcs` — weight-1 connected components among unvisited permutations;
/// * `succ1_unvisited` — whether the current permutation's weight-1
///   successor (left rotation) is unvisited.
///
/// Returns `r + arcs − [succ1_unvisited]` (0 when `r == 0`). Dominates
/// [`lower_bound`] pointwise.
#[inline]
pub fn lower_bound_arc(r: usize, arcs: usize, succ1_unvisited: bool) -> usize {
    debug_assert!(!(succ1_unvisited && arcs == 0));
    if r == 0 {
        0
    } else {
        r + arcs - usize::from(succ1_unvisited)
    }
}

/// Two-ended (deque) arc bound (see module docs for the proof sketch).
///
/// * `r` — unvisited permutation count;
/// * `arcs` — weight-1 connected components among unvisited permutations;
/// * `succ1_back_unvisited` — whether `succ1(back)` (the appending end's
///   left rotation) is unvisited;
/// * `pred1_front_unvisited` — whether `pred1(front)` (the prepending
///   end's right rotation) is unvisited.
///
/// Returns `max(r, r + arcs − [succ1_back_unvisited] −
/// [pred1_front_unvisited])` (0 when `r == 0`). The floor at `r` covers
/// the overcount when both free ends land on the same arc. Admissible
/// for the deque move set (append a successor of `back` / prepend a
/// predecessor of `front`).
#[inline]
pub fn lower_bound_arc2(
    r: usize,
    arcs: usize,
    succ1_back_unvisited: bool,
    pred1_front_unvisited: bool,
) -> usize {
    debug_assert!(!((succ1_back_unvisited || pred1_front_unvisited) && arcs == 0));
    if r == 0 {
        0
    } else {
        let free = usize::from(succ1_back_unvisited) + usize::from(pred1_front_unvisited);
        // arcs ≥ 1 whenever r ≥ 1, so r + arcs − free ≥ r − 1 ≥ 0.
        (r + arcs - free).max(r)
    }
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
    /// Weight-1 connected components (arcs) among unvisited permutations.
    /// Added after phase 1; defaults to 0 when reading old JSONL.
    #[serde(default)]
    pub arcs: u32,
    /// 1 if the current permutation's weight-1 successor is unvisited.
    /// Added after phase 1; defaults to 0 when reading old JSONL.
    #[serde(default)]
    pub succ1_unvisited: u32,
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

    #[test]
    fn lower_bound_arc_basic() {
        assert_eq!(lower_bound_arc(0, 0, false), 0);
        // One arc, headed by succ1(cur): a single rotation may finish it.
        assert_eq!(lower_bound_arc(1, 1, true), 1);
        // One arc elsewhere: ≥ 2 chars.
        assert_eq!(lower_bound_arc(1, 1, false), 2);
        // Dominates the cycle bound whenever arcs > k.
        assert!(lower_bound_arc(10, 5, false) > lower_bound(10, 3, false));
    }

    #[test]
    fn lower_bound_arc2_basic() {
        assert_eq!(lower_bound_arc2(0, 0, false, false), 0);
        // One arc, reachable weight-1 from the back: one char may do it.
        assert_eq!(lower_bound_arc2(1, 1, true, false), 1);
        // ... or weight-1 into the front.
        assert_eq!(lower_bound_arc2(1, 1, false, true), 1);
        // One arc touching both free ends: still ≥ r (the floor).
        assert_eq!(lower_bound_arc2(3, 1, true, true), 3);
        // No free end: every arc pays an entry.
        assert_eq!(lower_bound_arc2(10, 4, false, false), 14);
        // With the prepend side dead, reduces exactly to lb_arc.
        for r in 1..20 {
            for arcs in 1..=r {
                for s in [false, true] {
                    assert_eq!(
                        lower_bound_arc2(r, arcs, s, false),
                        lower_bound_arc(r, arcs, s)
                    );
                }
            }
        }
    }
}
