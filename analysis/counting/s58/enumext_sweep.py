#!/usr/bin/env python3
"""s58 EXTENDED-CENSUS SWEEP -- shardable driver for out/s57/express/enum_ext.py.

docs/SWEEP-QUEUE.md "## extended-census Sigma15-16 sweep".

WHAT IT ANSWERS.  The n=7 chain census (analysis/cover7) enumerates a
RESTRICTED family: pivot-7 loops only, reversal door only.  33 of the 221 known
record words live outside it.  `enum_ext.py` implements the 5-block extended
frame the corpus actually demands and proved it adds nothing at Sigma <= 12
(5 = 5 chains) and Sigma <= 14 (26 = 26, 88.8M nodes, EXHAUSTED).  The
remaining 197 census chains sit at Sigma 15..16, which was never swept.  This
runs that band: does the extended frame add ANY chain at the 5905-relevant
scores?  A new chain would be a new 5905/5906 route candidate for the cover
pipeline.

SHARD KEY -- and a correction.  SWEEP-QUEUE proposed sharding on "whatever
enum_ext.py's outermost loop iterates", flagged there as an untested claim.  It
is wrong: `cmd_dfs` has no outer loop.  It seeds a SINGLE root

    L0 = the pivot-7 loop containing the identity orbit, k0 = its entry index

and recurses.  The sound key is therefore the search FRONTIER: expand the tree
to `--depth` d, then deal those subtree roots round-robin to the shards.  The
partition is exact because the transition relation is local -- every prune
(`ssum > pmax`, `V - (pmax - ssum) > target`, `V + (141 - K) < target`) reads
only the current node, never a sibling -- so no subtree can affect another, and
the union of shard results is precisely the single-process result.  `seen`
dedups by full path, which is unique per node of a tree, so it never needs to
be shared across shards.

The transition relation lives in ONE place here (`expand`), used by both the
frontier builder and the shard DFS, so the two can never drift.  It is
enum_ext.cmd_dfs's inner loop verbatim in meaning; `enumext_oracle.py` pins
that by reproducing enum_ext's published node and chain counts exactly.

usage:
  enumext_sweep.py --shard i/N --out DIR [--target 15] [--pmax 16]
                   [--max-break 2] [--depth 3] [--dry-run] [--limit K]
                   [--max-nodes N] [--tl SEC]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(REPO, "out", "s57", "express"),
          os.path.join(REPO, "analysis", "cover7"),
          os.path.join(REPO, "..", "extraDocs",
                       "superpermutation-examples", "scripts")):
    if os.path.isdir(p):
        sys.path.insert(0, os.path.abspath(p))

import chain7  # noqa: E402
import enum_ext as EX  # noqa: E402
from enum_ext import E, ENTRY_ORB, NE  # noqa: E402
from chain7 import loops, entries, canonical_rotation  # noqa: E402

# pivot of a loop, precomputed: the DFS asks `loops[M][0] != "7"` per edge
PIV7 = [loops[L][0] == "7" for L in range(840)]


def root_state():
    """enum_ext.cmd_dfs's seed, verbatim."""
    ID = canonical_rotation(chain7.ALPHA)
    L0 = [L for L in range(840)
          if ID in chain7.orbitsets[L] and loops[L][0] == "7"][0]
    k0 = [canonical_rotation(e) for e in entries[L0]].index(ID)
    # (L, k, mask, used, K, ssum, path, nbreak, ngen)
    return (L0, k0, 0, 1 << L0, 1, 0, (), 0, 0)


def is_hit(L, k, mask, K, ssum, target):
    """Terminal test: V == target and the terminal loop can ride ALL orbits."""
    if K - ssum != target:
        return False
    return not any(mask >> ENTRY_ORB[L][(k + d) % NE] & 1 for d in range(NE))


