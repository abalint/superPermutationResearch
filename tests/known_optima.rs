//! Integration tests against known minimal superpermutation lengths and
//! the admissibility of the cycle lower bound.

use superperm::beam::{
    beam_search, beam_search_capped, beam_search_cutoffs, beam_search_endgame_snapshot,
    beam_search_jittered, beam_search_multi_seeded, beam_search_multi_seeded_capped,
    beam_search_multi_seeded_endgame, beam_search_seeded, beam_search_stratified,
    beam_search_stratified_cutoffs, Bound, Jitter, Scorer, SnapshotCfg, Stratify,
};
use superperm::endgame::{solve_endgame, spell_path};
use superperm::graph::Graph;
use superperm::greedy::greedy;
use superperm::model::{Model, Target};
use superperm::rollout::{log_trajectory, run_rollouts, run_rollouts_guided, Guide};
use superperm::validate::validate;
use superperm::walk::Walk;

/// Greedy must hit the known optima 9 / 33 / 153 and produce genuine
/// superpermutations.
#[test]
fn greedy_hits_known_optima() {
    for (n, expected) in [(3usize, 9usize), (4, 33), (5, 153)] {
        let g = Graph::new(n);
        let r = greedy(&g);
        assert_eq!(r.len, expected, "greedy length for n={n}");
        assert_eq!(r.string.len(), expected);
        let v = validate(n, &r.string);
        assert!(v.complete, "greedy output for n={n} is not complete");
        assert_eq!(r.path.len(), g.nfact);
    }
}

/// n=6 is the first size where greedy is NOT optimal (best known: 872).
/// Greedy must produce exactly the sum-of-factorials construction, 873.
/// This pins the phase-2 baseline: any learned-score beam result at n=6
/// is measured against this number.
#[test]
fn greedy_n6_is_sum_of_factorials_873() {
    let g = Graph::new(6);
    let r = greedy(&g);
    assert_eq!(r.len, 873);
    assert!(validate(6, &r.string).complete);
}

#[test]
fn beam_n4_width_512_is_optimal_under_both_bounds() {
    let g = Graph::new(4);
    for bound in [Bound::Cycle, Bound::Arc] {
        let b = beam_search(&g, 512, Scorer::Bound(bound));
        assert_eq!(b.len, 33, "{bound:?}");
        assert!(validate(4, &b.string).complete, "{bound:?}");
        assert_eq!(b.path.len(), g.nfact, "{bound:?}");
        assert_eq!(b.path[0], 0, "{bound:?}");
    }
}

#[test]
fn beam_n5_width_2000_is_optimal_under_both_bounds() {
    let g = Graph::new(5);
    for bound in [Bound::Cycle, Bound::Arc] {
        let b = beam_search(&g, 2000, Scorer::Bound(bound));
        assert!(validate(5, &b.string).complete, "{bound:?}");
        assert_eq!(b.len, 153, "{bound:?}");
    }
}

/// At the fresh n=4 start state the bound must not exceed the true
/// remaining cost of an optimal solution (33 total − n already emitted).
#[test]
fn lower_bound_admissible_at_start_n4() {
    let g = Graph::new(4);
    let w = Walk::new(&g);
    assert!(w.lb() <= 33 - 4, "lb = {}", w.lb());
}

/// Along a recorded greedy trajectory (n=4, which greedy solves
/// optimally at 33), the bound never exceeds the cost actually still to
/// be paid — a spot-check of admissibility.
#[test]
fn lower_bound_never_exceeds_cost_to_go_on_greedy_trajectory_n4() {
    let g = Graph::new(4);
    let res = greedy(&g);
    let mut w = Walk::new(&g);
    assert_eq!(res.path[0], 0);
    for &next in &res.path[1..] {
        assert!(
            w.lb() <= res.len - w.len_chars(),
            "lb {} > remaining {} at len {}",
            w.lb(),
            res.len - w.len_chars(),
            w.len_chars()
        );
        // The arc bound must also be admissible, and dominate the
        // cycle bound.
        assert!(w.lb_arc() <= res.len - w.len_chars());
        assert!(w.lb_arc() >= w.lb());
        // Recover the edge weight: either a stored successor, or the
        // weight-n fallback (only taken when no successor was unvisited,
        // so the target is never in the successor list in that case).
        let wt = g.succs[w.cur as usize]
            .iter()
            .find(|&&(q, _)| q == next)
            .map(|&(_, wt)| wt)
            .unwrap_or(g.n as u8);
        w.advance(next, wt);
    }
    assert!(w.done());
    assert_eq!(w.len_chars(), res.len);
    assert_eq!(w.lb(), 0);
}

