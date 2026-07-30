//! Command-line interface for the `superperm` research toolkit.
//!
//! Subcommands: `info`, `greedy`, `beam`, `rollouts`, `validate` — see
//! `superperm --help` and the crate-level documentation of the library.

use std::fs;
use std::io::BufWriter;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::Instant;

use clap::{Parser, Subcommand, ValueEnum};

use std::io::Write;

use superperm::beam::{
    beam_search_capped, beam_search_endgame_snapshot, beam_search_multi_seeded,
    beam_search_multi_seeded_capped, beam_search_multi_seeded_endgame, beam_search_stratified,
    beam_search_stratified_cutoffs, Bound, Jitter, Scorer, SnapshotCfg, Stratify,
};
use superperm::beam2::{beam2_search, Scorer2};
use superperm::endgame::{solve_endgame, spell_path, MAX_REMAINING};
use superperm::graph::Graph;
use superperm::greedy::greedy;
use superperm::model::Model;
use superperm::rollout::{log_trajectory, run_rollouts_strings, Guide};
use superperm::trace::{score_trajectory, trace_string};
use superperm::validate::validate;

/// CLI mirror of [`Bound`] (the library does not depend on clap).
#[derive(Clone, Copy, ValueEnum)]
enum BoundArg {
    /// Cycle bound `r + k − [current cycle live]` (phase 1).
    Cycle,
    /// Arc bound `r + arcs − [succ1(cur) unvisited]`; dominates cycle.
    Arc,
    /// Residual bound `r + door + intact + long`; dominates arc
    /// (`docs/RESIDUAL-BOUND-DESIGN.md`).
    Residual,
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

/// Load a model file, exiting with a clear message on a parse failure or
/// an `n` mismatch. With `allow_n_mismatch` the mismatch is downgraded to
/// a warning (cross-n transfer: the features are generic counts, so an
/// n=6-trained linear map is well-defined — if uncalibrated — at n=7).
fn load_model(path: &PathBuf, n: usize, allow_n_mismatch: bool) -> Model {
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

/// Parse a beam `--seed-file`: one walk per line, either a bare
/// comma-separated first-visit rank list or a `sojourn-dfs
/// --dump-frontier` TSV row (path in the last tab field); empty and
/// `#`-prefixed lines are skipped. Exits with a message on any invalid
/// walk (must start at rank 0, ranks in range, not a complete walk).
fn read_seed_file(path: &PathBuf, nfact: usize) -> Vec<Vec<u32>> {
    let text = std::fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("cannot read --seed-file {}: {e}", path.display());
        std::process::exit(1);
    });
    let mut seeds = Vec::new();
    for (i, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let field = line.rsplit('\t').next().unwrap();
        let walk: Vec<u32> = field
            .split(',')
            .map(|t| {
                t.trim().parse().unwrap_or_else(|_| {
                    eprintln!("--seed-file line {}: invalid rank {t:?}", i + 1);
                    std::process::exit(1);
                })
            })
            .collect();
        let bad = if walk.first() != Some(&0) {
            Some("walk must start at rank 0")
        } else if walk.len() >= nfact {
            Some("walk already visits every permutation")
        } else if walk.iter().any(|&r| r as usize >= nfact) {
            Some("rank out of range")
        } else {
            None
        };
        if let Some(msg) = bad {
            eprintln!("--seed-file line {}: {msg}", i + 1);
            std::process::exit(1);
        }
        seeds.push(walk);
    }
    if seeds.is_empty() {
        eprintln!("--seed-file {} contains no walks", path.display());
        std::process::exit(1);
    }
    seeds
}

/// Resolve the split-profile CLI pair shared by the sojourn-grammar
/// subcommands: `--records-profile` (the hard-coded n=6 constant) or
/// `--profile-file` (per-allocation census data); clap forbids both.
fn load_profile(
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
        None => records_profile.then(SplitProfile::records_n6),
    }
}

/// Write a visit-order path's feature trajectory to `path` as JSONL.
fn write_log(g: &Graph, ranks: &[u32], path: &PathBuf) {
    let file = fs::File::create(path).unwrap_or_else(|e| {
        eprintln!("cannot create {}: {e}", path.display());
        std::process::exit(1);
    });
    let mut writer = BufWriter::new(file);
    let lines = log_trajectory(g, ranks, &mut writer).expect("trajectory write failed");
    println!("trajectory log    = {} lines -> {}", lines, path.display());
}

/// Render a per-claim verdict line suffix for `cert-verify`.
fn agree(ok: bool) -> &'static str {
    if ok {
        "AGREE"
    } else {
        "DISAGREE"
    }
}

/// Compact y/n column for the `cert-verify` verdict table.
fn yn(ok: bool) -> &'static str {
    if ok {
        "y"
    } else {
        "n"
    }
}

