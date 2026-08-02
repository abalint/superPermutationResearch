#!/usr/bin/env python3
"""mc28_shim.py -- run the s63 v=28 supply-tight FOREST multi-cover branch under
the farm supervisor's contract, WITHOUT modifying pylib/mcover_search.py.

WHAT THIS SWEEP IS.  docs/SWEEP-QUEUE.md, the n=6 midgame j-probe (s62 entry) as
RESHAPED by out/s63/mcover/REPORT.md.  It exhausts the ONE j>=1 872 cell that
lies in a known allocation -- (140,8,0,0,0): splits=20, D=8, v=28, supply-TIGHT
-- by enumerating every supply-tight 28-loop multi-cover of the 120 one-cycles
whose loop-cycle incidence graph is a FOREST, and running the arc DFS on each.

  * length = 863 + R + xp and j = R - 8, so length <= 872 with j >= 1 forces
    R = 9 exactly and xp = 0 (all doors weight 3);
  * R >= K := #phi-cycles, K is even and K >= v - splits = 8 (REPORT.md §6), so
    the cell needs K = 8 exactly, which holds IFF the incidence graph is a
    forest -- hence --forest is a SOUND restriction here, not a heuristic.
  * ANY completion found is a first-of-species event: a materialized j >= 1
    walk of length <= 872 at n=6.  Nothing like it exists.  See ALARMS below.

WHY A SHIM EXISTS AT ALL (paircuts_shim.py / promote_shim.py / a0_shim.py carry
the longer version).  pysweep_run.ps1 launches every shard as

    upyw.exe -u <TARGET> [<Mode>] --shard i/N --out <dir> [--limit K] [--dry-run] <ExtraArgs>

This is the promote_shim case, NOT the a0_shim/qsb_shim case -- mcover_search.py
needs real translation on two axes:

 1. ARG SHAPE.  mcover_search.py reads `n` and `TMAX` POSITIONALLY (argv[1],
    argv[2]) and shards by `--stride N --offset i`, not `--shard i/N`.  The
    supervisor's only injection point (ExtraArgs) appends at the END, so
    int(argv[1]) would be int("--shard") and all shards would die at once.
    This shim accepts the supervisor's shape and calls mcover_search.run()
    directly with the translated arguments (--shard i/N -> stride=N, offset=i).
    The stride/offset partition is EXACT: cover index k is processed by offset
    o iff k % N == o, so the N shards partition the cover index space with no
    overlap and no gap (smoke-tested at n=5, see --self-test).

    COVER FILE, NOT RE-ENUMERATION.  Sharding the ENUMERATION would make every
    one of the N shards re-walk the entire forest tree -- N x the enumeration
    for 1 x the search, which at N_forest ~ 1e6 is hours of pure duplicated
    work.  So the covers are enumerated ONCE on the Mac
    (`--emit-covers`), shipped, and each shard runs `--covers-file` and takes
    the lines with idx % N == i.  Shards become exactly balanced (equal line
    counts) rather than balanced-in-expectation, and the engine verifies the
    file's body sha256 + declared total before processing a single line
    (exit 4 if either fails).  --covers-file is REQUIRED here: this shim
    refuses to fall back to enumeration sharding, because that fallback would
    silently turn a 45-minute run into an 12-hour one.

 2. NO HEARTBEAT.  mcover_search.py prints ONLY at the end of the whole branch
    and writes no STATUS file, so without this shim every shard would report 0
    progress and be flagged STALLED.  The shim wraps mcover_search.prepare --
    which run() resolves through module globals at call time, exactly the trick
    promote_shim.py uses on demotion.first_visit_path -- so the engine source is
    untouched and the tick can never drift from the real cover stream.

    STATUS units are TICKS, not covers: one row per --tick covers, and the
    declared total is in the same unit (ceil(shard_covers / tick)).  The
    supervisor takes <n> from the row's own `\\t<i>/<n>\\t` field and counts one
    line per row, so mixing units there would make the percentage lie.

ALARMS -- READ THIS BEFORE CHANGING ANY PRINT.  The supervisor's stdout scan is
      (?i)Traceback|MemoryError|^\\s*!!|\\*\\*\\*|ESCAPES\\s+[1-9]|NOVEL[^:\\r\\n]*:\\s*[1-9]
  * A healthy shard prints only `multi-covers containing lam(id): ...`,
    `phi-cycle-count histogram K: ...`, `walk nodes=... runtime=...s` and
    `NO walk in the supply-tight multi-cover family ...`.  None of those match,
    so a healthy shard is structurally incapable of self-bannering (the s52b
    trap: a normal summary that bannered all 24 healthy shards).
  * CRITICALLY, THE ENGINE DOES NOT BANNER A FIND EITHER.  A completion prints
    `MIN LENGTH BY j in this multi-cover family:` -- which matches NOTHING in
    that regex.  The alarm is therefore THIS SHIM'S JOB: on any find it prints
    a `*** ` banner, writes a `\\tESCAPE\\t` STATUS row (the supervisor's own
    escape channel), materializes the walk, and re-reads it through lib62 to
    record the ledger coordinates next to it.  If you ever change the engine's
    output, re-check it against that regex BEFORE the next launch.
  * The engine's own `*** PARTIAL (cap hit) ***` and `*** NOT SUPPLY-TIGHT: ...`
    lines DO match, and both SHOULD alarm: the first means a shard was capped
    and its "NO walk" is not a negative, the second means the launch was
    misconfigured.  No cap is passed on the farm, so neither should ever fire.
  * The supervisor's ALARM banner text is hardcoded n=7 boilerplate.  This is an
    n=6 hunt; the shim writes the correct gate into GATE.txt in its own out dir.

PRODUCTS in --out: `STATUS` (heartbeat), `mc28_stats_sNN.tsv` (one row; picked
up by the supervisor's `(?i)stat` row counter), `GATE.md`, and -- only if the
cell is non-empty -- `mc28-sNN-j<j>-<len>.txt` plus `mc28-sNN-FIND.txt`.
No name here contains `edge`, so nothing is double-counted.

  *** THE .txt EXTENSION IS LOAD-BEARING. ***  untargeted_status.ps1:92 counts
  EVERY `*.txt` under the run's out\\ tree and banners them as "ESCAPE
  CANDIDATES".  The notes file is therefore GATE.md, NOT GATE.txt -- a dry-run
  smoke with GATE.txt made the status page announce "24 product .txt file(s)
  written -- these are ESCAPE CANDIDATES" on a run that had found nothing, which
  is the s52b failure exactly: a healthy run that cries wolf teaches the
  operator to ignore the one banner that matters.  With GATE.md the counter is
  ZERO on a healthy run, so ANY nonzero count is a real find.  Do not add a
  .txt file to --out for any purpose other than an actual product.

usage:
  upyw.exe -u mc28_shim.py --shard 0/24 --out F:\\...\\s00 \\
      -n 6 --tmax 872 --v 28 --splits 20 --jmin 1 --forest \\
      --covers-file F:\\...\\covers_v28_forest.txt --tick 200
  python3 analysis/farm/mc28_shim.py --self-test        # partition + engine smoke
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# s64 P1: the instrument now lives in the TRACKED pylib/ package, not in
# gitignored out/s62/jtax.  The two-candidate probe is kept verbatim in
# shape because the farm payload unpacks as $ROOT\repo\... while a Mac
# checkout has this shim in analysis/farm/ -- same pattern as a0_shim.py /
# qsb_shim.py.  Ship pylib/ with the payload (see analysis/farm/mc28_ship.sh).
for _cand in (os.path.join(HERE, "repo", "pylib"),
              os.path.join(HERE, "..", "..", "pylib")):
    if os.path.isdir(_cand):
        JTAX = os.path.abspath(_cand)
        break
else:
    print("mc28_shim: cannot locate pylib/", file=sys.stderr)
    sys.exit(2)
sys.path.insert(0, JTAX)  # <- pylib bootstrap (farm-layout variant)
if not os.path.isfile(os.path.join(JTAX, "mcover_search.py")):
    print(f"mc28_shim: instrument not found: {JTAX}/mcover_search.py",
          file=sys.stderr)
    sys.exit(2)

import mcover_search as M            # noqa: E402
import lib62                         # noqa: E402


def stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def shard_covers(total, shards, offset):
    """How many covers index-stride `shards` at `offset` selects out of
    `total`.  Exact; the shards partition [0,total)."""
    if total <= 0:
        return 0
    return (total - offset + shards - 1) // shards if offset < total else 0


def self_test():
    """Partition + engine smoke, no farm needed.  n=5 (v=7,splits=4) is the
    designed-SAT multi-cover control from out/s63/mcover/REPORT.md §3.3."""
    ok = True
    tot, shards = 224, 7
    s = sum(shard_covers(tot, shards, o) for o in range(shards))
    print(f"partition: sum over {shards} offsets = {s} (want {tot})")
    ok &= (s == tot)
    seen = []
    for o in range(shards):
        got = [k for k in range(tot) if k % shards == o]
        seen += got
        ok &= (len(got) == shard_covers(tot, shards, o))
    ok &= (sorted(seen) == list(range(tot)))
    print(f"disjoint+complete over indices: {sorted(seen) == list(range(tot))}")
    import tempfile
    cf = os.path.join(tempfile.mkdtemp(), "n5covers.txt")
    M.run(5, 154, 7, 4, jmin=0, emit_covers=cf)
    res = M.run(5, 154, 7, 4, jmin=0, stride=7, offset=0, covers_file=cf)
    print(f"engine smoke (n=5 v=7 splits=4 shard 0/7 via covers-file): "
          f"best={res[0]}")
    ok &= bool(res[0])
    # emit->consume must equal enumeration mode cover-for-cover
    full = M.run(5, 154, 7, 4, jmin=0, covers_file=cf)
    direct = M.run(5, 154, 7, 4, jmin=0)
    ok &= (full[0] == direct[0])
    print(f"emit->consume == enumeration: {full[0] == direct[0]}")
    print("SELF-TEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    # a leading bare token would be pysweep_run.ps1's -Mode; this shim has no
    # subcommand, so drop one rather than letting the parse choke on it
    if a and not a[0].startswith("-"):
        del a[0]
    if "--self-test" in a:
        return self_test()

    def opt(name, d=None):
        return a[a.index(name) + 1] if name in a else d

    out = opt("--out")
    if not out:
        print("mc28_shim: --out is required", file=sys.stderr)
        return 2
    os.makedirs(out, exist_ok=True)

    shards, offset = 1, 0
    if "--shard" in a:
        i, k = opt("--shard").split("/")
        offset, shards = int(i), int(k)
    n = int(opt("-n", "6"))
    tmax = int(opt("--tmax", "872"))
    covers_file = opt("--covers-file")
    v = int(opt("--v", "28"))
    splits = int(opt("--splits", "20"))
    jmin = int(opt("--jmin", "1"))
    tick = max(1, int(opt("--tick", "200")))
    total_covers = int(opt("--total-covers", "0"))
    forest = "--forest" in a
    dry = "--dry-run" in a
    if not covers_file:
        print("mc28_shim: --covers-file is REQUIRED (enumeration sharding "
              "would re-walk the whole tree in every shard)", file=sys.stderr)
        return 2
    if not os.path.isfile(covers_file):
        print(f"mc28_shim: covers file not found: {covers_file}",
              file=sys.stderr)
        return 2
    # the file's own declared total beats any operator-supplied number
    try:
        _h, _n, _ok, _sg, _sw, _decl = M.read_covers(covers_file)
        if _decl:
            total_covers = _decl
        if not _ok:
            print(f"mc28_shim: covers file FAILED verification "
                  f"(lines={_n} declared={_decl} sha={_sg} want={_sw})",
                  file=sys.stderr)
            return 4
    except Exception as e:                                   # noqa: BLE001
        print(f"mc28_shim: cannot read covers file: {e}", file=sys.stderr)
        return 2
    # pysweep_run's --limit is a unit cap; map it to the engine's cover cap so a
    # deliberately truncated probe is possible -- it makes the run PARTIAL, and
    # the engine banners that itself, which is exactly what we want.
    limit = int(opt("--limit")) if "--limit" in a else None

    idx = offset
    status_p = os.path.join(out, "STATUS")
    stats_p = os.path.join(out, f"mc28_stats_s{idx:02d}.tsv")

    with open(os.path.join(out, "GATE.md"), "w") as fh:
        fh.write(
            "n=6 j-tax hunt (v=28 supply-tight FOREST multi-covers, the\n"
            "(140,8,0,0,0) cell).  The supervisor's ALARM text is n=7\n"
            "boilerplate.  The CORRECT gate for anything this run produces:\n"
            "  cargo run --release -- validate -n 6 --file <f> --complete\n"
            "  python3 analysis/counting/m3_check.py <f>        (exit 2 = novel)\n"
            "  python3 pylib/verify_master.py 6 <f>             (exit 1 = THEORY ALARM)\n"
            "A product here is a j >= 1 complete n=6 walk of length <= 872 --\n"
            "a FIRST OF ITS SPECIES.  Nothing may be claimed before all three\n"
            "pass on the MAC (the PC has no Rust toolchain).\n")

    st = open(status_p, "a", buffering=1)
    mine = shard_covers(total_covers, shards, offset) if total_covers else 0
    ticks_total = max(1, (mine + tick - 1) // tick) if mine else 0

    if dry:
        st.write(f"{stamp()}\tDRYRUN\t0/1\tsizing only\n")
        st.write(f"{stamp()}\tDONE\tdry-run: shard {idx}/{shards}, "
                 f"{mine} covers, {ticks_total} ticks, n={n} tmax={tmax} "
                 f"v={v} splits={splits} jmin={jmin} forest={forest}\n")
        with open(stats_p, "w") as fh:
            fh.write("shard\tshards\tcovers_declared\tticks\tn\ttmax\tv\t"
                     "splits\tjmin\tforest\n")
            fh.write(f"{idx}\t{shards}\t{mine}\t{ticks_total}\t{n}\t{tmax}\t"
                     f"{v}\t{splits}\t{jmin}\t{int(forest)}\n")
        print(f"dry-run shard {idx}/{shards}: {mine} covers, "
              f"{ticks_total} ticks", flush=True)
        st.close()
        return 0

    # --- the heartbeat -------------------------------------------------------
    # run() looks `prepare` up in the module globals every time it processes a
    # selected multi-cover, so rebinding it here is enough and stays exact even
    # if the DFS around it changes.  ONE call == ONE processed cover.
    orig_prepare = M.prepare
    state = {"i": 0, "t": 0, "t0": time.time()}

    def traced(B, cov):
        state["i"] += 1
        if state["i"] % tick == 0:
            state["t"] += 1
            tt = ticks_total if ticks_total else state["t"]
            st.write(f"{stamp()}\tcover\t{state['t']}/{tt}\t"
                     f"{state['i']} covers, "
                     f"{time.time() - state['t0']:.0f}s\n")
        return orig_prepare(B, cov)

    M.prepare = traced
    rc, res = 0, None
    try:
        res = M.run(n, tmax, v, splits, jmin=jmin, stride=shards,
                    offset=offset, forest=forest, max_covers=limit,
                    covers_file=covers_file)
    except SystemExit as e:                # engine exits 3 on a cap hit
        rc = int(e.code or 0)
        st.write(f"{stamp()}\tCAPPED\trc={rc} -- PARTIAL, not a negative\n")
    except Exception as e:                                   # noqa: BLE001
        rc = 1
        st.write(f"{stamp()}\tERROR\t{type(e).__name__}: {e}\n")
        raise
    finally:
        M.prepare = orig_prepare
        secs = time.time() - state["t0"]

    # --- the alarm path: the engine does NOT banner a find; we must -----------
    finds = 0
    if res and res[0]:
        best, wit = res
        B = M.add_rot(M.build(n))
        start = B["PIDX"][tuple(range(1, n + 1))]
        lines = []
        for j in sorted(wit):
            cov, steps = wit[j]
            F = orig_prepare(B, cov)
            s2, _ = M.materialize(B, F, steps, start)
            fn = os.path.join(out, f"mc28-s{idx:02d}-j{j}-{best[j]}.txt")
            with open(fn, "w") as fh:
                fh.write(s2 + "\n")
            r = lib62.analyze_path(lib62.first_visit_path(s2, n), n)
            led = ("IMPURE/UNREADABLE" if r is None else
                   " ".join(f"{k}={r[k]}" for k in
                            ("length", "S", "splits", "D", "xp", "v", "j", "L")))
            finds += 1
            lines.append(f"{fn}  len={len(s2)}  [{led}]")
            # the supervisor's own escape channel -> ALARM.txt + STATUS banner
            st.write(f"{stamp()}\tESCAPE\tj={j} len={best[j]} file={fn}\n")
        with open(os.path.join(out, f"mc28-s{idx:02d}-FIND.txt"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
        # `*** ` is what the supervisor's stdout scan matches
        cell = ("the (140,8,0,0,0) supply-tight forest family"
                if (n, v, splits) == (6, 28, 20) else
                f"the supply-tight family v={v} splits={splits} at n={n}")
        print(f"*** MC28 FIND: shard {idx} produced {finds} completion(s) in "
              f"{cell} -- a j>={jmin} n={n} walk <= {tmax}"
              + (", FIRST OF ITS SPECIES" if (n, v, splits) == (6, 28, 20)
                 else " (NOTE: not the n=6 target cell -- alarm-path test?)")
              + " ***", flush=True)
        for ln in lines:
            print(f"*** {ln}", flush=True)
        print("*** STOP. Gate on the Mac: validate -n 6 --complete, "
              "m3_check.py, verify_master.py 6 (exit 1 = THEORY ALARM) ***",
              flush=True)

    # final tick row so the supervisor reads N/N rather than parking at 99%
    if ticks_total and state["t"] < ticks_total:
        st.write(f"{stamp()}\tcover\t{ticks_total}/{ticks_total}\t"
                 f"{state['i']} covers, {secs:.0f}s (final)\n")
    st.write(f"{stamp()}\tDONE\tshard {idx}/{shards}: {state['i']} covers, "
             f"{finds} finds, {secs:.1f}s, rc={rc}\n")
    with open(stats_p, "w") as fh:
        fh.write("shard\tshards\tcovers_done\tcovers_declared\tfinds\tsecs\trc\n")
        fh.write(f"{idx}\t{shards}\t{state['i']}\t{mine}\t{finds}"
                 f"\t{secs:.1f}\t{rc}\n")
    st.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
