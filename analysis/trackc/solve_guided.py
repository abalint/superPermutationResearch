#!/usr/bin/env python3
"""Track C guided-DLX driver: run dlx7g, then compile + validate.

Mirrors analysis/cover7/solve_dlx.py but drives the guided engine
(analysis/trackc/dlx7g) and refuses to report success unless the Rust
validator accepts the compiled word.

usage:
  solve_guided.py <instance>            # a name under data/trackc/instances,
                                        # or a path to an instance .txt
  solve_guided.py --chains f.jsonl --index 3
  solve_guided.py n6std --weights w.txt --time-limit 600 --epsilon 0.05 --seed 2

exit: 0 validated (or verified cover when --no-compile); 2 exhausted;
      3 timeout; 4 compile/validate failure; 1 usage/setup error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPR = os.path.dirname(os.path.dirname(HERE))           # .../superPermutationResearch
EX = os.path.join(os.path.dirname(SPR), "extraDocs",
                  "superpermutation-examples", "scripts")
COVER7 = os.path.join(SPR, "analysis", "cover7")
INSTDIR = os.path.join(SPR, "data", "trackc", "instances")

for p in (EX, COVER7):
    if p not in sys.path:
        sys.path.insert(0, p)

import gain1                                            # noqa: E402
import chain7                                           # noqa: E402
from chain7 import build_instance_from_chain, compile_chain_cover, standard_chain  # noqa: E402
from certificate import compile_certificate             # noqa: E402


# --------------------------------------------------------------- instance io
def export_instance(inst: dict) -> str:
    """Text instance format consumed by dlx7g (row id == index in inst.rows)."""
    rows = inst["rows"]
    nchild = inst["n"] - 2
    col_index = {c: i for i, c in enumerate(inst["columns"])}
    loop_ids: dict = {}
    for r in rows:
        loop_ids.setdefault(r["loop"], len(loop_ids))
    lines = [f"{len(col_index)} {len(rows)} {len(loop_ids)} {nchild}"]
    roots = inst["roots"]
    for r in rows:
        po = r["parent_orbit"]
        pc = -1 if po in roots else col_index[po]
        ch = " ".join(str(col_index[c]) for c in r["children"])
        lines.append(f"{loop_ids[r['loop']]} {pc} {ch}")
    return "\n".join(lines) + "\n"


def instance_from_chain(chain) -> dict:
    sol = [tuple(x) for x in chain]
    return build_instance_from_chain(sol)


def resolve_instance(args) -> tuple[str, dict, str]:
    """-> (tag, python instance dict, path of the instance .txt used).

    The engine reads a text file; row ids are line order.  We always
    regenerate the text from the Python instance and cross-check it against
    any on-disk file, so a row-id mapping mismatch is loud, never silent.
    """
    if args.chains:
        with open(args.chains) as fh:
            rec = json.loads([ln for ln in fh][args.index])
        inst = instance_from_chain(rec["chain"])
        tag = f"{os.path.basename(args.chains).replace('.jsonl', '')}_{args.index}"
        return tag, inst, None

    spec = args.instance
    if spec is None:
        raise SystemExit("need an <instance> or --chains/--index")
    if os.path.sep in spec or spec.endswith(".txt"):
        path = os.path.abspath(spec)
    else:
        path = os.path.join(INSTDIR, spec + ".txt")
    if not os.path.exists(path):
        raise SystemExit(f"no such instance file: {path}")
    meta_path = path[:-4] + ".meta.json"
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    tag = meta.get("tag") or os.path.basename(path)[:-4]
    src = meta.get("source", "")

    inst = None
    if src.startswith("gain1.build_instance("):
        n = int(src[len("gain1.build_instance("):-1])
        inst = gain1.build_instance(n)
    elif src.startswith("chain7.standard_chain"):
        inst = build_instance_from_chain(standard_chain())
    elif ".jsonl" in src:
        # e.g. "analysis/cover7/chains_V15_s14.jsonl K=27 entry 0"
        parts = src.split()
        jsonl = parts[0]
        if not os.path.isabs(jsonl):
            jsonl = os.path.join(SPR, jsonl)
        K = None
        idx = 0
        for p in parts[1:]:
            if p.startswith("K="):
                K = int(p[2:])
            elif p.isdigit():
                idx = int(p)
        recs = [json.loads(ln) for ln in open(jsonl)]
        if K is not None:
            recs = [r for r in recs if r.get("K") == K]
        inst = instance_from_chain(recs[idx]["chain"])
    if inst is None:
        raise SystemExit(
            f"cannot rebuild the Python instance for {tag} "
            f"(meta source={src!r}); pass --chains/--index instead")

    text = export_instance(inst)
    with open(path) as fh:
        on_disk = fh.read()
    if text.split() != on_disk.split():
        raise SystemExit(
            f"REFUSING TO RUN: regenerated instance for {tag} does not match "
            f"{path}; row ids would be mis-mapped")
    return tag, inst, path


# ------------------------------------------------------------------- engine
def run_engine(inst_path: str, args, out_path: str) -> tuple[int, str]:
    exe = os.path.join(HERE, "dlx7g")
    if not os.path.exists(exe):
        raise SystemExit(f"engine not built: {exe} (run make in {HERE})")
    cmd = [exe, inst_path, "--out", out_path,
           "--time-limit", str(args.time_limit), "--seed", str(args.seed)]
    if args.weights:
        cmd += ["--weights", args.weights]
    if args.epsilon:
        cmd += ["--epsilon", str(args.epsilon)]
    if args.max_nodes:
        cmd += ["--max-nodes", str(args.max_nodes)]
    print("[run] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd)
    return proc.returncode, out_path


# ---------------------------------------------------------------- validation
def rust_validate(word_path: str, n: int) -> bool:
    cmd = ["cargo", "run", "--release", "--", "validate",
           "-n", str(n), "--file", word_path, "--complete"]
    print("[validate] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=SPR, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", nargs="?")
    ap.add_argument("--chains")
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--weights")
    ap.add_argument("--epsilon", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--time-limit", type=float, default=600.0)
    ap.add_argument("--max-nodes", type=int, default=0)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--no-compile", action="store_true",
                    help="stop after check_cover (no word compile/validate)")
    args = ap.parse_args()

    tag, inst, path = resolve_instance(args)
    n = inst["n"]
    m = inst.get("meta", {})
    print(f"[{tag}] n={n} cols={len(inst['columns'])} rows={len(inst['rows'])} "
          f"nchild={n - 2} meta={ {k: m[k] for k in sorted(m)} if m else '-'}",
          flush=True)

    args.outdir = os.path.abspath(args.outdir)
    os.makedirs(args.outdir, exist_ok=True)
    if path is None:
        path = os.path.join(args.outdir, f"inst_{tag}.txt")
        with open(path, "w") as fh:
            fh.write(export_instance(inst))
    rows_path = os.path.join(args.outdir, f"rows_{tag}.txt")

    t0 = time.time()
    rc, rows_path = run_engine(path, args, rows_path)
    el = time.time() - t0
    if rc == 2:
        print(f"[{tag}] EXHAUSTED: no rooted cover exists ({el:.1f}s)", flush=True)
        return 2
    if rc == 3:
        print(f"[{tag}] TIMEOUT ({el:.1f}s)", flush=True)
        return 3
    if rc != 0:
        print(f"[{tag}] engine error rc={rc}", flush=True)
        return 1

    ids = [int(x) for x in open(rows_path) if x.strip()]
    chosen = [inst["rows"][i] for i in ids]
    rep = gain1.check_cover(inst, chosen)
    print(f"[{tag}] SOLVED {len(ids)} rows in {el:.1f}s; check_cover={rep}",
          flush=True)
    if not rep["valid"]:
        print(f"[{tag}] engine returned an invalid cover (BUG)", flush=True)
        return 4
    if args.no_compile:
        return 0

    try:
        if n == 7:
            word, cert, costs = compile_chain_cover(inst, chosen)
        else:
            cert = gain1.assemble_certificate(inst, chosen)
            word, _path, costs = compile_certificate(cert)
    except Exception as exc:                       # noqa: BLE001
        print(f"[{tag}] compile FAILED: {exc!r}", flush=True)
        return 4

    L = len(word)
    if not gain1.verify_word(word, n):
        print(f"[{tag}] internal word verification failed", flush=True)
        return 4
    base = os.path.join(args.outdir, f"candidate_{L}_{tag}")
    with open(base + ".txt", "w") as fh:
        fh.write(word)
    with open(base + ".cert.json", "w") as fh:
        json.dump(cert, fh)
    with open(base + ".cover.json", "w") as fh:
        json.dump({"tag": tag, "row_ids": ids,
                   "entries": [r["entry"] for r in chosen]}, fh)

    if not rust_validate(base + ".txt", n):
        print(f"[{tag}] RUST VALIDATOR REJECTED {base}.txt — NOT a result",
              flush=True)
        return 4
    from collections import Counter
    print(f"[{tag}] SUCCESS validated length={L} -> {base}.txt "
          f"costs={dict(sorted(Counter(costs).items()))}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
