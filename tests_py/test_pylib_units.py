"""Unit-level pins on the s64 P1 consolidation.

P1 merged six copies of `first_visit_path`, six of `renumber`, three of
`weight` and seventeen definitions of `canon` (in TWO incompatible
meanings) into `pylib/walkio.py` + `pylib/canonical.py`.  A merge like
that fails silently: the wrong body still runs, it just answers wrong.
The expected values below were derived by RUNNING the merged code
against TRACKED corpus data — regression pins on the merge, not new
mathematics.

The sharpest of them is the canonicalizer/index agreement: every
committed `*_canon_index.tsv` is keyed by `sha256(canon_relabel_rev(s))`,
so if that body ever drifts, the M3 novelty gate silently starts calling
known classes novel.
"""
import hashlib
import importlib
import os

import pytest

from conftest import repo_path

SPECIMEN = "data/upstream872_specimens/872.up-6dbae421a839.txt"
SPECIMENS = [
    "872.up-00005a46cfe3.txt", "872.up-006185ae478a.txt",
    "872.up-009da25acce5.txt", "872.up-00b21d05e0f4.txt",
    "872.up-022441b7b1ff.txt", "872.up-13f91236b67c.txt",
    "872.up-249988a17b8a.txt", "872.up-6dbae421a839.txt",
]

# Self-contained: import with no path help beyond `import pylib` itself.
PYLIB_MODULES = [
    "pylib.walkio", "pylib.canonical", "pylib.lib62", "pylib.cover_search",
    "pylib.mcover_search", "pylib.verify_master", "pylib.dlxrun",
]

# The rest still reach a module P1 did NOT promote, so on a clean checkout
# they are NOT importable. Measured by this suite, worth recording:
#   `certificate` lives OUTSIDE the repo in the sibling
#   `../extraDocs/superpermutation-examples/scripts` checkout (a hard
#   external dependency of the whole n=7 stack), and `prefixlib` is still
#   in gitignored `out/s59/prefix`. Both are reached only through
#   `pylib.add_legacy_paths()`; promoting them is future work.
LEGACY_DEP_MODULES = {
    "pylib.chain7": "certificate",
    "pylib.symlib": "certificate",
    "pylib.anatlib": "certificate",
    "pylib.paircuts": "certificate",
    "pylib.cutlib": "prefixlib",
}


@pytest.fixture(scope="module")
def specimen():
    with open(repo_path(SPECIMEN)) as fh:
        return fh.read().strip()


# ------------------------------------------------- the package imports --

@pytest.mark.parametrize("mod", PYLIB_MODULES)
def test_pylib_module_imports(mod):
    """Every promoted instrument imports with no path help at all.

    That is the point of the package: before P1 these needed one of eight
    incompatible `sys.path` spellings, several cwd-dependent.
    """
    importlib.import_module(mod)


@pytest.mark.parametrize("mod,dep", sorted(LEGACY_DEP_MODULES.items()))
def test_pylib_module_imports_via_legacy_paths(mod, dep):
    """The promoted instruments that still need an unpromoted module.

    `add_legacy_paths()` is the sanctioned way to reach them; if the home
    is absent (clean checkout, or no sibling extraDocs clone) this skips
    with the dependency named, which is exactly the state P1 documented.
    """
    import pylib
    homes = {
        "certificate": pylib.EXTRA_DOCS_SCRIPTS,
        "prefixlib": os.path.join(pylib.REPO_ROOT, "out", "s59", "prefix"),
    }
    if not os.path.isdir(homes[dep]):
        pytest.skip(f"unpromoted dependency {dep!r} absent: {homes[dep]}")
    pylib.add_legacy_paths()
    importlib.import_module(mod)


def test_pylib_exports_no_bare_canon():
    """The name-collision guard, as an assert.

    `canon` meant two incompatible things across 17 definitions; pylib
    refuses to export the ambiguous spelling so no call site can pick the
    wrong one by autocompletion.
    """
    import pylib.canonical as C
    assert not hasattr(C, "canon")
    assert hasattr(C, "canon_rotation")
    assert hasattr(C, "canon_relabel_rev")


