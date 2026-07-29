//! Command-line interface for the `superperm` research toolkit.
//!
//! Subcommands: `info`, `greedy`, `beam`, `rollouts`, `validate` — see
//! `superperm --help` and the crate-level documentation of the library.

use std::fs;
use std::io::BufWriter;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use clap::{Parser, Subcommand, ValueEnum};

use std::io::Write;

use superperm::beam::{
    beam_search_endgame_snapshot, beam_search_stratified, beam_search_stratified_cutoffs, Bound,
    Jitter, Scorer, SnapshotCfg, Stratify,
};
use superperm::beam2::{beam2_search, Scorer2};
use superperm::endgame::{solve_endgame, spell_path, MAX_REMAINING};
use superperm::graph::Graph;
use superperm::greedy::greedy;
use superperm::model::Model;
use superperm::rollout::{log_trajectory, run_rollouts_guided, Guide};
use superperm::trace::{score_trajectory, trace_string};
use superperm::validate::validate;

/// CLI mirror of [`Bound`] (the library does not depend on clap).
#[derive(Clone, Copy, ValueEnum)]
enum BoundArg {
    /// Cycle bound `r + k − [current cycle live]` (phase 1).
    Cycle,
    /// Arc bound `r + arcs − [succ1(cur) unvisited]`; dominates cycle.
    Arc,
    /// Residual bound `r + door + intact + long`; dominates arc
    /// (`docs/RESIDUAL-BOUND-DESIGN.md`).
    Residual,
}

impl From<BoundArg> for Bound {
    fn from(b: BoundArg) -> Bound {
        match b {
            BoundArg::Cycle => Bound::Cycle,
            BoundArg::Arc => Bound::Arc,
            BoundArg::Residual => Bound::Residual,
        }
    }
}

/// Load a model file, exiting with a clear message on a parse failure or
/// an `n` mismatch. With `allow_n_mismatch` the mismatch is downgraded to
/// a warning (cross-n transfer: the features are generic counts, so an
/// n=6-trained linear map is well-defined — if uncalibrated — at n=7).
fn load_model(path: &PathBuf, n: usize, allow_n_mismatch: bool) -> Model {
    let m = Model::load(path).unwrap_or_else(|e| {
        eprintln!("cannot load model {}: {e}", path.display());
        std::process::exit(1);
    });
    if m.n() != n {
        if allow_n_mismatch {
            eprintln!(
                "warning: model was trained for n={} but -n is {n} (cross-n transfer)",
                m.n()
            );
        } else {
            eprintln!(
                "model was trained for n={} but -n is {n} \
                 (pass --allow-n-mismatch to transfer anyway)",
                m.n()
            );
            std::process::exit(1);
        }
    }
    m
}

/// Write a visit-order path's feature trajectory to `path` as JSONL.
fn write_log(g: &Graph, ranks: &[u32], path: &PathBuf) {
    let file = fs::File::create(path).unwrap_or_else(|e| {
        eprintln!("cannot create {}: {e}", path.display());
        std::process::exit(1);
    });
    let mut writer = BufWriter::new(file);
    let lines = log_trajectory(g, ranks, &mut writer).expect("trajectory write failed");
    println!("trajectory log    = {} lines -> {}", lines, path.display());
}

/// Render a per-claim verdict line suffix for `cert-verify`.
fn agree(ok: bool) -> &'static str {
    if ok {
        "AGREE"
    } else {
        "DISAGREE"
    }
}

/// Compact y/n column for the `cert-verify` verdict table.
fn yn(ok: bool) -> &'static str {
    if ok {
        "y"
    } else {
        "n"
    }
}

