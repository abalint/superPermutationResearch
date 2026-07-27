//! Epsilon-greedy rollout generator — training data for a future value
//! network.
//!
//! Each rollout walks the graph from the identity permutation until all
//! `n!` permutations are visited. At every step, with probability
//! `epsilon` a uniformly random unvisited successor is taken, otherwise
//! the greedy (first sorted) one; if no stored successor is unvisited
//! the weight-`n` fallback jump to the lowest-ranked unvisited
//! permutation is applied — exactly the greedy searcher's rule.
//!
//! Rollout `i` uses `StdRng::seed_from_u64(seed + i)`, so output is
//! fully reproducible. After a rollout completes, one JSONL line is
//! emitted per visited step (that is, `n!` lines: the start state and
//! each advance) containing a [`Features`] record with
//! `cost_to_go = final_len − len_so_far` filled in retroactively.

use std::io::{self, Write};

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

use crate::bound::Features;
use crate::graph::Graph;
use crate::walk::Walk;

/// Summary statistics for a batch of rollouts.
pub struct RolloutSummary {
    /// Number of rollouts performed.
    pub rollouts: usize,
    /// Mean final superpermutation length.
    pub mean_len: f64,
    /// Minimum final superpermutation length.
    pub min_len: usize,
    /// JSONL lines written (`rollouts × n!`).
    pub lines: usize,
}

/// Run `count` epsilon-greedy rollouts on `g`, writing one JSONL
/// [`Features`] line per visited step to `out`.
pub fn run_rollouts(
    g: &Graph,
    count: usize,
    epsilon: f64,
    seed: u64,
    out: &mut impl Write,
) -> io::Result<RolloutSummary> {
    let mut lines = 0usize;
    let mut total = 0u64;
    let mut min_len = usize::MAX;

    for i in 0..count {
        let mut rng = StdRng::seed_from_u64(seed.wrapping_add(i as u64));
        let mut walk = Walk::new(g);
        let mut records: Vec<Features> = Vec::with_capacity(g.nfact);
        records.push(walk.features());

        while !walk.done() {
            let options = walk.unvisited_succs();
            let (q, w) = if options.is_empty() {
                (walk.fallback_target(), g.n as u8)
            } else if rng.gen::<f64>() < epsilon {
                options[rng.gen_range(0..options.len())]
            } else {
                options[0]
            };
            walk.advance(q, w);
            records.push(walk.features());
        }

        let final_len = walk.len_chars();
        total += final_len as u64;
        min_len = min_len.min(final_len);
        for mut f in records {
            f.cost_to_go = final_len as u32 - f.len_so_far;
            serde_json::to_writer(&mut *out, &f)?;
            out.write_all(b"\n")?;
            lines += 1;
        }
    }

    Ok(RolloutSummary {
        rollouts: count,
        mean_len: if count == 0 {
            0.0
        } else {
            total as f64 / count as f64
        },
        min_len: if count == 0 { 0 } else { min_len },
        lines,
    })
}