#[test]
fn validator_rejects_non_superperm() {
    let v = validate(3, "123121");
    assert!(!v.complete);
    assert_eq!(v.distinct, 3);
    assert_eq!(v.length, 6);
    // Right length, wrong content.
    let v = validate(3, "111111111");
    assert!(!v.complete);
    assert_eq!(v.distinct, 0);
}

/// Rollouts are deterministic for a fixed seed, emit n! lines per
/// rollout, and with epsilon = 0 reproduce the greedy baseline.
#[test]
fn rollouts_deterministic_and_consistent() {
    let g = Graph::new(4);

    let mut a = Vec::new();
    let sa = run_rollouts(&g, 5, 0.2, 42, &mut a).unwrap();
    let mut b = Vec::new();
    let sb = run_rollouts(&g, 5, 0.2, 42, &mut b).unwrap();
    assert_eq!(a, b, "same seed must give identical output");
    assert_eq!(sa.lines, 5 * g.nfact);
    assert_eq!(sa.min_len, sb.min_len);

    // Every line parses back into Features with consistent cost_to_go.
    let text = String::from_utf8(a).unwrap();
    let records: Vec<superperm::bound::Features> = text
        .lines()
        .map(|l| serde_json::from_str(l).unwrap())
        .collect();
    assert_eq!(records.len(), sa.lines);
    let first = &records[0];
    assert_eq!(first.step, 0);
    assert_eq!(first.n, 4);
    assert_eq!(first.r, 23);
    assert_eq!(first.len_so_far, 4);
    for chunk in records.chunks(g.nfact) {
        let final_len = chunk[0].len_so_far + chunk[0].cost_to_go;
        for f in chunk {
            assert_eq!(f.len_so_far + f.cost_to_go, final_len);
        }
        assert_eq!(chunk.last().unwrap().cost_to_go, 0);
        assert_eq!(chunk.last().unwrap().r, 0);
    }

    // epsilon = 0 is exactly greedy.
    let mut c = Vec::new();
    let sc = run_rollouts(&g, 1, 0.0, 0, &mut c).unwrap();
    assert_eq!(sc.min_len, greedy(&g).len);
}

/// Trajectory logging replays a recorded path into the same records the
/// rollout generator would emit: an epsilon-0 rollout and a logged
/// greedy path must produce byte-identical JSONL.
#[test]
fn log_trajectory_matches_epsilon0_rollout() {
    let g = Graph::new(4);
    let mut rollout_bytes = Vec::new();
    run_rollouts(&g, 1, 0.0, 0, &mut rollout_bytes).unwrap();
    let res = greedy(&g);
    let mut log_bytes = Vec::new();
    let lines = log_trajectory(&g, &res.path, &mut log_bytes).unwrap();
    assert_eq!(lines, g.nfact);
    assert_eq!(rollout_bytes, log_bytes);
}

/// A linear model whose only nonzero coefficient is lb_arc = 1.0 (bias
/// 0, alpha 1.0) computes exactly len + lb_arc, so the learned-scored
/// beam must reproduce the Bound::Arc beam bit for bit — same length
/// AND same path.
#[test]
fn learned_lb_arc_model_reproduces_arc_bound_beam() {
    let mut coef = [0.0f64; 8];
    coef[7] = 1.0; // lb_arc is the last feature in FEATURE_ORDER.
    for (n, width) in [(4usize, 512usize), (5, 2000)] {
        let g = Graph::new(n);
        let model = Model::Linear {
            n,
            coef: coef.to_vec(),
            bias: 0.0,
            target: Target::Absolute,
        };
        let by_bound = beam_search(&g, width, Scorer::Bound(Bound::Arc));
        let by_model = beam_search(
            &g,
            width,
            Scorer::Learned {
                model: &model,
                alpha: 1.0,
            },
        );
        assert_eq!(by_model.len, by_bound.len, "length differs at n={n}");
        assert_eq!(by_model.path, by_bound.path, "path differs at n={n}");
        assert_eq!(by_model.string, by_bound.string);
        assert!(validate(n, &by_model.string).complete);
    }
}

