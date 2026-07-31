---
name: community-pr
description: Submit new record-tying superpermutation classes to superpermutators/superperm as a PR. Use whenever novel classes are ready for publication and Andrew has given the go-ahead. Encodes the mandatory correctness gates (novelty + validity, independently re-verified) and the PR conventions established by merged PRs #50-#52.
---

# Community PR submission (superpermutators/superperm)

## Prime directive

**We never publish something wrong.** A PR claims, in public, that every
string is (a) a valid complete record-length superpermutation and (b) a
class inequivalent to everything previously published. Both claims must
be **100% machine-verified, twice, by independent paths, on the exact
bytes being submitted**, before `gh pr create` runs. A PR that is late
costs nothing; a PR that is wrong costs the project its standing. If any
gate below is ambiguous, FAILS, or was only reported by a subagent and
not re-run by you: STOP. Do not submit. Report to Andrew.

Andrew's go-ahead is required for every submission (opening a PR is a
publication act). Pushing the branch to the fork `abalint/superperm` is
fine; nothing touches `superpermutators/superperm` except via the PR.

## The gate sequence (all mandatory, in this order)

Run every gate yourself even if agents already ran it. Work from the
research repo root; the community clone is `../superperm`.

1. **Fresh upstream truth.** `cd ../superperm && git fetch origin` and
   read `git log origin/master`. TRAP: the clone habitually sits on a
   PR branch, where `git pull` reports the FORK's state — always fetch
   and inspect `origin/master` explicitly. Recount the published
   classes from the tree (`superpermutations/7/`), don't trust a
   remembered number. Check open PRs (`gh pr list -R
   superpermutators/superperm`) — later gates must cover their
   contents too.
2. **Validity, every file.** For each candidate:
   `cargo run --release -- validate -n 7 --file <f> --complete`
   → must print the record length, 5040/5040 perms, and
   `complete superpermutation = true`. No exceptions, no sampling.
