README-FARM.txt -- F:\superpermFarm -- the n=7 5905 search farm
================================================================
Last re-aimed: 2026-07-27. Read this before touching anything.

WHAT CHANGED, AND WHY (2026-07-27)
----------------------------------
The farm previously ran Egan's PermutationChains.exe on 218 candidate kernel
chains. That engine has been RETIRED. It is broken on this machine:

  PermutationChains.exe 5           -> exit 0xC0000409, ZERO solution files
  PermutationChains.exe 6           -> exit 0xC0000409, ZERO solution files
  PermutationChains.exe 6 ffc       -> exit 0xC0000409, ZERO solution files

Egan's own Readme says `PermutationChains 5` must print 6 solutions instantly
and `PermutationChains 6` must find 42,288. The Windows build finds none of
them and dies with STATUS_STACK_BUFFER_OVERRUN. Rebuilding with /Od and with
/O2 /GS- reproduces the identical failure, so it is not an optimiser artefact.
The same source built with clang on the Mac passes both benchmarks exactly
(6 and 42,288 solutions), so the bug is specific to the MSVC/Windows build.

CONSEQUENCE: every "finished, no solution" result this farm produced with
PermutationChains.exe is VOID. Those chains were never searched. Do not cite
any of them as refuted.

Do not restart the old farm (farmlaunch.ps1 / farmscale.ps1 / watchdog.ps1);
they are kept only for the record.

THE ENGINE NOW RUNNING
----------------------
sat_chain.py -- CaDiCaL (PySAT Cadical195) over the exact-cover encoding built
by chain7.py, with lazy rootless-cycle cuts. Verdicts:

  SAT     -> a rooted exact cover exists. sat_chain.py then COMPILES it to a
             superpermutation word and verifies it before reporting, so a
             SAT-RECORD row is a candidate world record (5905 vs the 5906
             record). Still validate on the Mac before believing it.
  UNSAT   -> no rooted exact cover exists: the chain is genuinely REFUTED.
  TIMEOUT -> budget expired. Says nothing at all about the chain.

Soundness note: a "UNSAT after 0 cuts" line is an unconditional exact-cover
refutation. With k>0 cuts the refutation is of the rooted problem, which is
still exactly the question we are asking.

CONTROL-GATE STATUS -- READ THIS BEFORE INTERPRETING RESULTS
-----------------------------------------------------------
The UNSAT direction is validated: chain s14:5 (K=29) comes back UNSAT in 33 s
under CaDiCaL and 49 s under kissat, independently.

The FIND direction is NOT demonstrated. Two known-satisfiable controls are in
sat\control_chains.jsonl:
  index 0 -- standard K=5 kernel (covers exist; three were extracted from the
             published 5907s and recompiled + cargo-validated)
  index 1 -- the K=18 kernel of the real 5906 (a cover provably exists)
Neither CaDiCaL, the Python DLX (run_chain.py), nor the C DLX (dlx7) found a
cover for either control unseeded within 30 min. The historical
control_search.log shows the same failure. These instances are simply hard:
Egan himself needed `fullSymm limStab ffc` symmetry reduction to find 5907s.

So operate this farm as a REFUTATION ENGINE. UNSAT rows are the citable
scientific output. A SAT row would be a record, but no engine here has been
shown able to find one, so absence of SAT rows is NOT evidence of absence.

LAYOUT
------
  sat\                 engine + instances
    chain7.py gain1.py certificate.py     instance builders
    sat_chain.py       CaDiCaL engine (the one in use)
    run_chain.py       Python DLX engine (ENGINE="dlx" alternative)
    solve_dlx.py dlx7.exe dlx7_win.c      C DLX engine
    farm_chains.jsonl  223 chains: idx 0-4 = the K=27 priority chains,
                       idx 5-222 = the 218-pattern worklist, in tier order.
                       Line i of this file IS index i everywhere else.
    control_chains.jsonl  the two known-SAT controls described above
  satworker.py         one worker (see below)
  satscale.ps1         start/backfill to $TARGET workers
  satstatus.ps1        status + ledger summary
  satstop.ps1          stop everything
  claims\<i>.claim     atomic work claim, one file per chain index
  satruns\<i>_<pat>\   per-chain engine.log / engine.err / candidate_*.txt
  results.d\<i>.row    one JSON row per finished chain (write-once)
  results.csv          THE LEDGER, rebuilt from results.d after every job
  workers\<pid>.alive  liveness markers (WMI is Access-denied for this account)

HOW WORK IS SCHEDULED
---------------------
satworker.py is parameterless (nested quoting through ssh -> cmd -> PowerShell
mangles arguments). All workers are identical; they differentiate by ATOMICALLY
CLAIMING indices via O_CREAT|O_EXCL on claims\<i>.claim. Each worker:

    claim next unclaimed chain
    -> run the engine with a PER-CHAIN TIME BUDGET
    -> write results.d\<i>.row, rebuild results.csv
    -> repeat until the worklist is empty

BUDGET_MIN at the top of satworker.py is the single knob (default 30 min);
HARDKILL = BUDGET_MIN*60 + 180 s is the backstop, because sat_chain.py can only
check its own time limit between cuts. This budget is the fix for the old
farm's fatal flaw: 27 workers used to hold the same handful of chains forever
while 193 of 218 patterns were never started even once.

$TARGET at the top of satscale.ps1 is the worker count (default 27).

DAILY COMMANDS (from the Mac, or anywhere)
------------------------------------------
  ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\satstatus.ps1"
  ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\satscale.ps1"
  ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\satstop.ps1"
  scp "transcribe:F:/superpermFarm/results.csv" /tmp/results.csv

satscale.ps1 is idempotent: it counts live workers and launches only the
shortfall, so it doubles as the watchdog. Claims persist across restarts, so a
restarted farm resumes rather than redoing finished chains. To deliberately
re-run a chain, delete its claims\<i>.claim AND results.d\<i>.row.

PERSISTENCE
-----------
Windows OpenSSH kills its session's process tree on disconnect and this account
cannot use schtasks /ru SYSTEM or WMI process creation. Everything long-running
MUST be launched through detach.exe:

    detach.exe <workdir> <stdout> <stderr> <command> [args...]

satscale.ps1 already does this. NOTE: detach.exe launches python.exe reliably,
but a detached "powershell.exe -File" produced no output at all in testing --
that is why the worker is Python and not PowerShell. Do not "simplify" it back.

HARVEST -- WHAT A WIN LOOKS LIKE
--------------------------------
A SAT-RECORD row in results.csv, a candidate_*.txt under satruns\, and a line
in RECORD-FOUND.txt. Validate on the Mac before believing anything:

  scp "transcribe:F:/superpermFarm/satruns/<dir>/<candidate>.txt" /tmp/cand.txt
  cd .../superPermutationResearch
  cargo run --release -- validate -n 7 --file /tmp/cand.txt --complete
  cargo run --release -- trace    -n 7 --file /tmp/cand.txt

Length 5905 + "complete superpermutation = true" = a world record.

DO NOT
------
- Do not touch F:\audioPrime or C:. Work only in F:\superpermFarm.
- Do not report a chain as refuted from any engine that has not passed a
  control gate. Right now that means: UNSAT rows only, from sat_chain.py.
- Do not trust any PermutationChains.exe output, past or future.
