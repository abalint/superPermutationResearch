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

## Known failure modes

1. **OOM kills, not crashes.** Instances grow as the search deepens; on the Mac,
   13 concurrent solvers exhausted RAM and were killed silently (logs truncated
   mid-line, no crash report, one 0-byte log). Symptoms look like a mystery
   crash. Cap workers by RAM, not cores, and keep the watchdog's low-memory
   safety valve (no new workers below ~15% free).
   (An earlier stack-overflow theory was **wrong** — measured peak stack is
   under 100 KB: `searchPC`'s frame is 128 bytes over ~141 levels. The `/F`
   large-stack rebuild is harmless but fixes nothing.)
2. **Truncated `IntersectionFlags7.dat`.** A killed run leaves it corrupt and
   the engine then aborts instantly with `Error reading from file
   IntersectionFlags7.dat`. Launchers delete it before every start; do the same
   in anything new.
3. **The engine is fully deterministic** (no `rand()`), so restarting a crashed
   chain reproduces the identical run — restarts alone never help. Change the
   chain, the mode, or the resource that killed it.

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
