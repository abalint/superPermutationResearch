#!/usr/bin/env python3
"""a0_adapter.py -- the s62 A0 gate sweep, as a farm adapter (s64 P5).
Port of the 86-line `analysis/farm/a0_shim.py`.

`a0gate.py` already speaks `--shard/--out/--limit/--dry-run/--time-limit` and
already writes the STATUS heartbeat, so this is the THIN case: locate and exec.
Everything else (why an adapter exists, the -Mode token, the layout probe) is
`farmlayout.exec_instrument`; the supervisor-compatibility notes are
`configs/a0.conf`.

The one A0-specific fact worth keeping in front of the operator: ONE cell per
shard means a shard is legitimately SILENT for the whole `--time-limit`.
Launch with STALL_MINUTES > time-limit/60 (the config says 20 for TL 600) or
every healthy shard is flagged STALL.
"""
import farmlayout

farmlayout.exec_instrument("analysis", "counting", "s62", "a0gate.py")
