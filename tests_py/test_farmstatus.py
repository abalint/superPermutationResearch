"""Pins for the farm STATUS heartbeat contract (s64 P5).

`pylib/farmstatus.py` encodes ONCE what used to be prose restated per shim
docstring — and what both documented s52b bugs violated.  A contract that
lives only in prose drifts; these tests are the pin that stops it.

The alarm-regex cases below are a LINE-FOR-LINE mirror of
`analysis/farm/untargeted_alarmtest.ps1` (13 cases, "ALARM REGEX OK: 0
failures"), which runs the same regex under PowerShell on the farm.  Two
engines, one string: if PowerShell and Python ever disagree about it, one of
these two suites goes red.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

from conftest import PY, REPO, repo_path

sys.path.insert(0, repo_path("pylib"))
import farmstatus as FS  # noqa: E402

ALARMTEST_PS1 = repo_path("analysis", "farm", "untargeted_alarmtest.ps1")

# --- the 13 cases of untargeted_alarmtest.ps1, verbatim ---------------------
BENIGN = [
    "novel-candidate classes: 0",
    "distinct (src_class,tgt_class) pairs: 0",
    "edges written: 0 -> edges.tsv",
    "ESCAPES 0",
    "product-NOVEL: 0",
    "roundtrip-ok: 44124",
]
REAL = [
    "novel-candidate classes: 3",
    "*** NOVEL-CANDIDATE len=872 demo-872-abc.txt <- 872.up-x[F] PRO4/-1/nodoor",
    "*** DEGENERATE-DROP NOVEL len=871 drop-871-def.txt",
    "ESCAPES 2",
    "Traceback (most recent call last):",
    "MemoryError",
    "product-NOVEL: 1",
]


@pytest.mark.parametrize("line", BENIGN)
def test_benign_summary_never_alarms(line):
    """The s52b rule: a ZERO-count summary line must never alarm.

    It has fired twice for real — `ESCAPES 0` (s52) and
    `novel-candidate classes: 0` (s52b, which bannered all 24 HEALTHY
    shards into ALARM.txt).  A healthy run that cries wolf teaches the
    operator to ignore the one banner that matters.
    """
    assert not FS.is_alarming(line), f"benign line would alarm: {line!r}"


@pytest.mark.parametrize("line", REAL)
def test_real_event_always_alarms(line):
    assert FS.is_alarming(line), f"real event would be MISSED: {line!r}"


def test_alarm_regex_matches_the_supervisor_as_built():
    """The regex is not ours to choose — it is the supervisor's, verbatim.

    Pinned against BOTH PowerShell sources so a one-sided edit fails here:
    `untargeted_super.ps1` (the scanner) and `untargeted_alarmtest.ps1`
    (its regression test).
    """
    body = FS.ALARM_REGEX[len("(?i)"):]
    for rel in (("analysis", "farm", "untargeted_super.ps1"),
                ("analysis", "farm", "untargeted_alarmtest.ps1")):
        with open(repo_path(*rel)) as fh:
            text = fh.read()
        assert body in text, f"alarm regex drifted from {os.path.join(*rel)}"


@pytest.mark.skipif(sys.platform == "win32", reason="posix path check only")
def test_alarmtest_ps1_still_present_and_wired():
    """The PowerShell-side regression test must keep existing and asserting.

    We cannot run PowerShell here; the farm run is the other half (see the
    session report).  What IS checkable locally: the script exists, still
    carries all 13 cases, and still ends on the exact verdict string the
    operator greps for.
    """
    with open(ALARMTEST_PS1) as fh:
        text = fh.read()
    for line in BENIGN + REAL:
        assert line.replace("'", "''") in text or line in text, \
            f"case dropped from untargeted_alarmtest.ps1: {line!r}"
    assert "ALARM REGEX OK: 0 failures" in text


# --- the heartbeat contract ------------------------------------------------

def _status_bytes(d):
    with open(os.path.join(d, "STATUS"), "rb") as fh:
        return fh.read()


def _progress_rows(raw):
    """Parse STATUS exactly as untargeted_super.ps1:240 does."""
    return [(int(a), int(b)) for a, b in
            re.findall(rb"\t(\d+)/(\d+)\t", raw)]


def test_rows_and_declared_total_share_one_unit(tmp_path):
    """The s52b unit bug, pinned.

    `promote_shim` emitted `replays/total_replays` while ticking every 50
    replays, so a FINISHED run read `50/2462 (2%)`.  The supervisor COUNTS
    ROWS and reads `<n>` from the row; `work()` therefore derives both from
    the same tick and they cannot diverge.
    """
    st = FS.FarmStatus(str(tmp_path), total_units=1000, tick=50, label="cover")
    for _ in range(1000):
        st.work()
    st.finish(rc=0)
    st.close()
    rows = _progress_rows(_status_bytes(str(tmp_path)))
    assert len(rows) == 20                      # 1000 units / tick 50
    assert rows[-1] == (20, 20)                 # reads N/N, not 1000/20
    assert all(b == 20 for _, b in rows)


def test_final_fill_reaches_n_over_n(tmp_path):
    """A shard that finishes must not park at 99%."""
    st = FS.FarmStatus(str(tmp_path), total_units=205, tick=100)
    for _ in range(205):
        st.work()
    st.finish(rc=0)
    st.close()
    rows = _progress_rows(_status_bytes(str(tmp_path)))
    assert rows[-1] == (3, 3)                   # ceil(205/100) = 3


def test_batched_work_cannot_lose_rows(tmp_path):
    """rows == units // tick, whatever batch size the caller uses."""
    st = FS.FarmStatus(str(tmp_path), total_units=1000, tick=10)
    st.work(250)
    st.work(250)
    st.close()
    assert len(_progress_rows(_status_bytes(str(tmp_path)))) == 50


