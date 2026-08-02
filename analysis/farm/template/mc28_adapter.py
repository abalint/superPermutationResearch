#!/usr/bin/env python3
"""mc28_adapter.py -- the s63 v=28 supply-tight FOREST multi-cover branch, as a
farm adapter (s64 P5).  Port of the 356-line `analysis/farm/mc28_shim.py`.

Everything generic moved out: the STATUS contract is `pylib/farmstatus.py`, the
farm-vs-checkout layout probe is `farmlayout.py`, and the launch/gate/parity
prose is `configs/mc28.conf` + `template/README.md`.  What is left is the two
things that are genuinely about THIS instrument:

 1. ARG SHAPE.  `mcover_search.py` reads `n`/`TMAX` POSITIONALLY and shards by
    `--stride/--offset`; the supervisor supplies `--shard i/N` and appends
    ExtraArgs at the END, so `int(argv[1])` would be `int("--shard")` and all
    shards would die at once.  Translated below.
    `--covers-file` is REQUIRED for a real run: sharding the ENUMERATION would
    make every shard re-walk the whole forest tree (N x the enumeration for 1 x
    the search).  A `--dry-run` may size from `--total-covers` instead -- that
    is exactly what the s63 `mc28dry2` smoke did, and a dry shard processes
    nothing, so the guarantee is untouched.

 2. THE ALARM IS OURS.  The engine does NOT banner a find: a completion prints
    `MIN LENGTH BY j in this multi-cover family:`, which matches NOTHING in the
    supervisor's stdout scan.  So the banner, the ESCAPE row, the
    materialization and the lib62 ledger re-read are this file's job.
    (The engine's own `*** PARTIAL (cap hit)` and `*** NOT SUPPLY-TIGHT` DO
    match, and both SHOULD alarm.)

The heartbeat rebinds `mcover_search.prepare`, which `run()` resolves through
module globals per processed cover -- so ONE call == ONE cover, the engine
source is untouched, and the tick cannot drift from the real cover stream.
"""
import os
import sys

import farmlayout

farmlayout.add_pylib()
from farmstatus import FarmStatus, banner, safe_print, shard_slice_size  # noqa: E402

import mcover_search as M          # noqa: E402
import lib62                       # noqa: E402

GATE_DEFAULT = """\
n=6 j-tax hunt (v=28 supply-tight FOREST multi-covers, the (140,8,0,0,0) cell).
The supervisor's ALARM text is n=7 boilerplate.  The CORRECT gate here:
  cargo run --release -- validate -n 6 --file <f> --complete
  python3 analysis/counting/m3_check.py <f>        (exit 2 = novel)
  python3 pylib/verify_master.py 6 <f>             (exit 1 = THEORY ALARM)
A product is a j >= 1 complete n=6 walk of length <= 872 -- a FIRST OF ITS
SPECIES.  Nothing may be claimed before all three pass on the MAC (the PC has
no Rust toolchain).
"""


