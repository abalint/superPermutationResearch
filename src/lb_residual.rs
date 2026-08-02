//! Residual-graph admissible lower bound (`docs/RESIDUAL-BOUND-DESIGN.md`).
//!
//! # What is bounded
//!
//! A state is `(cur, visited)`; `R = complement(visited)` is the
//! *residual set* and `A = R ∪ {cur}` the set of permutations the walk
//! can still *stand on*. The quantity bounded is the minimum number of
//! characters needed to cover every member of `R`, allowing revisits of
//! already-covered permutations (a **covering walk**, the hard invariant
//! of the design doc).
//!
//! Covering walks reduce to simple ones: the overlap weight satisfies
//! the triangle inequality (`w(a,c) ≤ w(a,b)+w(b,c)`), so replacing a
//! covering walk by the first-visit order of `R` never costs more (the
//! same argument that makes [`crate::endgame`] exact). Hence
//!
//! > the optimal covering cost equals `min Σ w(v_{i−1}, v_i)` over
//! > sequences `cur = v₀, v₁, …, v_m` with `{v₁,…,v_m} = R` distinct,
//!
//! and it suffices to prove every term below for such **first-visit
//! sequences**. Two facts are used throughout:
//!
//! * the predecessor of `x`'s first visit lies in `A ∖ {x}` (it is `cur`
//!   or a member of `R` first-visited earlier);
//! * distinct `x ∈ R` have distinct first-visit steps, so charges made
//!   once per `x ∈ R` never collide.
//!
//! # The terms
//!
//! **(1) Minimum in-edge (`door`).** For `x ∈ R` let
//! `minin(x) = min{ w(y→x) : y ∈ A ∖ {x} }`. The first visit of `x`
//! costs `≥ minin(x)`, and these are distinct steps, so the completion
//! costs `≥ Σ_{x∈R} minin(x) = r + door` with
//! `door = Σ_{x∈R} (minin(x) − 1) ≥ 0`.
//!
//! `minin` is computed from the tabulated in-neighbours of weight ≤ 3
//! ([`PredTable`]): the weight-`w` in-neighbours of `x` are the `w!`
//! permutations `t ++ x[..n−w]` with `t` an arrangement of `x[n−w..]`,
//! i.e. 1 at weight 1 (`pred1`), 2 at weight 2 (the in-cycle
//! `rot⁻²(x)` and the **door** `τ⁻¹(x)` = [`crate::graph::Graph::w2rev`]),
//! 6 at weight 3. If none of those 9 is available the true minimum is
//! `≥ 4`, and `min(4, n)` is used.
//!
//! **(2) Intact classes (`intact`).** If a rotation class `C` is
//! *entirely* residual, the first member of `C` to be visited is entered
//! from outside `C` (any earlier-visited member would contradict
//! firstness), and every edge leaving a rotation class has weight ≥ 2
//! (weight-1 edges are rotations). That step already carries a charge of
//! `minin(x) = 1` in term (1) — `pred1(x) ∈ C ⊆ R ⊆ A` for *every*
//! `x ∈ C`, so whichever member is entered first was charged exactly 1 —
//! hence one further character may be charged per intact class.
//!
//! **(3) Dead-door singly-covered classes (`long`).** Let `C` be a
//! rotation class with exactly one covered member `p ≠ cur`. Its
//! residual part is the single arc `α = C ∖ {p}` with head
//! `h = succ1(p)`. Term (1) charged `minin(h) = 2` (its weight-1
//! in-neighbour `p` is covered, its weight-2 in-neighbour `rot⁻²(h)`
//! lies in `α ⊆ R`) and `minin(x) = 1` for the other members. The first
//! member of `α` to be visited is entered from outside `α`; that entry
//! costs
//! * `≥ 2` for `x ≠ h` (the weight-1 in-neighbour `pred1(x)` lies in
//!   `α`, so it cannot be the entry), which is 1 above the charge of
//!   term (1); and
//! * `≥ 3` for `x = h` **if the door `τ⁻¹(h)` is unavailable**, since
//!   `h`'s only in-neighbours of weight ≤ 2 are `p` (covered),
//!   `rot⁻²(h)` (inside `α`) and `τ⁻¹(h)`; that is 1 above the charge of
//!   term (1) too.
//!
//! So when `τ⁻¹(h) ∉ A` one further character may be charged for `C`,
//! whichever member of `α` is entered first. `cur`'s own class is
//! excluded (if it has exactly one covered member that member is `cur`
//! itself, and then `pred1(h) = cur ∈ A` makes the entry cheap).
//!
//! The three charges land on distinct steps or on distinct excess above
//! a step's own term-(1) charge, so they add:
//!
//! ```text
//! B_residual = r + door + intact + long.
//! ```
//!
//! # Relation to the existing bounds
//!
//! `B_residual ≥ lb_arc = r + arcs − [succ1(cur) ∈ R]` pointwise: every
//! *open* arc's head `h` has `pred1(h) ∉ R`, so `minin(h) ≥ 2` unless
//! `pred1(h) = cur` (which happens for at most one arc, the one headed
//! by `succ1(cur)`), giving `door ≥ #open arcs − [succ1(cur) ∈ R]`;
//! circular arcs are exactly the intact classes, contributing 1 each via
//! term (2). `lb_arc ≥ lb_cycle` is already known, so the residual bound
//! dominates both.
//!
//! # Cost
//!
//! All terms are maintained incrementally. The transition
//! `(cur, R) → (q, R∖{q})` changes the standable set from `A = R ∪ {cur}`
//! to `A' = R`, i.e. it removes exactly `cur`; that part is shared by
//! every candidate `q` of a state and is computed once in
//! [`ParentCtx::new`] (O(9²) lookups). Per candidate only `q`'s own
//! `minin` (9 lookups) and `q`'s rotation class need attention
//! ([`child_terms`], O(n)).

