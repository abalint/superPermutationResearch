//! Clean-room verifier for the n = 6 "gain-one kernel-chain" certificate.
//!
//! This module re-derives, from the mathematical definitions alone, the
//! combinatorial objects behind the claim that 872 is optimal within the
//! gain-one certificate grammar at n = 6. It deliberately shares no code
//! or data with the original analysis pipeline, so agreement between the
//! two implementations is independent evidence rather than a tautology.
//! The only reused infrastructure is [`Graph`], whose rotation cycles are
//! definitionally the orbits used here (`door(·, 1)` is the left
//! rotation).
//!
//! Objects (n = 6 throughout; symbols `1..=6`; words are length-6
//! permutations):
//!
//! * **door** — `door(w, c) = w[c..] ++ reverse(w[..c])`, `1 ≤ c ≤ 6`.
//!   Orbits under repeated `door(·, 1)` are the 120 rotation cycles.
//! * **marked loop** `m(a; C)` — a pivot symbol `a` plus a cyclic
//!   necklace `C` (up to rotation, not reflection) of the other five
//!   symbols; `6 · 4! = 144` loops. Entries: `e_0 = C_lin ++ [a]` for the
//!   canonical linearization of `C` (smallest symbol first), then
//!   `e_{i+1} = tv(e_i)` where [`tv`] rotates the first five symbols left
//!   and fixes the pivot; `tv` has period 5 and the five entries lie in
//!   five distinct orbits (the loop's orbit set — `a` inserted into the
//!   five gaps of `C`).
//! * **splice / hop** — splice source `s_i = rotate-right(e_i)`; the
//!   identity `door(s_i, 2) = e_{i+1}` is asserted at construction (it
//!   pins the `tv`/splice conventions). A hop of cost `c ∈ 3..=6` from
//!   splice `j` is the word `h = door(s_j, c)`; hops preserve the pivot
//!   (last symbol), so they stay inside one pivot class, and because each
//!   orbit contains exactly one word ending in `a`, a hop automatically
//!   lands on an *entry* of the loop owning its orbit ([`Cert::audit_hops`]
//!   verifies both facts exhaustively).
//! * **chain / ledger** — pairwise orbit-disjoint loops joined by hops,
//!   the first loop containing the identity's orbit (arrival entry = the
//!   entry that is a rotation of `123456`). A loop arrived at entry `k`
//!   and exited at splice `j` rides `(j − k) mod 5` tv-steps and skips
//!   `4 − ((j − k) mod 5)` entries; the last loop skips 0. The ledger
//!   value is `V = K − Σskip − 4·f4 − 8·f5 − 12·f6`.
//! * **rows / cover** — the ridden kernel orbits are *roots*; an oriented
//!   row is a non-chain loop with a designated parent orbit whose other
//!   four orbits ("children") are all non-root; a cover is a set of rows
//!   whose children partition the non-root orbits exactly and whose
//!   ownership digraph is *rooted* (every row's parent chain terminates
//!   at a root orbit).
//!
//! Public surface: a [`Cert`] context plus one routine per claim —
//! [`Cert::audit_hops`] (C2), [`Cert::forced_audit`] (C1),
//! [`Cert::search_class`] (C3, exhaustive branch-and-bound),
//! [`Cert::cover_search`] (C4, exact cover with rootedness), and
//! [`Cert::standard_kernel`] + [`waste_and_length`] (positive control and
//! C5 arithmetic). The `cert-verify` CLI subcommand runs everything and
//! prints a verdict table.

use std::collections::BTreeMap;

use crate::graph::{rank, Graph};

/// Word length and symbol count (this certificate is n = 6 only).
pub const W: usize = 6;
/// Number of rotation orbits (`5! = 120`).
pub const ORBITS: usize = 120;
/// Entries (and splices) per marked loop.
pub const ENTRIES: usize = 5;
/// Number of marked loops (`6 · 4! = 144`).
pub const LOOPS: usize = 144;
/// Marked loops per pivot class (`4! = 24`).
pub const CLASS_LOOPS: usize = 24;

/// A length-6 word (permutation of `1..=6` as `u8`).
pub type Word = [u8; W];

