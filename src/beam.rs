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
//!
//! Optional deterministic score [`Jitter`] adds a pseudo-random offset
//! in `[0, eps)` length units to every candidate's fixed-point score,
//! computed as a pure function of the child's `(cur, visited)` via an
//! incrementally maintained Zobrist hash of the visited set — so the
//! keep-first dedup argument (score varies only through `len` for
//! duplicate keys) is preserved, while near-ties are reordered
//! differently per seed. With jitter disabled the score path is
//! bit-identical to the unjittered search.

use std::collections::{HashMap, HashSet};

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
    /// `f = len + alpha * model.predict(child features)` (phase 2), or
    /// `f = len + lb_arc + alpha * predict` for a residual-target model
    /// (the prediction is `cost_to_go − lb_arc`, so the anchor is added
    /// back).
    Learned {
        /// Learned cost-to-go predictor.
        model: &'m Model,
        /// Blend factor multiplying the prediction.
        alpha: f64,
    },
}

/// Width reservation per structural class (stratified beam, phase 3
/// item 1). Frontier candidates are bucketed by a deficit-profile key —
/// the quantized triple `(intact, half_open, nearly_done)` counting how
/// the unvisited mass is arranged across rotation cycles (untouched
/// cycles / cycles with exactly 1–2 visited members / cycles with
/// exactly 1–2 unvisited members) — and each occupied bucket is
/// guaranteed up to `quota` of its best candidates before the remaining
/// width is filled in global score order. Record-like states (many
/// half-open cycles, penalized by the learned features — JOURNAL s5)
/// therefore cannot be crowded out of the beam by greedy-like ones.
///
/// Within buckets candidates are still taken in the global
/// `(score, len, succ, parent)` order and dedup is unchanged, so the
/// keep-first minimum-length argument is preserved. `quota = 0` keeps
/// nothing in the reservation pass and is bit-identical to the plain
/// beam.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Stratify {
    /// Kept slots reserved per occupied bucket (its best candidates by
    /// global score order). 0 = reservation off (plain beam).
    pub quota: usize,
    /// Quantization granularity: each of the three counts is divided by
    /// this (≥ 1) before forming the bucket key. Larger = coarser =
    /// fewer buckets.
    pub bucket: usize,
}

/// Endgame-snapshot request (phase-3 item 4): capture the top frontier
/// states at the level where exactly `remaining` permutations are left,
/// so the caller can solve their endgames exactly with
/// [`crate::endgame::solve_endgame`]. Pure instrumentation: the search
/// is bit-identical to the un-snapshotted run.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SnapshotCfg {
    /// Snapshot when exactly this many permutations are unvisited
    /// (`1 ..= n! − 1 − seed_prefix`).
    pub remaining: usize,
    /// How many frontier states to capture, in score order from the
    /// best (capped by the frontier size).
    pub top: usize,
}

/// One captured frontier state (see [`SnapshotCfg`]).
pub struct SnapState {
    /// Characters emitted so far.
    pub len: u32,
    /// Rank of the permutation the walk currently ends with.
    pub cur: u32,
    /// First-visit rank path from the root (starts with rank 0).
    pub path: Vec<u32>,
    /// Unvisited ranks, ascending (`remaining.len() == cfg.remaining`).
    pub remaining: Vec<u32>,
    /// Position of this state in the frontier's score order (0 = best).
    pub score_rank: usize,
    /// Shortest final length among the beam's own descendants of this
    /// state (`None` if no descendant survived to the end) — the
    /// heuristic completion the exact endgame is compared against.
    pub best_descendant_len: Option<u32>,
    /// Arena node, for the descendant mapping.
    node: u32,
}

/// Deterministic score jitter for diversified restarts.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Jitter {
    /// Offset magnitude in length units; each candidate gets a
    /// pseudo-random offset in `[0, eps)` added to its score.
    pub eps: f64,
    /// Seed of the Zobrist table; different seeds give independent
    /// tie-break orderings.
    pub seed: u64,
}

