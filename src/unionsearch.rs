//! Probe R3 — exhaustive search inside the corpus edge union
//! (`docs/RECOMB-DESIGN.md` §5; the TRACKB-DESIGN §7 tour-merge).
//!
//! The union of first-visit edges used by any known record is tiny
//! (n = 6: 1,279 edges over 720 nodes, out-degree ≤ 2), so a
//! depth-first search restricted to those edges, pruned by an
//! admissible bound against a length cap, can *exhaust* the space of
//! walks assembled from record structure — including interleavings
//! through states no record visits, which the splice closure
//! ([`crate::recomb`]) cannot reach. The bound is computed over the
//! full graph, so restricting the edge set only removes options and
//! admissibility is preserved.
//!
//! Transposition mode (`--tt`) prunes a revisited (visited set,
//! current perm) state unless it arrives strictly shorter. Sound for
//! decision/optimality claims: completions cost the same from a state
//! regardless of prefix, so the surviving minimal-length visit can
//! realize a final length ≤ that of any pruned visit. NOT sound for
//! enumeration counts — equal-length walks through a shared state
//! collapse to one representative.
//!
//! The searcher keeps its own undo-based state instead of cloning
//! [`crate::walk::Walk`] per node: the cycle bound needs only
//! `(r, k, cycle_rem)` and the residual bound's `(door, long, intact)`
//! terms are advanced with the same incremental rules as
//! `Walk::advance` and restored from a trail on retreat.

use crate::bitset::BitSet;
use crate::bound::lower_bound;
use crate::corpus::CorpusRecord;
use crate::graph::Graph;
use crate::lb_residual::{self, PredTable};
use crate::state::CycleState;
use crate::validate::validate;
use std::collections::HashMap;

/// Which admissible bound prunes the DFS.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum UnionBound {
    Cycle,
    Residual,
}

/// Search configuration (`union-dfs` CLI flags).
pub struct UnionCfg {
    /// Hard length cap; walks longer than this are pruned.
    pub cap: u32,
    pub bound: UnionBound,
    /// Transposition pruning (decision/optimality mode).
    pub tt: bool,
    /// Max transposition entries; probing continues after saturation.
    pub tt_max: usize,
    /// Off-union edge credits per walk.
    pub free: u32,
    /// Max weight of an off-union edge.
    pub free_w: u8,
    /// Node budget; hitting it makes the run TRUNCATED.
    pub max_nodes: u64,
}

/// Search outcome and statistics.
pub struct UnionResult {
    /// True iff the search exhausted the space within `max_nodes`.
    pub complete: bool,
    pub nodes: u64,
    pub bound_prunes: u64,
    /// Subtrees killed because an unvisited perm lost its last live
    /// union in-neighbour (lossless; see `UnionState::live_in`).
    pub strand_prunes: u64,
    pub dead_ends: u64,
    pub tt_prunes: u64,
    pub tt_saturated: bool,
    /// Completions reaching `done()` (before string dedup).
    pub completions: u64,
    /// Distinct validated strings ≤ cap, in discovery order.
    pub finds: Vec<String>,
    /// Deepest visited-perm count reached.
    pub max_depth: usize,
}

/// Per-node union adjacency. Ordered by record usage count
/// (descending, ties by weight then rank): the DFS tries the edge most
/// records take first, which rides record-consensus paths to
/// completions orders of magnitude sooner than weight order. Ordering
/// affects discovery time only — completeness claims are order-blind.
pub fn union_adjacency(g: &Graph, corpus: &[CorpusRecord]) -> Vec<Vec<(u32, u8)>> {
    let mut counted: Vec<Vec<(u32, u8, u32)>> = vec![Vec::new(); g.nfact];
    for rec in corpus {
        let path = &rec.trace.path;
        let weights = &rec.trace.weights;
        for i in 1..path.len() {
            let p = path[i - 1] as usize;
            let (q, w) = (path[i], weights[i - 1]);
            match counted[p].iter_mut().find(|e| (e.0, e.1) == (q, w)) {
                Some(e) => e.2 += 1,
                None => counted[p].push((q, w, 1)),
            }
        }
    }
    counted
        .into_iter()
        .map(|mut list| {
            list.sort_by_key(|&(q, w, uses)| (std::cmp::Reverse(uses), w, q));
            list.into_iter().map(|(q, w, _)| (q, w)).collect()
        })
        .collect()
}

