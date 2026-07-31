# R-BND — the boundary/door unit trade (s47 item 1)

Derived from the three (842,19)↔(844,17) conjugated cover twins.
Instrument: `analysis/counting/rbnd.py`. Oracle: `out/s47/item1/oracle2.py (scratch)`
(3/3 pairs, both directions, byte-identical). Literal 9-column
encoding: `data/loopswap/rules_n7_rbnd.tsv`.

## 1. Why no 9-column rule can express it

A 9-column loop-swap / i4a rule edits entries+doors and replays **from
the source walk's own start perm**. Every corpus file starts at the
identity in orientation F, so for each of the four orientation
combinations exactly ONE relabeling aligns the two starts — there is no
relabeling freedom (independently re-derived here in
`frames.py`, and by the s47 item-2 agent as their "rigidity theorem").

In those four admissible frames the twins are ~700 entries apart
(pair 1: |ents_out| = 747, |ents_in| = 749, cover overlap 16/142).
In the **cover-aligning** frame σ = swap 5↔6 they are 2 entries + 2
doors apart — but σ is inadmissible: the starts differ (1234657 vs
1234567), and replaying the 2-entry edit from the source's own start
dies ("w2 target 3462517 not an entry from exit 7134625").

**The missing degree of freedom is the walk's ORIGIN.** R-BND supplies
it: the edit is accompanied by an explicit re-rooting of the walk. This
is an i4a-style rigid rule with a frame/rooting action, implemented as
a separate instrument mode — the 9-column format is untouched.

## 2. The move, in theorem coordinates (THEORY §7)

A tight walk has `D` doors + the walk END terminating the `D+1`
partial-loop chains, and `D` door TARGETS + the walk START beginning
them. R-BND trades one door against one walk boundary. Four directed
variants; `g`, `rot` as in `loop_ledger_probe`.

| variant | Δ(S,D) | boundary | precondition | edit | new root |
|---|---|---|---|---|---|
| **FWD-END** | (+1,−1) | START preserved | `d2=(x2→y2)` the unique door with `y2 ∈ loop(rot(end))` | delete `d2`; add entry `a2 = g(rot(end))` | start unchanged; END becomes `x2` |
| **FWD-START** | (+1,−1) | END preserved | `d1=(x1→y1)` the unique door with `start ∈ loop(rot(x1))` | delete `d1`; add entry `a1 = g(rot(x1))` | START becomes `y1` |
| **REV-END** | (−1,+1) | START preserved | entry `a` with `weight(end, g(a)) = 3` | remove entry `a`; add door `end → g(a)` | END becomes `rot⁻¹(g⁻¹(a))` |
| **REV-START** | (−1,+1) | END preserved | entry `a` with `weight(rot⁻¹(g⁻¹(a)), start) = 3` | remove `a`; add door `rot⁻¹(g⁻¹(a)) → start` | START becomes `g(a)` |

