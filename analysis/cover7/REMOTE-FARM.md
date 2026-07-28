# REMOTE-FARM.md — the n=7 5905 search farm on the Windows PC

Session-independent runbook. The farm survives ssh disconnects, this laptop
sleeping, and any Claude session ending — everything below can be driven from a
fresh session, a phone, or by hand.

## The machine

- Host: `ssh transcribe` (alias in `~/.ssh/config`; `transcribe-svc@100.72.37.37`,
  Tailscale, key auth). 28 cores, 48 GB RAM. **Standard user — not admin.**
- Work dir: **`F:\superpermFarm`** (1.1 TB free). NEVER use C: (~20 GB free) and
  NEVER touch `F:\audioPrime` (a separate production app of the user's).
- Every ssh call prints a post-quantum warning to stderr; filter it:
  `2>&1 | grep -viE "WARNING|post-quantum|store now|openssh.com"`.
- Quoting through ssh → cmd → PowerShell mangles arguments. Ship a
  **parameterless** script with `scp <file> "transcribe:F:/superpermFarm/"` and
  run it by path.

## How persistence works (no admin needed)

Windows OpenSSH kills its session's process tree on disconnect, and this account
cannot use `schtasks /ru SYSTEM` or WMI process creation. The solution is
`F:\superpermFarm\detach.exe` (source `detach.c`, built by `builddetach.bat`
with the VS 2022 MSVC toolchain) — the Windows analogue of `nohup`:

```
detach.exe <workdir> <stdout-log> <stderr-log> <command> [args...]
```

It calls `CreateProcess` with `CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS |
CREATE_NEW_PROCESS_GROUP | BELOW_NORMAL_PRIORITY_CLASS`, opens the log files
itself, and restricts handle inheritance to exactly those three handles (without
that the child inherits sshd's pipes and the ssh call hangs forever).

**Anything launched any other way dies at disconnect.** Always use `detach.exe`.

Optional, admin-only: `install_tasks_admin.bat` registers the runs as SYSTEM
tasks with `/sc ONSTART` so they also survive *reboots*. It is more privilege
than the job needs — use only if a reboot is expected;
`uninstall_tasks_admin.bat` reverses it.

## Daily commands (from anywhere)

```sh
S='ssh transcribe powershell -NoProfile -ExecutionPolicy Bypass -File'
ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\status.ps1"    # alive workers, CPU, last progress, SOLUTION flags
ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\farmscale.ps1"  # start/backfill to the worker target
ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\watchdog.ps1"   # one backfill pass + appends to watchdog.log
ssh transcribe "powershell -NoProfile -ExecutionPolicy Bypass -File F:\superpermFarm\farmstop.ps1"   # stop everything
```

All are idempotent: `farmscale`/`watchdog` skip chains already running and
backfill only dead slots. Worker count is a single `TARGET` variable at the top
of `farmscale.ps1`.

> ## ⚠ SUPERSEDED IN PART — read this box first (session 15)
>
> The farm no longer runs Egan's `PermutationChains`. **The Windows build of it
> was broken at the build level**: `PermutationChains.exe 5` / `6` fail Egan's
> own smoke tests, exiting `0xC0000409` (STATUS_STACK_BUFFER_OVERRUN) with zero
> solution files, while the same source under clang on the Mac produces the
> correct 6 and 42,288 solutions. **Every chain the PermutationChains farm ever
> "finished" is void — those chains were never searched.** Nothing in the
> §"failure modes" discussion below about orderly exits should be treated as
> evidence about the mathematics; it was describing a crashing binary.
>
> **s16 update — root cause found and patched.** The Windows failure was NOT a
> stack overrun: `PermutationChains.c` passes invalid `fopen` modes (`"wa"`,
> `"aa"`), which the MSVC UCRT turns into `__fastfail` → the misleading
> 0xC0000409, plus a dropped `FILE*` assignment causing a write-to-closed-stream
> and a double close. Patch (3 lines, upstream-ready):
> `PermutationChains-fopen-fix.patch`. With it, MSVC and mingw-w64 builds both
> pass Egan's smoke tests on Windows (n=5 → 6, `6 ffc` → 36). The fixed binary
> was then used as an INDEPENDENT ORACLE and **agrees with our CaDiCaL
> refutations on 6 of 6 chains, 0 disagreements** — the UNSAT column of
> `results.csv` is cross-validated.
>
> The farm runs `satworker.py` (CaDiCaL over the exact-cover encoding) as a
> **refutation engine**: UNSAT is an unconditional refutation of a chain, SAT
> would be auto-compiled and validated. Operating commands are `satstatus.ps1` /
> `satscale.ps1` / `satstop.ps1` (same invocation pattern as below), ledger at
> `F:\superpermFarm\results.csv`.
>
> **Sobering limit, stated plainly:** no engine we have — CaDiCaL, Python DLX,
> or C DLX — can *find* a cover for a known-SAT control instance (the standard
> K=5 kernel, or the real 5906's K=18 chain) within 45 minutes. The validated
> 5907/5906 words this project compiled were **reconstructed from published
> words, not discovered**. So the farm is credible when it says UNSAT and is
> not a likely route to a record. Absence of SAT is not evidence of absence.

## Known failure modes (historical — PermutationChains era)

1. **Workers that vanish are (apparently) FINISHING, not crashing.** Two
   successive diagnoses were wrong and are recorded here so nobody re-runs them:
   - *Stack overflow* — **refuted by measurement**: `searchPC`'s frame is 128
     bytes over ~141 levels ⇒ peak stack under 100 KB. A 64 MB rebuild
     (`build64.bat`, `dumpbin` confirms a `4000000` reserve vs `100000`)
     changed nothing; workers exit at the same depth.
   - *OOM kill* — **refuted by measurement**: peak RSS is 4.4 MB per worker
     against 37 GB free.
   - What the evidence actually shows: logs end on a **complete line with a
     trailing newline** after the `PCsolSize=…` best-partial dump, with a
     0-byte stderr — an orderly exit, not a kill (a kill loses the unflushed
     4 KB stdout buffer, which is what mid-line truncation on the Mac looked
     like under memory pressure). Three K=29 chains "finished" in ~1
     CPU-minute.

   > **OPEN QUESTION — do not state a conclusion until it is settled.** If the
   > engine's plain mode exhausts its search space, then finishing without a
   > solution *refutes* that chain (no rooted cover ⇒ no 5905 from it), which
   > would make the farm a refutation engine and is publishable progress. If
   > instead the mode is bounded/heuristic, finishing means only "this
   > strategy gave up" and refutes nothing. **Positive control in flight**:
   > the standard K=5 kernel (`nsk66666`, `runs\ctrl`) provably HAS covers —
   > it is how the known 5907s were built. If the control finds one, orderly
   > completion elsewhere is meaningful; if the control also completes without
   > a solution, completion means nothing and the farm's negatives are void.
   > Check `runs\ctrl\out.log` for a `Found SOLUTION` line or a `7_59*.txt`.

2. **Truncated `IntersectionFlags7.dat`.** A killed run leaves it corrupt and
   the engine then aborts instantly with `Error reading from file
   IntersectionFlags7.dat`. Launchers delete it before every start; do the same
   in anything new.
3. **The engine is fully deterministic** (no `rand()`), so restarting a finished
   or crashed chain reproduces the identical run — restarts alone never help.
   Change the chain, the mode, or the resource involved.
4. **Perf counters, WMI, and `systeminfo` are all Access-denied** for this
   account. Use `meminfo.ps1` (`GlobalMemoryStatusEx` P/Invoke) for RAM.
5. **Two binaries exist**: `PermutationChains.exe` (held open by the 5 priority
   workers) and `PermutationChains64.exe` (the pointless large-stack build).
   `farmstop.ps1` targets both names.

## Harvest — what a win looks like

A solution writes `7_59*.txt` under `F:\superpermFarm\runs\` (status.ps1 flags
it prominently). Each line is a candidate word. Validate on the Mac before
believing it:

```sh
scp "transcribe:F:/superpermFarm/runs/<dir>/7_5905_<pattern>.txt" /tmp/cand.txt
cd /Users/andrew/Documents/code/math/superperms/superPermutationResearch
cargo run --release -- validate -n 7 --file /tmp/cand.txt --complete   # must print complete = true
cargo run --release -- trace    -n 7 --file /tmp/cand.txt              # census; length must be 5905
```

Length 5905 + `complete superpermutation = true` = **a world record** (current
record 5906). Save the word, the chain JSON, and the cover immediately, then see
`docs/RESULT-gain1-optimality-n6.md` for the writeup this would lead.

## What the farm is searching

Candidate kernel chains at V₇ ≥ 15 (ledger length 5905): 5 × K=27, 21 × K=29,
48 × K=30, 149 × K=31 (censuses in `chains_V15*.jsonl`, cross-validated against
Egan's KernelFinder). Any rooted exact cover on any one of them is the record.
Priority order is K=27 → K=29 → K=30 → K=31 (lower K = more row freedom).
Complementary work: CDCL (CaDiCaL/kissat) refutation runs prove individual
chains cover-free; three UNSATs on the distinct K=27 chains would close Σ=12.
