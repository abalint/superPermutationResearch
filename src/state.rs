//! The shared incremental search state — one definition of every
//! counter update rule in the crate (s64 P3).
//!
//! Every searcher here walks the permutation overlap graph one *first
//! visit* at a time and needs the same derived quantities to score,
//! bound and bucket its states. Before this module each engine kept its
//! own copy of the counters *and* of the arithmetic that maintains them
//! (`Walk`, the beam's `State` — re-derived a third and fourth time
//! inside `score_move` and `bucket_key` —, `beam2`'s `State2`, the
//! sojourn DFS and the union DFS), so a fix to one rule reached none of
//! the others. The rules now live here exactly once and the engines
//! store them:
//!
//! * [`CycleState`] — the per-cycle visit bookkeeping every engine
//!   keeps: the visited set, the per-cycle unvisited counts, the
//!   current permutation, the emitted length, `k` / `r` / `intact` and
//!   the residual bound's `door` / `long` terms. Used by
//!   [`crate::walk`], [`crate::beam`], [`crate::beam2`],
//!   [`crate::sojourn`] and [`crate::unionsearch`].
//! * [`SearchState`] — [`CycleState`] plus the counters only the
//!   beam-family engines derive: `arcs` (the arc bound), the
//!   deficit-distribution triple `half_open` / `nearly_done` /
//!   `w2_bridges` (phase-3 item 3 features) and the step counter. Used
//!   by [`crate::walk`], [`crate::beam`] and [`crate::beam2`].
//!
//! Two ways to apply a move, sharing one rule set:
//!
//! * `visit` / `advance` mutate a state in place (walk, sojourn, union
//!   DFS — states that are cloned or undone rather than re-derived);
//! * `child` builds the child from a parent plus an already-materialized
//!   visited set (the beams, which clone the visited set once per
//!   *surviving* candidate).
//!
//! and the individual `child_*` readers give one child counter in O(1)
//! from the parent's cached counters *without* materializing the child
//! at all — that is what the beams' candidate scoring, bucketing and
//! feature vectors call, so the O(1)-no-clone scoring contract
//! (CLAUDE.md) is met by the same arithmetic the states are updated
//! with.
//!
//! [`SearchState::recount`] recomputes every counter from scratch and is
//! the reference implementation the incremental rules are tested
//! against (`walk.rs`, `beam.rs`, `beam2.rs`, `sojourn.rs` unit tests
//! and `tests/deficit_features.rs`).

use crate::bitset::BitSet;
use crate::graph::Graph;
use crate::lb_residual::{self, ParentCtx, PredTable};

/// Where the walk's current permutation ends up when a move visits `q`.
///
/// Append-only searchers always use [`Cursor::Onto`]; the two-ended
/// beam's *prepend* moves visit `q` at the string's front while the
/// current (appending) end stays put, which is [`Cursor::Keep`].
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Cursor {
    /// `q` becomes the current permutation (append / one-ended move).
    Onto,
    /// The current permutation is unchanged (two-ended prepend move).
    Keep,
}

/// Residual-bound transition context: the in-neighbour table plus the
/// parent's shared [`ParentCtx`]. `None` = the residual terms are not
/// maintained (they stay 0, as before this refactor).
pub type Residual<'a> = Option<(&'a PredTable, &'a ParentCtx)>;

/// The per-cycle visit bookkeeping shared by every searcher.
#[derive(Clone, Debug)]
pub struct CycleState {
    /// Visited permutations by rank.
    pub visited: BitSet,
    /// `cycle_rem[c]` = number of unvisited permutations in cycle `c`.
    pub cycle_rem: Box<[u8]>,
    /// Rank of the permutation the string currently ends with (the
    /// *appending* end for the two-ended beam).
    pub cur: u32,
    /// Characters emitted so far.
    pub len: u32,
    /// Number of cycles with at least one unvisited permutation.
    pub k: u32,
    /// Number of unvisited permutations.
    pub r: u32,
    /// Cycles with all `n` members unvisited (intact) — the `intact`
    /// term of [`crate::lb_residual`].
    pub intact: u32,
    /// `Σ_{x unvisited} (minin(x) − 1)`, the `door` term of
    /// [`crate::lb_residual`] (0 unless the residual terms are
    /// maintained).
    pub door: u32,
    /// The dead-door singly-covered-class term of
    /// [`crate::lb_residual`] (0 unless maintained).
    pub long: u32,
}

