//! Command-line interface for the `superperm` research toolkit.
//!
//! Subcommands: `info`, `greedy`, `beam`, `rollouts`, `validate` — see
//! `superperm --help` and the crate-level documentation of the library.
//!
//! This file is the clap definition and the dispatch table only (s64 P4).
//! Each subcommand's arguments and body live in `src/cli/<command>.rs`;
//! the variant doc comments below are what `--help` prints.

use std::process::ExitCode;

use clap::{Parser, Subcommand};

mod cli;

/// Superpermutation search research toolkit (phase 1).
#[derive(Parser)]
#[command(name = "superperm", version, about)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Print graph statistics: n!, cycle count, edge histogram by weight.
    Info(cli::info::Args),
    /// Dump the door atlas (Track B T1): every weight->=3 edge with
    /// cycle labels, in-cycle offsets, and statically-known interior
    /// permutation windows, as TSV on stdout.
    Atlas(cli::atlas::Args),
    /// Exhaustive sojourn-level canonical opening DFS inside an L0/L1
    /// class (Track B L2; M2 gate).
    SojournDfs(cli::sojourn_dfs::Args),
    /// NRPA (nested rollout policy adaptation) over the sojourn move
    /// grammar of an L0/L1 class, with a capped-beam tail solver
    /// (Track B §4 step 4a; the s24 verdict machinery: the policy owns
    /// the contested midgame, the beam finishes from the switch depth).
    Nrpa(cli::nrpa::Args),
    /// Replay superpermutation strings through the sojourn grammar of
    /// an L0/L1 class and report how far each stays in-grammar (s27:
    /// validates per-allocation grammars against corpus specimens; a
    /// full-length replay = the walk lives in that caps+profile
    /// grammar). Strings are forward-renumbered to identity start
    /// first, so raw records are accepted. Exits nonzero if any input
    /// fails to replay fully.
    GrammarCheck(cli::grammar_check::Args),
    /// Run the deterministic greedy baseline and print the result.
    Greedy(cli::greedy::Args),
    /// Run beam search and print the best result plus wall-clock time.
    Beam(cli::beam::Args),
    /// Run the two-ended (deque) beam search: moves append a successor
    /// of the string's back or prepend a predecessor of its front,
    /// scored by the admissible two-ended arc bound (phase 3's
    /// decision-order probe).
    Beam2(cli::beam2::Args),
    /// Trace an existing superpermutation string: extract its
    /// first-visit trajectory, summarize its edge weights, and
    /// optionally score every trajectory state with a bound or model.
    Trace(cli::trace::Args),
    /// Exactly complete a prefix of an existing walk: truncate its
    /// first-visit path to n! − m visits and solve the last m perms
    /// optimally (Held-Karp exact endgame). The verdict is a theorem:
    /// no completion of that prefix can beat the reported total.
    Endgame(cli::endgame::Args),
    /// Generate epsilon-greedy rollouts and write JSONL feature records.
    Rollouts(cli::rollouts::Args),
    /// Independently verify the n=6 gain-one kernel-chain certificate
    /// (claims C1-C5) from a clean-room reimplementation, printing a
    /// verdict table (claim, computed value, agree y/n).
    CertVerify(cli::cert_verify::Args),
    /// Record-pair splice closure over the braid state-DAG (s26 Probe
    /// R1, docs/RECOMB-DESIGN.md §4): glue all corpus record paths at
    /// shared states, count/enumerate the closure, emit new hybrids.
    /// I1 tail block-ATSP (docs/SURGERY-DESIGN.md §4): per walk, cut the
    /// tail at the shallowest block boundary that yields at most
    /// --max-blocks blocks, then EXACTLY optimize the block order
    /// (junction re-pricing; block set and split compositions fixed).
    /// optimum < actual = an 871 candidate (materialized, validated,
    /// written to --out-dir; STILL goes through m3_check + validate
    /// before any claim). Exit code 2 iff any improvement was found.
    TailAtsp(cli::tail_atsp::Args),
    Recomb(cli::recomb::Args),
    /// Exhaustive bound-capped DFS inside the corpus edge union (s26
    /// Probe R3 / §7 tour-merge, docs/RECOMB-DESIGN.md §5). Without
    /// --tt the run enumerates all distinct walks ≤ cap; with --tt it
    /// supports decision/optimality claims only.
    UnionDfs(cli::union_dfs::Args),
    /// Validate a candidate superpermutation string.
    Validate(cli::validate::Args),
}

fn main() -> ExitCode {
    match Cli::parse().cmd {
        Cmd::Info(a) => cli::info::run(a),
        Cmd::Atlas(a) => cli::atlas::run(a),
        Cmd::SojournDfs(a) => cli::sojourn_dfs::run(a),
        Cmd::Nrpa(a) => cli::nrpa::run(a),
        Cmd::GrammarCheck(a) => cli::grammar_check::run(a),
        Cmd::Greedy(a) => cli::greedy::run(a),
        Cmd::Beam(a) => cli::beam::run(a),
        Cmd::Beam2(a) => cli::beam2::run(a),
        Cmd::Trace(a) => cli::trace::run(a),
        Cmd::Endgame(a) => cli::endgame::run(a),
        Cmd::Rollouts(a) => cli::rollouts::run(a),
        Cmd::CertVerify(a) => cli::cert_verify::run(a),
        Cmd::TailAtsp(a) => cli::tail_atsp::run(a),
        Cmd::Recomb(a) => cli::recomb::run(a),
        Cmd::UnionDfs(a) => cli::union_dfs::run(a),
        Cmd::Validate(a) => cli::validate::run(a),
    }
}