use crate::bitset::BitSet;
use crate::graph::Graph;

/// Highest edge weight whose in-neighbours are tabulated.
pub const MAX_PRED_WEIGHT: usize = 3;

/// Tabulated in-neighbours per rank: `1! + 2! + 3!`.
pub const PRED_SLOTS: usize = 9;

/// Weight of each slot of [`PredTable`]'s per-rank in-neighbour block.
const SLOT_WEIGHT: [u8; PRED_SLOTS] = [1, 2, 2, 3, 3, 3, 3, 3, 3];

/// In-neighbours of every rank at weight ≤ [`MAX_PRED_WEIGHT`].
///
/// Built by inverting the graph's successor lists, whose first
/// `1! + 2! + 3!` entries are exactly the weight-1, weight-2 and
/// weight-3 successors (successor lists are sorted by weight). For
/// `n = 3` weight-3 edges are the unstored zero-overlap jumps, so those
/// slots stay empty — harmless, since [`PredTable::minin`] then returns
/// `min(4, n) = 3`, which is the true weight of every such edge.
pub struct PredTable {
    /// `PRED_SLOTS` in-neighbour ranks per rank; `u32::MAX` = empty.
    preds: Vec<u32>,
    /// Value returned when no tabulated in-neighbour is available: any
    /// remaining in-edge has weight > [`MAX_PRED_WEIGHT`], and weights
    /// never exceed `n`.
    miss: u32,
}

