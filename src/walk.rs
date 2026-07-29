//! Incremental walk state shared by the greedy searcher and the rollout
//! generator.
//!
//! A [`Walk`] tracks the string built so far, the visited set, and the
//! per-cycle unvisited counts needed to evaluate the admissible lower
//! bound of [`crate::bound`] in O(1) per move.

use crate::bitset::BitSet;
use crate::bound::{lower_bound, lower_bound_arc, Features};
use crate::graph::Graph;
use crate::lb_residual::{self, ParentCtx, PredTable};

/// A partial superpermutation under construction.
///
/// Starts at rank 0 (the identity permutation) with its `n` characters
/// already emitted. Each [`Walk::advance`] visits one new permutation by
/// appending `weight` characters.
pub struct Walk<'g> {
    g: &'g Graph,
    /// Visited permutations by rank.
    pub visited: BitSet,
    /// `cycle_rem[c]` = number of unvisited permutations in cycle `c`.
    pub cycle_rem: Box<[u8]>,
    /// Number of cycles with at least one unvisited permutation.
    pub k: usize,
    /// Number of unvisited permutations.
    pub r: usize,
    /// Weight-1 connected components (arcs) among unvisited permutations.
    /// A fully-unvisited cycle counts as one (circular) component.
    pub arcs: usize,
    /// Cycles with exactly 1 or 2 visited members
    /// (`cycle_rem ∈ {n−1, n−2}`) — half-open (phase-3 item 3).
    pub half_open: usize,
    /// Cycles with exactly 1 or 2 unvisited members
    /// (`cycle_rem ∈ {1, 2}`) — nearly done (phase-3 item 3).
    pub nearly_done: usize,
    /// Live cross-cycle weight-2 edges joining two partially-visited
    /// cycles (see [`Graph::w2_bridges_delta`] for the exact
    /// definition; phase-3 item 3).
    pub w2_bridges: usize,
    /// Rank of the permutation the string currently ends with.
    pub cur: u32,
    /// The emitted symbols (values `1..=n`).
    pub chars: Vec<u8>,
    /// Number of advances taken (permutations visited − 1).
    pub steps: u32,
    /// Cycles with all `n` members unvisited (intact) — the `intact`
    /// term of [`crate::lb_residual`].
    pub intact: usize,
    /// `Σ_{x unvisited} (minin(x) − 1)`, the `door` term of
    /// [`crate::lb_residual`].
    pub door: u32,
    /// The dead-door singly-covered-class term of
    /// [`crate::lb_residual`].
    pub long: u32,
    /// Tabulated weight-≤3 in-neighbours (drives `door`/`long`).
    tab: PredTable,
}

impl<'g> Walk<'g> {
    /// Fresh walk positioned at the identity permutation (rank 0).
    pub fn new(g: &'g Graph) -> Walk<'g> {
        let mut visited = BitSet::new(g.nfact);
        visited.set(0);
        let mut cycle_rem = vec![g.n as u8; g.cycle_count].into_boxed_slice();
        cycle_rem[g.cycle_id[0] as usize] -= 1;
        let tab = PredTable::new(g);
        // At the root every permutation is standable, so every `minin`
        // is 1 (`pred1` is always available) and no class but rank 0's
        // is touched: `door = long = 0`. Computed rather than asserted
        // so the initialisation cannot drift from the definitions.
        let door = lb_residual::door_scratch(g, &tab, &visited, 0);
        let long = lb_residual::long_scratch(g, &visited, 0, &cycle_rem);
        Walk {
            g,
            visited,
            cycle_rem,
            k: g.cycle_count, // n ≥ 3 ⇒ every cycle still has unvisited members
            r: g.nfact - 1,
            // Every intact cycle is one circular component; visiting rank 0
            // turned its cycle into a single open arc — still one component.
            arcs: g.cycle_count,
            // Rank 0's cycle has exactly 1 visited member: half-open. It
            // is also nearly done iff n − 1 ≤ 2. No second cycle is
            // touched yet, so no w2 bridge can join two touched cycles.
            half_open: 1,
            nearly_done: usize::from(g.n - 1 <= 2),
            w2_bridges: 0,
            cur: 0,
            chars: g.perms[0].clone(),
            steps: 0,
            intact: g.cycle_count - 1,
            door,
            long,
            tab,
        }
    }

    /// The graph this walk lives in.
    pub fn graph(&self) -> &'g Graph {
        self.g
    }

    /// Whether every permutation has been visited.
    pub fn done(&self) -> bool {
        self.r == 0
    }

    /// Characters emitted so far.
    pub fn len_chars(&self) -> usize {
        self.chars.len()
    }

