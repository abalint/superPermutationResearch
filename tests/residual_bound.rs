//! Residual-graph admissible lower bound (`docs/RESIDUAL-BOUND-DESIGN.md`):
//! fast pins, plus the design doc's gates GA (admissibility) and GB
//! (strength) as `#[ignore]`d long runs.
//!
//! Run the gates with
//!
//! ```text
//! cargo test --release --test residual_bound -- --ignored --nocapture
//! ```

use superperm::beam::{beam_search, beam_search_endgame_snapshot, Bound, Scorer, SnapshotCfg};
use superperm::endgame::solve_endgame;
use superperm::graph::Graph;
use superperm::greedy::greedy;
use superperm::lb_residual::{
    door_scratch, heuristic_floor_not_admissible, long_scratch, PredTable,
};
use superperm::validate::validate;
use superperm::walk::Walk;

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

/// Advance `w` one step: greedy with probability `1 − eps`, otherwise a
/// uniformly random unvisited successor (weight-`n` fallback if stuck).
fn step(w: &mut Walk, rng: &mut StdRng, eps: f64) {
    let n = w.graph().n;
    let options = w.unvisited_succs();
    let (q, wt) = if options.is_empty() {
        (w.fallback_target(), n as u8)
    } else if rng.gen::<f64>() < eps {
        options[rng.gen_range(0..options.len())]
    } else {
        options[0]
    };
    w.advance(q, wt);
}

/// Exact optimal completion cost of `w`'s state (Held–Karp; `w.r` must
/// be within the tablebase's reach).
fn truth(w: &Walk) -> u32 {
    let g = w.graph();
    let remaining: Vec<u32> = (0..g.nfact as u32)
        .filter(|&x| !w.visited.get(x as usize))
        .collect();
    solve_endgame(g, w.cur, &remaining).cost
}

/// Replay a first-visit rank path into a fresh [`Walk`].
fn replay<'g>(g: &'g Graph, path: &[u32]) -> Walk<'g> {
    let mut w = Walk::new(g);
    for &q in &path[1..] {
        let wt = (g.n - Graph::overlap(&g.perms[w.cur as usize], &g.perms[q as usize])) as u8;
        w.advance(q, wt);
    }
    w
}

/// The beam scored by the residual bound must still reach the proven
/// optima, and the residual scorer must not disturb the other bounds.
#[test]
fn residual_beam_reaches_known_optima() {
    for (n, want) in [(3usize, 9usize), (4, 33), (5, 153)] {
        let g = Graph::new(n);
        let r = beam_search(&g, 200, Scorer::Bound(Bound::Residual));
        assert_eq!(r.len, want, "n={n}");
        assert!(validate(n, &r.string).complete, "n={n}");
        // Bit-identical default paths: the pre-existing bounds are
        // untouched by the new variant.
        let cyc = beam_search(&g, 200, Scorer::Bound(Bound::Cycle));
        let arc = beam_search(&g, 200, Scorer::Bound(Bound::Arc));
        assert_eq!(cyc.len, want, "n={n} cycle");
        assert_eq!(arc.len, want, "n={n} arc");
    }
}

/// Dominance over the arc bound (hence the cycle bound), incremental
/// counters against from-scratch recounts, and admissibility against the
/// exact tablebase on short tails — at every state of random walks.
#[test]
fn residual_dominates_and_is_admissible_small() {
    for n in [4usize, 5] {
        let g = Graph::new(n);
        let tab = PredTable::new(&g);
        for seed in 0..8u64 {
            let mut rng = StdRng::seed_from_u64(seed);
            let mut w = Walk::new(&g);
            while !w.done() {
                assert_eq!(w.door, door_scratch(&g, &tab, &w.visited, w.cur));
                assert_eq!(w.long, long_scratch(&g, &w.visited, w.cur, &w.cycle_rem));
                assert!(w.lb_residual() >= w.lb_arc());
                assert!(w.lb_arc() >= w.lb());
                if w.r <= 11 {
                    assert!(
                        w.lb_residual() as u32 <= truth(&w),
                        "n={n} seed={seed} step={}",
                        w.steps
                    );
                }
                step(&mut w, &mut rng, 0.35);
            }
            assert_eq!(w.lb_residual(), 0);
        }
    }
}

