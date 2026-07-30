#!/usr/bin/env python3
"""M3 novelty gate (s27b; n-generic since s33): is a candidate walk a
NEW record-length superpermutation?

M3 (TRACKB-DESIGN §6) re-scoped after s26b/c: "independent" means
inequivalent — under symbol relabeling AND reversal — to EVERY known
class of the community corpus, not merely byte-distinct from a local
sample. This script is the one gate every collected candidate (nrpa
--collect, union-dfs --out-dir, tail-atsp finds, hybrids, hand edits)
must pass before any novelty claim.

Per-n corpora (committed canonical indexes; archives stay local):
  n=6: 22,062 classes (superpermutators/superperm, 50,009 strings),
       record 872, index upstream872_canon_index.tsv
  n=7: 84 classes (the 83 published 5906s + Kristan's), record 5906,
       index upstream5906_canon_index.tsv — CAVEAT: the community
       twoCycles_* extension-set files are NOT decoded yet, so the n=7
       index may undercount the known corpus (the n=6 lesson); treat
       an n=7 "novel" verdict as novel-vs-published-strings.

Canonical form (s26b convention): min(renumber(s), renumber(reverse(s)))
where renumber = first-occurrence forward renumbering. The committed
index holds one sha256 per known class, so the check runs on a fresh
clone without the local archive.

Build an index (needs the local archive, see upstream872_dump.py /
upstream5906_dump.py):
    python3 analysis/counting/m3_check.py --build-index data/upstream872
    python3 analysis/counting/m3_check.py -n 7 --build-index data/upstream5906

Check candidates (any files containing one string per file):
    python3 analysis/counting/m3_check.py <file> [<file> ...]
    python3 analysis/counting/m3_check.py -n 7 <file> [<file> ...]

Exit codes: 0 = nothing new (all candidates known, invalid, or over the
record); 2 = AT LEAST ONE NOVEL COMPLETE candidate at or under the
record (the M3 event — re-verify with `validate -n <n> --file <f>
--complete` and archive before celebrating); 1 = usage/index errors.
"""
import hashlib
import math
import os
import sys

HERE = os.path.dirname(__file__)
PER_N = {
    6: {"record": 872, "index": "upstream872_canon_index.tsv"},
    7: {"record": 5906, "index": "upstream5906_canon_index.tsv"},
}


def renumber(s):
    m, nxt, out = {}, 0, []
    for c in s:
        if c not in m:
            nxt += 1
            m[c] = str(nxt)
        out.append(m[c])
    return "".join(out)


def canon(s):
    return min(renumber(s), renumber(s[::-1]))


def validate(s, n):
    """(complete, distinct_perms): sliding-window check, the only
    accepted proof (mirrors src/validate.rs)."""
    alphabet = set("123456789"[:n])
    seen = set()
    for i in range(len(s) - n + 1):
        w = s[i : i + n]
        if len(set(w)) == n and set(w) <= alphabet:
            seen.add(w)
    return len(seen) == math.factorial(n), len(seen)


def build_index(archive_dir, n, record, index_path):
    files = sorted(f for f in os.listdir(archive_dir) if f.endswith(".txt"))
    rows = []
    for f in files:
        s = open(os.path.join(archive_dir, f)).read().strip()
        ok, _ = validate(s, n)
        if not ok or len(s) != record:
            print(f"REFUSING to index {f}: not a complete {record}", file=sys.stderr)
            return 1
        rows.append((hashlib.sha256(canon(s).encode()).hexdigest(), f))
    dups = len(rows) - len({h for h, _ in rows})
    if dups:
        print(f"WARNING: {dups} duplicate canonical classes in the archive",
              file=sys.stderr)
    with open(index_path, "w") as out:
        out.write("canon_sha256\tclass_file\n")
        for h, f in sorted(rows):
            out.write(f"{h}\t{f}\n")
    print(f"indexed {len(rows)} classes ({len({h for h, _ in rows})} distinct) "
          f"-> {index_path}")
    return 0


def load_index(index_path):
    if not os.path.exists(index_path):
        print(f"index missing: {index_path}\n(build it with --build-index; needs "
              f"the local archive, see upstream872_dump.py / upstream5906_dump.py)",
              file=sys.stderr)
        sys.exit(1)
    idx = {}
    with open(index_path) as f:
        next(f)
        for line in f:
            h, name = line.rstrip("\n").split("\t")
            idx[h] = name
    return idx


def main():
    args = sys.argv[1:]
    n = 6
    if args[:1] == ["-n"]:
        if len(args) < 2 or not args[1].isdigit() or int(args[1]) not in PER_N:
            print(f"-n takes one of {sorted(PER_N)}", file=sys.stderr)
            return 1
        n = int(args[1])
        args = args[2:]
    if not args:
        print(__doc__, file=sys.stderr)
        return 1
    record = PER_N[n]["record"]
    index_path = os.path.join(HERE, PER_N[n]["index"])
    if args[0] == "--build-index":
        return build_index(args[1], n, record, index_path)
    idx = load_index(index_path)
    print(f"known-{record} index: {len(idx)} classes (relabel+reversal canonical)")
    nfact = math.factorial(n)
    novel = 0
    for path in args:
        s = open(path).read().strip()
        ok, distinct = validate(s, n)
        if not ok:
            print(f"{path}: INVALID (length {len(s)}, {distinct}/{nfact} perms) "
                  f"— not a superpermutation, no claim")
            continue
        hit = idx.get(hashlib.sha256(canon(s).encode()).hexdigest())
        if len(s) > record:
            print(f"{path}: valid, length {len(s)} > {record} — "
                  + (f"equivalent to known {hit}" if hit else "not in the "
                     f"known-{record} corpus (expected: the corpus holds only "
                     f"{record}s)")
                  + "; not an M3 event")
        elif hit:
            print(f"{path}: valid {record}, EQUIVALENT to known class {hit} — "
                  f"a rediscovery, not M3")
        else:
            novel += 1
            print(f"{path}: length {len(s)} <= {record}, complete, and "
                  f"INEQUIVALENT to all {len(idx)} known classes")
            print("!" * 72)
            print(f"!!  NOVEL <= {record}: possible M3"
                  + (" / WORLD RECORD" if len(s) < record else "")
                  + "  — re-verify with the Rust validator and archive NOW")
            print("!" * 72)
    return 2 if novel else 0


if __name__ == "__main__":
    sys.exit(main())