/// A residual-target model predicting a constant 0 scores exactly
/// len + lb_arc + 0, so the learned beam must reproduce the Bound::Arc
/// beam bit for bit (pins the residual score arithmetic).
#[test]
fn residual_zero_model_reproduces_arc_bound_beam() {
    for (n, width) in [(4usize, 512usize), (5, 2000)] {
        let g = Graph::new(n);
        let model = Model::Linear {
            n,
            coef: vec![0.0; 8],
            bias: 0.0,
            target: Target::Residual,
        };
        let by_bound = beam_search(&g, width, Scorer::Bound(Bound::Arc));
        let by_model = beam_search(
            &g,
            width,
            Scorer::Learned {
                model: &model,
                alpha: 1.0,
            },
        );
        assert_eq!(by_model.len, by_bound.len, "length differs at n={n}");
        assert_eq!(by_model.path, by_bound.path, "path differs at n={n}");
        assert_eq!(by_model.string, by_bound.string);
        assert!(validate(n, &by_model.string).complete);
    }
}

/// Model-guided rollouts: deterministic for a fixed seed, valid records,
/// and the absolute lb_arc model and the residual zero model score every
/// option identically (len + w + lb_arc), so their outputs must agree.
#[test]
fn guided_rollouts_deterministic_and_consistent() {
    let g = Graph::new(4);
    let mut coef = [0.0f64; 8];
    coef[7] = 1.0;
    let abs_model = Model::Linear {
        n: 4,
        coef: coef.to_vec(),
        bias: 0.0,
        target: Target::Absolute,
    };
    let res_model = Model::Linear {
        n: 4,
        coef: vec![0.0; 8],
        bias: 0.0,
        target: Target::Residual,
    };

    // Same seed => byte-identical, with and without exploration.
    for eps in [0.0, 0.1] {
        let guide = Guide {
            model: &abs_model,
            alpha: 1.0,
        };
        let mut a = Vec::new();
        let sa = run_rollouts_guided(&g, 3, eps, 7, Some(guide), &mut a).unwrap();
        let mut b = Vec::new();
        run_rollouts_guided(&g, 3, eps, 7, Some(guide), &mut b).unwrap();
        assert_eq!(a, b, "same seed must give identical output (eps={eps})");
        assert_eq!(sa.lines, 3 * g.nfact);

        // Every rollout completes with consistent cost_to_go labels.
        let text = String::from_utf8(a.clone()).unwrap();
        let records: Vec<superperm::bound::Features> = text
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .collect();
        for chunk in records.chunks(g.nfact) {
            let final_len = chunk[0].len_so_far + chunk[0].cost_to_go;
            for f in chunk {
                assert_eq!(f.len_so_far + f.cost_to_go, final_len);
            }
            assert_eq!(chunk.last().unwrap().cost_to_go, 0);
            assert_eq!(chunk.last().unwrap().r, 0);
        }

        // The residual zero model computes the same score for every
        // option, so it must pick identical moves.
        let mut c = Vec::new();
        run_rollouts_guided(
            &g,
            3,
            eps,
            7,
            Some(Guide {
                model: &res_model,
                alpha: 1.0,
            }),
            &mut c,
        )
        .unwrap();
        assert_eq!(a, c, "absolute lb_arc and residual zero must agree");
    }
}

/// Seed-prefix depth 0 must be bit-identical to the plain beam.
#[test]
fn seed_prefix_zero_is_identity() {
    let g = Graph::new(4);
    let plain = beam_search(&g, 512, Scorer::Bound(Bound::Arc));
    let seeded = beam_search_seeded(&g, 512, Scorer::Bound(Bound::Arc), None, 0);
    assert_eq!(seeded.len, plain.len);
    assert_eq!(seeded.path, plain.path);
    assert_eq!(seeded.string, plain.string);
}