def expand(st, pmax, target, max_break):
    """Children of a node -- the single definition of the transition."""
    L, k, mask, used, K, ssum, path, nbreak, ngen = st
    V = K - ssum
    if ssum > pmax or V - (pmax - ssum) > target:
        return
    if V + (141 - K) < target:
        return
    for sk in range(NE):
        j = (k - 1 - sk) % NE
        bits = 0
        ok = True
        for d in range(((j - k) % NE) + 1):
            o = ENTRY_ORB[L][(k + d) % NE]
            if mask >> o & 1:
                ok = False
                break
            bits |= 1 << o
        if not ok:
            continue
        nm = mask | bits
        for blk, M, ka in E[L][j]:
            if used >> M & 1 or nm >> ENTRY_ORB[M][ka] & 1:
                continue
            if not PIV7[M] and nbreak >= max_break:
                continue
            yield (M, ka, nm, used | (1 << M), K + 1, ssum + sk,
                   path + ((L, k, j, sk, blk),),
                   nbreak + (not PIV7[M]), ngen + (blk != (2, 1, 0)))


def frontier(depth, pmax, target, max_break):
    """Expand to `depth`, returning (roots, hits, nodes).

    `hits` are chains completed at depth < depth -- they belong to no subtree,
    so they are reported by the frontier builder itself (every shard rebuilds
    the identical frontier, and only shard 0 records them).
    """
    cur = [root_state()]
    nodes = 1
    hits = []
    if is_hit(*cur[0][:2], cur[0][2], cur[0][4], cur[0][5], target):
        hits.append(cur[0])
    for _ in range(depth):
        nxt = []
        for st in cur:
            for ch in expand(st, pmax, target, max_break):
                nodes += 1
                if is_hit(ch[0], ch[1], ch[2], ch[4], ch[5], target):
                    hits.append(ch)
                nxt.append(ch)
        cur = nxt
    return cur, hits, nodes


def sweep(roots, pmax, target, max_break, max_nodes, tl, status, label_every):
    """Iterative DFS over the assigned subtrees.  -> stats dict."""
    t0 = time.time()
    nodes = 0
    seen = set()
    found = []
    capped = False
    for ri, root in enumerate(roots):
        stack = [root]
        while stack:
            st = stack.pop()
            nodes += 1
            if nodes >= max_nodes or (nodes % 65536 == 0
                                      and time.time() - t0 > tl):
                capped = True
                break
            if is_hit(st[0], st[1], st[2], st[4], st[5], target):
                key = st[6]
                if key not in seen:
                    seen.add(key)
                    found.append(st)
            stack.extend(expand(st, pmax, target, max_break))
        if capped:
            break
        if status and (ri + 1) % label_every == 0:
            status(ri + 1, nodes, len(found))
    return dict(nodes=nodes, found=found, capped=capped,
                secs=time.time() - t0)


