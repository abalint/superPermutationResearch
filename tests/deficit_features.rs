//! Phase-3 item 3: deficit-distribution features (`half_open`,
//! `nearly_done`, `w2_bridges`) — end-to-end pins.
//!
//! Covers: beam-`State` vs `Walk` counter agreement along a real beam
//! path (through the exact fixed-point score at every level), JSONL
//! backward compatibility (old lines parse with the new fields
//! defaulting to 0), forward presence (new rollouts carry the fields),
//! and the model-contract versioning (an old 8-feature model file —
//! including the committed boot1 — scores bit-identically to the
//! pre-phase-3 build; a zero-extended 11-feature model reproduces it
//! move for move).
//!
//! Since s64 P3 all fourteen counters and their update rules live in
//! one place (`superperm::state`), so this file is one of four drift
//! guards over that module, each walking a *real* search path of its
//! own engine and comparing against the from-scratch reference recount
//! (`SearchState::recount`):
//!
//! * here — `Walk` vs the beam's `State`, through the score (the
//!   learned-model encoding below) and through every admissible bound
//!   (`arcs`, `intact`, `door`, `long`, `k`, `r`);
//! * `state.rs` unit tests — the rules themselves, in-place vs child
//!   construction vs the two-ended `Cursor::Keep` transition;
//! * `beam2.rs` unit tests — every `State2` the two-ended beam builds
//!   (both move types), including the five counters `State2` used to
//!   drop entirely;
//! * `sojourn.rs` unit tests — every state the sojourn DFS expands.

use superperm::beam::{beam_search, beam_search_cutoffs, Bound, Scorer};
use superperm::bound::Features;
use superperm::graph::Graph;
use superperm::model::{Model, Target, FEATURE_ORDER, FEATURE_ORDER_V2};
use superperm::rollout::{run_rollouts, run_rollouts_guided, Guide};
use superperm::state::SearchState;
use superperm::trace::score_trajectory;
use superperm::validate::validate;
use superperm::walk::Walk;

/// An 11-feature linear model whose prediction encodes exactly the
/// three deficit-distribution counters with distinct place values:
/// `pred = half_open + 1000·nearly_done + 1_000_000·w2_bridges`.
fn counter_encoding_model(n: usize) -> Model {
    let mut coef = vec![0.0f64; 11];
    coef[8] = 1.0; // half_open
    coef[9] = 1000.0; // nearly_done
    coef[10] = 1_000_000.0; // w2_bridges
    Model::Linear {
        n,
        coef,
        bias: 0.0,
        target: Target::Absolute,
    }
}

/// Walk-vs-beam-State consistency: run a width-1 beam (each level keeps
/// exactly one state, so the result path visits exactly the kept
/// states) scored by a model that encodes the three new counters with
/// distinct place values, then replay the result path through a `Walk`
/// (`score_trajectory` / `score_state`) and require the identical
/// fixed-point score at every level. Any divergence between the beam's
/// incremental counters (`child_state` / `score_move` / seed replay)
/// and the `Walk`'s (oracle-tested in `walk.rs`) would change the score
/// at that level.
#[test]
fn beam_state_counters_agree_with_walk_replay_at_every_step() {
    for (n, seed_prefix) in [(4usize, 0usize), (5, 0), (5, 40)] {
        let g = Graph::new(n);
        let model = counter_encoding_model(n);
        let scorer = Scorer::Learned {
            model: &model,
            alpha: 1.0,
        };
        let (b, cuts) = beam_search_cutoffs(&g, 1, scorer, None, seed_prefix);
        assert!(
            validate(n, &b.string).complete,
            "n={n} prefix={seed_prefix}"
        );
        let traj = score_trajectory(&g, &b.path, scorer);
        assert_eq!(traj.len(), g.nfact);
        assert_eq!(cuts.len(), g.nfact - 1 - seed_prefix);
        for c in &cuts {
            let (step, _len, walk_score) = traj[c.level as usize];
            assert_eq!(step, c.level, "n={n} prefix={seed_prefix}");
            assert_eq!(
                walk_score, c.best_score,
                "n={n} prefix={seed_prefix} level={}: beam State counters \
                 disagree with Walk replay",
                c.level
            );
        }
        // Terminal state: all three counters are 0, so the score is the
        // plain final length.
        assert_eq!(cuts.last().unwrap().best_score, b.len as f64);
    }
}

