//! `union-dfs` — exhaustive bound-capped DFS inside the corpus edge union.

use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use superperm::graph::Graph;

use super::BoundArg;

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
    /// Record directories, comma-separated.
    #[arg(long, value_delimiter = ',')]
    dirs: Vec<PathBuf>,
    /// Admissible length cap: walks longer than this are pruned.
    #[arg(long)]
    cap: u32,
    /// Write distinct finds ≤ cap into this dir.
    #[arg(long)]
    out_dir: Option<PathBuf>,
    /// Pruning bound (residual dominates cycle, costs more per node).
    #[arg(long, value_enum, default_value_t = BoundArg::Cycle)]
    bound: BoundArg,
    /// Transposition pruning (decision mode; kills enumeration).
    #[arg(long)]
    tt: bool,
    /// Max transposition entries (~150 B each at n=6; the default
    /// is ~7 GB worst case — size to the machine).
    #[arg(long, default_value_t = 50_000_000)]
    tt_max: usize,
    /// Off-union edge credits per walk (0 = pure tour-merge).
    #[arg(long, default_value_t = 0)]
    free: u32,
    /// Max weight of an off-union edge.
    #[arg(long, default_value_t = 2)]
    free_w: u8,
    /// Node budget; hitting it makes the run TRUNCATED.
    #[arg(long, default_value_t = 200_000_000)]
    max_nodes: u64,
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        dirs,
        cap,
        out_dir,
        bound,
        tt,
        tt_max,
        free,
        free_w,
        max_nodes,
    } = a;
    let g = Graph::new(n);
    let dir_refs: Vec<&std::path::Path> = dirs.iter().map(|p| p.as_path()).collect();
    let corpus = superperm::corpus::load_corpus(&g, &dir_refs).unwrap_or_else(|e| {
        eprintln!("{e}");
        std::process::exit(1);
    });
    let ub = match bound {
        BoundArg::Cycle => superperm::unionsearch::UnionBound::Cycle,
        BoundArg::Residual => superperm::unionsearch::UnionBound::Residual,
        BoundArg::Arc => {
            eprintln!("union-dfs supports --bound cycle|residual");
            return ExitCode::from(2);
        }
    };
    let adj = superperm::unionsearch::union_adjacency(&g, &corpus);
    let union_edges: usize = adj.iter().map(|l| l.len()).sum();
    println!(
        "corpus = {} records; union graph = {union_edges} edges, max out-degree {}",
        corpus.len(),
        adj.iter().map(|l| l.len()).max().unwrap_or(0)
    );
    println!(
        "claim supported: {}",
        if tt {
            "decision/optimality only (--tt collapses equal-length walks)"
        } else {
            "enumeration: all distinct walks <= cap"
        }
    );
    let cfg = superperm::unionsearch::UnionCfg {
        cap,
        bound: ub,
        tt,
        tt_max,
        free,
        free_w,
        max_nodes,
    };
    let t0 = Instant::now();
    let res = superperm::unionsearch::UnionSearch::new(&g, &corpus, cfg).run();
    let dt = t0.elapsed();
    println!(
        "nodes = {} ({:.0}/s), bound prunes = {}, strand prunes = {}, dead ends = {}, tt prunes = {}{}",
        res.nodes,
        res.nodes as f64 / dt.as_secs_f64(),
        res.bound_prunes,
        res.strand_prunes,
        res.dead_ends,
        res.tt_prunes,
        if res.tt_saturated {
            " (TT SATURATED)"
        } else {
            ""
        }
    );
    println!("max depth (visited perms) = {}", res.max_depth);
    println!(
        "completions = {}, distinct finds <= {cap} = {}",
        res.completions,
        res.finds.len()
    );
    if let Some(dir) = &out_dir {
        fs::create_dir_all(dir).expect("create out dir");
    }
    for s in &res.finds {
        let name = format!(
            "{}.u-{:07x}.txt",
            s.len(),
            superperm::recomb::fnv1a64(s) & 0xfff_ffff
        );
        println!("  find: {name} (len {})", s.len());
        if let Some(dir) = &out_dir {
            fs::write(dir.join(&name), s).expect("write find");
        }
    }
    println!("elapsed = {dt:.2?}");
    println!(
        "verdict: {}",
        if res.complete {
            "COMPLETE"
        } else {
            "TRUNCATED"
        }
    );
    ExitCode::SUCCESS
}
