"""The determinism guard — the s63 cutconvert lesson, generalized.

s63 lost a day to a DFS whose move order came from iterating a
`set` of strings: the search was correct but not reproducible, and the
node counts a REPORT cited could not be re-derived.  Python randomizes
`str.__hash__` per process (`PYTHONHASHSEED`), so set/dict iteration
order over strings differs run to run — a DFS that leaks that order into
its branching is nondeterministic and every node count it prints is
noise.

REFACTOR-BRIEF §0 makes byte-identical replay the acceptance bar for the
whole refactor, so this guard is load-bearing for every other pin in the
suite: run the engine under two different hash seeds, demand identical
stdout.  Only wall-clock timing tokens are normalized away (the pin
MANIFEST's own caveat); censuses, node counts and minima are compared
byte-for-byte.
"""
import pytest

from conftest import normalize_timings, run

# (id, argv) — small, fully-exhaustive n=4 cases, both DFS engines.
CASES = [
    ("cover_search_n4",
     ("pylib/cover_search.py", "4", "40", "--jmin", "0")),
    ("mcover_search_n4_v2",
     ("pylib/mcover_search.py", "4", "40", "--v", "2", "--splits", "0",
      "--jmin", "0", "--prune", "legacy", "--no-mids")),
    ("mcover_search_n4_v3_splits3",
     ("pylib/mcover_search.py", "4", "38", "--v", "3", "--splits", "3",
      "--jmin", "0")),
]


@pytest.mark.parametrize("argv", [c[1] for c in CASES], ids=[c[0] for c in CASES])
def test_stdout_identical_across_pythonhashseeds(argv):
    a = run(*argv, env_extra={"PYTHONHASHSEED": "0"}).stdout
    b = run(*argv, env_extra={"PYTHONHASHSEED": "1"}).stdout
    assert normalize_timings(a) == normalize_timings(b), (
        "NONDETERMINISM: stdout differs between PYTHONHASHSEED=0 and =1.\n"
        "Some container iteration order is leaking into the search "
        "(the s63 cutconvert bug). Sort the iteration, do not re-pin.")


@pytest.mark.parametrize("argv", [c[1] for c in CASES], ids=[c[0] for c in CASES])
def test_stdout_identical_on_repeat_same_seed(argv):
    """Same seed twice — separates hash-order effects from any other
    source of run-to-run drift (clock, gc, dict insertion timing)."""
    a = run(*argv, env_extra={"PYTHONHASHSEED": "0"}).stdout
    b = run(*argv, env_extra={"PYTHONHASHSEED": "0"}).stdout
    assert normalize_timings(a) == normalize_timings(b)
