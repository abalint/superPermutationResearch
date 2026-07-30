//! Per-allocation sojourn-grammar pins (s27): the census-derived profile
//! files represent the community corpus — one committed specimen per
//! specimen-backed L0 allocation replays fully through its allocation's
//! caps + profile grammar (`data/upstream872_specimens/NOTE.md`; the
//! corpus-wide 22,062/22,062 result is JOURNAL s27).

use std::path::Path;

use superperm::graph::Graph;
use superperm::sojourn::{ClassCaps, Grammar, SplitProfile};
use superperm::trace::trace_string;

/// (caps, profile file stem, specimen file) per allocation.
const SPECIMENS: [([u16; 5], &str, &str); 8] = [
    ([145, 3, 0, 0, 0], "a145_3_0_0_0", "872.up-00005a46cfe3.txt"),
    ([143, 5, 0, 0, 0], "a143_5_0_0_0", "872.up-006185ae478a.txt"),
    ([140, 6, 1, 0, 0], "a140_6_1_0_0", "872.up-022441b7b1ff.txt"),
    ([142, 6, 0, 0, 0], "a142_6_0_0_0", "872.up-13f91236b67c.txt"),
    ([135, 9, 2, 0, 0], "a135_9_2_0_0", "872.up-009da25acce5.txt"),
    ([140, 8, 0, 0, 0], "a140_8_0_0_0", "872.up-249988a17b8a.txt"),
    ([138, 8, 1, 0, 0], "a138_8_1_0_0", "872.up-00b21d05e0f4.txt"),
    ([141, 7, 0, 0, 0], "a141_7_0_0_0", "872.up-6dbae421a839.txt"),
];

fn caps(c: [u16; 5]) -> ClassCaps {
    ClassCaps {
        s: c[0],
        d3: c[1],
        d4: c[2],
        d5: c[3],
        ip: c[4],
    }
}

fn load(stem: &str) -> SplitProfile {
    SplitProfile::from_file(
        Path::new(&format!("analysis/trackb/profiles/{stem}.txt")),
        6,
    )
    .expect("profile file parses")
}

fn specimen_seq(g: &Graph, file: &str) -> Vec<u32> {
    let s = std::fs::read_to_string(format!("data/upstream872_specimens/{file}"))
        .expect("specimen file readable");
    let tr = trace_string(g, s.trim()).expect("specimen traces");
    assert_eq!(tr.path.len(), g.nfact, "specimen covers all perms");
    assert_eq!(tr.path[0], 0, "specimen is identity-start");
    tr.path[1..].to_vec()
}

/// The census-generated records-allocation profile file is exactly the
/// hard-coded records profile (same allowed-composition set) — the
/// `--profile-file` path is a strict generalization, not a divergence.
#[test]
fn records_profile_file_matches_constant() {
    let from_file = load("a145_3_0_0_0");
    let constant = SplitProfile::records_n6();
    let as_set = |p: &SplitProfile| {
        let mut v = p.allowed.clone();
        v.sort();
        v
    };
    assert_eq!(as_set(&from_file), as_set(&constant));
}

/// Every specimen replays all 719 first-visit moves through its own
/// allocation's caps + census-profile grammar — and still does with the
/// fresh-doors cap on (s27 corpus law: every weight>=3 door in every
/// known 872 opens an untouched cycle; 66,999/66,999 door events).
#[test]
fn specimens_replay_in_allocation_grammar() {
    let g = Graph::new(6);
    for fresh_doors in [false, true] {
        for (c, stem, file) in SPECIMENS {
            let mut grammar = Grammar::new(&g, caps(c), Some(load(stem)));
            grammar.fresh_doors = fresh_doors;
            let seq = specimen_seq(&g, file);
            assert_eq!(
                grammar.replay(&seq),
                seq.len(),
                "specimen {file} must replay fully in allocation {c:?} \
                 (fresh_doors={fresh_doors})"
            );
        }
    }
}

/// The check has teeth: the 1|5-split-bearing specimen (allocation
/// S=141, d3=7) dies partway under the records profile.
#[test]
fn records_profile_rejects_one_five_split() {
    let g = Graph::new(6);
    let grammar = Grammar::new(
        &g,
        caps([141, 7, 0, 0, 0]),
        Some(SplitProfile::records_n6()),
    );
    let seq = specimen_seq(&g, "872.up-6dbae421a839.txt");
    assert_eq!(
        grammar.replay(&seq),
        414,
        "measured s27; must not reach 719"
    );
}