/// CLI mirror of [`superperm::sojourn::DedupMode`].
#[derive(Clone, Copy, ValueEnum)]
enum DedupArg {
    /// Exact state dedup (no symmetry reduction).
    Exact,
    /// Relabeling-orbit quotient (sound exhaustion up to symmetry).
    Orbit,
    /// L2 canonical-key abstraction (book mode; not exhaustion-sound).
    Abstraction,
}

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
    Info {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
    },
    /// Dump the door atlas (Track B T1): every weight->=3 edge with
    /// cycle labels, in-cycle offsets, and statically-known interior
    /// permutation windows, as TSV on stdout.
    Atlas {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Minimum door weight to include (default 3; 2 adds w2x/i2).
        #[arg(long, default_value_t = 3)]
        min_weight: u8,
    },
    /// Exhaustive sojourn-level canonical opening DFS inside an L0/L1
    /// class (Track B L2; M2 gate).
    SojournDfs {
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
    },
    /// NRPA (nested rollout policy adaptation) over the sojourn move
    /// grammar of an L0/L1 class, with a capped-beam tail solver
    /// (Track B §4 step 4a; the s24 verdict machinery: the policy owns
    /// the contested midgame, the beam finishes from the switch depth).
    Nrpa {
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
        /// Nesting depth (1 = adapt over plain rollouts; 2-3 typical).
        #[arg(long, default_value_t = 2)]
        level: u32,
        /// Iterations per nesting level (iters^level rollouts total).
        #[arg(long, default_value_t = 30)]
        iters: u32,
        /// Adaptation step size (Rosin's alpha).
        #[arg(long, default_value_t = 1.0)]
        adapt: f64,
        /// RNG seed; runs are deterministic given it.
        #[arg(long, default_value_t = 0)]
        seed: u64,
        /// Visited-perm count at which rollouts hand off to the beam
        /// tail (clamped to n!).
        #[arg(long, default_value_t = 450)]
        switch_depth: usize,
        /// Beam width of the tail completion.
        #[arg(long, default_value_t = 2000)]
        tail_width: usize,
        /// Admissible length cap for the tail beam (0 = uncapped;
        /// capped tails can die, which scores the rollout dead).
        #[arg(long, default_value_t = 0)]
        max_len: u32,
        /// Tail scorer bound (default residual — the best completer).
        #[arg(long, value_enum)]
        bound: Option<BoundArg>,
        /// Compose the tail scorer with this learned model (T2).
        #[arg(long)]
        model: Option<PathBuf>,
        /// Blend factor for the composed tail score.
        #[arg(long, default_value_t = 0.25)]
        alpha: f64,
        /// Allow --model files trained for a different n.
        #[arg(long, requires = "model")]
        allow_n_mismatch: bool,
        /// Waste prior on the rollout logits: each move's logit gets
        /// -prior * (extra chars beyond 1 per perm), so the untrained
        /// policy favours cheap moves. 0 = classic uniform-start NRPA.
        #[arg(long, default_value_t = 0.0)]
        prior: f64,
        /// On an in-grammar dead-end, complete the partial prefix with
        /// the (unconstrained) beam tail instead of scoring the rollout
        /// dead — every rollout then returns a graded score, which a
        /// class too tight for random play needs to bootstrap learning.
        #[arg(long)]
        early_tail: bool,
        /// Warm-start the policy from these superpermutation string
        /// files (e.g. known records): each first-visit path is
        /// replayed as a grammar move sequence and the policy adapted
        /// toward it before the search (Track C policy initialization).
        #[arg(long)]
        warm_start: Vec<PathBuf>,
        /// Visited-perm depth of the warm-start prefix (0 = up to the
        /// switch depth).
        #[arg(long, default_value_t = 0, requires = "warm_start")]
        warm_depth: usize,
        /// Adapt passes over the warm-start sequence.
        #[arg(long, default_value_t = 3, requires = "warm_start")]
        warm_reps: u32,
        /// Collect every distinct completed walk of length <= this and
        /// print them all at the end (0 = off) — the M3 hunt wants all
        /// distinct <=872 walks, not just the best.
        #[arg(long, default_value_t = 0)]
        collect: u32,
        /// Suppress per-iteration progress lines.
        #[arg(long)]
        quiet: bool,
    },
    /// Replay superpermutation strings through the sojourn grammar of
    /// an L0/L1 class and report how far each stays in-grammar (s27:
    /// validates per-allocation grammars against corpus specimens; a
    /// full-length replay = the walk lives in that caps+profile
    /// grammar). Strings are forward-renumbered to identity start
    /// first, so raw records are accepted. Exits nonzero if any input
    /// fails to replay fully.
    GrammarCheck {
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
        /// Superpermutation string files to check.
        #[arg(required = true)]
        files: Vec<PathBuf>,
        /// Print only the summary line and failures.
        #[arg(long)]
        quiet: bool,
    },
    /// Run the deterministic greedy baseline and print the result.
    Greedy {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Write the trajectory's feature records to this JSONL file.
        #[arg(long)]
        log: Option<PathBuf>,
    },
    /// Run beam search and print the best result plus wall-clock time.
    Beam {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Beam width (states kept per depth level).
        #[arg(long, default_value_t = 1000)]
        width: usize,
        /// Admissible lower bound used for scoring (default: cycle).
        /// The arc bound is tighter but empirically no better as a beam
        /// ranker (see docs/JOURNAL.md 2026-07-27). With --model, an
        /// explicit --bound composes (T2): score = len + lb + alpha *
        /// prediction; without it the model scores alone as before.
        #[arg(long, value_enum)]
        bound: Option<BoundArg>,
        /// Score candidates with this learned value-function model
        /// (JSON produced by the training side); alone, or composed
        /// with an explicit --bound (T2).
        #[arg(long)]
        model: Option<PathBuf>,
        /// Blend factor for the learned score: len + alpha * prediction.
        #[arg(long, default_value_t = 1.0)]
        alpha: f64,
        /// Allow --model files trained for a different n (cross-n
        /// transfer; the mismatch is reported as a warning instead of
        /// an error).
        #[arg(long, requires = "model")]
        allow_n_mismatch: bool,
        /// Deterministic score jitter magnitude in length units: each
        /// candidate's score gets a pseudo-random offset in [0, eps)
        /// that is a pure function of (cur, visited, seed). 0 disables
        /// jitter (bit-identical to the unjittered search).
        #[arg(long, default_value_t = 0.0)]
        jitter: f64,
        /// Seed for the jitter's Zobrist table (only used with --jitter).
        #[arg(long, default_value_t = 0)]
        jitter_seed: u64,
        /// Seed the beam's root state by replaying this many greedy
        /// moves before the search starts (0 = plain beam; must be
        /// < n! - 1). The reported result includes the prefix.
        #[arg(long, default_value_t = 0)]
        seed_prefix: usize,
        /// Seed the beam from walk prefixes in this file (T3): one walk
        /// per line, either a comma-separated first-visit rank list
        /// starting at 0, or a `sojourn-dfs --dump-frontier` TSV row
        /// (the path is its last field; `#` lines are skipped). Each
        /// walk is injected at its own depth; a one-line file with the
        /// greedy prefix is bit-identical to --seed-prefix.
        #[arg(long, conflicts_with = "seed_prefix")]
        seed_file: Option<PathBuf>,
        /// Stratified selection: bucket candidates by deficit profile
        /// (quantized intact / half-open / nearly-done cycle counts)
        /// and reserve part of the width per occupied bucket, so
        /// record-like states can't be crowded out by globally
        /// better-scoring greedy-like ones. Off = bit-identical to the
        /// plain beam.
        #[arg(long)]
        stratify: bool,
        /// Kept slots reserved per occupied bucket (only with
        /// --stratify; 0 behaves like the plain beam).
        #[arg(long, default_value_t = 32, requires = "stratify")]
        strat_quota: usize,
        /// Bucket granularity: each deficit count is divided by this
        /// before forming the bucket key (only with --stratify; >= 1).
        #[arg(long, default_value_t = 4, requires = "stratify")]
        strat_bucket: usize,
        /// Exact endgame tablebase (phase-3 item 4): when exactly this
        /// many perms remain, snapshot the frontier and solve the top
        /// --endgame-top states' completions exactly (Held-Karp DP;
        /// provably optimal). The beam itself is unchanged; the summary
        /// reports whether any exact endgame beats the heuristic one,
        /// and the best exact string is printed if it beats the beam's.
        /// 0 = off; RAM/time grow as 2^m (20 is cheap, 24 is seconds
        /// and ~800 MB per state).
        #[arg(long, default_value_t = 0)]
        endgame: usize,
        /// Frontier states (in score order) to solve exactly (with
        /// --endgame).
        #[arg(long, default_value_t = 100)]
        endgame_top: usize,
        /// Write the best path's feature records to this JSONL file.
        #[arg(long)]
        log: Option<PathBuf>,
        /// Write one TSV line per level (level, kept, best_score,
        /// worst_kept_score — the pruning threshold; with --stratify
        /// the max kept score) to this file. Pure instrumentation;
        /// does not change the search.
        #[arg(long)]
        cutoff_log: Option<PathBuf>,
        /// Admissible length cap (T2): discard every candidate whose
        /// len + lb exceeds this — lossless for completions within the
        /// cap; the whole width is spent on states that can still make
        /// it. The search reports failure if no explored walk finishes
        /// within the cap. 0 = off.
        #[arg(long, default_value_t = 0)]
        max_len: u32,
    },
    /// Run the two-ended (deque) beam search: moves append a successor
    /// of the string's back or prepend a predecessor of its front,
    /// scored by the admissible two-ended arc bound (phase 3's
    /// decision-order probe).
    Beam2 {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Beam width (states kept per depth level).
        #[arg(long, default_value_t = 1000)]
        width: usize,
        /// Transfer experiment: score candidates with this learned
        /// one-ended model (features computed relative to the back end)
        /// instead of the two-ended arc bound.
        #[arg(long)]
        model: Option<PathBuf>,
        /// Blend factor for the learned score: len + alpha * prediction.
        #[arg(long, default_value_t = 1.0)]
        alpha: f64,
        /// Deterministic score jitter magnitude in length units (pure
        /// function of (front, back, visited, seed); 0 disables).
        #[arg(long, default_value_t = 0.0)]
        jitter: f64,
        /// Seed for the jitter's Zobrist table (only used with --jitter).
        #[arg(long, default_value_t = 0)]
        jitter_seed: u64,
    },
    /// Trace an existing superpermutation string: extract its
    /// first-visit trajectory, summarize its edge weights, and
    /// optionally score every trajectory state with a bound or model.
    Trace {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// File holding the superpermutation string (trimmed).
        #[arg(long)]
        file: PathBuf,
        /// Score trajectory states with this admissible bound
        /// (score = len + lb).
        #[arg(long, value_enum)]
        bound: Option<BoundArg>,
        /// Score trajectory states with this learned model instead
        /// (score = len + alpha * pred, + lb_arc for residual models —
        /// exactly the beam's arithmetic).
        #[arg(long, conflicts_with = "bound")]
        model: Option<PathBuf>,
        /// Blend factor for the learned score (only used with --model).
        #[arg(long, default_value_t = 1.0)]
        alpha: f64,
        /// Write the trajectory's feature records to this JSONL file.
        #[arg(long)]
        log: Option<PathBuf>,
        /// Write per-step scores as TSV (step, len, score) to this file
        /// instead of stdout (requires --bound or --model).
        #[arg(long)]
        score_log: Option<PathBuf>,
    },
    /// Exactly complete a prefix of an existing walk: truncate its
    /// first-visit path to n! − m visits and solve the last m perms
    /// optimally (Held-Karp exact endgame). The verdict is a theorem:
    /// no completion of that prefix can beat the reported total.
    Endgame {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// File holding the superpermutation string whose prefix to
        /// complete (trimmed).
        #[arg(long, conflicts_with = "greedy", required_unless_present = "greedy")]
        file: Option<PathBuf>,
        /// Use the deterministic greedy walk as the source instead.
        #[arg(long)]
        greedy: bool,
        /// How many trailing perms to solve exactly (1..=25; RAM/time
        /// grow as 2^m — 20 is cheap, 24 is seconds and ~800 MB).
        #[arg(long)]
        remaining: usize,
    },
    /// Generate epsilon-greedy rollouts and write JSONL feature records.
    Rollouts {
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
    },
    /// Independently verify the n=6 gain-one kernel-chain certificate
    /// (claims C1-C5) from a clean-room reimplementation, printing a
    /// verdict table (claim, computed value, agree y/n).
    CertVerify {
        /// Number of symbols (the certificate is defined for n = 6 only).
        #[arg(short, long)]
        n: usize,
    },
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
    TailAtsp {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// Record directories, comma-separated.
        #[arg(long, value_delimiter = ',')]
        dirs: Vec<PathBuf>,
        /// Anchor: smallest first-visit depth eligible as the cut.
        #[arg(long, default_value_t = 585)]
        anchor: usize,
        /// Widest instance to solve exactly; walks needing more blocks
        /// at --anchor are cut DEEPER (fewer blocks) instead of skipped.
        #[arg(long, default_value_t = 27)]
        max_blocks: usize,
        /// Also collect equal-cost orders (ties) and report those whose
        /// implied L0 allocation differs from the source walk's.
        #[arg(long)]
        ties: bool,
        /// Cap on collected tie orders per walk.
        #[arg(long, default_value_t = 64)]
        tie_cap: usize,
        /// Write improved (and, with --ties, new-allocation tie) walks
        /// here.
        #[arg(long)]
        out_dir: Option<PathBuf>,
        /// Process only the first K records (sweep sizing runs).
        #[arg(long)]
        limit: Option<usize>,
        /// Print only the summary and any improvements.
        #[arg(long)]
        quiet: bool,
    },
    Recomb {
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
    },
    /// Exhaustive bound-capped DFS inside the corpus edge union (s26
    /// Probe R3 / §7 tour-merge, docs/RECOMB-DESIGN.md §5). Without
    /// --tt the run enumerates all distinct walks ≤ cap; with --tt it
    /// supports decision/optimality claims only.
    UnionDfs {
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
    },
    /// Validate a candidate superpermutation string.
    Validate {
        /// Number of symbols (3..=8).
        #[arg(short, long)]
        n: usize,
        /// The candidate string (or use --file).
        string: Option<String>,
        /// Read the candidate string from a file instead.
        #[arg(long, conflicts_with = "string")]
        file: Option<PathBuf>,
        /// Exit nonzero unless the string is a complete superpermutation.
        #[arg(long)]
        complete: bool,
    },
}

