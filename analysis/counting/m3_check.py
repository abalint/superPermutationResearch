#!/usr/bin/env python3
"""M3 novelty gate (s27b): is a candidate walk a NEW n=6 872?

M3 (TRACKB-DESIGN §6) re-scoped after s26b/c: "independent 872" means
inequivalent — under symbol relabeling AND reversal — to EVERY class of
the community corpus (superpermutators/superperm; 50,009 strings =
22,062 classes), not merely byte-distinct from our old 296-record
sample. This script is the one gate every collected candidate (nrpa
--collect, union-dfs --out-dir, hybrids, hand edits) must pass before
any novelty claim.

Canonical form (s26b convention): min(renumber(s), renumber(reverse(s)))
where renumber = first-occurrence forward renumbering. The committed
index holds one sha256 per known class, so the check runs on a fresh
clone without the 22,062-file local archive.

Build the index (needs data/upstream872/, see upstream872_dump.py):
    python3 analysis/counting/m3_check.py --build-index data/upstream872

Check candidates (any files containing one string per file):
    python3 analysis/counting/m3_check.py <file> [<file> ...]

Exit codes: 0 = nothing new (all candidates known, invalid, or >872);
2 = AT LEAST ONE NOVEL COMPLETE <=872 (the M3 event — re-verify with
`validate -n 6 --file <f> --complete` and archive before celebrating);
1 = usage/index errors.
"""
import hashlib
import os
import sys

N = 6
NFACT = 720
RECORD = 872
INDEX = os.path.join(os.path.dirname(__file__), "upstream872_canon_index.tsv")


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


def validate(s):
    """(complete, distinct_perms): sliding-window check, the only
    accepted proof (mirrors src/validate.rs)."""
    seen = set()
    for i in range(len(s) - N + 1):
        w = s[i : i + N]
        if len(set(w)) == N and all(c in "123456" for c in w):
            seen.add(w)
    return len(seen) == NFACT, len(seen)


def build_index(archive_dir):
    files = sorted(f for f in os.listdir(archive_dir) if f.endswith(".txt"))
    rows = []
    for f in files:
        s = open(os.path.join(archive_dir, f)).read().strip()
        ok, _ = validate(s)
        if not ok or len(s) != RECORD:
            print(f"REFUSING to index {f}: not a complete 872", file=sys.stderr)
            return 1
        rows.append((hashlib.sha256(canon(s).encode()).hexdigest(), f))
    dups = len(rows) - len({h for h, _ in rows})
    if dups:
        print(f"WARNING: {dups} duplicate canonical classes in the archive",
              file=sys.stderr)
    with open(INDEX, "w") as out:
        out.write("canon_sha256\tclass_file\n")
        for h, f in sorted(rows):
            out.write(f"{h}\t{f}\n")
    print(f"indexed {len(rows)} classes ({len({h for h, _ in rows})} distinct) "
          f"-> {INDEX}")
    return 0


def load_index():
    if not os.path.exists(INDEX):
        print(f"index missing: {INDEX}\n(build it with --build-index; needs the "
              f"local data/upstream872/ archive, see upstream872_dump.py)",
              file=sys.stderr)
        sys.exit(1)
    idx = {}
    with open(INDEX) as f:
        next(f)
        for line in f:
            h, name = line.rstrip("\n").split("\t")
            idx[h] = name
    return idx


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        return 1
    if args[0] == "--build-index":
        return build_index(args[1])
    idx = load_index()
    print(f"known-872 index: {len(idx)} classes (relabel+reversal canonical)")
    novel = 0
    for path in args:
        s = open(path).read().strip()
        ok, distinct = validate(s)
        if not ok:
            print(f"{path}: INVALID (length {len(s)}, {distinct}/{NFACT} perms) "
                  f"— not a superpermutation, no claim")
            continue
        hit = idx.get(hashlib.sha256(canon(s).encode()).hexdigest())
        if len(s) > RECORD:
            print(f"{path}: valid, length {len(s)} > {RECORD} — "
                  + (f"equivalent to known {hit}" if hit else "not in the "
                     "known-872 corpus (expected: the corpus holds only 872s)")
                  + "; not an M3 event")
        elif hit:
            print(f"{path}: valid 872, EQUIVALENT to known class {hit} — "
                  f"a rediscovery, not M3")
        else:
            novel += 1
            print(f"{path}: length {len(s)} <= {RECORD}, complete, and "
                  f"INEQUIVALENT to all {len(idx)} known classes")
            print("!" * 72)
            print(f"!!  NOVEL <= {RECORD}: possible M3"
                  + (" / WORLD RECORD" if len(s) < RECORD else "")
                  + "  — re-verify with the Rust validator and archive NOW")
            print("!" * 72)
    return 2 if novel else 0


if __name__ == "__main__":
    sys.exit(main())
