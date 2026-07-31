#!/usr/bin/env python3
"""promote_shim.py -- run the s51 PROMOTION hunt (`demotion.py promote`) under
the untargeted farm supervisor's contract, WITHOUT modifying demotion.py.

Why a shim at all.  The supervisor launches every shard as

    upyw.exe -u <TARGET> <Mode> --shard i/N --out <dir> [--limit K] [--dry-run]

and demotion.py cannot be that TARGET directly, for two reasons:

 1. ARG SHAPE.  demotion.py reads positionally -- mode=a[0], n=int(a[1]),
    dirs=a[2] -- so it needs `promote 6 data/upstream872` in slots 0..2.  The
    supervisor's only injection point (ExtraArgs) appends at the END, so
    int(a[1]) would be int("--shard") and all 24 shards would die instantly.
    This shim accepts the supervisor's shape and supplies the positionals.

 2. NO HEARTBEAT.  Progress and the 5-minute stall flag are read from
    <out>/STATUS -- one appended line per unit of work.  demotion.py writes
    edges.tsv and stdout banners, never a STATUS file, so without this shim
    every shard would report 0 progress and be flagged STALLED after 5 min.

What does NOT need shimming (verified against untargeted_super.ps1):
 * the ALARM path already works -- demotion.py prints `*** NOVEL-CANDIDATE ...`
   and `*** DEGENERATE-DROP NOVEL ...` with flush=True, and the supervisor's
   stdout scan matches on `\\*\\*\\*`.
 * edges.tsv is already picked up by the supervisor's `(?i)edge` TSV counter.

STATUS line format (must match untargeted_super.ps1's parser exactly):
    <ts>\\t<label>\\t<i>/<n>\\t<note>      progress; the regex needs the
                                          TRAILING tab, and <n> is the shard's
                                          own declared total ("the instrument's
                                          own declared total always wins")
    <ts>\\tDONE\\t<summary>                terminal

CAVEAT for the operator: the supervisor's ALARM banner text is hardcoded for
n=7 ("validate -n 7", "m3_check.py -n 7").  This is an n=6 hunt -- the correct
gate for anything this run produces is
    cargo run --release -- validate -n 6 --file <f> --complete
    python3 analysis/counting/m3_check.py <f>            (exit 2 = novel)
The shim writes the right commands into GATE.txt in its own out dir.

usage: upyw.exe -u promote_shim.py promote --shard 0/24 --out F:\\...\\s00
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# demotion.py lives in the repo mirror; the shim ships next to the harness.
for cand in (os.path.join(HERE, "repo", "analysis", "counting", "s51"),
             os.path.join(HERE, "..", "counting", "s51")):
    if os.path.isdir(cand):
        sys.path.insert(0, os.path.abspath(cand))
        break
import demotion as D  # noqa: E402


def main():
    a = sys.argv[1:]
    # a leading bare token is the supervisor's $Mode ("promote"); tolerate it
    mode = a[0] if a and not a[0].startswith("--") else "promote"

    def opt(name, d=None):
        return a[a.index(name) + 1] if name in a else d

    out = opt("--out")
    if not out:
        print("promote_shim: --out is required", file=sys.stderr)
        return 2
    shard = None
    if "--shard" in a:
        i, k = opt("--shard").split("/")
        shard = (int(i), int(k))
    limit = int(opt("--limit")) if "--limit" in a else None
    w_from = int(opt("--w-from", "4"))
    n = int(opt("-n", "6"))
    dirs = opt("--dirs", "data/upstream872").split(",")
    dry = "--dry-run" in a
    os.makedirs(out, exist_ok=True)

    idx = shard[0] if shard else 0
    status_p = os.path.join(out, "STATUS")
    stats_p = os.path.join(out, f"promote_stats_s{idx:02d}.tsv")

    # the exact unit list for THIS shard -- demotion.gather() is the same
    # function run() uses, so the declared total can never drift from reality
    files = D.gather(dirs, None, limit, shard)
    total = 2 * len(files)          # first_visit_path fires once per orientation

    with open(os.path.join(out, "GATE.txt"), "w") as fh:
        fh.write("n=6 promotion hunt -- the supervisor's ALARM text is n=7 "
                 "boilerplate. The CORRECT gate for products here:\n"
                 "  cargo run --release -- validate -n 6 --file <f> --complete\n"
                 "  python3 analysis/counting/m3_check.py <f>   (exit 2 = novel)\n"
                 "Every product .txt in this dir is a NOVEL 872 by construction "
                 "(s51: no known 872 can be a promotion product) -- gate it "
                 "anyway, per the M3 ritual.\n")

    st = open(status_p, "a", buffering=1)

    def stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    if dry:
        st.write(f"{stamp()}\tDRYRUN\t0/{total}\tsizing only\n")
        st.write(f"{stamp()}\tDONE\tdry-run: {len(files)} walks, "
                 f"{total} orientations\n")
        with open(stats_p, "w") as fh:
            fh.write("shard\twalks\torientations\tmode\n")
            fh.write(f"{idx}\t{len(files)}\t{total}\t{mode}\n")
        print(f"dry-run shard {idx}: {len(files)} walks, {total} orientations")
        return 0

    # --- the heartbeat: wrap the per-orientation entry point -----------------
    # demotion.py did `from loop_ledger_probe import first_visit_path`, so the
    # name it calls resolves through demotion's module globals at call time --
    # rebinding it here is enough, and it stays exact even if the loop changes.
    orig = D.first_visit_path
    state = {"i": 0, "t0": time.time()}

    def traced(txt, nn):
        state["i"] += 1
        st.write(f"{stamp()}\twalk\t{state['i']}/{total}\t"
                 f"{state['i'] * 100 // max(total, 1)}%\n")
        return orig(txt, nn)

    D.first_visit_path = traced
    rc = 0
    try:
        D.run(mode, n, dirs, None, out, w_from, limit, shard, [], False)
    except Exception as e:                                   # noqa: BLE001
        rc = 1
        st.write(f"{stamp()}\tERROR\t{type(e).__name__}: {e}\n")
        raise
    finally:
        D.first_visit_path = orig
        secs = time.time() - state["t0"]
        prods = len([f for f in os.listdir(out) if f.endswith(".txt")
                     and (f.startswith("demo-") or f.startswith("drop-")
                          or f.startswith("prod-"))])
        st.write(f"{stamp()}\tDONE\tshard {idx}: {state['i']}/{total} "
                 f"orientations, {prods} product files, {secs:.1f}s, rc={rc}\n")
        with open(stats_p, "w") as fh:
            fh.write("shard\twalks\torientations_done\torientations_total"
                     "\tproduct_files\tsecs\trc\n")
            fh.write(f"{idx}\t{len(files)}\t{state['i']}\t{total}\t{prods}"
                     f"\t{secs:.1f}\t{rc}\n")
        st.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