FWD-END and FWD-START are exact reversal conjugates of one another (a
walk's reversal swaps start and end), so up to reversal there is **one**
undirected move. FWD-END / REV-END preserve the start and are therefore
the only two variants a 9-column applier can execute faithfully.

Mechanism (FWD-END): the walk's END terminates the chain of loop
`ℓ = loop(rot(end))`; that same chain BEGINS at `y2`, fed by door `d2`.
Deleting `d2` and adding the single missing loop entry `a2` closes `ℓ`
into a full loop (Φ+1), so the old end is now followed and `y2` is now
fed; the walk's end migrates to `x2`, whose w2 successor is gone.
Length is conserved: `len = 5045 + S + D` for pure-w3 walks, so
(S+1, D−1) stays at 5906. The added entry splits one more cycle, so
splits+1 = Φ+1 keeps the walk tight (verified: deficit 0 on all products).

**Every tight walk admits FWD-END and FWD-START exactly once** (the
chain beginning at the walk start, and the chain terminated by the walk
end, each begin/end at a door or at the boundary) — the precondition is
universal; the filter is entirely replay.

## 3. The twin move = FWD-START ∘ FWD-END (they commute)

The (842,19)→(844,17) two-unit trade is the composite of the two FWD
units, and they commute. In the σ frame the objects are literally
identical for all three pairs:

```
delete doors  7314625>4625137   (w3)   and  7651234>1234567   (w3)
add entries   3462517                  and  5123467
loops promoted partial→full: 1346257 (chain was terminated by the walk END)
                             1234657 (chain was terminated by door 7651234>1234567)
loop re-terminated: 1462537 (was killed by door 7314625>4625137, now by the walk END)
cycles split once more: 1734625 and 1234675
re-root: start 1234657 → 1234567 ,  end 7134625 → 7314625
```

## 4. Canonical ids (S₇-canonical, `loopswap_apply.canon_rule`)

| variant | shape (|eo|,|ei|,|do|,|di|) | canon id |
|---|---|---|
| FWD-END | (0,1,1,0) | `0f7d2db027b5` |
| FWD-START | (0,1,1,0) | `12a2a068d7f9` |
| REV-END | (1,0,0,1) | `8fb799d03e70` |
| REV-START | (1,0,0,1) | `049855ebecd7` |
| TWIN-FWD (composite) | (0,2,2,0) | `c5eea8cfe39f` |
| TWIN-REV (composite) | (2,0,0,2) | `cc2051680646` |

None of these ids occurs in the 862-rule vocabulary, and **no rule in
any table has any of these shapes** — R-BND is not R-K7 (shape
(1,0,1,2)/(0,1,2,1)) nor any loop-swap rule, in any frame.

Caveat: the literal 9-column encoding is a strictly weaker object than
the rule. A w3 door `(x→y)` has 6 relabel-classes (the S₃ pattern of
`x[0:3]` inside `y[4:7]`); the specimen encodes only one of them. The
intrinsic instrument is pattern-free.

## 5. Per-pair anatomy (σ-aligned frame, σ = swap 5↔6)

All three pairs carry the **same rigid move with literally the same
perms**: doors `7314625>4625137` + `7651234>1234567` out, entries
`3462517` + `5123467` in, loops `1234657` + `1346257` promoted
partial→full, loop `1462537` re-terminated from door to walk-END,
cycles `1734625` + `1234675` split once more, re-root
`1234657 → 1234567`.

| pair | (842,19) side | (844,17) side | door depths in the (842,19) walk | run-seq | literal lcp | s43 swap-sig |
|---|---|---|---|---|---|---|
| 1 (blind spot) | up-8b8c8916a24a | up-dab493384582 | 34 and 5004 of 5040 | 256 → 258, common prefix **0** | 4 chars | `3032f7c7fc40` |
| 2 | up-331228e22360 | up-756ff2ed09bd | 419 and 4619 | 250 → 252, common prefix **0** | 4 chars | `2a1bfa2ae9b5` |
| 3 | lswap-f4c2deec7c96 | lswap-9bd2a50baa0e | — | 252 → 254, common prefix **0** | 4 chars | `2a1bfa2ae9b5` |

**The difference region is NOT contiguous** and there is no rewrite
"window": the four edited objects sit at the two extreme ends of the
walk (depths ~34 and ~5004 of 5040), and because the walk is re-rooted
the two strings share only 4 leading characters and reorder the entire
time-ordered run sequence (common prefix 0 of ~256 runs). R-compound at
n=6 was the previous most order-scrambling move (common prefix 4–13);
R-BND's composite is total.

The s43-style swap signature (which encodes the CARRIER rotor
compositions) splits the three pairs 1 + 2 — pair 1's affected cycles
split [3,4]/[3,4], pairs 2 and 3 split [5,2]/[2,5]. So swap-signature
equality is a carrier invariant, not a move invariant: identical rule,
two signatures.
