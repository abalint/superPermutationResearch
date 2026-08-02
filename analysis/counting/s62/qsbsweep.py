#!/usr/bin/env python3
"""s62 QS-B FULL REALIZER VERDICT-MIX MAP -- chains #0 / #24, refutation lane.

docs/SWEEP-QUEUE.md "## QS-B full realizer verdict-mix map, chains #0/#24 (s59
item 4 follow-on)".  The product is the curve NOVELTY-DESIGN Sec 6.0/6.4
actually needs -- *what fraction of a generator's output can the realizer
DECIDE, as a function of the precision the generator achieves* -- replacing the
single "~100 decisions/s" scalar that s56 measured on three cells.

WHAT IS MEASURED.  For a chain (one of Houston's two still-open n=7 chains) the
exact-cover instance has a pool of `P` distinct 2-loops and a chain rank `R`.
A "proposer of precision m" is modelled by a uniform random draw of
k = round(m * R) loops from that pool; the realizer is dlx7g on the instance
restricted to rows whose loop is in the draw.  Sweeping m gives, per cell:

    decided fraction  = (SAT + UNSAT) / N          <- the throughput curve
    UNSAT fraction    = UNSAT / N                  <- ONLY sound at epsilon = 0
    decisions/s       = 1 / mean(seconds)          <- the s56 scalar, per cell

REFUTATION LANE ONLY (epsilon = 0, seed 0), by the queue entry's own reasoning:
a randomized-restart (epsilon > 0) run that stops without a witness has NOT
exhausted anything, so its "UNSAT" would be a statement about one restart
stream, not about the instance.  Only the deterministic lane can report an
UNSAT FRACTION soundly.  dlx7g skips its restart machinery entirely when
epsilon == 0 ("deterministic: restarting is pointless", dlx7g.c:1116), which is
also why one sample needs exactly one run here -- no seed replicates.

WHAT A VERDICT MEANS -- READ BEFORE WRITING ANY SENTENCE ABOUT IT.
  * UNSAT = a theorem about THAT DRAW: no cover of the chain uses only those k
    loops.  It is a real, positive datum (it is most of the product) and is
    NOT an alarm.  It says nothing about the chain being closed: the chain is
    open exactly because a cover may use loops outside the draw.
  * UNKNOWN (rc 3, timeout) = nothing learned.  Three-valued, always.  A
    timeout is never a negative result.
  * SAT = A COVER OF AN OPEN CHAIN.  Both chains here have K + R = 141
    (27+114 and 29+112), and length = 5764 + #2-loops with #2-loops = K + R
    pinned by the chain (s34 law, THEORY Sec 7), so a cover compiles to a
    5905 -- a WORLD RECORD CANDIDATE.  The shard STOPS on a SAT (nothing after
    it matters until it is gated) and banners it.  The gate is, all three
    green, and on the MAC:
        p1a_assume.confirm_sat
        cargo run --release -- validate -n 7 --file <abspath> --complete
        python3 analysis/counting/m3_check.py -n 7 <abspath>

THE SAMPLING STREAM IS LOAD-BEARING AND IS COPIED VERBATIM.
out/s59/cliff/qsb.py (and out/s56 p1a_throughput.py before it) draw

    pool = sorted({r["loop"] for r in inst["rows"]})
    rng  = random.Random(12345 + idx)          # idx = CHAIN index, 0 or 24
    samples = [set(rng.sample(pool, k)) for _ in range(nsamp)]

with the rng re-seeded per (chain, mult) cell.  `draw()` below is those three
lines and nothing else, so this sweep's cells are directly comparable to the
s56 and s59 numbers: for any mult they share, our first n samples ARE their n
samples, instance-text-for-instance-text.  Anything that reorders `pool`,
changes the seed base, changes the k formula, or draws in a different order
breaks the comparison silently -- do not "optimise" draw().

DELIBERATE DEVIATIONS FROM THE QUEUE ENTRY, ALL DEFAULTS, ALL RECORDED
---------------------------------------------------------------------
1. `mult = full` IS ONE DISTINCT DRAW, NOT 200.  k = |pool| makes
   `set(rng.sample(pool, k))` the whole pool every time, so the cell's 200
   "samples" are 200 copies of one atom set -- and at epsilon = 0 the engine is
   deterministic, so they are 200 copies of one solver run (~1.7 core-hours of
   duplicate work per chain at TL 30).  This module keeps the 200 sample rows
   (the empirical statistic over 200 draws is exactly what the queue asked for,
   and it is well defined) but SOLVES each distinct atom set once and reuses
   the verdict, marking the reused rows solved=0 dup_of=<sample>.  Below
   mult=full a collision is astronomically unlikely, so nothing else changes.
   --no-dedup disables it and pays the duplicate solves in full.
2. SHARDING IS BY UNIT, NOT BY CELL, by default (--shard-by cell restores the
   queue's literal "18 natural shards").  The cells do not price alike: the
   measured spread is ~0.004 s at 3.0xR against a 30 s timeout at 4.5xR+, i.e.
   FOUR ORDERS OF MAGNITUDE, so one-cell-per-shard would leave half the farm
   idle within seconds while the wall clock is set by a single ~1-2 hour shard.
   Unit sharding (`unit_idx % N == i`) hands every shard ~1/N of EVERY cell, so
   all shards finish together and the wall is total/N.  It also makes each
   shard its own round-robin probe.  Every unit carries its cell coordinates,
   so the per-cell aggregation is done at fetch time from the unit rows and is
   identical either way.
3. A SAT STOPS THE SHARD (--continue-after-sat to override).  A 5905 candidate
   makes the rest of the sweep irrelevant until it is gated.

FARM CONTRACT (analysis/farm/pysweep_run.ps1 + untargeted_super.ps1)
    upyw.exe -u <target> --shard i/N --out <dir> [--limit K] [--dry-run] <extra>
  * STATUS heartbeat in --out: appended, tab-delimited, flushed per write; one
    PROGRESS row per completed unit carrying a `\t<done>/<total>\t` field (that
    is where the supervisor reads declTotal); the terminal row carries `\tDONE\t`
    and DELIBERATELY NO `<d>/<d>` field, or the supervisor counts it as another
    intermediate and the tally reads 201/200.
  * qsb_stats_s<NN>.tsv matches the supervisor's `(?i)stat` TSV row counter and
    is APPENDED per unit, so the counter tracks live progress and a killed
    shard still leaves every completed unit on disk.
  * qsb_cells_s<NN>.tsv is this shard's per-cell rollup (does NOT match
    `(?i)stat` or `(?i)edge`, so it is not double-counted).
  * healthy stdout can never match the supervisor's alarm regex -- see say().

TRAPS
-----
1. `dlxrun.DLX7G` has no ".exe" suffix.  It happens to work on Windows because
   CreateProcess appends one for an extensionless image name, but this module
   rebinds the module attribute to the resolved path anyway; --dlx overrides.
2. `p1a_assume.confirm_sat` shells out to `cargo run --release`, and THE FARM
   PC HAS NO RUST TOOLCHAIN.  A 5905 must never be lost to a FileNotFoundError,
   so confirm() below runs it under a guard and falls back to the pure-Python
   half (gain1.check_cover + chain7.compile_chain_cover + the word on disk),
   reported as VALIDATOR-UNAVAILABLE -- never as validated.
3. confirm_sat wants a p1a_assume `ex` record, which normally comes from a
   KNOWN WORD.  These chains have no word (that is the point), so confirm()
   passes ex = {"inst": inst, "word": None}: check_cover and
   compile_chain_cover only ever read ex["inst"], and `identical` then compares
   against None and is reported as False, which is the truth.
4. dlx7g row ids index the FILTERED row list, not inst["rows"].  rowmap
   (built in the same order instance_text writes) maps them back; getting this
   wrong turns a 5905 into an invalid cover at gate time.

usage:
  qsbsweep.py --shard i/N --out DIR [--limit K] [--dry-run]
              [--time-limit 30] [--samples 200] [--probe K] [--mults ...]
              [--chains 0,24] [--shard-by unit|cell] [--dlx PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# s64 P1: `dlxrun` and `chain7` now come from the tracked pylib/ package
# instead of gitignored out/s57/proposer + analysis/cover7.  `p1a_assume`
# and `certificate` are not promoted yet -> add_legacy_paths().
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_legacy_paths()

import chain7                                    # noqa: E402
import dlxrun                                    # noqa: E402
import p1a_assume as P                           # noqa: E402

FARM_CHAINS = os.path.join(REPO, "analysis", "farm", "farm_chains.jsonl")
DEFAULT_DLX = os.path.join(REPO, "analysis", "trackc", "dlx7g")

# The queue grid.  ORDER IS PART OF THE CONTRACT: unit_idx is derived from
# these positions, so reordering either list reshuffles every shard.
CHAINS = [0, 24]
MULTS = [3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75, "full"]

# s34 law: length = 5764 + #2-loops, and a cover of a chain instance uses
# exactly K + R distinct 2-loops.  Both chains here have K + R = 141, so any
# SAT compiles to a 5905.  Asserted per chain at build time.
BASE_LEN = 5764
RECORD_TARGET = 5905

# `nsamp` is the cell's DECLARED sample count (N), carried on every unit row so
# the fetch-time aggregation can tell a complete cell from a truncated one
# without being told what N was.  A --probe run writes the same N with fewer
# rows, which is exactly the signal "this is a pricing pass, not the curve".
STAT_COLS = ["stage", "unit", "shard", "chain", "mult", "mult_x", "R", "pool",
             "k", "nsamp", "cols", "rows", "lane", "epsilon", "seed", "sample",
             "time_limit", "verdict", "seconds", "nodes", "attempts",
             "maxdepth", "solved", "dup_of", "inst_sha256"]
CELL_COLS = ["stage", "shard", "chain", "mult", "mult_x", "R", "pool", "k",
             "samples", "solved", "SAT", "UNSAT", "UNKNOWN", "ERROR",
             "decided_frac", "unsat_frac", "mean_s", "median_s", "p90_s",
             "max_s", "decisions_per_sec", "solver_s", "wall_s"]


# ------------------------------------------------ supervisor alarm guarding --
# untargeted_super.ps1 (~line 283) banners any stdout line matching this.  Two
# earlier sweeps bannered ALL healthy shards because their NORMAL end-of-run
# summary matched it (s52b fuse.py's "ESCAPES 0"; s52b demotion.py's
# "novel-candidate classes: 0"), and a0gate.py nearly repeated it today.  The
# standing rule is: diff YOUR summary against this regex before launching.
# This module enforces it at every print instead of diffing it once.
ALARM_RE = re.compile(
    r"(?i)Traceback|MemoryError|^\s*!!|\*\*\*|ESCAPES\s+[1-9]|NOVEL[^:\r\n]*:\s*[1-9]")

# Every token any branch of ALARM_RE can key on.  Note that no path or word in
# this instrument's normal output contains "novel" -- but a --dlx or --out path
# supplied by an operator could, and it is printed in the banner line, so the
# guard is applied unconditionally rather than argued about.
_DESENS = re.compile(r"[*!]|novel|escapes|traceback|memoryerror", re.I)


def say(msg, alarm=False):
    """Print one stdout line.  alarm=False lines CANNOT banner the supervisor.

    A healthy line that would match ALARM_RE is rewritten so that it provably
    cannot: every token the regex keys on is replaced by `.`, after which no
    branch has anything to match.  The rewrite is announced, never silent.
    alarm=True is reserved for the two events that SHOULD banner: a SAT (a 5905
    candidate on an open chain) and an engine error.  An UNSAT here is a NORMAL
    RESULT -- it is most of the product -- and must never alarm.
    """
    if not alarm and ALARM_RE.search(msg):
        msg = "alarm-regex guard rewrote this line | " + _DESENS.sub(".", msg)
    print(msg, flush=True)


# ---------------------------------------------------------------- the grid --
def mult_label(m):
    # Two decimals, not %g: "3.00" sorts next to "3.25" and reads like the
    # queue entry, whereas %g gives "3" and "4" and sorts them wrong.
    return "full" if m == "full" else f"{m:.2f}"


def cells():
    """The 18 cells in the FIXED order the unit index depends on."""
    out = []
    for ci, chain in enumerate(CHAINS):
        for mi, m in enumerate(MULTS):
            out.append(dict(cell=ci * len(MULTS) + mi, chain=chain, mult=m,
                            label=f"c{chain}m{mult_label(m)}"))
    return out


def units(nsamp, probe=0):
    """The flat unit list.  unit = one (chain, mult, sample) solver call.

    unit_idx = cell * nsamp + sample -- a STABLE identity that does not depend
    on --probe or on the shard count.  Sharding then takes every N-th unit of
    this list, which hands shard i a 1/N slice of EVERY cell (deviation 2).
    """
    out = []
    for c in cells():
        n = min(probe, nsamp) if probe else nsamp
        for s in range(n):
            out.append(dict(unit=c["cell"] * nsamp + s, sample=s, **c))
    return out


def draw(chain_idx, pool, k, nsamp):
    """THE sampling stream.  Verbatim from out/s59/cliff/qsb.py (which is in
    turn bit-identical to out/s56 p1a_throughput.py).  See the header."""
    rng = random.Random(12345 + chain_idx)
    return [set(rng.sample(pool, k)) for _ in range(nsamp)]


def load_chain(cache, chain_idx):
    """-> dict(inst, R, pool, rowsets) for one chain, built once per process."""
    if chain_idx not in cache:
        with open(FARM_CHAINS) as fh:
            rows = [json.loads(l) for l in fh]
        sol = [tuple(x) for x in rows[chain_idx]["chain"]]
        inst = chain7.build_instance_from_chain(sol)
        meta = inst["meta"]
        pool = sorted({r["loop"] for r in inst["rows"]})
        nloops = meta["K"] + meta["R"]
        assert BASE_LEN + nloops == RECORD_TARGET, (
            f"chain #{chain_idx} has K+R={nloops}, so a cover compiles to "
            f"{BASE_LEN + nloops}, not {RECORD_TARGET} -- the 'a SAT is a 5905' "
            f"claim in this instrument's banner would be WRONG for it")
        cache[chain_idx] = dict(inst=inst, R=meta["R"], pool=pool, meta=meta)
    return cache[chain_idx]


def k_of(mult, R, npool):
    """qsb.py's k formula.  `full` is the k the formula gives at mult=P/R."""
    if mult == "full":
        return npool
    return min(int(round(R * mult)), npool)


