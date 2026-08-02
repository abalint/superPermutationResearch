"""§6 Python pins: the jtax search engines, run through `pylib/`.

These four commands are the spine of the refactor's acceptance bar
(`docs/REFACTOR-BRIEF.md` §6).  Every number below is copied from
`out/s64/refactor/pins_before/` — the BEFORE capture, taken against the
frozen `out/s62/jtax/` originals.  P1 promoted those files into `pylib/`
byte-identically apart from a provenance header, so the pins must hold
verbatim against the package copies; that equality is the whole point.

Node counts are the sharpest assertion available: they are exact
deterministic search-tree sizes, so any accidental change to move
generation, ordering or pruning moves them.
"""
from conftest import needs, parse_dict, parse_int, parse_minima, run

# `analysis/counting/s58/paircuts.py` is untracked, but every module these
# four commands touch (`pylib/{cover_search,mcover_search,lib62}.py`) is
# tracked, so this whole file runs on a clean checkout.


def test_cover_search_n4_tmax40_j0():
    """pins_before/py_cover_search_n4_40.txt — 320 nodes, minima {0:33,...}."""
    out = run("pylib/cover_search.py", "4", "40", "--jmin", "0").stdout
    assert parse_int(out, r"nodes=(\d+)") == 320
    assert parse_minima(out) == {0: 33, 1: 34, 2: 35, 3: 36, 4: 37}
    # the family header is part of the contract too
    assert "6 cycles, 8 loops" in out
    assert "exact covers 4" in out


def test_mcover_n4_tmax40_v2_legacy_nomids():
    """pins_before/py_mcover_n4_40_v2.txt — 320 walk nodes.

    This is the node-for-node control against `cover_search` above: the
    two engines must agree exactly on the v=2 perfect-ride family.
    """
    out = run("pylib/mcover_search.py", "4", "40", "--v", "2", "--splits", "0",
              "--jmin", "0", "--prune", "legacy", "--no-mids").stdout
    assert parse_int(out, r"walk nodes=(\d+)") == 320
    assert parse_dict(out, "phi-cycle-count histogram K:") == {2: 1}
    assert parse_minima(out) == {0: 33, 1: 34, 2: 35, 3: 36, 4: 37}
    assert parse_dict(out, "census (j,length)->#walks:") == {
        (0, 33): 1, (0, 34): 2, (1, 34): 2, (1, 36): 4, (2, 35): 2,
        (2, 36): 10, (2, 37): 10, (2, 38): 2, (3, 36): 2, (3, 37): 12,
        (3, 38): 10, (3, 39): 16, (3, 40): 2, (4, 37): 3, (4, 38): 6,
        (4, 39): 16, (4, 40): 14}


def test_cover_and_mcover_agree_node_for_node():
    """The s63 two-engine control, as an explicit equality.

    `cover_search` was later found to search a strict SUPERSET (missing
    door-mid test, JOURNAL s63) — on THIS family the two still agree
    node-for-node, and that agreement is the pin.
    """
    a = run("pylib/cover_search.py", "4", "40", "--jmin", "0").stdout
    b = run("pylib/mcover_search.py", "4", "40", "--v", "2", "--splits", "0",
            "--jmin", "0", "--prune", "legacy", "--no-mids").stdout
    assert parse_int(a, r"nodes=(\d+)") == parse_int(b, r"walk nodes=(\d+)")
    assert parse_minima(a) == parse_minima(b)


def test_mcover_n4_tmax38_v3_splits3_census():
    """pins_before/py_mcover_n4_38_v3_s3.txt — the exact family census."""
    out = run("pylib/mcover_search.py", "4", "38", "--v", "3", "--splits", "3",
              "--jmin", "0").stdout
    assert parse_dict(out, "census (j,length)->#walks:") == {
        (2, 36): 12, (2, 37): 14, (3, 37): 14, (3, 38): 5, (4, 38): 40}
    assert parse_int(out, r"walk nodes=(\d+)") == 2127
    assert parse_int(out, r"enum_nodes=(\d+)") == 43


def test_mcover_n5_tmax155_v6_a5_is_153():
    """pins_before/py_mcover_n5_155_v6.txt — 964,317 nodes, a(5)=153.

    Measured 0.77 s in the BEFORE capture (the brief's "~20 s" estimate
    was pessimistic), so this stays in the default tier.  It is the
    engine's positive control: the minimum over the whole j=0
    perfect-ride family at n=5 is the proven optimum 153.
    """
    out = run("pylib/mcover_search.py", "5", "155", "--v", "6", "--splits", "0",
              "--jmin", "0", "--prune", "legacy", "--no-mids", timeout=180).stdout
    assert parse_int(out, r"walk nodes=(\d+)") == 964317
    assert parse_dict(out, "census (j,length)->#walks:") == {
        (0, 153): 2, (0, 154): 16, (0, 155): 195, (1, 154): 18, (1, 155): 171,
        (2, 154): 6, (2, 155): 73, (3, 155): 4}
    assert parse_minima(out) == {0: 153, 1: 154, 2: 154, 3: 155}
    assert parse_minima(out)[0] == 153          # a(5), the hard invariant


@needs("out/s63/mcover/mc_n5_v7_s4_j0_153.txt",
       "out/s63/mcover/mc_n5_v7_s4_j1_154.txt")
def test_verify_master_n5_witnesses_all_pass():
    """pins_before/py_verify_master_n5.txt — MASTER tight on both witnesses.

    The two committed-by-value witnesses live under gitignored `out/`, so
    this is the one §6 Python pin that cannot run from a clean checkout.
    """
    out = run("pylib/verify_master.py", "5",
              "out/s63/mcover/mc_n5_v7_s4_j0_153.txt",
              "out/s63/mcover/mc_n5_v7_s4_j1_154.txt").stdout
    assert "ALL PASS" in out
    assert parse_dict(out, "j histogram:") == {0: 1, 1: 1}
    assert parse_dict(out, "MASTER slack histogram") == {0: 2}
    assert "MASTER exactly tight on 2/2" in out
