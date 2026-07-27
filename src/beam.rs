//! Width-limited best-first (beam) search.
//!
//! All states at a level have visited the same number `d` of
//! permutations; the search expands level by level from `d = 1` (only
//! the identity visited) to `d = n!`. Each state is scored by the
//! chosen [`Scorer`]: either `f = len + lb`, where `lb` is a selectable
//! admissible lower bound of [`crate::bound`] ([`Bound::Cycle`] or the
//! stronger [`Bound::Arc`]), or `f = len + alpha * pred`, where `pred`
//! is a learned [`Model`]'s cost-to-go estimate. Scores are stored as
//! `i64` fixed-point with 12 fractional bits, so bound scoring
//! (`(len + lb) << 12`) preserves the phase-1 ordering exactly. At
//! every level the candidate children are sorted by `(f, len)`,
//! deduplicated by `(current permutation, visited set)` keeping the
//! minimum length, and truncated to the beam width.
//!
//! Candidate scores are computed *without* materializing child states
//! (O(1) arithmetic on the parent's counters); visited bitsets and
//! per-cycle counters are cloned only for the ≤ width states that
//! survive selection. Paths are reconstructed from an arena of
//! `(parent, rank)` nodes so states never carry full paths.

use std::collections::HashSet;

use crate::bitset::BitSet;
use crate::graph::Graph;
use crate::model::Model;

/// Which admissible lower bound scores beam candidates.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Bound {
    /// Cycle bound `r + k − [current cycle has unvisited]` (phase 1).
    Cycle,
    /// Arc bound `r + arcs − [succ1(cur) unvisited]`; dominates `Cycle`
    /// (see [`crate::bound::lower_bound_arc`]).
    Arc,
}

/// How beam candidates are scored.
#[derive(Clone, Copy)]
pub enum Scorer<'m> {
    /// `f = len + lb` for an admissible lower bound (phase 1).
    Bound(Bound),
    /// `f = len + alpha * model.predict(child features)` (phase 2).
    Learned {
        /// Learned cost-to-go predictor.
        model: &'m Model,
        /// Blend factor multiplying the prediction.
        alpha: f64,
    },
}

/// One beam state: a walk that has visited `popcount(visited)` perms.
struct State {
    /// Rank of the permutation the walk currently ends with.
    cur: u32,
    /// Characters emitted so far.
    len: u32,
    /// Visited permutations.
    visited: BitSet,
    /// Per-cycle unvisited counts.
    cycle_rem: Box<[u8]>,
    /// Cycles with ≥ 1 unvisited permutation.
    k: u32,
    /// Unvisited permutations.
    r: u32,
    /// Weight-1 arcs among unvisited permutations.
    arcs: u32,
    /// Cycles with all `n` members unvisited (intact).
    intact: u32,
    /// Index of this state's node in the path arena.
    node: u32,
}

/// Result of a beam run.
pub struct BeamResult {
    /// Best complete superpermutation found, as ASCII digits.
    pub string: String,
    /// Its length in characters.
    pub len: usize,
    /// Ranks of the permutations in visit order (starts with 0).
    pub path: Vec<u32>,
}

/// Number of weight-1 arcs in the child state after `parent` visits `q`,
/// in O(1) from the parent's counters (see `Walk::advance` for the case
/// analysis; `parent.visited` does not yet contain `q`).
#[inline]
fn child_arcs(g: &Graph, parent: &State, q: u32) -> u32 {
    let cid = g.cycle_id[q as usize] as usize;
    if parent.cycle_rem[cid] as usize == g.n {
        return parent.arcs; // circular component becomes one open arc
    }
    let p_unvis = !parent.visited.get(g.pred1[q as usize] as usize);
    let s_unvis = !parent.visited.get(g.succ1(q) as usize);
    if p_unvis && s_unvis {
        parent.arcs + 1
    } else if !p_unvis && !s_unvis {
        parent.arcs - 1
    } else {
        parent.arcs
    }
}

