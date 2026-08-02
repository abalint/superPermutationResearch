#!/usr/bin/env python3
"""Canonicalization — BOTH `canon` semantics, under distinct names (s64 P1).

################ READ THIS BEFORE IMPORTING ANYTHING ###################
`canon` was OVERLOADED in this repo across 17 definitions in two
completely different meanings.  They were merged BY BODY, never by name:

  canon_rotation(w)      — least cyclic ROTATION of a word.  The
      kernelchain / certificate frame's loop coordinate.  10 sites, all
      byte-identical one-liners:
        analysis/kernelchain/{chain,skipchain,skipcover}.py
        analysis/kernelchain7/{beam7,enum15,gates7,search7,segment7,
                               trace5907}.py
        analysis/farm/gen_worklist.py

  canon_relabel_rev(s)   — class representative of a superperm string
      under symbol RELABELING and REVERSAL: min(renumber(s),
      renumber(reverse(s))).  The M3 novelty gate's coordinate (s26b
      convention).  7 sites, byte-identical bodies:
        analysis/counting/m3_check.py:75   <-- the DANGER site named in
        analysis/counting/upstream872_census.py:18   REFACTOR-BRIEF §1
        analysis/counting/upstream872_dump.py:20
        analysis/counting/upstream5906_dump.py:43
        analysis/counting/build_supp_index_s51.py:26
        out/s55/aut/aut_scan.py:80                     (frozen)

They are NOT interchangeable: `canon_rotation` takes a loop word to its
necklace representative, `canon_relabel_rev` takes a whole superperm to
its equivalence-class representative.  Swapping them silently produces
wrong novelty verdicts.  Neither name is exported as bare `canon`.
########################################################################

`door` / `loop_of` / `tv` / `inverse_tv` travel with `canon_rotation`
(same 10 sites, same byte-identical one-liners) and are here too.
`h12`/`hash12` are the 12-hex class fingerprints, 12 sites.
"""
import hashlib
import re

from pylib.walkio import renumber

# --------------------------------------------- rotation frame (n=6/n=7) --


def canon_rotation(w):
    """Least cyclic rotation of a word (the loop necklace coordinate)."""
    return min(w[i:] + w[:i] for i in range(len(w)))


def door(w, c):
    """The weight-`c` door out of loop word `w`."""
    return w[c:] + w[:c][::-1]


def tv(w):
    """Twisted-vine successor."""
    return w[1:-1] + w[0] + w[-1]


def inverse_tv(w):
    """Inverse of `tv` (spelled `itv` at some sites)."""
    return w[-2] + w[:-2] + w[-1]


def loop_of(e):
    """(pivot, necklace) loop id of an entry word."""
    return (e[-1], canon_rotation(e[:-1]))


# ----------------------------------------- relabel+reversal class frame --


def canon_relabel_rev(s):
    """Class representative of a superperm string under relabel+reversal.

    s26b convention: min(renumber(s), renumber(s[::-1])).  This is the
    coordinate the committed M3 indexes are keyed by — changing it
    invalidates every `*_canon_index.tsv`.
    """
    return min(renumber(s), renumber(s[::-1]))


def hash12(s):
    """12-hex fingerprint of a string's relabel+reversal class."""
    return hashlib.sha256(canon_relabel_rev(s).encode()).hexdigest()[:12]


def h12(name):
    """Normalize any node spelling (path, class file name, bare hash) to
    its 12-hex hash.

    MERGED SUPERSET of the two tracked bodies: `analysis/counting/s49/
    blindspot.py:22` raises `SystemExit` with the offending spelling when
    no hash is present; `analysis/counting/s49/admdiff.py:76` is the same
    regex but lets the empty match raise `IndexError`.  The explicit
    error is kept — it is strictly more informative and both call sites
    treat a miss as fatal.
    """
    m = re.findall(r"([0-9a-f]{12})", name)
    if not m:
        raise SystemExit(f"no hash12 in {name!r}")
    return m[-1]
