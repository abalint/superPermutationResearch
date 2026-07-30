#!/usr/bin/env python3
"""Assemble the n=7 record corpus (s33; template: upstream872_dump.py).

Sources (all local, gathered in ../extraDocs — no network):
  - known5906_corpus/7_5906_nsk*.txt : the 83 published 5906 strings
    (community repo superpermutators/superperm, superpermutations/7/7_5906;
    the twoCycles_* companions are two-cycle EXTENSION SETS in set-of-tuples
    notation, not strings — decoding them into additional 5906s is future
    work and a known completeness caveat, cf. the n=6 lesson where a
    296-string sample hid a 22,062-class corpus).
  - tk-5906-repeat.txt : Tomaz Kristan's 5906 (the only known non-symmetric
    one; its "repeated permutation" is bookkeeping — the string read as a
    simple path is byte-identical, see 2026-07-29-tomaz-kristan-5906-repeat.md).
  - superpermutation-examples/n7/5907-*.txt : the three urdvr 5907s.

One forward-renumbered representative per equivalence class (relabel +
reversal), identity-start required by trace_string, exactly as at n=6:
  data/upstream5906/5906.up-<sha1:12>.txt   (gitignored archive)
  data/upstream5907/5907.up-<sha1:12>.txt
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
EXTRA = os.path.join(ROOT, os.pardir, "extraDocs")

N = 7
ALPHABET = "1234567"


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


def load_digits(path):
    """Every alphabet character in the file, concatenated (the tk file
    carries stray bytes; the nsk files are one string per line)."""
    with open(path, errors="replace") as fh:
        return fh.read()


def strings_from_text(text, length):
    for line in text.splitlines():
        line = "".join(c for c in line.strip() if c in ALPHABET)
        if len(line) == length and line:
            yield line


def gather(length, paths):
    reps = {}  # canon -> (forward string, source name)
    total = 0
    for p in paths:
        for s in strings_from_text(load_digits(p), length):
            total += 1
            c = canon(s)
            if c not in reps:
                reps[c] = (renumber(s), os.path.basename(p))
    return reps, total


def dump(reps, out_dir, prefix):
    os.makedirs(out_dir, exist_ok=True)
    skipped = 0
    for c, (fwd, src) in sorted(reps.items()):
        if len(set(fwd[:N])) != N:
            skipped += 1
            print(f"  skipped non-identity-start rep from {src}", file=sys.stderr)
            continue
        h = hashlib.sha1(fwd.encode()).hexdigest()[:12]
        with open(os.path.join(out_dir, f"{prefix}.up-{h}.txt"), "w") as f:
            f.write(fwd)
    return skipped


def main():
    corp = os.path.join(EXTRA, "known5906_corpus")
    src5906 = sorted(
        os.path.join(corp, f)
        for f in os.listdir(corp)
        if f.startswith("7_5906_nsk") and f.endswith(".txt")
    )
    src5906.append(os.path.join(EXTRA, "tk-5906-repeat.txt"))
    ex7 = os.path.join(EXTRA, "superpermutation-examples", "n7")
    src5907 = sorted(
        os.path.join(ex7, f)
        for f in os.listdir(ex7)
        if f.startswith("5907-") and f.endswith(".txt")
    )

    reps6, total6 = gather(5906, src5906)
    reps7, total7 = gather(5907, src5907)
    sk6 = dump(reps6, os.path.join(ROOT, "data", "upstream5906"), "5906")
    sk7 = dump(reps7, os.path.join(ROOT, "data", "upstream5907"), "5907")
    print(
        f"5906: {total6} strings from {len(src5906)} files -> "
        f"{len(reps6)} classes, {len(reps6) - sk6} written, {sk6} skipped"
    )
    print(
        f"5907: {total7} strings from {len(src5907)} files -> "
        f"{len(reps7)} classes, {len(reps7) - sk7} written, {sk7} skipped"
    )


if __name__ == "__main__":
    main()
