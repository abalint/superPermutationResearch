//! Epsilon-greedy rollout generator — training data for a future value
//! network.
//!
//! Each rollout walks the graph from the identity permutation until all
//! `n!` permutations are visited. At every step, with probability
//! `epsilon` a uniformly random unvisited successor is taken, otherwise
//! the exploit move: the greedy (first sorted) successor, or — with a
//! [`Guide`] — the successor minimizing the learned beam score
//! `len + weight + alpha * predict(child features)` (plus the child's
//! `lb_arc` for residual-target models), ties broken by the sorted
//! successor order. If no stored successor is unvisited the weight-`n`
//! fallback jump to the lowest-ranked unvisited permutation is applied —
//! exactly the greedy searcher's rule.
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
use crate::model::Model;
use crate::walk::Walk;

/// Learned policy for the exploit branch of a rollout.
#[derive(Clone, Copy)]
pub struct Guide<'m> {
    /// Learned cost-to-go (or residual) predictor.
    pub model: &'m Model,
    /// Blend factor multiplying the prediction.
    pub alpha: f64,
}

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

/// The child's full feature vector (matching
/// [`crate::model::FEATURE_ORDER_V2`]; models consuming only the
/// 8-feature prefix read the same values as before) and its `lb_arc`
/// for the move `walk.cur → q`, computed in O(1) from the walk's
/// counters without advancing it (O(n) when `q` first touches an intact
/// cycle — the `w2_bridges` scan) — the [`Walk`] counterpart of the
/// beam's `score_move`, reading the same shared child rules
/// ([`crate::state`]).
fn child_features(g: &Graph, walk: &Walk, q: u32) -> ([f64; 11], u32) {
    let st = &walk.st;
    let r = st.cyc.r - 1;
    let k = st.cyc.child_k(g, q);
    let intact = st.cyc.child_intact(g, q);
    let cur_rem = st.cyc.child_cur_rem(g, q);
    let arcs = st.child_arcs(g, q);
    let succ1_unvis = u32::from(!st.cyc.visited.get(g.succ1(q) as usize));
    let lb_cycle = if r == 0 {
        0
    } else {
        r + k - u32::from(cur_rem > 0)
    };
    let lb_arc = if r == 0 { 0 } else { r + arcs - succ1_unvis };
    let half_open = st.child_half_open(g, q);
    let nearly_done = st.child_nearly_done(g, q);
    let w2_bridges = st.child_w2_bridges(g, q);
    let x = [
        f64::from(r),
        f64::from(k),
        f64::from(intact),
        f64::from(cur_rem),
        f64::from(arcs),
        f64::from(succ1_unvis),
        f64::from(lb_cycle),
        f64::from(lb_arc),
        f64::from(half_open),
        f64::from(nearly_done),
        f64::from(w2_bridges),
    ];
    (x, lb_arc)
}

/// The option minimizing the learned beam score, ties broken by the
/// sorted (weight, suffix) order of `options`.
fn best_guided(g: &Graph, walk: &Walk, options: &[(u32, u8)], guide: Guide) -> (u32, u8) {
    let len = walk.len_chars() as u32;
    let mut best = options[0];
    let mut best_score = f64::INFINITY;
    for &(q, w) in options {
        let (x, lb_arc) = child_features(g, walk, q);
        let base = if guide.model.is_residual() {
            len + u32::from(w) + lb_arc
        } else {
            len + u32::from(w)
        };
        let score = f64::from(base) + guide.alpha * guide.model.predict(&x);
        if score < best_score {
            best_score = score;
            best = (q, w);
        }
    }
    best
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
    run_rollouts_guided(g, count, epsilon, seed, None, out)
}

/// [`run_rollouts`] with an optional model [`Guide`] replacing the
/// greedy exploit move (the epsilon-random exploration and the RNG
/// stream are unchanged, so `guide = None` is exactly `run_rollouts`).
pub fn run_rollouts_guided(
    g: &Graph,
    count: usize,
    epsilon: f64,
    seed: u64,
    guide: Option<Guide>,
    out: &mut impl Write,
) -> io::Result<RolloutSummary> {
    run_rollouts_strings(g, count, epsilon, seed, guide, out, None)
}

/// [`run_rollouts_guided`] that additionally writes each completed
/// rollout's superpermutation string (one per line) to `strings_out` —
/// the walk-level corpus consumed by Track B's identity verifier
/// (`analysis/trackb/verify_identity.py`). The RNG stream and JSONL
/// output are byte-identical to [`run_rollouts_guided`].
pub fn run_rollouts_strings(
    g: &Graph,
    count: usize,
    epsilon: f64,
    seed: u64,
    guide: Option<Guide>,
    out: &mut impl Write,
    mut strings_out: Option<&mut dyn Write>,
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
                match guide {
                    Some(gd) => best_guided(g, &walk, &options, gd),
                    None => options[0],
                }
            };
            walk.advance(q, w);
            records.push(walk.features());
        }

        let final_len = walk.len_chars();
        total += final_len as u64;
        min_len = min_len.min(final_len);
        if let Some(w) = strings_out.as_deref_mut() {
            w.write_all(walk.string().as_bytes())?;
            w.write_all(b"\n")?;
        }
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

/// Replay a completed visit-order `path` (ranks, starting at 0) through a
/// [`Walk`] and write one JSONL [`Features`] line per state with
/// `cost_to_go` backfilled — the trajectory-logging counterpart of
/// [`run_rollouts`] for greedy and beam paths. Returns lines written.
pub fn log_trajectory(g: &Graph, path: &[u32], out: &mut impl Write) -> io::Result<usize> {
    assert_eq!(path.first(), Some(&0), "paths must start at the identity");
    let mut walk = Walk::new(g);
    let mut records: Vec<Features> = Vec::with_capacity(path.len());
    records.push(walk.features());
    for &rank in &path[1..] {
        let p = &g.perms[walk.cur() as usize];
        let w = (g.n - Graph::overlap(p, &g.perms[rank as usize])) as u8;
        walk.advance(rank, w);
        records.push(walk.features());
    }
    let final_len = walk.len_chars() as u32;
    let mut lines = 0usize;
    for mut f in records {
        f.cost_to_go = final_len - f.len_so_far;
        serde_json::to_writer(&mut *out, &f)?;
        out.write_all(b"\n")?;
        lines += 1;
    }
    Ok(lines)
}