impl CycleState {
    /// Root state: the identity permutation (rank 0) visited, its `n`
    /// characters emitted.
    ///
    /// With `tab = Some`, `door`/`long` are computed from scratch rather
    /// than asserted to be their known root values (0 and 0 — at the
    /// root every permutation is standable, so every `minin` is 1 and
    /// only rank 0's class is touched), so the initialisation cannot
    /// drift from the definitions.
    pub fn root(g: &Graph, tab: Option<&PredTable>) -> CycleState {
        let mut visited = BitSet::new(g.nfact);
        visited.set(0);
        let mut cycle_rem = vec![g.n as u8; g.cycle_count].into_boxed_slice();
        cycle_rem[g.cycle_id[0] as usize] -= 1;
        let door = tab.map_or(0, |t| lb_residual::door_scratch(g, t, &visited, 0));
        let long = tab.map_or(0, |_| lb_residual::long_scratch(g, &visited, 0, &cycle_rem));
        CycleState {
            visited,
            cycle_rem,
            cur: 0,
            len: g.n as u32,
            // n ≥ 3 ⇒ every cycle still has unvisited members.
            k: g.cycle_count as u32,
            r: (g.nfact - 1) as u32,
            // Rank 0's cycle is already broken by the initial visit.
            intact: (g.cycle_count - 1) as u32,
            door,
            long,
        }
    }

    /// The parent's unvisited count of `q`'s cycle — the input every
    /// per-cycle rule below is a case analysis of.
    #[inline]
    pub fn rem_of(&self, g: &Graph, q: u32) -> u32 {
        u32::from(self.cycle_rem[g.cycle_id[q as usize] as usize])
    }

    /// Cycles with an unvisited member after visiting `q`: `q`'s cycle
    /// drops out iff `q` was its last unvisited member.
    #[inline]
    pub fn child_k(&self, g: &Graph, q: u32) -> u32 {
        self.k - u32::from(self.rem_of(g, q) == 1)
    }

    /// Intact (all-`n`-unvisited) cycles after visiting `q`: `q`'s cycle
    /// stops being intact iff it was.
    #[inline]
    pub fn child_intact(&self, g: &Graph, q: u32) -> u32 {
        self.intact - u32::from(self.rem_of(g, q) as usize == g.n)
    }

    /// Unvisited members of `of`'s cycle after visiting `q` (they share
    /// a cycle or they do not).
    #[inline]
    pub fn child_rem_of(&self, g: &Graph, q: u32, of: u32) -> u32 {
        self.rem_of(g, of) - u32::from(g.cycle_id[of as usize] == g.cycle_id[q as usize])
    }

    /// Unvisited members of `q`'s own cycle after visiting `q` — the
    /// `current_cycle_remaining` feature of a child whose current
    /// permutation is `q` (the `of == q` case of
    /// [`child_rem_of`](CycleState::child_rem_of)).
    #[inline]
    pub fn child_cur_rem(&self, g: &Graph, q: u32) -> u32 {
        self.child_rem_of(g, q, q)
    }

    /// The residual bound's shared per-parent transition context (see
    /// [`ParentCtx`]); one per parent state, reused by all its
    /// candidates.
    #[inline]
    pub fn parent_ctx(&self, g: &Graph, tab: &PredTable) -> ParentCtx {
        ParentCtx::new(
            g,
            tab,
            &self.visited,
            self.cur,
            &self.cycle_rem,
            self.door,
            self.long,
        )
    }

    /// The child's `(door, long)` residual terms after visiting `q`,
    /// for a [`Cursor::Onto`] move (`ctx` is this state's
    /// [`parent_ctx`](CycleState::parent_ctx)).
    #[inline]
    pub fn child_residual(
        &self,
        g: &Graph,
        tab: &PredTable,
        ctx: &ParentCtx,
        q: u32,
    ) -> (u32, u32) {
        lb_residual::child_terms(g, tab, &self.visited, &self.cycle_rem, ctx, q)
    }

    /// The child's `(door, long)` residual terms for a [`Cursor::Keep`]
    /// move (the current permutation stays standable).
    #[inline]
    pub fn child_residual_keeping_cur(&self, g: &Graph, tab: &PredTable, q: u32) -> (u32, u32) {
        lb_residual::child_terms_keeping_cur(
            g,
            tab,
            &self.visited,
            &self.cycle_rem,
            self.cur,
            self.door,
            self.long,
            q,
        )
    }

