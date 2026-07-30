//! s38 measurement probes (SURGERY-DESIGN §10.8) — all `#[ignore]`d;
//! run with `cargo test --release --test s38_measure -- --ignored
//! --nocapture`. These are the diagnostics behind the s38 verdict that
//! the natural 2-compound is not expressible at anchored reach:
//! `oracle_reach_450` (extraction direction: identity and compound
//! price +6 over equal), `oracle_absorption_450` (the mirror move —
//! absorb the tail part into the prefix ride — also +6: the 181 seam
//! is w2-entered), and `seam_partner_census` (equal-cost completion
//! rates by net/singleton at anchor 570, the T1/T2 calibration data).

use superperm::graph::Graph;
use superperm::tailatsp::*;

#[test]
#[ignore]
fn oracle_reach_450() {
    let g = Graph::new(6);
    let dir = std::path::Path::new("data/compound_specimens");
    let corpus = superperm::corpus::load_corpus(&g, &[dir]).expect("specimens");
    let a_side = corpus
        .iter()
        .find(|r| r.name.contains("55088ebb4107"))
        .expect("A side");
    let inst = decompose(6, &a_side.trace, 520).expect("decompose");
    println!("anchor={} blocks={}", inst.anchor_depth, inst.blocks.len());
    let exts = enumerate_extractions(6, &g, &a_side.trace, &inst);
    for e in &exts {
        println!(
            "ext candidate: cycle-min-rank={} depth={} nperms={} heal={}",
            e.cycle, e.entry_depth, e.nperms, e.heal
        );
    }
    let c126354 = superperm::graph::rank(&[1, 2, 6, 3, 5, 4]) as u32;
    let c123654 = superperm::graph::rank(&[1, 2, 3, 6, 5, 4]) as u32;
    let ext = exts
        .iter()
        .find(|e| e.cycle == c126354 && e.entry_depth == 181)
        .expect("126354@181");
    let ei = apply_extraction(6, &g, &inst, ext, 0);
    let prefix = healed_prefix(6, &a_side.string, inst.prefix_chars, ext);
    assert_eq!(prefix.len(), ei.prefix_chars);
    let groups = recomp_variants_by_cycle(6, &g, &ei);
    let whole6 = |cid: u32| -> Vec<&RecompMove> {
        groups
            .iter()
            .find(|(c, _)| *c == cid)
            .expect("cycle")
            .1
            .iter()
            .filter(|m| m.arcs.len() == 1 && m.arcs[0].1 == 6)
            .collect()
    };
    let va = whole6(c126354);
    let vb = whole6(c123654);
    println!("whole6 variants: {} x {}", va.len(), vb.len());
    let src_len = a_side.string.len();
    // also: true optimum of the B-entry compound (loose incumbent)
    {
        let a = va
            .iter()
            .find(|m| superperm::graph::unrank(6, m.arcs[0].0 as usize) == [2, 6, 3, 5, 4, 1])
            .unwrap();
        let b = vb
            .iter()
            .find(|m| superperm::graph::unrank(6, m.arcs[0].0 as usize) == [2, 3, 6, 5, 4, 1])
            .unwrap();
        let intra_m = ei.intra + a.remove.len() + b.remove.len() - a.arcs.len() - b.arcs.len();
        let inc = src_len + 1 - ei.prefix_chars - intra_m;
        let m = apply_recomp_multi(6, &g, &ei, &[a, b], 10_000);
        let t0 = std::time::Instant::now();
        let (mopt, morder, _) = solve_bb(&m, false, 0);
        let s = superperm::tailatsp::materialize_from_prefix(6, &g, &prefix, &m, &morder);
        let v = superperm::validate::validate(6, &s);
        println!(
            "TRUE OPT of B-entry compound: {} (equal target {}) len={} complete={} {:.1}s",
            mopt,
            inc - 1,
            s.len(),
            v.complete,
            t0.elapsed().as_secs_f64()
        );
        // and the extraction-identity instance (no recomps)
        let m0 = apply_recomp_multi(6, &g, &ei, &[], 10_000);
        let (m0opt, _, _) = solve_bb(&m0, false, 0);
        println!(
            "extraction-identity true opt: {} (equal target {})",
            m0opt,
            src_len - ei.prefix_chars - ei.intra
        );
    }
    for a in &va {
        for b in &vb {
            let intra_m = ei.intra + a.remove.len() + b.remove.len() - a.arcs.len() - b.arcs.len();
            let inc = src_len + 1 - ei.prefix_chars - intra_m;
            let m = apply_recomp_multi(6, &g, &ei, &[a, b], inc);
            let t0 = std::time::Instant::now();
            let (mopt, morder, _) = solve_bb(&m, false, 0);
            let ea = superperm::graph::unrank(6, a.arcs[0].0 as usize);
            let eb = superperm::graph::unrank(6, b.arcs[0].0 as usize);
            let mut verdict = "none".to_string();
            if mopt < inc {
                let s = superperm::tailatsp::materialize_from_prefix(6, &g, &prefix, &m, &morder);
                let v = superperm::validate::validate(6, &s);
                verdict = format!("len={} complete={}", s.len(), v.complete);
                if v.complete && s.len() == src_len {
                    let t = superperm::trace::trace_string(&g, &s).unwrap();
                    verdict = format!("{verdict} alloc={:?}", allocation_of(&t));
                }
            }
            println!(
                "entry {:?} x {:?}: inc={} mopt={} [{}] {:.2}s",
                ea,
                eb,
                inc,
                mopt,
                verdict,
                t0.elapsed().as_secs_f64()
            );
        }
    }
}