/// SplitMix64 step: advances `state` and returns the next output.
#[inline]
pub(crate) fn splitmix64(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
    splitmix64_mix(*state)
}

/// SplitMix64 finalizer: bijective 64-bit mix.
#[inline]
pub(crate) fn splitmix64_mix(z: u64) -> u64 {
    let z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    let z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

/// Precomputed jitter context: one Zobrist random word per rank plus
/// the offset magnitude prescaled to fixed-point units.
struct JitterCtx {
    /// Per-rank random words; XOR of the visited ranks' words is a pure
    /// function of the visited set (maintained incrementally).
    zobrist: Vec<u64>,
    /// `eps * 4096.0`: offset range in fixed-point score units.
    eps_fixed: f64,
}

impl JitterCtx {
    fn new(j: Jitter, nfact: usize) -> JitterCtx {
        let mut s = j.seed;
        let zobrist = (0..nfact).map(|_| splitmix64(&mut s)).collect();
        JitterCtx {
            zobrist,
            eps_fixed: j.eps * 4096.0,
        }
    }

    /// Fixed-point offset in `[0, eps * 4096)` for the child reached by
    /// visiting `q` from a parent whose visited-set hash is `zhash`.
    /// Pure function of the child's `(cur, visited)` (and the seed).
    #[inline]
    fn offset(&self, zhash: u64, q: u32) -> i64 {
        let child = zhash ^ self.zobrist[q as usize];
        let h = splitmix64_mix(child ^ u64::from(q).wrapping_mul(0x9E37_79B9_7F4A_7C15));
        // Top 53 bits -> uniform f64 in [0, 1).
        let u = (h >> 11) as f64 / (1u64 << 53) as f64;
        (u * self.eps_fixed) as i64
    }
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
    /// Cycles with exactly 1 or 2 visited members
    /// (`cycle_rem ∈ {n−1, n−2}`) — the "half-open" cycles the record
    /// walks keep alive via w2 moves (JOURNAL s5).
    half_open: u32,
    /// Cycles with exactly 1 or 2 unvisited members
    /// (`cycle_rem ∈ {1, 2}`) — nearly done.
    nearly_done: u32,
    /// Live cross-cycle weight-2 edges joining two partially-visited
    /// cycles (see [`crate::graph::Graph::w2_bridges_delta`] for the
    /// exact definition; phase-3 item 3). Pure function of the visited
    /// set.
    w2_bridges: u32,
    /// Zobrist hash of the visited set (0 when jitter is off).
    zhash: u64,
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

/// Per-level pruning summary recorded by [`beam_search_cutoffs`].
/// Scores are the beam's fixed-point scores divided by 4096, so they
/// compare exactly with [`crate::trace::score_state`].
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LevelCutoff {
    /// Level = number of moves the surviving states have taken (their
    /// trajectory step); runs `1 + seed_prefix ..= n! − 1`.
    pub level: u32,
    /// States kept (≤ width; can be smaller after dedup).
    pub kept: u32,
    /// Score of the best surviving state.
    pub best_score: f64,
    /// Score of the worst surviving state — the pruning threshold: a
    /// generated candidate scoring above this was discarded (candidates
    /// at exactly this score may survive or not depending on the
    /// `(len, succ, parent)` tie-break).
    pub worst_kept_score: f64,
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

/// Materialize the child state reached by visiting `q` from `parent`.
/// `visited` is the already-cloned parent set with bit `q` set, `len`
/// the child's length, `node` its already-pushed arena node. All
/// counters update in O(1) from the parent's (`parent.visited` itself
/// still excludes `q`, as `child_arcs` requires).
fn child_state(
    g: &Graph,
    parent: &State,
    q: u32,
    len: u32,
    visited: BitSet,
    node: u32,
    jctx: Option<&JitterCtx>,
) -> State {
    let arcs = child_arcs(g, parent, q);
    let w2_bridges = (parent.w2_bridges as i64
        + g.w2_bridges_delta(&parent.visited, &parent.cycle_rem, q)) as u32;
    let mut cycle_rem = parent.cycle_rem.clone();
    let cid = g.cycle_id[q as usize] as usize;
    let rem = cycle_rem[cid] as usize;
    let intact = parent.intact - u32::from(rem == g.n);
    let half_open = parent.half_open + u32::from(rem == g.n) - u32::from(rem == g.n - 2);
    let nearly_done = parent.nearly_done + u32::from(rem == 3) - u32::from(rem == 1);
    cycle_rem[cid] -= 1;
    let k = parent.k - u32::from(cycle_rem[cid] == 0);
    State {
        cur: q,
        len,
        visited,
        cycle_rem,
        k,
        r: parent.r - 1,
        arcs,
        intact,
        half_open,
        nearly_done,
        w2_bridges,
        zhash: jctx.map_or(0, |j| parent.zhash ^ j.zobrist[q as usize]),
        node,
    }
}

/// Deficit-profile bucket key of the child reached by visiting `q` from
/// `parent`, in O(1) from the parent's counters: the triple
/// `(intact, half_open, nearly_done)` each divided by the granularity
/// `b`, packed into a `u64`. The three counts are pure functions of the
/// visited set alone, so duplicate `(cur, visited)` dedup keys always
/// land in the same bucket (the keep-first argument needs this).
#[inline]
fn bucket_key(g: &Graph, parent: &State, q: u32, b: u32) -> u64 {
    let n = g.n;
    let rem = parent.cycle_rem[g.cycle_id[q as usize] as usize] as usize;
    let intact = parent.intact - u32::from(rem == n);
    let half_open = parent.half_open + u32::from(rem == n) - u32::from(rem == n - 2);
    let nearly_done = parent.nearly_done + u32::from(rem == 3) - u32::from(rem == 1);
    (u64::from(intact / b) << 42) | (u64::from(half_open / b) << 21) | u64::from(nearly_done / b)
}

/// Run beam search of the given `width` on `g`, scoring candidates with
/// the chosen `scorer`, and return the best complete superpermutation
/// found.
pub fn beam_search(g: &Graph, width: usize, scorer: Scorer) -> BeamResult {
    beam_search_seeded(g, width, scorer, None, 0)
}

/// [`beam_search`] with optional deterministic score [`Jitter`]. With
/// `jitter = None` (or `eps == 0`) this is exactly `beam_search`: the
/// same code path, with no offset applied.
pub fn beam_search_jittered(
    g: &Graph,
    width: usize,
    scorer: Scorer,
    jitter: Option<Jitter>,
) -> BeamResult {
    beam_search_seeded(g, width, scorer, jitter, 0)
}

/// [`beam_search_jittered`] with the root state seeded by replaying the
/// first `seed_prefix` moves of the deterministic greedy path, so the
/// beam explores continuations of a known-good prefix. `seed_prefix = 0`
/// is bit-identical to the unseeded search. The reported result covers
/// the full string (prefix included).
pub fn beam_search_seeded(
    g: &Graph,
    width: usize,
    scorer: Scorer,
    jitter: Option<Jitter>,
    seed_prefix: usize,
) -> BeamResult {
    beam_search_impl(g, width, scorer, jitter, seed_prefix, None, None, None)
}

/// [`beam_search_seeded`] with optional width reservation per
/// structural class (see [`Stratify`]). `stratify = None` is
/// bit-identical to `beam_search_seeded` (same code path, no
/// reservation logic touched), as is `Some` with `quota = 0`.
pub fn beam_search_stratified(
    g: &Graph,
    width: usize,
    scorer: Scorer,
    jitter: Option<Jitter>,
    seed_prefix: usize,
    stratify: Option<Stratify>,
) -> BeamResult {
    beam_search_impl(g, width, scorer, jitter, seed_prefix, stratify, None, None)
}

/// [`beam_search_stratified`] that additionally captures the top
/// `cfg.top` frontier states at the level where exactly `cfg.remaining`
/// permutations are unvisited (see [`SnapshotCfg`]). Pure
/// instrumentation: the returned [`BeamResult`] is bit-identical to the
/// un-snapshotted run; the snapshot is what the exact endgame tablebase
/// (phase-3 item 4) is solved from.
pub fn beam_search_endgame_snapshot(
    g: &Graph,
    width: usize,
    scorer: Scorer,
    jitter: Option<Jitter>,
    seed_prefix: usize,
    stratify: Option<Stratify>,
    cfg: SnapshotCfg,
) -> (BeamResult, Vec<SnapState>) {
    assert!(
        (1..g.nfact - seed_prefix).contains(&cfg.remaining),
        "snapshot remaining must be in 1..={} (got {})",
        g.nfact - 1 - seed_prefix,
        cfg.remaining
    );
    let mut snaps = Vec::new();
    let r = beam_search_impl(
        g,
        width,
        scorer,
        jitter,
        seed_prefix,
        stratify,
        None,
        Some((cfg, &mut snaps)),
    );
    (r, snaps)
}

/// [`beam_search_seeded`] that additionally records one [`LevelCutoff`]
/// per level. Pure instrumentation: the search itself is bit-identical
/// to the uninstrumented run.
pub fn beam_search_cutoffs(
    g: &Graph,
    width: usize,
    scorer: Scorer,
    jitter: Option<Jitter>,
    seed_prefix: usize,
) -> (BeamResult, Vec<LevelCutoff>) {
    beam_search_stratified_cutoffs(g, width, scorer, jitter, seed_prefix, None)
}

/// [`beam_search_stratified`] that additionally records one
/// [`LevelCutoff`] per level. Pure instrumentation: the search itself
/// is bit-identical to the uninstrumented run. Under stratification the
/// kept set is no longer a score-prefix of the candidate list, so
/// `worst_kept_score` is the maximum kept score (the window an outside
/// state would have to enter), not a sharp threshold.
pub fn beam_search_stratified_cutoffs(
    g: &Graph,
    width: usize,
    scorer: Scorer,
    jitter: Option<Jitter>,
    seed_prefix: usize,
    stratify: Option<Stratify>,
) -> (BeamResult, Vec<LevelCutoff>) {
    let mut cutoffs = Vec::new();
    let r = beam_search_impl(
        g,
        width,
        scorer,
        jitter,
        seed_prefix,
        stratify,
        Some(&mut cutoffs),
        None,
    );
    (r, cutoffs)
}

#[allow(clippy::too_many_arguments)]
fn beam_search_impl(
    g: &Graph,
    width: usize,
    scorer: Scorer,
    jitter: Option<Jitter>,
    seed_prefix: usize,
    stratify: Option<Stratify>,
    mut cutoffs: Option<&mut Vec<LevelCutoff>>,
    mut snapshot: Option<(SnapshotCfg, &mut Vec<SnapState>)>,
) -> BeamResult {
    assert!(width >= 1, "beam width must be at least 1");
    if let Some(st) = stratify {
        assert!(st.bucket >= 1, "stratify bucket granularity must be >= 1");
    }
    assert!(
        seed_prefix < g.nfact - 1,
        "seed prefix depth must be < n! - 1 = {} (got {seed_prefix})",
        g.nfact - 1
    );
    let nfact = g.nfact;
    let n = g.n;
    let jctx = jitter
        .filter(|j| j.eps > 0.0)
        .map(|j| JitterCtx::new(j, nfact));
    let jctx = jctx.as_ref();

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
            // ... and has exactly 1 visited member: half-open. It is
            // also nearly done iff n − 1 ≤ 2. Only one cycle is touched,
            // so no w2 bridge joins two touched cycles yet.
            half_open: 1,
            nearly_done: u32::from(n - 1 <= 2),
            w2_bridges: 0,
            zhash: jctx.map_or(0, |j| j.zobrist[0]),
            node: 0,
        }]
    };

    // Replay the greedy prefix through the same counter updates the
    // survivor loop applies, so the root state is exactly what the beam
    // would hold had it followed that path.
    if seed_prefix > 0 {
        let prefix = crate::greedy::greedy(g).path;
        let root = &mut beam[0];
        for &q in &prefix[1..=seed_prefix] {
            let w = (n - Graph::overlap(&g.perms[root.cur as usize], &g.perms[q as usize])) as u32;
            let arcs = child_arcs(g, root, q);
            let w2d = g.w2_bridges_delta(&root.visited, &root.cycle_rem, q);
            root.visited.set(q as usize);
            let cid = g.cycle_id[q as usize] as usize;
            let rem = root.cycle_rem[cid] as usize;
            root.intact -= u32::from(rem == n);
            root.half_open = root.half_open + u32::from(rem == n) - u32::from(rem == n - 2);
            root.nearly_done = root.nearly_done + u32::from(rem == 3) - u32::from(rem == 1);
            root.w2_bridges = (root.w2_bridges as i64 + w2d) as u32;
            root.cycle_rem[cid] -= 1;
            root.k -= u32::from(root.cycle_rem[cid] == 0);
            root.r -= 1;
            root.arcs = arcs;
            root.len += w;
            root.zhash = jctx.map_or(0, |j| root.zhash ^ j.zobrist[q as usize]);
            let node = arena.len() as u32;
            arena.push((root.node, q));
            root.node = node;
            root.cur = q;
        }
    }

    // Candidate = (score, len, succ, parent index in `beam`).
    let mut cands: Vec<(i64, u32, u32, u32)> = Vec::new();

    for depth in (1 + seed_prefix)..nfact {
        // Endgame snapshot: states at this point have visited `depth`
        // perms, so `nfact − depth` remain. Read-only capture — the
        // search below is untouched. The frontier is in global score
        // order (plain selection keeps the sorted candidate order;
        // stratified selection restores it), so `take(top)` is the top
        // of the score ranking.
        if let Some((cfg, out)) = snapshot.as_mut() {
            if nfact - depth == cfg.remaining {
                for (score_rank, s) in beam.iter().take(cfg.top).enumerate() {
                    let mut path = Vec::with_capacity(depth);
                    let mut node = s.node;
                    while node != u32::MAX {
                        let (parent, rank) = arena[node as usize];
                        path.push(rank);
                        node = parent;
                    }
                    path.reverse();
                    let remaining: Vec<u32> = (0..nfact as u32)
                        .filter(|&q| !s.visited.get(q as usize))
                        .collect();
                    out.push(SnapState {
                        len: s.len,
                        cur: s.cur,
                        path,
                        remaining,
                        score_rank,
                        best_descendant_len: None,
                        node: s.node,
                    });
                }
            }
        }
        cands.clear();
        for (pi, s) in beam.iter().enumerate() {
            let mut any = false;
            for &(q, w) in &g.succs[s.cur as usize] {
                if s.visited.get(q as usize) {
                    continue;
                }
                any = true;
                cands.push(score_move(g, s, q, w as u32, pi as u32, scorer, jctx));
            }
            if !any {
                // Weight-n fallback: jump to the lowest unvisited rank so
                // the state never silently dies.
                let q = s
                    .visited
                    .first_clear(nfact)
                    .expect("state with r > 0 must have an unvisited perm")
                    as u32;
                cands.push(score_move(g, s, q, n as u32, pi as u32, scorer, jctx));
            }
        }

        // Deterministic total order: (score, len, succ, parent). For
        // duplicate (cur, visited) keys the bound — and every learned
        // feature, hence the prediction, and the jitter offset (a hash
        // of exactly (cur, visited, seed)) — is identical (all depend
        // only on cur and visited), so the score differs only through
        // len (monotonically: +1 len is +4096 fixed-point, more than
        // any rounding) and keep-first after this sort keeps the
        // minimum length.
        cands.sort_unstable();

        let mut seen: HashSet<(u32, BitSet)> = HashSet::with_capacity(width.min(cands.len()) * 2);
        let mut next: Vec<State> = Vec::with_capacity(width.min(cands.len()));
        let mut best_kept: i64 = 0;
        let mut worst_kept: i64 = 0;
        match stratify {
            None | Some(Stratify { quota: 0, .. }) => {
                // Plain selection: global (score, len, succ, parent)
                // order, keep-first dedup, truncate to width.
                for &(score, len, q, pi) in cands.iter() {
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
                    let node = arena.len() as u32;
                    arena.push((parent.node, q));
                    if next.is_empty() {
                        best_kept = score;
                    }
                    worst_kept = score;
                    next.push(child_state(g, parent, q, len, visited, node, jctx));
                }
            }
            Some(st) => {
                // Stratified selection. Pass 1 (reservation): walk the
                // globally sorted candidates once, keeping up to
                // `quota` per occupied deficit-profile bucket — so a
                // bucket whose members all score badly still gets its
                // best `quota` states. Pass 2 (fill): walk again,
                // keeping everything not yet kept, until `width`. The
                // dedup set spans both passes, and within each pass
                // candidates arrive in global order, so the first kept
                // occurrence of any (cur, visited) key is still its
                // minimum-length one.
                let mut kept: Vec<(usize, State)> = Vec::with_capacity(width.min(cands.len()));
                let mut bucket_kept: HashMap<u64, usize> = HashMap::new();
                for (i, &(_score, len, q, pi)) in cands.iter().enumerate() {
                    if kept.len() >= width {
                        break;
                    }
                    let parent = &beam[pi as usize];
                    let bkey = bucket_key(g, parent, q, st.bucket as u32);
                    let count = bucket_kept.entry(bkey).or_insert(0);
                    if *count >= st.quota {
                        continue;
                    }
                    let mut visited = parent.visited.clone();
                    visited.set(q as usize);
                    let key = (q, visited);
                    if seen.contains(&key) {
                        continue;
                    }
                    let visited = key.1.clone();
                    seen.insert(key);
                    *count += 1;
                    let node = arena.len() as u32;
                    arena.push((parent.node, q));
                    kept.push((i, child_state(g, parent, q, len, visited, node, jctx)));
                }
                let pass1 = kept.len(); // entries 0..pass1 ascend by index
                let mut ki = 0;
                for (i, &(_score, len, q, pi)) in cands.iter().enumerate() {
                    if kept.len() >= width {
                        break;
                    }
                    if ki < pass1 && kept[ki].0 == i {
                        ki += 1; // already kept by the reservation pass
                        continue;
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
                    let node = arena.len() as u32;
                    arena.push((parent.node, q));
                    kept.push((i, child_state(g, parent, q, len, visited, node, jctx)));
                }
                // Restore global score order so the next level's
                // parent-index tie-break behaves exactly as if the beam
                // had been selected in one sorted pass.
                kept.sort_unstable_by_key(|&(i, _)| i);
                if let Some(&(i0, _)) = kept.first() {
                    best_kept = cands[i0].0;
                }
                if let Some(&(il, _)) = kept.last() {
                    worst_kept = cands[il].0;
                }
                next = kept.into_iter().map(|(_, s)| s).collect();
            }
        }
        if let Some(out) = cutoffs.as_deref_mut() {
            out.push(LevelCutoff {
                level: depth as u32,
                kept: next.len() as u32,
                best_score: best_kept as f64 / 4096.0,
                worst_kept_score: worst_kept as f64 / 4096.0,
            });
        }
        beam = next;
    }

    // Map each snapshotted state to the shortest final length among its
    // own beam descendants: every final state's ancestor at the
    // snapshot level is found by walking `remaining` arena steps up.
    if let Some((cfg, out)) = snapshot.as_mut() {
        if !out.is_empty() {
            let mut best_by_node: HashMap<u32, u32> = HashMap::new();
            for s in &beam {
                let mut node = s.node;
                for _ in 0..cfg.remaining {
                    node = arena[node as usize].0;
                }
                let e = best_by_node.entry(node).or_insert(u32::MAX);
                *e = (*e).min(s.len);
            }
            for st in out.iter_mut() {
                st.best_descendant_len = best_by_node.get(&st.node).copied();
            }
        }
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
/// parent's state, in O(1) from the parent's counters (O(n) when `q`
/// first touches an intact cycle — the `w2_bridges` scan). The score is
/// `i64` fixed-point with 12 fractional bits: `(len + lb) << 12` for
/// bound scoring (exactly the phase-1 ordering), or
/// `round((len + alpha * pred) * 4096)` for a learned model —
/// `round((len + lb_arc + alpha * pred) * 4096)` if the model is
/// residual-target — where `pred` is evaluated on the child's feature
/// vector (matching [`crate::model::FEATURE_ORDER_V2`]; an 8-feature
/// model reads only the [`crate::model::FEATURE_ORDER`] prefix, and the
/// appended deficit-distribution features are then not even computed,
/// so old models score bit-identically to the pre-phase-3 build)
/// computed here without materializing the child.
///
/// Both bounds and all learned features are pure functions of the
/// child's `(cur, visited, len)` (the three deficit-distribution
/// features depend on `visited` alone), which the keep-first dedup in
/// `beam_search` relies on. The optional jitter offset is likewise a
/// pure function of the child's `(cur, visited)` (via the parent's
/// incrementally maintained Zobrist hash), so it preserves that
/// invariant.
#[inline]
fn score_move(
    g: &Graph,
    parent: &State,
    q: u32,
    w: u32,
    parent_idx: u32,
    scorer: Scorer,
    jctx: Option<&JitterCtx>,
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
            // The appended deficit-distribution features (v2 contract)
            // are only computed when the model consumes them: an
            // 8-feature model must stay bit-identical to (and as fast
            // as) the pre-phase-3 build.
            let (half_open, nearly_done, w2_bridges) =
                if model.n_features() > crate::model::FEATURE_ORDER.len() {
                    let rem_n = rem as usize;
                    (
                        parent.half_open + u32::from(rem_n == g.n) - u32::from(rem_n == g.n - 2),
                        parent.nearly_done + u32::from(rem == 3) - u32::from(rem == 1),
                        (parent.w2_bridges as i64
                            + g.w2_bridges_delta(&parent.visited, &parent.cycle_rem, q))
                            as u32,
                    )
                } else {
                    (0, 0, 0)
                };
            let x = [
                f64::from(r),
                f64::from(k),
                f64::from(intact),
                f64::from(cur_rem),
                f64::from(arcs),
                f64::from(succ1_unvis),
                f64::from(lb_cycle),
                f64::from(lb_arc),
                f64::from(half_open),
                f64::from(nearly_done),
                f64::from(w2_bridges),
            ];
            let pred = model.predict(&x);
            // Residual models predict cost_to_go − lb_arc: add the
            // admissible anchor back. lb_arc is a pure function of
            // (cur, visited), so the dedup argument is unchanged.
            let base = if model.is_residual() {
                len + lb_arc
            } else {
                len
            };
            ((f64::from(base) + alpha * pred) * 4096.0).round() as i64
        }
    };
    let score = match jctx {
        Some(j) => score + j.offset(parent.zhash, q),
        None => score,
    };
    (score, len, q, parent_idx)
}
