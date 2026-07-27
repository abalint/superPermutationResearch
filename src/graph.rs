//! The permutation overlap graph.
//!
//! Vertices are the `n!` permutations of `{1, …, n}` in lexicographic
//! order, identified by their Lehmer-code rank. There is an edge from
//! permutation `P` to permutation `Q ≠ P` of weight
//! `w = n − (length of the maximal overlap of a suffix of P with a prefix of Q)`,
//! i.e. the number of characters that must be appended to a string ending
//! in `P` so that it ends in `Q`.
//!
//! For weight `w ∈ 1..=n−1` the successors of `P` are exactly the
//! permutations whose first `n − w` symbols are `P[w..]` and whose last
//! `w` symbols are some arrangement of `P[..w]` — there are `w!` of them
//! per weight, all distinct across weights (a weight-`w` successor starts
//! with symbol `P[w]`, and those first symbols are pairwise distinct).
//! Weight-`n` edges (zero overlap; a jump to an arbitrary permutation)
//! are *not* stored; searches handle them with an explicit fallback.
//!
//! The unique weight-1 successor of `P` is its left rotation
//! `P[1..] + P[0]`. Rotation partitions the `n!` permutations into
//! `(n−1)!` cycles of size `n` ("1-cycles"); [`Graph::cycle_id`] labels
//! each permutation with its cycle. Cycle structure drives the admissible
//! lower bound in [`crate::bound`].

use crate::bitset::BitSet;

/// `n!` as `usize` (exact for the small `n` used here; `8! = 40320`).
pub fn factorial(n: usize) -> usize {
    (1..=n).product()
}

/// Lexicographic (Lehmer-code) rank of a permutation of distinct symbols.
///
/// `rank(P) = Σᵢ (#{ j > i : P[j] < P[i] }) · (n − 1 − i)!` — the number
/// of permutations of the same symbols that are lexicographically
/// smaller than `P`.
pub fn rank(perm: &[u8]) -> usize {
    let n = perm.len();
    let mut r = 0usize;
    for (i, &pi) in perm.iter().enumerate() {
        let smaller = perm[i + 1..].iter().filter(|&&x| x < pi).count();
        r += smaller * factorial(n - 1 - i);
    }
    r
}

/// Inverse of [`rank`]: the permutation of `{1, …, n}` with the given
/// lexicographic rank (`0 ≤ rank < n!`).
///
/// Decodes the factorial-base digits of `rank` high-to-low, each digit
/// selecting (and removing) an element of the ascending pool `1..=n`.
pub fn unrank(n: usize, rank: usize) -> Vec<u8> {
    debug_assert!(rank < factorial(n));
    let mut pool: Vec<u8> = (1..=n as u8).collect();
    let mut out = Vec::with_capacity(n);
    let mut r = rank;
    for i in (0..n).rev() {
        let f = factorial(i);
        out.push(pool.remove(r / f));
        r %= f;
    }
    out
}

/// In-place lexicographic next permutation; returns `false` when the
/// input was already the lexicographically last arrangement.
fn next_permutation(a: &mut [u8]) -> bool {
    let len = a.len();
    if len < 2 {
        return false;
    }
    let mut i = len - 1;
    while i > 0 && a[i - 1] >= a[i] {
        i -= 1;
    }
    if i == 0 {
        return false;
    }
    let mut j = len - 1;
    while a[j] <= a[i - 1] {
        j -= 1;
    }
    a.swap(i - 1, j);
    a[i..].reverse();
    true
}