def parse_result(line):
    d = {}
    for key in ("nodes", "attempts", "maxdepth"):
        m = re.search(rf"{key}=(\d+)", line or "")
        d[key] = int(m.group(1)) if m else ""
    return d


READING = {
    "SAT": "COVER FOUND -- 5905 candidate, gate on the Mac",
    "UNSAT": "no cover uses only these k loops (a theorem about THIS DRAW)",
    "UNKNOWN": "nothing-learned (budget exhausted; NOT a negative result)",
}


# ------------------------------------------------------- SAT confirmation --
def confirm(inst, full_rows, outdir, tag):
    """p1a_assume.confirm_sat with a no-Rust-toolchain fallback (trap 2/3)."""
    ex = dict(inst=inst, word=None)
    try:
        c = P.confirm_sat(ex, full_rows, outdir, tag)
        c["mode"] = "confirm_sat(check_cover+compile+cargo validate)"
        return c
    except Exception as exc:                                    # noqa: BLE001
        import gain1
        chosen = [inst["rows"][i] for i in full_rows]
        rep = gain1.check_cover(inst, chosen)
        if not rep["valid"]:
            return dict(ok=False, length=None, word_file=None, identical=False,
                        validator=f"check_cover INVALID; {type(exc).__name__}",
                        mode="python-only fallback")
        word, _cert, _costs = chain7.compile_chain_cover(inst, chosen)
        wf = os.path.abspath(os.path.join(outdir, f"word_{tag}.txt"))
        with open(wf, "w") as fh:
            fh.write(word)
        return dict(ok=False, length=len(word), word_file=wf, identical=False,
                    validator=("VALIDATOR-UNAVAILABLE (no Rust toolchain here): "
                               f"{type(exc).__name__}; check_cover=valid, "
                               "compile=ok -- re-validate on the Mac"),
                    mode="python-only fallback")


