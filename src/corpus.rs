//! Record corpus loading shared by the s26 recombination probes
//! (`docs/RECOMB-DESIGN.md` §3).
//!
//! Loads every record file from a list of directories into traced walk
//! form. Deterministic (sorted per-directory file order), skips files
//! that are not bare superpermutation strings (e.g. `_filelist.txt`),
//! and fails loudly on corrupt records: a file that *looks* like a
//! record but is untight (`replay_len != input_len`) or incomplete
//! (fewer than `n!` first visits) is an error, not a skip — silent
//! corpus shrinkage would invalidate every census downstream.

use crate::graph::Graph;
use crate::trace::{trace_string, Trace};
use std::path::Path;

/// One corpus record: file stem, raw string, and its first-visit trace.
pub struct CorpusRecord {
    /// File name (without directory) the string was loaded from.
    pub name: String,
    /// The superpermutation string, as stored.
    pub string: String,
    /// First-visit path/weights (`trace::trace_string`).
    pub trace: Trace,
}

/// True iff `s` consists solely of digits `'1'..=('0'+n)` — the shape
/// of a bare record file for this `n`.
fn is_record_shaped(n: usize, s: &str) -> bool {
    let hi = b'0' + n as u8;
    !s.is_empty() && s.bytes().all(|b| (b'1'..=hi).contains(&b))
}

/// Load, trace, and dedup the record corpus in `dirs`.
///
/// Per directory, files are read in sorted name order. A file whose
/// trimmed content is not record-shaped is skipped (with a note to
/// stderr). Record-shaped files must trace tight and complete:
/// `replay_len == input_len` and `path.len() == n!` — anything else is
/// an error naming the file. Byte-identical strings are deduped, first
/// name wins.
pub fn load_corpus(g: &Graph, dirs: &[&Path]) -> Result<Vec<CorpusRecord>, String> {
    let nfact = crate::graph::factorial(g.n);
    let mut out: Vec<CorpusRecord> = Vec::new();
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    for dir in dirs {
        let mut names: Vec<_> = std::fs::read_dir(dir)
            .map_err(|e| format!("{}: {e}", dir.display()))?
            .filter_map(|ent| ent.ok())
            .filter(|ent| ent.path().is_file())
            .map(|ent| ent.file_name().to_string_lossy().into_owned())
            .collect();
        names.sort();
        for name in names {
            let path = dir.join(&name);
            let raw =
                std::fs::read_to_string(&path).map_err(|e| format!("{}: {e}", path.display()))?;
            let s = raw.trim();
            if !is_record_shaped(g.n, s) {
                eprintln!("corpus: skipping non-record file {}", path.display());
                continue;
            }
            let trace = trace_string(g, s).map_err(|e| format!("{}: {e}", path.display()))?;
            if trace.replay_len != trace.input_len {
                return Err(format!(
                    "{}: untight record (input {} chars, maximal-overlap replay {})",
                    path.display(),
                    trace.input_len,
                    trace.replay_len
                ));
            }
            if trace.path.len() != nfact {
                return Err(format!(
                    "{}: incomplete record ({} of {} permutations visited)",
                    path.display(),
                    trace.path.len(),
                    nfact
                ));
            }
            if seen.insert(s.to_string()) {
                out.push(CorpusRecord {
                    name,
                    string: s.to_string(),
                    trace,
                });
            }
        }
    }
    if out.is_empty() {
        return Err("corpus: no records loaded".to_string());
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::greedy::greedy;
    use std::io::Write;

    fn write_file(dir: &Path, name: &str, content: &str) {
        let mut f = std::fs::File::create(dir.join(name)).unwrap();
        write!(f, "{content}").unwrap();
    }

    fn temp_dir(tag: &str) -> std::path::PathBuf {
        let d = std::env::temp_dir().join(format!(
            "superperm-corpus-test-{tag}-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn loads_dedups_and_skips() {
        let g = Graph::new(5);
        let s153 = greedy(&g).string;
        assert_eq!(s153.len(), 153);
        let d = temp_dir("basic");
        write_file(&d, "a.txt", &s153);
        write_file(&d, "b.txt", &s153); // byte-identical dup
        write_file(&d, "_filelist.txt", "a.txt\nb.txt\n"); // non-record shape
        let recs = load_corpus(&g, &[&d]).unwrap();
        assert_eq!(recs.len(), 1);
        assert_eq!(recs[0].name, "a.txt");
        assert_eq!(recs[0].trace.path.len(), 120);
        assert_eq!(recs[0].trace.replay_len, recs[0].trace.input_len);
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn corrupt_record_is_an_error() {
        let g = Graph::new(5);
        let s153 = greedy(&g).string;
        let d = temp_dir("corrupt");
        // Record-shaped but incomplete: a prefix that covers some perms only.
        write_file(&d, "bad.txt", &s153[..60]);
        let err = match load_corpus(&g, &[&d]) {
            Err(e) => e,
            Ok(_) => panic!("corrupt record loaded"),
        };
        assert!(err.contains("bad.txt"), "{err}");
        std::fs::remove_dir_all(&d).unwrap();
    }

    #[test]
    fn n6_record_dirs_load() {
        if !Path::new("data/records872").exists() {
            eprintln!("skipping: gitignored corpus not present");
            return;
        }
        let g = Graph::new(6);
        let recs = load_corpus(
            &g,
            &[Path::new("data/records872"), Path::new("data/gain1_872s")],
        )
        .unwrap();
        assert_eq!(recs.len(), 296);
        assert!(recs
            .iter()
            .all(|r| r.trace.input_len == 872 && r.trace.path.len() == 720));
    }
}