/// The permutation overlap graph for a fixed `n` (3 ≤ n ≤ 8).
pub struct Graph {
    /// Number of symbols.
    pub n: usize,
    /// `n!`, the number of vertices.
    pub nfact: usize,
    /// `perms[r]` is the permutation with lexicographic rank `r`
    /// (symbols are `1..=n` stored as `u8`).
    pub perms: Vec<Vec<u8>>,
    /// `succs[r]` lists the weight ≤ `n−1` successors of `perms[r]` as
    /// `(successor rank, weight)`, sorted by weight ascending and then
    /// lexicographically by the appended `w`-character suffix (which
    /// equals the successor's last `w` symbols).
    pub succs: Vec<Vec<(u32, u8)>>,
    /// Rotation-cycle label of each permutation, in `0..cycle_count`.
    pub cycle_id: Vec<u32>,
    /// `(n−1)!`, the number of rotation cycles.
    pub cycle_count: usize,
    /// `pred1[r]` is the unique weight-1 predecessor of rank `r` — the
    /// right rotation `P[n−1] + P[..n−1]`, in the same cycle.
    pub pred1: Vec<u32>,
    /// `w2x[r]` is the unique *cross-cycle* weight-2 successor of rank
    /// `r`: `P[2..] + P[1] + P[0]` (swap the first two symbols, then
    /// rotate twice). Of a permutation's two weight-2 successors the
    /// other one is the in-cycle double rotation; this one always lands
    /// in a different rotation cycle (swapping an adjacent pair of a
    /// cyclic sequence of ≥ 3 distinct symbols never yields a rotation
    /// of it). These are the edges the record walks' "2-cycle weave" is
    /// built from (JOURNAL s5). The map is a bijection on ranks.
    pub w2x: Vec<u32>,
    /// Inverse of [`Graph::w2x`]: `w2rev[w2x[r]] == r`.
    pub w2rev: Vec<u32>,
}

impl Graph {
    /// Build the full graph for `n` symbols.
    ///
    /// Successor lists are generated directly in sorted order: for each
    /// weight `w` in ascending order, the arrangements of `P[..w]` are
    /// enumerated lexicographically, and within a fixed weight the
    /// appended suffix *is* the arrangement, so lexicographic order of
    /// arrangements is lexicographic order of appended suffixes.
    pub fn new(n: usize) -> Graph {
        assert!((3..=8).contains(&n), "n must be in 3..=8");
        let nfact = factorial(n);
        let perms: Vec<Vec<u8>> = (0..nfact).map(|r| unrank(n, r)).collect();

        let per_perm: usize = (1..n).map(factorial).sum();
        let mut succs = Vec::with_capacity(nfact);
        for p in &perms {
            let mut list = Vec::with_capacity(per_perm);
            for w in 1..n {
                let mut tail: Vec<u8> = p[..w].to_vec();
                tail.sort_unstable();
                loop {
                    let mut q: Vec<u8> = p[w..].to_vec();
                    q.extend_from_slice(&tail);
                    list.push((rank(&q) as u32, w as u8));
                    if !next_permutation(&mut tail) {
                        break;
                    }
                }
            }
            succs.push(list);
        }

        // Label rotation cycles by following weight-1 edges. The first
        // entry of every successor list is the unique weight-1 successor
        // (the left rotation), so cycles can be traced directly.
        let mut cycle_id = vec![u32::MAX; nfact];
        let mut cycle_count = 0usize;
        for start in 0..nfact {
            if cycle_id[start] != u32::MAX {
                continue;
            }
            let mut cur = start;
            loop {
                cycle_id[cur] = cycle_count as u32;
                cur = succs[cur][0].0 as usize;
                if cur == start {
                    break;
                }
            }
            cycle_count += 1;
        }
        debug_assert_eq!(cycle_count, factorial(n - 1));

        // Weight-1 predecessors: invert the weight-1 successor map.
        let mut pred1 = vec![0u32; nfact];
        for r in 0..nfact {
            pred1[succs[r][0].0 as usize] = r as u32;
        }

        // Cross-cycle weight-2 successors: of the two weight-2 entries
        // in each successor list, exactly one leaves the rotation cycle.
        let mut w2x = vec![u32::MAX; nfact];
        for r in 0..nfact {
            for &(q, w) in &succs[r] {
                if w == 2 && cycle_id[q as usize] != cycle_id[r] {
                    debug_assert_eq!(w2x[r], u32::MAX, "two cross-cycle w2 successors of {r}");
                    w2x[r] = q;
                }
            }
            debug_assert_ne!(w2x[r], u32::MAX, "no cross-cycle w2 successor of {r}");
        }
        let mut w2rev = vec![u32::MAX; nfact];
        for (r, &q) in w2x.iter().enumerate() {
            debug_assert_eq!(w2rev[q as usize], u32::MAX, "w2x is not injective at {q}");
            w2rev[q as usize] = r as u32;
        }

        Graph {
            n,
            nfact,
            perms,
            succs,
            cycle_id,
            cycle_count,
            pred1,
            w2x,
            w2rev,
        }
    }