    /// Apply the move visiting `q` (appending `weight` characters) in
    /// place. `tab = Some` maintains the residual terms, `None` leaves
    /// them untouched.
    #[inline]
    pub fn visit(&mut self, g: &Graph, q: u32, weight: u32, tab: Option<&PredTable>) {
        debug_assert!(!self.visited.get(q as usize), "revisit of {q}");
        if let Some(t) = tab {
            // The residual terms need the pre-move state.
            let ctx = self.parent_ctx(g, t);
            let (door, long) = self.child_residual(g, t, &ctx, q);
            self.door = door;
            self.long = long;
        }
        let cid = g.cycle_id[q as usize] as usize;
        self.intact -= u32::from(self.cycle_rem[cid] as usize == g.n);
        self.visited.set(q as usize);
        self.cycle_rem[cid] -= 1;
        self.k -= u32::from(self.cycle_rem[cid] == 0);
        self.r -= 1;
        self.len += weight;
        self.cur = q;
    }

    /// Undo the move that visited `q` with `weight` characters, from a
    /// state whose current permutation was `prev_cur` and whose residual
    /// terms were `prev_door` / `prev_long` (those two are not
    /// invertible, so the caller trails them; every other counter is
    /// restored by the exact inverse of [`visit`](CycleState::visit)).
    #[inline]
    pub fn unvisit(
        &mut self,
        g: &Graph,
        q: u32,
        weight: u32,
        prev_cur: u32,
        prev_door: u32,
        prev_long: u32,
    ) {
        debug_assert!(self.visited.get(q as usize), "unvisit of unvisited {q}");
        let cid = g.cycle_id[q as usize] as usize;
        self.k += u32::from(self.cycle_rem[cid] == 0);
        self.cycle_rem[cid] += 1;
        self.intact += u32::from(self.cycle_rem[cid] as usize == g.n);
        self.visited.clear(q as usize);
        self.r += 1;
        self.len -= weight;
        self.cur = prev_cur;
        self.door = prev_door;
        self.long = prev_long;
    }

    /// Whether every counter of `self` equals `other`'s (the visited
    /// set and per-cycle counts included) — the drift checks' predicate.
    pub fn counters_eq(&self, other: &CycleState) -> bool {
        self.visited == other.visited
            && self.cycle_rem == other.cycle_rem
            && self.cur == other.cur
            && self.len == other.len
            && self.k == other.k
            && self.r == other.r
            && self.intact == other.intact
            && self.door == other.door
            && self.long == other.long
    }

    /// A compact dump of every counter, for drift-test failure messages.
    pub fn counters(&self) -> String {
        format!(
            "cur={} len={} k={} r={} intact={} door={} long={}",
            self.cur, self.len, self.k, self.r, self.intact, self.door, self.long,
        )
    }

    /// The child reached by visiting `q`, with the child's visited set
    /// already materialized (the parent's clone with bit `q` set) and
    /// its length already known — the beams' construction path, which
    /// clones the visited set exactly once per surviving candidate.
    pub fn child(
        &self,
        g: &Graph,
        q: u32,
        len: u32,
        visited: BitSet,
        cursor: Cursor,
        res: Residual,
    ) -> CycleState {
        debug_assert!(!self.visited.get(q as usize), "revisit of {q}");
        let (door, long) = match (res, cursor) {
            (Some((tab, ctx)), Cursor::Onto) => self.child_residual(g, tab, ctx, q),
            (Some((tab, _)), Cursor::Keep) => self.child_residual_keeping_cur(g, tab, q),
            (None, _) => (0, 0),
        };
        let mut cycle_rem = self.cycle_rem.clone();
        let cid = g.cycle_id[q as usize] as usize;
        let intact = self.child_intact(g, q);
        let k = self.child_k(g, q);
        cycle_rem[cid] -= 1;
        CycleState {
            visited,
            cycle_rem,
            cur: match cursor {
                Cursor::Onto => q,
                Cursor::Keep => self.cur,
            },
            len,
            k,
            r: self.r - 1,
            intact,
            door,
            long,
        }
    }
}

