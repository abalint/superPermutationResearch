#!/usr/bin/env python3
"""qsb_adapter.py -- the s62 QS-B verdict-mix sweep, as a farm adapter (s64 P5).
Port of the 86-line `analysis/farm/qsb_shim.py`.

`qsbsweep.py` already speaks `--shard/--out/--limit/--dry-run` and already
writes the STATUS heartbeat, so this is the THIN case: locate and exec.

The one QS-B-specific hazard worth keeping in front of the operator: an UNSAT
is a NORMAL, EXPECTED result here -- it IS most of the product, since the sweep
measures the UNSAT FRACTION -- so an UNSAT must never banner.  Only a SAT does,
and a SAT here is a cover of an OPEN n=7 chain, i.e. a 5905 world-record
candidate.  See `configs/qsb.conf`.
"""
import farmlayout

farmlayout.exec_instrument("analysis", "counting", "s62", "qsbsweep.py")