/// A near-full greedy prefix leaves the beam only a few levels; the
/// result must still be a complete, valid superpermutation whose path
/// starts with the greedy prefix.
#[test]
fn seed_prefix_deep_n5_still_valid() {
    let g = Graph::new(5);
    let depth = g.nfact - 3; // 117 of 119 possible advances
    let b = beam_search_seeded(&g, 64, Scorer::Bound(Bound::Arc), None, depth);
    assert!(validate(5, &b.string).complete);
    assert_eq!(b.len, b.string.len());
    assert_eq!(b.path.len(), g.nfact);
    let greedy_path = greedy(&g).path;
    assert_eq!(b.path[..=depth], greedy_path[..=depth]);
}

/// A mid-depth greedy prefix must not cost the beam its n=5 optimum:
/// greedy itself reaches 153 at n=5, so the prefix lies on an optimal
/// path and width 2000 finds 153 from scratch already.
#[test]
fn seed_prefix_mid_depth_n5_width_2000_still_153() {
    let g = Graph::new(5);
    let b = beam_search_seeded(&g, 2000, Scorer::Bound(Bound::Cycle), None, 60);
    assert_eq!(b.len, 153);
    assert!(validate(5, &b.string).complete);
}

/// T2: `Composed` with `alpha = 0` must score bit-identically to the
/// bare bound, for every bound.
#[test]
fn composed_alpha_zero_matches_bound() {
    let g = Graph::new(5);
    let model = Model::Linear {
        n: 5,
        coef: vec![1.0; 11],
        bias: 0.5,
        target: Target::Absolute,
    };
    for bound in [Bound::Cycle, Bound::Arc, Bound::Residual] {
        let plain = beam_search(&g, 200, Scorer::Bound(bound));
        let comp = beam_search(
            &g,
            200,
            Scorer::Composed {
                bound,
                model: &model,
                alpha: 0.0,
            },
        );
        assert_eq!(comp.len, plain.len, "{bound:?}");
        assert_eq!(comp.path, plain.path, "{bound:?}");
        assert_eq!(comp.string, plain.string, "{bound:?}");
    }
}

/// T2: with a residual-target model, `Composed { bound: Arc }` uses the
/// same anchor (`len + lb_arc`) and the same prediction as `Learned`,
/// so the two scorers must be bit-identical.
#[test]
fn composed_arc_with_residual_model_matches_learned() {
    let g = Graph::new(5);
    let model = Model::Linear {
        n: 5,
        coef: vec![
            0.3, -0.2, 0.1, 0.05, -0.4, 0.7, 0.02, -0.03, 0.11, -0.07, 0.19,
        ],
        bias: 1.25,
        target: Target::Residual,
    };
    let learned = beam_search(
        &g,
        500,
        Scorer::Learned {
            model: &model,
            alpha: 0.8,
        },
    );
    let composed = beam_search(
        &g,
        500,
        Scorer::Composed {
            bound: Bound::Arc,
            model: &model,
            alpha: 0.8,
        },
    );
    assert_eq!(composed.len, learned.len);
    assert_eq!(composed.path, learned.path);
    assert_eq!(composed.string, learned.string);
}

/// T2 admissible cap: with the cap at the known optimum the beam must
/// still find it (pruning is lossless for completions within the cap);
/// with the cap one below the proven optimum the beam must die — a
/// `Some` there would contradict the proven bound.
#[test]
fn capped_beam_at_optimum_finds_and_below_optimum_dies() {
    let g = Graph::new(5);
    for bound in [Bound::Cycle, Bound::Arc, Bound::Residual] {
        let hit = beam_search_capped(&g, 2000, Scorer::Bound(bound), None, 0, None, 153);
        let b = hit.expect("cap at the optimum must still find 153");
        assert_eq!(b.len, 153, "{bound:?}");
        assert!(validate(5, &b.string).complete, "{bound:?}");
        let miss = beam_search_capped(&g, 2000, Scorer::Bound(bound), None, 0, None, 152);
        assert!(miss.is_none(), "{bound:?}: found < 153 — impossible");
    }
}

/// T2 cap composes with multi-seeding: greedy-prefix seeds at n=5 with
/// the cap at 153 must complete to exactly 153.
#[test]
fn capped_multi_seeded_beam_still_optimal_n5() {
    let g = Graph::new(5);
    let greedy_path = greedy(&g).path;
    let seeds: Vec<Vec<u32>> = vec![greedy_path[..=20].to_vec(), greedy_path[..=45].to_vec()];
    let b = beam_search_multi_seeded_capped(
        &g,
        2000,
        Scorer::Bound(Bound::Cycle),
        None,
        &seeds,
        None,
        153,
    )
    .expect("greedy-prefix seeds lie on an optimal path");
    assert_eq!(b.len, 153);
    assert!(validate(5, &b.string).complete);
}

