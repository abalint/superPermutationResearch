#!/usr/bin/env python3
"""Walk parsing and corpus loading — the ONE canonical copy (s64 P1).

Consolidates the copy-paste family the s63 survey measured: six
near-identical `first_visit_path`, six `renumber`, three `weight`, plus
the `rot`/`rotc`/`g`/`lam` quartet that always travelled with them.

MERGED BY BODY, not by name.  Every promoted body was diffed against
every copy before it was written here:

  first_visit_path — 6 sites, all semantically identical, differing only
    in whitespace and local variable names:
      analysis/counting/loop_ledger_probe.py:70   (the body kept here)
      analysis/trackb/verify_identity.py:45       (+ docstring)
      analysis/counting/upstream5906_twocycles.py:78  (n from a module
          global instead of a parameter — the SIGNATURE is the only
          difference; the (s, n) form is the superset and is kept)
      out/s62/jtax/lib62.py:59                    (frozen)
      out/s56/slacktax/jpricing.py:39             (frozen)
      out/s55/aut/aut_scan.py:42                  (frozen)
  renumber — 6 sites, byte-identical bodies:
      analysis/counting/m3_check.py:65 (kept), upstream872_census.py:9,
      upstream872_dump.py:11, upstream5906_dump.py:33,
      build_supp_index_s51.py:15, tail_conjugacy_census.py:75
      (build_supp_index_s51's differs only in where `out = []` sits).
  weight — 3 sites, byte-identical:
      analysis/counting/loop_ledger_probe.py:82 (kept),
      out/s62/jtax/lib62.py, out/s56/slacktax/jpricing.py.
  rot / rotc / g / lam — analysis/counting/loop_ledger_probe.py:89-115
      (kept) and out/s62/jtax/lib62.py.

`first_visit_starts` (analysis/counting/tail_conjugacy_census.py:75) is
the index-returning sibling of `first_visit_path` and lives here too.
`overlap` is analysis/trackb/verify_identity.py's, which is `weight`
counting the other way (`weight(a, b, n) == n - overlap(a, b)`); both
are kept because both spellings have call sites.

Rotation/relabel canonicalization is deliberately NOT here — see
`pylib/canonical.py`, which documents the `canon` NAME COLLISION.
"""
import os

# --------------------------------------------------------------- walks --


def first_visit_path(s, n):
    """First-visit permutation sequence of `s`, as a list of n-tuples."""
    want = set(range(1, n + 1))
    seen, path = set(), []
    vals = [int(c) for c in s]
    for i in range(len(vals) - n + 1):
        win = tuple(vals[i : i + n])
        if set(win) == want and win not in seen:
            seen.add(win)
            path.append(win)
    return path


def first_visit_starts(s, n):
    """Start index of each first-visit permutation window, in order."""
    want = set("123456789"[:n])
    seen, starts = set(), []
    for i in range(len(s) - n + 1):
        w = s[i : i + n]
        if len(set(w)) == n and set(w) <= want and w not in seen:
            seen.add(w)
            starts.append(i)
    return starts


def weight(a, b, n):
    """Edge weight of a -> b: n minus the longest suffix/prefix overlap."""
    for k in range(n - 1, 0, -1):
        if a[n - k :] == b[:k]:
            return n - k
    return n


def overlap(p, q):
    """Length of the longest suffix of p that is a prefix of q."""
    n = len(p)
    for k in range(n - 1, 0, -1):
        if p[n - k :] == q[:k]:
            return k
    return 0


# ------------------------------------------------- perms, cycles, loops --


def rot(p):
    """Weight-1 successor: rotate a perm tuple left by one."""
    return p[1:] + (p[0],)


def rotc(p):
    """Cycle id of a perm tuple = the lexicographically least rotation."""
    return min(p[i:] + p[:i] for i in range(len(p)))


def g(q):
    """Jump-composed map (the weight-2 cross-cycle successor's frame)."""
    n = len(q)
    return q[1 : n - 1] + (q[0], q[n - 1])


_LAM = {}


def lam(p):
    """Loop id of a perm tuple = least element of its g-orbit (cached)."""
    c = _LAM.get(p)
    if c is not None:
        return c
    orb = [p]
    for _ in range(len(p) - 2):
        orb.append(g(orb[-1]))
    c = min(orb)
    for q in orb:
        _LAM[q] = c
    return c


# ------------------------------------------------------- relabelling ----


def renumber(s):
    """First-occurrence forward renumbering of a digit string."""
    m, nxt, out = {}, 0, []
    for c in s:
        if c not in m:
            nxt += 1
            m[c] = str(nxt)
        out.append(m[c])
    return "".join(out)


# ---------------------------------------------------- corpus loading ----


def read_walk(path):
    """One superperm string from a one-string file."""
    with open(path) as fh:
        return fh.read().strip()


def class_files(dirs, root=None):
    """{class file name -> path} over repo-relative (or absolute) dirs.

    TRAP (HANDOFF-S51, kept verbatim from analysis/counting/s49/fuse.py's
    `file_map`): the suffix test is `endswith('.txt')` EXACTLY.
    `data/kristan5906_web/` holds `.txt.rediscovery` files that a
    `*.txt*` glob would inflate 2 -> 5.
    """
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    m = {}
    for d in dirs:
        p = d if os.path.isabs(d) else os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if f.endswith(".txt"):
                m.setdefault(f, os.path.join(p, f))
    return m


def strings_from_text(text, length, alphabet):
    """Every line of `text` that is a `length`-char word over `alphabet`.

    The n=6 corpus-dump filter (analysis/counting/upstream872_{census,
    dump}.py), generalized over (length, alphabet) instead of hardcoding
    872 / "123456".
    """
    for line in text.splitlines():
        line = line.strip()
        if len(line) == length and all(c in alphabet for c in line):
            yield line
