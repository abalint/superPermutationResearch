//! `sojourn-dfs` — the Track B L2 canonical opening DFS (M2 gate).

use std::io::Write;
use std::path::PathBuf;
use std::process::ExitCode;

use superperm::graph::Graph;

use super::{load_profile, DedupArg};

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
    /// Opening depth in completed sojourns.
    #[arg(long, default_value_t = 10)]
    depth: u16,
    /// Hard node budget (reported honestly if hit).
    #[arg(long, default_value_t = 10_000_000)]
    max_nodes: u64,
    /// Dedup tier: exact state, relabeling-orbit quotient (sound,
    /// the L2 default), or canonical-key abstraction (book mode,
    /// not exhaustion-sound).
    #[arg(long, value_enum, default_value_t = DedupArg::Orbit)]
    dedup: DedupArg,
    /// Abstraction mode only: exact exemplars expanded per class.
    #[arg(long, default_value_t = 1)]
    exemplars: u32,
    /// Write frontier exemplars to this TSV file (class key, len,
    /// ledger, first-visit rank path) — beam seeds for
    /// `beam --seed-file` (T3).
    #[arg(long)]
    dump_frontier: Option<PathBuf>,
    /// Frontier exemplars dumped per canonical class (with
    /// --dump-frontier).
    #[arg(long, default_value_t = 1, requires = "dump_frontier")]
    dump_per_class: u32,
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        class,
        records_profile,
        profile_file,
        fresh_doors,
        depth,
        max_nodes,
        dedup,
        exemplars,
        dump_frontier,
        dump_per_class,
    } = a;
    use superperm::sojourn::{ClassCaps, SojournDfs};
    assert_eq!(class.len(), 5, "--class needs S,d3,d4,d5,ip");
    let g = Graph::new(n);
    let caps = ClassCaps {
        s: class[0],
        d3: class[1],
        d4: class[2],
        d5: class[3],
        ip: class[4],
    };
    let dfs = SojournDfs {
        g: &g,
        caps,
        profile: load_profile(records_profile, profile_file.as_ref(), n),
        fresh_doors,
        depth,
        max_nodes,
        dedup: dedup.into(),
        exemplars_per_class: exemplars,
        dump_per_class: if dump_frontier.is_some() {
            dump_per_class
        } else {
            0
        },
    };
    let t = std::time::Instant::now();
    let st = dfs.run();
    println!(
        "sojourn-dfs n={n} class=(S={},d3={},d4={},d5={},ip={}) waste={} depth={depth}{}",
        caps.s,
        caps.d3,
        caps.d4,
        caps.d5,
        caps.ip,
        caps.waste(),
        if fresh_doors { " fresh-doors" } else { "" },
    );
    println!("nodes             = {}", st.nodes);
    println!("frontier states   = {}", st.frontier);
    println!("canonical classes = {}", st.canonical_classes);
    println!("dead ends         = {}", st.dead_ends);
    println!("completed walks   = {}", st.completed);
    println!(
        "oversize          = {} (max_nodes {max_nodes})",
        st.oversize
    );
    println!("elapsed           = {:.3}s", t.elapsed().as_secs_f64());
    if let Some(path) = dump_frontier {
        let f = std::fs::File::create(&path).expect("create frontier dump file");
        let mut f = std::io::BufWriter::new(f);
        writeln!(f, "# class_key\tlen\ts\td3\td4\td5\tip\tpath").unwrap();
        for seed in &st.dump {
            let ranks: Vec<String> = seed.path.iter().map(u32::to_string).collect();
            writeln!(
                f,
                "{:032x}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
                seed.class_key,
                seed.len,
                seed.s,
                seed.d3,
                seed.d4,
                seed.d5,
                seed.ip,
                ranks.join(",")
            )
            .unwrap();
        }
        println!(
            "frontier dump     = {} seeds ({} per class) -> {}",
            st.dump.len(),
            dump_per_class,
            path.display()
        );
    }
    ExitCode::SUCCESS
}
