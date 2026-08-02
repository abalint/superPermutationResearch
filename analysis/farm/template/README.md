# The farm harness template (s64 P5)

**One** `farm_ship.sh` / `farm_fetch.sh` / `farm_env.ps1`, parameterized by a
per-instrument config, plus **one** STATUS emitter (`pylib/farmstatus.py`)
that encodes the heartbeat contract in code instead of prose.

Before this, every instrument got its own quartet — `<tag>_ship.sh`,
`<tag>_shim.py`, `<tag>_env.ps1`, `<tag>_fetch.sh` — about 54% verbatim
boilerplate by normalized line-set intersection (s63 survey), ~2,900 tracked
lines across four instrument families. The genuinely instrument-specific part
is small. The cost was not the lines, it was that **a fix in one site reached
no others**: the bash-3.2 `mapfile` bug, the CRLF sha corruption, the
escape-scan `.txt` trap and the stall-minutes mis-sizing each had to be
rediscovered per instrument, and the two documented s52b bugs were both
violations of a contract that existed only as prose in a docstring.

## Layout

```
analysis/farm/template/
  farm_ship.sh        ship + verify (Mac).  Never launches.
  farm_fetch.sh       fetch + adjudicate (Mac).  Refuses to call an
                      unearned negative a negative.
  farm_env.ps1        env + PARITY check (PC).  Exit code = failure count.
  farmlayout.py       repo-vs-checkout path resolution + exec_instrument
                      (ships to the farm root next to the adapter)
  <tag>_adapter.py    the instrument-specific adapter (ships to the farm root)
  configs/
    <tag>.conf        the config: payload, shards, stall minutes, args,
                      gate commands, alarm/scope notes
    <tag>.parity.tsv  the parity rows farm_env.ps1 runs on the PC
    <tag>.gate.md     (optional) the gate text a shard writes into its out dir

pylib/farmstatus.py   the STATUS heartbeat contract, once
tests_py/test_farmstatus.py   its pin (incl. the 13 alarm-regex cases)
```

The supervisor itself (`pysweep_run.ps1` + `untargeted_super.ps1` +
`untargeted_status.ps1` + `untargeted_abort.ps1`) is unchanged and stays where
it is — it was already generic. This template is the matching generic
**client** side.

## Using it

```bash
bash analysis/farm/template/farm_ship.sh mc28 --manifest   # print, ship nothing
bash analysis/farm/template/farm_ship.sh mc28 --dry        # + the PC config
bash analysis/farm/template/farm_ship.sh mc28 --scripts    # adapter/env only
bash analysis/farm/template/farm_ship.sh mc28              # ship + verify
# launch/abort/status: the exact lines are printed by the ship
bash analysis/farm/template/farm_fetch.sh mc28 <tag>       # fetch + adjudicate
```

Env knobs: `FARM_HOST` (ssh target), `FARM_SCRATCH=<subdir>` (deploy the whole
harness under one throwaway subdirectory — how a template change is proven on
the PC without touching a live deployment), `FARM_SKIP_SIDEFILES=1` (harness
work only; it also removes the side-file check, so never on a pre-launch ship).

## Adding an instrument

1. **Thin case** — the instrument already speaks `--shard i/N --out DIR` and
   writes its own STATUS (a0, qsb, paircuts, enumext). The adapter is two
   lines:

   ```python
   import farmlayout
   farmlayout.exec_instrument("analysis", "counting", "s62", "a0gate.py")
   ```

2. **Translating case** — the instrument needs its args reshaped, or writes no
   heartbeat (mc28, promote, lswap). The adapter translates the arg shape and
   drives `FarmStatus`; see `mc28_adapter.py`, which takes its heartbeat by
   rebinding `mcover_search.prepare` (one call = one processed cover) so the
   engine source stays untouched and the tick cannot drift from the real work
   stream.

3. Write `configs/<tag>.conf` and `configs/<tag>.parity.tsv`.
4. `farm_ship.sh <tag> --dry` to check the manifest, then ship.

**Every new instrument must have its terminal summary diffed against the alarm
regex before it is driven through the supervisor.** That rule is now
executable: `farmstatus.check_summary(text)` returns the lines that would
banner, and `farmstatus.safe_print` refuses to emit one at all.

## The STATUS contract in one screen

Full derivation, with `untargeted_super.ps1` line references, is the module
docstring of `pylib/farmstatus.py`. The short form:

