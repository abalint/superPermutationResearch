"""Controls whose script or corpus lives under gitignored `out/`.

REFACTOR-BRIEF §1 measured it: 22 of this repo's 31 hand-run controls
live in `out/`, which git does not carry.  They are still the strongest
checks the repo has, so they are wrapped here — every one behind
`needs(...)`, which SKIPS with a reason naming the missing path.  On a
clean checkout this whole file skips; on a working machine it runs the
real s63 controls against their pinned numbers.

The frozen `out/sNN` scripts are driven exactly as the pin capture ran
them.  Nothing here writes: `scope_check` and `doorlaw_check` were read
line by line and only ever `open(...)` for reading.  The one control that
DOES write durable state (`singleton_pass.py`) lives in the slow tier,
behind a backup/restore fixture.
"""
from conftest import needs, parse_dict, parse_int, run

# `out/s57/proposer/controls.pkl` is the 177-word chain corpus both
# s63 chain controls read; `out/s56/p1a` holds `p1a_assume`.
CHAIN_INPUTS = ("out/s62/jtax/lib62.py", "out/s57/proposer/controls.pkl",
                "out/s56/p1a")


@needs("out/s63/chains/scope_check.py", *CHAIN_INPUTS)
def test_scope_check_177_words_no_prediction_failures():
    """pins_before/py_scope_check.txt — words=177 impure=0 failures=0.

    The s63 scoping control: every one of the 177 chain words satisfies
    the predicted ledger (S=720+R, D=K-1, splits=R, v=K+R, j=0,
    xp=f4+2f5+3f6, length=5764+K+R+xp).  This is the frame in which
    `j == 0` identically, the s63 general negative.
    """
    out = run("out/s63/chains/scope_check.py", timeout=180).stdout
    assert "words=177 impure=0 prediction_failures=0" in out
    assert out.count(" OK") >= 177


@needs("out/s63/chains/doorlaw_check.py", *CHAIN_INPUTS)
def test_doorlaw_check_zero_violations():
    """pins_before/py_doorlaw_check.txt — 3,122 doors / 145,979 inter-w2
    edges, 0 violations. The door law is a theorem in this frame."""
    out = run("out/s63/chains/doorlaw_check.py", timeout=180).stdout
    assert ("words=177 impure=0 doors=3122 inter_w2=145979 "
            "door_violations=0 w2_violations=0") in out


@needs("out/s63/mcover/brute_tight.py", "out/s62/jtax/lib62.py")
def test_brute_tight_n4_census_equals_mcover_search():
    """s63 control tier (b): independent brute force vs the search engine.

    `brute_tight.py 4 38` enumerates EVERY complete identity-started walk
    of length <= 38 by exhaustion (41,591,451 nodes, ~19 s) and censuses
    the supply-tight families.  `mcover_search.py` reaches the same
    census through loop-cover structure.  Equality of the two is the
    strongest control the multi-cover engine has, and it is the reason
    the s63 `cover_search` superset bug was catchable at all.
    """
    brute = run("out/s63/mcover/brute_tight.py", "4", "38", timeout=300).stdout
    assert parse_int(brute, r"nodes=(\d+)") == 41591451
    assert parse_dict(brute, "SUPPLY-TIGHT families") == {(2, 0): 66, (3, 3): 85}

    # the (v=3, splits=3) family is complete at cap 38, so its census must
    # match the engine's §6 pin exactly
    line = next(ln for ln in brute.splitlines() if "family v=3 splits=3" in ln)
    import ast
    brute_census = ast.literal_eval(line[line.index("{"):])

    engine = run("pylib/mcover_search.py", "4", "38", "--v", "3",
                 "--splits", "3", "--jmin", "0").stdout
    engine_census = parse_dict(engine, "census (j,length)->#walks:")

    assert brute_census == engine_census == {
        (2, 36): 12, (2, 37): 14, (3, 37): 14, (3, 38): 5, (4, 38): 40}