def self_test():
    """Partition + engine smoke, no farm needed.  n=5 (v=7,splits=4) is the
    designed-SAT multi-cover control of out/s63/mcover/REPORT.md §3.3."""
    import tempfile
    ok = True
    tot, shards = 224, 7
    s = sum(shard_slice_size(tot, shards, o) for o in range(shards))
    print(f"partition: sum over {shards} offsets = {s} (want {tot})")
    ok &= (s == tot)
    seen = []
    for o in range(shards):
        got = [k for k in range(tot) if k % shards == o]
        seen += got
        ok &= (len(got) == shard_slice_size(tot, shards, o))
    ok &= (sorted(seen) == list(range(tot)))
    print(f"disjoint+complete over indices: {sorted(seen) == list(range(tot))}")
    cf = os.path.join(tempfile.mkdtemp(), "n5covers.txt")
    M.run(5, 154, 7, 4, jmin=0, emit_covers=cf)
    res = M.run(5, 154, 7, 4, jmin=0, stride=7, offset=0, covers_file=cf)
    print(f"engine smoke (n=5 v=7 splits=4 shard 0/7 via covers-file): "
          f"best={res[0]}")
    ok &= bool(res[0])
    full = M.run(5, 154, 7, 4, jmin=0, covers_file=cf)
    direct = M.run(5, 154, 7, 4, jmin=0)
    ok &= (full[0] == direct[0])
    print(f"emit->consume == enumeration: {full[0] == direct[0]}")
    print("SELF-TEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    # a leading bare token would be pysweep_run.ps1's -Mode; this instrument
    # has no subcommand, so drop one rather than letting the parse choke
    if a and not a[0].startswith("-"):
        del a[0]
    if "--self-test" in a:
        return self_test()

    def opt(name, d=None):
        return a[a.index(name) + 1] if name in a else d

    out = opt("--out")
    if not out:
        print("mc28_adapter: --out is required", file=sys.stderr)
        return 2
    shard, shards = 0, 1
    if "--shard" in a:
        i, k = opt("--shard").split("/")
        shard, shards = int(i), int(k)
    n = int(opt("-n", "6"))
    tmax = int(opt("--tmax", "872"))
    v = int(opt("--v", "28"))
    splits = int(opt("--splits", "20"))
    jmin = int(opt("--jmin", "1"))
    tick = max(1, int(opt("--tick", "200")))
    total_covers = int(opt("--total-covers", "0"))
    covers_file = opt("--covers-file")
    forest = "--forest" in a
    dry = "--dry-run" in a
    limit = int(opt("--limit")) if "--limit" in a else None

    if not covers_file and not dry:
        print("mc28_adapter: --covers-file is REQUIRED for a real run "
              "(enumeration sharding would re-walk the whole tree in every "
              "shard)", file=sys.stderr)
        return 2
    if covers_file:
        if not os.path.isfile(covers_file):
            print(f"mc28_adapter: covers file not found: {covers_file}",
                  file=sys.stderr)
            return 2
        try:
            # the file's own declared total beats any operator-supplied number
            _h, _n, _ok, _sg, _sw, _decl = M.read_covers(covers_file)
        except Exception as e:                                # noqa: BLE001
            print(f"mc28_adapter: cannot read covers file: {e}",
                  file=sys.stderr)
            return 2
        if not _ok:
            print(f"mc28_adapter: covers file FAILED verification "
                  f"(lines={_n} declared={_decl} sha={_sg} want={_sw})",
                  file=sys.stderr)
            return 4
        total_covers = _decl or total_covers

    mine = shard_slice_size(total_covers, shards, shard)
    st = FarmStatus(out, shard=shard, shards=shards, total_units=mine,
                    tick=tick, label="cover")
    st.gate_md(farmlayout.text_asset("mc28.gate.md", GATE_DEFAULT))

    if dry:
        summary = (f"shard {shard}/{shards}, {mine} covers, "
                   f"{st.declared_rows} ticks, n={n} tmax={tmax} v={v} "
                   f"splits={splits} jmin={jmin} forest={forest}")
        rc = st.finish_dry(summary)
        safe_print(f"dry-run shard {shard}/{shards}: {mine} covers, "
                   f"{st.declared_rows} ticks")
        st.close()
        return rc

    # --- the heartbeat: ONE prepare() call == ONE processed cover ------------
    orig_prepare = M.prepare

    def traced(B, cov):
        st.work()
        return orig_prepare(B, cov)

    M.prepare = traced
    rc, res = 0, None
    try:
        res = M.run(n, tmax, v, splits, jmin=jmin, stride=shards,
                    offset=shard, forest=forest, max_covers=limit,
                    covers_file=covers_file)
    except SystemExit as e:                 # engine exits 3 on a cap hit
        rc = int(e.code or 0)
        st.row("CAPPED", f"rc={rc} -- PARTIAL, not a negative")
    except Exception as e:                                    # noqa: BLE001
        rc = 1
        st.row("ERROR", f"{type(e).__name__}: {e}")
        st.close()
        raise
    finally:
        M.prepare = orig_prepare

    # --- the alarm path: the engine does NOT banner a find; we must ----------
    finds = 0
    if res and res[0]:
        best, wit = res
        B = M.add_rot(M.build(n))
        start = B["PIDX"][tuple(range(1, n + 1))]
        lines = []
        for j in sorted(wit):
            cov, steps = wit[j]
            s2, _ = M.materialize(B, orig_prepare(B, cov), steps, start)
            fn = st.product(f"mc28-s{shard:02d}-j{j}-{best[j]}.txt", s2)
            r = lib62.analyze_path(lib62.first_visit_path(s2, n), n)
            led = ("IMPURE/UNREADABLE" if r is None else
                   " ".join(f"{k}={r[k]}" for k in
                            ("length", "S", "splits", "D", "xp", "v", "j", "L")))
            finds += 1
            lines.append(f"{fn}  len={len(s2)}  [{led}]")
            st.escape(f"j={j} len={best[j]} file={fn}")
        st.product(f"mc28-s{shard:02d}-FIND.txt", "\n".join(lines))
        cell = ("the (140,8,0,0,0) supply-tight forest family"
                if (n, v, splits) == (6, 28, 20) else
                f"the supply-tight family v={v} splits={splits} at n={n}")
        banner(f"MC28 FIND: shard {shard} produced {finds} completion(s) in "
               f"{cell} -- a j>={jmin} n={n} walk <= {tmax}"
               + (", FIRST OF ITS SPECIES" if (n, v, splits) == (6, 28, 20)
                  else " (NOTE: not the n=6 target cell -- alarm-path test?)"))
        for ln in lines:
            banner(ln)
        banner("STOP. Gate on the Mac: validate -n 6 --complete, m3_check.py, "
               "verify_master.py 6 (exit 1 = THEORY ALARM)")

    st.finish(finds=finds, rc=rc)
    st.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
