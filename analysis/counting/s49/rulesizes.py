#!/usr/bin/env python3
"""s49 item1 — size census of the 864-rule directed vocabulary."""
import collections
import csv
import os

R = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
TABLES = ['data/loopswap/rules_n7_a256.tsv',
          'data/loopswap/rules_n7_a4840_gen2.tsv',
          'data/loopswap/rules_n7_a4840_band200.tsv',
          'data/loopswap/rules_n7_s48_covertwin.tsv']

rules = {}
for t in TABLES:
    with open(os.path.join(R, t)) as fh:
        for row in csv.DictReader(fh, delimiter='\t'):
            def sp(x):
                return [] if not x else x.split(',')
            rules[row['rule_id']] = (
                len(sp(row['ents_out'])), len(sp(row['ents_in'])),
                len(sp(row['doors_out'])), len(sp(row['doors_in'])), t)
print(f"distinct directed rule ids: {len(rules)}")

pure = {k: v for k, v in rules.items() if v[2] == 0 and v[3] == 0}
print(f"door-free (pure loop-swap): {len(pure)}   with doors: "
      f"{len(rules)-len(pure)}")

eo = collections.Counter(v[0] for v in rules.values())
bad6 = [(k, v) for k, v in rules.items() if v[0] % 6 or v[1] % 6]
badeq = [(k, v) for k, v in rules.items() if v[0] != v[1]]
print(f"|ents_out| not a multiple of 6: {len(bad6)}")
print(f"|ents_out| != |ents_in|: {len(badeq)}  -> {badeq[:10]}")
print(f"|ents_out| range: {min(eo)} .. {max(eo)}   "
      f"(k = |eo|/6: {min(eo)//6} .. {max(eo)//6})")
print("\n|eo|  k   count")
for s in sorted(eo):
    print(f"{s:5d} {s/6:4g} {eo[s]:6d}")
tot = sorted(eo.elements(), reverse=True)
print(f"\ntop-10 |ents_out|: {tot[:10]}")
print(f"max |eo1|+|eo2| over ordered pairs: {tot[0]+tot[1]} "
      f"(k1+k2 = {(tot[0]+tot[1])//6})")
dr = collections.Counter((v[2], v[3]) for v in rules.values())
print(f"\n(|doors_out|,|doors_in|) histogram: {dict(dr)}")