/// The full incremental search state: [`CycleState`] plus the counters
/// the beam-family engines derive from the visited set.
#[derive(Clone, Debug)]
pub struct SearchState {
    /// The per-cycle visit bookkeeping (see [`CycleState`]).
    pub cyc: CycleState,
    /// Weight-1 connected components (arcs) among unvisited
    /// permutations. A fully-unvisited cycle counts as one (circular)
    /// component.
    pub arcs: u32,
    /// Cycles with exactly 1 or 2 visited members
    /// (`cycle_rem ∈ {n−1, n−2}`) — half-open (phase-3 item 3).
    pub half_open: u32,
    /// Cycles with exactly 1 or 2 unvisited members
    /// (`cycle_rem ∈ {1, 2}`) — nearly done (phase-3 item 3).
    pub nearly_done: u32,
    /// Live cross-cycle weight-2 edges joining two partially-visited
    /// cycles (see [`Graph::w2_bridges_delta`] for the exact
    /// definition; phase-3 item 3).
    pub w2_bridges: u32,
    /// Number of moves taken (permutations visited − 1).
    pub steps: u32,
}

impl SearchState {
    /// Root state (see [`CycleState::root`]).
    pub fn root(g: &Graph, tab: Option<&PredTable>) -> SearchState {
        SearchState {
            cyc: CycleState::root(g, tab),
            // Every intact cycle is one circular component; visiting
            // rank 0 turned its cycle into a single open arc — still one
            // component.
            arcs: g.cycle_count as u32,
            // Rank 0's cycle has exactly 1 visited member: half-open. It
            // is also nearly done iff n − 1 ≤ 2. No second cycle is
            // touched yet, so no w2 bridge can join two touched cycles.
            half_open: 1,
            nearly_done: u32::from(g.n - 1 <= 2),
            w2_bridges: 0,
            steps: 0,
        }
    }

    /// Number of weight-1 arcs after visiting `q`, in O(1) from the
    /// cached counters.
    ///
    /// If `q`'s cycle was fully unvisited its circular component becomes
    /// one open arc (no change); otherwise the count changes by the
    /// visited status of `q`'s two ring neighbours: both unvisited → the
    /// arc splits (+1); both visited → a singleton arc disappears (−1);
    /// mixed → an endpoint shrinks (0).
    #[inline]
    pub fn child_arcs(&self, g: &Graph, q: u32) -> u32 {
        if self.cyc.rem_of(g, q) as usize == g.n {
            return self.arcs;
        }
        let p_unvis = !self.cyc.visited.get(g.pred1[q as usize] as usize);
        let s_unvis = !self.cyc.visited.get(g.succ1(q) as usize);
        if p_unvis && s_unvis {
            self.arcs + 1
        } else if !p_unvis && !s_unvis {
            self.arcs - 1
        } else {
            self.arcs
        }
    }

    /// Half-open cycles after visiting `q`: `q`'s cycle becomes
    /// half-open iff it was intact, and stops being half-open iff it
    /// held exactly 2 visited members.
    #[inline]
    pub fn child_half_open(&self, g: &Graph, q: u32) -> u32 {
        let rem = self.cyc.rem_of(g, q) as usize;
        self.half_open + u32::from(rem == g.n) - u32::from(rem == g.n - 2)
    }

    /// Nearly-done cycles after visiting `q`: `q`'s cycle joins at 3
    /// unvisited members and leaves at 1.
    #[inline]
    pub fn child_nearly_done(&self, g: &Graph, q: u32) -> u32 {
        let rem = self.cyc.rem_of(g, q);
        self.nearly_done + u32::from(rem == 3) - u32::from(rem == 1)
    }

    /// Live cross-cycle weight-2 bridges after visiting `q` (O(1)
    /// except when `q` first touches an intact cycle, which costs the
    /// O(n) ring scan of [`Graph::w2_bridges_delta`]).
    #[inline]
    pub fn child_w2_bridges(&self, g: &Graph, q: u32) -> u32 {
        (i64::from(self.w2_bridges) + g.w2_bridges_delta(&self.cyc.visited, &self.cyc.cycle_rem, q))
            as u32
    }

    /// The deficit profile `(intact, half_open, nearly_done)` of the
    /// child reached by visiting `q` — the stratified beam's bucket key
    /// (all three are pure functions of the visited set alone, which the
    /// keep-first dedup argument needs).
    #[inline]
    pub fn child_deficit_profile(&self, g: &Graph, q: u32) -> (u32, u32, u32) {
        (
            self.cyc.child_intact(g, q),
            self.child_half_open(g, q),
            self.child_nearly_done(g, q),
        )
    }

