//! `validate` — the candidate-string gate every result must pass.

use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;

use superperm::validate::validate;

#[derive(clap::Args)]
pub struct Args {
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
}

pub fn run(a: Args) -> ExitCode {
    let Args {
        n,
        string,
        file,
        complete,
    } = a;
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
    ExitCode::SUCCESS
}