/// `door(w, c) = w[c..] ++ reverse(w[..c])` for `1 ≤ c ≤ 6`.
pub fn door(w: Word, c: usize) -> Word {
    assert!((1..=W).contains(&c), "door cost out of range");
    let mut out = [0u8; W];
    out[..W - c].copy_from_slice(&w[c..]);
    for (slot, &x) in out[W - c..].iter_mut().zip(w[..c].iter().rev()) {
        *slot = x;
    }
    out
}

/// `tv(w)`: rotate the first five symbols left by one, keep the last
/// (pivot) symbol fixed.
pub fn tv(w: Word) -> Word {
    [w[1], w[2], w[3], w[4], w[0], w[5]]
}

/// Splice source `s_i = [e_i[5]] ++ e_i[0..5]` (right rotation of the
/// entry, so the pivot moves to the front).
pub fn splice_source(e: Word) -> Word {
    [e[5], e[0], e[1], e[2], e[3], e[4]]
}

/// All arrangements of `items` (Heap's algorithm; deterministic order).
fn arrangements(items: &[u8]) -> Vec<Vec<u8>> {
    fn rec(a: &mut Vec<u8>, k: usize, out: &mut Vec<Vec<u8>>) {
        if k <= 1 {
            out.push(a.clone());
            return;
        }
        for i in 0..k {
            rec(a, k - 1, out);
            if k.is_multiple_of(2) {
                a.swap(i, k - 1);
            } else {
                a.swap(0, k - 1);
            }
        }
    }
    let mut a = items.to_vec();
    let mut out = Vec::new();
    let len = a.len();
    rec(&mut a, len, &mut out);
    out
}

/// A marked loop `m(a; C)`: pivot, its five entries in tv-order, and
/// their orbit ids.
pub struct MarkedLoop {
    /// Pivot symbol `a` (every entry ends with it).
    pub pivot: u8,
    /// The five entries `e_0, …, e_4` with `e_{i+1} = tv(e_i)`.
    pub entries: [Word; ENTRIES],
    /// Orbit id of each entry (five distinct values).
    pub orbits: [usize; ENTRIES],
}

/// A chain: loops joined by hops, as chosen by the search. `loops[i]` is
/// arrived at entry `arrivals[i]`; for `i < K − 1` it is exited by
/// `hops[i] = (splice j, cost c)`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Chain {
    /// Global loop ids, in visit order (`K = loops.len()`).
    pub loops: Vec<usize>,
    /// Arrival entry index of each loop (`arrivals[0]` = the identity
    /// entry of the first loop).
    pub arrivals: Vec<usize>,
    /// `(exit splice, hop cost)` per hop; `hops.len() = K − 1`.
    pub hops: Vec<(usize, usize)>,
}

/// Ledger statistics of a chain (recomputed from first principles, used
/// to cross-check the search's incremental accounting).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ChainStats {
    /// Number of loops `K`.
    pub k: usize,
    /// Total skip `Σ` (the last loop contributes 0).
    pub sigma: i64,
    /// Number of cost-4 hops.
    pub f4: usize,
    /// Number of cost-5 hops.
    pub f5: usize,
    /// Number of cost-6 hops.
    pub f6: usize,
    /// Ledger value `V = K − Σ − 4·f4 − 8·f5 − 12·f6`.
    pub v: i64,
}

impl Chain {
    /// Recompute the ledger from the chain's raw moves.
    pub fn stats(&self) -> ChainStats {
        let k = self.loops.len();
        let mut sigma = 0i64;
        let (mut f4, mut f5, mut f6) = (0usize, 0usize, 0usize);
        for (i, &(j, c)) in self.hops.iter().enumerate() {
            let ride = (j + ENTRIES - self.arrivals[i]) % ENTRIES;
            sigma += 4 - ride as i64;
            match c {
                4 => f4 += 1,
                5 => f5 += 1,
                6 => f6 += 1,
                _ => {}
            }
        }
        let v = k as i64 - sigma - 4 * f4 as i64 - 8 * f5 as i64 - 12 * f6 as i64;
        ChainStats {
            k,
            sigma,
            f4,
            f5,
            f6,
            v,
        }
    }
}

