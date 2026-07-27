//! Exact endgame tablebase (phase-3 item 4).
//!
//! Once only `m` permutations remain unvisited, the cheapest possible
//! completion is computable *exactly* by Held–Karp dynamic programming
//! over `(subset of remaining already visited, last visited perm)`:
//!
//! ```text
//! dp[S][j] = min chars appended to visit exactly the set S ⊆ remaining,
//!            starting from `cur` and ending on j ∈ S
//! dp[{j}][j] = w(cur, j)
//! dp[S][j]   = min over i ∈ S∖{j} of dp[S∖{j}][i] + w(i, j)
//! answer     = min over j of dp[remaining][j]
//! ```
//!
//! This is exact for superpermutation completion — not merely a bound —
//! because the overlap distance satisfies the triangle inequality
//! (`w(a, c) ≤ w(a, b) + w(b, c)`: appending `b`'s completion and then
//! `c`'s yields a string that reaches `c` from `a` at that combined
//! cost, and `w(a, c)` is minimal), so passing through already-visited
//! permutations, or through remaining ones out of first-visit order,
//! never saves characters: the optimal completion is an optimal
//! Hamiltonian path on the remaining set. Any claim of the form "no
//! completion of this prefix beats length L" produced by this module is
//! therefore a theorem, not a heuristic verdict.
//!
//! Cost is `2^m · m` `u16` table entries (`m = 20` → 40 MB, ~0.1 s;
//! `m = 24` → 800 MB, seconds) and `O(2^m · m²)` time, which caps
//! practical use at [`MAX_REMAINING`]. Weights are computed pairwise by
//! brute-force overlap — `O(m² n)` is noise next to the DP — and
//! weight-`n` "jump" edges (zero overlap) are included implicitly, so a
//! state can never dead-end.

use crate::graph::Graph;

/// Hard cap on the remaining-set size: `m = 25` already needs a 1.7 GB
/// table; anything larger is out of RAM reach on this design point.
pub const MAX_REMAINING: usize = 25;

/// An exact optimal completion.
pub struct Endgame {
    /// Characters that must be appended: the provably minimal cost of
    /// visiting every remaining permutation starting from `cur`.
    pub cost: u32,
    /// The remaining permutations' ranks in an optimal visit order
    /// (one witness; optima are typically non-unique).
    pub order: Vec<u32>,
}

/// Edge weight from rank `a` to rank `b`: characters appended so a
/// string ending in `perms[a]` ends in `perms[b]` (`n` when disjoint).
#[inline]
fn wt(g: &Graph, a: u32, b: u32) -> u16 {
    (g.n - Graph::overlap(&g.perms[a as usize], &g.perms[b as usize])) as u16
}

/// Solve the endgame exactly: minimal appended characters (and a
/// witness order) to visit all of `remaining` starting from `cur`.
///
/// `remaining` must be non-empty, at most [`MAX_REMAINING`] ranks, all
/// distinct and not containing `cur`.
pub fn solve_endgame(g: &Graph, cur: u32, remaining: &[u32]) -> Endgame {
    let m = remaining.len();
    assert!(
        (1..=MAX_REMAINING).contains(&m),
        "endgame size must be in 1..={MAX_REMAINING} (got {m})"
    );
    debug_assert!(!remaining.contains(&cur));

    // Dense weight matrices over remaining indices (u16 never overflows:
    // costs are at most m·n ≤ 25·8 < u16::MAX − n).
    let mut wm = vec![0u16; m * m];
    for i in 0..m {
        for j in 0..m {
            if i != j {
                wm[i * m + j] = wt(g, remaining[i], remaining[j]);
            }
        }
    }
    let w0: Vec<u16> = remaining.iter().map(|&q| wt(g, cur, q)).collect();

    let full: usize = (1 << m) - 1;
    let mut dp = vec![u16::MAX; (full + 1) * m];
    for (j, &w) in w0.iter().enumerate() {
        dp[(1 << j) * m + j] = w;
    }
    // Push-style relaxation: masks ascend, and every target mask is
    // strictly larger than its source, so each dp entry is final before
    // it is read.
    for mask in 1..=full {
        let base = mask * m;
        let mut inside = mask;
        while inside != 0 {
            let j = inside.trailing_zeros() as usize;
            inside &= inside - 1;
            let d = dp[base + j];
            if d == u16::MAX {
                continue;
            }
            let row = j * m;
            let mut outside = full & !mask;
            while outside != 0 {
                let k = outside.trailing_zeros() as usize;
                outside &= outside - 1;
                let slot = &mut dp[(mask | (1 << k)) * m + k];
                let nd = d + wm[row + k];
                if nd < *slot {
                    *slot = nd;
                }
            }
        }
    }

    let (mut j, &cost) = dp[full * m..]
        .iter()
        .enumerate()
        .min_by_key(|&(_, &c)| c)
        .expect("m >= 1");

    // Backtrack one optimal order by re-checking which predecessor
    // achieves each dp value (no parent table needed).
    let mut order = Vec::with_capacity(m);
    let mut mask = full;
    loop {
        order.push(remaining[j]);
        let prev = mask & !(1 << j);
        if prev == 0 {
            debug_assert_eq!(dp[mask * m + j], w0[j]);
            break;
        }
        let target = dp[mask * m + j];
        let mut inside = prev;
        let i = loop {
            let i = inside.trailing_zeros() as usize;
            if dp[prev * m + i] != u16::MAX && dp[prev * m + i] + wm[i * m + j] == target {
                break i;
            }
            inside &= inside - 1;
            debug_assert_ne!(inside, 0, "dp backtrack found no predecessor");
        };
        mask = prev;
        j = i;
    }
    order.reverse();

    Endgame {
        cost: u32::from(cost),
        order,
    }
}

