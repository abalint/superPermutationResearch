//! `nrpa` — nested rollout policy adaptation over a class's sojourn grammar.

use std::path::PathBuf;
use std::process::ExitCode;

use superperm::beam::Scorer;
use superperm::graph::Graph;
use superperm::trace::trace_string;

use super::{load_model, load_profile, yn, BoundArg};

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
    /// Nesting depth (1 = adapt over plain rollouts; 2-3 typical).
    #[arg(long, default_value_t = 2)]
    level: u32,
    /// Iterations per nesting level (iters^level rollouts total).
    #[arg(long, default_value_t = 30)]
    iters: u32,
    /// Adaptation step size (Rosin's alpha).
    #[arg(long, default_value_t = 1.0)]
    adapt: f64,
    /// RNG seed; runs are deterministic given it.
    #[arg(long, default_value_t = 0)]
    seed: u64,
    /// Visited-perm count at which rollouts hand off to the beam
    /// tail (clamped to n!).
    #[arg(long, default_value_t = 450)]
    switch_depth: usize,
    /// Beam width of the tail completion.
    #[arg(long, default_value_t = 2000)]
    tail_width: usize,
    /// Admissible length cap for the tail beam (0 = uncapped;
    /// capped tails can die, which scores the rollout dead).
    #[arg(long, default_value_t = 0)]
    max_len: u32,
    /// Tail scorer bound (default residual — the best completer).
    #[arg(long, value_enum)]
    bound: Option<BoundArg>,
    /// Compose the tail scorer with this learned model (T2).
    #[arg(long)]
    model: Option<PathBuf>,
    /// Blend factor for the composed tail score.
    #[arg(long, default_value_t = 0.25)]
    alpha: f64,
    /// Allow --model files trained for a different n.
    #[arg(long, requires = "model")]
    allow_n_mismatch: bool,
    /// Waste prior on the rollout logits: each move's logit gets
    /// -prior * (extra chars beyond 1 per perm), so the untrained
    /// policy favours cheap moves. 0 = classic uniform-start NRPA.
    #[arg(long, default_value_t = 0.0)]
    prior: f64,
    /// On an in-grammar dead-end, complete the partial prefix with
    /// the (unconstrained) beam tail instead of scoring the rollout
    /// dead — every rollout then returns a graded score, which a
    /// class too tight for random play needs to bootstrap learning.
    #[arg(long)]
    early_tail: bool,
    /// Warm-start the policy from these superpermutation string
    /// files (e.g. known records): each first-visit path is
    /// replayed as a grammar move sequence and the policy adapted
    /// toward it before the search (Track C policy initialization).
    #[arg(long)]
    warm_start: Vec<PathBuf>,
    /// Visited-perm depth of the warm-start prefix (0 = up to the
    /// switch depth).
    #[arg(long, default_value_t = 0, requires = "warm_start")]
    warm_depth: usize,
    /// Adapt passes over the warm-start sequence.
    #[arg(long, default_value_t = 3, requires = "warm_start")]
    warm_reps: u32,
    /// Collect every distinct completed walk of length <= this and
    /// print them all at the end (0 = off) — the M3 hunt wants all
    /// distinct <=872 walks, not just the best.
    #[arg(long, default_value_t = 0)]
    collect: u32,
    /// Suppress per-iteration progress lines.
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
        level,
        iters,
        adapt,
        seed,
        switch_depth,
        tail_width,
        max_len,
        bound,
        model,
        alpha,
        allow_n_mismatch,
        prior,
        early_tail,
        warm_start,
        warm_depth,
        warm_reps,
        collect,
        quiet,
    } = a;
    use superperm::nrpa::{nrpa_search, NrpaCfg};
    use superperm::sojourn::ClassCaps;
    assert_eq!(class.len(), 5, "--class needs S,d3,d4,d5,ip");
    let g = Graph::new(n);
    let caps = ClassCaps {
        s: class[0],
        d3: class[1],
        d4: class[2],
        d5: class[3],
        ip: class[4],
    };
    let loaded = model.map(|path| load_model(&path, n, allow_n_mismatch));
    let b = bound.unwrap_or(BoundArg::Residual);
    let bname = b.name();
    let (tail_scorer, tdesc) = match &loaded {
        Some(m) => (
            Scorer::Composed {
                bound: b.into(),
                model: m,
                alpha,
            },
            format!("bound={bname}+model={} alpha={alpha}", m.kind()),
        ),
        None => (Scorer::Bound(b.into()), format!("bound={bname}")),
    };
    println!(
        "nrpa n={n} class=(S={},d3={},d4={},d5={},ip={}) waste={} level={level} iters={iters} adapt={adapt} prior={prior} seed={seed} switch={switch_depth} tail: width={tail_width} {tdesc} max_len={max_len}",
        caps.s,
        caps.d3,
        caps.d4,
        caps.d5,
        caps.ip,
        caps.waste(),
    );
    let warm: Vec<Vec<u32>> = warm_start
        .iter()
        .map(|path| {
            let text = std::fs::read_to_string(path).unwrap_or_else(|e| {
                eprintln!("cannot read --warm-start {}: {e}", path.display());
                std::process::exit(1);
            });
            let tr = trace_string(&g, text.trim()).unwrap_or_else(|e| {
                eprintln!("--warm-start {}: {e}", path.display());
                std::process::exit(1);
            });
            let depth = if warm_depth == 0 {
                switch_depth
            } else {
                warm_depth
            }
            .min(tr.path.len());
            tr.path[1..depth].to_vec()
        })
        .collect();
    let cfg = NrpaCfg {
        g: &g,
        caps,
        profile: load_profile(records_profile, profile_file.as_ref(), n),
        fresh_doors,
        level,
        iters,
        adapt_alpha: adapt,
        seed,
        switch_depth,
        tail_width,
        max_len,
        tail_scorer,
        prior,
        early_tail,
        warm_start: warm,
        warm_reps,
        collect_max: collect,
        verbose: !quiet,
    };
    let t = std::time::Instant::now();
    let r = nrpa_search(&cfg);
    let dt = t.elapsed().as_secs_f64();
    println!(
        "rollouts = {} (dead {}, of which in-grammar {}) elapsed = {dt:.1}s",
        r.rollouts, r.dead, r.dead_in_grammar
    );
    println!(
        "in-grammar depth (visited perms at hand-off/death): min {} mean {:.1} max {}",
        r.depth_min, r.depth_mean, r.depth_max
    );
    if collect > 0 {
        println!(
            "collected {} distinct walks <= {collect}:",
            r.collected.len()
        );
        for s in &r.collected {
            let v = superperm::validate::validate(n, s);
            println!("  len {} complete={} {s}", s.len(), yn(v.complete));
        }
    }
    match (r.best_len, r.string) {
        (Some(len), Some(s)) => {
            let v = superperm::validate::validate(n, &s);
            println!(
                "nrpa best: length {len} (validated complete = {})",
                yn(v.complete)
            );
            println!("{s}");
            if !v.complete || v.length != len as usize {
                eprintln!("VALIDATION FAILED — do not believe this result");
                return ExitCode::FAILURE;
            }
        }
        _ => {
            println!("nrpa: NO completion found (all rollouts dead)");
        }
    }
    ExitCode::SUCCESS
}
