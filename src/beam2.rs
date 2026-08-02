//! Two-ended (deque) beam search — the phase-3 decision-order probe.
//!
//! An append-only search must commit to the string's *front* first, with
//! zero information; records and LKH-style optimizers effectively decide
//! positions in an information-rich order. This searcher decouples
//! decision order from string position: a state is a *deque*
//! `(front, back, visited, len)` — the string built so far runs
//! `front → … → back` — and a move either APPENDS an unvisited
//! successor of `back` (back moves onto it) or PREPENDS an unvisited
//! predecessor of `front` (front moves onto it), paying the edge weight
//! in characters either way. The string's middle can be decided early
//! and its two ends late; blind decisions are relocated, not eliminated
//! (ROADMAP phase 3, item 2).
//!
//! Structure mirrors [`crate::beam`]: level-synchronous (every level
//! visits exactly one more permutation), candidate scores computed in
//! O(1) from parent counters without materializing children, per-level
//! sort + keep-first dedup + width truncation, path arena. Differences:
//!
//! * moves are `(rank, prepend?)`; predecessor lists come from
//!   [`Preds`] (built once per search, the mirror of `Graph::succs`);
//! * the dedup key is `(front, back, visited)` — states with equal
//!   visited sets but different ends are genuinely distinct — and every
//!   score is a pure function of `(front, back, visited, len)`, which
//!   the keep-first dedup argument relies on;
//! * the admissible score is the two-ended arc bound
//!   [`lower_bound_arc2`]: `len + max(r, r + arcs − [succ1(back)
//!   unvisited] − [pred1(front) unvisited])` (proof sketch in
//!   [`crate::bound`]'s module docs);
//! * the weight-`n` fallback (append to the lowest unvisited rank)
//!   fires only when *both* ends are stuck. As in the one-ended beam
//!   the fallback target provably has overlap 0 with `back` (every
//!   positive-overlap successor of `back` is visited when the append
//!   side is stuck), so tracked lengths stay exact.
//!
//! [`Scorer2::Learned`] is a *transfer experiment*: it feeds the
//! one-ended 8-feature contract — computed relative to `back`, the
//! appending end — to a model trained on one-ended rollouts. The
//! features stay pure functions of `(back, visited)`, so dedup remains
//! sound, but nothing in the training distribution matches prepend
//! dynamics; treat results accordingly.
//!
//! Counters (s64 P3): states carry the shared
//! [`crate::state::SearchState`], whose `cur` is this searcher's
//! `back`, so all fourteen counters — the deficit triple and the
//! residual `door`/`long` terms included — are maintained here for the
//! first time. A prepend visits a rank *without* moving the appending
//! end, which is [`crate::state::Cursor::Keep`]; the counters that
//! depend only on the visited set are unaffected by the distinction,
//! and the residual terms take the `child_terms_keeping_cur`
//! transition. None of the five recovered counters is read by any
//! scorer: this searcher's output is unchanged.

use std::collections::HashSet;
use std::collections::VecDeque;

use crate::beam::{splitmix64, splitmix64_mix, Jitter};
use crate::bitset::BitSet;
use crate::bound::lower_bound_arc2;
use crate::graph::{Graph, Preds};
use crate::lb_residual::{ParentCtx, PredTable};
use crate::model::Model;
use crate::state::{Cursor, SearchState};

/// How two-ended beam candidates are scored.
#[derive(Clone, Copy)]
pub enum Scorer2<'m> {
    /// `f = len + lb_arc2` (admissible two-ended arc bound).
    Arc2,
    /// Transfer experiment: `f = len + alpha * model.predict(one-ended
    /// features relative to back)` (`+ lb_arc` for residual-target
    /// models). The model was trained on append-only trajectories.
    ///
    /// Only 8-feature ([`crate::model::FEATURE_ORDER`]) models are
    /// supported. Since s64 P3 `State2` *does* maintain the phase-3
    /// deficit-distribution counters (`half_open`, `nearly_done`,
    /// `w2_bridges`) and the residual terms (`door`, `long`) — they come
    /// free with the shared [`crate::state::SearchState`] — but nothing
    /// scores with them yet: that refactor was parity-only, and
    /// switching this NO-GO probe (JOURNAL s7) to v2 or residual
    /// scoring is a deliberate change with its own measurement.
    /// [`beam2_search`] rejects v2 models with a clear panic; the CLI
    /// refuses them up front.
    Learned {
        /// Learned cost-to-go predictor (one-ended feature contract).
        model: &'m Model,
        /// Blend factor multiplying the prediction.
        alpha: f64,
    },
}