/// Undo trail entry: everything `advance` changed that `retreat`
/// cannot recompute (the residual terms are not invertible; every other
/// counter is restored by [`CycleState::unvisit`]).
struct TrailEntry {
    rank: u32,
    weight: u8,
    prev_cur: u32,
    prev_door: u32,
    prev_long: u32,
}

/// The union DFS's state: the shared per-cycle bookkeeping
/// ([`CycleState`], s64 P3 — visited set, per-cycle counts, `k`/`r`/
/// `intact` and the residual `door`/`long` terms) plus this searcher's
/// own string, undo trail and stranding detector.
struct UnionState<'g> {
    g: &'g Graph,
    cyc: CycleState,
    chars: Vec<u8>,
    tab: PredTable,
    residual: bool,
    trail: Vec<TrailEntry>,
    // Stranding detector: `live_in[q]` = number of *unvisited* union
    // in-neighbours of `q`. A perm is only ever entered from an
    // in-neighbour we stand on at that moment, and we stand on each
    // perm exactly once (first-visit walks) — so an unvisited `q` with
    // `live_in[q] == 0` that is not a union successor of the current
    // perm can never be visited in pure union mode and the subtree is
    // dead. Records never strand (they complete in-union), so the
    // prune is lossless. `strand_z` counts unvisited perms with
    // `live_in == 0`; the per-node check exempts `cur`'s own union
    // successors (reachable right now) and off-union rescues are
    // charged one free credit each.
    live_in: Vec<u32>,
    strand_z: u32,
}

impl<'g> UnionState<'g> {
    fn new(g: &'g Graph, residual: bool, adj: &[Vec<(u32, u8)>]) -> Self {
        let tab = PredTable::new(g);
        let cyc = CycleState::root(g, residual.then_some(&tab));
        // live_in from the union in-degrees, with rank 0 already visited.
        let mut live_in = vec![0u32; g.nfact];
        for (p, list) in adj.iter().enumerate() {
            if p == 0 {
                continue;
            }
            for &(q, _) in list {
                live_in[q as usize] += 1;
            }
        }
        let strand_z = (1..g.nfact).filter(|&q| live_in[q] == 0).count() as u32;
        UnionState {
            g,
            cyc,
            chars: g.perms[0].clone(),
            tab,
            residual,
            trail: Vec::with_capacity(g.nfact),
            live_in,
            strand_z,
        }
    }

    /// Unvisited perms with no live in-neighbour, minus the ones we can
    /// still enter directly from `cur`. If this exceeds the remaining
    /// free-edge credits the subtree cannot complete.
    #[inline]
    fn stranded_beyond(&self, adj: &[Vec<(u32, u8)>]) -> u32 {
        let exempt = adj[self.cyc.cur as usize]
            .iter()
            .filter(|&&(q, _)| !self.cyc.visited.get(q as usize) && self.live_in[q as usize] == 0)
            .count() as u32;
        self.strand_z - exempt
    }

