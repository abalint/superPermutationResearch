//! `cert-verify` — clean-room verification of the n=6 gain-one
//! kernel-chain certificate (claims C1-C5).

use std::process::ExitCode;
use std::time::Instant;

use super::{agree, yn};

#[derive(clap::Args)]
pub struct Args {
    /// Number of symbols (the certificate is defined for n = 6 only).
    #[arg(short, long)]
    n: usize,
}

pub fn run(a: Args) -> ExitCode {
    let Args { n } = a;
    if n != 6 {
        eprintln!("cert-verify: the certificate is defined for n = 6 only (got {n})");
        std::process::exit(1);
    }
    use superperm::cert::{waste_and_length, Cert};
    let cert = Cert::new();
    println!("cert-verify n=6: clean-room verification of the gain-one kernel-chain certificate");
    println!(
        "construction gates passed: 144 loops, tv period 5, entry-orbit distinctness, \
         door(s,2)=e' splice identity, per-class orbit partition"
    );
    println!();

    // C1: forced map.
    let hops = cert.audit_hops();
    let forced = cert.forced_audit();
    let cycles: Vec<String> = forced
        .cycle_lengths
        .iter()
        .map(|(len, count)| format!("len {len} x{count}"))
        .collect();
    let c1_ok = forced.total_map
        && forced.is_permutation
        && forced.cycle_lengths.len() == 1
        && forced.cycle_lengths.get(&4) == Some(&180);
    println!("C1 forced map (exit skip-0 splice, cost-3 hop):");
    println!(
        "  valid hop targets per (loop,splice) pair, by cost 3/4/5/6 = {}/{}/{}/{} of {} \
         (cost-3 target unique per pair: {})",
        hops.valid_by_cost[0],
        hops.valid_by_cost[1],
        hops.valid_by_cost[2],
        hops.valid_by_cost[3],
        hops.pairs,
        hops.valid_by_cost[0] == hops.pairs
    );
    println!(
        "  total map = {}, permutation = {}, cycles = [{}]",
        forced.total_map,
        forced.is_permutation,
        cycles.join(", ")
    );
    println!(
        "  CLAIM permutation with all cycles length 4: {}",
        agree(c1_ok)
    );
    println!();

    // C2: pivot confinement.
    let c2_ok = hops.pivot_violations == 0 && hops.non_entry_landings == 0;
    println!("C2 pivot confinement:");
    println!(
        "  pivot preserved   = {} violations in {} hop words",
        hops.pivot_violations,
        hops.pairs * 4
    );
    println!(
        "  landing on entry  = automatic ({} exceptions)",
        hops.non_entry_landings
    );
    println!(
        "  class partition   = each pivot class's 24 loops cover the 120 orbits exactly \
         once (asserted at construction)"
    );
    println!(
        "  CLAIM chains confined to one pivot class, in-class orbit-disjointness automatic: {}",
        agree(c2_ok)
    );
    println!();

    // C3: exhaustive chain search per pivot class.
    println!("C3 exhaustive chain search (identity-started, hops cost 3..=6):");
    let t0 = Instant::now();
    let mut global_max = i64::MIN;
    let mut all_best = Vec::new();
    for pivot in 1..=6u8 {
        let s = cert.search_class(pivot);
        let mut breakdown = std::collections::BTreeMap::new();
        for c in &s.chains {
            let st = c.stats();
            *breakdown.entry((st.k, st.sigma, st.f4)).or_insert(0usize) += 1;
        }
        let bd: Vec<String> = breakdown
            .iter()
            .map(|((k, sg, f4), cnt)| format!("(K={k},S={sg},f4={f4}) x{cnt}"))
            .collect();
        println!(
            "  pivot {pivot}: max V = {}, chains at max = {}, nodes = {}, {}",
            s.max_v,
            s.chains.len(),
            s.nodes,
            bd.join(" ")
        );
        if s.max_v > global_max {
            global_max = s.max_v;
            all_best.clear();
        }
        if s.max_v == global_max {
            all_best.extend(s.chains);
        }
    }
    let c3_time = t0.elapsed();
    let mut total_bd = std::collections::BTreeMap::new();
    for c in &all_best {
        let st = c.stats();
        *total_bd.entry((st.k, st.sigma, st.f4)).or_insert(0usize) += 1;
    }
    let bd: Vec<String> = total_bd
        .iter()
        .map(|((k, sg, f4), cnt)| format!("(K={k},Sigma={sg},f4={f4}) x{cnt}"))
        .collect();
    println!(
        "  global: max V = {global_max}, chains at max = {}, breakdown {} ({:.2}s)",
        all_best.len(),
        bd.join(" "),
        c3_time.as_secs_f64()
    );
    println!("  V = 12 reachable: {}", global_max >= 12);
    let c3_ok = global_max == 8
        && all_best.len() == 12
        && total_bd.get(&(22, 14, 0)) == Some(&6)
        && total_bd.get(&(20, 8, 1)) == Some(&6);
    println!(
        "  CLAIM max V = 8 by exactly 12 chains (6 x (K=22,Sigma=14,f4=0) + 6 x \
         (K=20,Sigma=8,f4=1)), V = 12 unreachable: {}",
        agree(c3_ok)
    );
    println!();

    // C4: cover search over the optimal chains + positive control.
    println!("C4 rooted-cover search:");
    let t1 = Instant::now();
    let mut any_rooted = false;
    for (i, chain) in all_best.iter().enumerate() {
        let st = chain.stats();
        let r = cert.cover_search(chain, false);
        any_rooted |= r.rooted_covers > 0;
        println!(
            "  chain {:2} (pivot {}, K={:2}, Sigma={:2}, f4={}): roots={}, non-root={}, \
             rows={}, exact covers={}, rooted covers={}",
            i + 1,
            cert.loops[chain.loops[0]].pivot,
            st.k,
            st.sigma,
            st.f4,
            r.roots,
            r.non_root,
            r.rows,
            r.exact_covers,
            r.rooted_covers
        );
    }
    let kernel = cert.standard_kernel(6);
    let ks = kernel.stats();
    let control = cert.cover_search(&kernel, true);
    let c4_time = t1.elapsed();
    println!(
        "  control (standard kernel, pivot 6, K={}, Sigma={}, V={}): roots={}, \
         non-root={}, rows={}, rooted cover found = {}",
        ks.k,
        ks.sigma,
        ks.v,
        control.roots,
        control.non_root,
        control.rows,
        control.rooted_covers >= 1
    );
    println!("  ({:.2}s)", c4_time.as_secs_f64());
    let c4_ok = !any_rooted && control.rooted_covers >= 1;
    println!(
        "  CLAIM all optimal chains admit zero rooted covers; standard kernel admits one: {}",
        agree(c4_ok)
    );
    println!();

    // C5: ledger arithmetic.
    let (w4, l4) = waste_and_length(4);
    let (w8, l8) = waste_and_length(8);
    let c5_ok = (w4, l4) == (147, 872) && (w8, l8) == (146, 871);
    println!("C5 ledger arithmetic:");
    println!("  V = 4 -> waste {w4}, length {l4}; V = 8 -> waste {w8}, length {l8}");
    println!(
        "  CLAIM standard kernel gives waste 147 / length 872; V = 8 would give 146 / 871: {}",
        agree(c5_ok)
    );
    println!();

    println!("verdict table:");
    println!("  claim | computed | agree");
    println!(
        "  C1 forced map, all cycles length 4 | permutation={}, cycles=[{}] | {}",
        forced.is_permutation,
        cycles.join(", "),
        yn(c1_ok)
    );
    println!(
        "  C2 pivot confinement | {} pivot / {} entry violations | {}",
        hops.pivot_violations,
        hops.non_entry_landings,
        yn(c2_ok)
    );
    println!(
        "  C3 max V = 8 by exactly 12 chains | max V = {global_max}, {} chains, {} | {}",
        all_best.len(),
        bd.join(" "),
        yn(c3_ok)
    );
    println!(
        "  C4 optimal chains uncoverable, control coverable | rooted covers: chains {}, \
         control found {} | {}",
        if any_rooted { ">=1" } else { "all 0" },
        control.rooted_covers >= 1,
        yn(c4_ok)
    );
    println!(
        "  C5 waste arithmetic | V=4 -> {w4}/{l4}, V=8 -> {w8}/{l8} | {}",
        yn(c5_ok)
    );
    if !(c1_ok && c2_ok && c3_ok && c4_ok && c5_ok) {
        println!();
        println!("DISCREPANCY: at least one claim disagrees with this clean-room verification.");
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
