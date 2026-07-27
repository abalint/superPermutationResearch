//! Integration tests against known minimal superpermutation lengths and
//! the admissibility of the cycle lower bound.

use superperm::beam::beam_search;
use superperm::graph::Graph;
use superperm::greedy::greedy;
use superperm::rollout::run_rollouts;
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

#[test]
fn beam_n4_width_512_is_optimal() {
    let g = Graph::new(4);
    let b = beam_search(&g, 512);
    assert_eq!(b.len, 33);
    assert!(validate(4, &b.string).complete);
}

#[test]
fn beam_n5_width_2000_is_optimal() {
    let g = Graph::new(5);
    let b = beam_search(&g, 2000);
    assert!(validate(5, &b.string).complete);
    assert_eq!(b.len, 153);
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
