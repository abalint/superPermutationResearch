//! Per-subcommand CLI modules (s64 P4).
//!
//! `main.rs` owns the clap `Cli`/`Cmd` definition and the dispatch match and
//! nothing else; every subcommand's argument struct and its body live in its
//! own module here, named after the subcommand. Anything used by more than
//! one subcommand — the `Bound`/`DedupMode` CLI adapters, model and
//! split-profile loading, the JSONL trajectory writer, the verdict-cell
//! formatters — lives in this file.
//!
//! Adding a subcommand = one module here, one `pub mod` line, one variant in
//! `main.rs`'s `Cmd` (whose doc comment is its `--help` about text) and one
//! dispatch arm.

use std::fs;
use std::io::BufWriter;
use std::path::PathBuf;

use clap::ValueEnum;

use superperm::beam::Bound;
use superperm::graph::Graph;
use superperm::model::Model;
use superperm::rollout::log_trajectory;

pub mod atlas;
pub mod beam;
pub mod beam2;
pub mod cert_verify;
pub mod endgame;
pub mod grammar_check;
pub mod greedy;
pub mod info;
pub mod nrpa;
pub mod recomb;
pub mod rollouts;
pub mod sojourn_dfs;
pub mod tail_atsp;
pub mod trace;
pub mod union_dfs;
pub mod validate;

/// CLI mirror of [`Bound`] (the library does not depend on clap).
///
/// s64 P4 kept the mirror rather than deriving `ValueEnum` on `Bound`
/// itself: clap renders variant doc comments as the `--help` possible-value
/// text, and the library's docs (intra-doc links, the derivation notes) are
/// deliberately not the one-line CLI blurbs — deriving there would have
/// changed `--help` output, which the stage forbids.
#[derive(Clone, Copy, ValueEnum)]
pub enum BoundArg {
    /// Cycle bound `r + k − [current cycle live]` (phase 1).
    Cycle,
    /// Arc bound `r + arcs − [succ1(cur) unvisited]`; dominates cycle.
    Arc,
    /// Residual bound `r + door + intact + long`; dominates arc
    /// (`docs/RESIDUAL-BOUND-DESIGN.md`).
    Residual,
}

impl BoundArg {
    /// The bound's name as the run headers print it.
    pub fn name(self) -> &'static str {
        match self {
            BoundArg::Cycle => "cycle",
            BoundArg::Arc => "arc",
            BoundArg::Residual => "residual",
        }
    }
}

impl From<BoundArg> for Bound {
    fn from(b: BoundArg) -> Bound {
        match b {
            BoundArg::Cycle => Bound::Cycle,
            BoundArg::Arc => Bound::Arc,
            BoundArg::Residual => Bound::Residual,
        }
    }
}

/// CLI mirror of [`superperm::sojourn::DedupMode`] (see [`BoundArg`] for why
/// the mirror survived P4).
#[derive(Clone, Copy, ValueEnum)]
pub enum DedupArg {
    /// Exact state dedup (no symmetry reduction).
    Exact,
    /// Relabeling-orbit quotient (sound exhaustion up to symmetry).
    Orbit,
    /// L2 canonical-key abstraction (book mode; not exhaustion-sound).
    Abstraction,
}

impl From<DedupArg> for superperm::sojourn::DedupMode {
    fn from(d: DedupArg) -> superperm::sojourn::DedupMode {
        use superperm::sojourn::DedupMode;
        match d {
            DedupArg::Exact => DedupMode::Exact,
            DedupArg::Orbit => DedupMode::Orbit,
            DedupArg::Abstraction => DedupMode::Abstraction,
        }
    }
}

/// Load a model file, exiting with a clear message on a parse failure or
/// an `n` mismatch. With `allow_n_mismatch` the mismatch is downgraded to
/// a warning (cross-n transfer: the features are generic counts, so an
/// n=6-trained linear map is well-defined — if uncalibrated — at n=7).
pub fn load_model(path: &PathBuf, n: usize, allow_n_mismatch: bool) -> Model {
    let m = Model::load(path).unwrap_or_else(|e| {
        eprintln!("cannot load model {}: {e}", path.display());
        std::process::exit(1);
    });
    if m.n() != n {
        if allow_n_mismatch {
            eprintln!(
                "warning: model was trained for n={} but -n is {n} (cross-n transfer)",
                m.n()
            );
        } else {
            eprintln!(
                "model was trained for n={} but -n is {n} \
                 (pass --allow-n-mismatch to transfer anyway)",
                m.n()
            );
            std::process::exit(1);
        }
    }
    m
}

/// Resolve the split-profile CLI pair shared by the sojourn-grammar
/// subcommands: `--records-profile` (the records allocation's committed
/// census file, `SplitProfile::records_n6_loaded`) or `--profile-file`
/// (any per-allocation census file); clap forbids both.
///
/// The two arms differ in failure mode ON PURPOSE (`docs/CONTRACTS.md`
/// §2): `--profile-file` names a file the user chose, so a bad path is a
/// hard error; `--records-profile` names no file at all, so it falls back
/// to the compiled-in table rather than acquiring a file-IO failure it
/// never had.
pub fn load_profile(
    records_profile: bool,
    profile_file: Option<&PathBuf>,
    n: usize,
) -> Option<superperm::sojourn::SplitProfile> {
    use superperm::sojourn::SplitProfile;
    match profile_file {
        Some(path) => Some(SplitProfile::from_file(path, n as u8).unwrap_or_else(|e| {
            eprintln!("--profile-file {e}");
            std::process::exit(1);
        })),
        None => records_profile.then(SplitProfile::records_n6_loaded),
    }
}

/// Write a visit-order path's feature trajectory to `path` as JSONL.
pub fn write_log(g: &Graph, ranks: &[u32], path: &PathBuf) {
    let file = fs::File::create(path).unwrap_or_else(|e| {
        eprintln!("cannot create {}: {e}", path.display());
        std::process::exit(1);
    });
    let mut writer = BufWriter::new(file);
    let lines = log_trajectory(g, ranks, &mut writer).expect("trajectory write failed");
    println!("trajectory log    = {} lines -> {}", lines, path.display());
}

/// Render a per-claim verdict line suffix for `cert-verify`.
pub fn agree(ok: bool) -> &'static str {
    if ok {
        "AGREE"
    } else {
        "DISAGREE"
    }
}

/// Compact y/n column for the `cert-verify` verdict table.
pub fn yn(ok: bool) -> &'static str {
    if ok {
        "y"
    } else {
        "n"
    }
}