/// The same Walk-vs-beam-`State` pin through every admissible bound
/// (s64 P3): a width-1 beam scored by `len + lb` visits exactly the
/// states it keeps, and replaying its path through a `Walk` must
/// reproduce the identical fixed-point score at every level. Each bound
/// reads a different subset of the shared counters — `Cycle` reads
/// `k`/`r`, `Arc` reads `arcs`, `Residual` reads `door`/`intact`/`long`
/// — so a divergence between the beam's cached counters and the walk's
/// shows up here for all of them, not just the three deficit features.
#[test]
fn beam_state_bound_counters_agree_with_walk_replay_at_every_step() {
    for (n, seed_prefix) in [(4usize, 0usize), (5, 0), (5, 40)] {
        let g = Graph::new(n);
        for bound in [Bound::Cycle, Bound::Arc, Bound::Residual] {
            let scorer = Scorer::Bound(bound);
            let (b, cuts) = beam_search_cutoffs(&g, 1, scorer, None, seed_prefix);
            assert!(validate(n, &b.string).complete, "n={n} bound={bound:?}");
            let traj = score_trajectory(&g, &b.path, scorer);
            assert_eq!(cuts.len(), g.nfact - 1 - seed_prefix);
            for c in &cuts {
                let (step, _len, walk_score) = traj[c.level as usize];
                assert_eq!(step, c.level, "n={n} bound={bound:?}");
                assert_eq!(
                    walk_score, c.best_score,
                    "n={n} prefix={seed_prefix} bound={bound:?} level={}: beam \
                     State counters disagree with Walk replay",
                    c.level
                );
            }
            assert_eq!(cuts.last().unwrap().best_score, b.len as f64);
        }
    }
}

/// Direct counter-level pin (s64 P3): replaying a real beam path
/// through a `Walk` must reproduce the from-scratch reference recount
/// of all fourteen counters at every step — the shared rules driven by
/// the walk, checked against the definitions.
#[test]
fn walk_replay_of_a_beam_path_matches_the_reference_recount() {
    for n in [4usize, 5] {
        let g = Graph::new(n);
        let b = beam_search(&g, 64, Scorer::Bound(Bound::Residual));
        let mut w = Walk::new(&g);
        for &q in &b.path[1..] {
            let wt = (n - Graph::overlap(&g.perms[w.cur() as usize], &g.perms[q as usize])) as u8;
            w.advance(q, wt);
            let scratch = SearchState::recount(
                &g,
                &w.st.cyc.visited,
                w.cur(),
                w.len_chars() as u32,
                w.steps(),
                Some(w.pred_table()),
            );
            assert!(
                w.st.counters_eq(&scratch),
                "n={n} step={}\n  walk {}\n  ref  {}",
                w.steps(),
                w.st.counters(),
                scratch.counters()
            );
        }
        assert_eq!(w.string(), b.string, "n={n}");
    }
}

/// Old JSONL lines (pre-phase-3, and even pre-phase-2 without the arc
/// fields) must still deserialize, with the absent fields reading 0.
#[test]
fn old_jsonl_lines_parse_with_default_zero_deficit_features() {
    // The documented phase-1 sample line (docs/ARCHITECTURE.md).
    let phase1 = r#"{"n":4,"step":0,"r":23,"cycles_remaining":6,"intact_cycles":5,"current_cycle_remaining":3,"len_so_far":4,"cost_to_go":29}"#;
    let f: Features = serde_json::from_str(phase1).unwrap();
    assert_eq!(f.arcs, 0);
    assert_eq!(f.succ1_unvisited, 0);
    assert_eq!(f.half_open, 0);
    assert_eq!(f.nearly_done, 0);
    assert_eq!(f.w2_bridges, 0);
    // A phase-2 line (arc fields present, deficit fields absent).
    let phase2 = r#"{"n":4,"step":1,"r":22,"cycles_remaining":6,"intact_cycles":4,"current_cycle_remaining":2,"arcs":6,"succ1_unvisited":1,"len_so_far":5,"cost_to_go":28}"#;
    let f: Features = serde_json::from_str(phase2).unwrap();
    assert_eq!(f.arcs, 6);
    assert_eq!(f.half_open, 0);
    assert_eq!(f.nearly_done, 0);
    assert_eq!(f.w2_bridges, 0);
}

/// Fresh rollout JSONL must carry the three new fields, with values
/// consistent with the start/terminal states.
#[test]
fn rollout_jsonl_carries_deficit_features() {
    let g = Graph::new(4);
    let mut bytes = Vec::new();
    run_rollouts(&g, 2, 0.2, 9, &mut bytes).unwrap();
    let text = String::from_utf8(bytes).unwrap();
    assert!(text.lines().next().unwrap().contains("\"w2_bridges\""));
    let records: Vec<Features> = text
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    for chunk in records.chunks(g.nfact) {
        let first = &chunk[0];
        assert_eq!(
            (first.half_open, first.nearly_done, first.w2_bridges),
            (1, 0, 0)
        );
        let last = chunk.last().unwrap();
        assert_eq!(last.r, 0);
        assert_eq!(
            (last.half_open, last.nearly_done, last.w2_bridges),
            (0, 0, 0)
        );
        // Midgame states really exercise the counters.
        assert!(chunk.iter().any(|f| f.nearly_done > 0));
        assert!(chunk.iter().any(|f| f.half_open > 1));
    }
}

