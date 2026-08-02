#!/usr/bin/env python3
"""s62 A0 GATE RE-RUN -- the s56 "chain alone" baseline at a real budget.

docs/SWEEP-QUEUE.md "## A0 gate re-run at 120 s, both lanes (s60 menu item 2)";
out/s59/cliff/REPORT.md §7 ("Still uncorrected") calls the artifact this
instrument replaces **the most citation-dangerous line left in the repo**.

WHAT IS BEING RE-RUN.  s56 ran the A0 gate -- level "A0" of
`out/s56/p1a/p1a_assume.build_variant`, i.e. `atoms = None` and `fixed = []`,
the RAW chain-only exact-cover instance with no atom-pool restriction and no
fixed prefix rows -- on the six panel controls of `out/s59/cliff/geninst.py`
at a tiny time limit, got six UNKNOWNs, and `docs/JOURNAL.md`:189-190 wrote
them up as "A0 (chain only, the s15 baseline) 0/6 -- reproducing the field
fact exactly".  That sentence now reads, in every downstream citation, as *no
engine finds a cover from the chain alone*.  s59 §3.1 showed a 15 s UNKNOWN on
a sibling instance was as little as 0.6M nodes short of a SAT.  So the number
is a BUDGET ARTIFACT until it is re-measured, and this instrument re-measures
it: 6 controls x 3 runs, both lanes, at an operator-chosen budget.

WHAT A VERDICT MEANS HERE -- READ THIS BEFORE WRITING ANY SENTENCE ABOUT IT.

  * These six instances are **KNOWN-SAT BY CONSTRUCTION**.  Each is built from
    the certificate of a KNOWN 5906/5907 word, and `p1a_assume.extract`
    asserts that every row of that word's cover is present in the instance
    (`cert row {key} absent from instance rows`).  A0 deletes nothing.  So a
    cover exists; the only open question is whether an ENGINE FINDS IT.
    The A0 gate is a FINDABILITY measurement, never a decision problem.
    Never write "no cover exists" -- not for an UNKNOWN, and not ever.
  * UNKNOWN (rc 3, timeout / node cap) = **nothing learned**.  Three-valued,
    always.  It is not a negative result, it is the absence of one.
  * SAT (rc 0) = the alarm event.  An engine found a cover FROM THE CHAIN
    ALONE, which is exactly the premise the A-ladder (A0 < A1 < A2/A3, "atom
    assumptions are what make the instance solvable") is built on.  Note the
    chain pins the length: length = 5764 + #2-loops and #2-loops = K + R is
    fixed by the chain, so any cover of one of these instances compiles to a
    word of the SAME length as its source (5906, or 5907 for the 5907
    control).  A SAT here is a findability event, NOT a new record -- the
    sub-5906 check below is a defensive tripwire, not an expectation.
  * UNSAT (rc 2) = a **soundness contradiction**, because the known cover is
    in the instance.  It would mean the encoding or the engine is wrong.
    Alarms.

TWO LANES, THREE RUNS PER CONTROL (fixed grid, 18 cells):
    epsilon = 0.00, seed 0   REFUTATION lane -- deterministic single pass
                             (dlx7g skips its restart machinery when
                             epsilon == 0: "deterministic: restarting is
                             pointless", dlx7g.c:1116)
    epsilon = 0.15, seed 1   WITNESS lane -- randomized restarts
    epsilon = 0.15, seed 2   WITNESS lane, second seed
s59 §3.2 is the reason both lanes are mandatory and neither is privileged: at
120 s the DETERMINISTIC lane matched or beat epsilon=0.15 on every disputed
cell of this family, so "restarts are better" is itself a corrected claim.
Seed variance is real at boundary cells, hence two witness seeds.

SIZING, SO NOBODY IS SURPRISED BY THE RESULT.  A0 is the FULL pool: 4.92-5.73
x R on these six controls (see --dry-run).  The s59 cliff study measured this
instance family as SAT-reachable only to 2.69-3.50 x R at 120 s.  A0 sits far
above that band, so the honest prior is 18 UNKNOWNs -- and 18 UNKNOWNs at 600 s
is still a strictly better citation than 6 UNKNOWNs at 15 s, because it is the
difference between "we did not look" and "we looked hard".  The instrument
exists to make the field fact citable OR to break it, and both are products.

TRAPS
-----
1. `dlxrun.run` hard-codes its engine path with no `.exe`, so on Windows it
   would not find the binary.  This module rebinds `dlxrun.DLX7G` (the module
   attribute, NOT the file) to the resolved path before any call.  `--dlx`
   overrides.
2. `p1a_assume.confirm_sat` shells out to `cargo run --release` for the Rust
   validator.  **The farm PC has no Rust toolchain** (docs/SWEEP-QUEUE.md,
   "Farm execution").  A SAT there must not be lost to a FileNotFoundError, so
   confirm_sat is called inside a guard and falls back to the pure-Python half
   (gain1.check_cover + chain7.compile_chain_cover + word file on disk), which
   is reported as VALIDATOR-UNAVAILABLE, never as validated.
3. The supervisor's alarm regex.  See ALARM_RE / say() below -- a healthy
   shard is structurally incapable of self-bannering.

FARM CONTRACT (analysis/farm/pysweep_run.ps1 + untargeted_super.ps1)
    upyw.exe -u <target> --shard i/N --out <dir> [--limit K] [--dry-run] <extra>
  * STATUS heartbeat, appended, tab-delimited, flushed per write; one progress
    row per completed cell carrying a `\t<done>/<total>\t` field (that is
    where the supervisor reads declTotal), terminal row carries `\tDONE\t`.
  * a0_stats_s<NN>.tsv matches the supervisor's `(?i)stat` TSV row counter and
    is APPENDED per cell, so the counter tracks live progress and a killed
    shard still leaves every completed run on disk.
  * a0_ledger_s<NN>.tsv is the provenance ledger (instance sha256, engine
    argv, raw RESULT line, SAT confirmation), also appended per cell.

usage:
  a0gate.py --shard i/N --out DIR [--limit K] [--dry-run]
            [--time-limit 600] [--max-nodes N] [--dlx PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# p1a_assume sets most of these up itself on import, but it derives them from
# its OWN __file__; adding them here first keeps the import order honest and
# makes the failure mode "missing file" rather than "missing attribute".
# s64 P1: `dlxrun` now comes from the tracked pylib/ package instead of
# gitignored out/s57/proposer.  `p1a_assume` is not promoted yet, so the
# legacy homes are still registered (it also self-derives its own paths).
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_legacy_paths()

import dlxrun  # noqa: E402
import p1a_assume as P  # noqa: E402

# --------------------------------------------------------------- the panel --
# Verbatim from out/s59/cliff/geninst.py's PANEL (same order, same groups).
# The group tags are the s57 controls.pkl chain groups, kept so a0 rows join
# against out/s59/cliff/instances.json and out/s58 cut-store rows.
PANEL = [
    ("5906.up-02d771908307", "data/upstream5906/5906.up-02d771908307.txt", "ctrlgroup0"),
    ("5906.rbnd-2641d60c9d5c", "data/novel5906c/5906.rbnd-2641d60c9d5c.txt", "ctrlgroup8"),
    ("5906.up-331228e22360", "data/upstream5906/5906.up-331228e22360.txt", "ctrlgroup4"),
    ("5906.up-6f42b3603dac", "data/upstream5906/5906.up-6f42b3603dac.txt", "ctrlgroup3"),
    ("5906.up-0a065898a821", "data/upstream5906/5906.up-0a065898a821.txt", "ctrlgroup1"),
    ("5907.up-6f2e8d9df51c", "data/upstream5907/5907.up-6f2e8d9df51c.txt", "ctrlgroup6"),
]

# (epsilon, seed, lane).  ORDER IS PART OF THE CONTRACT -- shard i/N takes
# cells where idx % N == i, so reordering this list reshuffles every shard.
LANES = [
    (0.00, 0, "refutation"),
    (0.15, 1, "witness"),
    (0.15, 2, "witness"),
]

# The one surviving s56 A0 instance file.  Regenerating it must be byte-exact
# or this instrument is not measuring what s56 measured.
ANCHOR_CONTROL = "5906.up-02d771908307"
ANCHOR_FILE = os.path.join(REPO, "out", "s56", "p1a",
                           "inst_5906.up-02d771908307_A0_0.txt")

DEFAULT_DLX = os.path.join(REPO, "analysis", "trackc", "dlx7g")

# `stage` matches out/s59/cliff/trials.tsv's first column and the queue
# entry's "stage tag a0_120" convention, so s62 rows join straight onto the
# s59 ladder rows: stage = a0_<time-limit>.
STAT_COLS = ["stage", "idx", "shard", "control", "group", "lane", "epsilon", "seed",
             "time_limit", "max_nodes", "K", "Sigma", "V", "R", "pool", "mult",
             "cols", "rows", "known_rows", "verdict", "reading", "seconds",
             "nodes", "attempts", "maxdepth"]
LEDGER_COLS = ["stage", "ts", "idx", "shard", "control", "group", "word_path", "lane",
               "epsilon", "seed", "time_limit", "max_nodes", "verdict",
               "reading", "seconds", "inst_sha256", "anchor_bytecheck",
               "sol_rows", "validated", "length", "identical_to_source",
               "sub5906", "validator", "word_file", "result_line"]


# ------------------------------------------------ supervisor alarm guarding --
# untargeted_super.ps1 (~line 283) banners any stdout line matching this.  Two
# prior sweeps bannered ALL healthy shards because their NORMAL end-of-run
# summary matched it: s52b fuse.py printed "ESCAPES 0" (the `\bESCAPES\b`
# version of the regex), and s52b demotion.py printed "novel-candidate
# classes: 0" (the `\bNOVEL\b` version).  Both were fixed by requiring a
# NONZERO count -- but the standing rule from that episode is: diff YOUR
# summary against the regex before launching.  This module does better than
# diffing it once; it enforces it at every print.
ALARM_RE = re.compile(
    r"(?i)Traceback|MemoryError|^\s*!!|\*\*\*|ESCAPES\s+[1-9]|NOVEL[^:\r\n]*:\s*[1-9]")

# Substrings that can make an otherwise-healthy line match.  Note "novel":
# one panel control lives in data/novel5906c/, so ANY line carrying that path
# next to a timestamp ("...novel5906c... 12:34") matches the NOVEL branch.
# That is why stdout only ever names controls by BASE NAME; paths go to the
# ledger TSV, which the supervisor does not alarm-scan.
_DESENS = re.compile(r"[*!]|novel|escapes|traceback|memoryerror", re.I)


def say(msg, alarm=False):
    """Print one stdout line.  alarm=False lines CANNOT banner the supervisor.

    A healthy line that would match ALARM_RE is rewritten so that it provably
    cannot: every token the regex keys on (`*`, `!`, novel, escapes,
    traceback, memoryerror) is replaced by `.`, after which no branch of the
    regex has anything to match.  The rewrite is announced, never silent.
    alarm=True is reserved for the events that SHOULD banner: a SAT, an UNSAT
    (a soundness contradiction on a known-SAT instance), an engine error, and
    a failed anchor byte-check.
    """
    if not alarm and ALARM_RE.search(msg):
        msg = "alarm-regex guard rewrote this line | " + _DESENS.sub(".", msg)
    print(msg, flush=True)


# ---------------------------------------------------------------- the grid --
def cells():
    """The 18 cells, in the FIXED order sharding depends on.

    control-major, lane-minor: idx = control_index * 3 + lane_index.
    """
    out = []
    for ci, (base, wpath, group) in enumerate(PANEL):
        for li, (eps, seed, lane) in enumerate(LANES):
            out.append(dict(idx=ci * len(LANES) + li, control=base,
                            word_path=wpath, group=group, epsilon=eps,
                            seed=seed, lane=lane,
                            key=f"{base}[e{eps}s{seed}]"))
    return out


def build(cache, cell):
    """-> (instance text, rowmap, ex, sizing dict) for one cell's control.

    A0 is `build_variant(ex, "A0", fix=0, noise=0, seed=*)`: level "A0" is in
    none of build_variant's atom branches, so `atoms` stays None, and it is
    not in ("A2", "A3"), so `nfix = 0` and `fixed = []`.  The reduction is
    therefore the identity -- every column and every row of the chain instance
    survives -- which is exactly why the known cover is still inside it.  The
    seed argument is inert at A0 (no rng is constructed); it is passed as 1 to
    match out/s59/cliff/geninst.py's convention.
    """
    base = cell["control"]
    if base not in cache:
        ex = P.extract(os.path.join(REPO, cell["word_path"]))
        txt, rowmap, fixed, nc, nr, npool = P.build_variant(ex, "A0", 0, 0, 1)
        assert npool is None and not fixed, \
            f"A0 must have atoms=None and fixed=[]; got pool={npool} fixed={len(fixed)}"
        m = ex["inst"]["meta"]
        pool = len({r["loop"] for r in ex["inst"]["rows"]})
        cache[base] = (txt, rowmap, ex, dict(
            K=m["K"], Sigma=m["Sigma"], V=m["V"], R=m["R"], pool=pool,
            mult=round(pool / m["R"], 3), cols=nc, rows=nr,
            known_rows=len(ex["known_rows"]),
            sha256=hashlib.sha256(txt.encode()).hexdigest()))
    return cache[base]


def parse_result(line):
    """nodes / attempts / maxdepth out of dlx7g's `RESULT ...` stderr line."""
    d = {}
    for k in ("nodes", "attempts", "maxdepth"):
        m = re.search(rf"{k}=(\d+)", line or "")
        d[k] = int(m.group(1)) if m else ""
    return d


