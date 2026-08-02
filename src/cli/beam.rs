//! `beam` — the one-ended beam search and everything bolted onto it
//! (seeding, stratification, jitter, the admissible cap, the exact
//! endgame snapshot, the cutoff log).

use std::fs;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use superperm::beam::{
    beam_search_capped, beam_search_endgame_snapshot, beam_search_multi_seeded,
    beam_search_multi_seeded_capped, beam_search_multi_seeded_endgame, beam_search_stratified,
    beam_search_stratified_cutoffs, Jitter, Scorer, SnapshotCfg, Stratify,
};
use superperm::endgame::{solve_endgame, spell_path, MAX_REMAINING};
use superperm::graph::Graph;

use super::{load_model, write_log, BoundArg};

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
    /// Beam width (states kept per depth level).
    #[arg(long, default_value_t = 1000)]
    width: usize,
    /// Admissible lower bound used for scoring (default: cycle).
    /// The arc bound is tighter but empirically no better as a beam
    /// ranker (see docs/JOURNAL.md 2026-07-27). With --model, an
    /// explicit --bound composes (T2): score = len + lb + alpha *
    /// prediction; without it the model scores alone as before.
    #[arg(long, value_enum)]
    bound: Option<BoundArg>,
    /// Score candidates with this learned value-function model
    /// (JSON produced by the training side); alone, or composed
    /// with an explicit --bound (T2).
    #[arg(long)]
    model: Option<PathBuf>,
    /// Blend factor for the learned score: len + alpha * prediction.
    #[arg(long, default_value_t = 1.0)]
    alpha: f64,
    /// Allow --model files trained for a different n (cross-n
    /// transfer; the mismatch is reported as a warning instead of
    /// an error).
    #[arg(long, requires = "model")]
    allow_n_mismatch: bool,
    /// Deterministic score jitter magnitude in length units: each
    /// candidate's score gets a pseudo-random offset in [0, eps)
    /// that is a pure function of (cur, visited, seed). 0 disables
    /// jitter (bit-identical to the unjittered search).
    #[arg(long, default_value_t = 0.0)]
    jitter: f64,
    /// Seed for the jitter's Zobrist table (only used with --jitter).
    #[arg(long, default_value_t = 0)]
    jitter_seed: u64,
    /// Seed the beam's root state by replaying this many greedy
    /// moves before the search starts (0 = plain beam; must be
    /// < n! - 1). The reported result includes the prefix.
    #[arg(long, default_value_t = 0)]
    seed_prefix: usize,
    /// Seed the beam from walk prefixes in this file (T3): one walk
    /// per line, either a comma-separated first-visit rank list
    /// starting at 0, or a `sojourn-dfs --dump-frontier` TSV row
    /// (the path is its last field; `#` lines are skipped). Each
    /// walk is injected at its own depth; a one-line file with the
    /// greedy prefix is bit-identical to --seed-prefix.
    #[arg(long, conflicts_with = "seed_prefix")]
    seed_file: Option<PathBuf>,
    /// Stratified selection: bucket candidates by deficit profile
    /// (quantized intact / half-open / nearly-done cycle counts)
    /// and reserve part of the width per occupied bucket, so
    /// record-like states can't be crowded out by globally
    /// better-scoring greedy-like ones. Off = bit-identical to the
    /// plain beam.
    #[arg(long)]
    stratify: bool,
    /// Kept slots reserved per occupied bucket (only with
    /// --stratify; 0 behaves like the plain beam).
    #[arg(long, default_value_t = 32, requires = "stratify")]
    strat_quota: usize,
    /// Bucket granularity: each deficit count is divided by this
    /// before forming the bucket key (only with --stratify; >= 1).
    #[arg(long, default_value_t = 4, requires = "stratify")]
    strat_bucket: usize,
    /// Exact endgame tablebase (phase-3 item 4): when exactly this
    /// many perms remain, snapshot the frontier and solve the top
    /// --endgame-top states' completions exactly (Held-Karp DP;
    /// provably optimal). The beam itself is unchanged; the summary
    /// reports whether any exact endgame beats the heuristic one,
    /// and the best exact string is printed if it beats the beam's.
    /// 0 = off; RAM/time grow as 2^m (20 is cheap, 24 is seconds
    /// and ~800 MB per state).
    #[arg(long, default_value_t = 0)]
    endgame: usize,
    /// Frontier states (in score order) to solve exactly (with
    /// --endgame).
    #[arg(long, default_value_t = 100)]
    endgame_top: usize,
    /// Write the best path's feature records to this JSONL file.
    #[arg(long)]
    log: Option<PathBuf>,
    /// Write one TSV line per level (level, kept, best_score,
    /// worst_kept_score — the pruning threshold; with --stratify
    /// the max kept score) to this file. Pure instrumentation;
    /// does not change the search.
    #[arg(long)]
    cutoff_log: Option<PathBuf>,
    /// Admissible length cap (T2): discard every candidate whose
    /// len + lb exceeds this — lossless for completions within the
    /// cap; the whole width is spent on states that can still make
    /// it. The search reports failure if no explored walk finishes
    /// within the cap. 0 = off.
    #[arg(long, default_value_t = 0)]
    max_len: u32,
}