#[test]
#[ignore]
fn oracle_absorption_450() {
    use superperm::graph::{rank, unrank};
    let g = Graph::new(6);
    let dir = std::path::Path::new("data/compound_specimens");
    let corpus = superperm::corpus::load_corpus(&g, &[dir]).expect("specimens");
    let a_side = corpus
        .iter()
        .find(|r| r.name.contains("55088ebb4107"))
        .expect("A side");
    let t = &a_side.trace;
    for anchor in [450usize, 520] {
        let inst = decompose(6, t, anchor).expect("decompose");
        println!(
            "== anchor={} blocks={}",
            inst.anchor_depth,
            inst.blocks.len()
        );
        // absorption by hand: tail block (263541 x2) of cycle 126354 absorbed
        // into the prefix part @181 (entry 354126 x4) by PREPENDING.
        let tail_entry = rank(&[2, 6, 3, 5, 4, 1]) as u32;
        let bi = inst
            .blocks
            .iter()
            .position(|b| b.entry == tail_entry && b.nperms == 2)
            .expect("tail part of 126354");
        // part @181..184 (1-indexed): 0-idx 180..183; x = path[179]
        let i1 = 180usize;
        let w_in = t.weights[i1 - 1] as usize;
        let x = t.path[i1 - 1];
        let w_new = {
            let px = unrank(6, x as usize);
            let pe = unrank(6, tail_entry as usize);
            6 - Graph::overlap(&px, &pe)
        };
        let cut_start = 6 + t.weights[..i1].iter().map(|&w| w as usize).sum::<usize>() - w_in;
        // hmm: chars through x (0-idx i1-1) = 6 + sum(weights[..i1-1])
        let chars_through_x = 6 + t.weights[..i1 - 1]
            .iter()
            .map(|&w| w as usize)
            .sum::<usize>();
        assert_eq!(cut_start, chars_through_x);
        // new prefix string
        let mut prefix = a_side.string[..chars_through_x].to_string();
        let pe = unrank(6, tail_entry as usize);
        for &d in &pe[6 - w_new..] {
            prefix.push((b'0' + d) as char);
        }
        // ride 2 steps: leading symbols of 263541, 635412
        let mut cur = tail_entry;
        for _ in 0..2 {
            let p = unrank(6, cur as usize);
            prefix.push((b'0' + p[0]) as char);
            cur = g.succ1(cur);
        }
        assert_eq!(cur, rank(&[3, 5, 4, 1, 2, 6]) as u32);
        prefix.push_str(&a_side.string[chars_through_x + w_in..inst.prefix_chars]);
        let new_prefix_chars = inst.prefix_chars + w_new + 2 - w_in;
        assert_eq!(prefix.len(), new_prefix_chars);
        println!(
            "w_in={} w_new={} prefix delta={}",
            w_in,
            w_new,
            w_new as i64 + 2 - w_in as i64
        );
        // modified instance: drop block bi
        let blocks: Vec<Block> = inst
            .blocks
            .iter()
            .enumerate()
            .filter(|(k, _)| *k != bi)
            .map(|(_, b)| Block {
                entry: b.entry,
                exit: b.exit,
                nperms: b.nperms,
            })
            .collect();
        let mut mi = superperm::tailatsp::TailInstance {
            anchor_depth: inst.anchor_depth,
            anchor_cur: inst.anchor_cur,
            prefix_chars: new_prefix_chars,
            cost: vec![],
            intra: inst.intra - 1,
            actual: 10_000,
            blocks,
        };
        // rebuild cost via apply_recomp_multi with no moves
        mi = apply_recomp_multi(6, &g, &mi, &[], 10_000);
        // absorption-identity: equal target
        let id_target = a_side.string.len() - mi.prefix_chars - mi.intra;
        let (id_opt, _, _) = solve_bb(&mi, false, 0);
        println!(
            "absorption-identity: true opt {} vs equal target {}",
            id_opt, id_target
        );
        // + the 123654 whole-6 merge in-tail
        let c123654 = rank(&[1, 2, 3, 6, 5, 4]) as u32;
        let groups = recomp_variants_by_cycle(6, &g, &mi);
        let vb: Vec<&RecompMove> = groups
            .iter()
            .find(|(c, _)| *c == c123654)
            .map(|(_, v)| {
                v.iter()
                    .filter(|m| m.arcs.len() == 1 && m.arcs[0].1 == 6)
                    .collect()
            })
            .unwrap_or_default();
        println!("123654 whole-6 variants in tail: {}", vb.len());
        for b in &vb {
            let intra_m = mi.intra + b.remove.len() - b.arcs.len();
            let inc = a_side.string.len() + 1 - mi.prefix_chars - intra_m;
            let m = apply_recomp_multi(6, &g, &mi, &[b], inc);
            let (mopt, morder, _) = solve_bb(&m, false, 0);
            let eb = unrank(6, b.arcs[0].0 as usize);
            if mopt < inc {
                let s = superperm::tailatsp::materialize_from_prefix(6, &g, &prefix, &m, &morder);
                let v = superperm::validate::validate(6, &s);
                let mut extra = String::new();
                if v.complete {
                    let tt = superperm::trace::trace_string(&g, &s).unwrap();
                    extra = format!(
                        " alloc={:?} lambda_ok={}",
                        allocation_of(&tt),
                        loop_relation(6, &g, &tt).holds
                    );
                }
                println!(
                    "  absorb + 123654@{:?}: mopt={} inc={} len={} complete={}{}",
                    eb,
                    mopt,
                    inc,
                    s.len(),
                    v.complete,
                    extra
                );
            } else {
                println!("  absorb + 123654@{:?}: no completion < {}", eb, inc);
            }
        }
    }
}