    /// The unique weight-1 successor of rank `r` (its left rotation).
    #[inline]
    pub fn succ1(&self, r: u32) -> u32 {
        self.succs[r as usize][0].0
    }

    /// Change in the `w2_bridges` feature caused by visiting `q` from
    /// the state `(visited, cycle_rem)`, where
    ///
    /// ```text
    /// w2_bridges = #{ ranks P : P unvisited, w2x(P) unvisited,
    ///                 cycle(P) has ≥ 1 visited member,
    ///                 cycle(w2x(P)) has ≥ 1 visited member }
    /// ```
    ///
    /// — the number of still-traversable cross-cycle weight-2 edges
    /// joining two *partially visited* cycles (each endpoint cycle has
    /// deficit ≥ 1, witnessed by its unvisited endpoint, and ≥ 1 visited
    /// member). This is the "2-cycle weave capacity" between touched
    /// cycles that separates record midgames from rollout midgames at
    /// equal `(r, level)` (JOURNAL s5 §4): record walks keep many cycles
    /// partially open and rejoin them later through exactly these edges,
    /// while greedy-shaped walks finish cycles and leave few live
    /// bridges. A pure function of the visited set alone (not of `cur`),
    /// so beam dedup and bucket-key arguments are untouched.
    ///
    /// Caller contract: `visited`/`cycle_rem` describe the state
    /// *before* the move, and `cycle_rem` has not yet been decremented.
    /// The delta never reads `q`'s own visited bit, so it is safe to
    /// call just before or just after `visited.set(q)`.
    ///
    /// Cost: O(1) when `q`'s cycle is already touched (only `q`'s two
    /// incident edges can change — every other edge keeps both endpoint
    /// statuses and both cycle flags); O(n) when `q`'s cycle was intact
    /// (its `2(n−1)` other incident edges may all start counting — the
    /// cycle's "≥ 1 visited" flag flips, which happens once per cycle,
    /// so a full walk pays O(1) amortized). A cycle emptying out
    /// (`cycle_rem` 1 → 0) needs no scan: its flag stays true and every
    /// incident edge already has a visited endpoint on the `q` side.
    pub fn w2_bridges_delta(&self, visited: &BitSet, cycle_rem: &[u8], q: u32) -> i64 {
        let n = self.n;
        let touched = |cid: u32| (cycle_rem[cid as usize] as usize) < n;
        let cid_q = self.cycle_id[q as usize];
        if touched(cid_q) {
            // q's cycle stays touched; only q's own two edges die.
            let mut d = 0i64;
            let out = self.w2x[q as usize];
            if !visited.get(out as usize) && touched(self.cycle_id[out as usize]) {
                d -= 1; // edge q -> w2x(q) was counted, q is now visited
            }
            let inp = self.w2rev[q as usize];
            if !visited.get(inp as usize) && touched(self.cycle_id[inp as usize]) {
                d -= 1; // edge w2rev(q) -> q was counted, q is now visited
            }
            d
        } else {
            // q's cycle becomes touched: its other members' incident
            // edges may start counting (q's own contribute 0 both
            // before — untouched cycle — and after — q visited). Every
            // scanned rank is either a member m != q or a w2 partner of
            // one, which lies outside the cycle and hence is also != q,
            // so the pre-move visited bits and the other cycles' flags
            // equal the post-move ones.
            let mut d = 0i64;
            let mut m = self.succ1(q);
            while m != q {
                if !visited.get(m as usize) {
                    let out = self.w2x[m as usize];
                    if !visited.get(out as usize) && touched(self.cycle_id[out as usize]) {
                        d += 1;
                    }
                    let inp = self.w2rev[m as usize];
                    if !visited.get(inp as usize) && touched(self.cycle_id[inp as usize]) {
                        d += 1;
                    }
                }
                m = self.succ1(m);
            }
            d
        }
    }

    /// Length of the maximal overlap of a suffix of `a` with a prefix of
    /// `b` (both length-`n` permutations). Brute force; used for path
    /// reconstruction and by tests as an independent weight oracle.
    pub fn overlap(a: &[u8], b: &[u8]) -> usize {
        let n = a.len();
        for t in (1..n).rev() {
            if a[n - t..] == b[..t] {
                return t;
            }
        }
        0
    }
}

