//! `trace` — first-visit trajectory of an existing superpermutation string.

use std::fs;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::process::ExitCode;

use superperm::beam::Scorer;
use superperm::graph::Graph;
use superperm::trace::{score_trajectory, trace_string};
use superperm::validate::validate;

use super::{load_model, write_log, BoundArg};

#[derive(clap::Args)]
pub struct Args {
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
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        file,
        bound,
        model,
        alpha,
        log,
        score_log,
    } = a;
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
    ExitCode::SUCCESS
}
