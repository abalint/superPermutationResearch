#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s62/jtax/verify_master.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# See pylib/README.md.
# --------------------------------------------------------------------
"""s62 D1 verifier: the exact identity and the MASTER inequality, per walk.

  ID      length == n! + (n-1)! + (n-3) + v + j + xp
  SUPPLY  S <= (n-1)*v
  MASTER  length >= n! + (n-1)! + (n-3) + ceil(S/(n-1)) + j + xp
  LADDER  (n=6 restatement) length >= 867 + ceil(splits/5) + j + xp

Exit 0 = every walk passes.  Non-zero + loud output on any violation.
Usage: verify_master.py <n> <file-or-dir>...
"""
import os
import sys
import time
from collections import Counter
from math import factorial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib62 import first_visit_path, analyze_path, master_terms  # noqa: E402


def main():
    t0 = time.time()
    n = int(sys.argv[1])
    files = []
    for arg in sys.argv[2:]:
        if os.path.isdir(arg):
            files += [os.path.join(arg, f) for f in sorted(os.listdir(arg))
                      if f.endswith(".txt")]
        else:
            files.append(arg)
    read = impure = 0
    bad = []
    tight_master = 0
    jhist = Counter()
    slackhist = Counter()
    for f in files:
        s = open(f).read().strip().replace("\n", "")
        if not s or set(s) - set("123456789"):
            continue
        path = first_visit_path(s, n)
        if len(path) != factorial(n):
            continue
        r = analyze_path(path, n)
        if r is None:
            impure += 1
            continue
        read += 1
        ident, master, sup = master_terms(r)
        if ident != r["length"]:
            bad.append(("ID", f, r["length"], ident, r))
        if r["S"] > (n - 1) * r["v"]:
            bad.append(("SUPPLY", f, r["S"], (n - 1) * r["v"], r))
        if r["length"] < master:
            bad.append(("MASTER", f, r["length"], master, r))
        if r["length"] == master:
            tight_master += 1
        jhist[r["j"]] += 1
        slackhist[r["length"] - master] += 1
    dt = time.time() - t0
    print(f"n={n} walks read: {read}  (impure skipped: {impure})")
    print(f"j histogram: {dict(sorted(jhist.items()))}")
    print(f"MASTER slack histogram (length - master_rhs): "
          f"{dict(sorted(slackhist.items()))}")
    print(f"MASTER exactly tight on {tight_master}/{read}")
    print(f"runtime {dt:.1f}s")
    if bad:
        print(f"\n*** {len(bad)} VIOLATIONS ***")
        for kind, f, got, want, r in bad[:20]:
            print(f"  {kind}: {f} got={got} want={want} "
                  f"S={r['S']} splits={r['splits']} D={r['D']} xp={r['xp']} "
                  f"v={r['v']} j={r['j']} L={r['L']}")
        sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