/// T3 invariant: a one-walk seed list equal to the greedy prefix must
/// be bit-identical to `beam_search_seeded` with the same prefix depth
/// — same code path, same injection level, same arena layout.
#[test]
fn seed_file_single_greedy_walk_matches_seed_prefix() {
    let g = Graph::new(5);
    let greedy_path = greedy(&g).path;
    for depth in [1usize, 30, 60] {
        let walk = greedy_path[..=depth].to_vec();
        let multi = beam_search_multi_seeded(
            &g,
            256,
            Scorer::Bound(Bound::Cycle),
            None,
            std::slice::from_ref(&walk),
            None,
        );
        let seeded = beam_search_seeded(&g, 256, Scorer::Bound(Bound::Cycle), None, depth);
        assert_eq!(multi.len, seeded.len, "depth {depth}");
        assert_eq!(multi.path, seeded.path, "depth {depth}");
        assert_eq!(multi.string, seeded.string, "depth {depth}");
    }
}

/// T3: seeds of different lengths are injected at different levels; the
/// search must still complete every walk and return a valid optimum at
/// n=5 when one seed lies on the greedy (optimal) path.
#[test]
fn seed_file_mixed_depth_walks_n5_still_153() {
    let g = Graph::new(5);
    let greedy_path = greedy(&g).path;
    // Three prefixes of the optimal path plus a deliberately bad walk
    // (weight-4 fallback start: rank 0 then the second cycle's rep).
    let mut seeds: Vec<Vec<u32>> = [20usize, 40, 60]
        .iter()
        .map(|&d| greedy_path[..=d].to_vec())
        .collect();
    let far = (0..g.nfact as u32)
        .find(|&q| {
            q != 0
                && g.succs[0]
                    .iter()
                    .all(|&(s, w)| s != q || w >= g.n as u8 - 1)
        })
        .unwrap();
    seeds.push(vec![0, far]);
    let b = beam_search_multi_seeded(&g, 2000, Scorer::Bound(Bound::Cycle), None, &seeds, None);
    assert_eq!(b.len, 153);
    assert!(validate(5, &b.string).complete);
    assert_eq!(b.path.len(), g.nfact);
}

/// T3 + stratification + endgame snapshot compose: multi-seeded beam
/// with the records-style options must return a valid string and a
/// snapshot whose exact completions never beat the admissible bound's
/// floor (sanity, not strength).
#[test]
fn seed_file_endgame_snapshot_composes_n5() {
    let g = Graph::new(5);
    let greedy_path = greedy(&g).path;
    let seeds: Vec<Vec<u32>> = vec![greedy_path[..=40].to_vec(), greedy_path[..=50].to_vec()];
    let (b, snaps) = beam_search_multi_seeded_endgame(
        &g,
        512,
        Scorer::Bound(Bound::Cycle),
        None,
        &seeds,
        Some(Stratify {
            quota: 4,
            bucket: 1,
        }),
        SnapshotCfg {
            remaining: 12,
            top: 8,
        },
    );
    assert!(validate(5, &b.string).complete);
    assert!(!snaps.is_empty());
    for s in &snaps {
        assert_eq!(s.remaining.len(), 12);
        assert_eq!(s.path.len(), g.nfact - 12);
        let e = solve_endgame(&g, s.cur, &s.remaining);
        // exact completion appends >= 1 char per missing perm
        assert!(e.cost >= 12);
        if let Some(h) = s.best_descendant_len {
            assert!(s.len + e.cost <= h);
        }
    }
}

