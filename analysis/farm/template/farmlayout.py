#!/usr/bin/env python3
"""farmlayout -- resolve repo-relative paths under EITHER farm layout (s64 P5).

THE PROBLEM THIS RETIRES.  Every farm shim hand-probed the same two
candidates, in six near-identical spellings:

    analysis/farm/i4a_shim.py:26      repo/analysis/counting   ../counting
    analysis/farm/lswap_shim.py:35    repo/analysis/counting   ../counting
    analysis/farm/promote_shim.py:48  repo/analysis/counting/s51  ../counting/s51
    analysis/farm/paircuts_shim.py:38 repo/analysis/counting/s58  ../counting/s58
    analysis/farm/enumext_shim.py:34  repo/analysis/counting/s58  ../counting/s58
    analysis/farm/mc28_shim.py:113    repo/pylib               ../../pylib

Each probe is correct and each is written slightly differently, so a fix to
one reaches none of the others -- which is the whole reason the quartets were
worth unifying.  There is now ONE resolver, here.

WHY THE PROBE EXISTS AT ALL.  `pysweep_run.ps1` launches every shard as

    upyw.exe -u <TARGET> [<Mode>] --shard i/N --out <dir> ... <ExtraArgs>

with `$TGT = "$ROOT\\<Target>"`: the adapter MUST sit at the farm root, while
the instrument it drives derives its own repo root from `__file__` and so must
stay inside the repo mirror.  So the two layouts an adapter can find itself in
are:

    FARM   <adapter dir>\\repo\\<repo-relative path>      (payload extracted
                                                          under repo\\)
    MAC    <repo root>/<repo-relative path>               (a plain checkout,
                                                          adapter under
                                                          analysis/farm/...)

`repo_path()` returns the first that exists, and says which.  Nothing else in
the farm tree needs to know about layouts.

This module is deliberately stdlib-only and dependency-free: it is the
bootstrap, so it cannot import anything it might have to locate first.  It
ships to the farm root next to the adapters (see farm_ship.sh's SCRIPTS).
"""
import os
import sys

__all__ = ["FARM", "MAC", "HERE", "add_pylib", "add_repo_path", "layout",
           "repo_path", "repo_root"]

HERE = os.path.dirname(os.path.abspath(__file__))
FARM = "farm"    # <adapter dir>\repo\...
MAC = "mac"      # a plain checkout


def _mac_root(start=None):
    """Nearest ancestor of `start` that looks like this repo checkout.

    "Looks like" = contains BOTH `pylib/` and `analysis/` -- two markers, so
    a stray `pylib` copy somewhere up the tree cannot win.  Depth-independent
    (the same property the pylib bootstrap line has), so an adapter can live
    at any depth under the repo.
    """
    p = os.path.abspath(start or HERE)
    while True:
        if (os.path.isdir(os.path.join(p, "pylib"))
                and os.path.isdir(os.path.join(p, "analysis"))):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def repo_root():
    """(root, layout) -- the directory repo-relative paths hang off.

    FARM wins if `<adapter dir>\\repo` exists, because on the farm the MAC
    probe could otherwise walk up into an unrelated tree.
    """
    farm = os.path.join(HERE, "repo")
    if os.path.isdir(farm):
        return os.path.abspath(farm), FARM
    mac = _mac_root()
    if mac:
        return mac, MAC
    return None, None


def layout():
    """FARM, MAC, or None (unresolvable)."""
    return repo_root()[1]


def repo_path(*rel, **kw):
    """Resolve a repo-relative path under whichever layout is present.

    `required=True` (the default) exits 2 with a diagnostic naming both
    candidates rather than raising an opaque ImportError three frames later:
    a shard that cannot find its instrument must fail loudly at startup, when
    the operator is still watching, not on the first import inside the DFS.
    """
    required = kw.pop("required", True)
    if kw:
        raise TypeError(f"unexpected kwargs: {sorted(kw)}")
    root, _ = repo_root()
    cands = []
    if root:
        cands.append(os.path.join(root, *rel))
    else:  # nothing resolved -- report both shapes we would have accepted
        cands = [os.path.join(HERE, "repo", *rel),
                 os.path.join(HERE, "..", "..", *rel)]
    for c in cands:
        if os.path.exists(c):
            return os.path.abspath(c)
    if required:
        print(f"farmlayout: cannot locate {os.path.join(*rel)} "
              f"(tried: {', '.join(os.path.abspath(c) for c in cands)})",
              file=sys.stderr)
        sys.exit(2)
    return None


def add_repo_path(*rel):
    """Put a repo-relative DIRECTORY on `sys.path` (front, idempotent)."""
    p = repo_path(*rel)
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)
    return p


def exec_instrument(*rel):
    """Locate an instrument in the repo mirror and RUN IT IN PLACE.

    The whole body of a "thin" adapter (what `a0_shim.py`, `qsb_shim.py`,
    `paircuts_shim.py` and `enumext_shim.py` each spelled out separately):
    the instrument already speaks `--shard i/N --out DIR` and writes its own
    STATUS, so nothing needs translating -- but it must run from INSIDE the
    repo mirror, because it derives its own repo root from `__file__`.  An
    adapter is the one file that lives at the farm root; this runs the
    instrument from where it actually is.

    THE -Mode TOKEN.  `pysweep_run.ps1` interpolates `-Mode ""` as nothing at
    all, but a hand-typed `-Mode` or a launcher tweak injects a leading
    positional and argparse then dies with "unrecognized arguments" on every
    shard at once.  A flags-only instrument therefore drops one leading bare
    token defensively -- cheap insurance against a whole-sweep loss.
    """
    import runpy
    target = repo_path(*rel)
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        del sys.argv[1]
    sys.argv[0] = target
    runpy.run_path(target, run_name="__main__")


def text_asset(name, default=""):
    """Read a config-shipped text asset (gate text, notes) by BASENAME.

    Config assets land flat at the deployment root on the farm and live in
    `template/configs/` in a checkout, so both are tried.  A missing asset
    falls back to `default` rather than failing: the gate text is
    operator-facing, and losing it must never take a shard down.
    """
    for p in (os.path.join(HERE, name), os.path.join(HERE, "configs", name)):
        if os.path.isfile(p):
            with open(p) as fh:
                return fh.read()
    return default


def add_pylib():
    """Put the tracked instrument package on `sys.path` and return its path.

    The farm payload ships `pylib/` FLAT (the promoted instruments import each
    other with flat names -- `import lib62` -- which is also how they run as
    `python3 pylib/<tool>.py`), so this adds the pylib DIRECTORY, not the repo
    root.  That is the same resolution `pylib/__init__.py` sets up locally.
    """
    return add_repo_path("pylib")
