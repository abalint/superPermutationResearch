CC      ?= cc
CFLAGS  ?= -O2 -Wall -Wextra
LDLIBS  ?= -lm

DATA    := ../../data/trackc

all: dlx7g

dlx7g: dlx7g.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

# G0 gates ------------------------------------------------------------------
.PHONY: gates parity baseline clean
gates: parity baseline

# parity: --dump-features must byte-match the Python extractor's dump
parity: dlx7g
	./dlx7g $(DATA)/instances/n6std.txt \
	    --dump-features $(DATA)/parity/cover_rows.txt --out /tmp/parity_c.txt
	diff /tmp/parity_c.txt $(DATA)/parity/parity_py.txt && echo "PARITY OK"

# baseline: blind engine re-finds the n=6 rooted 25-row cover, compiles, validates
baseline: dlx7g
	python3 solve_guided.py n6std --time-limit 300 --outdir /tmp/trackc_out

clean:
	rm -f dlx7g
