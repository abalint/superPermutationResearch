//! `rollouts` — epsilon-greedy rollouts, written as JSONL feature records.

use std::fs;
use std::io::BufWriter;
use std::path::PathBuf;
use std::process::ExitCode;

use superperm::graph::Graph;
use superperm::rollout::{run_rollouts_strings, Guide};

use super::load_model;

#[derive(clap::Args)]
pub struct Args {
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
    /// Also write each completed rollout's superpermutation string
    /// (one per line) to this file.
    #[arg(long)]
    strings: Option<PathBuf>,
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        count,
        epsilon,
        seed,
        model,
        alpha,
        out,
        strings,
    } = a;
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
    let mut strings_writer = strings.map(|p| {
        BufWriter::new(fs::File::create(&p).unwrap_or_else(|e| {
            eprintln!("cannot create {}: {e}", p.display());
            std::process::exit(1);
        }))
    });
    let s = run_rollouts_strings(
        &g,
        count,
        epsilon,
        seed,
        guide,
        &mut writer,
        strings_writer
            .as_mut()
            .map(|w| w as &mut dyn std::io::Write),
    )
    .expect("rollout write failed");
    println!(
        "rollouts n={n} count={} epsilon={epsilon} seed={seed}{mdesc}",
        s.rollouts
    );
    println!("mean final length = {:.2}", s.mean_len);
    println!("min final length  = {}", s.min_len);
    println!("lines written     = {} -> {}", s.lines, out.display());
    ExitCode::SUCCESS
}