/// Jitter must not break correctness — it only reorders near-ties. At
/// n=4 the tie structure is loose enough that width 512 with a modest
/// jitter still finds the optimum, and the result must validate. With
/// jitter disabled (None, or eps = 0) the search must be bit-identical
/// to the unjittered API.
#[test]
fn jittered_beam_n4_still_optimal_and_zero_jitter_is_identity() {
    let g = Graph::new(4);
    let jittered = beam_search_jittered(
        &g,
        512,
        Scorer::Bound(Bound::Arc),
        Some(Jitter { eps: 0.5, seed: 1 }),
    );
    assert_eq!(jittered.len, 33);
    assert!(validate(4, &jittered.string).complete);

    let plain = beam_search(&g, 512, Scorer::Bound(Bound::Arc));
    for jit in [None, Some(Jitter { eps: 0.0, seed: 7 })] {
        let same = beam_search_jittered(&g, 512, Scorer::Bound(Bound::Arc), jit);
        assert_eq!(same.len, plain.len, "{jit:?}");
        assert_eq!(same.path, plain.path, "{jit:?}");
        assert_eq!(same.string, plain.string, "{jit:?}");
    }
}

/// The beam's returned path must replay to exactly the returned string.
#[test]
fn beam_path_replays_to_reported_length() {
    let g = Graph::new(4);
    let b = beam_search(&g, 512, Scorer::Bound(Bound::Arc));
    let mut bytes = Vec::new();
    log_trajectory(&g, &b.path, &mut bytes).unwrap();
    let text = String::from_utf8(bytes).unwrap();
    let last: superperm::bound::Features =
        serde_json::from_str(text.lines().last().unwrap()).unwrap();
    assert_eq!(last.len_so_far as usize, b.len);
    assert_eq!(last.cost_to_go, 0);
    assert_eq!(last.r, 0);
}

/// Tracing greedy's own output must reproduce greedy's path exactly:
/// same visit order (120 visits at n=5), a replay of the same length,
/// and a feature log byte-identical to the ε=0 rollout records.
#[test]
fn trace_of_greedy_n5_reproduces_greedy_path() {
    let g = Graph::new(5);
    let r = greedy(&g);
    let t = superperm::trace::trace_string(&g, &r.string).unwrap();
    assert_eq!(t.path, r.path);
    assert_eq!(t.path.len(), g.nfact);
    assert_eq!(t.input_len, 153);
    assert_eq!(t.replay_len, 153);
    // n + Σ w·hist[w] must reproduce the length.
    let weighted: usize = t.hist.iter().enumerate().map(|(w, c)| w * c).sum();
    assert_eq!(5 + weighted, 153);
    assert_eq!(t.hist.iter().sum::<usize>(), g.nfact - 1);

    let mut traced = Vec::new();
    log_trajectory(&g, &t.path, &mut traced).unwrap();
    let mut rolled = Vec::new();
    run_rollouts(&g, 1, 0.0, 0, &mut rolled).unwrap();
    assert_eq!(traced, rolled);
}

/// Trace must round-trip a downloaded community 872 record: complete,
/// 720 visits, replay length exactly 872 (no wasted characters), and
/// the identity start. Skips silently if the gitignored corpus is not
/// present.
#[test]
fn trace_roundtrips_downloaded_872_record() {
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("data/records872");
    let Ok(entries) = std::fs::read_dir(&dir) else {
        eprintln!("skipping: {} not present", dir.display());
        return;
    };
    let mut files: Vec<_> = entries
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension().is_some_and(|x| x == "txt")
                && p.file_name()
                    .is_some_and(|f| f.to_string_lossy().starts_with("872."))
        })
        .collect();
    files.sort();
    let Some(file) = files.first() else {
        eprintln!("skipping: no 872.*.txt files in {}", dir.display());
        return;
    };
    let s = std::fs::read_to_string(file).unwrap().trim().to_string();
    let g = Graph::new(6);
    let v = validate(6, &s);
    assert!(v.complete, "{} does not validate", file.display());
    assert_eq!(v.length, 872);
    let t = superperm::trace::trace_string(&g, &s).unwrap();
    assert_eq!(t.path.len(), 720);
    assert_eq!(t.input_len, 872);
    assert_eq!(t.replay_len, 872);
    assert_eq!(t.path[0], 0);
    assert_eq!(t.hist.iter().sum::<usize>(), 719);
}

