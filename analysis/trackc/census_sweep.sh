#!/bin/bash
# Track C bonus: local dlx7g refutation sweep over the farm census worklist.
# Blind mode (row order is irrelevant to exhaustion; guided only adds overhead).
# Writes one CSV row per chain to runs/census/results.csv as verdicts land.
# Skips indices 0-4 (open K=27, dedicated G3 runs). 30-min cap per chain.
set -u
cd "$(dirname "$0")"
WORKERS=${1:-4}
TL=${2:-1800}
OUT=runs/census
mkdir -p "$OUT/instances" "$OUT/logs"
CSV="$OUT/results.csv"
[ -f "$CSV" ] || echo "index,pattern,K,Sigma,verdict,nodes,maxdepth,seconds" > "$CSV"

# Export all worklist instances once (idempotent).
PYTHONPATH=../cover7:../../../extraDocs/superpermutation-examples/scripts python3 - "$OUT/instances" <<'EOF'
import json, os, sys
sys.path.insert(0, '.')
from instances import export_instance_text
import chain7
out = sys.argv[1]
rows = [json.loads(l) for l in open('../farm/farm_chains.jsonl')]
for i, r in enumerate(rows):
    if i <= 4:
        continue
    p = os.path.join(out, f'wl_{i:03d}.txt')
    if os.path.exists(p):
        continue
    inst = chain7.build_instance_from_chain([tuple(t) for t in r['chain']])
    with open(p, 'w') as f:
        f.write(export_instance_text(inst))
    with open(p + '.meta', 'w') as f:
        json.dump({'index': i, 'pattern': r['pattern'], 'K': r['K'], 'Sigma': r['Sigma']}, f)
print('instances ready')
EOF

run_one() {
  local idx=$1                      # unpadded, for the CSV
  local pad
  pad=$(printf 'wl_%03d' "$idx")    # files are zero-padded
  local inst="$OUT/instances/${pad}.txt"
  local log="$OUT/logs/${pad}.log"
  local meta pattern K Sigma
  meta=$(cat "$inst.meta")
  pattern=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['pattern'])" "$meta")
  K=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['K'])" "$meta")
  Sigma=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['Sigma'])" "$meta")
  local t0=$SECONDS
  nice -n 10 ./dlx7g "$inst" --time-limit "$TL" --out "$OUT/logs/${pad}.rows" > "$log" 2>&1
  local rc=$? dt=$((SECONDS - t0))
  local verdict nodes maxd
  case $rc in
    0) verdict=SAT-CANDIDATE ;;
    2) verdict=UNSAT ;;
    3) verdict=TIMEOUT ;;
    *) verdict=ERROR-$rc ;;
  esac
  nodes=$(grep -o 'nodes=[0-9]*' "$log" | tail -1 | cut -d= -f2)
  maxd=$(grep -o 'maxdepth=[0-9]*' "$log" | tail -1 | cut -d= -f2)
  echo "$idx,$pattern,$K,$Sigma,$verdict,${nodes:-},${maxd:-},$dt" >> "$CSV"
  if [ "$verdict" = SAT-CANDIDATE ]; then
    echo "!!! SAT CANDIDATE at index $idx — validate before believing" >> "$OUT/ALERT"
  fi
}

# Work queue: indices 5..222 not already in the CSV.
# If runs/census/worklist.txt exists (one index per line), sweep exactly those;
# else the full range. Already-recorded indices are skipped either way.
if [ -f "$OUT/worklist.txt" ]; then QUEUE=$(cat "$OUT/worklist.txt"); else QUEUE=$(seq 5 222); fi
for idx in $QUEUE; do
  grep -q "^${idx}," "$CSV" && continue
  while [ "$(jobs -rp | wc -l)" -ge "$WORKERS" ]; do wait -n; done
  run_one "$idx" &
done
wait
echo "SWEEP COMPLETE $(date)" >> "$CSV"
