//! Probe R1 — record-pair splice closure (`docs/RECOMB-DESIGN.md` §4).
//!
//! Two records that occupy the same search state (visited set, current
//! permutation) at equal prefix length can be spliced there:
//! prefix(A) + suffix(B) is a legal walk of the same total length. The
//! *braid DAG* glues every corpus record path together at shared
//! states: node = (visited bitset, current rank), edge = one record
//! step. Depth (= popcount) strictly increases along edges, so the
//! graph is a layered DAG and every root→terminal path is a complete
//! walk of corpus length reachable by chained splices. Enumerating
//! those paths yields the splice closure of the corpus; paths whose
//! strings are not byte-identical to an input record are new hybrid
//! records for free.
//!
//! Measured shape at n = 6 (296 records, RECOMB-DESIGN §2): 172,521
//! states, 172,816 edges, a single terminal, 298 closure paths — the
//! braid barely reconverges, so enumeration is trivial and the count
//! is pinned in the integration test.

use crate::bitset::BitSet;
use crate::corpus::CorpusRecord;
use crate::graph::Graph;
use crate::validate::validate;
use crate::walk::Walk;
use std::collections::HashMap;

/// One braid-DAG edge: a record step out of a state.
struct Edge {
    /// Target node index.
    to: u32,
    /// Rank visited by the step.
    rank: u32,
    /// Edge weight (characters appended).
    weight: u8,
    /// Records using this edge, as (record index, step index) — the
    /// step is unique per record because a record meets a state at
    /// exactly one depth.
    used_by: Vec<(u16, u32)>,
}

/// One braid-DAG node (a search state some record passes through).
struct Node {
    succs: Vec<Edge>,
    indeg: u32,
    /// Visited-perm count (DAG layer), for junction histograms.
    depth: u32,
}

/// A maximal single-record run of a hybrid path.
pub struct Segment {
    /// Corpus record the run follows.
    pub record: String,
    /// First edge of the run, as that record's step index (0-based).
    pub step_lo: u32,
    /// Last edge of the run, inclusive.
    pub step_hi: u32,
}

/// A closure walk not byte-identical to any input record.
pub struct Hybrid {
    pub string: String,
    pub len: usize,
    pub segments: Vec<Segment>,
}

/// Everything the `recomb` CLI reports (RECOMB-DESIGN §4).
pub struct BraidResult {
    pub records: usize,
    pub states: usize,
    pub edges: usize,
    pub terminals: usize,
    /// States with ≥ 2 distinct out-edges.
    pub out_junctions: usize,
    /// States with ≥ 2 in-edges.
    pub in_junctions: usize,
    /// Root→terminal path count (the splice-closure size).
    pub path_count: u128,
    /// Out-junction count per 100-perm depth band.
    pub junction_depth_hist: Vec<usize>,
    /// Closure walks that are new relative to the corpus. Empty if the
    /// path count exceeded the enumeration limit.
    pub hybrids: Vec<Hybrid>,
    /// Whether enumeration ran (path_count ≤ max_walks).
    pub enumerated: bool,
}

/// Braid DAG over a loaded corpus.
pub struct Braid<'g> {
    g: &'g Graph,
    nodes: Vec<Node>,
    root: u32,
    rec_names: Vec<String>,
}

