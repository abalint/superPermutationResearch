//! Incremental walk state shared by the greedy searcher and the rollout
//! generator.
//!
//! A [`Walk`] tracks the string built so far plus the shared
//! [`SearchState`] counters (visited set, per-cycle unvisited counts,
//! arcs, deficit distribution, residual terms) needed to evaluate the
//! admissible lower bounds of [`crate::bound`] and [`crate::lb_residual`]
//! in O(1) per move. Every counter update rule lives in
//! [`crate::state`] — this type only adds the emitted characters.

use crate::bound::{lower_bound, lower_bound_arc, Features};
use crate::graph::Graph;
use crate::lb_residual::PredTable;
use crate::state::SearchState;

/// A partial superpermutation under construction.
///
/// Starts at rank 0 (the identity permutation) with its `n` characters
/// already emitted. Each [`Walk::advance`] visits one new permutation by
/// appending `weight` characters.
pub struct Walk<'g> {
    g: &'g Graph,
    /// The shared incremental counters (see [`crate::state`]).
    pub st: SearchState,
    /// The emitted symbols (values `1..=n`).
    pub chars: Vec<u8>,
    /// Tabulated weight-≤3 in-neighbours (drives `door`/`long`).
    tab: PredTable,
}

impl<'g> Walk<'g> {
    /// Fresh walk positioned at the identity permutation (rank 0).
    pub fn new(g: &'g Graph) -> Walk<'g> {
        let tab = PredTable::new(g);
        Walk {
            g,
            st: SearchState::root(g, Some(&tab)),
            chars: g.perms[0].clone(),
            tab,
        }
    }

    /// The graph this walk lives in.
    pub fn graph(&self) -> &'g Graph {
        self.g
    }

    /// Rank of the permutation the string currently ends with.
    #[inline]
    pub fn cur(&self) -> u32 {
        self.st.cyc.cur
    }

    /// Number of advances taken (permutations visited − 1).
    #[inline]
    pub fn steps(&self) -> u32 {
        self.st.steps
    }

    /// Whether every permutation has been visited.
    pub fn done(&self) -> bool {
        self.st.cyc.r == 0
    }

    /// Characters emitted so far.
    pub fn len_chars(&self) -> usize {
        self.chars.len()
    }

    /// First unvisited successor in the sorted list (minimum weight,
    /// then lexicographically smallest appended suffix), if any.
    pub fn first_unvisited_succ(&self) -> Option<(u32, u8)> {
        self.g.succs[self.cur() as usize]
            .iter()
            .copied()
            .find(|&(q, _)| !self.st.cyc.visited.get(q as usize))
    }

    /// All unvisited successors, in sorted (weight, suffix) order.
    pub fn unvisited_succs(&self) -> Vec<(u32, u8)> {
        self.g.succs[self.cur() as usize]
            .iter()
            .copied()
            .filter(|&(q, _)| !self.st.cyc.visited.get(q as usize))
            .collect()
    }

    /// Lowest-ranked unvisited permutation — the target of the explicit
    /// weight-`n` fallback jump. Panics if the walk is done.
    pub fn fallback_target(&self) -> u32 {
        self.st
            .cyc
            .visited
            .first_clear(self.g.nfact)
            .expect("fallback_target called on a completed walk") as u32
    }

    /// Visit `rank` by appending `weight` characters (the last `weight`
    /// symbols of the target permutation), updating all counters through
    /// the shared [`SearchState::advance`].
    pub fn advance(&mut self, rank: u32, weight: u8) {
        let n = self.g.n;
        let w = weight as usize;
        debug_assert!((1..=n).contains(&w));
        let q = &self.g.perms[rank as usize];
        // The prefix of Q not appended must already be the string's tail.
        debug_assert_eq!(&self.chars[self.chars.len() - (n - w)..], &q[..n - w]);
        self.chars.extend_from_slice(&q[n - w..]);
        self.st
            .advance(self.g, rank, weight as u32, Some(&self.tab));
        debug_assert_eq!(self.st.cyc.len as usize, self.chars.len());
    }

    /// Admissible lower bound on the characters still needed from this
    /// state (see [`crate::bound::lower_bound`]).
    pub fn lb(&self) -> usize {
        let cur_rem = self.st.cyc.cycle_rem[self.g.cycle_id[self.cur() as usize] as usize];
        lower_bound(self.st.cyc.r as usize, self.st.cyc.k as usize, cur_rem > 0)
    }

    /// Whether the current permutation's weight-1 successor is unvisited.
    pub fn succ1_unvisited(&self) -> bool {
        !self.st.cyc.visited.get(self.g.succ1(self.cur()) as usize)
    }

    /// Arc-refined admissible lower bound; dominates [`Walk::lb`]
    /// pointwise (see [`crate::bound::lower_bound_arc`]).
    pub fn lb_arc(&self) -> usize {
        lower_bound_arc(
            self.st.cyc.r as usize,
            self.st.arcs as usize,
            self.succ1_unvisited(),
        )
    }

    /// Residual admissible lower bound; dominates [`Walk::lb_arc`]
    /// pointwise (see [`crate::lb_residual`]).
    pub fn lb_residual(&self) -> usize {
        crate::lb_residual::lower_bound_residual(
            self.st.cyc.r as usize,
            self.st.cyc.door as usize,
            self.st.cyc.intact as usize,
            self.st.cyc.long as usize,
        )
    }