    #[inline]
    fn advance(&mut self, rank: u32, weight: u8, adj: &[Vec<(u32, u8)>]) {
        let n = self.g.n;
        let w = weight as usize;
        let entry = TrailEntry {
            rank,
            weight,
            prev_cur: self.cyc.cur,
            prev_door: self.cyc.door,
            prev_long: self.cyc.long,
        };
        let tab = self.residual.then_some(&self.tab);
        self.cyc.visit(self.g, rank, u32::from(weight), tab);
        let q = &self.g.perms[rank as usize];
        self.chars.extend_from_slice(&q[n - w..]);
        // Strand bookkeeping: `rank` went unvisited → visited, so it
        // stops counting as a live in-neighbour of its union successors
        // (and stops counting as an unvisited zero itself, if it was one).
        if self.live_in[rank as usize] == 0 {
            self.strand_z -= 1;
        }
        for &(t, _) in &adj[rank as usize] {
            self.live_in[t as usize] -= 1;
            if self.live_in[t as usize] == 0 && !self.cyc.visited.get(t as usize) {
                self.strand_z += 1;
            }
        }
        self.trail.push(entry);
    }

    #[inline]
    fn retreat(&mut self, adj: &[Vec<(u32, u8)>]) {
        let e = self.trail.pop().expect("retreat without advance");
        for &(t, _) in adj[e.rank as usize].iter().rev() {
            if self.live_in[t as usize] == 0 && !self.cyc.visited.get(t as usize) {
                self.strand_z -= 1;
            }
            self.live_in[t as usize] += 1;
        }
        self.cyc.unvisit(
            self.g,
            e.rank,
            u32::from(e.weight),
            e.prev_cur,
            e.prev_door,
            e.prev_long,
        );
        if self.live_in[e.rank as usize] == 0 {
            self.strand_z += 1;
        }
        self.chars.truncate(self.chars.len() - e.weight as usize);
    }

    #[inline]
    fn lb(&self) -> usize {
        let c = &self.cyc;
        if self.residual {
            lb_residual::lower_bound_residual(
                c.r as usize,
                c.door as usize,
                c.intact as usize,
                c.long as usize,
            )
        } else {
            let cur_rem = c.cycle_rem[self.g.cycle_id[c.cur as usize] as usize];
            lower_bound(c.r as usize, c.k as usize, cur_rem > 0)
        }
    }

    fn string(&self) -> String {
        self.chars.iter().map(|&v| (b'0' + v) as char).collect()
    }
}

/// The exhaustive union DFS (RECOMB-DESIGN §5.1).
pub struct UnionSearch<'g> {
    g: &'g Graph,
    adj: Vec<Vec<(u32, u8)>>,
    cfg: UnionCfg,
}

impl<'g> UnionSearch<'g> {
    pub fn new(g: &'g Graph, corpus: &[CorpusRecord], cfg: UnionCfg) -> Self {
        UnionSearch {
            g,
            adj: union_adjacency(g, corpus),
            cfg,
        }
    }

    /// Run to completion or node budget. Deterministic: children are
    /// explored in (weight, rank) order, free edges after union edges.
    pub fn run(&self) -> UnionResult {
        let mut st = UnionState::new(self.g, self.cfg.bound == UnionBound::Residual, &self.adj);
        let mut res = UnionResult {
            complete: true,
            nodes: 0,
            bound_prunes: 0,
            strand_prunes: 0,
            dead_ends: 0,
            tt_prunes: 0,
            tt_saturated: false,
            completions: 0,
            finds: Vec::new(),
            max_depth: 1,
        };
        let mut tt: HashMap<(BitSet, u32), u32> = HashMap::new();
        let mut seen_finds: std::collections::HashSet<String> = std::collections::HashSet::new();
        let truncated = self.dfs(&mut st, self.cfg.free, &mut res, &mut tt, &mut seen_finds);
        res.complete = !truncated;
        res
    }

