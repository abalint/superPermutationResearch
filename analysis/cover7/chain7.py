#!/usr/bin/env python3
"""chain7.py -- kernel-parameterized instance builder + certificate assembly
for n=7 kernel chains with partial (skip) rides.

Chain format (from analysis/kernelchain7): list of tuples
    (L, k, j, sk, s, t, c)
L = global loop index (840 loops), k = arrival entry index, j = exit splice
index, sk = skip = 5 - ((j-k) % 6), s = hop source perm, t = hop target perm,
c = hop cost; last element has j = None (full ride, chain terminus).

Semantics (matches certificate.py compile_certificate):
- kernel loops  = the chain loops, in order; K-1 hop doors.
- forest roots  = RIDDEN orbits only (arrival k .. exit j of each loop).
- columns       = the 720 - |roots| other orbits, incl. skipped kernel orbits.
- rows          = oriented non-chain loops whose 5 children are all columns.
- disabled_splices = for each chain loop, its splices sourced in its own
  skipped orbits (compile_certificate's slack = root ∩ child orbits).
"""
from __future__ import annotations

import math
from itertools import permutations

from certificate import (
    alphabet_for_n,
    canonical_rotation,
    compile_certificate,
    door,
    format_loop,
    loop_of,
    loop_orbits,
    loop_splices,
    oriented_row,
    tv,
    inverse_tv,
    _build_splice_table,
)

N = 7
ALPHA = "1234567"
NE = 6  # orbits (and splices) per loop at n=7

# ---------------------------------------------------------------- loop tables
loops: list[tuple[str, str]] = []
for _pivot in ALPHA:
    _rest = [c for c in ALPHA if c != _pivot]
    _seen = set()
    for _p in permutations(_rest):
        _nk = canonical_rotation("".join(_p))
        if _nk not in _seen:
            _seen.add(_nk)
            loops.append((_pivot, _nk))
li = {lp: i for i, lp in enumerate(loops)}
entries: list[list[str]] = []
sources: list[list[str]] = []
orbitsets: list[frozenset[str]] = []
for (_a, _C) in loops:
    _e = _C + _a
    _es, _ss, _os = [], [], set()
    for _ in range(NE):
        _es.append(_e)
        _ss.append(_e[-1] + _e[:-1])
        _os.add(canonical_rotation(_e))
        _e = tv(_e)
    entries.append(_es)
    sources.append(_ss)
    orbitsets.append(frozenset(_os))

ALL_ORBITS = frozenset().union(*orbitsets)
assert len(ALL_ORBITS) == 720 and len(loops) == 840


# ------------------------------------------------------------ chain utilities
def verify_chain(sol) -> tuple[int, int, int, int, int, int]:
    """Re-verify a chain; returns (K, Sigma, f4, f5, f6, V)."""
    from collections import Counter

    ID = canonical_rotation(ALPHA)
    assert canonical_rotation(entries[sol[0][0]][sol[0][1]]) == ID
    piv = loops[sol[0][0]][0]
    seenL, orbs, ssum, f = set(), set(), 0, Counter()
    for idx, (L, k, j, sk, s, t, c) in enumerate(sol):
        assert loops[L][0] == piv
        assert L not in seenL
        seenL.add(L)
        assert not (orbitsets[L] & orbs)
        orbs |= orbitsets[L]
        if j is None:
            # terminal loop: partial ride allowed (skip sk, no hop needed)
            assert idx == len(sol) - 1 and 0 <= sk <= 5
            ssum += sk
            continue
        assert s == sources[L][j] and t == door(s, c)
        assert sk == 5 - ((j - k) % NE)
        ssum += sk
        f[c] += 1
        Ln, kn = sol[idx + 1][0], sol[idx + 1][1]
        assert loop_of(t) == loops[Ln] and entries[Ln][kn] == t
    K = len(sol)
    V = K - ssum - 5 * f[4] - 10 * f[5] - 15 * f[6]
    return K, ssum, f[4], f[5], f[6], V


def ridden_orbits_of(L: int, k: int, j, sk: int = 0) -> set[str]:
    """Orbits ridden by chain loop L arriving at entry k, exiting splice j.
    j=None -> terminal loop, riding NE - sk orbits from the arrival."""
    if j is None:
        return {
            canonical_rotation(entries[L][(k + d) % NE])
            for d in range(NE - sk)
        }
    return {
        canonical_rotation(entries[L][(k + d) % NE])
        for d in range(((j - k) % NE) + 1)
    }


def chain_roots(sol) -> set[str]:
    roots: set[str] = set()
    for (L, k, j, sk, s, t, c) in sol:
        roots |= ridden_orbits_of(L, k, j, sk)
    return roots


def chain_skipped(sol) -> list[tuple[int, set[str]]]:
    """Per chain loop: (global loop index, its skipped orbit set)."""
    out = []
    for (L, k, j, sk, s, t, c) in sol:
        skipped = set(orbitsets[L]) - ridden_orbits_of(L, k, j, sk)
        assert len(skipped) == sk
        out.append((L, skipped))
    return out


