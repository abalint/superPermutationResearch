#!/usr/bin/env python3
"""Chain cover search via the C DLX engine, then compile+verify.

usage: python3 solve_dlx.py <chains.jsonl|std> <index> <tl_s> [seed] [forest]
exit: 0 validated word; 2 exhausted (no rooted cover); 3 timeout; 4 compile fail.
"""
import json
import os
import subprocess
import sys
from collections import Counter

import gain1
import chain7
from chain7 import build_instance_from_chain, compile_chain_cover, standard_chain

HERE = os.path.dirname(os.path.abspath(__file__))


def export_instance(inst):
    rows = inst["rows"]
    col_index = {c: i for i, c in enumerate(inst["columns"])}
    loop_ids = {}
    for r in rows:
        loop_ids.setdefault(r["loop"], len(loop_ids))
    lines = [f"{len(col_index)} {len(rows)} {len(loop_ids)} 5"]
    roots = inst["roots"]
    for r in rows:
        po = r["parent_orbit"]
        pc = -1 if po in roots else col_index[po]
        ch = " ".join(str(col_index[c]) for c in r["children"])
        lines.append(f"{loop_ids[r['loop']]} {pc} {ch}")
    return "\n".join(lines) + "\n"


def seed_row_ids(inst, cert_path):
    from certificate import parse_loop
    cert = json.load(open(cert_path))
    rid_of = {(r["loop"], r["entry"]): i for i, r in enumerate(inst["rows"])}
    out = []
    for r in cert["rows"]:
        rid = rid_of.get((parse_loop(r["loop"], 7), r["entry_perm"]))
        if rid is not None:
            out.append(rid)
    return out


def main():
    src, idx = sys.argv[1], int(sys.argv[2])
    tl = float(sys.argv[3])
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    forest = sys.argv[5] if len(sys.argv) > 5 else "1"
    seedcert = sys.argv[6] if len(sys.argv) > 6 else "cert5907_5907-504778e6.json"
    eps = sys.argv[7] if len(sys.argv) > 7 else "3"
    if src == "std":
        sol = standard_chain()
        tag = "std"
    else:
        with open(src) as fh:
            rec = json.loads([l for l in fh][idx])
        sol = [tuple(x) for x in rec["chain"]]
        tag = f"{os.path.basename(src).replace('.jsonl','')}_{idx}"
    inst = build_instance_from_chain(sol)
    m = inst["meta"]
    print(f"[{tag}] K={m['K']} Sigma={m['Sigma']} V={m['V']} R={m['R']} "
          f"cols={len(inst['columns'])} rows={len(inst['rows'])}", flush=True)

    DLXBIN = os.path.join(HERE, "dlx7.exe" if os.name == "nt" else "dlx7")
    cmd = [DLXBIN, str(seed), str(tl), forest]
    if seedcert and seedcert != "none":
        prefs = seed_row_ids(inst, seedcert)
        pref_fn = os.path.abspath(f"pref_{tag}.txt")
        with open(pref_fn, "w") as fh:
            fh.write("\n".join(map(str, prefs)) + "\n")
        print(f"[{tag}] pref rows from {seedcert}: {len(prefs)}", flush=True)
        cmd += ["0", pref_fn, eps]
        if len(sys.argv) > 8:
            cmd += [sys.argv[8]]  # fixed attempt node cap
    proc = subprocess.run(cmd, input=export_instance(inst),
                          capture_output=True, text=True)
    sys.stderr.write(proc.stderr)
    lines = proc.stdout.strip().splitlines()
    verdict = lines[0] if lines else "NOOUTPUT"
    if verdict == "EXHAUSTED":
        print(f"[{tag}] EXHAUSTED: no {'rooted ' if forest=='1' else ''}cover "
              f"exists", flush=True)
        sys.exit(2)
    if verdict != "SOLVED":
        print(f"[{tag}] {verdict}", flush=True)
        sys.exit(3)
    ids = [int(x) for x in lines[1:]]
    chosen = [inst["rows"][i] for i in ids]
    rep = gain1.check_cover(inst, chosen)
    print(f"[{tag}] SOLVED {len(ids)} rows; check_cover valid={rep['valid']}",
          flush=True)
    if not rep["valid"]:
        print(f"[{tag}] engine returned invalid cover (bug!)", flush=True)
        sys.exit(4)
    if forest == "0":
        print(f"[{tag}] exact cover exists (forest not enforced); done",
              flush=True)
        sys.exit(0)
    try:
        word, cert, costs = compile_chain_cover(inst, chosen)
    except Exception as exc:
        print(f"[{tag}] compile FAILED: {exc!r}", flush=True)
        with open(f"failed_cover_{tag}.json", "w") as fh:
            json.dump({"chain": sol, "row_ids": ids,
                       "entries": [r["entry"] for r in chosen]}, fh)
        sys.exit(4)
    L = len(word)
    assert gain1.verify_word(word, 7), "internal word verification failed"
    base = f"candidate_{L}_{tag}"
    with open(base + ".txt", "w") as fh:
        fh.write(word)
    with open(base + ".cert.json", "w") as fh:
        json.dump(cert, fh)
    with open(base + ".cover.json", "w") as fh:
        json.dump({"chain": sol, "meta": m,
                   "entries": [r["entry"] for r in chosen]}, fh)
    hist = Counter(costs)
    print(f"[{tag}] SUCCESS length={L} -> {base}.txt "
          f"costs={dict(sorted(hist.items()))}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
