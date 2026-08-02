//! `recomb` — record-pair splice closure over the braid state-DAG.

use std::fs;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use superperm::graph::Graph;

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
    /// Record directories, comma-separated.
    #[arg(long, value_delimiter = ',')]
    dirs: Vec<PathBuf>,
    /// Emit new hybrid strings (+ provenance.tsv) into this dir.
    #[arg(long)]
    emit_dir: Option<PathBuf>,
    /// Refuse to enumerate closures larger than this.
    #[arg(long, default_value_t = 100_000)]
    max_walks: u128,
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        dirs,
        emit_dir,
        max_walks,
    } = a;
    let g = Graph::new(n);
    let dir_refs: Vec<&std::path::Path> = dirs.iter().map(|p| p.as_path()).collect();
    let corpus = superperm::corpus::load_corpus(&g, &dir_refs).unwrap_or_else(|e| {
        eprintln!("{e}");
        std::process::exit(1);
    });
    let t0 = Instant::now();
    let braid = superperm::recomb::Braid::build(&g, &corpus);
    let r = braid.probe(&corpus, max_walks).unwrap_or_else(|e| {
        eprintln!("{e}");
        std::process::exit(1);
    });
    println!("records = {}", r.records);
    println!("braid states = {}", r.states);
    println!("braid edges = {}", r.edges);
    println!("terminal states = {}", r.terminals);
    println!("out-junctions (>=2 out-edges) = {}", r.out_junctions);
    println!("in-junctions (>=2 in-edges) = {}", r.in_junctions);
    println!("closure path count = {}", r.path_count);
    println!("out-junctions per 100-perm depth band:");
    for (b, c) in r.junction_depth_hist.iter().enumerate() {
        if *c > 0 {
            println!("  {}..{}: {c}", b * 100, b * 100 + 99);
        }
    }
    if !r.enumerated {
        println!("closure larger than --max-walks {max_walks}; enumeration skipped");
    } else {
        println!("new hybrids = {}", r.hybrids.len());
        if let Some(dir) = emit_dir {
            fs::create_dir_all(&dir).expect("create emit dir");
            let mut prov = BufWriter::new(
                fs::File::create(dir.join("provenance.tsv")).expect("provenance.tsv"),
            );
            writeln!(prov, "file\tsegments (record:step_lo-step_hi)").unwrap();
            for h in &r.hybrids {
                let name = format!(
                    "{}.h-{:07x}.txt",
                    h.len,
                    superperm::recomb::fnv1a64(&h.string) & 0xfff_ffff
                );
                fs::write(dir.join(&name), &h.string).expect("write hybrid");
                let segs: Vec<String> = h
                    .segments
                    .iter()
                    .map(|s| format!("{}:{}-{}", s.record, s.step_lo, s.step_hi))
                    .collect();
                writeln!(prov, "{name}\t{}", segs.join(";")).unwrap();
                println!("  {name} ({} segments)", h.segments.len());
            }
        }
    }
    println!("elapsed = {:.2?}", t0.elapsed());
    ExitCode::SUCCESS
}