/// Exhaustive sweep of all `144 · 5 · 4` hop words (C2 and the C1
/// uniqueness question).
#[derive(Clone, Copy, Debug)]
pub struct HopAudit {
    /// `(loop, splice)` pairs per cost (= 720).
    pub pairs: usize,
    /// Hop words whose last symbol is not the pivot (claimed 0).
    pub pivot_violations: usize,
    /// Hop words lying in an orbit of loop `M` without equaling `M`'s
    /// entry there (claimed 0 — landing-on-entry is automatic).
    pub non_entry_landings: usize,
    /// Per cost `c = 3..=6` (index `c − 3`): `(loop, splice)` pairs whose
    /// hop word lands on a loop `M ≠ L` (a valid hop target).
    pub valid_by_cost: [usize; 4],
    /// Per cost: pairs whose hop word falls back on `L` itself.
    pub self_by_cost: [usize; 4],
}

/// C1 result: the forced map on `(loop, entry)` states.
#[derive(Clone, Debug)]
pub struct ForcedAudit {
    /// Number of states (`144 · 5 = 720`).
    pub states: usize,
    /// Every state has a valid forced successor (cost-3 hop from splice
    /// `(k − 1) mod 5` lands on a different loop).
    pub total_map: bool,
    /// The forced map is injective (hence a permutation when total).
    pub is_permutation: bool,
    /// Cycle length → number of cycles.
    pub cycle_lengths: BTreeMap<usize, usize>,
}

/// C3 result for one pivot class.
pub struct ClassSearch {
    /// The pivot symbol.
    pub pivot: u8,
    /// Maximum ledger value over all chains in the class.
    pub max_v: i64,
    /// Every chain achieving `max_v` (distinct move sequences).
    pub chains: Vec<Chain>,
    /// DFS nodes visited (each node is one valid partial chain).
    pub nodes: u64,
}

/// C4 result for one chain's cover search.
#[derive(Clone, Copy, Debug)]
pub struct CoverReport {
    /// Root (ridden) orbits, `5K − Σ`.
    pub roots: usize,
    /// Non-root orbits (the cover's universe).
    pub non_root: usize,
    /// Eligible oriented rows.
    pub rows: usize,
    /// Exact covers found (children partition the non-root orbits).
    pub exact_covers: u64,
    /// Exact covers that are also rooted.
    pub rooted_covers: u64,
}

/// Ledger arithmetic (C5): `waste = 148 − V/4`, realized length
/// `725 + waste`.
pub fn waste_and_length(v: i64) -> (i64, i64) {
    let waste = 148 - v / 4;
    (waste, 725 + waste)
}

/// The verification context: all 144 marked loops plus the orbit → (loop,
/// entry) index per pivot class. Construction asserts the internal gates
/// (tv period 5, entry-orbit distinctness, per-class orbit partition, and
/// the splice identity `door(s_i, 2) = e_{i+1}`).
pub struct Cert {
    g: Graph,
    /// The 144 loops; pivot class `a` occupies `(a−1)·24 .. a·24`.
    pub loops: Vec<MarkedLoop>,
    /// `orbit_entry[a−1][orbit] = (global loop id, entry index)` — the
    /// unique loop of pivot class `a` owning `orbit`, with the entry.
    orbit_entry: [[(usize, usize); ORBITS]; W],
    /// Orbit of the identity permutation `123456`.
    pub identity_orbit: usize,
}

impl Default for Cert {
    fn default() -> Self {
        Self::new()
    }
}

