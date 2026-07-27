#!/usr/bin/env python3
"""Positive control: the parameterized builder must reproduce gain1's own
standard-kernel instance exactly, and (control run) its covers must compile
to a valid 5907 word via the chain-aware assembler (disabled = empty)."""
import sys
import time

import gain1
import chain7
from chain7 import build_instance_from_chain, standard_chain, compile_chain_cover

sol = standard_chain()
K, S, f4, f5, f6, V = chain7.verify_chain(sol)
print(f"standard chain: K={K} Sigma={S} V={V}")
assert (K, S) == (5, 0)

mine = build_instance_from_chain(sol)
ref = gain1.build_instance(7)

assert mine["kernel"] == ref["kernel"], "kernel mismatch"
assert mine["hops"] == ref["hops"], "hops mismatch"
assert mine["roots"] == ref["roots"], "roots mismatch"
assert mine["columns"] == ref["columns"], "columns mismatch"
key = lambda r: (r["loop"], r["entry"])
mrows = {key(r): (r["parent_orbit"], r["children"]) for r in mine["rows"]}
rrows = {key(r): (r["parent_orbit"], r["children"]) for r in ref["rows"]}
assert mrows == rrows, "rows mismatch"
assert chain7.disabled_splices_for(sol) == []
print(f"INSTANCE MATCH: {len(mine['columns'])} columns, {len(mine['rows'])} rows,"
      f" {len(mine['roots'])} roots, R={mine['meta']['R']}")

if "--search" in sys.argv:
    deadline = time.monotonic() + 600
    attempt, max_nodes = 0, 200_000
    chosen = None
    while time.monotonic() < deadline and chosen is None:
        attempt += 1
        dlx = gain1.DLX(mine, seed=100 + attempt)
        dlx.max_nodes = max_nodes
        try:
            chosen = dlx.search(deadline)
        except TimeoutError:
            print(f"attempt {attempt}: restart after {dlx.nodes} nodes "
                  f"({dict(dlx.stats)})", flush=True)
            max_nodes = min(max_nodes * 2, 8_000_000)
            continue
        print(f"attempt {attempt}: {'SOLVED' if chosen else 'exhausted'} "
              f"({dict(dlx.stats)}, {dlx.nodes} nodes)", flush=True)
    if chosen is None:
        sys.exit("control search failed")
    rep = gain1.check_cover(mine, chosen)
    print("check_cover:", rep["valid"])
    word, cert, costs = compile_chain_cover(mine, chosen)
    print(f"compiled word length = {len(word)} (expect 5907)")
    assert gain1.verify_word(word, 7)
    with open("control_5907.txt", "w") as fh:
        fh.write(word)
    print("wrote control_5907.txt")