/// Precomputed jitter context for the two-ended beam: one Zobrist word
/// per rank plus the offset magnitude in fixed-point units. The offset
/// is a pure function of `(front, back, visited, seed)`.
struct Jitter2Ctx {
    zobrist: Vec<u64>,
    eps_fixed: f64,
}

impl Jitter2Ctx {
    fn new(j: Jitter, nfact: usize) -> Jitter2Ctx {
        let mut s = j.seed;
        let zobrist = (0..nfact).map(|_| splitmix64(&mut s)).collect();
        Jitter2Ctx {
            zobrist,
            eps_fixed: j.eps * 4096.0,
        }
    }

    /// Fixed-point offset in `[0, eps * 4096)` for the child state
    /// `(front, back, visited-hash)`. Front and back enter with
    /// different multipliers so mirrored states get independent offsets.
    #[inline]
    fn offset(&self, child_zhash: u64, front: u32, back: u32) -> i64 {
        let h = splitmix64_mix(
            child_zhash
                ^ u64::from(front).wrapping_mul(0x9E37_79B9_7F4A_7C15)
                ^ u64::from(back).wrapping_mul(0xC2B2_AE3D_27D4_EB4F),
        );
        let u = (h >> 11) as f64 / (1u64 << 53) as f64;
        (u * self.eps_fixed) as i64
    }
}

/// One two-ended beam state: a deque walk `front → … → back`.
///
/// The counters live in the shared [`SearchState`] (s64 P3), whose
/// `cur` is this state's **back** — the appending end, relative to
/// which the one-ended quantities (`current_cycle_remaining`, the
/// residual `door`/`long` terms) are defined here, exactly as the
/// transfer feature vector of [`Scorer2::Learned`] already was. All 14
/// counters are now maintained, the phase-3 deficit triple and the
/// residual terms included; **none of the five that `State2` used to
/// drop is read by any scorer** — the two-ended probe's scoring is
/// unchanged (s64 P3 is parity-only).
struct State2 {
    /// The shared incremental counters; `st.cyc.cur` is `back`.
    st: SearchState,
    /// Rank of the permutation the string currently starts with.
    front: u32,
    /// Zobrist hash of the visited set (0 when jitter is off).
    zhash: u64,
    /// Index of this state's node in the path arena.
    node: u32,
}

impl State2 {
    /// Rank of the permutation the string currently ends with.
    #[inline]
    fn back(&self) -> u32 {
        self.st.cyc.cur
    }
}

/// Result of a two-ended beam run.
pub struct Beam2Result {
    /// Best complete superpermutation found, as ASCII digits.
    pub string: String,
    /// Its length in characters.
    pub len: usize,
    /// Ranks of the permutations in string order (front to back).
    pub path: Vec<u32>,
    /// Moves in decision order: `(rank, prepended?)`. The first entry is
    /// the start permutation `(0, false)`.
    pub moves: Vec<(u32, bool)>,
}

