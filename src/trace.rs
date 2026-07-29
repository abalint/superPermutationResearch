//! Trajectory extraction from existing superpermutation strings.
//!
//! Given a complete superpermutation string (e.g. a community record),
//! recover the walk our searchers would represent it as: the
//! *first-visit order* of permutation ranks (sliding a width-`n` window
//! and recording each rank the first time its window appears), then a
//! replay of that path through a [`Walk`] using maximal-overlap edge
//! weights. For tight strings (every window advances the walk) the
//! replay reconstructs the input exactly; the replay length can only be
//! shorter, never longer, so `replay_len == input_len` certifies the
//! string wastes no characters on revisits.
//!
//! [`score_state`] mirrors the beam's `score_move` fixed-point
//! arithmetic exactly (including the residual-target anchor), so
//! trajectory states can be compared against beam cutoff scores
//! (`beam_search_cutoffs`) with no rounding skew.

use crate::beam::{Bound, Scorer};
use crate::graph::{rank, Graph};
use crate::walk::Walk;

/// A superpermutation string reduced to walk form.
pub struct Trace {
    /// First-visit order of permutation ranks (starts at the string's
    /// first covered permutation).
    pub path: Vec<u32>,
    /// Maximal-overlap edge weight of each move (`path.len() − 1`).
    pub weights: Vec<u8>,
    /// Length of the input string in characters.
    pub input_len: usize,
    /// Length of the maximal-overlap replay (`n` + Σ weights); equals
    /// `input_len` iff the string realizes every maximal overlap.
    pub replay_len: usize,
    /// Histogram of move weights: `hist[w]` = number of weight-`w`
    /// moves, `w` in `1..=n`.
    pub hist: Vec<usize>,
}

/// First-visit order of permutation ranks covered by `s` (values
/// `'1'..='8'`; any window that is not a permutation of `1..=n`
/// contributes nothing). Errors if `s` covers no permutation.
pub fn extract_path(n: usize, s: &str) -> Result<Vec<u32>, String> {
    let nfact = crate::graph::factorial(n);
    let vals: Vec<u8> = s
        .chars()
        .map(|c| match c {
            '1'..='8' => c as u8 - b'0',
            _ => 0,
        })
        .map(|v| if (v as usize) <= n { v } else { 0 })
        .collect();
    let mut seen = vec![false; nfact];
    let mut path = Vec::new();
    if vals.len() >= n {
        for win in vals.windows(n) {
            let mut mask = 0u16;
            for &v in win {
                mask |= 1u16 << v;
            }
            if mask == ((1u16 << n) - 1) << 1 {
                let r = rank(win);
                if !seen[r] {
                    seen[r] = true;
                    path.push(r as u32);
                }
            }
        }
    }
    if path.is_empty() {
        return Err(format!("string covers no permutation of 1..={n}"));
    }
    Ok(path)
}

/// Extract the first-visit path of `s` and replay it with
/// maximal-overlap weights. Errors if the string covers no permutation
/// or does not start at the identity (rank 0) — every searcher in this
/// crate starts there, and [`crate::rollout::log_trajectory`] asserts
/// it.
pub fn trace_string(g: &Graph, s: &str) -> Result<Trace, String> {
    let path = extract_path(g.n, s)?;
    if path[0] != 0 {
        return Err(format!(
            "string starts at rank {} (permutation {:?}), not the identity",
            path[0], g.perms[path[0] as usize]
        ));
    }
    let mut walk = Walk::new(g);
    let mut weights = Vec::with_capacity(path.len() - 1);
    for &q in &path[1..] {
        let p = &g.perms[walk.cur as usize];
        let w = (g.n - Graph::overlap(p, &g.perms[q as usize])) as u8;
        walk.advance(q, w);
        weights.push(w);
    }
    let mut hist = vec![0usize; g.n + 1];
    for &w in &weights {
        hist[w as usize] += 1;
    }
    Ok(Trace {
        path,
        weights,
        input_len: s.len(),
        replay_len: walk.len_chars(),
        hist,
    })
}