def ser(path):
    """Chain path -> a stable string key (L,k,j,sk,blk per hop)."""
    return ";".join(f"{L},{k},{j},{sk},{''.join(map(str, blk))}"
                    for (L, k, j, sk, blk) in path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=15)
    ap.add_argument("--pmax", type=int, default=16)
    ap.add_argument("--max-break", type=int, default=2)
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0,
                    help="probe mode: only the first K subtrees of this shard")
    ap.add_argument("--max-nodes", type=int, default=10**12)
    ap.add_argument("--tl", type=float, default=1e9)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    si, sn = (int(x) for x in a.shard.split("/"))
    os.makedirs(a.out, exist_ok=True)
    tag = f"s{si:02d}"
    st = open(os.path.join(a.out, "STATUS"), "a", buffering=1)

    def stamp():
        return time.strftime("%Y-%m-%d %H:%M:%S")

    t0 = time.time()
    roots, hits, fnodes = frontier(a.depth, a.pmax, a.target, a.max_break)
    mine = [r for k, r in enumerate(roots) if k % sn == si]
    if a.limit:
        mine = mine[:a.limit]
    # chains completed above the frontier belong to no subtree
    myhits = hits if si == 0 else []

    if a.dry_run:
        st.write(f"{stamp()}\tDRYRUN\t0/{len(mine)}\tsizing only\n")
        st.write(f"{stamp()}\tDONE\tdry-run: frontier {len(roots)} subtrees at "
                 f"depth {a.depth} ({fnodes} nodes, {time.time() - t0:.1f}s), "
                 f"{len(mine)} mine, {len(hits)} above-frontier hits\n")
        with open(os.path.join(a.out, f"enumext_stats_{tag}.tsv"), "w") as fh:
            fh.write("shard\tfrontier\tmine\tfrontier_nodes\tabove_hits"
                     "\ttarget\tpmax\tmax_break\tdepth\n")
            fh.write(f"{si}\t{len(roots)}\t{len(mine)}\t{fnodes}\t{len(hits)}"
                     f"\t{a.target}\t{a.pmax}\t{a.max_break}\t{a.depth}\n")
        print(f"dry-run shard {si}/{sn}: frontier={len(roots)} mine={len(mine)} "
              f"frontier_nodes={fnodes} above_hits={len(hits)}")
        st.close()
        return 0

    st.write(f"{stamp()}\tSTART\t0/{len(mine)}\tfrontier {len(roots)} at depth "
             f"{a.depth}, target V={a.target} pmax={a.pmax} "
             f"max_break={a.max_break}\n")
    every = max(1, len(mine) // 200)

    def tick(done, nodes, nfound):
        st.write(f"{stamp()}\tsubtree\t{done}/{len(mine)}\tnodes={nodes} "
                 f"found={nfound}\n")

    res = sweep(mine, a.pmax, a.target, a.max_break, a.max_nodes, a.tl,
                tick, every)

    allhits = myhits + res["found"]
    gen = sum(1 for h in allhits if h[8] > 0)
    piv = sum(1 for h in allhits if h[7] > 0)
    chains_p = os.path.join(a.out, f"enumext_chains_{tag}.tsv")
    with open(chains_p, "w") as fh:
        fh.write("#target\tpmax\tmax_break\tshard\n")
        fh.write(f"#{a.target}\t{a.pmax}\t{a.max_break}\t{si}/{sn}\n")
        fh.write("K\tssum\tV\tnbreak\tngen\tterm_L\tterm_k\tpath\n")
        for h in allhits:
            L, k, mask, used, K, ssum, path, nbreak, ngen = h
            fh.write(f"{K}\t{ssum}\t{K - ssum}\t{nbreak}\t{ngen}\t{L}\t{k}"
                     f"\t{ser(path)}\n")

    status = "CAPPED" if res["capped"] else "EXHAUSTED"
    with open(os.path.join(a.out, f"enumext_stats_{tag}.tsv"), "w") as fh:
        fh.write("shard\tsubtrees\tnodes\tstatus\tchains\tpivbreak\tgen"
                 "\ttarget\tpmax\tmax_break\tdepth\tsecs\n")
        fh.write(f"{si}\t{len(mine)}\t{res['nodes']}\t{status}\t{len(allhits)}"
                 f"\t{piv}\t{gen}\t{a.target}\t{a.pmax}\t{a.max_break}"
                 f"\t{a.depth}\t{res['secs']:.1f}\n")
    if res["capped"]:
        # a capped shard is NOT a negative result -- say so loudly
        print(f"*** SHARD {si} CAPPED at {res['nodes']} nodes -- coverage is "
              f"INCOMPLETE, this shard proves nothing ***", flush=True)
    if gen or piv:
        print(f"*** SHARD {si}: {gen} chain(s) using a generalized door, "
              f"{piv} with a pivot excursion -- OUTSIDE the census frame ***",
              flush=True)
    st.write(f"{stamp()}\tDONE\tshard {si}: {len(mine)} subtrees, "
             f"{res['nodes']} nodes, {status}, {len(allhits)} chains "
             f"({piv} pivbreak, {gen} gen), {res['secs']:.1f}s\n")
    st.close()
    print(f"shard {si}/{sn}: subtrees={len(mine)} nodes={res['nodes']} "
          f"{status} chains={len(allhits)} pivbreak={piv} gen={gen} "
          f"{res['secs']:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
