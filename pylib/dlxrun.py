#!/usr/bin/env python3
# --- PROVENANCE (s64 P1, 2026-08-02) --------------------------------
# Promoted BY COPY from out/s57/proposer/dlxrun.py.
# This pylib/ copy is CANONICAL as of s64; the out/ original is FROZEN
# history -- byte-untouched, cited by the session REPORTs.  Do NOT edit
# it; fix bugs HERE.
# See pylib/README.md.
# --------------------------------------------------------------------
"""Thin dlx7g runner that exposes the randomized-restart knobs s56 left at 0."""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DLX7G = os.path.join(REPO, "analysis", "trackc", "dlx7g")


def run(text, time_limit=15.0, max_nodes=None, tag="x", outdir=HERE,
        epsilon=0.0, seed=0, col_epsilon=0.0, col_seed=0, extra=None):
    inst_fn = os.path.join(outdir, f"inst_{tag}.txt")
    out_fn = os.path.join(outdir, f"sol_{tag}.txt")
    with open(inst_fn, "w") as fh:
        fh.write(text)
    cmd = [DLX7G, inst_fn, "--time-limit", str(time_limit), "--out", out_fn]
    if max_nodes:
        cmd += ["--max-nodes", str(max_nodes)]
    if epsilon:
        cmd += ["--epsilon", str(epsilon), "--seed", str(seed)]
    if col_epsilon:
        cmd += ["--col-epsilon", str(col_epsilon), "--col-seed", str(col_seed)]
    if extra:
        cmd += list(extra)
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.monotonic() - t0
    rc = proc.returncode
    verdict = {0: "SAT", 2: "UNSAT", 3: "UNKNOWN"}.get(rc, f"ERROR{rc}")
    ids = []
    if rc == 0 and os.path.exists(out_fn):
        ids = [int(x) for x in open(out_fn).read().split()]
    tail = [l for l in proc.stderr.strip().splitlines() if l.startswith("RESULT")]
    return dict(verdict=verdict, seconds=dt, rows=ids, rc=rc,
                result_line=(tail[-1] if tail else proc.stdout.strip()[:200]))
