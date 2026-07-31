#!/usr/bin/env python3
"""lswap_shim.py -- run `loopswap_apply.py apply-sym` under the farm
supervisor's contract (--shard i/N, --out, STATUS heartbeat), without
modifying loopswap_apply.

Sharding is BY RULE, which s45 established is exact: canonical rules have
disjoint relabeled-instance sets, so splitting the rule table and unioning the
per-shard edge TSVs reproduces the unsharded result. The shim writes this
shard's rule rows to <out>/rules_shard.tsv (round-robin over data rows) and
hands that file to run_apply_sym via its existing --rules path -- no internals
touched for the split itself.

Heartbeat.  loopswap_apply prints NOTHING between its setup lines and the
final summary, so a shard would be flagged STALLED at 5 min.  The shim wraps
`loopswap_apply.replay_ids` -- the id-based fast path the apply-sym hot loop
actually calls -- and emits a STATUS row every --beat calls.  (Wrapping
`replay`, which the module also imports, counts ZERO: verified.)  The row's
`i/n` is in ROW units, because the supervisor tallies rows, not replays.

The declared total.  The supervisor treats the `i/n` field as truth, so n must
be real.  Candidate counts are only knowable by running the instrument's own
--dry-run, which the shim therefore does FIRST unless --no-presize is given.
Cost is one extra index build per shard (~2-4 min at n=6); on a big sweep that
is amortised, on a tiny one pass --no-presize and accept the supervisor's
even-split fallback.

usage: upyw.exe -u lswap_shim.py apply-sym --shard 0/24 --out F:\\...\\s00
                --rules data/loopswap/rules_n6_a360.tsv [--dirs data/upstream872]
                [--beat 20000] [--no-presize] [-n 6]
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(HERE, "repo", "analysis", "counting"),
             os.path.join(HERE, "..", "counting")):
    if os.path.isdir(cand):
        sys.path.insert(0, os.path.abspath(cand))
        break
import loopswap_apply as L  # noqa: E402


def main():
    a = sys.argv[1:]

    def opt(name, d=None):
        return a[a.index(name) + 1] if name in a else d

    out = opt("--out")
    rules = opt("--rules")
    if not out or not rules:
        print("lswap_shim: --out and --rules are required", file=sys.stderr)
        return 2
    n = int(opt("-n", "6"))
    dirs = opt("--dirs", "data/upstream872").split(",")
    beat = int(opt("--beat", "20000"))
    presize = "--no-presize" not in a
    dry = "--dry-run" in a
    shard = None
    if "--shard" in a:
        i, k = opt("--shard").split("/")
        shard = (int(i), int(k))
    os.makedirs(out, exist_ok=True)
    sidx = shard[0] if shard else 0

    # --- split the rule table (exact per s45: disjoint instance sets) -------
    with open(rules) as fh:
        lines = fh.read().splitlines()
    header, rows = lines[0], [r for r in lines[1:] if r.strip()]
    mine = rows[shard[0]::shard[1]] if shard else rows
    shard_rules = os.path.join(out, "rules_shard.tsv")
    with open(shard_rules, "w") as fh:
        fh.write(header + "\n")
        for r in mine:
            fh.write(r + "\n")

    status_p = os.path.join(out, "STATUS")
    stats_p = os.path.join(out, f"lswap_stats_s{sidx:02d}.tsv")
    st = open(status_p, "a", buffering=1)

    def stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    if not mine:
        st.write(f"{stamp()}\tDONE\tshard {sidx}: no rules in this shard\n")
        with open(stats_p, "w") as fh:
            fh.write("shard\trules\tcandidates\tsecs\trc\n")
            fh.write(f"{sidx}\t0\t0\t0.0\t0\n")
        st.close()
        print(f"shard {sidx}: no rules, nothing to do")
        return 0

    # --- presize: the instrument's own dry-run gives the exact candidate count
    total = 0
    if dry or presize:
        t0 = time.time()
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            L.run_apply_sym(n, shard_rules, dirs, os.path.join(out, "_dry"),
                            dry_run=True)
        for line in buf.getvalue().splitlines():
            # the bare `replayed: N` line is the TOTAL; `replayed:<rid>: N`
            # are per-rule. Summing both double-counts -- take the bare one.
            if line.startswith("replayed: "):
                total = int(line.split(": ", 1)[1])
        # NB: deliberately NO `i/n` field here -- the supervisor's progress
        # regex matches any `\t<d>/<d>\t` and would take this line's total
        # (in REPLAY units) as declTotal until the first real row overwrote
        # it. Keep presize out of the progress channel entirely.
        st.write(f"{stamp()}\tPRESIZE\t{len(mine)} rules, {total} candidates, "
                 f"{time.time() - t0:.1f}s\n")
        if dry:
            st.write(f"{stamp()}\tDONE\tdry-run: {len(mine)} rules, "
                     f"{total} candidates\n")
            with open(stats_p, "w") as fh:
                fh.write("shard\trules\tcandidates\n")
                fh.write(f"{sidx}\t{len(mine)}\t{total}\n")
            print(f"dry-run shard {sidx}: {len(mine)} rules, {total} candidates")
            st.close()
            return 0

    # The seam is `replay_ids`, NOT `replay`.  loopswap_apply imports both
    # (`replay` from i4a_apply) but the apply-sym hot loop calls the id-based
    # fast path `replay_ids(f2, d2, st, n, TUP, ROT, G)`.  Wrapping `replay`
    # counts ZERO and the heartbeat never fires -- which means every shard
    # gets flagged STALLED at 5 min.  Verified against the instrument's own
    # `replayed:<rid>` counter on the specimens corpus.
    orig_replay = L.replay_ids
    state = {"i": 0, "beat": 0, "rows": 0, "t0": time.time()}

    # UNITS.  The supervisor counts PROGRESS ROWS (`$st.lines++` per matching
    # line) but takes the total from the line's own `i/n` field -- so n must be
    # in ROWS too, not replays.  Emitting `replays/total_replays` with
    # --beat 50 made a finished run read "50/2462 (2%)".  Both sides are rows.
    total_rows = max(1, -(-total // beat)) if total > 0 else 0

    def traced(*args, **kw):
        state["i"] += 1
        state["beat"] += 1
        if state["beat"] >= beat:
            state["beat"] = 0
            state["rows"] += 1
            st.write(f"{stamp()}\treplay\t{state['rows']}/{total_rows}\t"
                     f"{state['i']} replays\n")
        return orig_replay(*args, **kw)

    L.replay_ids = traced
    rc = 0
    try:
        L.run_apply_sym(n, shard_rules, dirs, out)
    except Exception as e:                                   # noqa: BLE001
        rc = 1
        st.write(f"{stamp()}\tERROR\t{type(e).__name__}: {e}\n")
        raise
    finally:
        L.replay_ids = orig_replay
        secs = time.time() - state["t0"]
        st.write(f"{stamp()}\tDONE\tshard {sidx}: {len(mine)} rules, "
                 f"{state['i']} replays, {secs:.1f}s, rc={rc}\n")
        with open(stats_p, "w") as fh:
            fh.write("shard\trules\tcandidates_presized\treplays_done"
                     "\tsecs\trc\n")
            fh.write(f"{sidx}\t{len(mine)}\t{total}\t{state['i']}"
                     f"\t{secs:.1f}\t{rc}\n")
        st.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
