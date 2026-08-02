#!/usr/bin/env python3
"""Track C instance builder / exporter (design doc: docs/TRACKC-DESIGN.md).

Builds every DLX rooted-cover instance Track C trains or gates on, and writes
each one as a text file in the (generalized) `solve_dlx.py` format plus a
sidecar `<name>.meta.json`.

Text format -- header line

    ncols nrows nloops nchild

then one line per row (row id = 0-based line order):

    loopid parent_col_or_-1 c1 .. c_nchild

`nchild` = n-2 (4 at n=6, 5 at n=7); a parent column of -1 means the row's
parent orbit is a kernel root.  Column ids are 0-based indices into the
instance's `sorted(columns)` list, row ids are indices into `inst["rows"]` in
the order the builders emit them.  Those two id spaces are the shared
vocabulary with the C engine -- do not reorder them.

usage: python3 instances.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
COVER7 = os.path.join(REPO, "analysis", "cover7")
FARM = os.path.join(REPO, "analysis", "farm")
EX_SCRIPTS = os.path.join(
    os.path.dirname(REPO), "extraDocs", "superpermutation-examples", "scripts"
)
# s64 P1: chain7 is promoted (pylib/chain7.py); gain1/certificate still
# live in the sibling extraDocs checkout, which add_legacy_paths() knows.
import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_legacy_paths()

import gain1  # noqa: E402
import chain7  # noqa: E402
from chain7 import (  # noqa: E402
    build_instance_from_chain,
    entries,
    li,
    sources,
    standard_chain,
)
from certificate import canonical_rotation, format_loop, loop_of, parse_loop  # noqa: E402

DATA = os.path.join(REPO, "data", "trackc")
INSTANCE_DIR = os.path.join(DATA, "instances")
NE = 6  # orbits per loop at n=7

CERT5907 = [
    "cert5907_5907-504778e6.json",
    "cert5907_5907-608be0be.json",
    "cert5907_5907-fff93aab.json",
]


# --------------------------------------------------------------- export


def export_instance_text(inst: dict) -> str:
    """Serialize an instance dict to the DLX engine text format."""
    n = inst["n"]
    nchild = n - 2
    rows = inst["rows"]
    col_index = {c: i for i, c in enumerate(inst["columns"])}
    roots = set(inst["roots"])
    loop_ids: dict = {}
    for r in rows:
        loop_ids.setdefault(r["loop"], len(loop_ids))
    lines = [f"{len(col_index)} {len(rows)} {len(loop_ids)} {nchild}"]
    for r in rows:
        po = r["parent_orbit"]
        pc = -1 if po in roots else col_index[po]
        assert len(r["children"]) == nchild, "child count != n-2"
        ch = " ".join(str(col_index[c]) for c in r["children"])
        lines.append(f"{loop_ids[r['loop']]} {pc} {ch}")
    return "\n".join(lines) + "\n"


def meta_for(inst: dict, name: str, tag: str, source: str) -> dict:
    m = inst.get("meta", {})
    return {
        "name": name,
        "tag": tag,
        "n": inst["n"],
        "nchild": inst["n"] - 2,
        "K": m.get("K", len(inst["kernel"])),
        "Sigma": m.get("Sigma", 0),
        "V": m.get("V"),
        "R": m.get("R", len(inst["columns"]) // (inst["n"] - 2)),
        "ncols": len(inst["columns"]),
        "nrows": len(inst["rows"]),
        "roots": len(inst["roots"]),
        "source": source,
    }


def write_instance(inst: dict, name: str, tag: str, source: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    txt = os.path.join(out_dir, f"{name}.txt")
    with open(txt, "w") as fh:
        fh.write(export_instance_text(inst))
    meta = meta_for(inst, name, tag, source)
    with open(os.path.join(out_dir, f"{name}.meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return meta


# ------------------------------------------------------- cert -> chain


def cert_to_chain(cert: dict) -> list:
    """Rebuild the chain-tuple form of a 5906-style certificate's kernel.

    The certificate records the kernel loops in ride order and the K-1 hop
    doors between them; that is enough to recover (L, k, j, sk, s, t, c) for
    every non-terminal loop.  The terminal loop's skip is recovered from the
    orbit budget: |columns| = (n-2) * #rows, roots = 720 - |columns|, and
    sum(sk) = 6K - roots.
    """
    if cert.get("n") != 7:
        raise ValueError("cert_to_chain is n=7 only")
    kl = [parse_loop(x, 7) for x in cert["kernel_loops"]]
    Ls = [li[x] for x in kl]
    hops = cert["hop_doors"]
    if len(hops) != len(Ls) - 1:
        raise ValueError("hop count != K-1")
    start = cert["start_perm"]
    ents = entries[Ls[0]]
    if start in ents:
        k = ents.index(start)
    else:
        k = [canonical_rotation(e) for e in ents].index(canonical_rotation(start))
    sol, sksum = [], 0
    for i, L in enumerate(Ls):
        if i < len(hops):
            s, t, c = hops[i]["source"], hops[i]["target"], hops[i]["cost"]
            j = sources[L].index(s)
            sk = 5 - ((j - k) % NE)
            sksum += sk
            sol.append((L, k, j, sk, s, t, c))
            Ln = li[loop_of(t)]
            if Ln != Ls[i + 1]:
                raise ValueError(f"hop {i} does not land on kernel loop {i+1}")
            k = entries[Ln].index(t)
        else:
            ncols = (7 - 2) * len(cert["rows"])
            roots = 720 - ncols
            sk_term = (NE * len(Ls) - roots) - sksum
            sol.append((L, k, None, sk_term, None, None, None))
    chain7.verify_chain(sol)
    return sol


def cert_family(fname: str) -> str:
    """`cert5906_666466646646_2.json` -> `666466646646` (the chain family)."""
    base = os.path.basename(fname)
    return base.replace("cert5906_", "").rsplit("_", 1)[0]


# ------------------------------------------------------ instance registry


def n6_standard() -> dict:
    return gain1.build_instance(6)


def n7_standard() -> dict:
    return build_instance_from_chain(standard_chain())


def cert5906_paths() -> list:
    return sorted(
        os.path.join(COVER7, f)
        for f in os.listdir(COVER7)
        if f.startswith("cert5906_") and f.endswith(".json")
    )


def cert5907_paths() -> list:
    return [os.path.join(COVER7, f) for f in CERT5907]


def chain5906_families() -> tuple[dict, list]:
    """{family: (instance, source cert path)} + list of (cert path, reason)."""
    fams: dict = {}
    failures = []
    for path in cert5906_paths():
        fam = cert_family(path)
        cert = json.load(open(path))
        try:
            sol = cert_to_chain(cert)
            inst = build_instance_from_chain(sol)
        except Exception as exc:  # pragma: no cover - reported, not raised
            failures.append((path, repr(exc)))
            continue
        if fam in fams:
            if fams[fam][2] != sol:
                failures.append((path, "chain disagrees with family sibling"))
            continue
        fams[fam] = (inst, path, sol)
    return fams, failures


def k27_chains() -> list:
    """The 5 open K=27 chains (V7=15 census), in file order."""
    src = os.path.join(COVER7, "chains_V15_s14.jsonl")
    if not os.path.exists(src):
        src = os.path.join(FARM, "farm_chains.jsonl")
    out = []
    with open(src) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("K") == 27:
                out.append((rec, src))
    return out


def build_all(out_dir: str = INSTANCE_DIR) -> dict:
    """Build + export every Track C instance.  Returns a report dict."""
    report = {"written": [], "dropped": []}

    inst = n6_standard()
    report["written"].append(
        write_instance(inst, "n6std", "n6std", "gain1.build_instance(6)", out_dir)
    )
    inst = n7_standard()
    report["written"].append(
        write_instance(inst, "n7std", "n7std", "chain7.standard_chain()", out_dir)
    )

    fams, failures = chain5906_families()
    for fam in sorted(fams):
        finst, path, _sol = fams[fam]
        report["written"].append(
            write_instance(
                finst,
                f"c5906_{fam}",
                f"c5906_{fam}",
                os.path.relpath(path, REPO),
                out_dir,
            )
        )
    for path, why in failures:
        report["dropped"].append({"src": os.path.relpath(path, REPO), "why": why})

    for idx, (rec, src) in enumerate(k27_chains()):
        sol = [tuple(x) for x in rec["chain"]]
        try:
            kinst = build_instance_from_chain(sol)
        except Exception as exc:
            report["dropped"].append(
                {"src": f"{os.path.relpath(src, REPO)}#K27[{idx}]", "why": repr(exc)}
            )
            continue
        report["written"].append(
            write_instance(
                kinst,
                f"k27_{idx}",
                f"k27_{idx}",
                f"{os.path.relpath(src, REPO)} K=27 entry {idx}",
                out_dir,
            )
        )
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=INSTANCE_DIR)
    args = ap.parse_args()
    rep = build_all(args.out)
    for m in rep["written"]:
        print(
            f"{m['name']:<22} n={m['n']} K={m['K']:>2} Sigma={m['Sigma']:>2} "
            f"cols={m['ncols']:>4} rows={m['nrows']:>5} roots={m['roots']:>3}"
        )
    print(f"\n{len(rep['written'])} instances written to {args.out}")
    if rep["dropped"]:
        print(f"{len(rep['dropped'])} dropped:")
        for d in rep["dropped"]:
            print("  ", d)
    else:
        print("0 dropped")

    # gates
    a = next(m for m in rep["written"] if m["name"] == "n6std")
    b = next(m for m in rep["written"] if m["name"] == "n7std")
    print(f"GATE(a) n6std {a['ncols']}x{a['nrows']} "
          f"{'OK' if (a['ncols'], a['nrows']) == (100, 464) else 'FAIL'}; "
          f"n7std {b['ncols']}x{b['nrows']} "
          f"{'OK' if (b['ncols'], b['nrows']) == (690, 4440) else 'FAIL'}")


if __name__ == "__main__":
    main()