impl PredTable {
    /// Tabulate `g`'s in-neighbours of weight ≤ [`MAX_PRED_WEIGHT`].
    pub fn new(g: &Graph) -> PredTable {
        // Slot layout per rank: [0] weight 1, [1..3] weight 2,
        // [3..9] weight 3. In-neighbours arrive in arbitrary weight
        // order (they are indexed by *source*), so each weight class
        // gets its own fill cursor.
        const SLOT_BASE: [usize; MAX_PRED_WEIGHT + 1] = [0, 0, 1, 3];
        let mut preds = vec![u32::MAX; g.nfact * PRED_SLOTS];
        let mut fill = vec![0u8; g.nfact * (MAX_PRED_WEIGHT + 1)];
        for x in 0..g.nfact {
            for &(q, w) in g.succs[x].iter() {
                let w = w as usize;
                if w > MAX_PRED_WEIGHT {
                    break; // successor lists ascend by weight
                }
                let cursor = &mut fill[q as usize * (MAX_PRED_WEIGHT + 1) + w];
                let slot = SLOT_BASE[w] + *cursor as usize;
                debug_assert_eq!(usize::from(SLOT_WEIGHT[slot]), w);
                preds[q as usize * PRED_SLOTS + slot] = x as u32;
                *cursor += 1;
            }
        }
        PredTable {
            preds,
            miss: 4.min(g.n as u32),
        }
    }

    /// `min{ w(y→x) : y ∈ A ∖ {x} }`, capped at `min(4, n)`, where
    /// availability is given by `avail`.
    ///
    /// `x` is never its own in-neighbour in the table (successor lists
    /// exclude self-loops), so the `∖ {x}` is automatic.
    #[inline]
    pub fn minin(&self, x: u32, avail: impl Fn(u32) -> bool) -> u32 {
        let base = x as usize * PRED_SLOTS;
        for (&y, &w) in self.preds[base..base + PRED_SLOTS].iter().zip(&SLOT_WEIGHT) {
            if y != u32::MAX && avail(y) {
                return u32::from(w);
            }
        }
        self.miss
    }

    /// `minin` with availability = "unvisited in `visited`".
    #[inline]
    pub fn minin_unvisited(&self, x: u32, visited: &BitSet) -> u32 {
        self.minin(x, |y| !visited.get(y as usize))
    }

    /// `minin` with availability = "unvisited in `visited`, or `cur`" —
    /// the standable set `A` of the state `(cur, visited)`.
    #[inline]
    pub fn minin_state(&self, x: u32, visited: &BitSet, cur: u32) -> u32 {
        self.minin(x, |y| y == cur || !visited.get(y as usize))
    }
}

/// The `door` term `Σ_{x ∈ R} (minin(x) − 1)` of the state
/// `(cur, visited)`, recomputed from scratch in `O(n! · PRED_SLOTS)`.
///
/// Reference implementation: the searchers maintain this incrementally
/// and the tests check them against it.
pub fn door_scratch(g: &Graph, tab: &PredTable, visited: &BitSet, cur: u32) -> u32 {
    (0..g.nfact as u32)
        .filter(|&x| !visited.get(x as usize))
        .map(|x| tab.minin_state(x, visited, cur) - 1)
        .sum()
}

/// The `long` term of the state `(cur, visited)`, recomputed from
/// scratch: rotation classes other than `cur`'s that have exactly one
/// covered member and whose residual arc head has an unavailable door.
pub fn long_scratch(g: &Graph, visited: &BitSet, cur: u32, cycle_rem: &[u8]) -> u32 {
    let cur_cid = g.cycle_id[cur as usize];
    (0..g.nfact as u32)
        .filter(|&p| {
            // p is the unique covered member of its class, which is not
            // cur's class, and the head succ1(p)'s door is unavailable.
            visited.get(p as usize)
                && g.cycle_id[p as usize] != cur_cid
                && cycle_rem[g.cycle_id[p as usize] as usize] as usize == g.n - 1
                && !avail(g.w2rev[g.succ1(p) as usize], visited, cur)
        })
        .count() as u32
}

/// Whether `y` is standable in the state `(cur, visited)`.
#[inline]
fn avail(y: u32, visited: &BitSet, cur: u32) -> bool {
    y == cur || !visited.get(y as usize)
}