# ------------------------------------------------------------- walkio ---

def test_first_visit_path_reads_720_perms_from_a_committed_872(specimen):
    from pylib.walkio import first_visit_path
    path = first_visit_path(specimen, 6)
    assert len(specimen) == 872
    assert len(path) == 720                    # 6! — a complete walk
    assert len(set(path)) == 720               # first-visit => no repeats
    assert path[0] == (1, 2, 3, 4, 5, 6)       # the specimen opens at identity
    assert path[-1] == (6, 1, 4, 3, 2, 5)


def test_first_visit_starts_agrees_with_first_visit_path(specimen):
    from pylib.walkio import first_visit_path, first_visit_starts
    starts = first_visit_starts(specimen, 6)
    path = first_visit_path(specimen, 6)
    assert len(starts) == len(path) == 720
    assert starts == sorted(starts)
    # the two spellings must read the SAME windows (one returns tuples of
    # ints, the other the index of each window)
    assert [tuple(int(c) for c in specimen[i:i + 6]) for i in starts] == path


def test_weight_and_overlap_are_the_same_law_counted_two_ways():
    from pylib.walkio import overlap, weight
    a, b = (1, 2, 3, 4, 5, 6), (2, 3, 4, 5, 6, 1)
    assert weight(a, b, 6) == 1                       # a rotation = weight 1
    assert weight(a, (3, 4, 5, 6, 1, 2), 6) == 2
    assert weight(a, (5, 4, 3, 2, 1, 6), 6) == 6      # no overlap at all
    # the reversal DOES overlap by one (suffix `6` = prefix `6`) — the
    # obvious "reversal is maximally far" intuition is wrong here
    assert weight(a, (6, 5, 4, 3, 2, 1), 6) == 5
    for q in [(2, 3, 4, 5, 6, 1), (3, 4, 5, 6, 1, 2), (6, 5, 4, 3, 2, 1),
              (5, 4, 3, 2, 1, 6)]:
        assert weight(a, q, 6) == 6 - overlap(a, q)


def test_walk_weight_sum_reproduces_the_specimen_length(specimen):
    """The waste identity's backbone: len = n + sum of edge weights."""
    from pylib.walkio import first_visit_path, weight
    path = first_visit_path(specimen, 6)
    total = 6 + sum(weight(path[i], path[i + 1], 6) for i in range(len(path) - 1))
    assert total == 872


def test_renumber_is_first_occurrence_forward():
    from pylib.walkio import renumber
    assert renumber("231123") == "123312"
    assert renumber("123456") == "123456"
    assert renumber(renumber("654321")) == renumber("654321")   # idempotent


def test_rotc_and_lam_are_the_cycle_and_loop_ids():
    from pylib.walkio import lam, rot, rotc
    assert rot((1, 2, 3, 4)) == (2, 3, 4, 1)
    assert rotc((3, 1, 2)) == (1, 2, 3)                 # least rotation
    assert rotc((1, 2, 3)) == rotc((2, 3, 1)) == rotc((3, 1, 2))
    assert lam((1, 2, 3, 4)) == (1, 2, 3, 4)
    # n=4: 6 cycles, 8 loops — the family header cover_search prints
    from itertools import permutations
    perms = list(permutations(range(1, 5)))
    assert len({rotc(p) for p in perms}) == 6
    assert len({lam(p) for p in perms}) == 8


def test_class_files_suffix_trap_is_exact_endswith_txt():
    """HANDOFF-S51's trap, kept as an assert: a `*.txt*` glob would
    inflate data/kristan5906_web/ from 2 files to 5."""
    from pylib.walkio import class_files
    m = class_files(["data/upstream872_specimens"], root=repo_path())
    assert set(m) == set(SPECIMENS)
    assert all(k.endswith(".txt") for k in m)


# ---------------------------------------------------------- canonical ---