impl<'g> Braid<'g> {
    /// Glue the corpus record paths into the braid DAG.
    pub fn build(g: &'g Graph, corpus: &[CorpusRecord]) -> Braid<'g> {
        assert!(corpus.len() <= u16::MAX as usize, "record index is u16");
        let mut key_to_node: HashMap<(BitSet, u32), u32> = HashMap::new();
        let mut nodes: Vec<Node> = Vec::new();
        let mut intern = |mask: &BitSet, cur: u32, nodes: &mut Vec<Node>| -> u32 {
            *key_to_node.entry((mask.clone(), cur)).or_insert_with(|| {
                nodes.push(Node {
                    succs: Vec::new(),
                    indeg: 0,
                    depth: mask.popcount(),
                });
                (nodes.len() - 1) as u32
            })
        };
        let mut root = u32::MAX;
        for (ri, rec) in corpus.iter().enumerate() {
            let path = &rec.trace.path;
            let weights = &rec.trace.weights;
            let mut mask = BitSet::new(g.nfact);
            mask.set(path[0] as usize);
            let mut at = intern(&mask, path[0], &mut nodes);
            if root == u32::MAX {
                root = at;
            }
            debug_assert_eq!(at, root, "all records start at the identity state");
            for (i, &q) in path.iter().enumerate().skip(1) {
                mask.set(q as usize);
                let next = intern(&mask, q, &mut nodes);
                let pos = nodes[at as usize].succs.iter().position(|e| e.to == next);
                match pos {
                    Some(p) => nodes[at as usize].succs[p]
                        .used_by
                        .push((ri as u16, (i - 1) as u32)),
                    None => {
                        nodes[at as usize].succs.push(Edge {
                            to: next,
                            rank: q,
                            weight: weights[i - 1],
                            used_by: vec![(ri as u16, (i - 1) as u32)],
                        });
                        nodes[next as usize].indeg += 1;
                    }
                }
                at = next;
            }
        }
        // Deterministic child order regardless of record load order.
        for node in &mut nodes {
            node.succs.sort_by_key(|e| e.rank);
        }
        let rec_names = corpus.iter().map(|r| r.name.clone()).collect();
        Braid {
            g,
            nodes,
            root,
            rec_names,
        }
    }

    /// Memoized root→terminal path count. Errors on u128 overflow —
    /// the count is a pin, not a big-number exercise.
    fn count_paths(&self) -> Result<u128, String> {
        let mut memo: Vec<Option<u128>> = vec![None; self.nodes.len()];
        // Iterative post-order (the DAG is ~n! deep; recursion would
        // not overflow at n = 6 but the stack discipline is free).
        let mut stack = vec![(self.root, false)];
        while let Some((v, expanded)) = stack.pop() {
            if memo[v as usize].is_some() {
                continue;
            }
            let node = &self.nodes[v as usize];
            if node.succs.is_empty() {
                memo[v as usize] = Some(1);
                continue;
            }
            if expanded {
                let mut total: u128 = 0;
                for e in &node.succs {
                    let c = memo[e.to as usize].expect("post-order");
                    total = total
                        .checked_add(c)
                        .ok_or("path count overflows u128 — braid unexpectedly dense")?;
                }
                memo[v as usize] = Some(total);
            } else {
                stack.push((v, true));
                for e in &node.succs {
                    stack.push((e.to, false));
                }
            }
        }
        Ok(memo[self.root as usize].expect("root counted"))
    }

    /// Enumerate every root→terminal path, replay it into a string,
    /// validate, and keep the ones not in `known` (byte-identity).
    fn enumerate_hybrids(&self, known: &std::collections::HashSet<&str>) -> Vec<Hybrid> {
        let mut hybrids = Vec::new();
        // DFS with an explicit stack of (node, next child index).
        let mut frames: Vec<(u32, usize)> = vec![(self.root, 0)];
        let mut edge_path: Vec<&Edge> = Vec::new();
        while let Some(&(v, ci)) = frames.last() {
            let node = &self.nodes[v as usize];
            if node.succs.is_empty() {
                if let Some(h) = self.materialize(&edge_path, known) {
                    hybrids.push(h);
                }
                frames.pop();
                edge_path.pop();
            } else if ci < node.succs.len() {
                frames.last_mut().expect("nonempty").1 += 1;
                let e = &node.succs[ci];
                frames.push((e.to, 0));
                edge_path.push(e);
            } else {
                frames.pop();
                edge_path.pop();
            }
        }
        hybrids
    }

    /// Replay one edge path into a walk; return it as a hybrid if it
    /// is a valid superpermutation not already in the corpus.
    fn materialize(
        &self,
        edge_path: &[&Edge],
        known: &std::collections::HashSet<&str>,
    ) -> Option<Hybrid> {
        let mut walk = Walk::new(self.g);
        for e in edge_path {
            walk.advance(e.rank, e.weight);
        }
        assert!(walk.done(), "terminal braid state must complete the walk");
        let s = walk.string();
        let v = validate(self.g.n, &s);
        assert!(
            v.complete && v.length == walk.len_chars(),
            "braid replay produced an invalid string"
        );
        if known.contains(s.as_str()) {
            return None;
        }
        Some(Hybrid {
            len: s.len(),
            segments: self.segments_of(edge_path),
            string: s,
        })
    }

    /// Greedy maximal-run provenance: attribute each run of consecutive
    /// edges to records that take exactly those steps consecutively;
    /// close a segment when the candidate set empties. Consecutive
    /// edges shared with a record are consecutive steps of that record
    /// (states are unique per record path), asserted cheaply below.
    fn segments_of(&self, edge_path: &[&Edge]) -> Vec<Segment> {
        let mut segments = Vec::new();
        // Candidate records for the current run, with the step at which
        // each entered the run.
        let mut run: Vec<(u16, u32, u32)> = Vec::new(); // (rec, step_lo, step_cur)
        for e in edge_path {
            let mut next_run: Vec<(u16, u32, u32)> = Vec::new();
            for &(r, s) in &e.used_by {
                if let Some(&(_, lo, cur)) = run.iter().find(|&&(pr, _, _)| pr == r) {
                    debug_assert_eq!(
                        s,
                        cur + 1,
                        "record steps along a braid path are consecutive"
                    );
                    next_run.push((r, lo, s));
                }
            }
            if next_run.is_empty() {
                if let Some(&(r, lo, hi)) = run.iter().min_by_key(|&&(pr, _, _)| pr) {
                    segments.push(Segment {
                        record: self.rec_names[r as usize].clone(),
                        step_lo: lo,
                        step_hi: hi,
                    });
                }
                next_run = e.used_by.iter().map(|&(r, s)| (r, s, s)).collect();
            }
            run = next_run;
        }
        if let Some(&(r, lo, hi)) = run.iter().min_by_key(|&&(pr, _, _)| pr) {
            segments.push(Segment {
                record: self.rec_names[r as usize].clone(),
                step_lo: lo,
                step_hi: hi,
            });
        }
        segments
    }

    /// Run the full probe: stats, path count, and (if the closure is
    /// small enough) hybrid enumeration.
    pub fn probe(&self, corpus: &[CorpusRecord], max_walks: u128) -> Result<BraidResult, String> {
        let path_count = self.count_paths()?;
        let terminals = self.nodes.iter().filter(|n| n.succs.is_empty()).count();
        let out_junctions = self.nodes.iter().filter(|n| n.succs.len() >= 2).count();
        let in_junctions = self.nodes.iter().filter(|n| n.indeg >= 2).count();
        let bands = self.g.nfact / 100 + 1;
        let mut junction_depth_hist = vec![0usize; bands];
        for n in &self.nodes {
            if n.succs.len() >= 2 {
                junction_depth_hist[n.depth as usize / 100] += 1;
            }
        }
        let edges = self.nodes.iter().map(|n| n.succs.len()).sum();
        let (hybrids, enumerated) = if path_count <= max_walks {
            let known: std::collections::HashSet<&str> =
                corpus.iter().map(|r| r.string.as_str()).collect();
            (self.enumerate_hybrids(&known), true)
        } else {
            (Vec::new(), false)
        };
        Ok(BraidResult {
            records: corpus.len(),
            states: self.nodes.len(),
            edges,
            terminals,
            out_junctions,
            in_junctions,
            path_count,
            junction_depth_hist,
            hybrids,
            enumerated,
        })
    }
}

/// Stable FNV-1a 64 over the string bytes; used for emitted file names.
pub fn fnv1a64(s: &str) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for &b in s.as_bytes() {
        h ^= b as u64;
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
    }
    h
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::corpus::load_corpus;
    use crate::greedy::greedy;
    use std::io::Write;
    use std::path::Path;

