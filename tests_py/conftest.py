"""Shared machinery for the s64 P2 control suite.

WHAT THIS SUITE IS (and is not)
-------------------------------
It **converts existing controls**; it writes no new oracles.  Every
number asserted here was pinned by the s64 pin-capture agent at
`out/s64/refactor/pins_before/MANIFEST.md` (the §6 pin list of
`docs/REFACTOR-BRIEF.md`), or was derived by RUNNING the shipped code —
these are regression pins, not novel mathematics.  A test that fails is
a refactor bug; per REFACTOR-BRIEF §0 you fix the stage, never the pin.

Instrument logic is never imported-and-monkeypatched: control scripts are
driven through their real CLI with `subprocess`, exactly as a human runs
them, so wrapping cannot change what is under test.

CLEAN-CHECKOUT RULE
-------------------
`out/` is gitignored, so roughly two thirds of this repo's 31 hand-run
controls need inputs a fresh clone does not have.  Anything whose script
or data is untracked is guarded with `needs(...)`, which skips with a
reason string naming the missing path.  A clean checkout therefore runs
green with skips, never with errors.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "python3"

# Timing tokens are the one thing the instruments print that is NOT
# byte-stable run to run.  This is the normalizer the pin MANIFEST
# prescribes (its §"How to diff after a refactor stage", caveat 2).
_TIME_RE = re.compile(r"[0-9]+\.[0-9]+s")


def normalize_timings(text: str) -> str:
    """Replace every `<float>s` wall-clock token with `TIMEs`."""
    return _TIME_RE.sub("TIMEs", text)


def repo_path(*parts: str) -> str:
    return os.path.join(REPO, *parts)


def needs(*rel_paths: str):
    """`pytest.mark.skipif` for inputs a clean checkout may not have.

    `out/` and several `data/` archives are gitignored; the reason string
    names the first missing path so a skip is never mysterious.
    """
    missing = [p for p in rel_paths if not os.path.exists(repo_path(p))]
    return pytest.mark.skipif(
        bool(missing),
        reason=("not in a clean checkout (gitignored / locally generated): "
                + ", ".join(missing)),
    )


def run(*argv: str, env_extra: dict | None = None, timeout: float = 300,
        expect_exit: int | None = 0) -> subprocess.CompletedProcess:
    """Run a repo script through its real CLI from the repo root.

    `argv[0]` is repo-relative; the interpreter is this pytest's own.
    """
    cmd = [PY, repo_path(argv[0]), *argv[1:]]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)          # the pylib bootstrap must stand alone
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, cwd=REPO, env=env, timeout=timeout,
                          capture_output=True, text=True)
    if expect_exit is not None and proc.returncode != expect_exit:
        raise AssertionError(
            f"{' '.join(argv)}\nexit {proc.returncode} (want {expect_exit})\n"
            f"--- stdout ---\n{proc.stdout[-4000:]}\n"
            f"--- stderr ---\n{proc.stderr[-4000:]}")
    return proc


# ------------------------------------------------------ output parsers --
# The instruments' stdout IS their contract; these read it the way the pin
# MANIFEST reads it, and nothing else.

def parse_dict(text: str, label: str) -> dict:
    """The `{...}` literal following `label` on its line."""
    for line in text.splitlines():
        if label in line:
            body = line[line.index("{"):]
            import ast
            return ast.literal_eval(body)
    raise AssertionError(f"no line containing {label!r} in:\n{text}")


def parse_int(text: str, pattern: str) -> int:
    m = re.search(pattern, text)
    if not m:
        raise AssertionError(f"pattern {pattern!r} not found in:\n{text}")
    return int(m.group(1).replace(",", ""))


def parse_minima(text: str) -> dict:
    """The `   j=K: L` block both search engines print at the end."""
    return {int(m.group(1)): int(m.group(2))
            for m in re.finditer(r"^\s+j=(\d+):\s*(\d+)\s*$", text, re.M)}