    /// First unvisited successor in the sorted list (minimum weight,
    /// then lexicographically smallest appended suffix), if any.
    pub fn first_unvisited_succ(&self) -> Option<(u32, u8)> {
        self.g.succs[self.cur as usize]
            .iter()
            .copied()
            .find(|&(q, _)| !self.visited.get(q as usize))
    }

    /// All unvisited successors, in sorted (weight, suffix) order.
    pub fn unvisited_succs(&self) -> Vec<(u32, u8)> {
        self.g.succs[self.cur as usize]
            .iter()
            .copied()
            .filter(|&(q, _)| !self.visited.get(q as usize))
            .collect()
    }

    /// Lowest-ranked unvisited permutation — the target of the explicit
    /// weight-`n` fallback jump. Panics if the walk is done.
    pub fn fallback_target(&self) -> u32 {
        self.visited
            .first_clear(self.g.nfact)
            .expect("fallback_target called on a completed walk") as u32
    }

    /// Visit `rank` by appending `weight` characters (the last `weight`
    /// symbols of the target permutation), updating all counters.
    pub fn advance(&mut self, rank: u32, weight: u8) {
        let n = self.g.n;
        let w = weight as usize;
        debug_assert!((1..=n).contains(&w));
        debug_assert!(!self.visited.get(rank as usize), "revisit of {rank}");
        let q = &self.g.perms[rank as usize];
        // The prefix of Q not appended must already be the string's tail.
        debug_assert_eq!(&self.chars[self.chars.len() - (n - w)..], &q[..n - w]);
        self.chars.extend_from_slice(&q[n - w..]);
        // w2-bridge delta needs the pre-move (visited, cycle_rem) state.
        let w2d = self
            .g
            .w2_bridges_delta(&self.visited, &self.cycle_rem, rank);
        // Residual-bound terms, likewise from the pre-move state.
        let ctx = ParentCtx::new(
            self.g,
            &self.tab,
            &self.visited,
            self.cur,
            &self.cycle_rem,
            self.door,
            self.long,
        );
        let (door, long) = lb_residual::child_terms(
            self.g,
            &self.tab,
            &self.visited,
            &self.cycle_rem,
            &ctx,
            rank,
        );
        self.door = door;
        self.long = long;
        self.intact -=
            usize::from(self.cycle_rem[self.g.cycle_id[rank as usize] as usize] as usize == n);
        self.visited.set(rank as usize);
        let cid = self.g.cycle_id[rank as usize] as usize;
        // Arc maintenance. If the cycle was fully unvisited its circular
        // component becomes one open arc (no change); otherwise the count
        // changes by the visited status of the two ring neighbors:
        // both unvisited → the arc splits (+1); both visited → a
        // singleton arc disappears (−1); mixed → an endpoint shrinks (0).
        if (self.cycle_rem[cid] as usize) < n {
            let p_unvis = !self.visited.get(self.g.pred1[rank as usize] as usize);
            let s_unvis = !self.visited.get(self.g.succ1(rank) as usize);
            if p_unvis && s_unvis {
                self.arcs += 1;
            } else if !p_unvis && !s_unvis {
                self.arcs -= 1;
            }
        }
        // Half-open / nearly-done counters, from the pre-decrement
        // per-cycle unvisited count (same case analysis as the beam's
        // `child_state`).
        let rem = self.cycle_rem[cid] as usize;
        self.half_open = self.half_open + usize::from(rem == n) - usize::from(rem == n - 2);
        self.nearly_done = self.nearly_done + usize::from(rem == 3) - usize::from(rem == 1);
        self.w2_bridges = (self.w2_bridges as i64 + w2d) as usize;
        self.cycle_rem[cid] -= 1;
        if self.cycle_rem[cid] == 0 {
            self.k -= 1;
        }
        self.r -= 1;
        self.cur = rank;
        self.steps += 1;
    }

    /// Admissible lower bound on the characters still needed from this
    /// state (see [`crate::bound::lower_bound`]).
    pub fn lb(&self) -> usize {
        let cur_rem = self.cycle_rem[self.g.cycle_id[self.cur as usize] as usize];
        lower_bound(self.r, self.k, cur_rem > 0)
    }

    /// Whether the current permutation's weight-1 successor is unvisited.
    pub fn succ1_unvisited(&self) -> bool {
        !self.visited.get(self.g.succ1(self.cur) as usize)
    }

    /// Arc-refined admissible lower bound; dominates [`Walk::lb`]
    /// pointwise (see [`crate::bound::lower_bound_arc`]).
    pub fn lb_arc(&self) -> usize {
        lower_bound_arc(self.r, self.arcs, self.succ1_unvisited())
    }

