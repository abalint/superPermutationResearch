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


# s64 P1: one body each, in pylib/walkio.py + pylib/canonical.py.  `canon`
# here is the RELABEL+REVERSAL class representative (m3_check semantics) --
# pylib keeps it apart from the kernelchain least-rotation `canon` by name.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
from pylib.canonical import canon_relabel_rev as canon  # noqa: E402,F401
from pylib.walkio import renumber  # noqa: E402,F401


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