/// Run the two-ended beam search of the given `width` on `g` and return
/// the best complete superpermutation found. With `jitter = None` (or
/// `eps == 0`) the search is deterministic and jitter-free.
pub fn beam2_search(
    g: &Graph,
    width: usize,
    scorer: Scorer2,
    jitter: Option<Jitter>,
) -> Beam2Result {
    assert!(width >= 1, "beam width must be at least 1");
    if let Scorer2::Learned { model, .. } = scorer {
        assert!(
            model.n_features() <= crate::model::FEATURE_ORDER.len(),
            "beam2's transfer scorer supports only the 8-feature contract \
             (NO-GO probe, see Scorer2::Learned docs)"
        );
    }
    let nfact = g.nfact;
    let n = g.n;
    let preds = Preds::new(g);
    // The residual terms are maintained (never scored with — see
    // `State2`), so the in-neighbour table is always built.
    let tab = PredTable::new(g);
    let jctx = jitter
        .filter(|j| j.eps > 0.0)
        .map(|j| Jitter2Ctx::new(j, nfact));
    let jctx = jctx.as_ref();

    // Arena node 0 is the root (identity permutation, no parent). Each
    // node stores (parent, rank, prepended?).
    let mut arena: Vec<(u32, u32, bool)> = vec![(u32::MAX, 0, false)];

    let mut beam = vec![State2 {
        st: SearchState::root(g, Some(&tab)),
        front: 0,
        zhash: jctx.map_or(0, |j| j.zobrist[0]),
        node: 0,
    }];

    // Candidate = (score, len, prepend, rank, parent index in `beam`).
    let mut cands: Vec<(i64, u32, u8, u32, u32)> = Vec::new();

    for _depth in 1..nfact {
        cands.clear();
        // One residual-bound transition context per parent, shared by
        // all its append candidates (see [`ParentCtx`]).
        let ctxs: Vec<ParentCtx> = beam.iter().map(|s| s.st.cyc.parent_ctx(g, &tab)).collect();
        for (pi, s) in beam.iter().enumerate() {
            let mut any = false;
            for &(q, w) in &g.succs[s.back() as usize] {
                if s.st.cyc.visited.get(q as usize) {
                    continue;
                }
                any = true;
                cands.push(score_move2(
                    g, s, q, w as u32, false, pi as u32, scorer, jctx,
                ));
            }
            for &(p, w) in &preds.lists[s.front as usize] {
                if s.st.cyc.visited.get(p as usize) {
                    continue;
                }
                any = true;
                cands.push(score_move2(
                    g, s, p, w as u32, true, pi as u32, scorer, jctx,
                ));
            }
            if !any {
                // Both ends stuck: weight-n fallback append to the
                // lowest unvisited rank so the state never silently
                // dies. Its overlap with `back` is provably 0 (all
                // positive-overlap successors of `back` are visited).
                let q =
                    s.st.cyc
                        .visited
                        .first_clear(nfact)
                        .expect("state with r > 0 must have an unvisited perm")
                        as u32;
                cands.push(score_move2(
                    g, s, q, n as u32, false, pi as u32, scorer, jctx,
                ));
            }
        }

        // Deterministic total order: (score, len, prepend, rank,
        // parent). For duplicate (front, back, visited) keys the bound,
        // every learned feature, and the jitter offset are identical
        // (all are pure functions of (front, back, visited)), so the
        // score differs only through len and keep-first after this sort
        // keeps the minimum length.
        cands.sort_unstable();

        let mut seen: HashSet<(u32, u32, BitSet)> =
            HashSet::with_capacity(width.min(cands.len()) * 2);
        let mut next: Vec<State2> = Vec::with_capacity(width.min(cands.len()));
        for &(_score, len, prepend, x, pi) in cands.iter() {
            if next.len() >= width {
                break;
            }
            let prepend = prepend != 0;
            let parent = &beam[pi as usize];
            let (front, back) = if prepend {
                (x, parent.back())
            } else {
                (parent.front, x)
            };
            let mut visited = parent.st.cyc.visited.clone();
            visited.set(x as usize);
            let key = (front, back, visited);
            if seen.contains(&key) {
                continue;
            }
            let visited = key.2.clone();
            seen.insert(key);
            let node = arena.len() as u32;
            arena.push((parent.node, x, prepend));
            // A prepend leaves the appending end (the shared state's
            // `cur`) where it is; an append moves it onto `x`.
            let cursor = if prepend { Cursor::Keep } else { Cursor::Onto };
            let child = State2 {
                st: parent
                    .st
                    .child(g, x, len, visited, cursor, Some((&tab, &ctxs[pi as usize]))),
                front,
                zhash: jctx.map_or(0, |j| parent.zhash ^ j.zobrist[x as usize]),
                node,
            };
            // Drift guard (s64 P3): in the library's own test build every
            // constructed child's counters are re-derived from scratch and
            // compared, so a wrong cursor or a wrong shared rule fails
            // immediately on a real two-ended search path — the `State2`
            // counterpart of the `Walk`-vs-beam pin in
            // `tests/deficit_features.rs`. Compiled out of every release
            // build (see the `counters_match_scratch_*` tests below).
            #[cfg(test)]
            {
                let scratch = SearchState::recount(
                    g,
                    &child.st.cyc.visited,
                    child.back(),
                    child.st.cyc.len,
                    child.st.steps,
                    Some(&tab),
                );
                assert!(
                    child.st.counters_eq(&scratch),
                    "beam2 State2 drift (prepend={prepend}, x={x})\n  inc {}\n  ref {}",
                    child.st.counters(),
                    scratch.counters()
                );
            }
            next.push(child);
        }
        beam = next;
    }

    let best = beam
        .iter()
        .min_by_key(|s| s.st.cyc.len)
        .expect("beam is never empty");
    debug_assert_eq!(best.st.cyc.r, 0);

    // Reconstruct the decision order from the arena, then replay it
    // into a deque to recover string order, then rebuild the string by
    // maximal-overlap concatenation.
    let mut moves = Vec::with_capacity(nfact);
    let mut node = best.node;
    while node != u32::MAX {
        let (parent, rank, prepend) = arena[node as usize];
        moves.push((rank, prepend));
        node = parent;
    }
    moves.reverse();

    let mut deque: VecDeque<u32> = VecDeque::with_capacity(nfact);
    deque.push_back(moves[0].0);
    for &(rank, prepend) in &moves[1..] {
        if prepend {
            deque.push_front(rank);
        } else {
            deque.push_back(rank);
        }
    }
    let path: Vec<u32> = deque.into_iter().collect();

    let mut chars: Vec<u8> = g.perms[path[0] as usize].clone();
    for pair in path.windows(2) {
        let p = &g.perms[pair[0] as usize];
        let q = &g.perms[pair[1] as usize];
        let t = Graph::overlap(p, q);
        chars.extend_from_slice(&q[t..]);
    }
    debug_assert_eq!(chars.len(), best.st.cyc.len as usize);

    Beam2Result {
        string: chars.iter().map(|&v| (b'0' + v) as char).collect(),
        len: chars.len(),
        path,
        moves,
    }
}