/// The committed boot1 model file (8-feature contract) must keep
/// loading, declare 8 consumed features, and predict the exact value it
/// produced before phase-3 item 3 (pinned constant), whether it is fed
/// the 8-feature prefix or the full 11-feature vector.
#[test]
fn committed_boot1_model_loads_and_scores_bit_identically() {
    let path =
        std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("ml/models/linear_n6_boot1.json");
    let m = Model::load(&path).unwrap();
    assert_eq!(m.n(), 6);
    assert_eq!(m.n_features(), 8);
    assert!(!m.is_residual());
    let x8 = [300.0, 70.0, 65.0, 3.0, 90.0, 1.0, 369.0, 389.0];
    let x11 = [
        300.0, 70.0, 65.0, 3.0, 90.0, 1.0, 369.0, 389.0, 17.0, 5.0, 42.0,
    ];
    // Pinned against the pre-phase-3 build (same serde_json parsing,
    // same coefficients, same left-to-right accumulation): if this
    // constant changes, predict's arithmetic changed and old models no
    // longer score bit-identically.
    let expected = f64::from_bits(0x4075624864435bd5); // 342.1426737433624
    assert_eq!(m.predict(&x8), expected);
    assert_eq!(m.predict(&x11), expected);
}

/// An 8-feature model and its zero-extended 11-feature twin must drive
/// the learned beam to bit-identical results (both reproducing the
/// arc-bound beam, since the lone nonzero coefficient encodes lb_arc):
/// pins that the appended features enter the score path append-only.
#[test]
fn zero_extended_v2_model_matches_v1_model_bitwise() {
    let mut coef8 = vec![0.0f64; 8];
    coef8[7] = 1.0;
    let mut coef11 = vec![0.0f64; 11];
    coef11[7] = 1.0;
    for (n, width) in [(4usize, 512usize), (5, 2000)] {
        let g = Graph::new(n);
        let m8 = Model::Linear {
            n,
            coef: coef8.clone(),
            bias: 0.0,
            target: Target::Absolute,
        };
        let m11 = Model::Linear {
            n,
            coef: coef11.clone(),
            bias: 0.0,
            target: Target::Absolute,
        };
        let by_bound = beam_search(&g, width, Scorer::Bound(Bound::Arc));
        for m in [&m8, &m11] {
            let b = beam_search(
                &g,
                width,
                Scorer::Learned {
                    model: m,
                    alpha: 1.0,
                },
            );
            assert_eq!(b.len, by_bound.len, "n={n} dims={}", m.n_features());
            assert_eq!(b.path, by_bound.path, "n={n} dims={}", m.n_features());
            assert_eq!(b.string, by_bound.string, "n={n} dims={}", m.n_features());
        }
    }
}

/// Guided rollouts with the v1 lb_arc model and its zero-extended v2
/// twin must emit byte-identical JSONL (pins `child_features`' extended
/// vector: the appended entries must not perturb old-model guidance).
#[test]
fn guided_rollouts_agree_between_v1_and_zero_extended_v2_models() {
    let g = Graph::new(4);
    let mut coef8 = vec![0.0f64; 8];
    coef8[7] = 1.0;
    let mut coef11 = vec![0.0f64; 11];
    coef11[7] = 1.0;
    let m8 = Model::Linear {
        n: 4,
        coef: coef8,
        bias: 0.0,
        target: Target::Absolute,
    };
    let m11 = Model::Linear {
        n: 4,
        coef: coef11,
        bias: 0.0,
        target: Target::Absolute,
    };
    for eps in [0.0, 0.1] {
        let mut a = Vec::new();
        run_rollouts_guided(
            &g,
            3,
            eps,
            7,
            Some(Guide {
                model: &m8,
                alpha: 1.0,
            }),
            &mut a,
        )
        .unwrap();
        let mut b = Vec::new();
        run_rollouts_guided(
            &g,
            3,
            eps,
            7,
            Some(Guide {
                model: &m11,
                alpha: 1.0,
            }),
            &mut b,
        )
        .unwrap();
        assert_eq!(a, b, "eps={eps}");
    }
}

/// The two contract versions are append-only: v2 extends v1 exactly.
#[test]
fn feature_order_v2_extends_v1_append_only() {
    assert_eq!(&FEATURE_ORDER_V2[..8], &FEATURE_ORDER[..]);
    assert_eq!(
        &FEATURE_ORDER_V2[8..],
        &["half_open", "nearly_done", "w2_bridges"]
    );
}
