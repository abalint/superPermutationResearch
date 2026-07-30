# The natural cross-allocation surgery specimen pair (s28)

Two community 872 classes (superpermutators/superperm upstream corpus,
forward-renumbered class representatives) that are BYTE-IDENTICAL for
their first 584 perm visits and then re-cover the same 136 residual
perms two different ways at equal cost:

- `872.up-b020caf20414.txt` — allocation (142,6,0,0,0): tail plays
  `(w1-entry) A ·w3· B ·w3· C` (the entry extends the prefix's last
  sojourn).
- `872.up-0105a4b77ce8.txt` — allocation (143,5,0,0,0): tail plays
  `(w2-entry) C ·w2· A ·w3· B`.

Same 24 cycles, same per-cycle split compositions — the (S+1, d3−1)
unit edit realized as a pure block reordering with junction re-pricing
(docs/SURGERY-DESIGN.md §2.4). Committed as the oracle control for
`tail-atsp --ties`: from the (143,5) side, anchored at the natural cut,
the tie search must re-derive the (142,6) partner byte-identically
(pinned in `src/tailatsp.rs::tests`).
