//! `endgame` — exact (Held-Karp) completion of a walk prefix.

use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use superperm::endgame::{solve_endgame, spell_path, MAX_REMAINING};
use superperm::graph::Graph;
use superperm::greedy::greedy;
use superperm::trace::trace_string;
use superperm::validate::validate;

#[derive(clap::Args)]
pub struct Args {
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
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        file,
        greedy: use_greedy,
        remaining,
    } = a;
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
    ExitCode::SUCCESS
}
