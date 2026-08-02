"""The slow tier — `python3 -m pytest tests_py/ -m slow`.

Deselected by default (pytest.ini `addopts`).  Two kinds of thing live
here: controls that cost tens of seconds to minutes, and the one control
that REWRITES durable s63 state.

STATE SAFETY (the hard rule of this stage)
------------------------------------------
`out/sNN` is frozen history: nothing under it may be modified.
`singleton_pass.py farm0` rewrites exactly one durable artifact,
`out/s63/chains/singleton_farm0.json`, and the pin MANIFEST documents the
backup/restore procedure the pin-capture agent performed by hand.  That
procedure is encoded in the `restores_s63_singleton_json` fixture below:
back up, run, restore the ORIGINAL bytes, and assert the sha1 the
MANIFEST recorded (`a365985d…`).  The restore runs even if the test
fails, and the sha1 assertion is what proves it worked.
"""
import hashlib
import os
import shutil

import pytest

from conftest import needs, run

SINGLETON_JSON = "out/s63/chains/singleton_farm0.json"
# The pre-run hash the pin MANIFEST recorded and restored to.
SINGLETON_SHA1 = "a365985d2542a542f2d83917ee66d5faa53d18ad"


def _sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def restores_s63_singleton_json(tmp_path):
    """Back up the durable artifact, yield, restore it byte-for-byte.

    Also sweeps the per-worker scratch files the instrument writes
    (`_si_farm0_*` / `_so_farm0_*`) in case a crash leaves them behind —
    the pin MANIFEST notes the clean run deletes its own.
    """
    from conftest import repo_path
    target = repo_path(SINGLETON_JSON)
    backup = None
    if os.path.exists(target):
        backup = str(tmp_path / "singleton_farm0.json.bak")
        shutil.copy2(target, backup)
        before = _sha1(target)
    try:
        yield
    finally:
        chains = repo_path("out/s63/chains")
        if os.path.isdir(chains):
            for f in os.listdir(chains):
                if f.startswith(("_si_farm0_", "_so_farm0_")):
                    os.remove(os.path.join(chains, f))
        if backup is not None:
            shutil.copy2(backup, target)
            assert _sha1(target) == before, "restore of the s63 artifact failed"


@pytest.mark.slow
@needs(SINGLETON_JSON, "out/s63/chains/singleton_pass.py",
       "analysis/counting/s58/paircuts.py", "analysis/trackc/dlx7g")
def test_singleton_pass_farm0_reaches_the_pinned_fixpoint(
        restores_s63_singleton_json):
    """pins_before/py_singleton_pass_farm0.txt — 54 deleted, fixpoint at
    pass 2, 0 violations / 0 reconfirm failures / 0 SAT.

    The s63 fixed-column singleton layer on chain #0: 2,350 rows -> 2,296.
    A SAT here would be a 5905 world record, so `SAT=0` is asserted
    explicitly rather than left implicit in the exit code.
    """
    from conftest import repo_path
    before_sha = _sha1(repo_path(SINGLETON_JSON))
    assert before_sha == SINGLETON_SHA1, (
        "the s63 artifact was already modified before this test ran")

    out = run("out/s63/chains/singleton_pass.py", "farm0", "--workers", "7",
              timeout=1800).stdout

    assert ("spec=farm0 rows=2350 cols=570 loops=525 K=27 R=114 V=15") in out
    assert ("pass 1: pool=2350 UNSAT(deletable)=54 SAT=0 UNKNOWN=2296 "
            "errors=0 reconfirm_fail=0 violations=0 "
            "(cumulative deleted 54)") in out
    assert ("pass 2: pool=2296 UNSAT(deletable)=0 SAT=0 UNKNOWN=2296 "
            "errors=0 reconfirm_fail=0 violations=0 "
            "(cumulative deleted 54)") in out
    assert "FIXPOINT[farm0]: 54 rows deleted, 2350 -> 2296 (-2.30%)" in out


@pytest.mark.slow
def test_rung_869_two_engine_parity_at_n6():
    """REFACTOR-BRIEF §6 "heavier optional gate": the 36,304,934-node pair.

    This is the repo's rung-869 proof (`j >= 1 => length >= 869` at n=6),
    and the strongest control either engine has: two independently
    written searchers walk the SAME supply-tight v=24 perfect-ride family
    and must agree on the exact node count, on the 1,678 relabel-WLOG
    covers, and on the verdict NO WALK.

    ~21 s + ~27 s, clean-checkout safe (both engines are in `pylib/`).
    """
    from conftest import parse_int
    cover = run("pylib/cover_search.py", "6", "868", "--jmin", "1",
                timeout=1800).stdout
    mcover = run("pylib/mcover_search.py", "6", "868", "--v", "24",
                 "--splits", "0", "--jmin", "1", "--prune", "legacy",
                 "--no-mids", timeout=1800).stdout

    assert parse_int(cover, r"nodes=(\d+)") == 36304934
    assert parse_int(mcover, r"walk nodes=(\d+)") == 36304934
    assert "exact covers 10068, containing lam(id) 1678" in cover
    assert "total=1678 seen=1678 processed=1678" in mcover
    assert "NO walk in the perfect-ride family with j>=1" in cover
    assert "NO walk in the supply-tight multi-cover family" in mcover


@pytest.mark.slow
@needs(SINGLETON_JSON)
def test_the_s63_artifact_is_byte_identical_after_the_slow_tier():
    """Ordered after the singleton test within this module: whatever the
    fixture did, the frozen bytes are back.  A standalone assert so a
    fixture bug cannot hide behind a passing control."""
    from conftest import repo_path
    assert _sha1(repo_path(SINGLETON_JSON)) == SINGLETON_SHA1