    /// Apply the move visiting `q` (appending `weight` characters) in
    /// place, updating every counter. `tab = Some` maintains the
    /// residual terms.
    #[inline]
    pub fn advance(&mut self, g: &Graph, q: u32, weight: u32, tab: Option<&PredTable>) {
        // All of these read the pre-move state.
        let arcs = self.child_arcs(g, q);
        let half_open = self.child_half_open(g, q);
        let nearly_done = self.child_nearly_done(g, q);
        let w2_bridges = self.child_w2_bridges(g, q);
        self.cyc.visit(g, q, weight, tab);
        self.arcs = arcs;
        self.half_open = half_open;
        self.nearly_done = nearly_done;
        self.w2_bridges = w2_bridges;
        self.steps += 1;
    }

    /// The child reached by visiting `q` with its visited set already
    /// materialized (see [`CycleState::child`]).
    pub fn child(
        &self,
        g: &Graph,
        q: u32,
        len: u32,
        visited: BitSet,
        cursor: Cursor,
        res: Residual,
    ) -> SearchState {
        SearchState {
            arcs: self.child_arcs(g, q),
            half_open: self.child_half_open(g, q),
            nearly_done: self.child_nearly_done(g, q),
            w2_bridges: self.child_w2_bridges(g, q),
            steps: self.steps + 1,
            cyc: self.cyc.child(g, q, len, visited, cursor, res),
        }
    }

    /// Recompute every counter from scratch for the state
    /// `(cur, visited)` — the reference implementation the incremental
    /// rules above are tested against. `O(n! · n)`; test-only.
    pub fn recount(
        g: &Graph,
        visited: &BitSet,
        cur: u32,
        len: u32,
        steps: u32,
        tab: Option<&PredTable>,
    ) -> SearchState {
        let n = g.n;
        let mut cycle_rem = vec![0u8; g.cycle_count].into_boxed_slice();
        for x in 0..g.nfact {
            if !visited.get(x) {
                cycle_rem[g.cycle_id[x] as usize] += 1;
            }
        }
        let r = (0..g.nfact).filter(|&x| !visited.get(x)).count() as u32;
        let k = cycle_rem.iter().filter(|&&c| c > 0).count() as u32;
        let intact = cycle_rem.iter().filter(|&&c| c as usize == n).count() as u32;
        // Every arc has exactly one head (an unvisited rank whose
        // weight-1 predecessor is visited), except a fully-unvisited
        // cycle, which is circular and has none.
        let heads = (0..g.nfact)
            .filter(|&x| !visited.get(x) && visited.get(g.pred1[x] as usize))
            .count() as u32;
        let half_open = cycle_rem
            .iter()
            .filter(|&&c| (1..=2).contains(&(n - c as usize)))
            .count() as u32;
        let nearly_done = cycle_rem
            .iter()
            .filter(|&&c| (1..=2).contains(&(c as usize)))
            .count() as u32;
        let touched = |x: usize| (cycle_rem[g.cycle_id[x] as usize] as usize) < n;
        let w2_bridges = (0..g.nfact)
            .filter(|&p| {
                let q = g.w2x[p] as usize;
                !visited.get(p) && !visited.get(q) && touched(p) && touched(q)
            })
            .count() as u32;
        let door = tab.map_or(0, |t| lb_residual::door_scratch(g, t, visited, cur));
        let long = tab.map_or(0, |_| {
            lb_residual::long_scratch(g, visited, cur, &cycle_rem)
        });
        SearchState {
            cyc: CycleState {
                visited: visited.clone(),
                cycle_rem,
                cur,
                len,
                k,
                r,
                intact,
                door,
                long,
            },
            arcs: heads + intact,
            half_open,
            nearly_done,
            w2_bridges,
            steps,
        }
    }

    /// Whether every counter of `self` equals `other`'s (the visited set
    /// and per-cycle counts included). Test helper for the drift checks.
    pub fn counters_eq(&self, other: &SearchState) -> bool {
        self.cyc.counters_eq(&other.cyc)
            && self.arcs == other.arcs
            && self.half_open == other.half_open
            && self.nearly_done == other.nearly_done
            && self.w2_bridges == other.w2_bridges
    }