/// Gate GA: ≥ 10k sampled states at `n = 5, 6` with `m ≤ 25` remaining,
/// from greedy/beam prefixes at assorted depths with randomized
/// suffixes; the bound must never exceed the tablebase truth.
#[test]
#[ignore = "gate GA: minutes of Held-Karp"]
fn gate_ga_admissibility() {
    let mut total = 0usize;
    let mut violations = 0usize;
    for n in [5usize, 6] {
        let g = Graph::new(n);
        // Beam-shaped states: exact frontier snapshots at several tail
        // sizes, each continued randomly to a random smaller tail.
        let mut beam_seeds: Vec<Vec<u32>> = Vec::new();
        for m in [22usize, 25] {
            if m >= g.nfact {
                continue;
            }
            let (_, snaps) = beam_search_endgame_snapshot(
                &g,
                300,
                Scorer::Bound(Bound::Cycle),
                None,
                0,
                None,
                SnapshotCfg {
                    remaining: m,
                    top: 40,
                },
            );
            beam_seeds.extend(snaps.into_iter().map(|s| s.path));
        }
        let greedy_path = greedy(&g).path;

        let mut slacks: Vec<i64> = Vec::new();
        // Tier 3 is measured alongside, never asserted: it is expected
        // to exceed the truth, which is exactly why it may not prune.
        let mut floor_violations = 0usize;
        let mut rng = StdRng::seed_from_u64(20260728 + n as u64);
        let samples = 5200;
        for i in 0..samples {
            // Half greedy-prefix walks, half beam-frontier states.
            let mut w = if i % 2 == 0 || beam_seeds.is_empty() {
                let depth = rng.gen_range(1..g.nfact - 26);
                replay(&g, &greedy_path[..=depth])
            } else {
                replay(&g, &beam_seeds[rng.gen_range(0..beam_seeds.len())])
            };
            // Randomized suffix down to a random tail size.
            let target = rng.gen_range(2usize..=18);
            let eps = [0.05, 0.2, 0.5, 1.0][rng.gen_range(0..4)];
            while w.r > target && !w.done() {
                step(&mut w, &mut rng, eps);
            }
            if w.r == 0 {
                continue;
            }
            let b = w.lb_residual() as i64;
            let t = truth(&w) as i64;
            total += 1;
            if b > t {
                violations += 1;
                eprintln!("GA VIOLATION n={n} r={} bound={b} truth={t}", w.r);
            }
            slacks.push(t - b);
            let floor = heuristic_floor_not_admissible(n, w.r, w.lb_residual()) as i64;
            if floor > t {
                floor_violations += 1;
            }
        }
        slacks.sort_unstable();
        let mean = slacks.iter().sum::<i64>() as f64 / slacks.len() as f64;
        println!(
            "GA n={n}: samples={} violations={} slack min={} median={} mean={:.2} max={}",
            slacks.len(),
            violations,
            slacks[0],
            slacks[slacks.len() / 2],
            mean,
            slacks[slacks.len() - 1]
        );
        println!(
            "GA n={n}: Tier-3 heuristic_floor exceeded the truth on {floor_violations}/{} samples \
             (NOT admissible, ordering only)",
            slacks.len()
        );
    }
    println!("GA total samples={total} violations={violations}");
    assert_eq!(violations, 0, "admissibility violated");
    assert!(total >= 10_000, "gate GA needs >= 10k samples, got {total}");
}

/// Gate GA tail: a handful of large-`m` states (the RAM-heavy end of the
/// tablebase, `m` up to 25) — run separately so the bulk gate stays
/// cheap.
#[test]
#[ignore = "gate GA tail: ~2^25 Held-Karp tables"]
fn gate_ga_admissibility_large_m() {
    let mut violations = 0usize;
    let mut n_samples = 0usize;
    for n in [5usize, 6] {
        let g = Graph::new(n);
        let greedy_path = greedy(&g).path;
        let mut rng = StdRng::seed_from_u64(99 + n as u64);
        for m in [20usize, 22, 24, 25] {
            if m + 2 >= g.nfact {
                continue;
            }
            for rep in 0..2 {
                let depth = rng.gen_range(1..g.nfact - m - 2);
                let mut w = replay(&g, &greedy_path[..=depth]);
                while w.r > m {
                    step(&mut w, &mut rng, if rep == 0 { 0.1 } else { 0.6 });
                }
                let b = w.lb_residual() as i64;
                let t = truth(&w) as i64;
                n_samples += 1;
                if b > t {
                    violations += 1;
                    eprintln!("GA-large VIOLATION n={n} m={m} bound={b} truth={t}");
                }
                println!(
                    "GA-large n={n} m={m} rep={rep} bound={b} truth={t} slack={}",
                    t - b
                );
            }
        }
    }
    println!("GA-large samples={n_samples} violations={violations}");
    assert_eq!(violations, 0);
}

/// Gate GB: exact root values per tier at `n = 5, 6, 7`, and the mean
/// uplift over 100 beam states at depth 200 (`n = 6`).
#[test]
#[ignore = "gate GB: builds the n=7 graph and runs a beam"]
fn gate_gb_strength() {
    for n in [5usize, 6, 7] {
        let g = Graph::new(n);
        let w = Walk::new(&g);
        println!(
            "GB root n={n}: cycle={} arc={} residual={}  (total = n + bound: {} / {} / {})",
            w.lb(),
            w.lb_arc(),
            w.lb_residual(),
            n + w.lb(),
            n + w.lb_arc(),
            n + w.lb_residual()
        );
    }

    // 100 beam states at depth 200 (n = 6): the canonical stratified
    // config's frontier, snapshotted where 720 − 200 = 520 remain.
    let g = Graph::new(6);
    let (_, snaps) = beam_search_endgame_snapshot(
        &g,
        2000,
        Scorer::Bound(Bound::Cycle),
        None,
        0,
        None,
        SnapshotCfg {
            remaining: g.nfact - 200,
            top: 100,
        },
    );
    let (mut sc, mut sa, mut sr) = (0f64, 0f64, 0f64);
    let mut worse = 0usize;
    for s in &snaps {
        let w = replay(&g, &s.path);
        assert_eq!(w.r, g.nfact - 200);
        sc += w.lb() as f64;
        sa += w.lb_arc() as f64;
        sr += w.lb_residual() as f64;
        if w.lb_residual() < w.lb_arc() {
            worse += 1;
        }
    }
    let k = snaps.len() as f64;
    println!(
        "GB depth-200 n=6 over {} states: mean cycle={:.2} arc={:.2} residual={:.2} \
         (uplift vs arc {:+.2}, vs cycle {:+.2}); states where residual < arc: {worse}",
        snaps.len(),
        sc / k,
        sa / k,
        sr / k,
        (sr - sa) / k,
        (sr - sc) / k
    );
    assert_eq!(worse, 0, "residual must dominate arc pointwise");
}
