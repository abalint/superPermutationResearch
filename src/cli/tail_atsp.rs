//! `tail-atsp` — the I1/I2a/I3 surgery instrument (block-ATSP tail
//! re-optimization, merges, recompositions, pair recompositions).

use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use superperm::graph::Graph;

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
    /// Record directories, comma-separated.
    #[arg(long, value_delimiter = ',')]
    dirs: Vec<PathBuf>,
    /// Anchor: smallest first-visit depth eligible as the cut.
    #[arg(long, default_value_t = 585)]
    anchor: usize,
    /// Widest instance to solve exactly; walks needing more blocks
    /// at --anchor are cut DEEPER (fewer blocks) instead of skipped.
    #[arg(long, default_value_t = 27)]
    max_blocks: usize,
    /// Also collect equal-cost orders (ties) and report those whose
    /// implied L0 allocation differs from the source walk's.
    #[arg(long)]
    ties: bool,
    /// I2a merge moves (SURGERY-DESIGN §9): additionally try every
    /// single same-cycle block merge (the S−1 unit edit) and re-solve
    /// exactly. A merged walk SHORTER than the source is an 871
    /// candidate (banner, exit 2); an EQUAL-length one is a new 872
    /// at S−1 with one extra door-unit — an allocation no source
    /// walk occupies — reported and written to --out-dir.
    #[arg(long)]
    merge: bool,
    /// I2a recomp-1 (SURGERY-DESIGN §9, s31): try EVERY single-cycle
    /// recomposition — all alternative arc-partitions of each cycle's
    /// tail perm set (subsumes --merge; adds splits, repartitions,
    /// entry rotations, and out-of-vocabulary 1|5 arcs) — and
    /// re-solve exactly. Shorter = 871 candidate (exit 2); equal
    /// length in a different allocation = reported + written.
    #[arg(long)]
    recomp: bool,
    /// I3 recomp2 (SURGERY-DESIGN §10, s38): try every PAIR of
    /// recompositions on two distinct tail cycles under T1 budget
    /// (combined net split ∈ {−2,−1,0}) + T2 vocabulary (no
    /// singleton arcs), plus single prefix-part extraction of each
    /// straddling cycle (float its only prefix part into the tail,
    /// heal the seam exactly; then identity/single/pair moves on the
    /// extended instance). Shorter = 871/5905 candidate (exit 2);
    /// equal length in a new allocation = reported + written — at
    /// n=7 an (844,17)↔(843,18) equal IS the Kristan seam. Run at
    /// anchor 450/520 (n=6) or 4770/4840 (n=7) with --max-blocks ~56.
    #[arg(long)]
    recomp2: bool,
    /// Lift T2 for --recomp2 (singleton 1|k arcs in) — the
    /// broader-negative second pass; ~15× more exact re-solves.
    #[arg(long)]
    recomp2_wide: bool,
    /// Restrict --recomp2's T1 to net ∈ {−2, −1} (the S−1 budget
    /// family), skipping the net-0 (d3−1) family — ~4× fewer exact
    /// re-solves; the deep-anchor budget option.
    #[arg(long)]
    recomp2_tight: bool,
    /// Cap on collected tie orders per walk.
    #[arg(long, default_value_t = 64)]
    tie_cap: usize,
    /// Write improved (and, with --ties, new-allocation tie) walks
    /// here.
    #[arg(long)]
    out_dir: Option<PathBuf>,
    /// Process only the first K records (sweep sizing runs).
    #[arg(long)]
    limit: Option<usize>,
    /// Print only the summary and any improvements.
    #[arg(long)]
    quiet: bool,
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        dirs,
        anchor,
        max_blocks,
        ties,
        merge,
        recomp,
        recomp2,
        recomp2_wide,
        recomp2_tight,
        tie_cap,
        out_dir,
        limit,
        quiet,
    } = a;
    use superperm::tailatsp;
    let g = Graph::new(n);
    let dir_refs: Vec<&std::path::Path> = dirs.iter().map(|p| p.as_path()).collect();
    let mut corpus = superperm::corpus::load_corpus(&g, &dir_refs).unwrap_or_else(|e| {
        eprintln!("{e}");
        std::process::exit(1);
    });
    if let Some(k) = limit {
        corpus.truncate(k);
    }
    let t0 = Instant::now();
    let (mut optimal, mut improved, mut skipped, mut new_alloc_ties) = (0u64, 0u64, 0u64, 0u64);
    let (mut merge_moves, mut merge_improved, mut merge_equal) = (0u64, 0u64, 0u64);
    let mut merge_allocs: std::collections::BTreeMap<(usize, usize, usize, usize), u64> =
        std::collections::BTreeMap::new();
    let (mut rc_moves, mut rc_improved, mut rc_equal_new, mut rc_equal_same) =
        (0u64, 0u64, 0u64, 0u64);
    let mut rc_allocs: std::collections::BTreeMap<(usize, usize, usize, usize), u64> =
        std::collections::BTreeMap::new();
    let (mut r2_ext, mut r2_raw, mut r2_t1, mut r2_solved) = (0u64, 0u64, 0u64, 0u64);
    let mut r2_by_net = [0u64; 3];
    let (mut r2_improved, mut r2_eq_new, mut r2_eq_same, mut r2_lambda_bad) =
        (0u64, 0u64, 0u64, 0u64);
    let mut r2_allocs: std::collections::BTreeMap<(usize, usize, usize, usize), u64> =
        std::collections::BTreeMap::new();
    let emit = |tag: &str, s: &str| {
        if let Some(dir) = &out_dir {
            fs::create_dir_all(dir).expect("create out dir");
            let path = dir.join(format!("{tag}.txt"));
            fs::write(&path, format!("{s}\n")).expect("write find");
            println!("  written -> {}", path.display());
        }
    };
    for rec in &corpus {
        // Shallowest anchor whose instance fits max_blocks: cut
        // deeper until it fits (deeper = fewer blocks).
        let mut min_depth = anchor;
        let inst = loop {
            match tailatsp::decompose(n, &rec.trace, min_depth) {
                None => break None,
                Some(i) if i.blocks.len() <= max_blocks => break Some(i),
                Some(i) => min_depth = i.anchor_depth + 1,
            }
        };
        let Some(inst) = inst else {
            skipped += 1;
            continue;
        };
        let (opt, order, tie_orders) = tailatsp::solve_bb(&inst, ties, tie_cap);
        if opt < inst.actual {
            improved += 1;
            let s = tailatsp::materialize(n, &g, &rec.string, &inst, &order);
            let v = superperm::validate::validate(n, &s);
            println!(
                "*** IMPROVEMENT *** {} anchor={} blocks={} {} -> {} chars={} valid={} ({}/{})",
                rec.name,
                inst.anchor_depth,
                inst.blocks.len(),
                inst.actual,
                opt,
                s.len(),
                v.complete,
                v.distinct,
                v.total
            );
            println!("    NEXT: python3 analysis/counting/m3_check.py + validate --complete before ANY claim");
            emit(&format!("cand-{}", rec.name.trim_end_matches(".txt")), &s);
        } else {
            optimal += 1;
            if !quiet {
                println!(
                    "{}: anchor={} blocks={} cost={} block-order-optimal",
                    rec.name,
                    inst.anchor_depth,
                    inst.blocks.len(),
                    inst.actual
                );
            }
            if merge {
                // I2a: every single-merge move, re-solved with the
                // unmerged optimum as incumbent — a result of
                // opt − 1 is an equal-length 872 at S−1 (always a
                // new allocation vs the source), ≤ opt − 2 an 871.
                let mut emitted = 0usize;
                for mv in tailatsp::enumerate_merges(n, &g, &inst) {
                    merge_moves += 1;
                    let m = tailatsp::apply_merge(n, &g, &inst, &mv, opt);
                    let (mopt, morder, _) = tailatsp::solve_bb(&m, false, 0);
                    if mopt >= opt {
                        continue;
                    }
                    let s = tailatsp::materialize(n, &g, &rec.string, &m, &morder);
                    let v = superperm::validate::validate(n, &s);
                    if !v.complete {
                        continue;
                    }
                    let t = superperm::trace::trace_string(&g, &s).expect("merge trace");
                    let alloc = tailatsp::allocation_of(&t);
                    if s.len() < rec.string.len() {
                        merge_improved += 1;
                        println!(
                            "*** MERGE IMPROVEMENT *** {} anchor={} chars={} (source {}) alloc={:?} valid={}",
                            rec.name,
                            inst.anchor_depth,
                            s.len(),
                            rec.string.len(),
                            alloc,
                            v.complete
                        );
                        println!("    NEXT: python3 analysis/counting/m3_check.py + validate --complete before ANY claim");
                        emit(
                            &format!("merge-cand-{}", rec.name.trim_end_matches(".txt")),
                            &s,
                        );
                    } else {
                        merge_equal += 1;
                        *merge_allocs.entry(alloc).or_default() += 1;
                        if !quiet || merge_equal <= 20 {
                            println!(
                                "  merge-equal 872 at S-1: {} -> alloc {:?} (anchor {})",
                                rec.name, alloc, inst.anchor_depth
                            );
                        }
                        if emitted < 8 {
                            emit(
                                &format!(
                                    "merge-eq-{}-{}",
                                    rec.name.trim_end_matches(".txt"),
                                    merge_equal
                                ),
                                &s,
                            );
                            emitted += 1;
                        }
                    }
                }
            }
            if recomp {
                // I2a recomp-1: every single-cycle recomposition,
                // re-solved with an incumbent one above the
                // equal-length junction total (result = inc − 1 ⇔
                // equal-length 872, ≤ inc − 2 ⇔ 871 candidate).
                let src_alloc = tailatsp::allocation_of(&rec.trace);
                let mut emitted = 0usize;
                let mut emitted_same = 0usize;
                for mv in tailatsp::enumerate_recomps(n, &g, &inst) {
                    rc_moves += 1;
                    let inc = opt + mv.arcs.len() + 1 - mv.remove.len();
                    let m = tailatsp::apply_recomp(n, &g, &inst, &mv, inc);
                    let (mopt, morder, _) = tailatsp::solve_bb(&m, false, 0);
                    if mopt >= inc {
                        continue;
                    }
                    let s = tailatsp::materialize(n, &g, &rec.string, &m, &morder);
                    let v = superperm::validate::validate(n, &s);
                    if !v.complete {
                        continue;
                    }
                    let t = superperm::trace::trace_string(&g, &s).expect("recomp trace");
                    let alloc = tailatsp::allocation_of(&t);
                    if s.len() < rec.string.len() {
                        rc_improved += 1;
                        println!(
                            "*** RECOMP IMPROVEMENT *** {} anchor={} chars={} (source {}) alloc={:?} valid={}",
                            rec.name,
                            inst.anchor_depth,
                            s.len(),
                            rec.string.len(),
                            alloc,
                            v.complete
                        );
                        println!("    NEXT: python3 analysis/counting/m3_check.py + validate --complete before ANY claim");
                        emit(
                            &format!("recomp-cand-{}", rec.name.trim_end_matches(".txt")),
                            &s,
                        );
                    } else if alloc != src_alloc {
                        rc_equal_new += 1;
                        *rc_allocs.entry(alloc).or_default() += 1;
                        if !quiet || rc_equal_new <= 20 {
                            println!(
                                "  recomp-equal 872 in NEW allocation: {} -> {:?} (source {:?}, anchor {})",
                                rec.name, alloc, src_alloc, inst.anchor_depth
                            );
                        }
                        if emitted < 8 {
                            emit(
                                &format!(
                                    "recomp-eq-{}-{}",
                                    rec.name.trim_end_matches(".txt"),
                                    rc_equal_new
                                ),
                                &s,
                            );
                            emitted += 1;
                        }
                    } else {
                        rc_equal_same += 1;
                        // sample for offline m3_check: same-allocation
                        // equal-cost recompositions may still be NOVEL
                        // classes (the shell-density question)
                        if emitted_same < 2 {
                            emit(
                                &format!(
                                    "recomp-sameeq-{}-{}",
                                    rec.name.trim_end_matches(".txt"),
                                    rc_equal_same
                                ),
                                &s,
                            );
                            emitted_same += 1;
                        }
                    }
                }
            }
            if recomp2 {
                // I3: pair recompositions + prefix-part
                // extraction (SURGERY-DESIGN §10.4/§10.6/§10.7).
                let src_alloc = tailatsp::allocation_of(&rec.trace);
                let tw = Instant::now();
                let rep = tailatsp::recomp2_walk(
                    n,
                    &g,
                    &rec.string,
                    &rec.trace,
                    &inst,
                    recomp2_wide,
                    !recomp2_tight,
                    8,
                    2,
                );
                r2_ext += rep.ext_candidates as u64;
                r2_raw += rep.raw_pairs;
                r2_t1 += rep.t1_pairs;
                r2_solved += rep.solved;
                for (k, v) in r2_by_net.iter_mut().enumerate() {
                    *v += rep.solved_by_net[k];
                }
                r2_improved += rep.improved;
                r2_eq_new += rep.equal_new;
                r2_eq_same += rep.equal_same;
                r2_lambda_bad += rep.lambda_bad;
                for (a, k) in &rep.eq_new_allocs {
                    *r2_allocs.entry(*a).or_default() += k;
                }
                let (mut k_eq, mut k_same) = (0usize, 0usize);
                for f in &rep.finds {
                    if !f.lambda_ok {
                        println!(
                            "*** LOOP-RELATION VIOLATION *** (solver bug or first counterexample to the s35 law) {} [{}]",
                            rec.name, f.desc
                        );
                    }
                    match f.kind {
                        tailatsp::R2Kind::Shorter => {
                            println!(
                                "*** RECOMP2 IMPROVEMENT *** {} anchor={} chars={} (source {}) alloc={:?} [{}]",
                                rec.name,
                                inst.anchor_depth,
                                f.s.len(),
                                rec.string.len(),
                                f.alloc,
                                f.desc
                            );
                            println!("    NEXT: python3 analysis/counting/m3_check.py + validate --complete before ANY claim");
                            emit(
                                &format!("recomp2-cand-{}", rec.name.trim_end_matches(".txt")),
                                &f.s,
                            );
                        }
                        tailatsp::R2Kind::EqualNew => {
                            let kristan = n == 7
                                && ((src_alloc.0, src_alloc.1) == (844, 17)
                                    && (f.alloc.0, f.alloc.1) == (843, 18)
                                    || (src_alloc.0, src_alloc.1) == (843, 18)
                                        && (f.alloc.0, f.alloc.1) == (844, 17));
                            if kristan {
                                println!(
                                    "*** KRISTAN SEAM FOUND *** equal-length {:?} <-> {:?} compound: {} [{}]",
                                    src_alloc, f.alloc, rec.name, f.desc
                                );
                            } else if !quiet || r2_eq_new <= 20 {
                                println!(
                                    "  recomp2-equal in NEW allocation: {} -> {:?} (source {:?}) [{}]",
                                    rec.name, f.alloc, src_alloc, f.desc
                                );
                            }
                            k_eq += 1;
                            emit(
                                &format!(
                                    "recomp2-eq-{}-{}",
                                    rec.name.trim_end_matches(".txt"),
                                    k_eq
                                ),
                                &f.s,
                            );
                        }
                        tailatsp::R2Kind::EqualSame => {
                            k_same += 1;
                            emit(
                                &format!(
                                    "recomp2-sameeq-{}-{}",
                                    rec.name.trim_end_matches(".txt"),
                                    k_same
                                ),
                                &f.s,
                            );
                        }
                    }
                }
                if !quiet {
                    println!(
                        "  recomp2 {}: ext={} raw={} t1={} solved={} eq_new={} eq_same={} ({:.1}s)",
                        rec.name,
                        rep.ext_candidates,
                        rep.raw_pairs,
                        rep.t1_pairs,
                        rep.solved,
                        rep.equal_new,
                        rep.equal_same,
                        tw.elapsed().as_secs_f64()
                    );
                }
            }
            if ties {
                let src_alloc = tailatsp::allocation_of(&rec.trace);
                for (ti, ord) in tie_orders.iter().enumerate() {
                    let s = tailatsp::materialize(n, &g, &rec.string, &inst, ord);
                    if s == rec.string {
                        continue;
                    }
                    let v = superperm::validate::validate(n, &s);
                    if !v.complete || s.len() != rec.string.len() {
                        continue;
                    }
                    let t = superperm::trace::trace_string(&g, &s).expect("tie trace");
                    let alloc = tailatsp::allocation_of(&t);
                    if alloc != src_alloc {
                        new_alloc_ties += 1;
                        println!(
                            "  tie in NEW allocation {:?} (source {:?}): {} tie#{}",
                            alloc, src_alloc, rec.name, ti
                        );
                        emit(
                            &format!("tie-{}-{}", rec.name.trim_end_matches(".txt"), ti),
                            &s,
                        );
                    }
                }
            }
        }
    }
    println!(
        "tail-atsp: {} walks, {optimal} block-order-optimal, {improved} improved, {skipped} skipped, {new_alloc_ties} new-allocation ties ({:.1}s)",
        corpus.len(),
        t0.elapsed().as_secs_f64()
    );
    if merge {
        println!(
            "  merge (I2a): {merge_moves} moves tried, {merge_improved} improved (871 candidates), {merge_equal} equal-cost 872s at S-1"
        );
        for (alloc, k) in &merge_allocs {
            println!("    merged allocation {alloc:?}: {k}");
        }
    }
    if recomp {
        println!(
            "  recomp-1 (I2a): {rc_moves} moves tried, {rc_improved} improved (871 candidates), {rc_equal_new} equal-cost 872s in NEW allocations, {rc_equal_same} equal-cost same-allocation"
        );
        for (alloc, k) in &rc_allocs {
            println!("    recomposed allocation {alloc:?}: {k}");
        }
    }
    if recomp2 {
        println!(
            "  recomp2 (I3): {r2_ext} extraction candidates, {r2_raw} raw pairs, {r2_t1} post-T1, {r2_solved} exact re-solves (net -2/-1/0: {}/{}/{}), {r2_improved} improved (candidates), {r2_eq_new} equal-cost in NEW allocations, {r2_eq_same} equal-cost same-allocation, {r2_lambda_bad} loop-relation violations",
            r2_by_net[0], r2_by_net[1], r2_by_net[2]
        );
        for (alloc, k) in &r2_allocs {
            println!("    compound allocation {alloc:?}: {k}");
        }
    }
    if improved > 0 || merge_improved > 0 || rc_improved > 0 || r2_improved > 0 {
        std::process::exit(2);
    }
    ExitCode::SUCCESS
}