impl Cert {
    /// Build (and gate-check) the full context.
    pub fn new() -> Cert {
        let g = Graph::new(W);
        let mut loops = Vec::with_capacity(LOOPS);
        let mut orbit_entry = [[(usize::MAX, usize::MAX); ORBITS]; W];
        for pivot in 1..=W as u8 {
            let others: Vec<u8> = (1..=W as u8).filter(|&x| x != pivot).collect();
            // Canonical necklace linearization: smallest non-pivot symbol
            // first — one linearization per necklace, 4! necklaces.
            for tail in arrangements(&others[1..]) {
                let mut e0 = [0u8; W];
                e0[0] = others[0];
                e0[1..ENTRIES].copy_from_slice(&tail);
                e0[ENTRIES] = pivot;
                let mut entries = [e0; ENTRIES];
                for i in 1..ENTRIES {
                    entries[i] = tv(entries[i - 1]);
                }
                assert_eq!(tv(entries[ENTRIES - 1]), e0, "tv must have period 5");
                let id = loops.len();
                let mut orbits = [0usize; ENTRIES];
                for (i, e) in entries.iter().enumerate() {
                    let o = g.cycle_id[rank(e)] as usize;
                    orbits[i] = o;
                    let slot = &mut orbit_entry[pivot as usize - 1][o];
                    assert_eq!(
                        slot.0,
                        usize::MAX,
                        "orbit {o} claimed twice within pivot class {pivot}"
                    );
                    *slot = (id, i);
                }
                loops.push(MarkedLoop {
                    pivot,
                    entries,
                    orbits,
                });
            }
        }
        assert_eq!(loops.len(), LOOPS);
        for class in &orbit_entry {
            for &(l, _) in class.iter() {
                assert_ne!(l, usize::MAX, "a pivot class fails to cover every orbit");
            }
        }
        // Splice-convention gate: door(s_i, 2) = e_{i+1} for every entry.
        for lp in &loops {
            for i in 0..ENTRIES {
                assert_eq!(
                    door(splice_source(lp.entries[i]), 2),
                    lp.entries[(i + 1) % ENTRIES],
                    "splice identity door(s, 2) = next entry violated"
                );
            }
        }
        let identity_orbit = g.cycle_id[0] as usize; // rank 0 = 123456
        Cert {
            g,
            loops,
            orbit_entry,
            identity_orbit,
        }
    }

    /// The hop word `door(s_j, c)` from splice `j` of loop `l`, together
    /// with the loop of `l`'s pivot class owning its orbit and the entry
    /// index there.
    pub fn hop_word(&self, l: usize, j: usize, c: usize) -> (Word, usize, usize) {
        let lp = &self.loops[l];
        let h = door(splice_source(lp.entries[j]), c);
        let o = self.g.cycle_id[rank(&h)] as usize;
        let (m, k) = self.orbit_entry[lp.pivot as usize - 1][o];
        (h, m, k)
    }

    /// Valid hop target `(loop M, arrival entry k)`, or `None` when the
    /// hop word stays on `l`'s own orbit set (no self-hops in a chain).
    pub fn hop(&self, l: usize, j: usize, c: usize) -> Option<(usize, usize)> {
        let (h, m, k) = self.hop_word(l, j, c);
        if m == l {
            return None;
        }
        debug_assert_eq!(self.loops[m].entries[k], h, "hop landed off-entry");
        Some((m, k))
    }

    /// Sweep every `(loop, splice, cost)` hop word: pivot preservation,
    /// landing-on-entry, and valid-target counts per cost (C2, and the
    /// C1 uniqueness premise).
    pub fn audit_hops(&self) -> HopAudit {
        let mut audit = HopAudit {
            pairs: LOOPS * ENTRIES,
            pivot_violations: 0,
            non_entry_landings: 0,
            valid_by_cost: [0; 4],
            self_by_cost: [0; 4],
        };
        for l in 0..LOOPS {
            for j in 0..ENTRIES {
                for c in 3..=W {
                    let (h, m, k) = self.hop_word(l, j, c);
                    if h[W - 1] != self.loops[l].pivot {
                        audit.pivot_violations += 1;
                    }
                    if self.loops[m].entries[k] != h {
                        audit.non_entry_landings += 1;
                    }
                    if m == l {
                        audit.self_by_cost[c - 3] += 1;
                    } else {
                        audit.valid_by_cost[c - 3] += 1;
                    }
                }
            }
        }
        audit
    }

