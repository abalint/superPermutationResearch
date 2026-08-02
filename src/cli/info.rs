//! `info` — graph statistics (n!, cycle count, edge histogram by weight).

use std::process::ExitCode;

use superperm::graph::Graph;

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
}

pub fn run(a: Args) -> ExitCode {
    let Args { n } = a;
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
    ExitCode::SUCCESS
}