/// Run beam search of the given `width` on `g`, scoring candidates with
/// the chosen `scorer`, and return the best complete superpermutation
/// found.
pub fn beam_search(g: &Graph, width: usize, scorer: Scorer) -> BeamResult {
    assert!(width >= 1, "beam width must be at least 1");
    let nfact = g.nfact;
    let n = g.n;

    // Arena node 0 is the root (identity permutation, no parent).
    let mut arena: Vec<(u32, u32)> = vec![(u32::MAX, 0)];

    let mut beam = {
        let mut visited = BitSet::new(nfact);
        visited.set(0);
        let mut cycle_rem = vec![n as u8; g.cycle_count].into_boxed_slice();
        cycle_rem[g.cycle_id[0] as usize] -= 1;
        vec![State {
            cur: 0,
            len: n as u32,
            visited,
            cycle_rem,
            k: g.cycle_count as u32,
            r: (nfact - 1) as u32,
            arcs: g.cycle_count as u32,
            // Rank 0's cycle is already broken by the initial visit.
            intact: (g.cycle_count - 1) as u32,
            node: 0,
        }]
    };

    // Candidate = (score, len, succ, parent index in `beam`).
    let mut cands: Vec<(i64, u32, u32, u32)> = Vec::new();

    for _depth in 1..nfact {
        cands.clear();
        for (pi, s) in beam.iter().enumerate() {
            let mut any = false;
            for &(q, w) in &g.succs[s.cur as usize] {
                if s.visited.get(q as usize) {
                    continue;
                }
                any = true;
                cands.push(score_move(g, s, q, w as u32, pi as u32, scorer));
            }
            if !any {
                // Weight-n fallback: jump to the lowest unvisited rank so
                // the state never silently dies.
                let q = s
                    .visited
                    .first_clear(nfact)
                    .expect("state with r > 0 must have an unvisited perm")
                    as u32;
                cands.push(score_move(g, s, q, n as u32, pi as u32, scorer));
            }
        }

        // Deterministic total order: (score, len, succ, parent). For
        // duplicate (cur, visited) keys the bound — and every learned
        // feature, hence the prediction — is identical (all depend only
        // on cur and visited), so the score differs only through len
        // (monotonically: +1 len is +4096 fixed-point, more than any
        // rounding) and keep-first after this sort keeps the minimum
        // length.
        cands.sort_unstable();

        let mut seen: HashSet<(u32, BitSet)> = HashSet::with_capacity(width.min(cands.len()) * 2);
        let mut next: Vec<State> = Vec::with_capacity(width.min(cands.len()));
        for &(_score, len, q, pi) in cands.iter() {
            if next.len() >= width {
                break;
            }
            let parent = &beam[pi as usize];
            let mut visited = parent.visited.clone();
            visited.set(q as usize);
            let key = (q, visited);
            if seen.contains(&key) {
                continue;
            }
            let visited = key.1.clone();
            seen.insert(key);
            let arcs = child_arcs(g, parent, q);
            let mut cycle_rem = parent.cycle_rem.clone();
            let cid = g.cycle_id[q as usize] as usize;
            let intact = parent.intact - u32::from(parent.cycle_rem[cid] as usize == n);
            cycle_rem[cid] -= 1;
            let k = parent.k - u32::from(cycle_rem[cid] == 0);
            let node = arena.len() as u32;
            arena.push((parent.node, q));
            next.push(State {
                cur: q,
                len,
                visited,
                cycle_rem,
                k,
                r: parent.r - 1,
                arcs,
                intact,
                node,
            });
        }
        beam = next;
    }

    let best = beam
        .iter()
        .min_by_key(|s| s.len)
        .expect("beam is never empty");
    debug_assert_eq!(best.r, 0);

    // Reconstruct the visit order from the arena, then rebuild the
    // string by maximal-overlap concatenation.
    let mut ranks = Vec::with_capacity(nfact);
    let mut node = best.node;
    while node != u32::MAX {
        let (parent, rank) = arena[node as usize];
        ranks.push(rank);
        node = parent;
    }
    ranks.reverse();

    let mut chars: Vec<u8> = g.perms[ranks[0] as usize].clone();
    for pair in ranks.windows(2) {
        let p = &g.perms[pair[0] as usize];
        let q = &g.perms[pair[1] as usize];
        let t = Graph::overlap(p, q);
        chars.extend_from_slice(&q[t..]);
    }
    debug_assert_eq!(chars.len(), best.len as usize);

    BeamResult {
        string: chars.iter().map(|&v| (b'0' + v) as char).collect(),
        len: chars.len(),
        path: ranks,
    }
}

/// Score the move `parent → q` with edge weight `w` without cloning the
/// parent's state, in O(1) from the parent's counters. The score is
/// `i64` fixed-point with 12 fractional bits: `(len + lb) << 12` for
/// bound scoring (exactly the phase-1 ordering), or
/// `round((len + alpha * pred) * 4096)` for a learned model, where
/// `pred` is evaluated on the child's 8 features (matching
/// [`crate::model::FEATURE_ORDER`]) computed here without materializing
/// the child.
///
/// Both bounds and all 8 learned features are pure functions of the
/// child's `(cur, visited, len)`, which the keep-first dedup in
/// `beam_search` relies on.
#[inline]
fn score_move(
    g: &Graph,
    parent: &State,
    q: u32,
    w: u32,
    parent_idx: u32,
    scorer: Scorer,
) -> (i64, u32, u32, u32) {
    let len = parent.len + w;
    let r = parent.r - 1;
    let score = match scorer {
        Scorer::Bound(bound) => {
            let lb = if r == 0 {
                0
            } else {
                match bound {
                    Bound::Cycle => {
                        let rem = parent.cycle_rem[g.cycle_id[q as usize] as usize] as u32;
                        let k = parent.k - u32::from(rem == 1);
                        r + k - u32::from(rem > 1)
                    }
                    Bound::Arc => {
                        let arcs = child_arcs(g, parent, q);
                        let succ1_unvis = !parent.visited.get(g.succ1(q) as usize);
                        r + arcs - u32::from(succ1_unvis)
                    }
                }
            };
            i64::from(len + lb) << 12
        }
        Scorer::Learned { model, alpha } => {
            let rem = parent.cycle_rem[g.cycle_id[q as usize] as usize] as u32;
            let k = parent.k - u32::from(rem == 1);
            let intact = parent.intact - u32::from(rem as usize == g.n);
            let cur_rem = rem - 1;
            let arcs = child_arcs(g, parent, q);
            let succ1_unvis = u32::from(!parent.visited.get(g.succ1(q) as usize));
            let lb_cycle = if r == 0 {
                0
            } else {
                r + k - u32::from(cur_rem > 0)
            };
            let lb_arc = if r == 0 { 0 } else { r + arcs - succ1_unvis };
            let x = [
                f64::from(r),
                f64::from(k),
                f64::from(intact),
                f64::from(cur_rem),
                f64::from(arcs),
                f64::from(succ1_unvis),
                f64::from(lb_cycle),
                f64::from(lb_arc),
            ];
            let pred = model.predict(&x);
            ((f64::from(len) + alpha * pred) * 4096.0).round() as i64
        }
    };
    (score, len, q, parent_idx)
}