    /// Returns true if the node budget was hit (search truncated).
    fn dfs(
        &self,
        st: &mut UnionState,
        free_left: u32,
        res: &mut UnionResult,
        tt: &mut HashMap<(BitSet, u32), u32>,
        seen_finds: &mut std::collections::HashSet<String>,
    ) -> bool {
        if res.nodes >= self.cfg.max_nodes {
            return true;
        }
        res.nodes += 1;
        let depth = self.g.nfact - st.cyc.r as usize;
        if depth > res.max_depth {
            res.max_depth = depth;
        }
        if st.cyc.r == 0 {
            res.completions += 1;
            let s = st.string();
            let v = validate(self.g.n, &s);
            assert!(
                v.complete && v.length == st.cyc.len as usize,
                "union DFS completed an invalid string"
            );
            if seen_finds.insert(s.clone()) {
                res.finds.push(s);
            }
            return false;
        }
        let mut moved = false;
        // Union edges first, then (if credits remain) off-union edges;
        // both lists are already weight-then-rank sorted.
        for pass in 0..2 {
            if pass == 1 && free_left == 0 {
                break;
            }
            let list: &[(u32, u8)] = if pass == 0 {
                &self.adj[st.cyc.cur as usize]
            } else {
                &self.g.succs[st.cyc.cur as usize]
            };
            for &(q, w) in list {
                if pass == 1 {
                    if w > self.cfg.free_w {
                        break; // sorted by weight
                    }
                    if self.adj[st.cyc.cur as usize].contains(&(q, w)) {
                        continue; // already tried as a union edge
                    }
                }
                if st.cyc.visited.get(q as usize) {
                    continue;
                }
                moved = true;
                let free_after = free_left - u32::from(pass == 1);
                st.advance(q, w, &self.adj);
                if st.stranded_beyond(&self.adj) > free_after {
                    res.strand_prunes += 1;
                    st.retreat(&self.adj);
                    continue;
                }
                if st.cyc.len as usize + st.lb() > self.cfg.cap as usize {
                    res.bound_prunes += 1;
                    st.retreat(&self.adj);
                    continue;
                }
                if self.cfg.tt {
                    let key = (st.cyc.visited.clone(), st.cyc.cur);
                    match tt.get_mut(&key) {
                        Some(best) if *best <= st.cyc.len => {
                            res.tt_prunes += 1;
                            st.retreat(&self.adj);
                            continue;
                        }
                        Some(best) => *best = st.cyc.len,
                        None => {
                            if tt.len() < self.cfg.tt_max {
                                tt.insert(key, st.cyc.len);
                            } else {
                                res.tt_saturated = true;
                            }
                        }
                    }
                }
                let truncated = self.dfs(st, free_after, res, tt, seen_finds);
                st.retreat(&self.adj);
                if truncated {
                    return true;
                }
            }
        }
        if !moved {
            res.dead_ends += 1;
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::corpus::load_corpus;
    use crate::greedy::greedy;
    use std::io::Write;

    fn temp_corpus(tag: &str, strings: &[&str]) -> std::path::PathBuf {
        let d =
            std::env::temp_dir().join(format!("superperm-union-test-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        for (i, s) in strings.iter().enumerate() {
            let mut f = std::fs::File::create(d.join(format!("r{i}.txt"))).unwrap();
            write!(f, "{s}").unwrap();
        }
        d
    }

    fn cfg(cap: u32) -> UnionCfg {
        UnionCfg {
            cap,
            bound: UnionBound::Cycle,
            tt: false,
            tt_max: 1_000_000,
            free: 0,
            free_w: 2,
            max_nodes: 10_000_000,
        }
    }

    /// C-U0: a single-record corpus's union graph is the record itself.
    #[test]
    fn single_record_rederives_itself() {
        let g = Graph::new(5);
        let s = greedy(&g).string;
        let d = temp_corpus("cu0", &[&s]);
        let corpus = load_corpus(&g, &[&d]).unwrap();
        let adj = union_adjacency(&g, &corpus);
        assert_eq!(adj.iter().map(|l| l.len()).sum::<usize>(), 119);

        let search = UnionSearch::new(&g, &corpus, cfg(153));
        let r1 = search.run();
        assert!(r1.complete);
        assert_eq!(r1.finds, vec![s.clone()]);

        // Determinism: identical find lists on a second run.
        let r2 = UnionSearch::new(&g, &corpus, cfg(153)).run();
        assert_eq!(r1.finds, r2.finds);

        // Cap 152: complete with zero finds.
        let r3 = UnionSearch::new(&g, &corpus, cfg(152)).run();
        assert!(r3.complete);
        assert!(r3.finds.is_empty());

        // TT mode still finds a 153 (decision claim).
        let mut c = cfg(153);
        c.tt = true;
        let r4 = UnionSearch::new(&g, &corpus, c).run();
        assert!(r4.complete);
        assert_eq!(r4.finds.len(), 1);

        // Residual bound agrees.
        let mut c = cfg(153);
        c.bound = UnionBound::Residual;
        let r5 = UnionSearch::new(&g, &corpus, c).run();
        assert!(r5.complete);
        assert_eq!(r5.finds.len(), 1);

        std::fs::remove_dir_all(&d).unwrap();
    }

    /// Free-edge sanity: credits are optional, the original walk is
    /// still found, and the run terminates cleanly.
    #[test]
    fn free_edges_keep_the_original() {
        let g = Graph::new(5);
        let s = greedy(&g).string;
        let d = temp_corpus("free", &[&s]);
        let corpus = load_corpus(&g, &[&d]).unwrap();
        let mut c = cfg(153);
        c.free = 1;
        c.tt = true;
        c.max_nodes = 2_000_000;
        let r = UnionSearch::new(&g, &corpus, c).run();
        assert!(!r.finds.is_empty());
        assert!(r.finds.iter().any(|f| *f == s));
        std::fs::remove_dir_all(&d).unwrap();
    }

    /// C-U1a: n=6 single-record corpus — the union graph is the record
    /// chain, so enumeration COMPLETEs and re-derives it exactly (the
    /// full pipe at n=6: load → adjacency → DFS → validate → emit).
    #[test]
    fn n6_single_record_completes() {
        let Ok(rec) = std::fs::read_to_string("data/records872/872.0053cad.txt") else {
            eprintln!("skipping: gitignored corpus not present");
            return;
        };
        let g = Graph::new(6);
        let d = temp_corpus("n6single", &[rec.trim()]);
        let corpus = load_corpus(&g, &[&d]).unwrap();
        let mut c = cfg(872);
        c.bound = UnionBound::Residual;
        let r = UnionSearch::new(&g, &corpus, c).run();
        assert!(r.complete);
        assert_eq!(r.finds, vec![rec.trim().to_string()]);
        std::fs::remove_dir_all(&d).unwrap();
    }

    /// C-U1b: n=6 record-pair smoke — measured s26 reality: even a
    /// 2-record union does NOT exhaust in a small budget (mixed
    /// prefixes die deep; the blocked zone seen a third way). Pin the
    /// honest behavior: clean truncation, strand pruning firing, no
    /// invalid finds.
    #[test]
    fn n6_pair_truncates_cleanly() {
        let Ok(a) = std::fs::read_to_string("data/records872/872.0053cad.txt") else {
            eprintln!("skipping: gitignored corpus not present");
            return;
        };
        let b = std::fs::read_to_string("data/records872/872.008c387.txt").unwrap();
        let g = Graph::new(6);
        let d = temp_corpus("n6pair", &[a.trim(), b.trim()]);
        let corpus = load_corpus(&g, &[&d]).unwrap();
        let mut c = cfg(872);
        c.bound = UnionBound::Residual;
        c.max_nodes = 3_000_000;
        let r = UnionSearch::new(&g, &corpus, c).run();
        assert!(
            !r.complete,
            "pair enumeration unexpectedly completed — update the pins!"
        );
        assert!(r.strand_prunes > 0, "strand pruning never fired");
        assert!(r.finds.iter().all(|f| f.len() == 872));
        std::fs::remove_dir_all(&d).unwrap();
    }
}
