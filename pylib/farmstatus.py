#!/usr/bin/env python3
"""farmstatus -- the farm STATUS heartbeat contract, encoded ONCE (s64 P5).

Before s64 this contract existed only as PROSE, restated (and drifted) in
every shim docstring under `analysis/farm/`.  Both documented s52b bugs are
violations of it, and both were found by smoke test rather than by
construction:

  * "Heartbeat units must match the declared total."  `promote_shim` emitted
    `replays/total_replays` while ticking every 50 replays, so a FINISHED run
    read `50/2462 (2%)`.
  * "A zero-count summary line must never alarm."  `demotion.py`'s normal
    `novel-candidate classes: 0` matched the supervisor's stdout scan and
    bannered all 24 HEALTHY shards into ALARM.txt.

Everything below is derived from `analysis/farm/untargeted_super.ps1`
AS BUILT (line refs are to that file).  If the supervisor changes, this
module changes, and `tests_py/test_farmstatus.py` is the pin.

THE CONTRACT
------------
1.  **File.**  The heartbeat is a file whose name starts with `STATUS`, in
    the shard's `--out` directory (super.ps1 `Find-Status`, :105).  It is
    APPEND-only and line-buffered: the supervisor reads it incrementally and
    a crashed shard must leave its history behind.

2.  **Progress rows.**  The supervisor counts a row as progress iff the line
    contains a tab-delimited `<i>/<n>` FIELD -- regex ``\\t(\\d+)/(\\d+)\\t``
    (:240).  It increments its own counter by one per matching row and takes
    the shard's declared total from `<n>`.  Two consequences that have each
    cost a run:
      * the `i/n` field needs a tab on BOTH sides, so it can never be the
        last field on the line;
      * **the row count and `<n>` must be in the same unit.**  The supervisor
        does not read `<i>`; it counts ROWS.  So `<n>` is "how many rows will
        this shard write", not "how many widgets will it process".

3.  **Work-based tick.**  Emitting one row per unit of work is exact but
    floods the supervisor's incremental reader; emitting one row per N units
    is the norm.  `FarmStatus.work()` does the accounting: the caller ticks
    REAL WORK, the emitter converts to rows, and `declared_rows` is derived
    from the same `tick`, so units can never drift from the declared total.
    A tick is a decision about the STALL threshold too: one row every
    `tick x per-unit-seconds`, and `-StallMinutes` must exceed that gap.
    (Raising `--tick` without raising `-StallMinutes` flags healthy shards.)

4.  **Non-progress rows must not look like progress.**  DONE/ESCAPE/note rows
    carry no `i/n` field, or the supervisor counts them as progress and
    (worse) redefines the declared total from whatever digits they contain.
    Every writer here strips tabs out of caller-supplied text, so a note can
    never manufacture a field boundary.

5.  **Terminal row.**  `<ts>\\tDONE\\t<summary>` sets the supervisor's
    `sawDone`, which is the strong form of its completion verdict (:249,
    :332 -- `verdict-by=STATUS-DONE` beats `verdict-by=heartbeat`).  Emit it
    even on failure; put the rc in the summary.

6.  **Escape rows.**  `<ts>\\t(ESCAPE|MIDESCAPE|SHORTER)\\t<detail>` is the
    supervisor's own alarm channel (:241): it raises ALARM.txt and banners
    STATUS.  This is the row a find writes.  It is NOT a progress row.

7.  **Alarm-regex-safe stdout.**  The supervisor scans new stdout with
    ``(?i)Traceback|MemoryError|^\\s*!!|\\*\\*\\*|ESCAPES\\s+[1-9]|NOVEL[^:\\r\\n]*:\\s*[1-9]``
    (:283).  A healthy shard must be STRUCTURALLY incapable of matching it.
    `safe_print()` enforces that by raising on any line that would match;
    `banner()` is the one sanctioned way to match it on purpose.
    `check_summary()` is the "diff a new instrument's terminal summary
    against the alarm regex" rule, executable.

8.  **Products.**  `untargeted_status.ps1:92` counts EVERY `*.txt` under the
    run's `out\\` tree and banners them as ESCAPE CANDIDATES, so a scratch
    `.txt` is a false find (four recurrences through s63).  Notes go to
    `.md` -- hence `gate_md()`.  `.tsv` names matching `(?i)stat` are
    row-counted as products and `(?i)edge` as rediscoveries (super.ps1 :263);
    anything else must match neither.

9.  **Newlines.**  Every file here is opened with ``newline=""`` so a "\\n"
    is written as one LF byte on Windows too.  s63 lost a farm pre-flight to
    exactly this: `--emit-covers` used plain `open(p,"w")`, Windows wrote
    CRLF, and the sha256 accumulated over the pre-translation bytes could
    never match -- every shard would have exited 4.

USAGE (the whole adapter side of the contract)
----------------------------------------------
    from farmstatus import FarmStatus, safe_print, banner

    st = FarmStatus(out, shard=i, shards=n, total_units=mine, tick=200)
    st.gate_md("... the gate for anything this run produces ...")
    for item in work:
        ...
        st.work()                      # one unit; rows emitted every `tick`
    st.escape(f"j={j} len={ln} file={fn}")     # only on a find
    st.stats(["shard", "done", "rc"], [i, done, rc])
    st.done(f"shard {i}/{n}: {done} units, {secs:.1f}s, rc={rc}")
"""
import math
import os
import re
import time

