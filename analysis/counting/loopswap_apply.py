#!/usr/bin/env python3
"""s44: I5 — the loop-swap applier (the s43 tier made executable).

s43 found the cover-CHANGING, door-preserving loop-swap tier via
tail-conjugacy: inequivalent classes sharing literal relabel-conjugate
traversal suffixes, whose aligned-frame diff is k cycle-disjoint
2-loops swapped for k others riding k swapped rotors, ALL doors
identical, allocation preserved. In i4a replay coordinates (a tight
walk = deterministic replay of (start perm, entry sets, door list)),
doors identical means the A→B edit is pure ENTRY-SET REPLACEMENT: the
rule is (entries removed, entries added, door edits — usually none),
extracted literally from each anatomized pair in its aligned frame
(orientation + tail relabeling; the shared head guarantees a common
start perm, so both sides replay from the same origin).

Modes:
  extract  — read a tail-conjugacy pairs TSV, align each NEW pair at
             its recorded depth/orientation, diff the two structures,
             emit the rule table (one directed rule per pair direction,
             deduped up to relabeling; cross-referenced against the
             s43 swap-signature census where available).
  oracle   — extract, then verify every pair re-derives: applying the
             A→B rule to A's structure and replaying must reproduce
             the aligned B string BYTE-IDENTICALLY (and B→A likewise).
             Exit 0 iff all pairs pass.
  apply-sym— the conjugated sweep: every relabeled instance (n! per
             directed rule) against every walk in the given dirs, both
             orientations. Fast path: per-walk flat entry sets as
             perm-id ints + an inverted posting index (entry perm →
             walks), progressive posting intersection per instance,
             then exact edit + replay only on surviving candidates.
             Products are canon-gated inline against the committed
             class indexes (m3_check convention): rediscoveries become
             natural-move-graph edges, novel classes are written +
             bannered, shorter-than-record products are candidates
             (banner, drop everything). STILL run m3_check on any
             novel/shorter file before believing it.
             --record <int> overrides the record length used for the
             longer/equal/shorter split (default 872 at n=6, 5906
             otherwise). Needed for ABOVE-record corpora such as the
             s49 w4 lift shells (--record 873 / 5907), where the
             default silently discards every product as "longer".

Usage:
  python3 analysis/counting/loopswap_apply.py oracle
  python3 analysis/counting/loopswap_apply.py extract -n 6 \
      data/tailconj/tail_pairs_n6_a240.tsv --dirs data/upstream872 \
      --min-perms 400 --rules-out out/s44/rules_n6.tsv
  python3 analysis/counting/loopswap_apply.py apply-sym -n 6 \
      --rules out/s44/rules_n6.tsv --dirs data/upstream872 \
      --out out/s44/products_n6
"""
import hashlib
import os
import sys
from collections import Counter
from itertools import permutations
from math import factorial