#[test]
#[ignore]
fn seam_partner_census() {
    let g = Graph::new(6);
    let dir = std::path::Path::new("data/surgery_specimens");
    let corpus = superperm::corpus::load_corpus(&g, &[dir]).expect("pair");
    let c5 = corpus
        .iter()
        .find(|r| r.name.contains("0105a4b77ce8"))
        .expect("(143,5) side");
    let inst = decompose(6, &c5.trace, 570).expect("decompose");
    let (opt, _, _) = solve_bb(&inst, false, 0);
    assert_eq!(opt, inst.actual);
    let src_len = c5.string.len();
    let groups = recomp_variants_by_cycle(6, &g, &inst);
    println!(
        "blocks={} cycles-with-variants={} total-variants={}",
        inst.blocks.len(),
        groups.len(),
        groups.iter().map(|(_, v)| v.len()).sum::<usize>()
    );
    let mut by_net_total = std::collections::BTreeMap::new();
    let mut by_net_equal = std::collections::BTreeMap::new();
    for (_cid, mvs) in &groups {
        for mv in mvs {
            let net = net_split(mv);
            *by_net_total
                .entry((net, has_singleton_arc(mv)))
                .or_insert(0u32) += 1;
            let intra_m = inst.intra + mv.remove.len() - mv.arcs.len();
            let inc = src_len + 1 - inst.prefix_chars - intra_m;
            let m = apply_recomp_multi(6, &g, &inst, &[mv], inc);
            let (mopt, _, _) = solve_bb(&m, false, 0);
            if mopt + 1 == inc {
                *by_net_equal
                    .entry((net, has_singleton_arc(mv)))
                    .or_insert(0u32) += 1;
            }
        }
    }
    println!("(net, has_singleton) -> total variants: {by_net_total:?}");
    println!("(net, has_singleton) -> equal-cost completions: {by_net_equal:?}");
}
