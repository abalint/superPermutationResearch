#!/usr/bin/env python3
"""Build the s51 supplementary canon indexes (novel5906d + kristan5906_web).

Same canonical form as m3_check.py (s26b convention): min over {s, reverse(s)}
of first-occurrence forward renumbering, sha256 per class. Rerun after adding
files to either directory.
"""
import hashlib
import os

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..")


def renumber(s):
    m, nxt = {}, 0
    out = []
    for c in s:
        if c not in m:
            nxt += 1
            m[c] = str(nxt)
        out.append(m[c])
    return "".join(out)


def canon(s):
    return min(renumber(s), renumber(s[::-1]))


def build(src, out_name):
    rows = []
    d = os.path.join(ROOT, src)
    for f in sorted(os.listdir(d)):
        if not f.endswith(".txt"):
            continue
        s = open(os.path.join(d, f)).read().strip()
        assert len(s) == 5906, (f, len(s))
        rows.append((hashlib.sha256(canon(s).encode()).hexdigest(), f))
    assert len(rows) == len({h for h, _ in rows}), "duplicate classes"
    path = os.path.join(HERE, out_name)
    with open(path, "w") as o:
        o.write("canon_sha256\tclass_file\n")
        for h, f in rows:
            o.write(f"{h}\t{f}\n")
    print(out_name, len(rows), "rows")


if __name__ == "__main__":
    build("data/novel5906d", "novel5906d_canon_index.tsv")
    build("data/kristan5906_web", "kristan5906_web_canon_index.tsv")
