#!/usr/bin/env python3
"""trace5907.py -- validate the n=7 ledger against the real 5907 record words.

Expect per word: waste = Sigma(gap-1) = 861, census T1=4182, T2=853, T3=4,
the 4 weight-3 transitions are door(s,3) hops forming a K=5 orbit-disjoint
skip-0 chain == the standard kernel up to symbol relabeling.
"""
import sys, glob
from itertools import permutations

N = 7; ALPHA = "1234567"; NE = 6; MAXSKIP = 5
def door(w, c): return w[c:] + w[:c][::-1]
def tv(w): return w[1:-1] + w[0] + w[-1]
def canon(w): return min(w[i:] + w[:i] for i in range(len(w)))
def loop_of(e): return (e[-1], canon(e[:-1]))

def loop_entries(lp):
    e = lp[1] + lp[0]; out = []
    for _ in range(NE):
        out.append(e); e = tv(e)
    return out

# standard kernel loop sequence (from gates7.py, gain1 construction)
lows, hi2, hi1 = ALPHA[:5], ALPHA[5], ALPHA[6]
klo = [loop_of(ALPHA)]
for x in range(1, 5):
    src = hi1 + hi2 + lows[x-1] + lows[x:] + lows[:x-1]
    klo.append(loop_of(door(src, 3)))

for path in sorted(glob.glob(
        "/Users/andrew/Documents/code/math/superperms/extraDocs/"
        "superpermutation-examples/n7/5907-*.txt")):
    w = open(path).read().strip()
    assert len(w) == 5907, len(w)
    pos = [i for i in range(len(w) - N + 1)
           if len(set(w[i:i+N])) == N]
    assert len(pos) == 5040, "word does not visit each perm... count"
    assert len(set(w[i:i+N] for i in pos)) == 5040
    gaps = [pos[i+1] - pos[i] for i in range(len(pos) - 1)]
    from collections import Counter
    h = Counter(gaps)
    waste = sum(g - 1 for g in gaps)
    name = path.split("/")[-1]
    print(f"{name}: histogram {dict(sorted(h.items()))}  waste={waste}")
    assert waste == 861 and h[3] == 4 and h[2] == 853 and h[1] == 4182, "census FAIL"
    # extract the 4 weight-3 hops and the K=5 chain
    hops = [i for i, g in zip(pos, gaps) if g == 3]
    chain = []
    for i in hops:
        s, t = w[i:i+N], w[i+3:i+3+N]
        assert t == door(s, 3), "w3 transition is not a cost-3 door"
        e_exit = s[1:] + s[0]            # entry whose splice is replaced
        if not chain:
            chain.append(loop_of(e_exit))
        assert loop_of(e_exit) == chain[-1], "hop leaves a different loop"
        chain.append(loop_of(t))
    assert len(set(chain)) == 5
    orbs = set()
    for lp in chain:
        os_ = set(canon(e) for e in loop_entries(lp))
        assert not (os_ & orbs); orbs |= os_
    # skip-0 check: arrival entry of hop h target vs exit splice of hop h+1
    ok0 = True
    for h_ in range(3):
        M = chain[h_ + 1]
        ent = loop_entries(M)
        k = ent.index(w[hops[h_]+3:hops[h_]+10])
        s2 = w[hops[h_+1]:hops[h_+1]+N]
        j = [e[-1] + e[:-1] for e in ent].index(s2)
        if MAXSKIP - ((j - k) % NE) != 0: ok0 = False
    print(f"  K=5 chain {['m%s;%s' % lp for lp in chain]}, orbit-disjoint, "
          f"interior skips all 0: {ok0}")
    # standard-kernel-up-to-relabeling: find rho with rho(chain)==klo
    found = None
    for perm in permutations(ALPHA):
        rho = dict(zip(ALPHA, perm))
        rc = [loop_of("".join(rho[c] for c in loop_entries(lp)[0]))
              for lp in chain]
        if rc == klo:
            found = "".join(perm); break
    print(f"  equals STANDARD kernel under relabeling {ALPHA}->{found}: "
          f"{found is not None}")
