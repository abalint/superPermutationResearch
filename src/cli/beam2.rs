//! `beam2` — the two-ended (deque) beam search.

use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use superperm::beam::Jitter;
use superperm::beam2::{beam2_search, Scorer2};
use superperm::graph::Graph;

use super::load_model;

#[derive(clap::Args)]
pub struct Args {
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
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        width,
        model,
        alpha,
        jitter,
        jitter_seed,
    } = a;
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
    ExitCode::SUCCESS
}
