#!/usr/bin/env python3
"""satworker.py -- one worker of the n=7 cover farm.

Parameterless by design (nested quoting through ssh -> cmd -> PowerShell
mangles arguments): every worker is identical and they distinguish themselves
by atomically CLAIMING chain indices out of a shared worklist.

Loop:  claim next unclaimed chain
       -> run the engine under a hard wall-clock budget
       -> drop one row file into results.d\\
       -> rebuild results.csv
       -> repeat until the worklist is empty.

Launch with detach.exe so it survives ssh disconnect:
    detach.exe <root> <log> <err> python.exe satworker.py

Outcome vocabulary written to the ledger:
    SAT-RECORD  engine found a rooted exact cover AND compiled+verified the
                word. At V7=15 that word is length 5905 = a world record.
    UNSAT       engine proved no rooted exact cover exists -> the chain is
                REFUTED. This is the scientific output of a negative run.
    TIMEOUT     budget expired with no verdict -> inconclusive, says nothing.
    ERROR-n     engine crashed; treat as inconclusive.
"""
import csv
import json
import os
import subprocess
import sys
import time

# ------------------------------------------------------------------ parameters
BUDGET_MIN = 30           # per-chain time budget, minutes   <-- single knob
ENGINE     = "sat"        # "sat" = sat_chain.py (CaDiCaL) | "dlx" = run_chain.py

ROOT   = r"F:\superpermFarm"
SAT    = os.path.join(ROOT, "sat")
CHAINS = os.path.join(SAT, "farm_chains.jsonl")
CLAIMS = os.path.join(ROOT, "claims")
RUNS   = os.path.join(ROOT, "satruns")
ROWS   = os.path.join(ROOT, "results.d")
ALIVE  = os.path.join(ROOT, "workers")
CSV    = os.path.join(ROOT, "results.csv")
PY     = sys.executable

BUDGET_S = BUDGET_MIN * 60
HARDKILL = BUDGET_S + 180        # engine self-limits; this is the backstop

HEADER = ["timestamp", "index", "pattern", "K", "Sigma", "engine",
          "outcome", "best_partial", "minutes", "worker_pid", "word_file"]


def claim(idx):
    """Atomically claim a chain index. True iff this worker got it."""
    path = os.path.join(CLAIMS, f"{idx}.claim")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as fh:
        fh.write(f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    return True


def rebuild_csv():
    """Merge results.d\\*.row into results.csv. Row files are written once and
    never mutated, so this needs no locking."""
    rows = []
    for name in sorted(os.listdir(ROWS)):
        if not name.endswith(".row"):
            continue
        try:
            with open(os.path.join(ROWS, name)) as fh:
                rows.append(json.load(fh))
        except Exception:
            continue
    rows.sort(key=lambda r: int(r["index"]))
    tmp = CSV + f".{os.getpid()}.tmp"
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(tmp, CSV)


def best_partial(log_path):
    """Deepest progress the engine reported, for the ledger."""
    if not os.path.exists(log_path):
        return ""
    last = ""
    try:
        with open(log_path, errors="replace") as fh:
            for line in fh:
                if ENGINE == "sat" and "iter " in line:
                    last = line.strip()
                elif ENGINE == "dlx" and "attempt " in line:
                    last = line.strip()
    except Exception:
        return ""
    return last[-160:]


def main():
    for d in (CLAIMS, RUNS, ROWS, ALIVE):
        os.makedirs(d, exist_ok=True)

    # liveness marker: WMI/Get-CimInstance is Access-denied for this account,
    # so satscale.ps1 counts these files and checks the pid is still running.
    alive_path = os.path.join(ALIVE, f"{os.getpid()}.alive")
    with open(alive_path, "w") as fh:
        fh.write(time.strftime("%Y-%m-%dT%H:%M:%S"))

    with open(CHAINS) as fh:
        records = [json.loads(l) for l in fh if l.strip()]

    for idx, rec in enumerate(records):
        if not claim(idx):
            continue

        pat = rec["pattern"]
        d = os.path.join(RUNS, f"{idx:03d}_{pat}")
        os.makedirs(d, exist_ok=True)
        log = os.path.join(d, "engine.log")
        err = os.path.join(d, "engine.err")

        if ENGINE == "sat":
            cmd = [PY, os.path.join(SAT, "sat_chain.py"), CHAINS, str(idx),
                   "--time-limit", str(BUDGET_S)]
        else:
            cmd = [PY, os.path.join(SAT, "run_chain.py"), CHAINS, str(idx),
                   str(BUDGET_S), "1"]

        t0 = time.time()
        killed = False
        with open(log, "w") as lo, open(err, "w") as le:
            p = subprocess.Popen(cmd, cwd=d, stdout=lo, stderr=le)
            try:
                code = p.wait(timeout=HARDKILL)
            except subprocess.TimeoutExpired:
                killed = True
                p.kill()
                try:
                    code = p.wait(timeout=30)
                except Exception:
                    code = -9
        mins = round((time.time() - t0) / 60.0, 2)

        if killed:
            outcome = "TIMEOUT-KILLED"
        elif ENGINE == "sat":
            # sat_chain.py: 0 = validated word, 2 = UNSAT, 1 = limit/stall
            outcome = {0: "SAT-RECORD", 2: "UNSAT", 1: "TIMEOUT"}.get(
                code, f"ERROR-{code}")
        else:
            # run_chain.py: 0 = word, 2 = exhausted, 3 = limit, 4 = compile fail
            outcome = {0: "SAT-RECORD", 2: "UNSAT", 3: "TIMEOUT",
                       4: "COVER-NOCOMPILE"}.get(code, f"ERROR-{code}")

        words = [f for f in os.listdir(d) if f.startswith("candidate_")
                 and f.endswith(".txt")]
        word_file = words[0] if words else ""

        row = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "index": idx, "pattern": pat, "K": rec["K"], "Sigma": rec["Sigma"],
            "engine": ENGINE, "outcome": outcome,
            "best_partial": best_partial(log).replace(",", ";"),
            "minutes": mins, "worker_pid": os.getpid(), "word_file": word_file,
        }
        with open(os.path.join(ROWS, f"{idx:03d}.row"), "w") as fh:
            json.dump(row, fh)
        try:
            rebuild_csv()
        except Exception:
            pass

        if outcome == "SAT-RECORD":
            with open(os.path.join(ROOT, "RECORD-FOUND.txt"), "a") as fh:
                fh.write(f"RECORD idx={idx} pattern={pat} dir={d} "
                         f"file={word_file}\n")

    with open(os.path.join(ROOT, "satworkers.log"), "a") as fh:
        fh.write(f"worker {os.getpid()} finished worklist "
                 f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    try:
        os.remove(alive_path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