    /// Residual admissible lower bound; dominates [`Walk::lb_arc`]
    /// pointwise (see [`crate::lb_residual`]).
    pub fn lb_residual(&self) -> usize {
        lb_residual::lower_bound_residual(
            self.r,
            self.door as usize,
            self.intact,
            self.long as usize,
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
        let intact = self
            .cycle_rem
            .iter()
            .filter(|&&c| c as usize == self.g.n)
            .count();
        Features {
            n: self.g.n as u32,
            step: self.steps,
            r: self.r as u32,
            cycles_remaining: self.k as u32,
            intact_cycles: intact as u32,
            current_cycle_remaining: self.cycle_rem[self.g.cycle_id[self.cur as usize] as usize]
                as u32,
            arcs: self.arcs as u32,
            succ1_unvisited: u32::from(self.succ1_unvisited()),
            half_open: self.half_open as u32,
            nearly_done: self.nearly_done as u32,
            w2_bridges: self.w2_bridges as u32,
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
        assert_eq!(w.r, 23);
        assert_eq!(w.k, 6);
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

    /// From-scratch arc recount: every arc has exactly one head (an
    /// unvisited rank whose weight-1 predecessor is visited), except a
    /// fully-unvisited cycle, which is circular and has none.
    fn arcs_scratch(w: &Walk) -> usize {
        let g = w.graph();
        let heads = (0..g.nfact)
            .filter(|&x| !w.visited.get(x) && w.visited.get(g.pred1[x] as usize))
            .count();
        let intact = w.cycle_rem.iter().filter(|&&c| c as usize == g.n).count();
        heads + intact
    }

    #[test]
    fn arcs_incremental_matches_scratch_and_bound_dominates() {
        for n in [4usize, 5] {
            let g = Graph::new(n);
            let path = crate::greedy::greedy(&g).path;
            let mut w = Walk::new(&g);
            assert_eq!(w.arcs, arcs_scratch(&w));
            for &rank in &path[1..] {
                let weight = match w.first_unvisited_succ() {
                    Some((q, wt)) if q == rank => wt,
                    _ => {
                        let p = &g.perms[w.cur as usize];
                        (n - Graph::overlap(p, &g.perms[rank as usize])) as u8
                    }
                };
                w.advance(rank, weight);
                assert_eq!(w.arcs, arcs_scratch(&w), "n={n} step={}", w.steps);
                assert!(w.lb_arc() >= w.lb(), "n={n} step={}", w.steps);
            }
            assert_eq!(w.arcs, 0);
            assert_eq!(w.lb_arc(), 0);
        }
    }

    /// From-scratch recounts of the phase-3 deficit-distribution
    /// counters (definitions in the field docs / `w2_bridges_delta`).
    fn deficit_scratch(w: &Walk) -> (usize, usize, usize) {
        let g = w.graph();
        let n = g.n;
        let half_open = w
            .cycle_rem
            .iter()
            .filter(|&&c| {
                let visited = n - c as usize;
                (1..=2).contains(&visited)
            })
            .count();
        let nearly_done = w
            .cycle_rem
            .iter()
            .filter(|&&c| (1..=2).contains(&(c as usize)))
            .count();
        let touched = |x: usize| (w.cycle_rem[g.cycle_id[x] as usize] as usize) < n;
        let w2_bridges = (0..g.nfact)
            .filter(|&p| {
                let q = g.w2x[p] as usize;
                !w.visited.get(p) && !w.visited.get(q) && touched(p) && touched(q)
            })
            .count();
        (half_open, nearly_done, w2_bridges)
    }

    /// The incrementally maintained deficit-distribution counters must
    /// match from-scratch recounts at every step of random ε-greedy
    /// walks (the arcs-oracle pattern, but off the greedy path so the
    /// cycle-status transitions are exercised in arbitrary orders).
    #[test]
    fn deficit_counters_match_scratch_on_random_walks() {
        use rand::rngs::StdRng;
        use rand::{Rng, SeedableRng};
        for n in [4usize, 5] {
            for seed in 0..4u64 {
                let mut rng = StdRng::seed_from_u64(seed);
                let g = Graph::new(n);
                let mut w = Walk::new(&g);
                assert_eq!(
                    (w.half_open, w.nearly_done, w.w2_bridges),
                    deficit_scratch(&w)
                );
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
                    assert_eq!(
                        (w.half_open, w.nearly_done, w.w2_bridges),
                        deficit_scratch(&w),
                        "n={n} seed={seed} step={}",
                        w.steps
                    );
                }
                assert_eq!(w.half_open, 0);
                assert_eq!(w.nearly_done, 0);
                assert_eq!(w.w2_bridges, 0);
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
        assert_eq!(w.r, 4);
        assert_eq!(w.k, 2);
    }
}