/// Cutoff instrumentation must not change the search: same result as
/// the plain API, one record per level, kept ≤ width, and
/// best ≤ worst per level. Scores here are (len + lb) exactly, so the
/// last level's best score equals the final length.
#[test]
fn beam_cutoffs_are_pure_instrumentation() {
    let g = Graph::new(4);
    let plain = beam_search_seeded(&g, 64, Scorer::Bound(Bound::Arc), None, 0);
    let (instr, cuts) = beam_search_cutoffs(&g, 64, Scorer::Bound(Bound::Arc), None, 0);
    assert_eq!(instr.len, plain.len);
    assert_eq!(instr.path, plain.path);
    assert_eq!(instr.string, plain.string);
    assert_eq!(cuts.len(), g.nfact - 1);
    for (i, c) in cuts.iter().enumerate() {
        assert_eq!(c.level as usize, i + 1);
        assert!(c.kept >= 1 && c.kept <= 64);
        assert!(c.best_score <= c.worst_kept_score, "level {}", c.level);
    }
    // Final level: r = 0 ⇒ lb = 0 ⇒ best score = best final length.
    assert_eq!(cuts.last().unwrap().best_score, plain.len as f64);
}

/// score_trajectory along greedy must mirror the beam's score
/// arithmetic: with the arc bound it is len + lb_arc at every step.
#[test]
fn score_trajectory_matches_walk_bounds_on_greedy_n4() {
    let g = Graph::new(4);
    let r = greedy(&g);
    let scores = superperm::trace::score_trajectory(&g, &r.path, Scorer::Bound(Bound::Arc));
    assert_eq!(scores.len(), g.nfact);
    let mut w = Walk::new(&g);
    assert_eq!(scores[0], (0, 4, (4 + w.lb_arc()) as f64));
    for (i, &rank) in r.path[1..].iter().enumerate() {
        let p = &g.perms[w.cur as usize];
        let wt = (g.n - Graph::overlap(p, &g.perms[rank as usize])) as u8;
        w.advance(rank, wt);
        let expect = (w.len_chars() + w.lb_arc()) as f64;
        assert_eq!(scores[i + 1], (w.steps, w.len_chars() as u32, expect));
    }
}

/// The stratify-off beam is pinned bit-identical to the pre-stratification
/// beam: these exact output strings were captured from the build at commit
/// 9b03761 (before the stratified selection landed). If a refactor changes
/// them, the refactor broke bit-identity, not the test.
#[test]
fn stratify_off_is_bit_identical_to_pre_stratification_beam() {
    const N4_CYCLE: &str = "123412314231243121342132413214321";
    const N5_ARC: &str = "123451324513425134521354213524135214352134512341523412534123541231452\
                          314253142351423154231245312435124315243125432153421532415321453215432\
                          514325413254312";
    let n4_cycle: String = N4_CYCLE.into();
    let n5_arc: String = N5_ARC.split_whitespace().collect();
    let g4 = Graph::new(4);
    let b4 = beam_search(&g4, 512, Scorer::Bound(Bound::Cycle));
    assert_eq!(b4.string, n4_cycle);
    let g5 = Graph::new(5);
    let b5 = beam_search(&g5, 2000, Scorer::Bound(Bound::Arc));
    assert_eq!(b5.string, n5_arc);
    // stratify = None and quota = 0 take the same selection path.
    for strat in [
        None,
        Some(Stratify {
            quota: 0,
            bucket: 4,
        }),
    ] {
        let s4 = beam_search_stratified(&g4, 512, Scorer::Bound(Bound::Cycle), None, 0, strat);
        assert_eq!(s4.string, n4_cycle, "{strat:?}");
        assert_eq!(s4.path, b4.path, "{strat:?}");
        let s5 = beam_search_stratified(&g5, 2000, Scorer::Bound(Bound::Arc), None, 0, strat);
        assert_eq!(s5.string, n5_arc, "{strat:?}");
        assert_eq!(s5.path, b5.path, "{strat:?}");
    }
}

/// With stratification ON (default CLI parameterization: quota 32,
/// bucket 4) the beam gates still hold: n=4 width 512 → 33 and
/// n=5 width 2000 → 153 under both bounds, all outputs complete.
#[test]
fn stratified_beam_gates_still_optimal() {
    let strat = Some(Stratify {
        quota: 32,
        bucket: 4,
    });
    let g4 = Graph::new(4);
    for bound in [Bound::Cycle, Bound::Arc] {
        let b = beam_search_stratified(&g4, 512, Scorer::Bound(bound), None, 0, strat);
        assert_eq!(b.len, 33, "{bound:?}");
        assert!(validate(4, &b.string).complete, "{bound:?}");
    }
    let g5 = Graph::new(5);
    for bound in [Bound::Cycle, Bound::Arc] {
        let b = beam_search_stratified(&g5, 2000, Scorer::Bound(bound), None, 0, strat);
        assert_eq!(b.len, 153, "{bound:?}");
        assert!(validate(5, &b.string).complete, "{bound:?}");
    }
}