fn main() -> ExitCode {
    match Cli::parse().cmd {
        Cmd::Info { n } => {
            let g = Graph::new(n);
            println!("n = {n}");
            println!("n! (vertices) = {}", g.nfact);
            println!("cycle_count ((n-1)!) = {}", g.cycle_count);
            let mut hist = vec![0usize; n];
            for list in &g.succs {
                for &(_, w) in list {
                    hist[w as usize] += 1;
                }
            }
            println!("successor edges by weight (weight-n jumps not stored):");
            for (w, count) in hist.iter().enumerate().skip(1) {
                println!("  weight {w}: {count} edges ({} per perm)", count / g.nfact);
            }
            println!("successors per perm = {}", g.succs[0].len());
        }
        Cmd::Atlas { n, min_weight } => {
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
            use std::io::Write;
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
        }
        Cmd::SojournDfs {
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
        } => {
            use superperm::sojourn::{ClassCaps, DedupMode, SojournDfs};
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
                dedup: match dedup {
                    DedupArg::Exact => DedupMode::Exact,
                    DedupArg::Orbit => DedupMode::Orbit,
                    DedupArg::Abstraction => DedupMode::Abstraction,
                },
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
                use std::io::Write;
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
        }
        Cmd::Nrpa {
            n,
            class,
            records_profile,
            profile_file,
            fresh_doors,
            level,
            iters,
            adapt,
            seed,
            switch_depth,
            tail_width,
            max_len,
            bound,
            model,
            alpha,
            allow_n_mismatch,
            prior,
            early_tail,
            warm_start,
            warm_depth,
            warm_reps,
            collect,
            quiet,
        } => {
            use superperm::nrpa::{nrpa_search, NrpaCfg};
            use superperm::sojourn::ClassCaps;
            assert_eq!(class.len(), 5, "--class needs S,d3,d4,d5,ip");
            let g = Graph::new(n);
            let caps = ClassCaps {
                s: class[0],
                d3: class[1],
                d4: class[2],
                d5: class[3],
                ip: class[4],
            };
            let loaded = model.map(|path| load_model(&path, n, allow_n_mismatch));
            let b = bound.unwrap_or(BoundArg::Residual);
            let bname = match b {
                BoundArg::Cycle => "cycle",
                BoundArg::Arc => "arc",
                BoundArg::Residual => "residual",
            };
            let (tail_scorer, tdesc) = match &loaded {
                Some(m) => (
                    Scorer::Composed {
                        bound: b.into(),
                        model: m,
                        alpha,
                    },
                    format!("bound={bname}+model={} alpha={alpha}", m.kind()),
                ),
                None => (Scorer::Bound(b.into()), format!("bound={bname}")),
            };
            println!(
                "nrpa n={n} class=(S={},d3={},d4={},d5={},ip={}) waste={} level={level} iters={iters} adapt={adapt} prior={prior} seed={seed} switch={switch_depth} tail: width={tail_width} {tdesc} max_len={max_len}",
                caps.s,
                caps.d3,
                caps.d4,
                caps.d5,
                caps.ip,
                caps.waste(),
            );
            let warm: Vec<Vec<u32>> = warm_start
                .iter()
                .map(|path| {
                    let text = std::fs::read_to_string(path).unwrap_or_else(|e| {
                        eprintln!("cannot read --warm-start {}: {e}", path.display());
                        std::process::exit(1);
                    });
                    let tr = trace_string(&g, text.trim()).unwrap_or_else(|e| {
                        eprintln!("--warm-start {}: {e}", path.display());
                        std::process::exit(1);
                    });
                    let depth = if warm_depth == 0 {
                        switch_depth
                    } else {
                        warm_depth
                    }
                    .min(tr.path.len());
                    tr.path[1..depth].to_vec()
                })
                .collect();
            let cfg = NrpaCfg {
                g: &g,
                caps,
                profile: load_profile(records_profile, profile_file.as_ref(), n),
                fresh_doors,
                level,
                iters,
                adapt_alpha: adapt,
                seed,
                switch_depth,
                tail_width,
                max_len,
                tail_scorer,
                prior,
                early_tail,
                warm_start: warm,
                warm_reps,
                collect_max: collect,
                verbose: !quiet,
            };
            let t = std::time::Instant::now();
            let r = nrpa_search(&cfg);
            let dt = t.elapsed().as_secs_f64();
            println!(
                "rollouts = {} (dead {}, of which in-grammar {}) elapsed = {dt:.1}s",
                r.rollouts, r.dead, r.dead_in_grammar
            );
            println!(
                "in-grammar depth (visited perms at hand-off/death): min {} mean {:.1} max {}",
                r.depth_min, r.depth_mean, r.depth_max
            );
            if collect > 0 {
                println!(
                    "collected {} distinct walks <= {collect}:",
                    r.collected.len()
                );
                for s in &r.collected {
                    let v = superperm::validate::validate(n, s);
                    println!("  len {} complete={} {s}", s.len(), yn(v.complete));
                }
            }
            match (r.best_len, r.string) {
                (Some(len), Some(s)) => {
                    let v = superperm::validate::validate(n, &s);
                    println!(
                        "nrpa best: length {len} (validated complete = {})",
                        yn(v.complete)
                    );
                    println!("{s}");
                    if !v.complete || v.length != len as usize {
                        eprintln!("VALIDATION FAILED — do not believe this result");
                        return ExitCode::FAILURE;
                    }
                }
                _ => {
                    println!("nrpa: NO completion found (all rollouts dead)");
                }
            }
        }
        Cmd::GrammarCheck {
            n,
            class,
            records_profile,
            profile_file,
            fresh_doors,
            files,
            quiet,
        } => {
            use superperm::sojourn::{ClassCaps, Grammar};
            assert_eq!(class.len(), 5, "--class needs S,d3,d4,d5,ip");
            let g = Graph::new(n);
            let caps = ClassCaps {
                s: class[0],
                d3: class[1],
                d4: class[2],
                d5: class[3],
                ip: class[4],
            };
            let profile = load_profile(records_profile, profile_file.as_ref(), n);
            let mut grammar = Grammar::new(&g, caps, profile.clone());
            grammar.fresh_doors = fresh_doors;
            println!(
                "grammar-check n={n} class=(S={},d3={},d4={},d5={},ip={}) waste={} profile={}{}",
                caps.s,
                caps.d3,
                caps.d4,
                caps.d5,
                caps.ip,
                caps.waste(),
                match (&profile, &profile_file) {
                    (None, _) => "none".to_string(),
                    (Some(_), None) => "records".to_string(),
                    (Some(p), Some(f)) =>
                        format!("{} ({} compositions)", f.display(), p.allowed.len()),
                },
                if fresh_doors { " fresh-doors" } else { "" },
            );
            let mut failures = 0u32;
            for path in &files {
                let text = std::fs::read_to_string(path).unwrap_or_else(|e| {
                    eprintln!("cannot read {}: {e}", path.display());
                    std::process::exit(1);
                });
                // forward-renumber to identity start: relabel symbols so
                // the first window reads 12..n (the grammar roots at the
                // identity permutation)
                let s = text.trim();
                let mut sigma = [0u8; 256];
                for (i, b) in s.bytes().take(n).enumerate() {
                    sigma[b as usize] = b'1' + i as u8;
                }
                let renum: String = s.bytes().map(|b| sigma[b as usize] as char).collect();
                let tr = trace_string(&g, &renum).unwrap_or_else(|e| {
                    eprintln!("{}: {e}", path.display());
                    std::process::exit(1);
                });
                let seq = &tr.path[1..];
                let done = grammar.replay(seq);
                let ok = done == seq.len();
                if !ok {
                    failures += 1;
                }
                if !quiet || !ok {
                    println!(
                        "  {}: {done} of {} moves in-grammar{}",
                        path.display(),
                        seq.len(),
                        if ok { "" } else { "  OUT-OF-GRAMMAR" },
                    );
                }
            }
            println!(
                "grammar-check: {} of {} files replay fully",
                files.len() as u32 - failures,
                files.len(),
            );
            if failures > 0 {
                return ExitCode::FAILURE;
            }
        }
        Cmd::Greedy { n, log } => {
            let g = Graph::new(n);
            let r = greedy(&g);
            println!("greedy n={n}: length {}", r.len);
            println!("{}", r.string);
            if let Some(path) = log {
                write_log(&g, &r.path, &path);
            }
        }
        Cmd::Beam {
            n,
            width,
            bound,
            model,
            alpha,
            allow_n_mismatch,
            jitter,
            jitter_seed,
            seed_prefix,
            seed_file,
            stratify,
            strat_quota,
            strat_bucket,
            endgame,
            endgame_top,
            log,
            cutoff_log,
            max_len,
        } => {
            let g = Graph::new(n);
            if seed_prefix >= g.nfact - 1 {
                eprintln!(
                    "--seed-prefix must be less than n! - 1 = {} (got {seed_prefix})",
                    g.nfact - 1
                );
                std::process::exit(1);
            }
            let seeds = seed_file.as_ref().map(|p| read_seed_file(p, g.nfact));
            let loaded = model.map(|path| load_model(&path, n, allow_n_mismatch));
            let bname = |b: BoundArg| match b {
                BoundArg::Cycle => "cycle",
                BoundArg::Arc => "arc",
                BoundArg::Residual => "residual",
            };
            let (scorer, desc) = match (&loaded, bound) {
                (Some(m), Some(b)) => (
                    Scorer::Composed {
                        bound: b.into(),
                        model: m,
                        alpha,
                    },
                    format!("bound={}+model={} alpha={alpha}", bname(b), m.kind()),
                ),
                (Some(m), None) => (
                    Scorer::Learned { model: m, alpha },
                    format!("model={} alpha={alpha}", m.kind()),
                ),
                (None, b) => {
                    let b = b.unwrap_or(BoundArg::Cycle);
                    (Scorer::Bound(b.into()), format!("bound={}", bname(b)))
                }
            };
            let jit = (jitter > 0.0).then_some(Jitter {
                eps: jitter,
                seed: jitter_seed,
            });
            let jdesc = match jit {
                Some(j) => format!(" jitter={} jitter_seed={}", j.eps, j.seed),
                None => String::new(),
            };
            let sdesc = match (&seeds, seed_prefix) {
                (Some(s), _) => format!(
                    " seed_file={} seeds={}",
                    seed_file.as_ref().unwrap().display(),
                    s.len()
                ),
                (None, 0) => String::new(),
                (None, k) => format!(" seed_prefix={k}"),
            };
            if stratify && strat_bucket == 0 {
                eprintln!("--strat-bucket must be >= 1");
                std::process::exit(1);
            }
            let strat = stratify.then_some(Stratify {
                quota: strat_quota,
                bucket: strat_bucket,
            });
            let stdesc = match strat {
                Some(s) => format!(" stratify quota={} bucket={}", s.quota, s.bucket),
                None => String::new(),
            };
            if endgame > 0 {
                let seeded = match &seeds {
                    Some(s) => s.iter().map(Vec::len).max().unwrap(),
                    None => 1 + seed_prefix,
                };
                let max_m = MAX_REMAINING.min(g.nfact - seeded);
                if !(1..=max_m).contains(&endgame) {
                    eprintln!("--endgame must be in 1..={max_m} (got {endgame})");
                    std::process::exit(1);
                }
                if cutoff_log.is_some() {
                    eprintln!("--endgame cannot be combined with --cutoff-log");
                    std::process::exit(1);
                }
            }
            if seeds.is_some() && cutoff_log.is_some() {
                eprintln!("--seed-file cannot be combined with --cutoff-log");
                std::process::exit(1);
            }
            if max_len > 0 && (endgame > 0 || cutoff_log.is_some()) {
                eprintln!("--max-len cannot be combined with --endgame or --cutoff-log");
                std::process::exit(1);
            }
            let t0 = Instant::now();
            if max_len > 0 {
                let capped = match &seeds {
                    Some(s) => {
                        beam_search_multi_seeded_capped(&g, width, scorer, jit, s, strat, max_len)
                    }
                    None => beam_search_capped(&g, width, scorer, jit, seed_prefix, strat, max_len),
                };
                let dt = t0.elapsed();
                match capped {
                    Some(b) => {
                        println!(
                            "beam n={n} width={width} {desc}{jdesc}{sdesc}{stdesc} max_len={max_len}: length {} ({:.3}s)",
                            b.len,
                            dt.as_secs_f64()
                        );
                        println!("{}", b.string);
                        if let Some(path) = log {
                            write_log(&g, &b.path, &path);
                        }
                    }
                    None => {
                        println!(
                            "beam n={n} width={width} {desc}{jdesc}{sdesc}{stdesc} max_len={max_len}: NO completion within cap ({:.3}s)",
                            dt.as_secs_f64()
                        );
                    }
                }
                return ExitCode::SUCCESS;
            }
            let (b, cuts, snaps) = if endgame > 0 {
                let cfg = SnapshotCfg {
                    remaining: endgame,
                    top: endgame_top,
                };
                let (b, s) = match &seeds {
                    Some(s) => {
                        beam_search_multi_seeded_endgame(&g, width, scorer, jit, s, strat, cfg)
                    }
                    None => beam_search_endgame_snapshot(
                        &g,
                        width,
                        scorer,
                        jit,
                        seed_prefix,
                        strat,
                        cfg,
                    ),
                };
                (b, None, Some(s))
            } else if let Some(s) = &seeds {
                (
                    beam_search_multi_seeded(&g, width, scorer, jit, s, strat),
                    None,
                    None,
                )
            } else {
                match &cutoff_log {
                    Some(_) => {
                        let (b, c) = beam_search_stratified_cutoffs(
                            &g,
                            width,
                            scorer,
                            jit,
                            seed_prefix,
                            strat,
                        );
                        (b, Some(c), None)
                    }
                    None => (
                        beam_search_stratified(&g, width, scorer, jit, seed_prefix, strat),
                        None,
                        None,
                    ),
                }
            };
            let dt = t0.elapsed();
            println!(
                "beam n={n} width={width} {desc}{jdesc}{sdesc}{stdesc}: length {} ({:.3}s)",
                b.len,
                dt.as_secs_f64()
            );
            println!("{}", b.string);
            if let Some(snaps) = snaps {
                let t1 = Instant::now();
                let mut best: Option<(u32, usize, Vec<u32>)> = None; // (total, idx, order)
                let mut beats_own = 0usize; // exact < its own beam descendant
                let mut max_gain = 0i64;
                let mut beats_beam = 0usize; // exact total < beam final result
                for (i, s) in snaps.iter().enumerate() {
                    let e = solve_endgame(&g, s.cur, &s.remaining);
                    let total = s.len + e.cost;
                    if let Some(h) = s.best_descendant_len {
                        let gain = i64::from(h) - i64::from(total);
                        if gain >= 1 {
                            beats_own += 1;
                        }
                        max_gain = max_gain.max(gain);
                    }
                    if (total as usize) < b.len {
                        beats_beam += 1;
                    }
                    if best.as_ref().is_none_or(|(t, _, _)| total < *t) {
                        best = Some((total, i, e.order));
                    }
                }
                let (best_total, best_idx, best_order) = best.expect("endgame top >= 1");
                let snap = &snaps[best_idx];
                println!(
                    "endgame m={endgame} top={}: solved {} frontier states ({:.3}s)",
                    endgame_top,
                    snaps.len(),
                    t1.elapsed().as_secs_f64()
                );
                println!(
                    "  best exact total = {best_total} (score-rank #{}, len {} + exact {})",
                    snap.score_rank,
                    snap.len,
                    best_total - snap.len
                );
                println!(
                    "  exact beats own beam descendant by >=1 char: {beats_own} / {} states (max gain {max_gain})",
                    snaps.len()
                );
                println!(
                    "  exact total beats beam result ({}): {beats_beam} / {} states",
                    b.len,
                    snaps.len()
                );
                if (best_total as usize) < b.len {
                    let mut path = snap.path.clone();
                    path.extend_from_slice(&best_order);
                    let s = spell_path(&g, &path);
                    assert_eq!(s.len(), best_total as usize);
                    let v = superperm::validate::validate(n, &s);
                    println!(
                        "  IMPROVED result: length {best_total} (validated complete = {})",
                        v.complete
                    );
                    println!("{s}");
                }
            }
            if let Some(path) = log {
                write_log(&g, &b.path, &path);
            }
            if let (Some(path), Some(cuts)) = (cutoff_log, cuts) {
                let file = fs::File::create(&path).unwrap_or_else(|e| {
                    eprintln!("cannot create {}: {e}", path.display());
                    std::process::exit(1);
                });
                let mut w = BufWriter::new(file);
                writeln!(w, "level\tkept\tbest_score\tworst_kept_score").unwrap();
                for c in &cuts {
                    writeln!(
                        w,
                        "{}\t{}\t{}\t{}",
                        c.level, c.kept, c.best_score, c.worst_kept_score
                    )
                    .unwrap();
                }
                println!(
                    "cutoff log        = {} levels -> {}",
                    cuts.len(),
                    path.display()
                );
            }
        }
        Cmd::Beam2 {
            n,
            width,
            model,
            alpha,
            jitter,
            jitter_seed,
        } => {
            let g = Graph::new(n);
            let loaded = model.map(|path| load_model(&path, n, false));
            if let Some(m) = &loaded {
                if m.n_features() > superperm::model::FEATURE_ORDER.len() {
                    eprintln!(
                        "beam2's transfer scorer supports only the 8-feature contract; \
                         this model consumes {} features (the deficit-distribution \
                         features are not maintained in the two-ended searcher)",
                        m.n_features()
                    );
                    std::process::exit(1);
                }
            }
            let (scorer, desc) = match &loaded {
                Some(m) => (
                    Scorer2::Learned { model: m, alpha },
                    format!("model={} alpha={alpha}", m.kind()),
                ),
                None => (Scorer2::Arc2, "bound=arc2".to_string()),
            };
            let jit = (jitter > 0.0).then_some(Jitter {
                eps: jitter,
                seed: jitter_seed,
            });
            let jdesc = match jit {
                Some(j) => format!(" jitter={} jitter_seed={}", j.eps, j.seed),
                None => String::new(),
            };
            let t0 = Instant::now();
            let b = beam2_search(&g, width, scorer, jit);
            let dt = t0.elapsed();
            let prepends = b.moves.iter().filter(|&&(_, p)| p).count();
            println!(
                "beam2 n={n} width={width} {desc}{jdesc}: length {} ({:.3}s, {} prepends / {} moves)",
                b.len,
                dt.as_secs_f64(),
                prepends,
                b.moves.len() - 1
            );
            println!("{}", b.string);
        }
        Cmd::Trace {
            n,
            file,
            bound,
            model,
            alpha,
            log,
            score_log,
        } => {
            let g = Graph::new(n);
            let s = fs::read_to_string(&file)
                .unwrap_or_else(|e| {
                    eprintln!("cannot read {}: {e}", file.display());
                    std::process::exit(1);
                })
                .trim()
                .to_string();
            let v = validate(n, &s);
            if !v.complete {
                eprintln!(
                    "not a complete superpermutation: {} / {} perms covered",
                    v.distinct, v.total
                );
                std::process::exit(1);
            }
            let t = trace_string(&g, &s).unwrap_or_else(|e| {
                eprintln!("cannot trace {}: {e}", file.display());
                std::process::exit(1);
            });
            println!(
                "trace n={n} {}: length {} (replay {}), visits {}",
                file.display(),
                t.input_len,
                t.replay_len,
                t.path.len()
            );
            if t.replay_len != t.input_len {
                println!(
                    "warning: replay is {} chars shorter — the string does not \
                     realize every maximal overlap",
                    t.input_len - t.replay_len
                );
            }
            print!("moves by weight  :");
            for (w, count) in t.hist.iter().enumerate().skip(1) {
                print!(" w{w}={count}");
            }
            println!();
            let heavy: Vec<String> = t
                .weights
                .iter()
                .enumerate()
                .filter(|&(_, &w)| w >= 3)
                .map(|(i, &w)| format!("{}(w{})", i + 1, w))
                .collect();
            println!(
                "weight>=3 moves  : {}{}",
                heavy.len(),
                if heavy.is_empty() {
                    String::new()
                } else {
                    format!(" at steps {}", heavy.join(" "))
                }
            );
            if let Some(path) = log {
                write_log(&g, &t.path, &path);
            }
            let loaded = model.map(|path| load_model(&path, n, false));
            let scorer = match (&loaded, bound) {
                (Some(m), _) => Some(Scorer::Learned { model: m, alpha }),
                (None, Some(b)) => Some(Scorer::Bound(b.into())),
                (None, None) => None,
            };
            if scorer.is_none() && score_log.is_some() {
                eprintln!("--score-log requires --bound or --model");
                std::process::exit(1);
            }
            if let Some(scorer) = scorer {
                let scores = score_trajectory(&g, &t.path, scorer);
                match score_log {
                    Some(path) => {
                        let file = fs::File::create(&path).unwrap_or_else(|e| {
                            eprintln!("cannot create {}: {e}", path.display());
                            std::process::exit(1);
                        });
                        let mut w = BufWriter::new(file);
                        writeln!(w, "step\tlen\tscore").unwrap();
                        for (step, len, score) in &scores {
                            writeln!(w, "{step}\t{len}\t{score}").unwrap();
                        }
                        println!(
                            "score log        = {} steps -> {}",
                            scores.len(),
                            path.display()
                        );
                    }
                    None => {
                        println!("step\tlen\tscore");
                        for (step, len, score) in &scores {
                            println!("{step}\t{len}\t{score}");
                        }
                    }
                }
            }
        }
        Cmd::Endgame {
            n,
            file,
            greedy: use_greedy,
            remaining,
        } => {
            let g = Graph::new(n);
            if !(1..=MAX_REMAINING.min(g.nfact - 1)).contains(&remaining) {
                eprintln!(
                    "--remaining must be in 1..={} (got {remaining})",
                    MAX_REMAINING.min(g.nfact - 1)
                );
                std::process::exit(1);
            }
            let (path, src_len, src_desc) = if use_greedy {
                let r = greedy(&g);
                (r.path, r.len, "greedy".to_string())
            } else {
                let file = file.expect("clap enforces --file or --greedy");
                let s = fs::read_to_string(&file)
                    .unwrap_or_else(|e| {
                        eprintln!("cannot read {}: {e}", file.display());
                        std::process::exit(1);
                    })
                    .trim()
                    .to_string();
                let v = validate(n, &s);
                if !v.complete {
                    eprintln!(
                        "not a complete superpermutation: {} / {} perms covered",
                        v.distinct, v.total
                    );
                    std::process::exit(1);
                }
                let t = trace_string(&g, &s).unwrap_or_else(|e| {
                    eprintln!("cannot trace {}: {e}", file.display());
                    std::process::exit(1);
                });
                (t.path, t.replay_len, file.display().to_string())
            };
            let keep = g.nfact - remaining;
            let prefix = &path[..keep];
            let prefix_len = spell_path(&g, prefix).len();
            let mut rem: Vec<u32> = path[keep..].to_vec();
            rem.sort_unstable();
            let t0 = Instant::now();
            let e = solve_endgame(&g, *prefix.last().unwrap(), &rem);
            let dt = t0.elapsed();
            let total = prefix_len + e.cost as usize;
            let own = src_len - prefix_len;
            println!("endgame n={n} source={src_desc} (length {src_len})");
            println!(
                "prefix = {keep} visits, {prefix_len} chars; last {remaining} perms solved exactly ({:.3}s)",
                dt.as_secs_f64()
            );
            println!(
                "exact completion = {} chars -> total {total}; source's own completion = {own} chars (exact saves {})",
                e.cost,
                own - e.cost as usize
            );
            println!("THEOREM: no completion of this {keep}-visit prefix yields length < {total}");
            let mut full = prefix.to_vec();
            full.extend_from_slice(&e.order);
            let s = spell_path(&g, &full);
            assert_eq!(s.len(), total);
            let v = validate(n, &s);
            assert!(v.complete, "recomposed endgame string failed validation");
            println!("{s}");
        }
        Cmd::Rollouts {
            n,
            count,
            epsilon,
            seed,
            model,
            alpha,
            out,
            strings,
        } => {
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
        }
        Cmd::CertVerify { n } => {
            if n != 6 {
                eprintln!("cert-verify: the certificate is defined for n = 6 only (got {n})");
                std::process::exit(1);
            }
            use superperm::cert::{waste_and_length, Cert};
            let cert = Cert::new();
            println!(
                "cert-verify n=6: clean-room verification of the gain-one kernel-chain certificate"
            );
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
                println!(
                    "DISCREPANCY: at least one claim disagrees with this clean-room verification."
                );
                return ExitCode::FAILURE;
            }
        }
        Cmd::TailAtsp {
            n,
            dirs,
            anchor,
            max_blocks,
            ties,
            tie_cap,
            out_dir,
            limit,
            quiet,
        } => {
            use superperm::tailatsp;
            let g = Graph::new(n);
            let dir_refs: Vec<&std::path::Path> = dirs.iter().map(|p| p.as_path()).collect();
            let mut corpus = superperm::corpus::load_corpus(&g, &dir_refs).unwrap_or_else(|e| {
                eprintln!("{e}");
                std::process::exit(1);
            });
            if let Some(k) = limit {
                corpus.truncate(k);
            }
            let t0 = Instant::now();
            let (mut optimal, mut improved, mut skipped, mut new_alloc_ties) =
                (0u64, 0u64, 0u64, 0u64);
            let emit = |tag: &str, s: &str| {
                if let Some(dir) = &out_dir {
                    fs::create_dir_all(dir).expect("create out dir");
                    let path = dir.join(format!("{tag}.txt"));
                    fs::write(&path, format!("{s}\n")).expect("write find");
                    println!("  written -> {}", path.display());
                }
            };
            for rec in &corpus {
                // Shallowest anchor whose instance fits max_blocks: cut
                // deeper until it fits (deeper = fewer blocks).
                let mut min_depth = anchor;
                let inst = loop {
                    match tailatsp::decompose(n, &rec.trace, min_depth) {
                        None => break None,
                        Some(i) if i.blocks.len() <= max_blocks => break Some(i),
                        Some(i) => min_depth = i.anchor_depth + 1,
                    }
                };
                let Some(inst) = inst else {
                    skipped += 1;
                    continue;
                };
                let (opt, order, tie_orders) = tailatsp::solve_bb(&inst, ties, tie_cap);
                if opt < inst.actual {
                    improved += 1;
                    let s = tailatsp::materialize(n, &g, &rec.string, &inst, &order);
                    let v = superperm::validate::validate(n, &s);
                    println!(
                        "*** IMPROVEMENT *** {} anchor={} blocks={} {} -> {} chars={} valid={} ({}/{})",
                        rec.name,
                        inst.anchor_depth,
                        inst.blocks.len(),
                        inst.actual,
                        opt,
                        s.len(),
                        v.complete,
                        v.distinct,
                        v.total
                    );
                    println!("    NEXT: python3 analysis/counting/m3_check.py + validate --complete before ANY claim");
                    emit(&format!("cand-{}", rec.name.trim_end_matches(".txt")), &s);
                } else {
                    optimal += 1;
                    if !quiet {
                        println!(
                            "{}: anchor={} blocks={} cost={} block-order-optimal",
                            rec.name,
                            inst.anchor_depth,
                            inst.blocks.len(),
                            inst.actual
                        );
                    }
                    if ties {
                        let src_alloc = tailatsp::allocation_of(&rec.trace);
                        for (ti, ord) in tie_orders.iter().enumerate() {
                            let s = tailatsp::materialize(n, &g, &rec.string, &inst, ord);
                            if s == rec.string {
                                continue;
                            }
                            let v = superperm::validate::validate(n, &s);
                            if !v.complete || s.len() != rec.string.len() {
                                continue;
                            }
                            let t = superperm::trace::trace_string(&g, &s).expect("tie trace");
                            let alloc = tailatsp::allocation_of(&t);
                            if alloc != src_alloc {
                                new_alloc_ties += 1;
                                println!(
                                    "  tie in NEW allocation {:?} (source {:?}): {} tie#{}",
                                    alloc, src_alloc, rec.name, ti
                                );
                                emit(
                                    &format!("tie-{}-{}", rec.name.trim_end_matches(".txt"), ti),
                                    &s,
                                );
                            }
                        }
                    }
                }
            }
            println!(
                "tail-atsp: {} walks, {optimal} block-order-optimal, {improved} improved, {skipped} skipped, {new_alloc_ties} new-allocation ties ({:.1}s)",
                corpus.len(),
                t0.elapsed().as_secs_f64()
            );
            if improved > 0 {
                std::process::exit(2);
            }
        }
        Cmd::Recomb {
            n,
            dirs,
            emit_dir,
            max_walks,
        } => {
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
        }
        Cmd::UnionDfs {
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
        } => {
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
        }
        Cmd::Validate {
            n,
            string,
            file,
            complete,
        } => {
            let s = match (string, file) {
                (Some(s), None) => s,
                (None, Some(p)) => fs::read_to_string(&p)
                    .unwrap_or_else(|e| {
                        eprintln!("cannot read {}: {e}", p.display());
                        std::process::exit(1);
                    })
                    .trim()
                    .to_string(),
                _ => {
                    eprintln!("provide exactly one of <STRING> or --file");
                    return ExitCode::from(2);
                }
            };
            let v = validate(n, &s);
            println!("length = {}", v.length);
            println!("distinct perms covered = {} / {}", v.distinct, v.total);
            println!("complete superpermutation = {}", v.complete);
            if complete && !v.complete {
                return ExitCode::FAILURE;
            }
        }
    }
    ExitCode::SUCCESS
}