/// The residual admissible lower bound `r + door + intact + long`
/// (0 when nothing remains). See the module docs for the proof.
#[inline]
pub fn lower_bound_residual(r: usize, door: usize, intact: usize, long: usize) -> usize {
    if r == 0 {
        0
    } else {
        r + door + intact + long
    }
}

/// The part of a state→child transition shared by every candidate move.
///
/// Moving to any `q` turns the standable set `A = R ∪ {cur}` into
/// `A' = R` (`cur` is dropped; `q` stays, as the new current
/// permutation). `door_mid`/`long_mid` are the `door`/`long` terms of
/// the *parent's* residual set re-evaluated under `A'`, before `q`
/// itself is removed from it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ParentCtx {
    /// `Σ_{x ∈ R} (minin_{A'}(x) − 1)` over the parent's residual set.
    pub door_mid: u32,
    /// `long` over *all* classes with one covered member under `A'`
    /// (no class excluded; the child excludes its own).
    pub long_mid: u32,
}

impl ParentCtx {
    /// Compute the shared transition data of the state
    /// `(cur, visited)` whose maintained terms are `door` and `long`.
    ///
    /// Only permutations having `cur` as an in-neighbour of weight ≤ 3
    /// can change `minin` when `cur` stops being standable — that is,
    /// exactly `cur`'s ≤ 9 successors of weight ≤ 3. Likewise the only
    /// door that can die is `cur`'s own weight-2 cross-class successor
    /// `w2x(cur)`, and the only class whose exclusion changes is
    /// `cur`'s. O(`PRED_SLOTS`²) lookups.
    pub fn new(
        g: &Graph,
        tab: &PredTable,
        visited: &BitSet,
        cur: u32,
        cycle_rem: &[u8],
        door: u32,
        long: u32,
    ) -> ParentCtx {
        let mut door_mid = door;
        for &(x, w) in g.succs[cur as usize].iter() {
            if w as usize > MAX_PRED_WEIGHT {
                break;
            }
            if visited.get(x as usize) {
                continue; // not in R: carries no door charge
            }
            let before = tab.minin_state(x, visited, cur);
            let after = tab.minin_unvisited(x, visited);
            door_mid += after - before;
        }

        let mut long_mid = long;
        // (a) cur's class was excluded from `long` and is not excluded
        //     from `long_mid`. It qualifies only if it has exactly one
        //     covered member, which is then cur itself.
        let cur_cid = g.cycle_id[cur as usize] as usize;
        if cycle_rem[cur_cid] as usize == g.n - 1 {
            let head = g.succ1(cur);
            debug_assert_eq!(g.pred1[head as usize], cur);
            if visited.get(g.w2rev[head as usize] as usize) {
                long_mid += 1;
            }
        }
        // (b) the one door that can die when cur stops being standable
        //     is the door of h = w2x(cur); it matters only if h heads
        //     the arc of a singly-covered class other than cur's.
        let h = g.w2x[cur as usize];
        let h_cid = g.cycle_id[h as usize] as usize;
        if h_cid != cur_cid
            && cycle_rem[h_cid] as usize == g.n - 1
            && !visited.get(h as usize)
            && visited.get(g.pred1[h as usize] as usize)
        {
            // Under A the door w2rev[h] == cur was available, so this
            // class contributed 0; under A' it contributes 1.
            debug_assert_eq!(g.w2rev[h as usize], cur);
            long_mid += 1;
        }
        ParentCtx { door_mid, long_mid }
    }
}