/// Stratified cutoff logging is pure instrumentation (same search), the
/// kept window covers the whole kept set (best ≤ worst), and the
/// reservation really keeps states a plain truncation would discard:
/// with a tiny width and a fine bucket key the stratified beam's kept
/// window at some level must extend beyond the plain beam's threshold.
#[test]
fn stratified_selection_reserves_beyond_plain_cutoff() {
    let g = Graph::new(5);
    let strat = Some(Stratify {
        quota: 4,
        bucket: 1,
    });
    let (b1, cuts) =
        beam_search_stratified_cutoffs(&g, 200, Scorer::Bound(Bound::Arc), None, 0, strat);
    let b2 = beam_search_stratified(&g, 200, Scorer::Bound(Bound::Arc), None, 0, strat);
    assert_eq!(b1.string, b2.string);
    assert_eq!(b1.path, b2.path);
    assert!(validate(5, &b1.string).complete);
    let (_, plain_cuts) = beam_search_cutoffs(&g, 200, Scorer::Bound(Bound::Arc), None, 0);
    assert_eq!(cuts.len(), plain_cuts.len());
    let mut widened = 0usize;
    for (c, p) in cuts.iter().zip(plain_cuts.iter()) {
        assert_eq!(c.level, p.level);
        assert!(c.best_score <= c.worst_kept_score, "level {}", c.level);
        assert!(c.kept <= 200);
        if c.worst_kept_score > p.worst_kept_score {
            widened += 1;
        }
    }
    assert!(
        widened > 0,
        "stratified selection never kept anything beyond the plain cutoff"
    );
}

/// The endgame snapshot must be pure instrumentation (bit-identical
/// beam result), and every snapshotted state's exact completion must
/// (a) dominate its own beam descendant (the exact endgame is optimal
/// from that state) and (b) respect the global optimum 153.
#[test]
fn endgame_snapshot_pure_and_exact_dominates_descendants_n5() {
    let g = Graph::new(5);
    let scorer = Scorer::Bound(Bound::Cycle);
    let plain = beam_search_stratified(&g, 2000, scorer, None, 0, None);
    // top = width captures the whole frontier, so the final winner's
    // ancestor is guaranteed to be among the snapshots.
    let cfg = SnapshotCfg {
        remaining: 15,
        top: 2000,
    };
    let (instr, snaps) = beam_search_endgame_snapshot(&g, 2000, scorer, None, 0, None, cfg);
    assert_eq!(instr.len, plain.len);
    assert_eq!(instr.path, plain.path);
    assert_eq!(instr.string, plain.string);
    assert_eq!(plain.len, 153);
    assert!(!snaps.is_empty() && snaps.len() <= 2000);
    let mut totals = Vec::with_capacity(snaps.len());
    for (i, s) in snaps.iter().enumerate() {
        assert_eq!(s.score_rank, i);
        assert_eq!(s.path.len(), g.nfact - 15);
        assert_eq!(s.remaining.len(), 15);
        // The stored path spells to exactly `len` chars.
        assert_eq!(spell_path(&g, &s.path).len(), s.len as usize);
        let e = solve_endgame(&g, s.cur, &s.remaining);
        let exact = s.len + e.cost;
        assert!(exact >= 153, "rank {i}: exact {exact} < optimum");
        if let Some(h) = s.best_descendant_len {
            assert!(
                exact <= h,
                "rank {i}: exact {exact} worse than heuristic descendant {h}"
            );
        }
        // Recomposed exact string is a valid complete superpermutation.
        let mut path = s.path.clone();
        path.extend_from_slice(&e.order);
        let full = spell_path(&g, &path);
        assert_eq!(full.len(), exact as usize);
        assert!(validate(5, &full).complete, "rank {i}");
        totals.push(exact);
    }
    // The beam finds 153, and its winner's ancestor is snapshotted, so
    // the best exact completion over the frontier is exactly 153.
    assert_eq!(totals.iter().min().copied().unwrap(), 153);
}