__all__ = [
    "ALARM_REGEX", "ALARM_RE", "PROGRESS_FIELD_RE", "AlarmContractError",
    "FarmStatus", "STATS_HEADER", "banner", "check_summary", "is_alarming",
    "open_lf", "parse_shard", "safe_print", "shard_slice_size",
]

# The supervisor's stdout scan, VERBATIM from untargeted_super.ps1:283.
# `untargeted_alarmtest.ps1` is the PowerShell-side regression test for the
# same string; tests_py/test_farmstatus.py mirrors its 13 cases here.
ALARM_REGEX = (r"(?i)Traceback|MemoryError|^\s*!!|\*\*\*|ESCAPES\s+[1-9]"
               r"|NOVEL[^:\r\n]*:\s*[1-9]")
ALARM_RE = re.compile(ALARM_REGEX, re.MULTILINE)

# What the supervisor counts as a progress row (untargeted_super.ps1:240).
PROGRESS_FIELD_RE = re.compile(r"\t(\d+)/(\d+)\t")

# Rows the supervisor treats as its own escape channel (:241).
ESCAPE_KINDS = ("ESCAPE", "MIDESCAPE", "SHORTER")

# The canonical per-shard stats row.  `farm_fetch.sh` adjudicates ANY
# instrument's run from these seven columns; keep them stable.
STATS_HEADER = ("shard", "shards", "units_done", "units_declared",
                "finds", "secs", "rc")


class AlarmContractError(RuntimeError):
    """A line that would trip the supervisor's alarm scan was printed as if
    it were healthy output.  This is the s52b bug class; fix the print."""


def is_alarming(line):
    """True iff `line` would make the supervisor raise ALARM.txt."""
    return bool(ALARM_RE.search(line))


def check_summary(lines):
    """Return the subset of `lines` that would alarm.

    The executable form of the OPS rule "before driving a NEW instrument
    through the supervisor, diff its terminal summary against the alarm
    regex".  Feed it an instrument's real end-of-run output; a non-empty
    result means a healthy shard would banner itself.
    """
    if isinstance(lines, str):
        lines = lines.splitlines()
    return [ln for ln in lines if is_alarming(ln)]


def safe_print(*parts, **kw):
    """print() that REFUSES to emit a line matching the alarm regex.

    Every healthy print in a farm instrument goes through this.  A deliberate
    alarm goes through `banner()` instead.  There is no third option: a print
    that can sometimes alarm is the s52b bug.
    """
    msg = " ".join(str(p) for p in parts)
    bad = check_summary(msg)
    if bad:
        raise AlarmContractError(
            "refusing to print a line that matches the supervisor's alarm "
            "scan (use banner() if it is a real event): " + repr(bad[0]))
    kw.setdefault("flush", True)
    print(msg, **kw)


def banner(*parts, **kw):
    """Print a DELIBERATE alarm line (`*** ... ***`).

    Reserved for the event the sweep exists to find, or for a
    misconfiguration that must stop the run.  The supervisor's `\\*\\*\\*`
    branch matches this and raises ALARM.txt.
    """
    msg = " ".join(str(p) for p in parts)
    if not msg.startswith("***"):
        msg = "*** " + msg
    if not msg.endswith("***"):
        msg = msg + " ***"
    kw.setdefault("flush", True)
    print(msg, **kw)


def open_lf(path, mode="w"):
    """open() that writes "\\n" as one LF byte on every platform.

    Windows text mode would translate to CRLF; s63 lost a pre-flight to that
    (a sha256 over pre-translation bytes can never match the file on disk).
    Use this for EVERY file a farm instrument writes.
    """
    return open(path, mode, newline="")


