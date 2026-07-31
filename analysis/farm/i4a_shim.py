#!/usr/bin/env python3
"""i4a_shim.py -- run `i4a_apply.py apply-sym` under the farm supervisor's
contract (--shard i/N, --out, STATUS heartbeat), without modifying i4a_apply.

Sharding.  i4a_apply.run_apply_sym() takes DIRS and does its own
`sorted(f for f in os.listdir(d) if f.endswith('.txt'))`, so there is no file
list to slice from outside.  Rather than copy ~920 files per shard, the shim
wraps `os.listdir` for the corpus dir ONLY and returns this shard's
round-robin slice (`files[i::k]`, the same rule demotion.gather() uses, so
shard splits are consistent across instruments).  Every other listdir call is
passed through untouched.

Heartbeat.  i4a_apply prints one progress line per 2,000 walks -- far too
coarse for the 5-minute stall flag -- so the shim wraps
`i4a_apply.first_visit_path`, which fires exactly once per (file,
orientation).  The declared total is therefore 2 x len(shard files), computed
directly and exactly: no presize pass needed.

usage: upyw.exe -u i4a_shim.py apply-sym --shard 0/24 --out F:\\...\\s00
                                         [--dirs data/upstream872] [--only fwd]
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
import i4a_apply as I  # noqa: E402


def main():
    a = sys.argv[1:]

    def opt(name, d=None):
        return a[a.index(name) + 1] if name in a else d

    out = opt("--out")
    if not out:
        print("i4a_shim: --out is required", file=sys.stderr)
        return 2
    dirs = opt("--dirs", "data/upstream872").split(",")
    only = opt("--only")
    only = only.split(",") if only else None
    shard = None
    if "--shard" in a:
        i, k = opt("--shard").split("/")
        shard = (int(i), int(k))
    limit = int(opt("--limit")) if "--limit" in a else None
    dry = "--dry-run" in a
    os.makedirs(out, exist_ok=True)
    sidx = shard[0] if shard else 0

    # --- exact shard file list (same round-robin rule as demotion.gather) ---
    absdirs = {os.path.abspath(d) for d in dirs}
    picked = {}
    for d in dirs:
        txt = sorted(f for f in os.listdir(d) if f.endswith(".txt"))
        if shard:
            txt = txt[shard[0]::shard[1]]
        if limit:
            txt = txt[:limit]
        picked[os.path.abspath(d)] = set(txt)
    nfiles = sum(len(v) for v in picked.values())
    total = 2 * nfiles

    status_p = os.path.join(out, "STATUS")
    stats_p = os.path.join(out, f"i4a_stats_s{sidx:02d}.tsv")
    st = open(status_p, "a", buffering=1)

    def stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    if dry:
        st.write(f"{stamp()}\tDRYRUN\t0/{total}\tsizing only\n")
        st.write(f"{stamp()}\tDONE\tdry-run: {nfiles} walks, {total} orientations\n")
        with open(stats_p, "w") as fh:
            fh.write("shard\twalks\torientations\n")
            fh.write(f"{sidx}\t{nfiles}\t{total}\n")
        print(f"dry-run shard {sidx}: {nfiles} walks, {total} orientations")
        return 0

    real_listdir = os.listdir

    def sharded_listdir(p):
        ap = os.path.abspath(p)
        if ap in absdirs and ap in picked:
            keep = picked[ap]
            return [f for f in real_listdir(p) if f in keep]
        return real_listdir(p)

    orig_fvp = I.first_visit_path
    state = {"i": 0, "t0": time.time()}

    def traced(txt, nn):
        state["i"] += 1
        st.write(f"{stamp()}\twalk\t{state['i']}/{total}\t"
                 f"{state['i'] * 100 // max(total, 1)}%\n")
        return orig_fvp(txt, nn)

    os.listdir = sharded_listdir
    I.first_visit_path = traced
    rc = 0
    try:
        rc = I.run_apply_sym(dirs, out, only) or 0
    except Exception as e:                                   # noqa: BLE001
        rc = 1
        st.write(f"{stamp()}\tERROR\t{type(e).__name__}: {e}\n")
        raise
    finally:
        os.listdir = real_listdir
        I.first_visit_path = orig_fvp
        secs = time.time() - state["t0"]
        st.write(f"{stamp()}\tDONE\tshard {sidx}: {state['i']}/{total} "
                 f"orientations, {secs:.1f}s, rc={rc}\n")
        with open(stats_p, "w") as fh:
            fh.write("shard\twalks\torientations_done\torientations_total"
                     "\tsecs\trc\n")
            fh.write(f"{sidx}\t{nfiles}\t{state['i']}\t{total}\t{secs:.1f}\t{rc}\n")
        st.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