READING = {
    "SAT": "cover-found-from-chain-alone",
    "UNSAT": "exhausted-CONTRADICTION-known-cover-is-in-this-instance",
    "UNKNOWN": "nothing-learned (budget exhausted; NOT a negative result)",
}


# ------------------------------------------------------- SAT confirmation --
def confirm(ex, full_rows, outdir, tag):
    """p1a_assume.confirm_sat, with a no-Rust-toolchain fallback.

    -> dict(ok, length, validator, identical, word_file, mode)
    """
    try:
        c = P.confirm_sat(ex, full_rows, outdir, tag)
        c["mode"] = "confirm_sat(check_cover+compile+cargo validate)"
        return c
    except Exception as exc:                                    # noqa: BLE001
        # Almost certainly `cargo` missing (the farm PC has no Rust
        # toolchain).  Do the Python half here so the SAT is never lost.
        import chain7
        import gain1
        inst = ex["inst"]
        chosen = [inst["rows"][i] for i in full_rows]
        rep = gain1.check_cover(inst, chosen)
        if not rep["valid"]:
            return dict(ok=False, length=None, identical=None, word_file=None,
                        validator=f"check_cover INVALID; {type(exc).__name__}",
                        mode="python-only fallback")
        word, _cert, _costs = chain7.compile_chain_cover(inst, chosen)
        wf = os.path.abspath(os.path.join(outdir, f"word_{tag}.txt"))
        with open(wf, "w") as fh:
            fh.write(word)
        return dict(ok=False, length=len(word), word_file=wf,
                    identical=(word == ex["word"]),
                    validator=("VALIDATOR-UNAVAILABLE (no Rust toolchain here): "
                               f"{type(exc).__name__}; check_cover=valid, "
                               "compile=ok -- re-validate on the Mac"),
                    mode="python-only fallback")