/// Score a walk state exactly as the beam's `score_move` would score
/// the candidate that produced it: `len + lb` for a bound, or
/// `len + α·pred` (`len + lb_arc + α·pred` for residual-target models)
/// for a learned model — passed through the beam's `i64` fixed-point
/// representation (12 fractional bits) and back, so the returned `f64`
/// is bit-comparable with `beam_search_cutoffs` thresholds divided by
/// 4096.
pub fn score_state(walk: &Walk, scorer: Scorer) -> f64 {
    let len = walk.len_chars() as u32;
    let fixed: i64 = match scorer {
        Scorer::Bound(Bound::Cycle) => i64::from(len + walk.lb() as u32) << 12,
        Scorer::Bound(Bound::Arc) => i64::from(len + walk.lb_arc() as u32) << 12,
        Scorer::Bound(Bound::Residual) => i64::from(len + walk.lb_residual() as u32) << 12,
        Scorer::Learned { model, alpha } => {
            let f = walk.features();
            let lb_cycle = walk.lb() as u32;
            let lb_arc = walk.lb_arc() as u32;
            let x = [
                f64::from(f.r),
                f64::from(f.cycles_remaining),
                f64::from(f.intact_cycles),
                f64::from(f.current_cycle_remaining),
                f64::from(f.arcs),
                f64::from(f.succ1_unvisited),
                f64::from(lb_cycle),
                f64::from(lb_arc),
                f64::from(f.half_open),
                f64::from(f.nearly_done),
                f64::from(f.w2_bridges),
            ];
            let pred = model.predict(&x);
            let base = if model.is_residual() {
                len + lb_arc
            } else {
                len
            };
            ((f64::from(base) + alpha * pred) * 4096.0).round() as i64
        }
        Scorer::Composed {
            bound,
            model,
            alpha,
        } => {
            let f = walk.features();
            let lb_cycle = walk.lb() as u32;
            let lb_arc = walk.lb_arc() as u32;
            let x = [
                f64::from(f.r),
                f64::from(f.cycles_remaining),
                f64::from(f.intact_cycles),
                f64::from(f.current_cycle_remaining),
                f64::from(f.arcs),
                f64::from(f.succ1_unvisited),
                f64::from(lb_cycle),
                f64::from(lb_arc),
                f64::from(f.half_open),
                f64::from(f.nearly_done),
                f64::from(f.w2_bridges),
            ];
            let pred = model.predict(&x);
            let lb = match bound {
                Bound::Cycle => lb_cycle,
                Bound::Arc => lb_arc,
                Bound::Residual => walk.lb_residual() as u32,
            };
            ((f64::from(len + lb) + alpha * pred) * 4096.0).round() as i64
        }
    };
    fixed as f64 / 4096.0
}

/// Replay `path` and score every state (step 0 = the start state) with
/// `scorer`; returns `(step, len, score)` triples. Step `t` here is
/// directly comparable with beam cutoff level `t` (states that have
/// taken `t` moves).
pub fn score_trajectory(g: &Graph, path: &[u32], scorer: Scorer) -> Vec<(u32, u32, f64)> {
    assert_eq!(path.first(), Some(&0), "paths must start at the identity");
    let mut walk = Walk::new(g);
    let mut out = Vec::with_capacity(path.len());
    out.push((0, walk.len_chars() as u32, score_state(&walk, scorer)));
    for &q in &path[1..] {
        let p = &g.perms[walk.cur as usize];
        let w = (g.n - Graph::overlap(p, &g.perms[q as usize])) as u8;
        walk.advance(q, w);
        out.push((
            walk.steps,
            walk.len_chars() as u32,
            score_state(&walk, scorer),
        ));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::greedy::greedy;

    #[test]
    fn extracts_known_n3_superperm() {
        let g = Graph::new(3);
        let t = trace_string(&g, "123121321").unwrap();
        assert_eq!(t.path.len(), 6);
        assert_eq!(t.input_len, 9);
        assert_eq!(t.replay_len, 9);
        assert_eq!(t.hist.iter().sum::<usize>(), 5);
    }

    #[test]
    fn rejects_garbage_and_non_identity_start() {
        let g = Graph::new(3);
        assert!(trace_string(&g, "xyz").is_err());
        assert!(trace_string(&g, "213121321").is_err());
    }

    #[test]
    fn greedy_n4_roundtrips() {
        let g = Graph::new(4);
        let r = greedy(&g);
        let t = trace_string(&g, &r.string).unwrap();
        assert_eq!(t.path, r.path);
        assert_eq!(t.input_len, 33);
        assert_eq!(t.replay_len, 33);
    }

    #[test]
    fn score_matches_bound_arithmetic() {
        let g = Graph::new(4);
        let w = Walk::new(&g);
        // len 4, lb_cycle 28 (see walk.rs tests).
        assert_eq!(score_state(&w, Scorer::Bound(Bound::Cycle)), 32.0);
        assert_eq!(score_state(&w, Scorer::Bound(Bound::Arc)), 32.0);
    }
}