def test_canon_relabel_rev_matches_the_committed_index_key(specimen):
    """The M3 coordinate: sha256(canon_relabel_rev(s)) is the index key."""
    from pylib.canonical import canon_relabel_rev
    key = hashlib.sha256(canon_relabel_rev(specimen).encode()).hexdigest()
    assert key == ("08238afb61f00100b59b20b2643655bc39aae5e733c185883aa9c120"
                   "e4e69d79")
    assert _index()[key] == "872.up-6dbae421a839.txt"


def test_every_committed_specimen_hits_its_own_class_in_the_index():
    from pylib.canonical import canon_relabel_rev
    idx = _index()
    assert len(idx) == 22062
    for name in SPECIMENS:
        with open(repo_path("data/upstream872_specimens", name)) as fh:
            s = fh.read().strip()
        key = hashlib.sha256(canon_relabel_rev(s).encode()).hexdigest()
        assert idx[key] == name


def test_canon_relabel_rev_is_invariant_under_relabel_and_reversal(specimen):
    from pylib.canonical import canon_relabel_rev
    table = str.maketrans("123456", "246135")
    assert canon_relabel_rev(specimen.translate(table)) == canon_relabel_rev(specimen)
    assert canon_relabel_rev(specimen[::-1]) == canon_relabel_rev(specimen)


def test_the_two_canon_semantics_are_not_interchangeable():
    """REFACTOR-BRIEF §1's DANGER, pinned: same input, different answers."""
    from pylib.canonical import canon_relabel_rev, canon_rotation
    w = "1732465"
    assert canon_rotation(w) == "1732465"        # already its least rotation
    assert canon_relabel_rev(w) == "1234567"     # first-occurrence relabel
    assert canon_rotation("465173 2".replace(" ", "")) == "1732465"


def test_hash12_is_the_12_hex_prefix_of_the_class_key(specimen):
    from pylib.canonical import h12, hash12
    assert hash12(specimen) == "08238afb61f0"
    assert h12("872.up-6dbae421a839.txt") == "6dbae421a839"
    with pytest.raises(SystemExit):
        h12("no-hash-here")


def test_door_tv_inverse_tv_round_trip():
    from pylib.canonical import inverse_tv, loop_of, tv
    for w in ["123456", "1732465", "162534"]:
        assert inverse_tv(tv(w)) == w
    assert loop_of("1732465") == ("5", "173246")


def _index():
    path = repo_path("analysis/counting/upstream872_canon_index.tsv")
    with open(path) as fh:
        rows = fh.read().strip().splitlines()
    assert rows[0] == "canon_sha256\tclass_file"
    return dict(line.split("\t") for line in rows[1:])


# ------------------------------------- the import-hygiene architecture --

def test_tracked_python_carries_only_the_sanctioned_sys_path_line():
    """P1's structural win, guarded against regrowth.

    275 `sys.path` mutation sites became one sanctioned bootstrap line.
    The only tracked `.py` exceptions are the three farm shims that
    search a two-candidate farm layout the repo-root walk cannot express
    (docs/ARCHITECTURE.md names them).
    """
    import subprocess
    allowed_files = {
        "analysis/farm/i4a_shim.py",
        "analysis/farm/lswap_shim.py",
        "analysis/farm/promote_shim.py",
    }
    out = subprocess.run(
        ["git", "grep", "-n", "sys.path", "--", "analysis/", "ml/"],
        cwd=repo_path(), capture_output=True, text=True).stdout
    offenders = []
    for line in out.splitlines():
        path, _, text = line.split(":", 2)
        if not path.endswith(".py"):
            continue                       # .sh/.ps1 quote old spellings in prose
        if path in allowed_files:
            continue
        if "pylib bootstrap" in text:
            continue                       # the ONE sanctioned line
        offenders.append(line)
    assert offenders == [], (
        "unsanctioned sys.path mutation in tracked Python — use "
        "`import pylib; pylib.add_paths(...)` (docs/ARCHITECTURE.md):\n"
        + "\n".join(offenders))
