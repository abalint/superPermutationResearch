"""Tracked control/oracle scripts, wrapped through their real CLIs.

These are the repo's own hand-run controls — the ones CLAUDE.md's
Commands block documents with "exit 0 = verified" / "oracle PASS" —
turned into asserts.  No new oracle is invented here; the expected values
are what the shipped code prints today, which is what makes them
regression pins.

Every SCRIPT here is tracked, but four of them read a CORPUS that is not:
`data/upstream872/` (22,062 class files, rebuilt from the community
corpus) and `../extraDocs/known5906_corpus` (a sibling checkout).  Those
four carry `needs(...)` guards; the rest, including the whole M3 gate,
run on a fresh clone.
"""
from conftest import needs, parse_int, run

# The n=6 archive `data/upstream872/` (22,062 class files) is gitignored —
# it is rebuilt from the community corpus, not carried in git. Three of the
# oracles below read it directly, so they are guarded; the M3 gate is not,
# because its index is committed precisely so a fresh clone can run it.
NEEDS_N6_ARCHIVE = needs("data/upstream872")


# ------------------------------------------------------- the M3 gate ----
# `analysis/counting/m3_check.py` is the single novelty gate every
# candidate <= the record must pass.  Its index is committed, so this is
# clean-checkout safe, and it exercises `pylib.canonical.canon_relabel_rev`
# through the DANGER site named in REFACTOR-BRIEF §1.

def test_m3_check_872_specimen_is_a_rediscovery():
    """pins_before/py_m3_check_872.txt — known, NOT novel; exit 0."""
    out = run("analysis/counting/m3_check.py",
              "data/upstream872_specimens/872.up-6dbae421a839.txt").stdout
    assert parse_int(out, r"known-872 index: ([\d,]+) classes") == 22062
    assert "valid 872" in out
    assert "EQUIVALENT to known class 872.up-6dbae421a839.txt" in out
    assert "a rediscovery, not M3" in out
    assert "NOVEL" not in out


def test_m3_check_every_tracked_n6_specimen_maps_to_its_own_class():
    """All 8 committed n=6 specimens are rediscoveries of themselves.

    Guards the index <-> canonicalizer agreement in bulk: if
    `canon_relabel_rev` ever changed, every one of these would miss.
    """
    out = run("analysis/counting/m3_check.py",
              *[f"data/upstream872_specimens/{f}" for f in FILES_N6]).stdout
    for f in FILES_N6:
        assert f"{f}: valid 872, EQUIVALENT to known class {f}" in out
    assert out.count("a rediscovery, not M3") == len(FILES_N6)


FILES_N6 = [
    "872.up-00005a46cfe3.txt", "872.up-006185ae478a.txt",
    "872.up-009da25acce5.txt", "872.up-00b21d05e0f4.txt",
    "872.up-022441b7b1ff.txt", "872.up-13f91236b67c.txt",
    "872.up-249988a17b8a.txt", "872.up-6dbae421a839.txt",
]


def test_m3_check_n7_corpus_is_fully_indexed():
    """All 84 committed 5906 classes are known to the n=7 gate."""
    out = run("analysis/counting/m3_check.py", "-n", "7",
              *[f"data/upstream5906/{f}" for f in _n7_files()]).stdout
    assert out.count("a rediscovery, not M3") == 84
    assert "NOVEL" not in out


def _n7_files():
    import os

    from conftest import repo_path
    return sorted(f for f in os.listdir(repo_path("data/upstream5906"))
                  if f.endswith(".txt"))


# ------------------------------------------------- structural controls --

def test_verify_identity_t0_on_committed_specimens():
    """T0 (s22): the waste identity holds on every tracked specimen.

    `analysis/trackb/verify_identity.py` — CLAUDE.md: "exit 0 = general
    identity holds".  The per-walk columns print `A-A` / `B-B` pairs
    (predicted-actual); a mismatch is a non-zero exit.
    """
    out = run("analysis/trackb/verify_identity.py",
              *[f"data/upstream872_specimens/{f}" for f in FILES_N6]).stdout
    assert out.count(".txt") >= len(FILES_N6)
    assert "147-147" in out          # the S-term column, all 8 walks


@NEEDS_N6_ARCHIVE
def test_m4a_pair_anatomy_verifies():
    """s40 M-4a: the 13 cover-sharing pairs, three rigid rewrite rules.

    CLAUDE.md: "exit 0 = verified".
    """
    run("analysis/counting/m4a_pair_anatomy.py")


@NEEDS_N6_ARCHIVE
def test_i4a_apply_oracle_rederives_all_13_pairs():
    """s41 I4-A oracle: re-derive all 13 anatomized pairs byte-identically."""
    out = run("analysis/counting/i4a_apply.py", "oracle").stdout
    assert out.strip().endswith("oracle: PASS")
    assert out.count(" OK") == 13


@NEEDS_N6_ARCHIVE
def test_loopswap_apply_oracle_passes():
    """s44 I5 oracle: every anatomized n=6 tail-conjugate pair re-derived."""
    out = run("analysis/counting/loopswap_apply.py", "oracle").stdout
    assert "oracle PASS: 108" in out


@needs("../extraDocs/known5906_corpus")
def test_upstream5906_twocycles_law():
    """s34: length = 5764 + #2loops on all 87 known n=7 words.

    CLAUDE.md: "re-verifies, exit 0".  84 x 142 loops, 3 x 143.
    """
    out = run("analysis/counting/upstream5906_twocycles.py").stdout
    assert "upstream5906: 84 walks, ALL at 142 loops, length = 5764 + loops holds" in out
    assert "upstream5907: 3 walks, ALL at 143 loops, length = 5764 + loops holds" in out
    assert out.strip().endswith("PASS")


def test_upstream5906_structure_census():
    """s33 L0 census over the committed n=7 corpus: 6 pure-w3 allocations,
    Kristan's (843,18) alone in its own row (count=1, S=843)."""
    out = run("analysis/counting/upstream5906_structure.py").stdout
    assert "count=  1  len=5906  S=843  inter={3: 18}  intra={}" in out