    /// The weight-≤3 in-neighbour table backing the residual bound.
    pub fn pred_table(&self) -> &PredTable {
        &self.tab
    }

    /// Snapshot the state as a [`Features`] record (`cost_to_go` is left
    /// 0; the rollout generator fills it in once the final length is
    /// known).
    pub fn features(&self) -> Features {
        Features {
            n: self.g.n as u32,
            step: self.st.steps,
            r: self.st.cyc.r,
            cycles_remaining: self.st.cyc.k,
            intact_cycles: self.st.cyc.intact,
            current_cycle_remaining: u32::from(
                self.st.cyc.cycle_rem[self.g.cycle_id[self.cur() as usize] as usize],
            ),
            arcs: self.st.arcs,
            succ1_unvisited: u32::from(self.succ1_unvisited()),
            half_open: self.st.half_open,
            nearly_done: self.st.nearly_done,
            w2_bridges: self.st.w2_bridges,
            len_so_far: self.chars.len() as u32,
            cost_to_go: 0,
        }
    }

    /// Render the emitted symbols as ASCII digits `'1'..='8'`.
    pub fn string(&self) -> String {
        self.chars.iter().map(|&v| (b'0' + v) as char).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn start_state_counters() {
        let g = Graph::new(4);
        let w = Walk::new(&g);
        assert_eq!(w.st.cyc.r, 23);
        assert_eq!(w.st.cyc.k, 6);
        assert_eq!(w.len_chars(), 4);
        assert_eq!(w.string(), "1234");
        let f = w.features();
        assert_eq!(f.r, 23);
        assert_eq!(f.cycles_remaining, 6);
        assert_eq!(f.intact_cycles, 5);
        assert_eq!(f.current_cycle_remaining, 3);
        assert_eq!(f.arcs, 6);
        assert_eq!(f.succ1_unvisited, 1);
        assert_eq!(f.half_open, 1);
        assert_eq!(f.nearly_done, 0);
        assert_eq!(f.w2_bridges, 0);
        // lb = 23 + 6 − 1 = 28 ≤ 33 − 4.
        assert_eq!(w.lb(), 28);
        // At the start arcs == cycles, so the bounds coincide.
        assert_eq!(w.lb_arc(), 28);
    }

    #[test]
    fn arcs_incremental_matches_scratch_and_bound_dominates() {
        for n in [4usize, 5] {
            let g = Graph::new(n);
            let path = crate::greedy::greedy(&g).path;
            let mut w = Walk::new(&g);
            for &rank in &path[1..] {
                let weight = match w.first_unvisited_succ() {
                    Some((q, wt)) if q == rank => wt,
                    _ => {
                        let p = &g.perms[w.cur() as usize];
                        (n - Graph::overlap(p, &g.perms[rank as usize])) as u8
                    }
                };
                w.advance(rank, weight);
                assert!(w.lb_arc() >= w.lb(), "n={n} step={}", w.steps());
            }
            assert_eq!(w.st.arcs, 0);
            assert_eq!(w.lb_arc(), 0);
        }
    }

    /// Every counter the walk maintains incrementally must match the
    /// from-scratch reference recount at every step of random ε-greedy
    /// walks (off the greedy path, so the cycle-status transitions are
    /// exercised in arbitrary orders). The counter rules themselves are
    /// pinned in `crate::state`; this pins that `Walk::advance` drives
    /// them with the right arguments.
    #[test]
    fn walk_counters_match_scratch_on_random_walks() {
        use rand::rngs::StdRng;
        use rand::{Rng, SeedableRng};
        for n in [4usize, 5] {
            for seed in 0..4u64 {
                let mut rng = StdRng::seed_from_u64(seed);
                let g = Graph::new(n);
                let mut w = Walk::new(&g);
                while !w.done() {
                    let options = w.unvisited_succs();
                    let (q, wt) = if options.is_empty() {
                        (w.fallback_target(), n as u8)
                    } else if rng.gen::<f64>() < 0.3 {
                        options[rng.gen_range(0..options.len())]
                    } else {
                        options[0]
                    };
                    w.advance(q, wt);
                    let scratch = SearchState::recount(
                        &g,
                        &w.st.cyc.visited,
                        w.cur(),
                        w.len_chars() as u32,
                        w.steps(),
                        Some(w.pred_table()),
                    );
                    assert!(
                        w.st.counters_eq(&scratch),
                        "n={n} seed={seed} step={}\n  walk {}\n  ref  {}",
                        w.steps(),
                        w.st.counters(),
                        scratch.counters()
                    );
                }
                assert_eq!(w.st.half_open, 0);
                assert_eq!(w.st.nearly_done, 0);
                assert_eq!(w.st.w2_bridges, 0);
                assert_eq!(w.st.arcs, 0);
            }
        }
    }

    #[test]
    fn advance_updates_counters() {
        let g = Graph::new(3);
        let mut w = Walk::new(&g);
        let (q, wt) = w.first_unvisited_succ().unwrap();
        assert_eq!(wt, 1); // left rotation 231
        w.advance(q, wt);
        assert_eq!(w.string(), "1231");
        assert_eq!(w.st.cyc.r, 4);
        assert_eq!(w.st.cyc.k, 2);
    }
}