| clause | rule | what broke without it |
|---|---|---|
| file | `STATUS*` in `--out`, append, line-buffered | a killed shard loses its history |
| progress row | `<ts>\t<label>\t<i>/<n>\t<note>` — the `i/n` field needs tabs on **both** sides | a trailing `i/n` is not counted at all |
| units | the supervisor counts **rows** and reads `<n>` from the row: rows and `<n>` must share one unit | s52b: a FINISHED run read `50/2462 (2%)` |
| non-progress | DONE / ESCAPE / notes carry **no** `i/n` field | they get counted as progress and redefine the total |
| terminal | `<ts>\tDONE\t<summary>` | weak completion verdict only |
| escape | `<ts>\tESCAPE\t<detail>` → ALARM.txt | the find channel |
| stdout | must not match `(?i)Traceback\|MemoryError\|^\s*!!\|\*\*\*\|ESCAPES\s+[1-9]\|NOVEL[^:\r\n]*:\s*[1-9]` | s52b: `novel-candidate classes: 0` bannered all 24 healthy shards |
| products | **no `.txt` in `--out` that is not a real product** | `untargeted_status.ps1:92` counts every `*.txt` as an ESCAPE CANDIDATE (4 recurrences through s63) |
| newlines | everything written with `newline=""` | Windows CRLF vs a sha over pre-translation bytes: every shard exits 4 |

`FarmStatus.work()` is the whole point of the class: the caller ticks **real
work** and the emitter converts to rows, so `rows == units // tick` by
construction and the declared total is derived from the same `tick`.

Sizing the tick is sizing the stall threshold: one row every
`tick × per-unit-seconds`, and `-StallMinutes` must exceed that gap by a wide
margin. **Never raise `--tick` without raising `-StallMinutes` with it.**

## What is ported, and what is still frozen

| instrument | config | adapter | ship/env | fetch adjudication |
|---|---|---|---|---|
| **mc28** | `configs/mc28.conf` | `mc28_adapter.py` (translating) | ported, PC-verified | ported (canonical stats schema) |
| **a0** | `configs/a0.conf` | `a0_adapter.py` (thin) | ported | generic tier only — see below |
| **qsb** | `configs/qsb.conf` | `qsb_adapter.py` (thin) | ported | generic tier only — see below |
| s58, promote, i4a, lswap, paircuts, enumext, untargeted | — | — | — | frozen legacy |

Everything under `analysis/farm/` is now **tracked**. The per-instrument
quartets stay in place as **FROZEN LEGACY**: they are the historical record
(s52b/s62/s63 sessions cite them by path), they are what is currently deployed
on the PC, and for a0/qsb they still hold work the template does not yet carry:

* **a0/qsb deep parity.** `a0_env.ps1` rebuilds all six A0 instances on the PC
  and SHA-compares them against a Mac-computed table (plus a dlxrun eps-lane
  probe); `qsb_env.ps1` redraws the Mac's sample stream, rebuilds six pinned
  instances and re-derives verdicts and node counts. The generic parity rows in
  `configs/{a0,qsb}.parity.tsv` prove the *import chain* resolves farm-side and
  nothing more. **Run the frozen `*_env.ps1` before either of those launches.**
* **a0/qsb fetch headlines.** `a0_fetch.sh` and `qsb_fetch.sh` compute
  instrument-specific rollups (verdict mix per lane, decisions/s curves) from
  those instruments' own stats schemas. `farm_fetch.sh` adjudicates the
  *generic* tier — rc, DONE row, partial markers, partition closure — from the
  canonical `farmstatus` schema, which those two instruments do not write yet.
  Port them by moving them onto `FarmStatus.finish()`.

## PC verification of this template (s64 P5, 2026-08-02)

Approved scope: env-check + `-DryRun` only, scratch tag, farm idle
(`Get-Process -Name upyw` = 0 — process **name**, never a `pgrep -f`-style
command-line match, which catches the monitor's own command line).

* Deployed to `F:\superpermFarm\untargeted\s64tpl_scratch\`, run dir
  `runs\s64tpl`; **both removed afterwards**, farm restored to 33 root files.
* `farm_env.ps1 -Tag mc28 -Full`: **ENV OK, 0 failures** — manifest 7/7
  re-hashed identical, P1 12 covers / 2,127 nodes / brute-force census, P2 224
  covers / 47,623 nodes / SAT-path census, P2b adapter self-test, **P3 real
  branch 200 covers, K histogram {8: 200}, 29,609,908 nodes, NO walk** (the
  s63 pin, exactly). P3 wall 59 s vs 33 s on the Mac.
* Dry smoke, 24 shards: **24/24 DONE, 0 failed, ESCAPES=0, stats rows=24, edge
  rows 0, `.txt` product files = 0, stalled none** — the s63 `mc28dry2` result
  reproduced. Shard 0 sized `8586 covers, 43 ticks`, shard 23 `8585`; STATUS
  written on Windows contained **0 CR bytes**.
* `untargeted_alarmtest.ps1` on the PC: **ALARM REGEX OK: 0 failures** (13
  cases). Mirrored in `tests_py/test_farmstatus.py` so the Python and
  PowerShell readings of that one string can never diverge silently.