    fn temp_corpus(tag: &str, strings: &[&str]) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!(
            "superperm-recomb-test-{tag}-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        for (i, s) in strings.iter().enumerate() {
            let mut f = std::fs::File::create(d.join(format!("r{i}.txt"))).unwrap();
            write!(f, "{s}").unwrap();
        }
        d
    }

    #[test]
    fn single_record_is_a_chain() {
        let g = Graph::new(5);
        let s = greedy(&g).string;
        let d = temp_corpus("chain", &[&s]);
        let corpus = load_corpus(&g, &[&d]).unwrap();
        let braid = Braid::build(&g, &corpus);
        let r = braid.probe(&corpus, 100_000).unwrap();
        assert_eq!(r.states, 120);
        assert_eq!(r.edges, 119);
        assert_eq!(r.terminals, 1);
        assert_eq!(r.out_junctions, 0);
        assert_eq!(r.in_junctions, 0);
        assert_eq!(r.path_count, 1);
        assert!(r.enumerated);
        assert!(r.hybrids.is_empty());
        std::fs::remove_dir_all(&d).unwrap();
    }

    /// Full-corpus integration pin (RECOMB-DESIGN §4); the numbers were
    /// measured independently in Python
    /// (`analysis/trackb/recomb_feasibility.py`).
    #[test]
    fn n6_braid_pins() {
        if !Path::new("data/records872").exists() {
            eprintln!("skipping: gitignored corpus not present");
            return;
        }
        let g = Graph::new(6);
        let corpus = load_corpus(
            &g,
            &[Path::new("data/records872"), Path::new("data/gain1_872s")],
        )
        .unwrap();
        let braid = Braid::build(&g, &corpus);
        let r = braid.probe(&corpus, 100_000).unwrap();
        assert_eq!(r.records, 296);
        assert_eq!(r.states, 172_521);
        assert_eq!(r.edges, 172_816);
        assert_eq!(r.terminals, 1);
        assert_eq!(r.path_count, 298);
        assert!(r.enumerated);
        assert_eq!(r.hybrids.len(), 2);
        for h in &r.hybrids {
            assert_eq!(h.len, 872);
            assert!(h.segments.len() >= 2, "a hybrid crosses records");
        }
    }
}