def test_non_progress_rows_are_not_counted(tmp_path):
    """DONE / ESCAPE / notes must carry no `\\t<i>/<n>\\t` field.

    Otherwise the supervisor counts them as progress AND redefines the
    declared total from whatever digits they contain.
    """
    st = FS.FarmStatus(str(tmp_path), total_units=10, tick=10)
    st.work(10)
    st.escape("j=1 len=872 file=x.txt")
    st.row("CAPPED", "rc=3 -- PARTIAL, not a negative")
    st.done("shard 0/24: 10 covers, 1 finds, 5s, rc=0")
    st.close()
    raw = _status_bytes(str(tmp_path))
    assert _progress_rows(raw) == [(1, 1)]
    assert b"\tESCAPE\t" in raw and b"\tDONE\t" in raw


def test_caller_text_cannot_forge_a_progress_field(tmp_path):
    """A note containing tabs must not manufacture a field boundary."""
    st = FS.FarmStatus(str(tmp_path), total_units=1, tick=1)
    st.row("NOTE", "sneaky\t7/9\ttail")
    st.close()
    assert _progress_rows(_status_bytes(str(tmp_path))) == []


def test_dry_run_shard_reads_complete(tmp_path):
    """A dry smoke exists to prove the launch path; 24 dry shards must read
    24/24 DONE, not 24 failures."""
    st = FS.FarmStatus(str(tmp_path), shard=0, shards=24, total_units=8586,
                       tick=200)
    st.finish_dry("shard 0/24, 8586 covers, 43 ticks")
    st.close()
    raw = _status_bytes(str(tmp_path))
    assert _progress_rows(raw) == [(0, 1)]
    assert b"\tDONE\t" in raw


def test_status_and_products_are_lf_only(tmp_path):
    """The s63 CRLF trap, generalized.

    `--emit-covers` used plain `open(p,"w")`; Windows wrote CRLF while the
    sha256 accumulated over pre-translation bytes, so every shard would have
    exited 4.  Everything farmstatus writes goes through `newline=""`.
    """
    st = FS.FarmStatus(str(tmp_path), total_units=2, tick=1)
    st.work(2)
    st.gate_md("gate line\nsecond line")
    st.product("prod.txt", "abc")
    st.finish(rc=0)
    st.close()
    for name in ("STATUS", "GATE.md", "prod.txt", "stats_s00.tsv"):
        with open(os.path.join(str(tmp_path), name), "rb") as fh:
            assert b"\r\n" not in fh.read(), f"CRLF in {name}"


def test_gate_notes_may_not_be_txt(tmp_path):
    """`untargeted_status.ps1:92` counts EVERY `*.txt` under the run's out
    tree as an ESCAPE CANDIDATE — the escape-scan trap, 4 recurrences."""
    st = FS.FarmStatus(str(tmp_path), total_units=1, tick=1)
    with pytest.raises(ValueError):
        st.gate_md("...", name="GATE.txt")
    st.close()


def test_stats_name_is_counted_by_the_supervisor(tmp_path):
    """The supervisor row-counts `(?i)stat` TSVs as products and `(?i)edge`
    as rediscoveries; the canonical stats file must land in the first."""
    st = FS.FarmStatus(str(tmp_path), shard=7, shards=24, total_units=1,
                       tick=1)
    p = st.stats(FS.STATS_HEADER, [7, 24, 1, 1, 0, "1.0", 0])
    st.close()
    name = os.path.basename(p)
    assert re.search(r"(?i)stat", name) and not re.search(r"(?i)edge", name)
    with open(p) as fh:
        assert fh.readline().rstrip("\n").split("\t") == list(FS.STATS_HEADER)