/// Superpermutation search research toolkit (phase 1).
#[derive(Parser)]
#[command(name = "superperm", version, about)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Print graph statistics: n!, cycle count, edge histogram by weight.
    Info {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
    },
    /// Run the deterministic greedy baseline and print the result.
    Greedy {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Write the trajectory's feature records to this JSONL file.
        #[arg(long)]
        log: Option<PathBuf>,
    },
    /// Run beam search and print the best result plus wall-clock time.
    Beam {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Beam width (states kept per depth level).
        #[arg(long, default_value_t = 1000)]
        width: usize,
        /// Admissible lower bound used for scoring. The arc bound is
        /// tighter but empirically no better as a beam ranker (see
        /// docs/JOURNAL.md 2026-07-27).
        #[arg(long, value_enum, default_value_t = BoundArg::Cycle)]
        bound: BoundArg,
        /// Score candidates with this learned value-function model
        /// (JSON produced by the training side) instead of a bound.
        #[arg(long, conflicts_with = "bound")]
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
    },
    /// Run the two-ended (deque) beam search: moves append a successor
    /// of the string's back or prepend a predecessor of its front,
    /// scored by the admissible two-ended arc bound (phase 3's
    /// decision-order probe).
    Beam2 {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Beam width (states kept per depth level).
        #[arg(long, default_value_t = 1000)]
        width: usize,
        /// Transfer experiment: score candidates with this learned
        /// one-ended model (features computed relative to the back end)
        /// instead of the two-ended arc bound.
        #[arg(long)]
        model: Option<PathBuf>,
        /// Blend factor for the learned score: len + alpha * prediction.
        #[arg(long, default_value_t = 1.0)]
        alpha: f64,
        /// Deterministic score jitter magnitude in length units (pure
        /// function of (front, back, visited, seed); 0 disables).
        #[arg(long, default_value_t = 0.0)]
        jitter: f64,
        /// Seed for the jitter's Zobrist table (only used with --jitter).
        #[arg(long, default_value_t = 0)]
        jitter_seed: u64,
    },
    /// Trace an existing superpermutation string: extract its
    /// first-visit trajectory, summarize its edge weights, and
    /// optionally score every trajectory state with a bound or model.
    Trace {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// File holding the superpermutation string (trimmed).
        #[arg(long)]
        file: PathBuf,
        /// Score trajectory states with this admissible bound
        /// (score = len + lb).
        #[arg(long, value_enum)]
        bound: Option<BoundArg>,
        /// Score trajectory states with this learned model instead
        /// (score = len + alpha * pred, + lb_arc for residual models —
        /// exactly the beam's arithmetic).
        #[arg(long, conflicts_with = "bound")]
        model: Option<PathBuf>,
        /// Blend factor for the learned score (only used with --model).
        #[arg(long, default_value_t = 1.0)]
        alpha: f64,
        /// Write the trajectory's feature records to this JSONL file.
        #[arg(long)]
        log: Option<PathBuf>,
        /// Write per-step scores as TSV (step, len, score) to this file
        /// instead of stdout (requires --bound or --model).
        #[arg(long)]
        score_log: Option<PathBuf>,
    },
    /// Exactly complete a prefix of an existing walk: truncate its
    /// first-visit path to n! − m visits and solve the last m perms
    /// optimally (Held-Karp exact endgame). The verdict is a theorem:
    /// no completion of that prefix can beat the reported total.
    Endgame {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// File holding the superpermutation string whose prefix to
        /// complete (trimmed).
        #[arg(long, conflicts_with = "greedy", required_unless_present = "greedy")]
        file: Option<PathBuf>,
        /// Use the deterministic greedy walk as the source instead.
        #[arg(long)]
        greedy: bool,
        /// How many trailing perms to solve exactly (1..=25; RAM/time
        /// grow as 2^m — 20 is cheap, 24 is seconds and ~800 MB).
        #[arg(long)]
        remaining: usize,
    },
    /// Generate epsilon-greedy rollouts and write JSONL feature records.
    Rollouts {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Number of rollouts.
        #[arg(long, default_value_t = 100)]
        count: usize,
        /// Probability of a random (non-greedy) move at each step.
        #[arg(long, default_value_t = 0.1)]
        epsilon: f64,
        /// Base RNG seed; rollout i uses seed + i.
        #[arg(long, default_value_t = 0)]
        seed: u64,
        /// Guide the exploit move with this learned value-function model
        /// instead of the greedy successor rule.
        #[arg(long)]
        model: Option<PathBuf>,
        /// Blend factor for the guided score: len + weight + alpha *
        /// prediction (only used with --model).
        #[arg(long, default_value_t = 1.0)]
        alpha: f64,
        /// Output JSONL file path.
        #[arg(long)]
        out: PathBuf,
    },
    /// Independently verify the n=6 gain-one kernel-chain certificate
    /// (claims C1-C5) from a clean-room reimplementation, printing a
    /// verdict table (claim, computed value, agree y/n).
    CertVerify {
        /// Number of symbols (the certificate is defined for n = 6 only).
        #[arg(short, long)]
        n: usize,
    },
    /// Validate a candidate superpermutation string.
    Validate {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// The candidate string (or use --file).
        string: Option<String>,
        /// Read the candidate string from a file instead.
        #[arg(long, conflicts_with = "string")]
        file: Option<PathBuf>,
        /// Exit nonzero unless the string is a complete superpermutation.
        #[arg(long)]
        complete: bool,
    },
}

