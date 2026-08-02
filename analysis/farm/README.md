# farm — the scripts that run the n=7 search on the Windows PC

Committed copies of what lives on `F:\superpermFarm`. Operating instructions
are in `../cover7/REMOTE-FARM.md` (read that first); this directory is the
version-controlled source of the scripts themselves.

> **New harness work goes through `template/` (s64 P5).** One parameterized
> `farm_ship.sh` / `farm_fetch.sh` / `farm_env.ps1` driven by a per-instrument
> config, plus the shared STATUS emitter `pylib/farmstatus.py` which encodes
> the heartbeat contract ONCE — read `template/README.md` before adding an
> instrument, and do **not** clone another `<tag>_{ship,shim,env,fetch}`
> quartet. mc28, a0 and qsb are ported (`template/configs/`).
>
> Everything else in this directory — including the per-instrument quartets
> `mc28_*`, `a0_*`, `qsb_*`, `s58_*`, `untargeted_*`, `promote_*`, and the
> `*_shim.py` family — is **tracked and FROZEN LEGACY**: the historical record
> the session REPORTs cite, and what is currently deployed on the PC. Two
> pieces of it are still load-bearing and are NOT superseded:
> `a0_env.ps1` / `qsb_env.ps1` carry deep instrument parity (instance SHAs,
> sample streams, verdict/node re-derivation) that the generic parity rows do
> not replace — run them before either of those launches — and
> `a0_fetch.sh` / `qsb_fetch.sh` carry those instruments' own result rollups.
>
> The supervisor stack (`pysweep_run.ps1`, `untargeted_super.ps1`,
> `untargeted_status.ps1`, `untargeted_abort.ps1`,
> `untargeted_alarmtest.ps1`) is unchanged — it was already generic.

| file | what it is |
|---|---|
| `detach.c`, `builddetach.bat` | `detach.exe` — the Windows `nohup`: `CreateProcess` with `CREATE_BREAKAWAY_FROM_JOB \| DETACHED_PROCESS \| CREATE_NEW_PROCESS_GROUP \| BELOW_NORMAL_PRIORITY_CLASS`, opening its own log handles and restricting inheritance to exactly those three (otherwise the child inherits sshd's pipes and the ssh call hangs). This is what makes workers survive disconnect as a non-admin user. Usage: `detach.exe <workdir> <stdout> <stderr> <cmd> [args...]` |
| `gen_worklist.py` | derives KernelFinder `nsk` pattern strings from the chain censuses (ride length `((j−k) mod 6)+1` per loop). **Self-gating**: refuses to emit a worklist unless it reproduces the five known K=27 patterns exactly |
| `farmlaunch.ps1` | starts the 5 priority K=27 chains (idempotent) |
| `farmscale.ps1` | backfilling scheduler: keeps `$TARGET` workers alive against `worklist.txt`, skips live chains, clears stale `IntersectionFlags7.dat`, honours a `$MINFREEPCT` low-memory valve |
| `watchdog.ps1` | one backfill pass + a timestamped line in `watchdog.log` (alive count, started, free RAM). Call periodically from the Mac; it is NOT scheduled (non-admin) |
| `status.ps1` | per-worker pattern / CPU / last progress line, and prominent flagging of any `7_59*.txt` solution file |
| `farmstop.ps1` | stops all workers (both binary names) |
| `meminfo.ps1` | free/total RAM via `GlobalMemoryStatusEx` P/Invoke — WMI, `systeminfo`, and `Get-Counter` are all Access-denied for this account |
| `build64.bat` | MSVC rebuild with a 64 MB stack. **Kept only for the record — the stack was never the problem** (see REMOTE-FARM.md failure modes) |
| `install_tasks_admin.bat`, `uninstall_tasks_admin.bat` | optional, admin-only: SYSTEM tasks with `/sc ONSTART` so the farm also survives reboots. More privilege than the job needs; use only if a reboot is expected |

`../cover7/worklist_5905_tiers.txt` is the generated worklist (218 patterns,
K=29 → K=30 → K=31).
