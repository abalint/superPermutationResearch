//! Command-line interface for the `superperm` research toolkit.
//!
//! Subcommands: `info`, `greedy`, `beam`, `rollouts`, `validate` — see
//! `superperm --help` and the crate-level documentation of the library.

use std::fs;
use std::io::BufWriter;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use clap::{Parser, Subcommand};

use superperm::beam::beam_search;
use superperm::graph::Graph;
use superperm::greedy::greedy;
use superperm::rollout::run_rollouts;
use superperm::validate::validate;

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
    },
    /// Run beam search and print the best result plus wall-clock time.
    Beam {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Beam width (states kept per depth level).
        #[arg(long, default_value_t = 1000)]
        width: usize,
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
        Cmd::Greedy { n } => {
            let g = Graph::new(n);
            let r = greedy(&g);
            println!("greedy n={n}: length {}", r.len);
            println!("{}", r.string);
        }
        Cmd::Beam { n, width } => {
            let g = Graph::new(n);
            let t0 = Instant::now();
            let b = beam_search(&g, width);
            let dt = t0.elapsed();
            println!(
                "beam n={n} width={width}: length {} ({:.3}s)",
                b.len,
                dt.as_secs_f64()
            );
            println!("{}", b.string);
        }
        Cmd::Rollouts {
            n,
            count,
            epsilon,
            seed,
            out,
        } => {
            let g = Graph::new(n);
            let file = fs::File::create(&out).unwrap_or_else(|e| {
                eprintln!("cannot create {}: {e}", out.display());
                std::process::exit(1);
            });
            let mut writer = BufWriter::new(file);
            let s =
                run_rollouts(&g, count, epsilon, seed, &mut writer).expect("rollout write failed");
            println!(
                "rollouts n={n} count={} epsilon={epsilon} seed={seed}",
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
