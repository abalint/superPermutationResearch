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
    beam_search_stratified, beam_search_stratified_cutoffs, Bound, Jitter, Scorer, Stratify,
};
use superperm::beam2::{beam2_search, Scorer2};
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
}

impl From<BoundArg> for Bound {
    fn from(b: BoundArg) -> Bound {
        match b {
            BoundArg::Cycle => Bound::Cycle,
            BoundArg::Arc => Bound::Arc,
        }
    }
}

/// Load a model file, exiting with a clear message on a parse failure or
/// an `n` mismatch.
fn load_model(path: &PathBuf, n: usize) -> Model {
    let m = Model::load(path).unwrap_or_else(|e| {
        eprintln!("cannot load model {}: {e}", path.display());
        std::process::exit(1);
    });
    if m.n() != n {
        eprintln!("model was trained for n={} but -n is {n}", m.n());
        std::process::exit(1);
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
            jitter,
            jitter_seed,
            seed_prefix,
            stratify,
            strat_quota,
            strat_bucket,
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
            let loaded = model.map(|path| load_model(&path, n));
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
            let t0 = Instant::now();
            let (b, cuts) = match &cutoff_log {
                Some(_) => {
                    let (b, c) =
                        beam_search_stratified_cutoffs(&g, width, scorer, jit, seed_prefix, strat);
                    (b, Some(c))
                }
                None => (
                    beam_search_stratified(&g, width, scorer, jit, seed_prefix, strat),
                    None,
                ),
            };
            let dt = t0.elapsed();
            println!(
                "beam n={n} width={width} {desc}{jdesc}{sdesc}{stdesc}: length {} ({:.3}s)",
                b.len,
                dt.as_secs_f64()
            );
            println!("{}", b.string);
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
            let loaded = model.map(|path| load_model(&path, n));
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
            let loaded = model.map(|path| load_model(&path, n));
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
            let loaded = model.map(|path| load_model(&path, n));
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