/// Parse a beam `--seed-file`: one walk per line, either a bare
/// comma-separated first-visit rank list or a `sojourn-dfs
/// --dump-frontier` TSV row (path in the last tab field); empty and
/// `#`-prefixed lines are skipped. Exits with a message on any invalid
/// walk (must start at rank 0, ranks in range, not a complete walk).
fn read_seed_file(path: &PathBuf, nfact: usize) -> Vec<Vec<u32>> {
    let text = std::fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("cannot read --seed-file {}: {e}", path.display());
        std::process::exit(1);
    });
    let mut seeds = Vec::new();
    for (i, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let field = line.rsplit('\t').next().unwrap();
        let walk: Vec<u32> = field
            .split(',')
            .map(|t| {
                t.trim().parse().unwrap_or_else(|_| {
                    eprintln!("--seed-file line {}: invalid rank {t:?}", i + 1);
                    std::process::exit(1);
                })
            })
            .collect();
        let bad = if walk.first() != Some(&0) {
            Some("walk must start at rank 0")
        } else if walk.len() >= nfact {
            Some("walk already visits every permutation")
        } else if walk.iter().any(|&r| r as usize >= nfact) {
            Some("rank out of range")
        } else {
            None
        };
        if let Some(msg) = bad {
            eprintln!("--seed-file line {}: {msg}", i + 1);
            std::process::exit(1);
        }
        seeds.push(walk);
    }
    if seeds.is_empty() {
        eprintln!("--seed-file {} contains no walks", path.display());
        std::process::exit(1);
    }
    seeds
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        width,
        bound,
        model,
        alpha,
        allow_n_mismatch,
        jitter,
        jitter_seed,
        seed_prefix,
        seed_file,
        stratify,
        strat_quota,
        strat_bucket,
        endgame,
        endgame_top,
        log,
        cutoff_log,
        max_len,
    } = a;
    let g = Graph::new(n);
    if seed_prefix >= g.nfact - 1 {
        eprintln!(
            "--seed-prefix must be less than n! - 1 = {} (got {seed_prefix})",
            g.nfact - 1
        );
        std::process::exit(1);
    }
    let seeds = seed_file.as_ref().map(|p| read_seed_file(p, g.nfact));
    let loaded = model.map(|path| load_model(&path, n, allow_n_mismatch));
    let (scorer, desc) = match (&loaded, bound) {
        (Some(m), Some(b)) => (
            Scorer::Composed {
                bound: b.into(),
                model: m,
                alpha,
            },
            format!("bound={}+model={} alpha={alpha}", b.name(), m.kind()),
        ),
        (Some(m), None) => (
            Scorer::Learned { model: m, alpha },
            format!("model={} alpha={alpha}", m.kind()),
        ),
        (None, b) => {
            let b = b.unwrap_or(BoundArg::Cycle);
            (Scorer::Bound(b.into()), format!("bound={}", b.name()))
        }
    };
    let jit = (jitter > 0.0).then_some(Jitter {
        eps: jitter,
        seed: jitter_seed,
    });
    let jdesc = match jit {
        Some(j) => format!(" jitter={} jitter_seed={}", j.eps, j.seed),
        None => String::new(),
    };
    let sdesc = match (&seeds, seed_prefix) {
        (Some(s), _) => format!(
            " seed_file={} seeds={}",
            seed_file.as_ref().unwrap().display(),
            s.len()
        ),
        (None, 0) => String::new(),
        (None, k) => format!(" seed_prefix={k}"),
    };
    if stratify && strat_bucket == 0 {
        eprintln!("--strat-bucket must be >= 1");
        std::process::exit(1);
    }
    let strat = stratify.then_some(Stratify {
        quota: strat_quota,
        bucket: strat_bucket,
    });
    let stdesc = match strat {
        Some(s) => format!(" stratify quota={} bucket={}", s.quota, s.bucket),
        None => String::new(),
    };
    if endgame > 0 {
        let seeded = match &seeds {
            Some(s) => s.iter().map(Vec::len).max().unwrap(),
            None => 1 + seed_prefix,
        };
        let max_m = MAX_REMAINING.min(g.nfact - seeded);
        if !(1..=max_m).contains(&endgame) {
            eprintln!("--endgame must be in 1..={max_m} (got {endgame})");
            std::process::exit(1);
        }
        if cutoff_log.is_some() {
            eprintln!("--endgame cannot be combined with --cutoff-log");
            std::process::exit(1);
        }
    }
    if seeds.is_some() && cutoff_log.is_some() {
        eprintln!("--seed-file cannot be combined with --cutoff-log");
        std::process::exit(1);
    }
    if max_len > 0 && (endgame > 0 || cutoff_log.is_some()) {
        eprintln!("--max-len cannot be combined with --endgame or --cutoff-log");
        std::process::exit(1);
    }
    let t0 = Instant::now();
    if max_len > 0 {
        let capped = match &seeds {
            Some(s) => beam_search_multi_seeded_capped(&g, width, scorer, jit, s, strat, max_len),
            None => beam_search_capped(&g, width, scorer, jit, seed_prefix, strat, max_len),
        };
        let dt = t0.elapsed();
        match capped {
            Some(b) => {
                println!(
                    "beam n={n} width={width} {desc}{jdesc}{sdesc}{stdesc} max_len={max_len}: length {} ({:.3}s)",
                    b.len,
                    dt.as_secs_f64()
                );
                println!("{}", b.string);
                if let Some(path) = log {
                    write_log(&g, &b.path, &path);
                }
            }
            None => {
                println!(
                    "beam n={n} width={width} {desc}{jdesc}{sdesc}{stdesc} max_len={max_len}: NO completion within cap ({:.3}s)",
                    dt.as_secs_f64()
                );
            }
        }
        return ExitCode::SUCCESS;
    }
    let (b, cuts, snaps) = if endgame > 0 {
        let cfg = SnapshotCfg {
            remaining: endgame,
            top: endgame_top,
        };
        let (b, s) = match &seeds {
            Some(s) => beam_search_multi_seeded_endgame(&g, width, scorer, jit, s, strat, cfg),
            None => beam_search_endgame_snapshot(&g, width, scorer, jit, seed_prefix, strat, cfg),
        };
        (b, None, Some(s))
    } else if let Some(s) = &seeds {
        (
            beam_search_multi_seeded(&g, width, scorer, jit, s, strat),
            None,
            None,
        )
    } else {
        match &cutoff_log {
            Some(_) => {
                let (b, c) =
                    beam_search_stratified_cutoffs(&g, width, scorer, jit, seed_prefix, strat);
                (b, Some(c), None)
            }
            None => (
                beam_search_stratified(&g, width, scorer, jit, seed_prefix, strat),
                None,
                None,
            ),
        }
    };
    let dt = t0.elapsed();
    println!(
        "beam n={n} width={width} {desc}{jdesc}{sdesc}{stdesc}: length {} ({:.3}s)",
        b.len,
        dt.as_secs_f64()
    );
    println!("{}", b.string);
    if let Some(snaps) = snaps {
        let t1 = Instant::now();
        let mut best: Option<(u32, usize, Vec<u32>)> = None; // (total, idx, order)
        let mut beats_own = 0usize; // exact < its own beam descendant
        let mut max_gain = 0i64;
        let mut beats_beam = 0usize; // exact total < beam final result
        for (i, s) in snaps.iter().enumerate() {
            let e = solve_endgame(&g, s.cur, &s.remaining);
            let total = s.len + e.cost;
            if let Some(h) = s.best_descendant_len {
                let gain = i64::from(h) - i64::from(total);
                if gain >= 1 {
                    beats_own += 1;
                }
                max_gain = max_gain.max(gain);
            }
            if (total as usize) < b.len {
                beats_beam += 1;
            }
            if best.as_ref().is_none_or(|(t, _, _)| total < *t) {
                best = Some((total, i, e.order));
            }
        }
        let (best_total, best_idx, best_order) = best.expect("endgame top >= 1");
        let snap = &snaps[best_idx];
        println!(
            "endgame m={endgame} top={}: solved {} frontier states ({:.3}s)",
            endgame_top,
            snaps.len(),
            t1.elapsed().as_secs_f64()
        );
        println!(
            "  best exact total = {best_total} (score-rank #{}, len {} + exact {})",
            snap.score_rank,
            snap.len,
            best_total - snap.len
        );
        println!(
            "  exact beats own beam descendant by >=1 char: {beats_own} / {} states (max gain {max_gain})",
            snaps.len()
        );
        println!(
            "  exact total beats beam result ({}): {beats_beam} / {} states",
            b.len,
            snaps.len()
        );
        if (best_total as usize) < b.len {
            let mut path = snap.path.clone();
            path.extend_from_slice(&best_order);
            let s = spell_path(&g, &path);
            assert_eq!(s.len(), best_total as usize);
            let v = superperm::validate::validate(n, &s);
            println!(
                "  IMPROVED result: length {best_total} (validated complete = {})",
                v.complete
            );
            println!("{s}");
        }
    }
    if let Some(path) = log {
        write_log(&g, &b.path, &path);
    }
    if let (Some(path), Some(cuts)) = (cutoff_log, cuts) {
        let file = fs::File::create(&path).unwrap_or_else(|e| {
            eprintln!("cannot create {}: {e}", path.display());
            std::process::exit(1);
        });
        let mut w = BufWriter::new(file);
        writeln!(w, "level\tkept\tbest_score\tworst_kept_score").unwrap();
        for c in &cuts {
            writeln!(
                w,
                "{}\t{}\t{}\t{}",
                c.level, c.kept, c.best_score, c.worst_kept_score
            )
            .unwrap();
        }
        println!(
            "cutoff log        = {} levels -> {}",
            cuts.len(),
            path.display()
        );
    }
    ExitCode::SUCCESS
}
