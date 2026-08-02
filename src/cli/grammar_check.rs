//! `grammar-check` — replay strings through an L0/L1 class grammar.

use std::path::PathBuf;
use std::process::ExitCode;

use superperm::graph::Graph;
use superperm::trace::trace_string;

use super::load_profile;

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
    /// Class caps as S,d3,d4,d5,ip (e.g. "145,3,0,0,0" = records).
    #[arg(long, value_delimiter = ',')]
    class: Vec<u16>,
    /// Enforce the records' n=6 split profile (6|2,4|3,3|4,2|2,2,2).
    #[arg(long)]
    records_profile: bool,
    /// Enforce a split profile loaded from a file (one composition
    /// per line, parts space-separated; per-allocation files live
    /// in analysis/trackb/profiles/, from the s27 corpus census).
    #[arg(long, conflicts_with = "records_profile")]
    profile_file: Option<PathBuf>,
    /// Restrict weight-3/4/5 doors to untouched cycles (s27
    /// corpus law: all 66,999 heavy doors in the 22,062 community
    /// classes open a fresh cycle; corpus-calibrated prune, not a
    /// theorem — exhaustion claims made with it must say so).
    #[arg(long)]
    fresh_doors: bool,
    /// Superpermutation string files to check.
    #[arg(required = true)]
    files: Vec<PathBuf>,
    /// Print only the summary line and failures.
    #[arg(long)]
    quiet: bool,
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        class,
        records_profile,
        profile_file,
        fresh_doors,
        files,
        quiet,
    } = a;
    use superperm::sojourn::{ClassCaps, Grammar};
    assert_eq!(class.len(), 5, "--class needs S,d3,d4,d5,ip");
    let g = Graph::new(n);
    let caps = ClassCaps {
        s: class[0],
        d3: class[1],
        d4: class[2],
        d5: class[3],
        ip: class[4],
    };
    let profile = load_profile(records_profile, profile_file.as_ref(), n);
    let mut grammar = Grammar::new(&g, caps, profile.clone());
    grammar.fresh_doors = fresh_doors;
    println!(
        "grammar-check n={n} class=(S={},d3={},d4={},d5={},ip={}) waste={} profile={}{}",
        caps.s,
        caps.d3,
        caps.d4,
        caps.d5,
        caps.ip,
        caps.waste(),
        match (&profile, &profile_file) {
            (None, _) => "none".to_string(),
            (Some(_), None) => "records".to_string(),
            (Some(p), Some(f)) => format!("{} ({} compositions)", f.display(), p.allowed.len()),
        },
        if fresh_doors { " fresh-doors" } else { "" },
    );
    let mut failures = 0u32;
    for path in &files {
        let text = std::fs::read_to_string(path).unwrap_or_else(|e| {
            eprintln!("cannot read {}: {e}", path.display());
            std::process::exit(1);
        });
        // forward-renumber to identity start: relabel symbols so
        // the first window reads 12..n (the grammar roots at the
        // identity permutation)
        let s = text.trim();
        let mut sigma = [0u8; 256];
        for (i, b) in s.bytes().take(n).enumerate() {
            sigma[b as usize] = b'1' + i as u8;
        }
        let renum: String = s.bytes().map(|b| sigma[b as usize] as char).collect();
        let tr = trace_string(&g, &renum).unwrap_or_else(|e| {
            eprintln!("{}: {e}", path.display());
            std::process::exit(1);
        });
        let seq = &tr.path[1..];
        let done = grammar.replay(seq);
        let ok = done == seq.len();
        if !ok {
            failures += 1;
        }
        if !quiet || !ok {
            println!(
                "  {}: {done} of {} moves in-grammar{}",
                path.display(),
                seq.len(),
                if ok { "" } else { "  OUT-OF-GRAMMAR" },
            );
        }
    }
    println!(
        "grammar-check: {} of {} files replay fully",
        files.len() as u32 - failures,
        files.len(),
    );
    if failures > 0 {
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
