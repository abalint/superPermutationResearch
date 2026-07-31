#!/usr/bin/env python3
"""s49 item1 PART B analysis — the 12-class table + divisibility verdict."""
import collections
import csv
import os

R = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
rows = list(csv.DictReader(
    open(os.path.join(R, 'out/s49/item1/admdiff_blind12.tsv')),
    delimiter='\t'))
for r in rows:
    for k in ('symdiff', 'ents_out', 'ents_in', 'doors_out', 'doors_in'):
        r[k] = int(r[k])
by = collections.defaultdict(list)
for r in rows:
    by[r['blind']].append(r)

print("PART B TABLE — blind class -> nearest class in the 198, "
      "admissible frame (exact identity for |ents_out|)\n")
hdr = (f"{'blind class':28s} {'alloc':7s} "
       f"{'minSD':>6s} {'eo':>5s} {'ei':>5s} {'eo%6':>5s} {'ei%6':>5s} "
       f"{'dO':>3s} {'dI':>3s} {'nearest':28s} {'T/B':3s} "
       f"{'minSD_touched':>13s} {'eo_t':>6s} {'eo_t%6':>7s} "
       f"{'ndoorfree':>9s} {'minSD_doorfree':>14s}")
print(hdr)
summary = []
for b in sorted(by):
    rs = by[b]
    best = min(rs, key=lambda r: r['symdiff'])
    bt = min((r for r in rs if r['other_touched'] == 'T'),
             key=lambda r: r['symdiff'])
    df = [r for r in rs if r['doors_out'] == 0 and r['doors_in'] == 0]
    dfmin = min((r['symdiff'] for r in df), default=None)
    print(f"{b:28s} {best['alloc_blind']:7s} "
          f"{best['symdiff']:6d} {best['ents_out']:5d} {best['ents_in']:5d} "
          f"{best['ents_out']%6:5d} {best['ents_in']%6:5d} "
          f"{best['doors_out']:3d} {best['doors_in']:3d} "
          f"{best['other']:28s} {best['other_touched']:3s} "
          f"{bt['symdiff']:13d} {bt['ents_out']:6d} {bt['ents_out']%6:7d} "
          f"{len(df):9d} {str(dfmin):>14s}")
    summary.append((b, best, bt, len(df), dfmin))

print("\n--- divisibility census over ALL 12 x 197 ordered blind->other "
      "admissible pairs ---")
c6 = collections.Counter(r['ents_out'] % 6 for r in rows)
print("ents_out mod 6 histogram:", dict(sorted(c6.items())))
c6i = collections.Counter(r['ents_in'] % 6 for r in rows)
print("ents_in  mod 6 histogram:", dict(sorted(c6i.items())))
print("pairs with ents_out == ents_in:",
      sum(1 for r in rows if r['ents_out'] == r['ents_in']), "/", len(rows))
print("pairs with zero door edit:",
      sum(1 for r in rows if r['doors_out'] == 0 == r['doors_in']),
      "/", len(rows))
print("pairs BOTH door-free AND ents_out%6==0:",
      sum(1 for r in rows if r['doors_out'] == 0 == r['doors_in']
          and r['ents_out'] % 6 == 0), "/", len(rows))

print("\n--- min ents_out over all 12x197 pairs (the size a fused pair "
      "must realize) ---")
mins = sorted((min(r['ents_out'] for r in by[b]), b) for b in by)
for m, b in mins:
    print(f"  {b:28s} min|ents_out| = {m:4d}  (= 6 * {m/6:g})")
print("\nglobal min |ents_out| over the whole blind block:", mins[0][0])