fn main() -> ExitCode {
    match Cli::parse().cmd {
        Cmd::Info { n } => {
            let g = Graph::new(n);
            println!("n = {n}");
            println!("n! (vertices) = {}", g.nfact);
            println!("cycle_count ((n-1)!) = {}", g.cycle_count);
            let mut hist = vec![0usize; n];
            for list in &g.succs {
                for &(_, w) in list {
                    hist[w as usize] += 1;
                }
            }
            println!("successor edges by weight (weight-n jumps not stored):");
            for (w, count) in hist.iter().enumerate().skip(1) {
                println!("  weight {w}: {count} edges ({} per perm)", count / g.nfact);
            }
            println!("successors per perm = {}", g.succs[0].len());
        }
        Cmd::Greedy { n, log } => {
            let g = Graph::new(n);
            let r = greedy(&g);
            println!("greedy n={n}: length {}", r.len);
            println!("{}", r.string);
            if let Some(path) = log {
                write_log(&g, &r.path, &path);
            }
        }
        Cmd::Beam {
            n,
            width,
            bound,
            model,
            alpha,
            allow_n_mismatch,
            jitter,
            jitter_seed,
            seed_prefix,
            stratify,
            strat_quota,
            strat_bucket,
            endgame,
            endgame_top,
            log,
            cutoff_log,
        } => {
            let g = Graph::new(n);
            if seed_prefix >= g.nfact - 1 {
                eprintln!(
                    "--seed-prefix must be less than n! - 1 = {} (got {seed_prefix})",
                    g.nfact - 1
                );
                std::process::exit(1);
            }
            let loaded = model.map(|path| load_model(&path, n, allow_n_mismatch));
            let (scorer, desc) = match &loaded {
                Some(m) => (
                    Scorer::Learned { model: m, alpha },
                    format!("model={} alpha={alpha}", m.kind()),
                ),
                None => (
                    Scorer::Bound(bound.into()),
                    format!(
                        "bound={}",
                        match bound {
                            BoundArg::Cycle => "cycle",
                            BoundArg::Arc => "arc",
                            BoundArg::Residual => "residual",
                        }
                    ),
                ),
            };
            let jit = (jitter > 0.0).then_some(Jitter {
                eps: jitter,
                seed: jitter_seed,
            });
            let jdesc = match jit {
                Some(j) => format!(" jitter={} jitter_seed={}", j.eps, j.seed),
                None => String::new(),
            };
            let sdesc = if seed_prefix > 0 {
                format!(" seed_prefix={seed_prefix}")
            } else {
                String::new()
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
                let max_m = MAX_REMAINING.min(g.nfact - 1 - seed_prefix);
                if !(1..=max_m).contains(&endgame) {
                    eprintln!("--endgame must be in 1..={max_m} (got {endgame})");
                    std::process::exit(1);
                }
                if cutoff_log.is_some() {
                    eprintln!("--endgame cannot be combined with --cutoff-log");
                    std::process::exit(1);
                }
            }
            let t0 = Instant::now();
            let (b, cuts, snaps) = if endgame > 0 {
                let (b, s) = beam_search_endgame_snapshot(
                    &g,
                    width,
                    scorer,
                    jit,
                    seed_prefix,
                    strat,
                    SnapshotCfg {
                        remaining: endgame,
                        top: endgame_top,
                    },
                );
                (b, None, Some(s))
            } else {
                match &cutoff_log {
                    Some(_) => {
                        let (b, c) = beam_search_stratified_cutoffs(
                            &g,
                            width,
                            scorer,
                            jit,
                            seed_prefix,
                            strat,
                        );
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
        }
        Cmd::Beam2 {
            n,
            width,
            model,
            alpha,
            jitter,
            jitter_seed,
        } => {
            let g = Graph::new(n);
            let loaded = model.map(|path| load_model(&path, n, false));
            if let Some(m) = &loaded {
                if m.n_features() > superperm::model::FEATURE_ORDER.len() {
                    eprintln!(
                        "beam2's transfer scorer supports only the 8-feature contract; \
                         this model consumes {} features (the deficit-distribution \
                         features are not maintained in the two-ended searcher)",
                        m.n_features()
                    );
                    std::process::exit(1);
                }
            }
            let (scorer, desc) = match &loaded {
                Some(m) => (
                    Scorer2::Learned { model: m, alpha },
                    format!("model={} alpha={alpha}", m.kind()),
                ),
                None => (Scorer2::Arc2, "bound=arc2".to_string()),
            };
            let jit = (jitter > 0.0).then_some(Jitter {
                eps: jitter,
                seed: jitter_seed,
            });
            let jdesc = match jit {
                Some(j) => format!(" jitter={} jitter_seed={}", j.eps, j.seed),
                None => String::new(),
            };
            let t0 = Instant::now();
            let b = beam2_search(&g, width, scorer, jit);
            let dt = t0.elapsed();
            let prepends = b.moves.iter().filter(|&&(_, p)| p).count();
            println!(
                "beam2 n={n} width={width} {desc}{jdesc}: length {} ({:.3}s, {} prepends / {} moves)",
                b.len,
                dt.as_secs_f64(),
                prepends,
                b.moves.len() - 1
            );
            println!("{}", b.string);
        }
        Cmd::Trace {
            n,
            file,
            bound,
            model,
            alpha,
            log,
            score_log,
        } => {
            let g = Graph::new(n);
            let s = fs::read_to_string(&file)
                .unwrap_or_else(|e| {
                    eprintln!("cannot read {}: {e}", file.display());
                    std::process::exit(1);
                })
                .trim()
                .to_string();
            let v = validate(n, &s);
            if !v.complete {
                eprintln!(
                    "not a complete superpermutation: {} / {} perms covered",
                    v.distinct, v.total
                );
                std::process::exit(1);
            }
            let t = trace_string(&g, &s).unwrap_or_else(|e| {
                eprintln!("cannot trace {}: {e}", file.display());
                std::process::exit(1);
            });
            println!(
                "trace n={n} {}: length {} (replay {}), visits {}",
                file.display(),
                t.input_len,
                t.replay_len,
                t.path.len()
            );
            if t.replay_len != t.input_len {
                println!(
                    "warning: replay is {} chars shorter — the string does not \
                     realize every maximal overlap",
                    t.input_len - t.replay_len
                );
            }
            print!("moves by weight  :");
            for (w, count) in t.hist.iter().enumerate().skip(1) {
                print!(" w{w}={count}");
            }
            println!();
            let heavy: Vec<String> = t
                .weights
                .iter()
                .enumerate()
                .filter(|&(_, &w)| w >= 3)
                .map(|(i, &w)| format!("{}(w{})", i + 1, w))
                .collect();
            println!(
                "weight>=3 moves  : {}{}",
                heavy.len(),
                if heavy.is_empty() {
                    String::new()
                } else {
                    format!(" at steps {}", heavy.join(" "))
                }
            );
            if let Some(path) = log {
                write_log(&g, &t.path, &path);
            }
            let loaded = model.map(|path| load_model(&path, n, false));
            let scorer = match (&loaded, bound) {
                (Some(m), _) => Some(Scorer::Learned { model: m, alpha }),
                (None, Some(b)) => Some(Scorer::Bound(b.into())),
                (None, None) => None,
            };
            if scorer.is_none() && score_log.is_some() {
                eprintln!("--score-log requires --bound or --model");
                std::process::exit(1);
            }
            if let Some(scorer) = scorer {
                let scores = score_trajectory(&g, &t.path, scorer);
                match score_log {
                    Some(path) => {
                        let file = fs::File::create(&path).unwrap_or_else(|e| {
                            eprintln!("cannot create {}: {e}", path.display());
                            std::process::exit(1);
                        });
                        let mut w = BufWriter::new(file);
                        writeln!(w, "step\tlen\tscore").unwrap();
                        for (step, len, score) in &scores {
                            writeln!(w, "{step}\t{len}\t{score}").unwrap();
                        }
                        println!(
                            "score log        = {} steps -> {}",
                            scores.len(),
                            path.display()
                        );
                    }
                    None => {
                        println!("step\tlen\tscore");
                        for (step, len, score) in &scores {
                            println!("{step}\t{len}\t{score}");
                        }
                    }
                }
            }
        }
        Cmd::Endgame {
            n,
            file,
            greedy: use_greedy,
            remaining,
        } => {
            let g = Graph::new(n);
            if !(1..=MAX_REMAINING.min(g.nfact - 1)).contains(&remaining) {
                eprintln!(
                    "--remaining must be in 1..={} (got {remaining})",
                    MAX_REMAINING.min(g.nfact - 1)
                );
                std::process::exit(1);
            }
            let (path, src_len, src_desc) = if use_greedy {
                let r = greedy(&g);
                (r.path, r.len, "greedy".to_string())
            } else {
                let file = file.expect("clap enforces --file or --greedy");
                let s = fs::read_to_string(&file)
                    .unwrap_or_else(|e| {
                        eprintln!("cannot read {}: {e}", file.display());
                        std::process::exit(1);
                    })
                    .trim()
                    .to_string();
                let v = validate(n, &s);
                if !v.complete {
                    eprintln!(
                        "not a complete superpermutation: {} / {} perms covered",
                        v.distinct, v.total
                    );
                    std::process::exit(1);
                }
                let t = trace_string(&g, &s).unwrap_or_else(|e| {
                    eprintln!("cannot trace {}: {e}", file.display());
                    std::process::exit(1);
                });
                (t.path, t.replay_len, file.display().to_string())
            };
            let keep = g.nfact - remaining;
            let prefix = &path[..keep];
            let prefix_len = spell_path(&g, prefix).len();
            let mut rem: Vec<u32> = path[keep..].to_vec();
            rem.sort_unstable();
            let t0 = Instant::now();
            let e = solve_endgame(&g, *prefix.last().unwrap(), &rem);
            let dt = t0.elapsed();
            let total = prefix_len + e.cost as usize;
            let own = src_len - prefix_len;
            println!("endgame n={n} source={src_desc} (length {src_len})");
            println!(
                "prefix = {keep} visits, {prefix_len} chars; last {remaining} perms solved exactly ({:.3}s)",
                dt.as_secs_f64()
            );
            println!(
                "exact completion = {} chars -> total {total}; source's own completion = {own} chars (exact saves {})",
                e.cost,
                own - e.cost as usize
            );
            println!("THEOREM: no completion of this {keep}-visit prefix yields length < {total}");
            let mut full = prefix.to_vec();
            full.extend_from_slice(&e.order);
            let s = spell_path(&g, &full);
            assert_eq!(s.len(), total);
            let v = validate(n, &s);
            assert!(v.complete, "recomposed endgame string failed validation");
            println!("{s}");
        }
        Cmd::Rollouts {
            n,
            count,
            epsilon,
            seed,
            model,
            alpha,
            out,
        } => {
            let g = Graph::new(n);
            let loaded = model.map(|path| load_model(&path, n, false));
            let guide = loaded.as_ref().map(|m| Guide { model: m, alpha });
            let mdesc = match &loaded {
                Some(m) => format!(" model={} alpha={alpha}", m.kind()),
                None => String::new(),
            };
            let file = fs::File::create(&out).unwrap_or_else(|e| {
                eprintln!("cannot create {}: {e}", out.display());
                std::process::exit(1);
            });
            let mut writer = BufWriter::new(file);
            let s = run_rollouts_guided(&g, count, epsilon, seed, guide, &mut writer)
                .expect("rollout write failed");
            println!(
                "rollouts n={n} count={} epsilon={epsilon} seed={seed}{mdesc}",
                s.rollouts
            );
            println!("mean final length = {:.2}", s.mean_len);
            println!("min final length  = {}", s.min_len);
            println!("lines written     = {} -> {}", s.lines, out.display());
        }
        Cmd::CertVerify { n } => {
            if n != 6 {
                eprintln!("cert-verify: the certificate is defined for n = 6 only (got {n})");
                std::process::exit(1);
            }
            use superperm::cert::{waste_and_length, Cert};
            let cert = Cert::new();
            println!(
                "cert-verify n=6: clean-room verification of the gain-one kernel-chain certificate"
            );
            println!(
                "construction gates passed: 144 loops, tv period 5, entry-orbit distinctness, \
                 door(s,2)=e' splice identity, per-class orbit partition"
            );
            println!();

            // C1: forced map.
            let hops = cert.audit_hops();
            let forced = cert.forced_audit();
            let cycles: Vec<String> = forced
                .cycle_lengths
                .iter()
                .map(|(len, count)| format!("len {len} x{count}"))
                .collect();
            let c1_ok = forced.total_map
                && forced.is_permutation
                && forced.cycle_lengths.len() == 1
                && forced.cycle_lengths.get(&4) == Some(&180);
            println!("C1 forced map (exit skip-0 splice, cost-3 hop):");
            println!(
                "  valid hop targets per (loop,splice) pair, by cost 3/4/5/6 = {}/{}/{}/{} of {} \
                 (cost-3 target unique per pair: {})",
                hops.valid_by_cost[0],
                hops.valid_by_cost[1],
                hops.valid_by_cost[2],
                hops.valid_by_cost[3],
                hops.pairs,
                hops.valid_by_cost[0] == hops.pairs
            );
            println!(
                "  total map = {}, permutation = {}, cycles = [{}]",
                forced.total_map,
                forced.is_permutation,
                cycles.join(", ")
            );
            println!(
                "  CLAIM permutation with all cycles length 4: {}",
                agree(c1_ok)
            );
            println!();

            // C2: pivot confinement.
            let c2_ok = hops.pivot_violations == 0 && hops.non_entry_landings == 0;
            println!("C2 pivot confinement:");
            println!(
                "  pivot preserved   = {} violations in {} hop words",
                hops.pivot_violations,
                hops.pairs * 4
            );
            println!(
                "  landing on entry  = automatic ({} exceptions)",
                hops.non_entry_landings
            );
            println!(
                "  class partition   = each pivot class's 24 loops cover the 120 orbits exactly \
                 once (asserted at construction)"
            );
            println!(
                "  CLAIM chains confined to one pivot class, in-class orbit-disjointness automatic: {}",
                agree(c2_ok)
            );
            println!();

            // C3: exhaustive chain search per pivot class.
            println!("C3 exhaustive chain search (identity-started, hops cost 3..=6):");
            let t0 = Instant::now();
            let mut global_max = i64::MIN;
            let mut all_best = Vec::new();
            for pivot in 1..=6u8 {
                let s = cert.search_class(pivot);
                let mut breakdown = std::collections::BTreeMap::new();
                for c in &s.chains {
                    let st = c.stats();
                    *breakdown.entry((st.k, st.sigma, st.f4)).or_insert(0usize) += 1;
                }
                let bd: Vec<String> = breakdown
                    .iter()
                    .map(|((k, sg, f4), cnt)| format!("(K={k},S={sg},f4={f4}) x{cnt}"))
                    .collect();
                println!(
                    "  pivot {pivot}: max V = {}, chains at max = {}, nodes = {}, {}",
                    s.max_v,
                    s.chains.len(),
                    s.nodes,
                    bd.join(" ")
                );
                if s.max_v > global_max {
                    global_max = s.max_v;
                    all_best.clear();
                }
                if s.max_v == global_max {
                    all_best.extend(s.chains);
                }
            }
            let c3_time = t0.elapsed();
            let mut total_bd = std::collections::BTreeMap::new();
            for c in &all_best {
                let st = c.stats();
                *total_bd.entry((st.k, st.sigma, st.f4)).or_insert(0usize) += 1;
            }
            let bd: Vec<String> = total_bd
                .iter()
                .map(|((k, sg, f4), cnt)| format!("(K={k},Sigma={sg},f4={f4}) x{cnt}"))
                .collect();
            println!(
                "  global: max V = {global_max}, chains at max = {}, breakdown {} ({:.2}s)",
                all_best.len(),
                bd.join(" "),
                c3_time.as_secs_f64()
            );
            println!("  V = 12 reachable: {}", global_max >= 12);
            let c3_ok = global_max == 8
                && all_best.len() == 12
                && total_bd.get(&(22, 14, 0)) == Some(&6)
                && total_bd.get(&(20, 8, 1)) == Some(&6);
            println!(
                "  CLAIM max V = 8 by exactly 12 chains (6 x (K=22,Sigma=14,f4=0) + 6 x \
                 (K=20,Sigma=8,f4=1)), V = 12 unreachable: {}",
                agree(c3_ok)
            );
            println!();

            // C4: cover search over the optimal chains + positive control.
            println!("C4 rooted-cover search:");
            let t1 = Instant::now();
            let mut any_rooted = false;
            for (i, chain) in all_best.iter().enumerate() {
                let st = chain.stats();
                let r = cert.cover_search(chain, false);
                any_rooted |= r.rooted_covers > 0;
                println!(
                    "  chain {:2} (pivot {}, K={:2}, Sigma={:2}, f4={}): roots={}, non-root={}, \
                     rows={}, exact covers={}, rooted covers={}",
                    i + 1,
                    cert.loops[chain.loops[0]].pivot,
                    st.k,
                    st.sigma,
                    st.f4,
                    r.roots,
                    r.non_root,
                    r.rows,
                    r.exact_covers,
                    r.rooted_covers
                );
            }
            let kernel = cert.standard_kernel(6);
            let ks = kernel.stats();
            let control = cert.cover_search(&kernel, true);
            let c4_time = t1.elapsed();
            println!(
                "  control (standard kernel, pivot 6, K={}, Sigma={}, V={}): roots={}, \
                 non-root={}, rows={}, rooted cover found = {}",
                ks.k,
                ks.sigma,
                ks.v,
                control.roots,
                control.non_root,
                control.rows,
                control.rooted_covers >= 1
            );
            println!("  ({:.2}s)", c4_time.as_secs_f64());
            let c4_ok = !any_rooted && control.rooted_covers >= 1;
            println!(
                "  CLAIM all optimal chains admit zero rooted covers; standard kernel admits one: {}",
                agree(c4_ok)
            );
            println!();

            // C5: ledger arithmetic.
            let (w4, l4) = waste_and_length(4);
            let (w8, l8) = waste_and_length(8);
            let c5_ok = (w4, l4) == (147, 872) && (w8, l8) == (146, 871);
            println!("C5 ledger arithmetic:");
            println!("  V = 4 -> waste {w4}, length {l4}; V = 8 -> waste {w8}, length {l8}");
            println!(
                "  CLAIM standard kernel gives waste 147 / length 872; V = 8 would give 146 / 871: {}",
                agree(c5_ok)
            );
            println!();

            println!("verdict table:");
            println!("  claim | computed | agree");
            println!(
                "  C1 forced map, all cycles length 4 | permutation={}, cycles=[{}] | {}",
                forced.is_permutation,
                cycles.join(", "),
                yn(c1_ok)
            );
            println!(
                "  C2 pivot confinement | {} pivot / {} entry violations | {}",
                hops.pivot_violations,
                hops.non_entry_landings,
                yn(c2_ok)
            );
            println!(
                "  C3 max V = 8 by exactly 12 chains | max V = {global_max}, {} chains, {} | {}",
                all_best.len(),
                bd.join(" "),
                yn(c3_ok)
            );
            println!(
                "  C4 optimal chains uncoverable, control coverable | rooted covers: chains {}, \
                 control found {} | {}",
                if any_rooted { ">=1" } else { "all 0" },
                control.rooted_covers >= 1,
                yn(c4_ok)
            );
            println!(
                "  C5 waste arithmetic | V=4 -> {w4}/{l4}, V=8 -> {w8}/{l8} | {}",
                yn(c5_ok)
            );
            if !(c1_ok && c2_ok && c3_ok && c4_ok && c5_ok) {
                println!();
                println!(
                    "DISCREPANCY: at least one claim disagrees with this clean-room verification."
                );
                return ExitCode::FAILURE;
            }
        }
        Cmd::Validate {
            n,
            string,
            file,
            complete,
        } => {
            let s = match (string, file) {
                (Some(s), None) => s,
                (None, Some(p)) => fs::read_to_string(&p)
                    .unwrap_or_else(|e| {
                        eprintln!("cannot read {}: {e}", p.display());
                        std::process::exit(1);
                    })
                    .trim()
                    .to_string(),
                _ => {
                    eprintln!("provide exactly one of <STRING> or --file");
                    return ExitCode::from(2);
                }
            };
            let v = validate(n, &s);
            println!("length = {}", v.length);
            println!("distinct perms covered = {} / {}", v.distinct, v.total);
            println!("complete superpermutation = {}", v.complete);
            if complete && !v.complete {
                return ExitCode::FAILURE;
            }
        }
    }
    ExitCode::SUCCESS
}
