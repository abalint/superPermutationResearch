//! Deterministic greedy baseline.
//!
//! From the identity permutation, repeatedly take the first unvisited
//! successor in the sorted successor list — i.e. the move that appends
//! the fewest characters, breaking ties by lexicographically smallest
//! appended suffix. If every stored (weight ≤ n−1) successor is already
//! visited but permutations remain, jump (weight `n`, zero overlap) to
//! the lowest-ranked unvisited permutation.
//!
//! This classic greedy construction produces the known minimal lengths
//! 9, 33 and 153 for `n = 3, 4, 5` (a hard acceptance criterion tested
//! in `tests/known_optima.rs`) and 873 for `n = 6`.

use crate::graph::Graph;
use crate::walk::Walk;

/// Result of a greedy run.
pub struct GreedyResult {
    /// The completed superpermutation as ASCII digits.
    pub string: String,
    /// Its length in characters.
    pub len: usize,
    /// Ranks of the permutations in visit order (starts with 0).
    pub path: Vec<u32>,
}

/// Run the deterministic greedy search on `g` (see module docs).
pub fn greedy(g: &Graph) -> GreedyResult {
    let mut walk = Walk::new(g);
    let mut path = Vec::with_capacity(g.nfact);
    path.push(0u32);
    while !walk.done() {
        let (q, w) = match walk.first_unvisited_succ() {
            Some(step) => step,
            None => (walk.fallback_target(), g.n as u8),
        };
        walk.advance(q, w);
        path.push(q);
    }
    GreedyResult {
        string: walk.string(),
        len: walk.len_chars(),
        path,
    }
}
