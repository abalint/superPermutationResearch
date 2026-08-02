"""`pylib` — the tracked Python instrument layer for this repo (s64 P1).

WHY THIS EXISTS
---------------
Before s64 the engine-grade Python instruments lived in gitignored
`out/sNN/` directories (one `rm -rf out/` from gone) and 275 ad-hoc
`sys.path` mutations glued them together in eight mutually incompatible
spellings, several of them cwd-dependent.  s64 P1 promoted the
instruments here BY COPY.  The `out/sNN` originals are FROZEN history —
the session REPORTs cite them by path, so they stay byte-untouched.
**These copies are canonical**: new work imports from `pylib`, and any
fix goes here, never into `out/`.

THE ONE SANCTIONED BOOTSTRAP
----------------------------
Scripts in this repo run as plain files from arbitrary depths
(`python3 analysis/counting/m3_check.py …`), so Python puts the *script's*
directory on `sys.path`, not the repo root.  Every entry script therefore
carries exactly ONE line, identical everywhere, before its `pylib`
imports:

    # --- pylib bootstrap (s64 P1): the ONE sanctioned sys.path line ---
    import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))

It is depth-independent, cwd-independent, and grep-countable
(`git grep -n "sys.path" -- analysis/ ml/` counts entry scripts, nothing
else).  Everything downstream of it goes through this module:

    import pylib
    pylib.add_paths("analysis/counting")      # repo-relative, idempotent
    pylib.add_legacy_paths()                  # not-yet-promoted homes
    from pylib.walkio import first_visit_path, weight
    from pylib.canonical import canon_relabel_rev

Importing `pylib` also puts the repo root AND this directory on
`sys.path`, so the promoted instruments' own flat imports
(`import lib62`, `import chain7`, …) resolve to the promoted copies.

NOT A DISTRIBUTION
------------------
Deliberately no `pyproject.toml`/`setup.py`: nothing is installed,
nothing is versioned, consumers are scripts inside this repo.
"""
import os
import sys

PYLIB_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(PYLIB_DIR)

# `certificate.py` / `gain1.py` live OUTSIDE this repo, in the sibling
# checkout of the community examples.  `chain7` needs `certificate`, so
# this path is a hard external dependency of the whole n=7 stack.
EXTRA_DOCS_SCRIPTS = os.path.abspath(
    os.path.join(REPO_ROOT, "..", "extraDocs",
                 "superpermutation-examples", "scripts"))

# Homes of modules the promoted instruments still reach outside pylib/.
# s64 P1b promoted prefixlib (out/s59) and p1a_assume (out/s56) into the
# package, so the only remaining CODE dependency here is the external
# certificate/gain1 pair; the out/ entries below are DATA homes
# (controls.pkl, prune_all.json, positives.pkl — regenerable artifacts).
LEGACY_MODULE_HOMES = (
    os.path.join(REPO_ROOT, "out", "s57", "proposer"),  # data: controls.pkl, prune_all.json
    EXTRA_DOCS_SCRIPTS,                                 # certificate, gain1
)


def _prepend(path):
    """Idempotent front-insert of an existing directory."""
    if path and os.path.isdir(path):
        path = os.path.abspath(path)
        if path in sys.path:
            sys.path.remove(path)
        sys.path.insert(0, path)
        return True
    return False


def add_paths(*rel_dirs):
    """Put repo-relative directories on `sys.path` (front, idempotent).

    The single replacement for every hand-rolled
    `sys.path.insert(0, os.path.join(R, 'analysis', 'counting'))` in
    tracked code.  Missing directories are skipped silently — the old
    spellings did the same, and a missing dir must fail as an
    ImportError at the point of use, not here.
    """
    for rel in rel_dirs:
        _prepend(rel if os.path.isabs(rel) else os.path.join(REPO_ROOT, rel))


def add_legacy_paths():
    """Reach the not-yet-promoted module homes (see LEGACY_MODULE_HOMES).

    Call this before `import chain7` (or anything that pulls it in).
    `chain7` itself is promoted, but it imports `certificate` from the
    sibling `extraDocs` checkout, so n=7 code needs this even for the
    promoted copy.  prefixlib/p1a_assume are promoted as of s64 P1b.
    """
    for p in LEGACY_MODULE_HOMES:
        _prepend(p)
    # ... but the promoted copies always win: `out/s57/proposer` holds the
    # frozen dlxrun.py, `analysis/cover7` the frozen chain7.py.
    _prepend(PYLIB_DIR)
    _prepend(REPO_ROOT)


# Make the repo root and this package directory importable the moment
# `pylib` itself is imported.  The promoted instruments use flat imports
# among themselves (`from lib62 import …`), which is how they run under
# `python3 pylib/<tool>.py`; this keeps `from pylib import <tool>` on the
# same resolution.
_prepend(PYLIB_DIR)
_prepend(REPO_ROOT)