# ------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser(
        description="s62 A0 gate re-run -- chain-only completion, both lanes")
    ap.add_argument("--shard", default="0/1", help="i/N; cell idx %% N == i")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0,
                    help="run only the first K cells of THIS shard")
    ap.add_argument("--dry-run", action="store_true",
                    help="enumerate + size the cells, write the TSVs, never "
                         "invoke dlx7g")
    ap.add_argument("--time-limit", type=float, default=600.0,
                    help="per-run wall budget in seconds (queue entry says "
                         ">= 300; 15 s is the artifact being replaced)")
    ap.add_argument("--max-nodes", type=int, default=None)
    ap.add_argument("--dlx", default=None, help="dlx7g path override")
    a = ap.parse_args()

    try:
        si, sn = (int(x) for x in a.shard.split("/"))
    except ValueError:
        raise SystemExit(f"--shard must be i/N, got {a.shard!r}")
    if sn < 1 or not (0 <= si < sn):
        raise SystemExit(f"--shard out of range: {a.shard}")

    os.makedirs(a.out, exist_ok=True)
    workdir = os.path.join(a.out, "work")
    os.makedirs(workdir, exist_ok=True)
    tag = f"s{si:02d}"

    # TRAP 1: dlxrun.DLX7G carries no .exe suffix.  Rebind the attribute.
    dlx = a.dlx or (DEFAULT_DLX + (".exe" if os.name == "nt" else ""))
    dlxrun.DLX7G = dlx

    status_p = os.path.join(a.out, "STATUS")
    st = open(status_p, "a", buffering=1)

    def stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def beat_progress(key, done, total, note):
        """One PROGRESS row.  The `\\t<done>/<total>\\t` field is what
        untargeted_super.ps1 counts and where it reads declTotal from."""
        st.write(f"{stamp()}\t{key}\t{done}/{total}\t{note}\n")
        st.flush()

    def beat_event(field, note):
        """An EVENT or the terminal row.  Deliberately carries NO
        `\\t<d>/<d>\\t` field: the supervisor counts every STATUS line that has
        one as an intermediate, so a DONE/SAT row with a progress field makes
        the tally read 4/3 instead of 3/3 -- the exact over-count its own
        comment (untargeted_super.ps1 ~line 236) warns about."""
        st.write(f"{stamp()}\t{field}\t{note}\n")
        st.flush()

    stats_p = os.path.join(a.out, f"a0_stats_{tag}.tsv")
    ledger_p = os.path.join(a.out, f"a0_ledger_{tag}.tsv")

    def append(path, cols, rec):
        new = not os.path.exists(path)
        with open(path, "a") as fh:
            if new:
                fh.write("\t".join(cols) + "\n")
            fh.write("\t".join(str(rec.get(c, "")).replace("\t", " ")
                               for c in cols) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    t0 = time.time()
    allcells = cells()
    mine = [c for c in allcells if c["idx"] % sn == si]
    if a.limit:
        mine = mine[:a.limit]

    say(f"a0gate shard {si}/{sn}: {len(mine)} of {len(allcells)} cells "
        f"| time-limit {a.time_limit:g}s max-nodes {a.max_nodes} "
        f"| engine {os.path.basename(dlx)} "
        f"| mode {'DRY-RUN' if a.dry_run else 'LIVE'}")
    if not a.dry_run and not os.path.exists(dlx):
        st.close()
        raise SystemExit(f"dlx7g not found: {dlx}")

    cache = {}
    anchor_state = "not-checked"
    n_sat = n_unsat = n_unknown = n_err = 0
    rc = 0

    # ---- 1. anchor byte-check.  Regenerating the one surviving s56 A0
    #         instance must reproduce it byte-for-byte, or this instrument is
    #         not re-running the same gate.
    if any(c["control"] == ANCHOR_CONTROL for c in mine) or a.dry_run:
        if os.path.exists(ANCHOR_FILE):
            acell = next(c for c in allcells if c["control"] == ANCHOR_CONTROL)
            atxt, _rm, _ex, _sz = build(cache, acell)
            with open(ANCHOR_FILE) as fh:
                want = fh.read()
            if want == atxt:
                anchor_state = "OK"
                say(f"anchor byte-check: OK -- regenerated "
                    f"{ANCHOR_CONTROL} A0 == out/s56/p1a/"
                    f"inst_{ANCHOR_CONTROL}_A0_0.txt ({len(atxt)} bytes)")
            else:
                anchor_state = "MISMATCH"
                say(f"!! a0gate ANCHOR BYTE-CHECK FAILED: regenerated "
                    f"{ANCHOR_CONTROL} A0 is {len(atxt)} bytes, s56 file is "
                    f"{len(want)} bytes -- this shard is NOT re-running the "
                    f"s56 gate.  Refusing to continue.", alarm=True)
                beat_event("ANCHORFAIL",
                           "regenerated A0 != the s56 instance file")
                beat_event("DONE",
                           "aborted on anchor byte-check failure")
                st.close()
                return 3
        else:
            anchor_state = "anchor-file-absent"
            say(f"anchor byte-check: SKIPPED -- {ANCHOR_FILE} not present "
                f"(ship it with the payload to enable this check)")

    # ---- 2. the cells
    for k, c in enumerate(mine):
        txt, rowmap, ex, sz = build(cache, c)
        rec = dict(stage=f"a0_{a.time_limit:g}", idx=c["idx"], shard=a.shard, control=c["control"],
                   group=c["group"], word_path=c["word_path"], lane=c["lane"],
                   epsilon=c["epsilon"], seed=c["seed"],
                   time_limit=a.time_limit, max_nodes=a.max_nodes,
                   anchor_bytecheck=anchor_state, ts=stamp(), **sz)
        rec["inst_sha256"] = sz["sha256"]

        if a.dry_run:
            rec.update(verdict="DRYRUN", reading="sizing only, no solver call",
                       seconds=0)
            say(f"[{k + 1}/{len(mine)}] idx={c['idx']:2d} {c['control']:24} "
                f"{c['lane']:10} eps={c['epsilon']} seed={c['seed']} "
                f"R={sz['R']} pool={sz['pool']} ({sz['mult']:.2f}xR) "
                f"cols={sz['cols']} rows={sz['rows']} "
                f"known_cover_rows={sz['known_rows']} sha={sz['sha256'][:12]}")
        else:
            rtag = f"a0_{c['control']}_e{c['epsilon']}_s{c['seed']}"
            r = dlxrun.run(txt, time_limit=a.time_limit,
                           max_nodes=a.max_nodes, tag=rtag, outdir=workdir,
                           epsilon=c["epsilon"], seed=c["seed"])
            p = parse_result(r["result_line"])
            v = r["verdict"]
            rec.update(verdict=v, reading=READING.get(v, "ENGINE ERROR"),
                       seconds=round(r["seconds"], 2),
                       result_line=r["result_line"], sol_rows=len(r["rows"]),
                       **p)
            say(f"[{k + 1}/{len(mine)}] idx={c['idx']:2d} {c['control']:24} "
                f"{c['lane']:10} eps={c['epsilon']} seed={c['seed']} "
                f"pool={sz['mult']:.2f}xR rows={sz['rows']} -> {v} "
                f"in {rec['seconds']}s nodes={p['nodes']} "
                f"attempts={p['attempts']} maxdepth={p['maxdepth']}")

            if v == "SAT":
                n_sat += 1
                full = [rowmap[i] for i in r["rows"]]
                cf = confirm(ex, full, a.out, rtag)
                rec.update(validated=cf.get("ok"), length=cf.get("length"),
                           identical_to_source=cf.get("identical"),
                           validator=cf.get("validator"),
                           word_file=cf.get("word_file"),
                           sub5906=bool(cf.get("length") and
                                        cf["length"] < 5906))
                say(f"*** A0 SAT: {c['control']} lane={c['lane']} "
                    f"eps={c['epsilon']} seed={c['seed']} -- a cover of the "
                    f"CHAIN-ONLY instance was FOUND in {rec['seconds']}s. "
                    f"rows={len(full)} validated={cf.get('ok')} "
                    f"length={cf.get('length')} "
                    f"identical_to_source={cf.get('identical')} "
                    f"word={cf.get('word_file')} "
                    f"validator={cf.get('validator')} "
                    f"-- the A-ladder premise (A0 unreachable) is BROKEN ***",
                    alarm=True)
                if rec["sub5906"]:
                    say(f"*** SUB-5906 CANDIDATE: length {cf['length']} < 5906 "
                        f"from {c['control']} -- gate it before believing "
                        f"anything: cargo run --release -- validate -n 7 "
                        f"--file {cf.get('word_file')} --complete AND "
                        f"analysis/counting/m3_check.py -n 7 "
                        f"{cf.get('word_file')} ***", alarm=True)
                beat_event("SAT",
                           f"{c['key']} rows={len(full)} "
                           f"len={cf.get('length')} validated={cf.get('ok')}")
            elif v == "UNSAT":
                n_unsat += 1
                say(f"*** A0 UNSAT: {c['control']} lane={c['lane']} "
                    f"eps={c['epsilon']} seed={c['seed']} -- the engine "
                    f"reports EXHAUSTED on an instance that provably contains "
                    f"the {sz['known_rows']}-row cover of its own source "
                    f"word.  This is a SOUNDNESS CONTRADICTION in the "
                    f"encoding or the engine, not a result about covers ***",
                    alarm=True)
                beat_event("UNSAT",
                           f"{c['key']} soundness contradiction: the known "
                           f"cover is inside this instance")
            elif v == "UNKNOWN":
                n_unknown += 1
            else:
                n_err += 1
                rc = 1
                say(f"!! a0gate engine error on {c['control']} "
                    f"eps={c['epsilon']} seed={c['seed']}: {v} "
                    f"| {r['result_line'][:160]}", alarm=True)

        append(stats_p, STAT_COLS, rec)
        append(ledger_p, LEDGER_COLS, rec)
        beat_progress(c["key"], k + 1, len(mine),
                      f"verdict={rec['verdict']} secs={rec.get('seconds')} "
                      f"pool={sz['mult']}xR rows={sz['rows']}")

    secs = time.time() - t0

    # ---- 3. terminal summary.  Diffed against ALARM_RE below AND routed
    #         through say(), so a healthy shard cannot self-banner.
    if a.dry_run:
        summary = (f"a0gate dry-run shard {si}/{sn}: cells={len(mine)} "
                   f"of {len(allcells)} anchor={anchor_state} "
                   f"controls={len(cache)} no solver calls {secs:.1f}s")
    else:
        summary = (f"a0gate shard {si}/{sn}: cells={len(mine)} "
                   f"sat={n_sat} unsat={n_unsat} unknown={n_unknown} "
                   f"engine_errors={n_err} anchor={anchor_state} "
                   f"tl={a.time_limit:g}s {secs:.1f}s")
    assert not ALARM_RE.search(summary), \
        "terminal summary matches the supervisor alarm regex -- the s52b bug"
    say(summary)
    beat_event("DONE", summary)
    st.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