/// Weight-graded predecessor lists — the mirror of [`Graph::succs`],
/// needed by the two-ended (deque) searcher, which prepends predecessors
/// of the string's front. Built on demand ([`Preds::new`]) so
/// [`Graph::new`] — and every one-ended searcher — is untouched.
pub struct Preds {
    /// `lists[r]` lists the weight ≤ `n−1` predecessors of `perms[r]` as
    /// `(predecessor rank, weight)`: `(p, w)` appears here iff `(r, w)`
    /// appears in `succs[p]`. Sorted by weight ascending, then
    /// lexicographically by the prepended `w`-character prefix (which
    /// equals the predecessor's first `w` symbols) — the exact mirror of
    /// the successor ordering.
    pub lists: Vec<Vec<(u32, u8)>>,
}

impl Preds {
    /// Build the predecessor lists for `g`.
    ///
    /// Mirror of the successor construction: the weight-`w` predecessors
    /// of `Q` are exactly `A ++ Q[..n−w]` for the `w!` arrangements `A`
    /// of `Q[n−w..]` — such a `p` satisfies `p[w..] = Q[..n−w]` (the
    /// overlap) while `Q`'s last `w` symbols are an arrangement of
    /// `p[..w]`, i.e. `(Q, w) ∈ succs[p]`; conversely every weight-`w`
    /// successor relation has this shape. Enumerating the arrangements
    /// lexicographically yields lists sorted by weight then prefix,
    /// generated in order (never sorted), like `Graph::new`.
    pub fn new(g: &Graph) -> Preds {
        let n = g.n;
        let per_perm: usize = (1..n).map(factorial).sum();
        let mut lists = Vec::with_capacity(g.nfact);
        for q in &g.perms {
            let mut list = Vec::with_capacity(per_perm);
            for w in 1..n {
                let mut head: Vec<u8> = q[n - w..].to_vec();
                head.sort_unstable();
                loop {
                    let mut p = head.clone();
                    p.extend_from_slice(&q[..n - w]);
                    list.push((rank(&p) as u32, w as u8));
                    if !next_permutation(&mut head) {
                        break;
                    }
                }
            }
            lists.push(list);
        }
        Preds { lists }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rank_unrank_roundtrip() {
        for n in 3..=6 {
            for r in 0..factorial(n) {
                let p = unrank(n, r);
                assert_eq!(rank(&p), r, "n={n} r={r}");
            }
            // Lexicographic order is respected: rank 0 is the identity.
            assert_eq!(unrank(n, 0), (1..=n as u8).collect::<Vec<_>>());
        }
    }

    #[test]
    fn successor_counts() {
        for n in 3..=6 {
            let g = Graph::new(n);
            let expected: usize = (1..n).map(factorial).sum();
            for list in &g.succs {
                assert_eq!(list.len(), expected);
                // No duplicate targets.
                let mut targets: Vec<u32> = list.iter().map(|&(q, _)| q).collect();
                targets.sort_unstable();
                targets.dedup();
                assert_eq!(targets.len(), expected);
            }
        }
    }

    #[test]
    fn successor_lists_sorted_by_weight_then_suffix() {
        let g = Graph::new(4);
        for (r, list) in g.succs.iter().enumerate() {
            for pair in list.windows(2) {
                let (q0, w0) = pair[0];
                let (q1, w1) = pair[1];
                assert!(w0 <= w1, "weights ascending for perm {r}");
                if w0 == w1 {
                    let s0 = &g.perms[q0 as usize][g.n - w0 as usize..];
                    let s1 = &g.perms[q1 as usize][g.n - w1 as usize..];
                    assert!(s0 < s1, "suffixes lex-ascending for perm {r}");
                }
            }
        }
    }

    /// Every listed edge's weight matches the brute-force overlap
    /// definition, and every pair with overlap ≥ 1 is listed (n = 4).
    #[test]
    fn edge_weights_match_brute_force_n4() {
        let n = 4;
        let g = Graph::new(n);
        for a in 0..g.nfact {
            let listed: std::collections::HashMap<u32, u8> = g.succs[a].iter().copied().collect();
            for b in 0..g.nfact {
                if a == b {
                    continue;
                }
                let w = n - Graph::overlap(&g.perms[a], &g.perms[b]);
                if w < n {
                    assert_eq!(listed.get(&(b as u32)), Some(&(w as u8)), "{a}->{b}");
                } else {
                    assert!(
                        !listed.contains_key(&(b as u32)),
                        "{a}->{b} weight n listed"
                    );
                }
            }
        }
    }

    #[test]
    fn pred1_inverts_succ1_and_is_right_rotation() {
        for n in 3..=6 {
            let g = Graph::new(n);
            for r in 0..g.nfact {
                let s = g.succ1(r as u32);
                assert_eq!(g.pred1[s as usize], r as u32, "n={n} r={r}");
                // pred1 of P is the right rotation P[n−1] + P[..n−1].
                let p = &g.perms[r];
                let mut rot: Vec<u8> = vec![p[n - 1]];
                rot.extend_from_slice(&p[..n - 1]);
                assert_eq!(g.perms[g.pred1[r] as usize], rot, "n={n} r={r}");
            }
        }
    }

    #[test]
    fn preds_invert_succs_exactly() {
        for n in 3..=5 {
            let g = Graph::new(n);
            let preds = Preds::new(&g);
            let expected: usize = (1..n).map(factorial).sum();
            let mut succ_edges = std::collections::HashSet::new();
            for (p, list) in g.succs.iter().enumerate() {
                for &(q, w) in list {
                    succ_edges.insert((p as u32, q, w));
                }
            }
            let mut pred_edges = std::collections::HashSet::new();
            for (q, list) in preds.lists.iter().enumerate() {
                assert_eq!(list.len(), expected, "n={n} q={q}");
                for &(p, w) in list {
                    pred_edges.insert((p, q as u32, w));
                }
            }
            assert_eq!(succ_edges, pred_edges, "n={n}");
        }
    }

    #[test]
    fn preds_sorted_by_weight_then_prefix_and_head_is_pred1() {
        let g = Graph::new(4);
        let preds = Preds::new(&g);
        for (q, list) in preds.lists.iter().enumerate() {
            // First entry is the unique weight-1 predecessor.
            assert_eq!(list[0], (g.pred1[q], 1), "q={q}");
            for pair in list.windows(2) {
                let (p0, w0) = pair[0];
                let (p1, w1) = pair[1];
                assert!(w0 <= w1, "weights ascending for perm {q}");
                if w0 == w1 {
                    let a = &g.perms[p0 as usize][..w0 as usize];
                    let b = &g.perms[p1 as usize][..w1 as usize];
                    assert!(a < b, "prefixes lex-ascending for perm {q}");
                }
            }
        }
    }

    #[test]
    fn w2x_is_the_cross_cycle_swap_and_a_bijection() {
        for n in 3..=6 {
            let g = Graph::new(n);
            let mut seen = vec![false; g.nfact];
            for r in 0..g.nfact {
                let q = g.w2x[r];
                // It is a stored weight-2 successor...
                assert!(
                    g.succs[r].contains(&(q, 2)),
                    "n={n} r={r}: w2x not a w2 successor"
                );
                // ... in a different cycle ...
                assert_ne!(g.cycle_id[r], g.cycle_id[q as usize], "n={n} r={r}");
                // ... equal to P[2..] + P[1] + P[0] ...
                let p = &g.perms[r];
                let mut expect: Vec<u8> = p[2..].to_vec();
                expect.push(p[1]);
                expect.push(p[0]);
                assert_eq!(g.perms[q as usize], expect, "n={n} r={r}");
                // ... and the inverse map agrees.
                assert_eq!(g.w2rev[q as usize], r as u32, "n={n} r={r}");
                assert!(!seen[q as usize], "n={n}: w2x not injective");
                seen[q as usize] = true;
            }
        }
    }

    #[test]
    fn cycles_partition_perms() {
        for n in 3..=6 {
            let g = Graph::new(n);
            assert_eq!(g.cycle_count, factorial(n - 1));
            let mut sizes = vec![0usize; g.cycle_count];
            for &c in &g.cycle_id {
                sizes[c as usize] += 1;
            }
            assert!(sizes.iter().all(|&s| s == n), "n={n}: {sizes:?}");
            // The weight-1 successor stays in the same cycle.
            for r in 0..g.nfact {
                let (q, w) = g.succs[r][0];
                assert_eq!(w, 1);
                assert_eq!(g.cycle_id[r], g.cycle_id[q as usize]);
            }
        }
    }
}
