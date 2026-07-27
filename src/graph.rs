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

        Graph {
            n,
            nfact,
            perms,
            succs,
            cycle_id,
            cycle_count,
            pred1,
        }
    }

    /// The unique weight-1 successor of rank `r` (its left rotation).
    #[inline]
    pub fn succ1(&self, r: u32) -> u32 {
        self.succs[r as usize][0].0
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