def test_safe_print_refuses_an_alarming_line(capsys):
    """A print that can SOMETIMES alarm is the s52b bug; there is no third
    option between `safe_print` and `banner`."""
    FS.safe_print("healthy: 0 escapes, 24 shards")
    assert "healthy" in capsys.readouterr().out
    with pytest.raises(FS.AlarmContractError):
        FS.safe_print("novel-candidate classes: 3")


def test_banner_is_the_sanctioned_alarm(capsys):
    FS.banner("MC28 FIND: shard 3 produced 1 completion")
    out = capsys.readouterr().out
    assert out.startswith("*** ") and out.rstrip().endswith(" ***")
    assert FS.is_alarming(out)


def test_check_summary_is_the_new_instrument_rule():
    """"Before driving a NEW instrument through the supervisor, diff its
    terminal summary against the alarm regex" — executable."""
    healthy = ("multi-covers containing lam(id): total=224\n"
               "walk nodes=47623  runtime=0.1s\n"
               "NO walk in the supply-tight multi-cover family\n")
    assert FS.check_summary(healthy) == []
    assert FS.check_summary("novel-candidate classes: 0\nESCAPES 1\n") == \
        ["ESCAPES 1"]


def test_shard_slices_partition_exactly():
    """What lets a fetch assert `sum(shard units) == declared total`."""
    for total, shards in ((224, 7), (206043, 24), (5, 24), (0, 3)):
        sizes = [FS.shard_slice_size(total, shards, o) for o in range(shards)]
        assert sum(sizes) == total
        for o in range(shards):
            assert sizes[o] == len([k for k in range(total)
                                    if k % shards == o])


# --- the ported mc28 adapter -----------------------------------------------

ADAPTER = repo_path("analysis", "farm", "template", "mc28_adapter.py")


def test_mc28_adapter_self_test():
    """The adapter's own control: stride partition, emit->consume equality,
    and an engine smoke on the designed-SAT n=5 family."""
    proc = subprocess.run([PY, ADAPTER, "--self-test"], cwd=REPO,
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SELF-TEST OK" in proc.stdout


def test_mc28_adapter_dry_run_reproduces_the_s63_smoke(tmp_path):
    """Parity with the s63 `mc28dry2` farm smoke, shard 0: 8586 covers,
    43 ticks, one DRYRUN progress row and a DONE row."""
    out = str(tmp_path / "s00")
    proc = subprocess.run(
        [PY, ADAPTER, "--shard", "0/24", "--out", out, "--dry-run",
         "-n", "6", "--tmax", "872", "--v", "28", "--splits", "20",
         "--jmin", "1", "--forest", "--total-covers", "206043",
         "--tick", "200"],
        cwd=REPO, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "8586 covers, 43 ticks" in proc.stdout
    raw = _status_bytes(out)
    assert _progress_rows(raw) == [(0, 1)]
    assert b"\tDONE\t" in raw
    assert os.path.isfile(os.path.join(out, "GATE.md"))
    # the escape-scan trap: a healthy dry shard writes NO .txt at all
    assert [f for f in os.listdir(out) if f.endswith(".txt")] == []


def test_mc28_adapter_refuses_enumeration_sharding(tmp_path):
    """A real run without `--covers-file` would make every shard re-walk the
    whole forest tree (N x the enumeration for 1 x the search)."""
    proc = subprocess.run(
        [PY, ADAPTER, "--shard", "0/24", "--out", str(tmp_path),
         "-n", "6", "--tmax", "872", "--v", "28", "--splits", "20",
         "--jmin", "1", "--forest"],
        cwd=REPO, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2
    assert "--covers-file is REQUIRED" in proc.stderr


def test_farm_layout_resolution_from_a_checkout():
    """The layout probe the 6 shims each hand-rolled, resolved once."""
    sys.path.insert(0, repo_path("analysis", "farm", "template"))
    import farmlayout                                          # noqa: E402
    root, kind = farmlayout.repo_root()
    assert kind == farmlayout.MAC
    assert os.path.realpath(root) == os.path.realpath(REPO)
    assert os.path.isfile(farmlayout.repo_path("pylib", "mcover_search.py"))
    assert farmlayout.repo_path("no", "such", "thing", required=False) is None