    /// C1: the forced map on `(loop, entry)` states — exit at splice
    /// `j = (k − 1) mod 5` (skip 0) with a cost-3 hop — and its cycle
    /// structure.
    pub fn forced_audit(&self) -> ForcedAudit {
        let states = LOOPS * ENTRIES;
        let mut img = vec![usize::MAX; states];
        let mut total_map = true;
        for l in 0..LOOPS {
            for k in 0..ENTRIES {
                let j = (k + ENTRIES - 1) % ENTRIES;
                match self.hop(l, j, 3) {
                    Some((m, k2)) => img[l * ENTRIES + k] = m * ENTRIES + k2,
                    None => total_map = false,
                }
            }
        }
        let mut hit = vec![false; states];
        let mut is_permutation = total_map;
        for &t in &img {
            if t != usize::MAX {
                if hit[t] {
                    is_permutation = false;
                }
                hit[t] = true;
            }
        }
        let mut cycle_lengths = BTreeMap::new();
        if is_permutation {
            let mut visited = vec![false; states];
            for s in 0..states {
                if visited[s] {
                    continue;
                }
                let mut len = 0usize;
                let mut cur = s;
                while !visited[cur] {
                    visited[cur] = true;
                    len += 1;
                    cur = img[cur];
                }
                *cycle_lengths.entry(len).or_insert(0) += 1;
            }
        }
        ForcedAudit {
            states,
            total_map,
            is_permutation,
            cycle_lengths,
        }
    }

    /// The standard kernel for `pivot`: the forced orbit of the identity
    /// state as a `K = 4` chain (three skip-0 cost-3 hops, last loop
    /// open). A fourth forced hop returning to the start state is
    /// debug-asserted (period 4).
    pub fn standard_kernel(&self, pivot: u8) -> Chain {
        let (l0, k0) = self.orbit_entry[pivot as usize - 1][self.identity_orbit];
        let mut loops = vec![l0];
        let mut arrivals = vec![k0];
        let mut hops = Vec::new();
        let (mut l, mut k) = (l0, k0);
        for _ in 0..3 {
            let j = (k + ENTRIES - 1) % ENTRIES;
            let (m, k2) = self.hop(l, j, 3).expect("forced hop must be valid");
            hops.push((j, 3));
            loops.push(m);
            arrivals.push(k2);
            (l, k) = (m, k2);
        }
        let j = (k + ENTRIES - 1) % ENTRIES;
        debug_assert_eq!(
            self.hop(l, j, 3),
            Some((l0, k0)),
            "forced map must return to the start after 4 steps"
        );
        Chain {
            loops,
            arrivals,
            hops,
        }
    }