def parse_shard(argv, default=(0, 1)):
    """`--shard i/N` -> (i, N).  The supervisor's launch shape."""
    if "--shard" in argv:
        i, k = argv[argv.index("--shard") + 1].split("/")
        return int(i), int(k)
    return default


def shard_slice_size(total, shards, offset):
    """Size of the index-stride slice `k % shards == offset` of [0,total).

    Exact, and the slices partition [0,total) with no overlap and no gap --
    which is what lets a fetch script assert that the per-shard counts SUM to
    the instrument's own total (a short sum means a shard died mid-tree).
    """
    if total <= 0 or offset >= total:
        return 0
    return (total - offset + shards - 1) // shards


class FarmStatus:
    """The shard's STATUS heartbeat, plus its stats TSV and GATE.md.

    Parameters
    ----------
    out_dir : the shard's `--out` directory (created if missing).
    shard, shards : this shard's index and the shard count.
    total_units : units of REAL WORK this shard will process, or None if it
        cannot be known up front.  With None the declared total floats
        (rows so far), which the supervisor tolerates but which makes its
        percentage meaningless -- declare a total whenever you can.
    tick : units of work per emitted progress row (>= 1).
    label : the progress rows' second field.  Free text; the supervisor does
        not read it, but the operator does.
    """

    def __init__(self, out_dir, shard=0, shards=1, total_units=None,
                 tick=1, label="unit", status_name="STATUS"):
        self.out = out_dir
        self.shard = int(shard)
        self.shards = int(shards)
        self.tick = max(1, int(tick))
        self.label = label
        self.total_units = total_units
        self.units = 0
        self.rows = 0
        self.t0 = time.time()
        self.closed = False
        os.makedirs(out_dir, exist_ok=True)
        # append + line-buffered: the supervisor reads incrementally, and a
        # killed shard must leave its history on disk.  (Buffered stdout is
        # how s63 lost a killed process's totals.)
        self._fh = open(os.path.join(out_dir, status_name), "a",
                        buffering=1, newline="")
        # rows, not units -- clause 2.  ceil, so the last partial tick has a
        # row to land in and `final_fill()` can reach N/N exactly.
        self.declared_rows = (max(1, math.ceil(total_units / self.tick))
                              if total_units else 0)

    # ---------------------------------------------------------------- rows --
    @staticmethod
    def _stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _field(text):
        """Caller text -> one safe field: no tabs, no newlines.

        This is what makes clause 4 structural rather than a convention: a
        note can never manufacture a `\\t<i>/<n>\\t` boundary.
        """
        return re.sub(r"[\t\r\n]+", " ", str(text))

    def _write(self, line):
        if self.closed:
            raise RuntimeError("FarmStatus already closed")
        self._fh.write(line)

    def row(self, kind, note=""):
        """A NON-progress row: `<ts>\\t<kind>\\t<note>`.

        Never counted as progress, never redefines the declared total.
        """
        self._write(f"{self._stamp()}\t{self._field(kind)}"
                    f"\t{self._field(note)}\n")

    def progress(self, note=""):
        """Emit ONE progress row (`<ts>\\t<label>\\t<i>/<n>\\t<note>`).

        Prefer `work()`: it does the unit->row conversion, which is the part
        that has actually gone wrong in production.
        """
        self.rows += 1
        total = self.declared_rows or self.rows
        note = self._field(note) or f"{self.units} {self.label}s"
        self._write(f"{self._stamp()}\t{self._field(self.label)}"
                    f"\t{self.rows}/{total}\t{note}"
                    f"\t{time.time() - self.t0:.0f}s\n")

    def work(self, n=1, note=""):
        """Record `n` units of REAL WORK; emit rows as ticks complete.

        The whole point of the class: the caller counts what it actually
        did, and the row/declared-total units can never diverge.
        """
        self.units += n
        # rows are a pure function of units: after `u` units exactly
        # `u // tick` rows have been emitted.  A batched caller (n > tick)
        # therefore cannot lose rows, and no arithmetic drift is possible.
        while self.rows < self.units // self.tick:
            self.progress(note)
        return self.units

    def escape(self, note, kind="ESCAPE"):
        """The supervisor's own alarm channel -> ALARM.txt + STATUS banner.

        Write one per product.  This is a NON-progress row on purpose.
        """
        if kind not in ESCAPE_KINDS:
            raise ValueError(f"escape kind must be one of {ESCAPE_KINDS}")
        self.row(kind, note)

    def final_fill(self, note="final"):
        """Emit the row(s) needed for the supervisor to read N/N.

        Without this a shard that finished parks at 99% and the supervisor's
        weak completion test (`lines >= total`) never fires -- it then has to
        fall back to the DONE row.  Cheap insurance; call it before `done()`.
        """
        if self.declared_rows and self.rows < self.declared_rows:
            self.rows = self.declared_rows - 1
            self.progress(note)

    def done(self, summary):
        """The terminal `DONE` row (clause 5).  Emit it even on failure."""
        self.row("DONE", summary)

    def dry_run(self, summary):
        """A dry-run's whole heartbeat: one sizing row plus DONE.

        The sizing row IS a progress row (`0/1`), so a dry shard reads
        1/1 rather than 0/0 and the supervisor's tally is 24/24, not 0/24.
        """
        self._write(f"{self._stamp()}\tDRYRUN\t0/1\t{self._field(summary)}\n")
        self.rows = max(self.rows, 1)
        self.declared_rows = self.declared_rows or 1
        self.done("dry-run: " + str(summary))

    # ------------------------------------------------------------- products --
    def stats(self, header, values, name=None):
        """Write the shard's one-row stats TSV.

        The name matches `(?i)stat`, which is what the supervisor row-counts
        as live product progress (super.ps1 :264).  Keep any TSV that must
        NOT be counted free of both "stat" and "edge".
        """
        name = name or f"stats_s{self.shard:02d}.tsv"
        path = os.path.join(self.out, name)
        with open_lf(path) as fh:
            fh.write("\t".join(str(h) for h in header) + "\n")
            fh.write("\t".join(str(v) for v in values) + "\n")
        return path

    def gate_md(self, text, name="GATE.md"):
        """Write the run's own gate text.

        `.md`, NEVER `.txt`: `untargeted_status.ps1:92` counts every `*.txt`
        under the run's out tree as an ESCAPE CANDIDATE, and a healthy run
        that cries wolf trains the operator to ignore the one banner that
        matters (four recurrences through s63).  A `.txt` in `--out` must be
        an actual product and nothing else.
        """
        if name.lower().endswith(".txt"):
            raise ValueError(
                "GATE notes must not be .txt -- untargeted_status.ps1 counts "
                "every *.txt under out\\ as an ESCAPE CANDIDATE")
        path = os.path.join(self.out, name)
        with open_lf(path) as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        return path

    def product(self, name, text):
        """Write a real product file (a `.txt` here is CORRECT -- it is what
        the status page is counting)."""
        path = os.path.join(self.out, name)
        with open_lf(path) as fh:
            fh.write(text if text.endswith("\n") else text + "\n")
        return path

    # -------------------------------------------------------------- closing --
    def finish(self, finds=0, rc=0, note=""):
        """Fill to N/N, write the CANONICAL stats row, emit DONE.

        The canonical schema is what makes `farm_fetch.sh` generic: every
        adapter's stats TSV has the same seven columns, so one adjudicator
        can check "every shard rc 0, every shard has a DONE row, the
        per-shard unit counts SUM to the declared total" for any instrument.
        Instrument-specific numbers go in a SECOND TSV whose name matches
        neither `(?i)stat` nor `(?i)edge`.
        """
        self.final_fill()
        secs = self.elapsed
        self.stats(STATS_HEADER,
                   [self.shard, self.shards, self.units,
                    self.total_units or 0, finds, f"{secs:.1f}", rc])
        self.done(f"shard {self.shard}/{self.shards}: {self.units} "
                  f"{self.label}s, {finds} finds, {secs:.1f}s, rc={rc}"
                  + (f" -- {note}" if note else ""))
        return rc

    def finish_dry(self, summary, extra_header=(), extra_values=()):
        """A dry run's whole output: sizing row, DONE, canonical stats.

        A dry shard must still look COMPLETE to the supervisor (1/1 + DONE),
        or a dry smoke -- whose entire job is to prove the launch path --
        reads as 24 failed shards.
        """
        self.dry_run(summary)
        self.stats(list(STATS_HEADER) + list(extra_header),
                   [self.shard, self.shards, 0, self.total_units or 0,
                    0, f"{self.elapsed:.1f}", 0] + list(extra_values))
        return 0

    @property
    def elapsed(self):
        return time.time() - self.t0

    def close(self):
        if not self.closed:
            self._fh.close()
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


if __name__ == "__main__":                                   # pragma: no cover
    import sys
    print(f"farm alarm regex: {ALARM_REGEX}")
    bad = check_summary(sys.stdin.read()) if not sys.stdin.isatty() else []
    for ln in bad:
        print("WOULD ALARM: " + repr(ln))
    sys.exit(1 if bad else 0)
