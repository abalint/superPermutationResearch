//! `greedy` — the deterministic min-weight + lex tie-break baseline.

use std::path::PathBuf;
use std::process::ExitCode;

use superperm::graph::Graph;
use superperm::greedy::greedy;

use super::write_log;

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
    /// Write the trajectory's feature records to this JSONL file.
    #[arg(long)]
    log: Option<PathBuf>,
}

pub fn run(a: Args) -> ExitCode {
    let Args { n, log } = a;
    let g = Graph::new(n);
    let r = greedy(&g);
    println!("greedy n={n}: length {}", r.len);
    println!("{}", r.string);
    if let Some(path) = log {
        write_log(&g, &r.path, &path);
    }
    ExitCode::SUCCESS
}