/// The child's `(door, long)` terms after the parent visits `q`.
///
/// `visited`/`cycle_rem` describe the parent (`q` not yet visited),
/// `ctx` is the parent's [`ParentCtx`]. O(n).
#[inline]
pub fn child_terms(
    g: &Graph,
    tab: &PredTable,
    visited: &BitSet,
    cycle_rem: &[u8],
    ctx: &ParentCtx,
    q: u32,
) -> (u32, u32) {
    // `q` leaves the residual set; its own charge goes with it. The
    // child's standable set is exactly the parent's unvisited set.
    let door = ctx.door_mid - (tab.minin_unvisited(q, visited) - 1);

    // The child excludes q's class from `long`; it is the only class
    // whose covered-member count changes, so nothing else moves.
    let cid = g.cycle_id[q as usize] as usize;
    let mut long = ctx.long_mid;
    if cycle_rem[cid] as usize == g.n - 1 {
        // Under the parent this class had exactly one covered member p;
        // find it (O(n)) and undo its contribution if it had one.
        let mut p = g.succ1(q);
        while !visited.get(p as usize) {
            p = g.succ1(p);
        }
        let head = g.succ1(p);
        if visited.get(g.w2rev[head as usize] as usize) {
            long -= 1;
        }
    }
    (door, long)
}

/// The `(door, long)` terms after `q` is visited **without the current
/// permutation moving onto it** — the two-ended beam's *prepend* move,
/// which visits `q` at the string's front while `cur` (the appending
/// end, relative to which [`crate::beam2`] keeps its one-ended terms)
/// stays put.
///
/// `visited`/`cycle_rem`/`door`/`long` describe the parent (`q` not yet
/// visited). The standable set goes from `A = R ∪ {cur}` to
/// `A' = A ∖ {q}`: `q` leaves the residual set and, being visited, is
/// not standable. Same shape as [`ParentCtx::new`] + [`child_terms`],
/// with `q` rather than `cur` leaving `A`. O(n).
#[allow(clippy::too_many_arguments)]
pub fn child_terms_keeping_cur(
    g: &Graph,
    tab: &PredTable,
    visited: &BitSet,
    cycle_rem: &[u8],
    cur: u32,
    door: u32,
    long: u32,
    q: u32,
) -> (u32, u32) {
    debug_assert!(!visited.get(q as usize), "revisit of {q}");
    debug_assert_ne!(cur, q, "a keep-cursor move never lands on cur");
    let avail_parent = |y: u32| avail(y, visited, cur);
    let avail_child = |y: u32| y != q && avail(y, visited, cur);

    // door: `q` leaves R, so its own charge goes with it; every other
    // charge can change only for the ≤ 3-weight successors of `q`,
    // whose minimum in-edge may have used `q`.
    let mut d = door - (tab.minin(q, avail_parent) - 1);
    for &(x, w) in g.succs[q as usize].iter() {
        if w as usize > MAX_PRED_WEIGHT {
            break;
        }
        if visited.get(x as usize) {
            continue; // not in R: carries no door charge
        }
        d += tab.minin(x, avail_child) - tab.minin(x, avail_parent);
    }

    let mut l = long;
    let cur_cid = g.cycle_id[cur as usize] as usize;
    let q_cid = g.cycle_id[q as usize] as usize;
    let rem = cycle_rem[q_cid] as usize;
    // (a) q's class gains a covered member. cur's own class is excluded
    //     from `long` before and after, so it never contributes.
    if q_cid != cur_cid {
        if rem == g.n {
            // q becomes its class's unique covered member.
            let head = g.succ1(q);
            if !avail_child(g.w2rev[head as usize]) {
                l += 1;
            }
        } else if rem == g.n - 1 {
            // The class had a unique covered member p; now it has two,
            // so it stops qualifying — undo its contribution if it had
            // one (O(n) to find p).
            let mut p = g.succ1(q);
            while !visited.get(p as usize) {
                p = g.succ1(p);
            }
            let head = g.succ1(p);
            if !avail_parent(g.w2rev[head as usize]) {
                l -= 1;
            }
        }
    }
    // (b) the one door that dies when q stops being standable is the
    //     door of h = w2x(q); it matters only if h heads the residual
    //     arc of a singly-covered class other than cur's (h always lies
    //     outside q's own class — w2x is the cross-class edge).
    let h = g.w2x[q as usize];
    let h_cid = g.cycle_id[h as usize] as usize;
    debug_assert_ne!(h_cid, q_cid, "w2x leaves the rotation class");
    if h_cid != cur_cid
        && cycle_rem[h_cid] as usize == g.n - 1
        && !visited.get(h as usize)
        && visited.get(g.pred1[h as usize] as usize)
    {
        // Under A the door w2rev[h] == q was available, so this class
        // contributed 0; under A' it contributes 1.
        debug_assert_eq!(g.w2rev[h as usize], q);
        l += 1;
    }
    (d, l)
}