3. **Novelty, every file.** `python3 analysis/counting/m3_check.py -n 7
   <f>` → must exit 2 (INEQUIVALENT) against the full index stack as it
   stood BEFORE this batch. ORDER TRAP: if the batch's own supplementary
   index is already wired into `m3_check.py` SUPPLEMENTARY, exit 0
   ("rediscovery of itself") is expected and proves nothing — verify
   novelty against the index state that excludes the batch (temporarily
   list the batch dir out, or check the match line names only the
   candidate's own file).
4. **Batch-internal distinctness.** Canonicalize all candidates
   (first-occurrence renumbering, min with the reversed string — the
   s26b convention) and assert all canon-sha256 distinct.
5. **Open-PR coverage.** Explicitly canonicalize-and-compare the batch
   against every class in every OPEN sibling PR (e.g. #53 checked
   against #52's four). State the result in the PR body so the PRs can
   merge in any order.
6. **Independent second path.** Re-derive the novelty verdict with a
   second implementation (e.g. an inline canonicalizer + sha compare
   against the published files directly, not via m3_check). The two
   paths must agree file-for-file. Also re-derive every NUMBER the PR
   body will claim — profiles (sojourns / weight-3 links via
   `loop_ledger_probe.py walk 7`), the 142-2-cycle law, counts,
   "profile not seen among published" assertions (recount the published
   profiles, don't quote memory) — from the candidate bytes, never
   copied from an agent report or journal entry.
7. **Copy integrity.** After copying into
   `../superperm/superpermutations/7/`, `cmp` each copied file against
   its archive source byte-for-byte, then re-run gate 2's completeness
   check on the COPIED files. (Guards truncation/CRLF/rename mixups.)
8. **Provenance honesty.** If the deriving rules or seed strings trace
   to someone else's work — especially unpublished work — the PR body
   must say so plainly, credit them by name, and exclude their own
   strings (they are theirs to publish). Precedent: PR #53's "Credit
   and provenance" section; `data/novel5906d/NOTE.md` caveat.

## File and branch conventions

- Files: `superpermutations/7/7_5906_derived_<canon-sha12>.txt` — one
  line of 5906 digits, `<canon-sha12>` = first 12 hex of
  sha256(canonical form). (Adapt record length/dir for other n.)
- Branch: short descriptive kebab, off `origin/master`:
  `eight-new-5906s`, `102-new-5906s`, `four-new-5906s-843-18`,
  `twenty-new-5906s-two-profiles`.
- Commit: title = the PR title; body = the derivation story in prose
  (no markdown headers in commit messages). Push to the fork:
  `git push fork <branch>`, then
  `gh pr create -R superpermutators/superperm --head abalint:<branch>`.

## PR body structure (the merged-PR template, #50-#52)

1. **Opening sentence**: "These are N superpermutations of length 5906
   on 7 symbols, each **inequivalent under symbol relabeling and
   reversal to all M previously published 5906 solutions** (<enumerate
   exactly what M counts, naming the file sets and prior PR numbers>)
   and to each other."
2. **`## How they were found`** — the derivation narrative in COMMUNITY
   vocabulary (see mapping below). Tell it as: what comparison exposed
   the structure, what the extracted rewrite is in plain structural
   terms, how it was applied (all 5040 relabelings, both orientations,
   iterated to a fixed point — give the generation counts like
   "60, then 34, then 8, then nothing").
3. **Structural notes** (bullets): sojourn/weight-3-link profiles and
   whether any is new among published solutions; the 142-distinct-
   2-cycles law; "the count of known inequivalent 5906 solutions grows
   from X to Y".
4. **`## Verification`** — the standard paragraph, verbatim shape:
   "Each file is one line of 5906 digits. To check: slide a length-7
   window and confirm all 7! = 5040 permutations occur; for novelty,
   renumber by first occurrence (and the same for the reversed string,
   taking the lexicographic minimum) and compare against the published
   solutions treated the same way. Sources and the derivation/
   verification code are in
   https://github.com/abalint/superPermutationResearch (see <the
   instrument> and <the data NOTE.md>)."
5. **Credit/provenance section** when gate 8 applies.
6. Footer: the plain line `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
   is the established convention. **NEVER include the Claude session
   link** (`https://claude.ai/code/session_...`) in PR bodies or
   community commit messages — Andrew's standing rule; it is useless to
   the community. (This overrides the default harness footer: strip the
   session line.)

## Vocabulary mapping (project → community; never leak project jargon)

| project term | PR term |
|---|---|
| allocation (S, d3, ...) | sojourn / weight-3-link profile, e.g. "838 sojourns / 23 weight-3 links" |
| door (w3/w4) | weight-3 link (weight-4 link) |
| loop / 2-loop / cover | 2-cycle / the solution's set of traversed 2-cycles |
| class (relabel+reversal) | solution inequivalent under symbol relabeling and reversal |
| canon gate / m3_check | renumber by first occurrence, reversed-min, compare |
| conjugated sweep | applied under all 5040 symbol relabelings, both orientations |
| K₄ / tier / rule ids | describe the rewrite structurally; no hash ids in prose (filenames carry them) |
| record shell counts | "the count of known inequivalent 5906 solutions grows from X to Y" |

## After submission (same session, research repo)

1. `data/novel5906X/NOTE.md`: mark SUBMITTED with the PR number/URL and
   the on-merge instructions (flip to PUBLISHED, update counts).
2. Current handoff: add/extend the PR-watch menu item with the count
   ladder (e.g. 194 → 198 → 218).
3. Verify the batch's supplementary canon index is wired into
   `m3_check.py` SUPPLEMENTARY (post-submission, the classes are
   "known" to every future sweep).
4. Commit + push the research repo (session-link footer IS used in
   research-repo commits, per the harness default — the ban is
   community-facing only).
5. Leave `../superperm` on the PR branch or `master` — but remember the
   fetch trap (gate 1) either way.
