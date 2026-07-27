# FARM.md — running the n=7 5905 cover farm on a fresh (big) machine

Goal: decide the five K=27/Σ=12 chains (and the K=29..31 tier) — any exact
rooted cover is a **5905 world record**. Highest-value lead: on chain 0,
PermutationChains' `coverFirst` mode reached `minColsLeft=0` (covers of the
reduced set exist) and then **crashed silently** — fixing that crash may be
worth more than any amount of extra compute (see §5).

Prereqs: git, python3 (3.9+), a C/C++ compiler, make. Linux or macOS
(Windows: use WSL).

## 1. Clone

```bash
git clone https://github.com/abalint/superPermutationResearch.git
cd superPermutationResearch && cargo build --release   # validator (needs Rust; rustup.rs)
cd ..
git clone https://github.com/superpermutators/superperm.git        # Egan tools + 5906s
git clone https://github.com/urdvr/superpermutation-examples.git   # gain1/certificate machinery
```

## 2. Build the engines

```bash
# Egan's PermutationChains (the engine that found the 5906s):
cd superperm/PermutationChains && cc -O3 -o PermutationChains PermutationChains.c && cd ../..
# SAT solvers:
git clone https://github.com/arminbiere/cadical && cd cadical && ./configure && make && cd ..
git clone https://github.com/arminbiere/kissat  && cd kissat  && ./configure && make && cd ..
# Optional MILP: pip3 install highspy
```

## 3. Working directory

```bash
mkdir -p farm && cd farm
cp ../superPermutationResearch/analysis/cover7/*.py .
cp ../superPermutationResearch/analysis/cover7/chains_*.jsonl .
cp ../superpermutation-examples/scripts/gain1.py ../superpermutation-examples/scripts/certificate.py .
mkdir -p egan && cd egan && ln -s ../../superperm/PermutationChains/PermutationChains . && cd ..
```

## 4. Launch (scale to cores)

The five K=27 kernel patterns (KernelFinder `nsk` form — chains 0..4):

```
nsk666646664666466466646664666
nsk666646664664666466466646666
nsk666646646664666466466646666
nsk666646664664666466646646666
nsk666466646664664666466646666
```

```bash
# Egan plain mode (the mode that found the 5906s), one per core:
for P in 666646664666466466646664666 666646664664666466466646666 \
         666646646664666466466646666 666646664664666466646646666 \
         666466646664664666466646666; do
  nohup ./egan/PermutationChains 7 nsk$P trackPartial > egan/plain_$P.log 2>&1 &
done
# Long CDCL per chain (UNSATs close Sigma=12): chain index 0..4 into chains_V15_s14.jsonl
nohup python3 sat_chain.py --chains chains_V15_s14.jsonl --index 0 --solver ../cadical/build/cadical --timeout 259200 > sat_c0.log 2>&1 &
# (repeat for the other distinct chains; 3 distinct up to reversal: 0/4, 1/3, 2)
# Tier-2/3 triage over the open K=30..33 chains:
nohup python3 sat_chain.py --chains chains_V15_s16.jsonl --triage --timeout 3600 > triage_s16.log 2>&1 &
```

(Check each script's `--help`/header for exact flags — they were written
mid-campaign; `NOTES.md` documents intent. If a flag differs, the header
comment is authoritative.)

## 5. The crash lever (potentially the whole game)

`coverFirst` mode reaches far deeper than plain mode (129/141 two-cycles;
`minColsLeft=0` on chain 0 = reduced-set covers EXIST) but dies silently on our
nsk kernels — reproduced twice. Build with sanitizers and catch it:

```bash
cc -O1 -g -fsanitize=address -o PermutationChains_asan PermutationChains.c
./PermutationChains_asan 7 nsk666646646664666466466646666 coverFirst
```

A fixed coverFirst on the five chains is the single highest-probability path
to a 5905. Suspected area: the DLX→searchPC handoff (crash after
`minColsLeft=0` / at `PCsolSize=129`).

## 6. Harvest

Any `Found SOLUTION` line writes `egan/7_5905_<pattern>.txt` — each line of
that file is a candidate word. Validate immediately:

```bash
cd ../superPermutationResearch
cargo run --release -- validate -n 7 --file ../farm/egan/7_5905_<pattern>.txt --complete
cargo run --release -- trace    -n 7 --file ../farm/egan/7_5905_<pattern>.txt
```

`complete superpermutation = true` at length 5905 = the record. Save
everything, then celebrate responsibly.