/// Score the deque move visiting `x` (append to `back` if `prepend` is
/// false, prepend to `front` otherwise) with edge weight `w`, in O(1)
/// from the parent's counters and without cloning. Scores are `i64`
/// fixed-point with 12 fractional bits, exactly like the one-ended beam.
///
/// Every quantity used here — the two-ended arc bound and all 8
/// transferred features — is a pure function of the child's
/// `(front, back, visited, len)`, which the keep-first dedup in
/// [`beam2_search`] relies on; the jitter offset is likewise a pure
/// function of `(front, back, visited, seed)`.
#[allow(clippy::too_many_arguments)]
#[inline]
fn score_move2(
    g: &Graph,
    parent: &State2,
    x: u32,
    w: u32,
    prepend: bool,
    parent_idx: u32,
    scorer: Scorer2,
    jctx: Option<&Jitter2Ctx>,
) -> (i64, u32, u8, u32, u32) {
    let st = &parent.st;
    let len = st.cyc.len + w;
    let r = st.cyc.r - 1;
    // Child-end indicators, accounting for x becoming visited.
    let succ1_back_unvis = |b: u32| {
        let sb = g.succ1(b);
        sb != x && !st.cyc.visited.get(sb as usize)
    };
    let pred1_front_unvis = |f: u32| {
        let pf = g.pred1[f as usize];
        pf != x && !st.cyc.visited.get(pf as usize)
    };
    let score = match scorer {
        Scorer2::Arc2 => {
            let lb = if r == 0 {
                0
            } else {
                let arcs = st.child_arcs(g, x);
                let (ind_b, ind_f) = if prepend {
                    // Child ends: front = x, back unchanged.
                    (succ1_back_unvis(parent.back()), pred1_front_unvis(x))
                } else {
                    // Child ends: front unchanged, back = x.
                    (succ1_back_unvis(x), pred1_front_unvis(parent.front))
                };
                lower_bound_arc2(r as usize, arcs as usize, ind_b, ind_f) as u32
            };
            i64::from(len + lb) << 12
        }
        Scorer2::Learned { model, alpha } => {
            // One-ended feature contract, computed relative to the
            // child's back (the appending end).
            let k = st.cyc.child_k(g, x);
            let intact = st.cyc.child_intact(g, x);
            let arcs = st.child_arcs(g, x);
            let (cur_rem, succ1_unvis) = if prepend {
                // back unchanged; x may share its cycle.
                (
                    st.cyc.child_rem_of(g, x, parent.back()),
                    u32::from(succ1_back_unvis(parent.back())),
                )
            } else {
                // back = x; x's own visit leaves rem_x − 1 in its cycle.
                (st.cyc.child_cur_rem(g, x), u32::from(succ1_back_unvis(x)))
            };
            let lb_cycle = if r == 0 {
                0
            } else {
                r + k - u32::from(cur_rem > 0)
            };
            let lb_arc = if r == 0 { 0 } else { r + arcs - succ1_unvis };
            let feats = [
                f64::from(r),
                f64::from(k),
                f64::from(intact),
                f64::from(cur_rem),
                f64::from(arcs),
                f64::from(succ1_unvis),
                f64::from(lb_cycle),
                f64::from(lb_arc),
            ];
            let pred = model.predict(&feats);
            let base = if model.is_residual() {
                len + lb_arc
            } else {
                len
            };
            ((f64::from(base) + alpha * pred) * 4096.0).round() as i64
        }
    };
    let score = match jctx {
        Some(j) => {
            let child_zhash = parent.zhash ^ j.zobrist[x as usize];
            let (front, back) = if prepend {
                (x, parent.back())
            } else {
                (parent.front, x)
            };
            score + j.offset(child_zhash, front, back)
        }
        None => score,
    };
    (score, len, u8::from(prepend), x, parent_idx)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Model, Target};
    use crate::validate::validate;

    /// Every counter `State2` maintains must equal a from-scratch
    /// recount at every state the two-ended beam constructs, on a real
    /// search path exercising both move types (append and prepend).
    ///
    /// The comparison itself runs inside `beam2_search` under
    /// `#[cfg(test)]`; these cases drive it. Before s64 P3 `State2`
    /// dropped five of the fourteen counters (`half_open`,
    /// `nearly_done`, `w2_bridges`, `door`, `long`) and had no drift
    /// test at all.
    #[test]
    fn counters_match_scratch_on_real_two_ended_paths() {
        for (n, width) in [(4usize, 64usize), (5, 24)] {
            let g = Graph::new(n);
            let r = beam2_search(&g, width, Scorer2::Arc2, None);
            assert!(validate(n, &r.string).complete, "n={n}");
            // Both move types must actually occur, or the drift guard
            // would only have seen appends.
            assert!(
                r.moves.iter().any(|&(_, p)| p),
                "n={n}: no prepend on the pinned path"
            );
            assert!(
                r.moves.iter().skip(1).any(|&(_, p)| !p),
                "n={n}: no append on the pinned path"
            );
        }
    }

    /// Same guard along a jittered path and a learned-scorer path (both
    /// reorder the frontier, so different states get constructed).
    #[test]
    fn counters_match_scratch_under_jitter_and_learned_scoring() {
        let g = Graph::new(4);
        beam2_search(
            &g,
            48,
            Scorer2::Arc2,
            Some(Jitter {
                eps: 0.05,
                seed: 11,
            }),
        );
        let mut coef = vec![0.0f64; 8];
        coef[7] = 1.0; // lb_arc
        coef[2] = 0.5; // intact
        let model = Model::Linear {
            n: 4,
            coef,
            bias: 0.0,
            target: Target::Absolute,
        };
        beam2_search(
            &g,
            48,
            Scorer2::Learned {
                model: &model,
                alpha: 1.0,
            },
            None,
        );
    }
}