/// Spell out a first-visit rank path as its superpermutation string
/// (maximal-overlap concatenation), as ASCII digits.
pub fn spell_path(g: &Graph, ranks: &[u32]) -> String {
    let mut chars: Vec<u8> = g.perms[ranks[0] as usize].clone();
    for pair in ranks.windows(2) {
        let p = &g.perms[pair[0] as usize];
        let q = &g.perms[pair[1] as usize];
        let t = Graph::overlap(p, q);
        chars.extend_from_slice(&q[t..]);
    }
    chars.iter().map(|&v| (b'0' + v) as char).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::greedy::greedy;
    use crate::validate::validate;

    /// Brute-force optimal completion cost by enumerating every visit
    /// order of `remaining`.
    fn brute(g: &Graph, cur: u32, remaining: &mut Vec<u32>) -> u32 {
        if remaining.is_empty() {
            return 0;
        }
        let mut best = u32::MAX;
        for i in 0..remaining.len() {
            let q = remaining.remove(i);
            let c = u32::from(wt(g, cur, q)) + brute(g, q, remaining);
            best = best.min(c);
            remaining.insert(i, q);
        }
        best
    }

    fn order_cost(g: &Graph, cur: u32, order: &[u32]) -> u32 {
        let mut c = u32::from(wt(g, cur, order[0]));
        for pair in order.windows(2) {
            c += u32::from(wt(g, pair[0], pair[1]));
        }
        c
    }

    #[test]
    fn matches_brute_force_on_greedy_suffixes_n4() {
        let g = Graph::new(4);
        let path = greedy(&g).path;
        for m in 1..=8 {
            let keep = g.nfact - m;
            let cur = path[keep - 1];
            let mut remaining: Vec<u32> = path[keep..].to_vec();
            remaining.sort_unstable();
            let e = solve_endgame(&g, cur, &remaining);
            let b = brute(&g, cur, &mut remaining.clone());
            assert_eq!(e.cost, b, "m={m}");
            // The witness order is a permutation of remaining at its cost.
            let mut o = e.order.clone();
            o.sort_unstable();
            assert_eq!(o, remaining, "m={m}");
            assert_eq!(order_cost(&g, cur, &e.order), e.cost, "m={m}");
        }
    }

    /// Arbitrary (non-suffix) remaining sets, against brute force.
    #[test]
    fn matches_brute_force_on_arbitrary_sets_n4() {
        let g = Graph::new(4);
        for (cur, remaining) in [
            (0u32, vec![1u32, 3, 5, 8, 13, 21]),
            (7, vec![0, 2, 11, 17, 22, 23]),
            (23, vec![4, 6, 9, 10, 12, 14, 19]),
        ] {
            let e = solve_endgame(&g, cur, &remaining);
            let b = brute(&g, cur, &mut remaining.clone());
            assert_eq!(e.cost, b, "cur={cur}");
            assert_eq!(order_cost(&g, cur, &e.order), e.cost, "cur={cur}");
        }
    }

    /// Full n=4 endgame from the identity start: the exact completion
    /// must land exactly on the proven optimum 33.
    #[test]
    fn full_n4_endgame_reproduces_proven_optimum() {
        let g = Graph::new(4);
        let remaining: Vec<u32> = (1..g.nfact as u32).collect();
        let e = solve_endgame(&g, 0, &remaining);
        assert_eq!(g.n as u32 + e.cost, 33);
        let mut path = vec![0u32];
        path.extend_from_slice(&e.order);
        let s = spell_path(&g, &path);
        assert_eq!(s.len(), 33);
        let v = validate(4, &s);
        assert!(v.complete);
    }

    /// Greedy n=5 prefix + exact endgame: any completion of an optimal
    /// walk's prefix is bounded below by the global optimum 153 and
    /// above by greedy's own completion (153), so the exact total is
    /// exactly 153 — and the recomposed string must validate.
    #[test]
    fn greedy_prefix_plus_exact_endgame_is_optimal_n5() {
        let g = Graph::new(5);
        let r = greedy(&g);
        for m in [12usize, 15] {
            let keep = g.nfact - m;
            let prefix = &r.path[..keep];
            let mut remaining: Vec<u32> = r.path[keep..].to_vec();
            remaining.sort_unstable();
            let prefix_len = spell_path(&g, prefix).len();
            let e = solve_endgame(&g, *prefix.last().unwrap(), &remaining);
            assert_eq!(prefix_len as u32 + e.cost, 153, "m={m}");
            let mut path = prefix.to_vec();
            path.extend_from_slice(&e.order);
            let s = spell_path(&g, &path);
            assert_eq!(s.len(), 153, "m={m}");
            assert!(validate(5, &s).complete, "m={m}");
        }
    }
}