    /// A compact dump of every counter, for drift-test failure messages.
    pub fn counters(&self) -> String {
        format!(
            "{} arcs={} half_open={} nearly_done={} w2_bridges={}",
            self.cyc.counters(),
            self.arcs,
            self.half_open,
            self.nearly_done,
            self.w2_bridges,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The root state must agree with a from-scratch recount, residual
    /// terms included.
    #[test]
    fn root_matches_recount() {
        for n in [3usize, 4, 5] {
            let g = Graph::new(n);
            let tab = PredTable::new(&g);
            let st = SearchState::root(&g, Some(&tab));
            let scratch = SearchState::recount(&g, &st.cyc.visited, 0, g.n as u32, 0, Some(&tab));
            assert!(
                st.counters_eq(&scratch),
                "n={n}\n  inc {}\n  ref {}",
                st.counters(),
                scratch.counters()
            );
        }
    }

    /// Every counter, maintained incrementally through random walks,
    /// must equal the from-scratch recount at every step — for both the
    /// in-place `advance` path and the `child` construction path, and
    /// with the residual terms on.
    #[test]
    fn advance_and_child_match_recount_on_random_walks() {
        use rand::rngs::StdRng;
        use rand::{Rng, SeedableRng};
        for n in [4usize, 5] {
            let g = Graph::new(n);
            let tab = PredTable::new(&g);
            for seed in 0..4u64 {
                let mut rng = StdRng::seed_from_u64(seed);
                let mut st = SearchState::root(&g, Some(&tab));
                let mut child_path = SearchState::root(&g, Some(&tab));
                while st.cyc.r > 0 {
                    let options: Vec<(u32, u8)> = g.succs[st.cyc.cur as usize]
                        .iter()
                        .copied()
                        .filter(|&(q, _)| !st.cyc.visited.get(q as usize))
                        .collect();
                    let (q, w) = if options.is_empty() {
                        (
                            st.cyc.visited.first_clear(g.nfact).unwrap() as u32,
                            g.n as u8,
                        )
                    } else {
                        options[rng.gen_range(0..options.len())]
                    };
                    // `child` path: the beams' construction.
                    let mut visited = child_path.cyc.visited.clone();
                    visited.set(q as usize);
                    let ctx = child_path.cyc.parent_ctx(&g, &tab);
                    child_path = child_path.child(
                        &g,
                        q,
                        child_path.cyc.len + u32::from(w),
                        visited,
                        Cursor::Onto,
                        Some((&tab, &ctx)),
                    );
                    // In-place path.
                    st.advance(&g, q, u32::from(w), Some(&tab));
                    let scratch = SearchState::recount(
                        &g,
                        &st.cyc.visited,
                        st.cyc.cur,
                        st.cyc.len,
                        st.steps,
                        Some(&tab),
                    );
                    assert!(
                        st.counters_eq(&scratch),
                        "advance n={n} seed={seed} step={}\n  inc {}\n  ref {}",
                        st.steps,
                        st.counters(),
                        scratch.counters()
                    );
                    assert!(
                        child_path.counters_eq(&scratch),
                        "child n={n} seed={seed} step={}\n  inc {}\n  ref {}",
                        st.steps,
                        child_path.counters(),
                        scratch.counters()
                    );
                }
            }
        }
    }

    /// The [`Cursor::Keep`] transition (the two-ended beam's prepend:
    /// the current permutation stays standable while some other rank is
    /// visited) must reproduce the from-scratch residual terms too.
    #[test]
    fn keep_cursor_child_matches_recount_on_random_visits() {
        use rand::rngs::StdRng;
        use rand::{Rng, SeedableRng};
        for n in [4usize, 5] {
            let g = Graph::new(n);
            let tab = PredTable::new(&g);
            for seed in 0..6u64 {
                let mut rng = StdRng::seed_from_u64(seed);
                let mut st = SearchState::root(&g, Some(&tab));
                while st.cyc.r > 1 {
                    // Visit an arbitrary unvisited rank other than the
                    // current one, keeping `cur` where it is.
                    let unvis: Vec<u32> = (0..g.nfact as u32)
                        .filter(|&x| !st.cyc.visited.get(x as usize))
                        .collect();
                    let q = unvis[rng.gen_range(0..unvis.len())];
                    let mut visited = st.cyc.visited.clone();
                    visited.set(q as usize);
                    st = st.child(
                        &g,
                        q,
                        st.cyc.len + 1,
                        visited,
                        Cursor::Keep,
                        Some((&tab, &st.cyc.parent_ctx(&g, &tab))),
                    );
                    let scratch = SearchState::recount(
                        &g,
                        &st.cyc.visited,
                        st.cyc.cur,
                        st.cyc.len,
                        st.steps,
                        Some(&tab),
                    );
                    assert!(
                        st.counters_eq(&scratch),
                        "keep n={n} seed={seed} step={}\n  inc {}\n  ref {}",
                        st.steps,
                        st.counters(),
                        scratch.counters()
                    );
                }
            }
        }
    }
}