# ------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser(
        description="s62 QS-B verdict-mix map -- chains 0/24, refutation lane")
    ap.add_argument("--shard", default="0/1", help="i/N")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0,
                    help="run only the first K units of THIS shard")
    ap.add_argument("--dry-run", action="store_true",
                    help="enumerate + size + DRAW every cell, write the TSVs, "
                         "never invoke dlx7g")
    ap.add_argument("--time-limit", type=float, default=30.0)
    ap.add_argument("--samples", type=int, default=200,
                    help="N per cell (the queue says 200)")
    ap.add_argument("--probe", type=int, default=0,
                    help="round-robin pricing pass: use only the first K "
                         "samples of every cell (house rule -- high-mult cells "
                         "do not price like low-mult cells)")
    ap.add_argument("--shard-by", choices=("unit", "cell"), default="unit")
    ap.add_argument("--no-dedup", action="store_true",
                    help="solve duplicate atom sets again instead of reusing "
                         "the verdict (see deviation 1)")
    ap.add_argument("--continue-after-sat", action="store_true")
    ap.add_argument("--max-nodes", type=int, default=None)
    ap.add_argument("--dlx", default=None)
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

    dlx = a.dlx or (DEFAULT_DLX + (".exe" if os.name == "nt" else ""))
    dlxrun.DLX7G = dlx                                          # trap 1

    st = open(os.path.join(a.out, "STATUS"), "a", buffering=1)

    def stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def beat_progress(key, done, total, note):
        """PROGRESS row.  The `\\t<done>/<total>\\t` field is what
        untargeted_super.ps1 counts and reads declTotal from."""
        st.write(f"{stamp()}\t{key}\t{done}/{total}\t{note}\n")
        st.flush()

    def beat_event(field, note):
        """EVENT / terminal row.  Carries NO `\\t<d>/<d>\\t` field on purpose:
        the supervisor counts every STATUS line that has one as an
        intermediate, so a DONE row with a progress field makes the tally read
        201/200 (untargeted_super.ps1 ~line 236 warns about exactly this)."""
        st.write(f"{stamp()}\t{field}\t{note}\n")
        st.flush()

    stats_p = os.path.join(a.out, f"qsb_stats_{tag}.tsv")
    cells_p = os.path.join(a.out, f"qsb_cells_{tag}.tsv")

    def append(path, cols, rec):
        new = not os.path.exists(path)
        with open(path, "a") as fh:
            if new:
                fh.write("\t".join(cols) + "\n")
            fh.write("\t".join(str(rec.get(c, "")).replace("\t", " ")
                               for c in cols) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    t_run = time.time()
    allunits = units(a.samples, a.probe)
    if a.shard_by == "cell":
        mine = [u for u in allunits if u["cell"] % sn == si]
    else:
        # Round-robin on POSITION in the unit list, not on the unit id.  For
        # the full grid the two are the same thing (position == unit id when
        # every cell contributes all N samples), but for a --probe pass the
        # unit ids are sparse (cell * N + s with s < K), and `unit % N` would
        # hand some shards twice the work of others.  The `unit` field stays
        # the stable identity for provenance and duplicate detection.
        mine = [u for j, u in enumerate(allunits) if j % sn == si]
    if a.limit:
        mine = mine[:a.limit]

    stage = f"qsb_{a.time_limit:g}"
    say(f"qsbsweep shard {si}/{sn}: {len(mine)} of {len(allunits)} units "
        f"| {len(cells())} cells x N={a.samples}"
        f"{f' (probe {a.probe}/cell)' if a.probe else ''} "
        f"| lane refutation eps=0 seed=0 | TL {a.time_limit:g}s "
        f"| shard-by {a.shard_by} | dedup {'off' if a.no_dedup else 'on'} "
        f"| engine {os.path.basename(dlx)} "
        f"| mode {'DRY-RUN' if a.dry_run else 'LIVE'}")
    if not a.dry_run and not os.path.exists(dlx):
        st.close()
        raise SystemExit(f"dlx7g not found: {dlx}")

    chains = {}
    samples = {}        # cell -> the cell's full N-sample list
    memo = {}           # (cell, frozenset(atoms)) -> (verdict, seconds, p, sample)
    acc = {}            # cell -> rollup accumulator
    n_by = {"SAT": 0, "UNSAT": 0, "UNKNOWN": 0}
    n_err = 0
    n_solved = 0
    rc = 0
    stopped = None

    for step, u in enumerate(mine):
        ch = load_chain(chains, u["chain"])
        R, pool, inst = ch["R"], ch["pool"], ch["inst"]
        k = k_of(u["mult"], R, len(pool))
        if u["cell"] not in samples:
            # The FULL N draws, always -- sample s must be the s-th draw of the
            # cell's stream no matter which shard runs it.
            samples[u["cell"]] = draw(u["chain"], pool, k, a.samples)
            # R/pool/k are carried in the accumulator, not looked up again at
            # rollup time: the rollup must not depend on any other structure
            # still being populated when it runs.
            acc[u["cell"]] = dict(t0=time.time(), secs=[], solver=0.0,
                                  v={"SAT": 0, "UNSAT": 0, "UNKNOWN": 0,
                                     "ERROR": 0}, solved=0, n=0,
                                  R=R, pool=len(pool), k=k)
        atoms = samples[u["cell"]][u["sample"]]
        A = acc[u["cell"]]

        rows = [r for r in inst["rows"] if r["loop"] in atoms]
        txt = P.instance_text(inst["columns"], rows, set(inst["roots"]))
        rec = dict(stage=stage, unit=u["unit"], shard=a.shard, chain=u["chain"],
                   mult=mult_label(u["mult"]), mult_x=round(k / R, 4), R=R,
                   pool=len(pool), k=k, nsamp=a.samples,
                   cols=len(inst["columns"]),
                   rows=len(rows), lane="refutation", epsilon=0.0, seed=0,
                   sample=u["sample"], time_limit=a.time_limit,
                   inst_sha256=hashlib.sha256(txt.encode()).hexdigest())

        if a.dry_run:
            rec.update(verdict="DRYRUN", seconds=0, solved=0, dup_of="")
            append(stats_p, STAT_COLS, rec)
            A["n"] += 1
            beat_progress(u["label"], step + 1, len(mine),
                          f"DRYRUN k={k} ({rec['mult_x']}xR) rows={len(rows)} "
                          f"sha={rec['inst_sha256'][:12]}")
            continue

        key = (u["cell"], frozenset(atoms))
        if not a.no_dedup and key in memo:
            v, secs, p, src = memo[key]
            rec.update(verdict=v, seconds=secs, solved=0, dup_of=src, **p)
        else:
            r = dlxrun.run(txt, time_limit=a.time_limit, max_nodes=a.max_nodes,
                           tag=f"qsb_{tag}", outdir=workdir, epsilon=0.0,
                           seed=0)
            p = parse_result(r["result_line"])
            v = r["verdict"]
            secs = round(r["seconds"], 4)
            rec.update(verdict=v, seconds=secs, solved=1, dup_of="", **p)
            memo[key] = (v, secs, p, u["sample"])
            n_solved += 1
            A["solved"] += 1
            A["solver"] += r["seconds"]

            if v == "SAT":
                # dlx row ids index the FILTERED list (trap 4).
                rowmap = [i for i, rr in enumerate(inst["rows"])
                          if rr["loop"] in atoms]
                full = [rowmap[i] for i in r["rows"]]
                stag = f"qsb_c{u['chain']}_m{mult_label(u['mult'])}_s{u['sample']}"
                with open(os.path.join(a.out, f"inst_{stag}.txt"), "w") as fh:
                    fh.write(txt)
                cf = confirm(inst, full, a.out, stag)
                art = os.path.join(a.out, f"JACKPOT_{stag}.json")
                with open(art, "w") as fh:
                    json.dump(dict(chain=u["chain"], mult=mult_label(u["mult"]),
                                   sample=u["sample"], k=k, R=R,
                                   atoms=sorted(map(str, atoms)),
                                   dlx_rows=r["rows"], inst_rows=full,
                                   length=cf.get("length"),
                                   validated=cf.get("ok"),
                                   validator=cf.get("validator"),
                                   word_file=cf.get("word_file")), fh, indent=1)
                say(f"*** QS-B SAT: chain #{u['chain']} mult={mult_label(u['mult'])} "
                    f"({rec['mult_x']}xR, k={k}) sample={u['sample']} -- a COVER "
                    f"of an OPEN n=7 chain in {secs}s. rows={len(full)} "
                    f"length={cf.get('length')} validated={cf.get('ok')} "
                    f"word={cf.get('word_file')} validator={cf.get('validator')} "
                    f"artifact={art} -- this is a {RECORD_TARGET} CANDIDATE. "
                    f"Gate on the Mac before believing anything: confirm_sat, "
                    f"cargo run --release -- validate -n 7 --complete, "
                    f"m3_check.py -n 7 ***", alarm=True)
                beat_event("SAT", f"{u['label']} sample={u['sample']} "
                                  f"rows={len(full)} len={cf.get('length')} "
                                  f"validated={cf.get('ok')} artifact={art}")
                if not a.continue_after_sat:
                    stopped = (f"stopped after SAT on {u['label']} "
                               f"sample={u['sample']}")
            elif v not in ("UNSAT", "UNKNOWN"):
                n_err += 1
                rc = 1
                say(f"!! qsbsweep engine error on chain #{u['chain']} "
                    f"mult={mult_label(u['mult'])} sample={u['sample']}: {v} "
                    f"| {(r['result_line'] or '')[:160]}", alarm=True)

        v = rec["verdict"]
        n_by[v] = n_by.get(v, 0) + 1
        A["v"][v if v in A["v"] else "ERROR"] += 1
        A["secs"].append(rec["seconds"])
        A["n"] += 1
        append(stats_p, STAT_COLS, rec)
        beat_progress(u["label"], step + 1, len(mine),
                      f"{v} {rec['seconds']}s k={k} ({rec['mult_x']}xR) "
                      f"solved={rec['solved']}")
        if stopped:
            break

    # ---- per-cell rollup for THIS shard.  With unit sharding each shard holds
    #      a 1/N slice of every cell, so these rows are PARTIAL by design and
    #      the authoritative aggregation is done at fetch time over the unit
    #      rows of all shards.  They are written anyway: they are what a human
    #      reads off a live shard, and they survive a killed run.
    for c in cells():
        A = acc.get(c["cell"])
        if not A or not A["n"]:
            continue
        ts = A["secs"] or [0.0]
        dec = A["v"]["SAT"] + A["v"]["UNSAT"]
        srt = sorted(ts)
        row = dict(stage=stage, shard=a.shard, chain=c["chain"],
                   mult=mult_label(c["mult"]), R=A["R"], pool=A["pool"],
                   k=A["k"],
                   samples=A["n"], solved=A["solved"], SAT=A["v"]["SAT"],
                   UNSAT=A["v"]["UNSAT"], UNKNOWN=A["v"]["UNKNOWN"],
                   ERROR=A["v"]["ERROR"],
                   decided_frac=round(dec / A["n"], 4),
                   unsat_frac=round(A["v"]["UNSAT"] / A["n"], 4),
                   mean_s=round(statistics.mean(ts), 4),
                   median_s=round(statistics.median(ts), 4),
                   p90_s=round(srt[min(len(srt) - 1, int(0.9 * len(srt)))], 4),
                   max_s=round(max(ts), 4),
                   decisions_per_sec=(round(1.0 / statistics.mean(ts), 3)
                                      if statistics.mean(ts) > 0 else ""),
                   solver_s=round(A["solver"], 2),
                   wall_s=round(time.time() - A["t0"], 1))
        row["mult_x"] = round(row["k"] / row["R"], 4)
        append(cells_p, CELL_COLS, row)
        if not a.dry_run:
            say(f"cell chain#{c['chain']} mult={row['mult']} "
                f"({row['mult_x']}xR k={row['k']}) n={row['samples']} "
                f"solved={row['solved']} "
                f"SAT={row['SAT']} UNSAT={row['UNSAT']} "
                f"UNKNOWN={row['UNKNOWN']} ERR={row['ERROR']} "
                f"decided={row['decided_frac']} unsat_frac={row['unsat_frac']} "
                f"mean={row['mean_s']}s median={row['median_s']}s "
                f"max={row['max_s']}s dec/s={row['decisions_per_sec']}")

    secs = time.time() - t_run

    # ---- terminal summary.  Routed through say() AND asserted against
    #      ALARM_RE, so a healthy shard is structurally incapable of
    #      self-bannering (the s52b bug, twice repeated).
    if a.dry_run:
        summary = (f"qsbsweep dry-run shard {si}/{sn}: units={len(mine)} "
                   f"of {len(allunits)} cells_touched={len(acc)} "
                   f"chains_built={len(chains)} no solver calls {secs:.1f}s")
    else:
        summary = (f"qsbsweep shard {si}/{sn}: units={len(mine)} "
                   f"solves={n_solved} sat={n_by.get('SAT', 0)} "
                   f"unsat={n_by.get('UNSAT', 0)} "
                   f"unknown={n_by.get('UNKNOWN', 0)} engine_errors={n_err} "
                   f"tl={a.time_limit:g}s {secs:.1f}s"
                   + (f" [{stopped}]" if stopped else ""))
    assert not ALARM_RE.search(summary), \
        "terminal summary matches the supervisor alarm regex -- the s52b bug"
    say(summary)
    beat_event("DONE", summary)
    st.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
