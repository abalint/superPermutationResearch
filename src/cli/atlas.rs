//! `atlas` — the Track B T1 door atlas, as TSV on stdout.

use std::io::{BufWriter, Write};
use std::process::ExitCode;

use superperm::graph::Graph;

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (3..=8).
    #[arg(short, long)]
    n: usize,
    /// Minimum door weight to include (default 3; 2 adds w2x/i2).
    #[arg(long, default_value_t = 3)]
    min_weight: u8,
}

pub fn run(a: Args) -> ExitCode {
    let Args { n, min_weight } = a;
    let g = Graph::new(n);
    // In-cycle offset: number of weight-1 rotations from the
    // cycle's representative (lowest-ranked member) to the perm.
    let mut offset = vec![0u8; g.nfact];
    for cid in 0..g.cycle_count {
        let rep = (0..g.nfact)
            .find(|&r| g.cycle_id[r] == cid as u32)
            .expect("nonempty cycle");
        let mut cur = rep;
        for off in 0..n {
            offset[cur] = off as u8;
            cur = g.succ1(cur as u32) as usize;
        }
        debug_assert_eq!(cur, rep);
    }
    let out = std::io::stdout();
    let mut w = BufWriter::new(out.lock());
    writeln!(
        w,
        "from_rank\tweight\tto_rank\tfrom_cycle\tfrom_off\tto_cycle\tto_off\tinterior_perm_ranks"
    )
    .unwrap();
    for r in 0..g.nfact {
        let p = &g.perms[r];
        for &(q, wt) in &g.succs[r] {
            if wt < min_weight {
                continue;
            }
            let qp = &g.perms[q as usize];
            // appended chars are qp[n-wt..]; interior window after
            // j appended chars (1 <= j < wt) is p[j..] + qp[n-wt..n-wt+j]
            let mut interior = Vec::new();
            for j in 1..wt as usize {
                let mut win: Vec<u8> = p[j..].to_vec();
                win.extend_from_slice(&qp[n - wt as usize..n - wt as usize + j]);
                let mut mask = 0u16;
                for &v in &win {
                    mask |= 1 << v;
                }
                if mask == ((1u16 << n) - 1) << 1 {
                    interior.push(superperm::graph::rank(&win).to_string());
                }
            }
            writeln!(
                w,
                "{r}\t{wt}\t{q}\t{}\t{}\t{}\t{}\t{}",
                g.cycle_id[r],
                offset[r],
                g.cycle_id[q as usize],
                offset[q as usize],
                interior.join(";")
            )
            .unwrap();
        }
    }
    ExitCode::SUCCESS
}
