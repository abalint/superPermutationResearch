//! Incremental walk state shared by the greedy searcher and the rollout
//! generator.
//!
//! A [`Walk`] tracks the string built so far, the visited set, and the
//! per-cycle unvisited counts needed to evaluate the admissible lower
//! bound of [`crate::bound`] in O(1) per move.

use crate::bitset::BitSet;
use crate::bound::{lower_bound, Features};
use crate::graph::Graph;

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
    /// Rank of the permutation the string currently ends with.
    pub cur: u32,
    /// The emitted symbols (values `1..=n`).
    pub chars: Vec<u8>,
    /// Number of advances taken (permutations visited − 1).
    pub steps: u32,
}

impl<'g> Walk<'g> {
    /// Fresh walk positioned at the identity permutation (rank 0).
    pub fn new(g: &'g Graph) -> Walk<'g> {
        let mut visited = BitSet::new(g.nfact);
        visited.set(0);
        let mut cycle_rem = vec![g.n as u8; g.cycle_count].into_boxed_slice();
        cycle_rem[g.cycle_id[0] as usize] -= 1;
        Walk {
            g,
            visited,
            cycle_rem,
            k: g.cycle_count, // n ≥ 3 ⇒ every cycle still has unvisited members
            r: g.nfact - 1,
            cur: 0,
            chars: g.perms[0].clone(),
            steps: 0,
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
        self.visited.set(rank as usize);
        let cid = self.g.cycle_id[rank as usize] as usize;
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
        // lb = 23 + 6 − 1 = 28 ≤ 33 − 4.
        assert_eq!(w.lb(), 28);
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