# ----------------------------------------------------------- instance builder
def build_instance_from_chain(sol) -> dict:
    """gain1.DLX-compatible instance for an arbitrary chain kernel."""
    K, ssum, f4, f5, f6, V = verify_chain(sol)
    kernel = [loops[x[0]] for x in sol]
    hops = []
    for (L, k, j, sk, s, t, c) in sol[:-1]:
        hops.append(
            {
                "source": s,
                "target": t,
                "cost": c,
                "replaced_loop": format_loop(loops[L]),
            }
        )
    roots = chain_roots(sol)
    assert len(roots) == NE * K - ssum
    columns = ALL_ORBITS - roots
    assert len(columns) % (N - 2) == 0
    chainL = {x[0] for x in sol}
    rows = []
    for Lx in range(len(loops)):
        if Lx in chainL:
            continue
        for e in entries[Lx]:
            children = []
            cursor = e
            for _ in range(N - 2):
                children.append(canonical_rotation(cursor))
                cursor = tv(cursor)
            if all(ch in columns for ch in children):
                rows.append(
                    {
                        "loop": loops[Lx],
                        "entry": e,
                        "parent_orbit": canonical_rotation(inverse_tv(e)),
                        "children": tuple(children),
                    }
                )
    return {
        "n": N,
        "kernel": kernel,
        "hops": hops,
        "roots": roots,
        "columns": sorted(columns),
        "rows": rows,
        "chain": sol,
        "meta": {"K": K, "Sigma": ssum, "f4": f4, "f5": f5, "f6": f6, "V": V,
                 "R": len(columns) // (N - 2)},
    }


# ------------------------------------------------------- certificate assembly
def disabled_splices_for(sol) -> list[dict]:
    out = []
    for L, skipped in chain_skipped(sol):
        if not skipped:
            continue
        for source, target, orbit in loop_splices(loops[L]):
            if orbit in skipped:
                out.append(
                    {
                        "source": source,
                        "target": target,
                        "replaced_loop": format_loop(loops[L]),
                    }
                )
    return out


def walk_order_chain(inst: dict, chosen: list[dict], disabled: list[dict]):
    """Order chosen rows by first-entry during the compiled walk (riding-loop
    recorded), honoring hop overrides AND disabled splices."""
    selected = list(inst["kernel"]) + [r["loop"] for r in chosen]
    overrides: dict[str, tuple[str, int]] = {
        src: (tgt, 2) for src, (tgt, _, _) in _build_splice_table(selected).items()
    }
    for h in inst["hops"]:
        overrides[h["source"]] = (h["target"], h["cost"])
    for d in disabled:
        overrides.pop(d["source"], None)
    by_entry = {r["entry"]: r for r in chosen}
    current = ALPHA
    current_loop = inst["kernel"][0]
    ordered = []
    for _ in range(math.factorial(N) - 1):
        target, cost = overrides.get(current, (door(current, 1), 1))
        if cost != 1:
            if cost == 2 and target in by_entry:
                ordered.append((by_entry.pop(target), current_loop))
            current_loop = loop_of(target)
        current = target
    if by_entry:
        raise AssertionError(f"{len(by_entry)} rows never opened by the walk")
    return ordered


def assemble_certificate_chain(inst: dict, chosen: list[dict]) -> dict:
    disabled = disabled_splices_for(inst["chain"])
    rows = [
        oriented_row(r["entry"], riding_loop, N)
        for r, riding_loop in walk_order_chain(inst, chosen, disabled)
    ]
    return {
        "format": "superperm-loop-certificate-v1",
        "n": N,
        "start_perm": ALPHA,
        "kernel_loops": [format_loop(lp) for lp in inst["kernel"]],
        "hop_doors": inst["hops"],
        "rows": rows,
        "disabled_splices": disabled,
    }


def compile_chain_cover(inst: dict, chosen: list[dict]):
    """Assemble + compile; returns (word, cert). Raises on any violation --
    the walk replay in compile_certificate is the final arbiter."""
    cert = assemble_certificate_chain(inst, chosen)
    word, path, costs = compile_certificate(cert)
    return word, cert, costs


# -------------------------------------------------- standard kernel as chain
def standard_chain() -> list:
    """The standard K=5 kernel expressed in chain-tuple form (positive
    control; skip = 0 everywhere)."""
    import gain1

    kernel, hops = gain1.standard_kernel(N)
    sol = []
    arrival = ALPHA  # start perm is the arrival entry of loop 0
    for i, lp in enumerate(kernel):
        L = li[lp]
        k = entries[L].index(arrival)
        if i < len(hops):
            s = hops[i]["source"]
            j = sources[L].index(s)
            sk = 5 - ((j - k) % NE)
            sol.append((L, k, j, sk, s, hops[i]["target"], hops[i]["cost"]))
            arrival = hops[i]["target"]
        else:
            sol.append((L, k, None, 0, None, None, None))
    return sol