/// **NOT ADMISSIBLE — ordering only (Tier 3 of the design doc).**
///
/// Hunter's per-vertex price `q_k = 1 + 1/k + 1/(k(k−1)) + 1/((k−1)(k(k−1)(k−2)−k))`
/// applied to the residual count. The price is proven only for
/// *complete* Hamiltonian paths over all `n!` permutations, through a
/// global F-transform and an amortized left-to-right excess induction
/// (`thm:b1`, `thm:excess`); nothing in that argument survives
/// restriction to an arbitrary residual set, and this function *does*
/// exceed the true completion cost on small residual sets. It must
/// never be used for pruning or for any admissibility-dependent
/// reasoning — it exists so move/beam **ordering** experiments can try
/// the shape without contaminating the admissible path.
pub fn heuristic_floor_not_admissible(n: usize, r: usize, admissible: usize) -> usize {
    if r == 0 {
        return 0;
    }
    let k = n as f64;
    let q =
        1.0 + 1.0 / k + 1.0 / (k * (k - 1.0)) + 1.0 / ((k - 1.0) * (k * (k - 1.0) * (k - 2.0) - k));
    admissible.max((q * r as f64).ceil() as usize)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::walk::Walk;
    use rand::rngs::StdRng;
    use rand::{Rng, SeedableRng};

    /// The tabulated in-neighbours must be exactly the true weight-≤3
    /// in-neighbours, with the right multiplicities.
    #[test]
    fn pred_table_matches_brute_force() {
        for n in [3usize, 4, 5] {
            let g = Graph::new(n);
            let tab = PredTable::new(&g);
            for x in 0..g.nfact {
                let mut got: Vec<(u8, u32)> = (0..PRED_SLOTS)
                    .filter_map(|s| {
                        let y = tab.preds[x * PRED_SLOTS + s];
                        (y != u32::MAX).then_some((SLOT_WEIGHT[s], y))
                    })
                    .collect();
                let mut want: Vec<(u8, u32)> = (0..g.nfact as u32)
                    .filter(|&y| y as usize != x)
                    .filter_map(|y| {
                        let w = n - Graph::overlap(&g.perms[y as usize], &g.perms[x]);
                        (w <= MAX_PRED_WEIGHT).then_some((w as u8, y))
                    })
                    .collect();
                got.sort_unstable();
                want.sort_unstable();
                // n = 3 stores no weight-3 edges (they are the jumps).
                if n > MAX_PRED_WEIGHT {
                    assert_eq!(got, want, "n={n} x={x}");
                } else {
                    assert_eq!(
                        got,
                        want.into_iter().filter(|&(w, _)| w < 3).collect::<Vec<_>>(),
                        "n={n} x={x}"
                    );
                }
            }
        }
    }

    /// `minin` never exceeds the true cheapest available in-edge.
    #[test]
    fn minin_is_a_lower_bound_on_every_available_in_edge() {
        for n in [4usize, 5] {
            let g = Graph::new(n);
            let tab = PredTable::new(&g);
            let mut rng = StdRng::seed_from_u64(7);
            for _ in 0..200 {
                let mut visited = BitSet::new(g.nfact);
                for x in 0..g.nfact {
                    if rng.gen::<f64>() < 0.5 {
                        visited.set(x);
                    }
                }
                let cur = rng.gen_range(0..g.nfact as u32);
                for x in 0..g.nfact as u32 {
                    let lb = tab.minin_state(x, &visited, cur);
                    let truth = (0..g.nfact as u32)
                        .filter(|&y| y != x && avail(y, &visited, cur))
                        .map(|y| {
                            (n - Graph::overlap(&g.perms[y as usize], &g.perms[x as usize])) as u32
                        })
                        .min();
                    if let Some(t) = truth {
                        assert!(lb <= t, "n={n} x={x} lb={lb} truth={t}");
                    }
                }
            }
        }
    }

    /// The incrementally maintained `door`/`long`/`intact` terms must
    /// equal from-scratch recounts at every step of random walks.
    #[test]
    fn incremental_terms_match_scratch_on_random_walks() {
        for n in [3usize, 4, 5] {
            let g = Graph::new(n);
            let tab = PredTable::new(&g);
            for seed in 0..4u64 {
                let mut rng = StdRng::seed_from_u64(seed);
                let mut w = Walk::new(&g);
                loop {
                    assert_eq!(
                        w.st.cyc.door,
                        door_scratch(&g, &tab, &w.st.cyc.visited, w.cur()),
                        "n={n} seed={seed} step={} door",
                        w.steps()
                    );
                    assert_eq!(
                        w.st.cyc.long,
                        long_scratch(&g, &w.st.cyc.visited, w.cur(), &w.st.cyc.cycle_rem),
                        "n={n} seed={seed} step={} long",
                        w.steps()
                    );
                    assert_eq!(
                        w.st.cyc.intact as usize,
                        w.st.cyc
                            .cycle_rem
                            .iter()
                            .filter(|&&c| c as usize == n)
                            .count(),
                        "n={n} seed={seed} step={} intact",
                        w.steps()
                    );
                    if w.done() {
                        break;
                    }
                    let options = w.unvisited_succs();
                    let (q, wt) = if options.is_empty() {
                        (w.fallback_target(), n as u8)
                    } else if rng.gen::<f64>() < 0.4 {
                        options[rng.gen_range(0..options.len())]
                    } else {
                        options[0]
                    };
                    w.advance(q, wt);
                }
            }
        }
    }

    /// The residual bound dominates the arc bound (hence the cycle
    /// bound) at every state of random walks, and is admissible against
    /// the exact endgame tablebase once the tail is small enough.
    #[test]
    fn dominates_arc_bound_and_never_exceeds_exact_truth() {
        for n in [4usize, 5] {
            let g = Graph::new(n);
            for seed in 0..6u64 {
                let mut rng = StdRng::seed_from_u64(100 + seed);
                let mut w = Walk::new(&g);
                while !w.done() {
                    assert!(
                        w.lb_residual() >= w.lb_arc(),
                        "n={n} seed={seed} step={} residual={} arc={}",
                        w.steps(),
                        w.lb_residual(),
                        w.lb_arc()
                    );
                    // Small tails only: the tablebase is 2^m — the
                    // large-m sweep is gate GA's job, not a unit test.
                    if w.st.cyc.r <= 12 {
                        let remaining: Vec<u32> = (0..g.nfact as u32)
                            .filter(|&x| !w.st.cyc.visited.get(x as usize))
                            .collect();
                        let truth = crate::endgame::solve_endgame(&g, w.cur(), &remaining).cost;
                        assert!(
                            w.lb_residual() as u32 <= truth,
                            "n={n} seed={seed} step={} bound={} truth={truth}",
                            w.steps(),
                            w.lb_residual()
                        );
                    }
                    let options = w.unvisited_succs();
                    let (q, wt) = if options.is_empty() {
                        (w.fallback_target(), n as u8)
                    } else if rng.gen::<f64>() < 0.35 {
                        options[rng.gen_range(0..options.len())]
                    } else {
                        options[0]
                    };
                    w.advance(q, wt);
                }
            }
        }
    }
}