    /// C3: exhaustive branch-and-bound over all identity-started chains
    /// in one pivot class. Every partial chain is itself a chain and is
    /// visited exactly once (moves are enumerated over distinct
    /// `(splice, cost)` pairs, and distinct splices give distinct hop
    /// words at fixed cost since entries lie in distinct orbits), so the
    /// returned `chains` are exactly the distinct
    /// loop-sequences-with-hops achieving `max_v`. Termination: each
    /// recursion adds one unused loop of the 24-loop class, so depth
    /// ≤ 24 and branching ≤ 20. Soundness of the prune: extending by one
    /// loop changes `V` by `1 − skip − 4(c−3) ≤ 1`, so a state with
    /// value `v` and `rem` unused loops can reach at most `v + rem`.
    pub fn search_class(&self, pivot: u8) -> ClassSearch {
        struct Dfs<'a> {
            cert: &'a Cert,
            base: usize,
            best: i64,
            chains: Vec<Chain>,
            nodes: u64,
            loops: Vec<usize>,
            arrivals: Vec<usize>,
            hops: Vec<(usize, usize)>,
        }
        impl Dfs<'_> {
            fn go(&mut self, used: u32, last: usize, k: usize, v: i64) {
                self.nodes += 1;
                if v > self.best {
                    self.best = v;
                    self.chains.clear();
                }
                if v == self.best {
                    let chain = Chain {
                        loops: self.loops.clone(),
                        arrivals: self.arrivals.clone(),
                        hops: self.hops.clone(),
                    };
                    debug_assert_eq!(chain.stats().v, v, "incremental ledger drifted");
                    self.chains.push(chain);
                }
                let rem = CLASS_LOOPS as i64 - i64::from(used.count_ones());
                for j in 0..ENTRIES {
                    let skip = (4 - (j + ENTRIES - k) % ENTRIES) as i64;
                    for c in 3..=W {
                        let dv = 1 - skip - 4 * (c as i64 - 3);
                        if v + dv + rem - 1 < self.best {
                            continue;
                        }
                        let Some((m, k2)) = self.cert.hop(last, j, c) else {
                            continue;
                        };
                        let bit = 1u32 << (m - self.base);
                        if used & bit != 0 {
                            continue;
                        }
                        self.loops.push(m);
                        self.arrivals.push(k2);
                        self.hops.push((j, c));
                        self.go(used | bit, m, k2, v + dv);
                        self.loops.pop();
                        self.arrivals.pop();
                        self.hops.pop();
                    }
                }
            }
        }
        let base = (pivot as usize - 1) * CLASS_LOOPS;
        let (l0, k0) = self.orbit_entry[pivot as usize - 1][self.identity_orbit];
        let mut dfs = Dfs {
            cert: self,
            base,
            best: i64::MIN,
            chains: Vec::new(),
            nodes: 0,
            loops: vec![l0],
            arrivals: vec![k0],
            hops: Vec::new(),
        };
        dfs.go(1u32 << (l0 - base), l0, k0, 1);
        ClassSearch {
            pivot,
            max_v: dfs.best,
            chains: dfs.chains,
            nodes: dfs.nodes,
        }
    }

    /// Bitmask (over the 120 orbits) of a chain's *root* orbits: the
    /// ridden entries `k, k+1, …, j` of each loop (all five for the last
    /// loop, which skips nothing).
    pub fn root_mask(&self, chain: &Chain) -> u128 {
        let kn = chain.loops.len();
        let mut mask = 0u128;
        for i in 0..kn {
            let k = chain.arrivals[i];
            let ride_len = if i + 1 < kn {
                (chain.hops[i].0 + ENTRIES - k) % ENTRIES + 1
            } else {
                ENTRIES
            };
            for t in 0..ride_len {
                mask |= 1u128 << self.loops[chain.loops[i]].orbits[(k + t) % ENTRIES];
            }
        }
        mask
    }

    /// C4: exhaustive exact-cover search over the chain's eligible
    /// oriented rows, counting covers and *rooted* covers. With
    /// `stop_at_first_rooted` the search unwinds as soon as one rooted
    /// cover is found (the positive control only needs existence).
    pub fn cover_search(&self, chain: &Chain, stop_at_first_rooted: bool) -> CoverReport {
        let root_mask = self.root_mask(chain);
        let roots = root_mask.count_ones() as usize;
        // Universe = the non-root orbits, indexed densely.
        let mut uidx = [usize::MAX; ORBITS];
        let mut universe = Vec::new();
        for (o, slot) in uidx.iter_mut().enumerate() {
            if root_mask >> o & 1 == 0 {
                *slot = universe.len();
                universe.push(o);
            }
        }
        let mut in_chain = [false; LOOPS];
        for &l in &chain.loops {
            in_chain[l] = true;
        }
        // Eligible rows: a non-chain loop X and a parent orbit p such
        // that X's other four orbits are all non-root.
        struct Row {
            parent: usize,
            children: [usize; 4],
            umask: u128,
        }
        let mut rows = Vec::new();
        for (x, lp) in self.loops.iter().enumerate() {
            if in_chain[x] {
                continue;
            }
            for p in 0..ENTRIES {
                let mut children = [0usize; 4];
                let mut umask = 0u128;
                let mut idx = 0;
                let mut ok = true;
                for (i, &o) in lp.orbits.iter().enumerate() {
                    if i == p {
                        continue;
                    }
                    if root_mask >> o & 1 == 1 {
                        ok = false;
                        break;
                    }
                    children[idx] = o;
                    idx += 1;
                    umask |= 1u128 << uidx[o];
                }
                if ok {
                    rows.push(Row {
                        parent: lp.orbits[p],
                        children,
                        umask,
                    });
                }
            }
        }
        // For each universe element, the rows containing it.
        let mut elem_rows = vec![Vec::new(); universe.len()];
        for (ri, r) in rows.iter().enumerate() {
            let mut m = r.umask;
            while m != 0 {
                elem_rows[m.trailing_zeros() as usize].push(ri);
                m &= m - 1;
            }
        }
        struct Search<'a> {
            rows: &'a [Row],
            elem_rows: &'a [Vec<usize>],
            root_mask: u128,
            exact: u64,
            rooted: u64,
            stop_first: bool,
            done: bool,
            chosen: Vec<usize>,
        }
        impl Search<'_> {
            /// Algorithm-X style recursion: cover the free element with
            /// the fewest still-available rows.
            fn go(&mut self, free: u128) {
                if self.done {
                    return;
                }
                if free == 0 {
                    self.exact += 1;
                    if self.check_rooted() {
                        self.rooted += 1;
                        if self.stop_first {
                            self.done = true;
                        }
                    }
                    return;
                }
                let mut best: Option<(usize, usize)> = None; // (count, elem)
                let mut f = free;
                while f != 0 {
                    let e = f.trailing_zeros() as usize;
                    f &= f - 1;
                    let cnt = self.elem_rows[e]
                        .iter()
                        .filter(|&&ri| self.rows[ri].umask & !free == 0)
                        .count();
                    if cnt == 0 {
                        return; // element e is uncoverable — dead end
                    }
                    if best.is_none_or(|(bc, _)| cnt < bc) {
                        best = Some((cnt, e));
                        if cnt == 1 {
                            break;
                        }
                    }
                }
                let (_, e) = best.expect("free != 0 has at least one element");
                let cands: Vec<usize> = self.elem_rows[e]
                    .iter()
                    .copied()
                    .filter(|&ri| self.rows[ri].umask & !free == 0)
                    .collect();
                for ri in cands {
                    self.chosen.push(ri);
                    self.go(free & !self.rows[ri].umask);
                    self.chosen.pop();
                    if self.done {
                        return;
                    }
                }
            }

            /// Every chosen row's parent chain must terminate at a root
            /// orbit (the ownership digraph is acyclic toward roots).
            fn check_rooted(&self) -> bool {
                let mut owner = [usize::MAX; ORBITS];
                for (slot, &ri) in self.chosen.iter().enumerate() {
                    for &o in &self.rows[ri].children {
                        owner[o] = slot;
                    }
                }
                let mut state = vec![0u8; self.chosen.len()]; // 0 new, 1 visiting, 2 rooted
                for start in 0..self.chosen.len() {
                    if state[start] == 2 {
                        continue;
                    }
                    let mut stack = Vec::new();
                    let mut cur = start;
                    loop {
                        if state[cur] == 2 {
                            break; // joins an already-rooted chain
                        }
                        if state[cur] == 1 {
                            return false; // ownership cycle
                        }
                        state[cur] = 1;
                        stack.push(cur);
                        let p = self.rows[self.chosen[cur]].parent;
                        if self.root_mask >> p & 1 == 1 {
                            break; // parent is a root orbit
                        }
                        cur = owner[p]; // p is non-root ⇒ owned by a chosen row
                        debug_assert_ne!(cur, usize::MAX, "non-root orbit without owner");
                    }
                    for s in stack {
                        state[s] = 2;
                    }
                }
                true
            }
        }
        let full: u128 = if universe.is_empty() {
            0
        } else {
            (!0u128) >> (128 - universe.len())
        };
        let mut search = Search {
            rows: &rows,
            elem_rows: &elem_rows,
            root_mask,
            exact: 0,
            rooted: 0,
            stop_first: stop_at_first_rooted,
            done: false,
            chosen: Vec::new(),
        };
        search.go(full);
        CoverReport {
            roots,
            non_root: universe.len(),
            rows: rows.len(),
            exact_covers: search.exact,
            rooted_covers: search.rooted,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// door on a concrete word, all costs.
    #[test]
    fn door_definition() {
        let w: Word = [1, 2, 3, 4, 5, 6];
        assert_eq!(door(w, 1), [2, 3, 4, 5, 6, 1]);
        assert_eq!(door(w, 2), [3, 4, 5, 6, 2, 1]);
        assert_eq!(door(w, 3), [4, 5, 6, 3, 2, 1]);
        assert_eq!(door(w, 4), [5, 6, 4, 3, 2, 1]);
        assert_eq!(door(w, 5), [6, 5, 4, 3, 2, 1]);
        assert_eq!(door(w, 6), [6, 5, 4, 3, 2, 1]);
    }

    /// Construction runs all internal gates: 144 loops, tv period 5,
    /// distinct entry orbits, per-class orbit partition, and the splice
    /// identity door(s_i, 2) = e_{i+1}.
    #[test]
    fn construction_gates() {
        let cert = Cert::new();
        assert_eq!(cert.loops.len(), LOOPS);
        for lp in &cert.loops {
            let mut orbits = lp.orbits;
            orbits.sort_unstable();
            orbits.windows(2).for_each(|w| assert_ne!(w[0], w[1]));
            for e in &lp.entries {
                assert_eq!(e[W - 1], lp.pivot);
            }
        }
    }

    /// C2: every hop word keeps the pivot and lands on an entry of the
    /// owning loop (landing-on-entry is automatic).
    #[test]
    fn hop_audit_gates() {
        let cert = Cert::new();
        let a = cert.audit_hops();
        assert_eq!(a.pairs, 720);
        assert_eq!(a.pivot_violations, 0);
        assert_eq!(a.non_entry_landings, 0);
        // Computed: every hop word at every cost lands on a different
        // loop of the class — one valid target per (loop, splice, cost).
        assert_eq!(a.valid_by_cost, [720, 720, 720, 720]);
        assert_eq!(a.self_by_cost, [0, 0, 0, 0]);
    }

    /// C1 (computed, then pinned): the forced map is a permutation of
    /// the 720 states with 180 cycles, all of length exactly 4.
    #[test]
    fn forced_map_is_period_4_permutation() {
        let cert = Cert::new();
        let f = cert.forced_audit();
        assert_eq!(f.states, 720);
        assert!(f.total_map);
        assert!(f.is_permutation);
        assert_eq!(f.cycle_lengths, BTreeMap::from([(4, 180)]));
    }

    /// Positive control scaffold: the standard kernel (forced orbit of
    /// the identity state) is a K = 4 chain of distinct loops with
    /// Σ = 0 and V = 4, for every pivot.
    #[test]
    fn standard_kernel_recovery() {
        let cert = Cert::new();
        for pivot in 1..=W as u8 {
            let kernel = cert.standard_kernel(pivot);
            let mut ls = kernel.loops.clone();
            ls.sort_unstable();
            ls.dedup();
            assert_eq!(ls.len(), 4, "pivot {pivot}: kernel loops not distinct");
            let s = kernel.stats();
            assert_eq!((s.k, s.sigma, s.v), (4, 0, 4), "pivot {pivot}");
            assert_eq!((s.f4, s.f5, s.f6), (0, 0, 0), "pivot {pivot}");
            assert_eq!(cert.root_mask(&kernel).count_ones(), 20, "pivot {pivot}");
        }
    }

    /// C5: ledger arithmetic.
    #[test]
    fn ledger_arithmetic() {
        assert_eq!(waste_and_length(4), (147, 872));
        assert_eq!(waste_and_length(8), (146, 871));
    }

    /// C3 (computed, then pinned): pivot class 1 — max V = 8 achieved by
    /// exactly two chains, one (K=22, Σ=14, f4=0) and one
    /// (K=20, Σ=8, f4=1). The CLI runs all six classes; by symmetry the
    /// test pins one class to keep the suite fast.
    #[test]
    fn class_search_pivot_1() {
        let cert = Cert::new();
        let s = cert.search_class(1);
        assert_eq!(s.max_v, 8);
        assert_eq!(s.chains.len(), 2);
        let mut breakdown: Vec<(usize, i64, usize)> = s
            .chains
            .iter()
            .map(|c| {
                let st = c.stats();
                assert_eq!(st.v, 8);
                (st.k, st.sigma, st.f4)
            })
            .collect();
        breakdown.sort_unstable();
        assert_eq!(breakdown, vec![(20, 8, 1), (22, 14, 0)]);
    }

    /// C4 (computed, then pinned): the two optimal chains of pivot
    /// class 1 admit no rooted cover, while the standard kernel (the
    /// positive control) does — validating the cover machinery.
    #[test]
    fn covers_optimal_chains_fail_control_succeeds() {
        let cert = Cert::new();
        let s = cert.search_class(1);
        for chain in &s.chains {
            let r = cert.cover_search(chain, false);
            assert_eq!(r.rooted_covers, 0, "optimal chain unexpectedly coverable");
        }
        let kernel = cert.standard_kernel(6);
        let r = cert.cover_search(&kernel, true);
        assert_eq!(r.non_root, 100);
        assert!(r.rooted_covers >= 1, "control must find a rooted cover");
    }
}