import pathlib, sys; sys.path.insert(0, str(next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pylib").is_dir())))  # noqa: E401,E402,E501  <- pylib bootstrap, the ONE sanctioned sys.path line (docs/ARCHITECTURE.md)
import pylib  # noqa: E402
pylib.add_paths("analysis/counting")
from i4a_apply import edit, replay, structure
from loop_ledger_probe import first_visit_path, weight
from m3_check import SUPPLEMENTARY, canon, load_index
from tail_conjugacy_census import Walk
from tail_pair_anatomy import aligned_strings

HERE = os.path.dirname(os.path.abspath(__file__))

# canonical oracle/extraction sets (the s43 anatomized tiers)
DEFAULT_SETS = {
    6: ("data/tailconj/tail_pairs_n6_a240.tsv", ["data/upstream872"], 400),
    7: ("data/tailconj/tail_all_n7.tsv",
        ["data/upstream5906", "data/novel5906"], 500),
}


def s(p):
    return "".join(map(str, p))


def P(t):
    return tuple(int(c) for c in t)


def load_pairs(tsv, min_perms):
    """NEW pairs from a census TSV: (a, b, deepest_d, orient)."""
    pairs = []
    with open(tsv) as fh:
        next(fh)
        for line in fh:
            a, b, d, sp, orient, status = line.rstrip("\n").split("\t")
            if int(sp) >= min_perms and status != "KNOWN-EDGE":
                pairs.append((a, b, int(d), orient))
    return pairs


def file_map(dirs):
    files = {}
    for d in dirs:
        for f in sorted(os.listdir(d)):
            if f.endswith(".txt"):
                files[f] = os.path.join(d, f)
    return files


def extract_rule(ra, rb, n):
    """The A→B structure diff in the aligned frame, or (None, reason).
    Rule = (ents_out, ents_in, doors_out, doors_in), all literal perms."""
    Ea, Da, sa = structure(first_visit_path(ra, n))
    Eb, Db, sb = structure(first_visit_path(rb, n))
    if sa != sb:
        return None, "start-perm mismatch (heads share no perm)"
    fa = set().union(*Ea.values())
    fb = set().union(*Eb.values())
    rule = (
        tuple(sorted(fa - fb)),
        tuple(sorted(fb - fa)),
        tuple(sorted((e, v) for e, v in Da.items() if Db.get(e) != v)),
        tuple(sorted((e, v) for e, v in Db.items() if Da.get(e) != v)),
    )
    return rule, None


def rev_rule(rule):
    eo, ei, do, di = rule
    return (ei, eo, di, do)


def relab_rule(rule, sigma):
    eo, ei, do, di = rule
    rl = lambda p: tuple(sigma[x - 1] for x in p)
    return (
        tuple(sorted(rl(p) for p in eo)),
        tuple(sorted(rl(p) for p in ei)),
        tuple(sorted((rl(a), rl(b)) for a, b in do)),
        tuple(sorted((rl(a), rl(b)) for a, b in di)),
    )


def canon_rule(rule, n):
    """Min over all n! relabelings of the DIRECTED rule."""
    best = None
    for sigma in permutations(range(1, n + 1)):
        cand = relab_rule(rule, sigma)
        if best is None or cand < best:
            best = cand
    return best


def rule_id(crule):
    return hashlib.sha256(repr(crule).encode()).hexdigest()[:12]


def load_sigs(n):
    """pair frozenset -> s43 swap-signature hash (if census committed)."""
    path = os.path.join(HERE, "..", "..", "data", "tailconj",
                        f"tail_swap_sigs_n{n}.tsv")
    sigs = {}
    if os.path.exists(path):
        with open(path) as fh:
            next(fh)
            for line in fh:
                a, b, _, _, _, sig = line.rstrip("\n").split("\t")
                sigs[frozenset((a, b))] = sig
    return sigs


def serialize_rule(rule):
    eo, ei, do, di = rule
    return (",".join(s(p) for p in eo), ",".join(s(p) for p in ei),
            ",".join(f"{s(a)}>{s(b)}" for a, b in do),
            ",".join(f"{s(a)}>{s(b)}" for a, b in di))


def parse_rule(eo, ei, do, di):
    pd = lambda t: tuple(P(x) for x in t.split(",")) if t else ()
    dd = lambda t: tuple(tuple(P(y) for y in x.split(">"))
                         for x in t.split(",")) if t else ()
    return (pd(eo), pd(ei), dd(do), dd(di))


def run_extract(n, tsv, dirs, min_perms, rules_out=None, do_oracle=False):
    pairs = load_pairs(tsv, min_perms)
    files = file_map(dirs)
    sigs = load_sigs(n)
    print(f"n={n}: {len(pairs)} NEW pairs >= {min_perms} shared perms "
          f"from {tsv}")
    walks = {}
    for a, b, *_ in pairs:
        for name in (a, b):
            if name not in walks:
                walks[name] = Walk(name, open(files[name]).read().strip(), n)

    stats = Counter()
    by_rid = {}   # rid -> (canonical rule, [(pair, dir, sig)])
    ok = True
    for a, b, d, orient in pairs:
        oa, ob = orient
        ra, rb = aligned_strings(walks[a], oa, walks[b], ob, d)
        rule, why = extract_rule(ra, rb, n)
        if rule is None:
            stats[f"unextractable: {why}"] += 1
            print(f"  {a} ~ {b}: UNEXTRACTABLE ({why})")
            ok = False
            continue
        eo, ei, do, di = rule
        stats[f"edit |ents_out|={len(eo)} |ents_in|={len(ei)} "
              f"|doors|={len(do)}+{len(di)}"] += 1
        if do_oracle:
            good = True
            for src, tgt, r in ((ra, rb, rule), (rb, ra, rev_rule(rule))):
                E, D, st = structure(first_visit_path(src, n))
                ed = edit(E, D, *r)
                prod, reason = replay(*ed, st, n) if ed else (None, "edit refused")
                if prod != tgt:
                    good = False
                    print(f"  {a} ~ {b}: ORACLE FAIL ({reason})")
            ok &= good
            stats["oracle PASS" if good else "oracle FAIL"] += 1
        sig = sigs.get(frozenset((a, b)), "-")
        for direction, r in (("AB", rule), ("BA", rev_rule(rule))):
            rid = rule_id(canon_rule(r, n))
            by_rid.setdefault(rid, (r, []))[1].append((f"{a}~{b}", direction, sig))

    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"{len(by_rid)} distinct directed rules up to relabeling "
          f"({len(by_rid) // 2 if len(by_rid) % 2 == 0 else len(by_rid)}"
          f" undirected if all reverses pair up)")
    # signature -> rids crosswalk
    sig_rids = {}
    for rid, (r, members) in by_rid.items():
        for _, _, sig in members:
            sig_rids.setdefault(sig, set()).add(rid)
    for sig, rids in sorted(sig_rids.items(), key=lambda kv: -len(kv[1])):
        n_pairs = len({m for rid in rids for m, _, sg in by_rid[rid][1]
                       if sg == sig}) // 1
        print(f"  sig {sig}: {len(rids)} directed entry-level rules")
    if rules_out:
        os.makedirs(os.path.dirname(rules_out) or ".", exist_ok=True)
        with open(rules_out, "w") as out:
            out.write("rule_id\tn\tents_out\tents_in\tdoors_out\tdoors_in\t"
                      "n_pairs\tsigs\texample_pair\n")
            for rid, (r, members) in sorted(
                    by_rid.items(), key=lambda kv: -len(kv[1][1])):
                eo, ei, do, di = serialize_rule(r)
                sgs = ",".join(sorted({sg for _, _, sg in members}))
                out.write(f"{rid}\t{n}\t{eo}\t{ei}\t{do}\t{di}\t"
                          f"{len(members)}\t{sgs}\t{members[0][0]}\n")
        print(f"-> {rules_out}")
    return ok, by_rid


def run_oracle():
    all_ok = True
    for n, (tsv, dirs, min_perms) in DEFAULT_SETS.items():
        ok, _ = run_extract(n, tsv, dirs, min_perms, do_oracle=True)
        all_ok &= ok
    print("oracle:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


# ---------- apply-sym: the conjugated sweep (perm-id fast path) ----------

def make_tables(n):
    from loop_ledger_probe import g as gfn
    perms = sorted(permutations(range(1, n + 1)))
    pid = {p: i for i, p in enumerate(perms)}
    ROT = [pid[p[1:] + p[:1]] for p in perms]
    G = [pid[gfn(p)] for p in perms]
    return perms, pid, ROT, G


def replay_ids(flat, doors, start, n, TUP, ROT, G):
    total = factorial(n)
    out = list(TUP[start])
    cur = start
    seen = set()
    covered = 0
    for _ in range(total + 1):
        if cur not in flat or cur in seen:
            return None
        seen.add(cur)
        p = cur
        alen = 1
        while ROT[p] not in flat:
            p = ROT[p]
            out.append(TUP[p][-1])
            alen += 1
        covered += alen
        if covered == total:
            prod = "".join(map(str, out))
            if len(first_visit_path(prod, n)) != total:
                return None
            return prod
        if p in doors:
            nxt = doors[p]
        else:
            nxt = G[ROT[p]]
            if nxt not in flat:
                return None
        w = weight(TUP[p], TUP[nxt], n)
        out.extend(TUP[nxt][n - w:])
        cur = nxt
    return None


def run_apply_sym(n, rules_tsv, dirs, outdir, max_replays=None,
                  dry_run=False, skip_rules=(), record=None):
    os.makedirs(outdir, exist_ok=True)
    if record is None:
        record = 872 if n == 6 else 5906
    TUP, pid, ROT, G = make_tables(n)

    # novelty gate = m3_check convention (published + our discovery indexes)
    idx_file = ("upstream872_canon_index.tsv" if n == 6
                else "upstream5906_canon_index.tsv")
    idx = load_index(os.path.join(HERE, idx_file))
    for supp in SUPPLEMENTARY.get(n, []):
        p = os.path.join(HERE, supp)
        if os.path.exists(p):
            idx.update(load_index(p))

    # rules
    rules = []
    with open(rules_tsv) as fh:
        next(fh)
        for line in fh:
            rid, rn, eo, ei, do, di, npairs, sgs, ex = \
                line.rstrip("\n").split("\t")
            if int(rn) != n or rid in skip_rules:
                continue
            rules.append((rid, parse_rule(eo, ei, do, di)))
    print(f"{len(rules)} directed rules; generating conjugated instances...")

    instances = {}
    for rid, rule in rules:
        for sigma in permutations(range(1, n + 1)):
            eo, ei, do, di = relab_rule(rule, sigma)
            key = (
                tuple(pid[p] for p in eo), tuple(pid[p] for p in ei),
                tuple((pid[a], pid[b]) for a, b in do),
                tuple((pid[a], pid[b]) for a, b in di),
            )
            instances.setdefault(key, rid)
    print(f"{len(instances)} distinct conjugated instances")

    # walks: flat entry sets, doors, start — both orientations
    names, structs = [], []
    postings = {}
    door_postings = {}
    files = file_map(dirs)
    for f, path in files.items():
        src = open(path).read().strip()
        if not src.isdigit():
            continue
        for orient, txt in (("F", src), ("R", src[::-1])):
            E, D, st = structure(first_visit_path(txt, n))
            flat = frozenset(pid[p] for c in E for p in E[c])
            doors = {pid[a]: pid[b] for a, b in D.items()}
            wi = len(names)
            names.append((f, orient))
            structs.append((flat, doors, pid[st]))
            for p in flat:
                postings.setdefault(p, set()).add(wi)
            for a, b in doors.items():
                door_postings.setdefault((a, b), set()).add(wi)
    print(f"{len(names)} walk-orientations from {len(files)} files; "
          f"index built", flush=True)

    stats = Counter()
    edges = set()
    novel, novel_shas, novel_src = [], set(), {}
    n_replays = 0
    empty = set()
    all_wi = set(range(len(structs)))
    for (eo, ei, do, di), rid in instances.items():
        # candidate walks: post on ents_out; a rule with EMPTY ents_out (the
        # near-pure door moves) posts on doors_out instead — s46 fix, those
        # used to be silently skipped. Neither ⇒ no removal precondition.
        posts = ([postings.get(p, empty) for p in eo] if eo
                 else [door_postings.get(d, empty) for d in do])
        if any(not po for po in posts):
            continue
        if posts:
            posts.sort(key=len)
            cand = posts[0]
            for po in posts[1:]:
                cand = cand & po
                if not cand:
                    break
        else:
            cand = all_wi
        if not cand:
            continue
        for wi in cand:
            flat, doors, st = structs[wi]
            if any(p in flat for p in ei):
                continue
            if any(doors.get(a) != b for a, b in do):
                continue
            f2 = set(flat)
            f2.difference_update(eo)
            bad = False
            for p in ei:
                f2.add(p)
            d2 = dict(doors)
            for a, _ in do:
                del d2[a]
            for a, b in di:
                if a in d2:
                    bad = True
                    break
                d2[a] = b
            if bad:
                continue
            stats["replayed"] += 1
            stats[f"replayed:{rid}"] += 1
            if dry_run:
                continue
            n_replays += 1
            if max_replays and n_replays > max_replays:
                print(f"STOP: replay budget {max_replays} exhausted")
                break
            prod = replay_ids(f2, d2, st, n, TUP, ROT, G)
            if prod is None:
                stats["replay-killed"] += 1
                continue
            L = len(prod)
            f, orient = names[wi]
            if L > record:
                stats["longer"] += 1
                continue
            sha = hashlib.sha256(canon(prod).encode()).hexdigest()
            if L == record and sha in idx:
                tgt = idx[sha]
                if tgt == f:
                    stats["self-edge"] += 1
                else:
                    edges.add((n, f, tgt, rid))
                    stats["edge"] += 1
            else:
                tag = "SHORTER" if L < record else "NOVEL"
                name = f"lswap-{tag}-{L}-{rid}-{orient}-{sha[:12]}-{f}"
                if sha not in novel_shas:
                    novel_shas.add(sha)
                    open(os.path.join(outdir, name), "w").write(prod)
                    novel.append(name)
                    print(f"*** {tag} {L} *** {rid} on {f}[{orient}] -> {name}",
                          flush=True)
                novel_src.setdefault(sha, []).append((f, rid, orient, L))
        else:
            continue
        break  # replay budget exhausted

    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    ep = os.path.join(outdir, f"lswap_sym_edges_n{n}.tsv")
    with open(ep, "w") as out:
        out.write("n\tsource_class\ttarget_class\trule\n")
        for nn, a, b, r in sorted(edges):
            out.write(f"{nn}\t{a}\t{b}\t{r}\n")
    und = {(nn, frozenset((a, b))) for nn, a, b, _ in edges}
    if novel_src:
        pp = os.path.join(outdir, f"lswap_sym_novel_provenance_n{n}.tsv")
        with open(pp, "w") as out:
            out.write("product_sha256\tsource_class\trule\torientation\tlength\n")
            for sha, rows in sorted(novel_src.items()):
                for f, rid, orient, L in sorted(set(rows)):
                    out.write(f"{sha}\t{f}\t{rid}\t{orient}\t{L}\n")
        print(f"provenance of {len(novel_src)} distinct products -> {pp}")
    print(f"\n{len(edges)} directed edges ({len(und)} undirected) -> {ep}")
    print(f"{len(novel)} NOVEL/SHORTER products in {outdir}" if novel
          else "corpus CLOSED under the conjugated loop-swap vocabulary")
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    mode = args[0]
    args = args[1:]
    if mode == "oracle":
        return run_oracle()
    n = 6
    if args[:1] == ["-n"]:
        n = int(args[1])
        args = args[2:]
    opts = {"--dirs": None, "--min-perms": None, "--rules-out": None,
            "--rules": None, "--out": None, "--max-replays": None,
            "--skip-rules": None, "--record": None}
    flags = {"--dry-run": False}
    pos = []
    i = 0
    while i < len(args):
        if args[i] in opts:
            opts[args[i]] = args[i + 1]
            i += 2
        elif args[i] in flags:
            flags[args[i]] = True
            i += 1
        else:
            pos.append(args[i])
            i += 1
    if mode == "extract":
        tsv0, dirs0, mp0 = DEFAULT_SETS[n]
        tsv = pos[0] if pos else tsv0
        dirs = opts["--dirs"].split(",") if opts["--dirs"] else dirs0
        mp = int(opts["--min-perms"]) if opts["--min-perms"] else mp0
        ok, _ = run_extract(n, tsv, dirs, mp, rules_out=opts["--rules-out"])
        return 0 if ok else 1
    if mode == "apply-sym":
        return run_apply_sym(
            n, opts["--rules"], opts["--dirs"].split(","), opts["--out"],
            int(opts["--max-replays"]) if opts["--max-replays"] else None,
            dry_run=flags["--dry-run"],
            skip_rules=set(opts["--skip-rules"].split(","))
            if opts["--skip-rules"] else (),
            record=int(opts["--record"]) if opts["--record"] else None)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
