//! I1 — tail block-ATSP (docs/SURGERY-DESIGN.md §4, s28/s29).
//!
//! Cut a walk's tail at an anchor (a w≥2 block boundary) into blocks
//! (maximal weight-1 runs), price junctions between blocks by overlap
//! weight, and solve the block-order ATSP-path EXACTLY. The block set —
//! hence every per-cycle split composition — is fixed; only the order
//! (and with it the junction weights) may change. Junction pricing is
//! allocation-blind: a cheaper order lands in whatever L0 allocation its
//! junction weights imply, including specimen-free ones.
//!
//! Verdict semantics (honest claims, per the design doc):
//! - optimum < actual: an 871 candidate — materialize, validate, and put
//!   it through the M3 ritual before believing ANYTHING.
//! - optimum = actual corpus-wide: "block-order-optimal from this
//!   anchor" — always with the fixed-decomposition caveat (a shorter
//!   walk could still RECOMPOSE cycles; that is instrument I2's
//!   question, not this one's).
//!
//! Exact solvers: Held–Karp DP for ≤ `HK_MAX` blocks (cross-check tier),
//! branch-and-bound above it — cheap min-in-edge bound first, assignment
//! relaxation (Hungarian) only where the cheap bound fails to prune.

use crate::graph::{factorial, unrank, Graph};
use crate::trace::Trace;

/// Held–Karp ceiling: 2^20 × 20 u16 cells ≈ 42 MB, a comfortable pin
/// tier; B&B handles everything above.
pub const HK_MAX: usize = 20;

/// One block: a maximal weight-1 run of first visits.
pub struct Block {
    /// Rank of the first perm in the block.
    pub entry: u32,
    /// Rank of the last perm in the block.
    pub exit: u32,
    /// Number of perms in the block (≥ 1).
    pub nperms: usize,
}

/// A decomposed tail instance at one anchor.
pub struct TailInstance {
    /// 1-indexed first-visit depth of the LAST prefix perm (the anchor
    /// state's `cur`); the tail starts at depth `anchor_depth + 1`.
    pub anchor_depth: usize,
    /// Rank of the anchor state's `cur` (junction source for `cost[0]`).
    pub anchor_cur: u32,
    /// Characters of the source string covered by the prefix.
    pub prefix_chars: usize,
    /// Tail blocks in the walk's own order.
    pub blocks: Vec<Block>,
    /// Junction cost matrix: `cost[0][j]` = anchor → block `j−1`,
    /// `cost[i][j]` = block `i−1` exit → block `j−1` entry (i, j ≥ 1;
    /// diagonal unused).
    pub cost: Vec<Vec<u16>>,
    /// Weight-1 characters spent inside blocks (order-invariant).
    pub intra: usize,
    /// The walk's own junction total (its order = 1, 2, …, B).
    pub actual: usize,
}

/// Junction weight from perm `a` to perm `b`: characters appended when
/// the window jumps from `a` to `b` (n − max overlap; `n` if none).
fn junction(n: usize, a: u32, b: u32) -> u16 {
    let pa = unrank(n, a as usize);
    let pb = unrank(n, b as usize);
    (n - Graph::overlap(&pa, &pb)) as u16
}

/// Decompose `trace`'s tail at the block boundary nearest — at or after
/// — first-visit depth `min_depth` (1-indexed). Returns `None` if no
/// boundary exists at or after `min_depth` (tail would be empty), or if
/// the string is not tight (replay ≠ input — corpus loader forbids
/// this, but be honest at the API too).
pub fn decompose(n: usize, trace: &Trace, min_depth: usize) -> Option<TailInstance> {
    if trace.replay_len != trace.input_len || trace.path.len() < min_depth + 1 {
        return None;
    }
    let nfact = factorial(n);
    debug_assert_eq!(trace.path.len(), nfact);
    // Anchor = last prefix perm: the first d ≥ min_depth (1-indexed)
    // whose OUTGOING move (weights[d−1]) has weight ≥ 2.
    let d0 = (min_depth.max(1)..trace.path.len()).find(|&d| trace.weights[d - 1] >= 2)?;
    let prefix_chars = n + trace.weights[..d0 - 1]
        .iter()
        .map(|&w| w as usize)
        .sum::<usize>();

    let mut blocks: Vec<Block> = Vec::new();
    let mut intra = 0usize;
    let mut actual = trace.weights[d0 - 1] as usize; // the entry junction
    let mut entry = trace.path[d0];
    let mut nperms = 1usize;
    for i in d0..trace.path.len() - 1 {
        let w = trace.weights[i] as usize;
        if w == 1 {
            intra += 1;
            nperms += 1;
        } else {
            blocks.push(Block {
                entry,
                exit: trace.path[i],
                nperms,
            });
            actual += w;
            entry = trace.path[i + 1];
            nperms = 1;
        }
    }
    blocks.push(Block {
        entry,
        exit: trace.path[nfact - 1],
        nperms,
    });

    let b = blocks.len();
    let mut cost = vec![vec![0u16; b + 1]; b + 1];
    let anchor_cur = trace.path[d0 - 1];
    for (j, blk) in blocks.iter().enumerate() {
        cost[0][j + 1] = junction(n, anchor_cur, blk.entry);
    }
    for (i, bi) in blocks.iter().enumerate() {
        for (j, bj) in blocks.iter().enumerate() {
            if i != j {
                cost[i + 1][j + 1] = junction(n, bi.exit, bj.entry);
            }
        }
    }
    // The walk's own order must reprice to exactly its own junctions —
    // maximal-overlap tightness guarantees it; assert the invariant.
    let repriced: usize = (0..b).map(|j| cost[j][j + 1] as usize).sum();
    debug_assert_eq!(repriced, actual, "tight walk must reprice to itself");

    Some(TailInstance {
        anchor_depth: d0,
        anchor_cur,
        prefix_chars,
        blocks,
        cost,
        intra,
        actual,
    })
}

/// Canonical cycle id of a rank: the minimum rank over its rotation
/// orbit (n perms — a permutation of distinct symbols is never
/// rotation-symmetric).
pub fn cycle_id(g: &Graph, r: u32) -> u32 {
    let mut m = r;
    let mut c = g.succ1(r);
    while c != r {
        m = m.min(c);
        c = g.succ1(c);
    }
    m
}

/// One I2a merge move (SURGERY-DESIGN §9): replace two same-cycle tail
/// blocks whose perm arcs are contiguous with a single block riding
/// their union. Net −1 sojourn part — the S−1 unit edit. When the pair
/// covers the whole cycle (complementary arcs), every cyclic entry is a
/// valid ride and each is a separate variant.
pub struct MergeMove {
    /// Indices (into `TailInstance::blocks`) of the two merged blocks.
    pub bi: usize,
    pub bj: usize,
    /// Entry perm of the merged block.
    pub entry: u32,
    /// Perms in the merged block (= the two constituents' sum).
    pub nperms: usize,
}

/// Enumerate all single-merge moves of an instance. Only pairs whose
/// arc union is a single contiguous ride are expressible without
/// pass-overs (an i2-priced move — out of I2a's vocabulary): partial
/// unions need arc adjacency (1 variant); complementary pairs covering
/// the whole cycle admit all `n` rotations as entries (`n` variants).
pub fn enumerate_merges(n: usize, g: &Graph, inst: &TailInstance) -> Vec<MergeMove> {
    let mut by_cycle: std::collections::HashMap<u32, Vec<usize>> = std::collections::HashMap::new();
    for (i, b) in inst.blocks.iter().enumerate() {
        by_cycle.entry(cycle_id(g, b.entry)).or_default().push(i);
    }
    let mut out = Vec::new();
    for idxs in by_cycle.values() {
        if idxs.len() < 2 {
            continue;
        }
        for x in 0..idxs.len() {
            for y in x + 1..idxs.len() {
                let (i, j) = (idxs[x], idxs[y]);
                let (a, b) = (&inst.blocks[i], &inst.blocks[j]);
                let total = a.nperms + b.nperms;
                if total == n {
                    // complementary arcs tile the cycle: whole-6 ride
                    // from any entry
                    let mut e = a.entry;
                    for _ in 0..n {
                        out.push(MergeMove {
                            bi: i,
                            bj: j,
                            entry: e,
                            nperms: n,
                        });
                        e = g.succ1(e);
                    }
                } else if g.succ1(a.exit) == b.entry {
                    out.push(MergeMove {
                        bi: i,
                        bj: j,
                        entry: a.entry,
                        nperms: total,
                    });
                } else if g.succ1(b.exit) == a.entry {
                    out.push(MergeMove {
                        bi: i,
                        bj: j,
                        entry: b.entry,
                        nperms: total,
                    });
                }
            }
        }
    }
    out
}

/// One I2a recomposition move: replace ALL of a cycle's tail blocks
/// with a different arc-partition of the same perm set. Subsumes merge
/// (fewer arcs), split (more arcs), and repartition (equal arcs,
/// different boundaries — the junction-neutral 3|3↔2|4 family). The
/// enumeration includes 1|5-style singleton arcs even though no natural
/// recomposition uses them (census M-R1) — a broader negative is a
/// stronger law, and the extra variants are cheap.
pub struct RecompMove {
    /// Indices (into `TailInstance::blocks`) of the cycle's blocks, all
    /// removed.
    pub remove: Vec<usize>,
    /// Replacement arcs as (entry rank, perm count), covering exactly
    /// the same perm set.
    pub arcs: Vec<(u32, usize)>,
}

/// Enumerate every single-cycle recomposition of an instance. For a
/// cycle fully covered in the tail, the alternatives are all nonempty
/// sets of arc starts around the n-cycle (2^n − 1 variants, minus the
/// walk's own). For a partially covered cycle, each maximal contiguous
/// covered run is independently re-partitioned (2^(len−1) compositions
/// per run, cartesian across runs) — arcs never cross a prefix-covered
/// gap (that would need a pass-over, an i2-priced move outside I2a).
pub fn enumerate_recomps(n: usize, g: &Graph, inst: &TailInstance) -> Vec<RecompMove> {
    let mut by_cycle: std::collections::HashMap<u32, Vec<usize>> = std::collections::HashMap::new();
    for (i, b) in inst.blocks.iter().enumerate() {
        by_cycle.entry(cycle_id(g, b.entry)).or_default().push(i);
    }
    let mut out = Vec::new();
    for (cid, idxs) in &by_cycle {
        // cycle perm sequence and position lookup
        let mut seq = Vec::with_capacity(n);
        let mut p = *cid;
        for _ in 0..n {
            seq.push(p);
            p = g.succ1(p);
        }
        let pos_of = |r: u32| seq.iter().position(|&q| q == r).expect("perm in cycle");
        let mut covered = vec![false; n];
        for &bi in idxs {
            let b = &inst.blocks[bi];
            let mut r = b.entry;
            for _ in 0..b.nperms {
                covered[pos_of(r)] = true;
                r = g.succ1(r);
            }
        }
        let ncov = covered.iter().filter(|&&c| c).count();
        let cur_starts: std::collections::BTreeSet<usize> = idxs
            .iter()
            .map(|&bi| pos_of(inst.blocks[bi].entry))
            .collect();
        let mut push = |starts: &std::collections::BTreeSet<usize>, full: bool| {
            if *starts == cur_starts {
                return;
            }
            // arc lengths: from each start to the next covered boundary
            let sv: Vec<usize> = starts.iter().copied().collect();
            let mut arcs = Vec::with_capacity(sv.len());
            for (k, &s) in sv.iter().enumerate() {
                let len = if full {
                    let next = sv[(k + 1) % sv.len()];
                    (next + n - s - 1) % n + 1
                } else {
                    // run to the next start or the end of the covered run
                    let mut len = 0;
                    let mut q = s;
                    loop {
                        len += 1;
                        q = (q + 1) % n;
                        if !covered[q] || starts.contains(&q) {
                            break;
                        }
                    }
                    len
                };
                arcs.push((seq[s], len));
            }
            out.push(RecompMove {
                remove: idxs.clone(),
                arcs,
            });
        };
        if ncov == n {
            for mask in 1u32..(1 << n) {
                let starts: std::collections::BTreeSet<usize> =
                    (0..n).filter(|i| mask & (1 << i) != 0).collect();
                push(&starts, true);
            }
        } else {
            // maximal covered runs (cyclic); enumerate cut subsets per
            // run, cartesian across runs
            let run_starts: Vec<usize> = (0..n)
                .filter(|&i| covered[i] && !covered[(i + n - 1) % n])
                .collect();
            let run_lens: Vec<usize> = run_starts
                .iter()
                .map(|&s| {
                    let mut len = 0;
                    let mut q = s;
                    while covered[q] {
                        len += 1;
                        q = (q + 1) % n;
                        if len == n {
                            break;
                        }
                    }
                    len
                })
                .collect();
            let total_variants: usize = run_lens.iter().map(|&l| 1usize << (l - 1)).product();
            for v in 0..total_variants {
                let mut starts: std::collections::BTreeSet<usize> =
                    std::collections::BTreeSet::new();
                let mut rem = v;
                for (ri, &s) in run_starts.iter().enumerate() {
                    let l = run_lens[ri];
                    let cuts = rem % (1 << (l - 1));
                    rem /= 1 << (l - 1);
                    starts.insert(s);
                    for j in 1..l {
                        if cuts & (1 << (j - 1)) != 0 {
                            starts.insert((s + j) % n);
                        }
                    }
                }
                push(&starts, false);
            }
        }
    }
    out
}

/// Build the recomposed instance: the cycle's blocks replaced by the
/// move's arcs, cost matrix re-derived, `intra` adjusted by the part
/// delta (each arc fewer = one healed boundary = +1 weight-1 move).
/// `incumbent` seeds the B&B bound exactly as in [`apply_merge`].
pub fn apply_recomp(
    n: usize,
    g: &Graph,
    inst: &TailInstance,
    mv: &RecompMove,
    incumbent: usize,
) -> TailInstance {
    let mut blocks: Vec<Block> = inst
        .blocks
        .iter()
        .enumerate()
        .filter(|(k, _)| !mv.remove.contains(k))
        .map(|(_, b)| Block {
            entry: b.entry,
            exit: b.exit,
            nperms: b.nperms,
        })
        .collect();
    for &(entry, np) in &mv.arcs {
        let mut exit = entry;
        for _ in 1..np {
            exit = g.succ1(exit);
        }
        blocks.push(Block {
            entry,
            exit,
            nperms: np,
        });
    }
    let nb = blocks.len();
    let mut cost = vec![vec![0u16; nb + 1]; nb + 1];
    for (j, blk) in blocks.iter().enumerate() {
        cost[0][j + 1] = junction(n, inst.anchor_cur, blk.entry);
    }
    for (i, bi) in blocks.iter().enumerate() {
        for (j, bj) in blocks.iter().enumerate() {
            if i != j {
                cost[i + 1][j + 1] = junction(n, bi.exit, bj.entry);
            }
        }
    }
    TailInstance {
        anchor_depth: inst.anchor_depth,
        anchor_cur: inst.anchor_cur,
        prefix_chars: inst.prefix_chars,
        blocks,
        cost,
        intra: inst.intra + mv.remove.len() - mv.arcs.len(),
        actual: incumbent,
    }
}

/// Build the merged instance: the two constituent blocks replaced by
/// one, cost matrix re-derived, `intra` up one (the healed boundary
/// becomes a weight-1 move). `incumbent` seeds the B&B upper bound —
/// pass the UNMERGED optimum to search only for strictly cheaper
/// junction totals (`solve_bb` result < incumbent ⇔ merged walk is
/// shorter than `unmerged_total − 1 + (result − incumbent + 1)`… in
/// plain terms: result = incumbent − 1 ⇒ equal length at S−1; result ≤
/// incumbent − 2 ⇒ an 871 candidate). Pass a large incumbent to recover
/// the merged instance's true optimum (tests do).
pub fn apply_merge(
    n: usize,
    g: &Graph,
    inst: &TailInstance,
    mv: &MergeMove,
    incumbent: usize,
) -> TailInstance {
    let mut exit = mv.entry;
    for _ in 1..mv.nperms {
        exit = g.succ1(exit);
    }
    let mut blocks: Vec<Block> = Vec::new();
    for (k, b) in inst.blocks.iter().enumerate() {
        if k == mv.bj {
            continue;
        }
        if k == mv.bi {
            blocks.push(Block {
                entry: mv.entry,
                exit,
                nperms: mv.nperms,
            });
        } else {
            blocks.push(Block {
                entry: b.entry,
                exit: b.exit,
                nperms: b.nperms,
            });
        }
    }
    let nb = blocks.len();
    let mut cost = vec![vec![0u16; nb + 1]; nb + 1];
    for (j, blk) in blocks.iter().enumerate() {
        cost[0][j + 1] = junction(n, inst.anchor_cur, blk.entry);
    }
    for (i, bi) in blocks.iter().enumerate() {
        for (j, bj) in blocks.iter().enumerate() {
            if i != j {
                cost[i + 1][j + 1] = junction(n, bi.exit, bj.entry);
            }
        }
    }
    TailInstance {
        anchor_depth: inst.anchor_depth,
        anchor_cur: inst.anchor_cur,
        prefix_chars: inst.prefix_chars,
        blocks,
        cost,
        intra: inst.intra + 1,
        actual: incumbent,
    }
}

/// Exact Held–Karp optimum (junction total) for instances with ≤
/// `HK_MAX` blocks. Path formulation: start at node 0 (anchor), visit
/// every block, end anywhere.
pub fn solve_hk(inst: &TailInstance) -> Option<usize> {
    let b = inst.blocks.len();
    if b > HK_MAX {
        return None;
    }
    let full = (1usize << b) - 1;
    let mut dp = vec![u16::MAX; (full + 1) * b];
    for j in 0..b {
        dp[(1 << j) * b + j] = inst.cost[0][j + 1];
    }
    for mask in 1..=full {
        for j in 0..b {
            let c = dp[mask * b + j];
            if c == u16::MAX || mask & (1 << j) == 0 {
                continue;
            }
            for k in 0..b {
                if mask & (1 << k) != 0 {
                    continue;
                }
                let nm = mask | (1 << k);
                let nc = c + inst.cost[j + 1][k + 1];
                if nc < dp[nm * b + k] {
                    dp[nm * b + k] = nc;
                }
            }
        }
    }
    (0..b).map(|j| dp[full * b + j] as usize).min()
}

/// Standard O(k³) Hungarian (potentials + explicit alternating-path
/// bookkeeping) on a square cost matrix; large entries mark forbidden
/// cells. Returns the optimal assignment cost — the strong lower bound
/// inside the B&B.
fn hungarian_full(a: &[Vec<u32>]) -> u32 {
    let k = a.len();
    if k == 0 {
        return 0;
    }
    const BIG: i64 = i64::MAX / 4;
    let mut u = vec![0i64; k + 1];
    let mut v = vec![0i64; k + 1];
    let mut p = vec![0usize; k + 1];
    let mut way = vec![0usize; k + 1];
    for i in 1..=k {
        p[0] = i;
        let mut j0 = 0usize;
        let mut minv = vec![BIG; k + 1];
        let mut used = vec![false; k + 1];
        loop {
            used[j0] = true;
            let i0 = p[j0];
            let mut delta = BIG;
            let mut j1 = 0usize;
            for j in 1..=k {
                if used[j] {
                    continue;
                }
                let cur = a[i0 - 1][j - 1] as i64 - u[i0] - v[j];
                if cur < minv[j] {
                    minv[j] = cur;
                    way[j] = j0;
                }
                if minv[j] < delta {
                    delta = minv[j];
                    j1 = j;
                }
            }
            for j in 0..=k {
                if used[j] {
                    u[p[j]] += delta;
                    v[j] -= delta;
                } else {
                    minv[j] -= delta;
                }
            }
            j0 = j1;
            if p[j0] == 0 {
                break;
            }
        }
        while j0 != 0 {
            let j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        }
    }
    let mut total = 0u32;
    for j in 1..=k {
        if p[j] != 0 {
            total += a[p[j] - 1][j - 1];
        }
    }
    total
}

/// Assignment-relaxation lower bound for the remaining path: suppliers =
/// {current node} ∪ unvisited, consumers = unvisited ∪ {END}. Forbidden:
/// self-loops, current → END (must move unless done). Each unvisited
/// block gets an in-edge, exactly one unvisited supplies END (cost 0) —
/// a relaxation of the path constraint (subtours ignored).
fn assignment_lb(cost: &[Vec<u16>], at: usize, unvisited: &[usize]) -> usize {
    let k = unvisited.len();
    if k == 0 {
        return 0;
    }
    const FORBID: u32 = 1 << 20;
    let mut a = vec![vec![FORBID; k + 1]; k + 1];
    for (cj, &j) in unvisited.iter().enumerate() {
        a[0][cj] = cost[at][j + 1] as u32;
    }
    for (si, &i) in unvisited.iter().enumerate() {
        for (cj, &j) in unvisited.iter().enumerate() {
            if i != j {
                a[si + 1][cj] = cost[i + 1][j + 1] as u32;
            }
        }
        a[si + 1][k] = 0; // any unvisited block may end the path
    }
    hungarian_full(&a) as usize
}

/// Exact branch-and-bound. Returns `(optimum, one optimal order)` of
/// block indices (0-based). `collect_ties`: also gather every complete
/// order that achieves the optimum (search prunes only strictly worse
/// prefixes — slower; capped at `tie_cap`).
pub fn solve_bb(
    inst: &TailInstance,
    collect_ties: bool,
    tie_cap: usize,
) -> (usize, Vec<usize>, Vec<Vec<usize>>) {
    let b = inst.blocks.len();
    // Incumbent: the walk's own order.
    let mut best = inst.actual;
    let mut best_order: Vec<usize> = (0..b).collect();
    let mut ties: Vec<Vec<usize>> = Vec::new();

    // Cheap bound ingredient: min in-edge per block (over anchor + all
    // other blocks).
    let min_in: Vec<usize> = (0..b)
        .map(|j| {
            (0..=b)
                .filter(|&i| i != j + 1)
                .map(|i| inst.cost[i][j + 1] as usize)
                .min()
                .unwrap()
        })
        .collect();

    struct Ctx<'a> {
        inst: &'a TailInstance,
        min_in: &'a [usize],
        best: &'a mut usize,
        best_order: &'a mut Vec<usize>,
        ties: &'a mut Vec<Vec<usize>>,
        collect_ties: bool,
        tie_cap: usize,
        order: Vec<usize>,
        unvisited_mask: Vec<bool>,
    }

    fn descend(ctx: &mut Ctx, at: usize, spent: usize) {
        let b = ctx.inst.blocks.len();
        if ctx.order.len() == b {
            if spent < *ctx.best {
                *ctx.best = spent;
                *ctx.best_order = ctx.order.clone();
                ctx.ties.clear();
                if ctx.collect_ties {
                    ctx.ties.push(ctx.order.clone());
                }
            } else if ctx.collect_ties && spent == *ctx.best && ctx.ties.len() < ctx.tie_cap {
                ctx.ties.push(ctx.order.clone());
            }
            return;
        }
        // Tier 1: min-in bound.
        let cheap: usize = (0..b)
            .filter(|&j| ctx.unvisited_mask[j])
            .map(|j| ctx.min_in[j])
            .sum();
        let prune = |lb: usize, best: usize, ties: bool| {
            if ties {
                lb > best
            } else {
                lb >= best
            }
        };
        if prune(spent + cheap, *ctx.best, ctx.collect_ties) {
            return;
        }
        // Tier 2: assignment relaxation, only when tier 1 fails to cut.
        let unvisited: Vec<usize> = (0..b).filter(|&j| ctx.unvisited_mask[j]).collect();
        let lb2 = assignment_lb(&ctx.inst.cost, at, &unvisited);
        if prune(spent + lb2, *ctx.best, ctx.collect_ties) {
            return;
        }
        // Children, nearest junction first.
        let mut children = unvisited;
        children.sort_by_key(|&j| ctx.inst.cost[at][j + 1]);
        for j in children {
            ctx.unvisited_mask[j] = false;
            ctx.order.push(j);
            descend(ctx, j + 1, spent + ctx.inst.cost[at][j + 1] as usize);
            ctx.order.pop();
            ctx.unvisited_mask[j] = true;
        }
    }

    let mut ctx = Ctx {
        inst,
        min_in: &min_in,
        best: &mut best,
        best_order: &mut best_order,
        ties: &mut ties,
        collect_ties,
        tie_cap,
        order: Vec::with_capacity(b),
        unvisited_mask: vec![true; b],
    };
    descend(&mut ctx, 0, 0);
    // If ties were requested and the incumbent (walk order) was never
    // beaten, the walk's own order is among the optima but may not have
    // been re-visited; ensure it is present.
    if collect_ties && best == inst.actual {
        let own: Vec<usize> = (0..b).collect();
        if !ties.contains(&own) && ties.len() < tie_cap {
            ties.push(own);
        }
    }
    (best, best_order, ties)
}

/// Materialize a block order as a full superpermutation string:
/// `prefix_chars` of the source string, then each block joined by its
/// junction characters. Pure string construction — the caller MUST run
/// the validator on the result (emergent windows can in principle
/// duplicate coverage; validity, not construction, is the arbiter).
pub fn materialize(
    n: usize,
    g: &Graph,
    source: &str,
    inst: &TailInstance,
    order: &[usize],
) -> String {
    materialize_from_prefix(n, g, &source[..inst.prefix_chars], inst, order)
}

/// [`materialize`] with an explicit prefix string — the extraction path
/// (I3) heals the prefix, so it can no longer be sliced off the source.
pub fn materialize_from_prefix(
    n: usize,
    g: &Graph,
    prefix: &str,
    inst: &TailInstance,
    order: &[usize],
) -> String {
    let mut s: String = prefix.to_string();
    let mut prev_exit: Option<u32> = None;
    for &bi in order {
        let blk = &inst.blocks[bi];
        let from = match prev_exit {
            None => inst.cost[0][bi + 1],
            Some(e) => junction(n, e, blk.entry),
        } as usize;
        let entry_perm: Vec<u8> = unrank(n, blk.entry as usize);
        let chars: String = entry_perm[n - from..]
            .iter()
            .map(|&d| (b'0' + d) as char)
            .collect();
        s.push_str(&chars);
        // ride the block: nperms − 1 weight-1 moves, each appending the
        // leading symbol of the current perm
        let mut cur = blk.entry;
        for _ in 1..blk.nperms {
            let p = unrank(n, cur as usize);
            s.push((b'0' + p[0]) as char);
            cur = g.succ1(cur);
        }
        debug_assert_eq!(cur, blk.exit, "block must ride to its exit");
        prev_exit = Some(blk.exit);
    }
    s
}

/// Implied L0 allocation (S, d3, d4, d5) of a full-walk weight
/// histogram; `ip` is the waste-identity residue and is 0 for every
/// pure ride/skip/door walk.
pub fn allocation_of(trace: &Trace) -> (usize, usize, usize, usize) {
    // hist[w] = count of weight-w moves; S = #(w≥2) + 1
    let ge2: usize = trace.hist.iter().skip(2).sum();
    (
        ge2 + 1,
        trace.hist.get(3).copied().unwrap_or(0),
        trace.hist.get(4).copied().unwrap_or(0),
        trace.hist.get(5).copied().unwrap_or(0),
    )
}

// ───────────────────────────────────────────────────────────────────────
// I3 — the multi-move tier: `tail-atsp --recomp2` (SURGERY-DESIGN §10,
// s38). Pair recompositions across two distinct tail cycles under the T1
// budget (combined net-split ∈ {−2, −1, 0}) and T2 vocabulary (no
// singleton arcs; lift with `wide`), plus single prefix-part extraction
// of straddling cycles (§10.7): remove a straddling cycle's only prefix
// part, heal its prefix seam exactly, float its perms into the tail as
// one more mergeable block, and re-solve. NOTE the T1 range: §10.4 wrote
// ΔS ∈ {−1, 0}, but nature's own minimal compound (§10.6) is net −2 (two
// merges, +2 door promotions, equal length) — the budget must admit −2
// or the pinned oracle below is unreachable by construction.

/// One single-prefix-part extraction (§10.7).
pub struct Extraction {
    /// Canonical id of the straddling cycle.
    pub cycle: u32,
    /// Entry perm of the floated part.
    pub entry: u32,
    /// Exit perm of the floated part.
    pub exit: u32,
    /// Perms in the part.
    pub nperms: usize,
    /// 1-indexed first-visit depth of the part's entry (reporting).
    pub entry_depth: usize,
    /// Char index in the source where the part's entry junction begins.
    pub cut_start: usize,
    /// Char index in the source just past the heal target's window.
    pub cut_end: usize,
    /// The perm following the part in the walk (the heal target).
    pub y: u32,
    /// Heal junction weight: predecessor → `y`.
    pub heal: u16,
}

/// Enumerate the extraction candidates of an instance: straddling cycles
/// (tail blocks + prefix parts) whose prefix presence is exactly ONE
/// part, with the part strictly inside the prefix (a predecessor exists
/// and the part does not end at the anchor). s37 measured a mean 2.2
/// straddling cycles/walk at anchors 450/520, each with exactly one
/// prefix part, so the single-part restriction loses nothing in
/// practice; multi-part straddlers are silently skipped.
/// The prefix parts of an instance's walk, grouped by cycle: maximal
/// weight-1 runs among path[0..=d0−1] as 0-indexed inclusive spans. The
/// move out of path[d0−1] has weight ≥ 2 (anchor definition), so the
/// scan partitions the prefix completely.
fn prefix_parts(
    g: &Graph,
    trace: &Trace,
    d0: usize,
) -> std::collections::HashMap<u32, Vec<(usize, usize)>> {
    let mut by_cycle: std::collections::HashMap<u32, Vec<(usize, usize)>> =
        std::collections::HashMap::new();
    let mut i1 = 0usize;
    for i in 0..d0 {
        if trace.weights[i] >= 2 {
            by_cycle
                .entry(cycle_id(g, trace.path[i1]))
                .or_default()
                .push((i1, i));
            i1 = i + 1;
        }
    }
    by_cycle
}

pub fn enumerate_extractions(
    n: usize,
    g: &Graph,
    trace: &Trace,
    inst: &TailInstance,
) -> Vec<Extraction> {
    let tail_cycles: std::collections::HashSet<u32> =
        inst.blocks.iter().map(|b| cycle_id(g, b.entry)).collect();
    let d0 = inst.anchor_depth; // anchor perm is path[d0 − 1]
    let by_cycle = prefix_parts(g, trace, d0);
    let mut out = Vec::new();
    for (c, ps) in &by_cycle {
        if !tail_cycles.contains(c) || ps.len() != 1 {
            continue;
        }
        let (a, b) = ps[0];
        // need a predecessor, and the heal target still inside the prefix
        if a == 0 || b + 1 > d0 - 1 {
            continue;
        }
        let cut_start = n + trace.weights[..a]
            .iter()
            .map(|&w| w as usize)
            .sum::<usize>();
        let cut_end = n + trace.weights[..=b]
            .iter()
            .map(|&w| w as usize)
            .sum::<usize>();
        let y = trace.path[b + 1];
        out.push(Extraction {
            cycle: *c,
            entry: trace.path[a],
            exit: trace.path[b],
            nperms: b - a + 1,
            entry_depth: a + 1,
            cut_start,
            cut_end,
            y,
            heal: junction(n, trace.path[a - 1], y),
        });
    }
    out.sort_by_key(|e| e.entry_depth);
    out
}

fn rebuild_cost(n: usize, anchor_cur: u32, blocks: &[Block]) -> Vec<Vec<u16>> {
    let nb = blocks.len();
    let mut cost = vec![vec![0u16; nb + 1]; nb + 1];
    for (j, blk) in blocks.iter().enumerate() {
        cost[0][j + 1] = junction(n, anchor_cur, blk.entry);
    }
    for (i, bi) in blocks.iter().enumerate() {
        for (j, bj) in blocks.iter().enumerate() {
            if i != j {
                cost[i + 1][j + 1] = junction(n, bi.exit, bj.entry);
            }
        }
    }
    cost
}

/// Build the extraction-extended instance: the floated part appended as
/// one more block, prefix bookkeeping healed (`prefix_chars` shrinks by
/// the part's junctions + rides and grows by the heal junction), `intra`
/// up by the part's rides. `incumbent` seeds the B&B bound as usual.
pub fn apply_extraction(
    n: usize,
    g: &Graph,
    inst: &TailInstance,
    ext: &Extraction,
    incumbent: usize,
) -> TailInstance {
    let mut blocks: Vec<Block> = inst
        .blocks
        .iter()
        .map(|b| Block {
            entry: b.entry,
            exit: b.exit,
            nperms: b.nperms,
        })
        .collect();
    blocks.push(Block {
        entry: ext.entry,
        exit: ext.exit,
        nperms: ext.nperms,
    });
    let cost = rebuild_cost(n, inst.anchor_cur, &blocks);
    debug_assert_eq!(g.succ1(ext.exit), {
        // the part must be a genuine w1 ride of its cycle
        let mut e = ext.entry;
        for _ in 0..ext.nperms {
            e = g.succ1(e);
        }
        e
    });
    TailInstance {
        anchor_depth: inst.anchor_depth,
        anchor_cur: inst.anchor_cur,
        prefix_chars: ext.cut_start + ext.heal as usize + (inst.prefix_chars - ext.cut_end),
        blocks,
        cost,
        intra: inst.intra + ext.nperms - 1,
        actual: incumbent,
    }
}

/// The healed prefix string of an extraction: source up to the part's
/// entry junction, the heal junction's characters completing `y`'s
/// window, then the untouched rest of the source prefix.
pub fn healed_prefix(
    n: usize,
    source: &str,
    source_prefix_chars: usize,
    ext: &Extraction,
) -> String {
    let mut s = source[..ext.cut_start].to_string();
    let y = unrank(n, ext.y as usize);
    for &d in &y[n - ext.heal as usize..] {
        s.push((b'0' + d) as char);
    }
    s.push_str(&source[ext.cut_end..source_prefix_chars]);
    s
}

/// Apply several recomposition moves on DISTINCT cycles at once (their
/// `remove` sets are disjoint by construction). Generalizes
/// [`apply_recomp`]; an empty slice reproduces the instance with a new
/// incumbent.
pub fn apply_recomp_multi(
    n: usize,
    g: &Graph,
    inst: &TailInstance,
    mvs: &[&RecompMove],
    incumbent: usize,
) -> TailInstance {
    let mut removed = vec![false; inst.blocks.len()];
    let mut intra = inst.intra;
    for mv in mvs {
        for &k in &mv.remove {
            debug_assert!(!removed[k], "moves must touch distinct cycles");
            removed[k] = true;
        }
        intra += mv.remove.len();
        intra -= mv.arcs.len();
    }
    let mut blocks: Vec<Block> = inst
        .blocks
        .iter()
        .enumerate()
        .filter(|(k, _)| !removed[*k])
        .map(|(_, b)| Block {
            entry: b.entry,
            exit: b.exit,
            nperms: b.nperms,
        })
        .collect();
    for mv in mvs {
        for &(entry, np) in &mv.arcs {
            let mut exit = entry;
            for _ in 1..np {
                exit = g.succ1(exit);
            }
            blocks.push(Block {
                entry,
                exit,
                nperms: np,
            });
        }
    }
    let cost = rebuild_cost(n, inst.anchor_cur, &blocks);
    TailInstance {
        anchor_depth: inst.anchor_depth,
        anchor_cur: inst.anchor_cur,
        prefix_chars: inst.prefix_chars,
        blocks,
        cost,
        intra,
        actual: incumbent,
    }
}

/// T1 ingredient: a move's net split delta (arcs − parts removed).
pub fn net_split(mv: &RecompMove) -> i64 {
    mv.arcs.len() as i64 - mv.remove.len() as i64
}

/// T2 ingredient: does the move use an out-of-vocabulary singleton arc?
/// (M-R1's vocabulary {n, 2|4, 3|3, 2|2|2} at n=6 is exactly the
/// singleton-free composition set — 17 of the 63 full-cycle start-sets —
/// so "no arc of length 1" is the n-generic form of T2.)
pub fn has_singleton_arc(mv: &RecompMove) -> bool {
    mv.arcs.iter().any(|&(_, l)| l == 1)
}

/// Recomp-1's per-cycle variant enumeration, grouped by cycle id — the
/// pair enumerator's raw material.
pub fn recomp_variants_by_cycle(
    n: usize,
    g: &Graph,
    inst: &TailInstance,
) -> Vec<(u32, Vec<RecompMove>)> {
    let mut map: std::collections::BTreeMap<u32, Vec<RecompMove>> =
        std::collections::BTreeMap::new();
    for mv in enumerate_recomps(n, g, inst) {
        map.entry(cycle_id(g, inst.blocks[mv.remove[0]].entry))
            .or_default()
            .push(mv);
    }
    map.into_iter().collect()
}

/// The s35 loop-count relation — the T4 tripwire (§10.7: tautological as
/// a prune, kept as a consistency assertion): `L = S + #doors −
/// ((n−1)! − 1)`, exceptionless on every walk ever measured (22k+ n=6
/// classes incl. off-shell 873s, all 87 n=7 walks). Corpus-law status —
/// derivation OPEN (THEORY §6) — so a violation on a materialized
/// compound is either a solver bug or drop-everything news.
pub struct LoopCheck {
    /// Distinct 2-loops ridden by the walk's w2 moves.
    pub l: usize,
    /// Sojourn parts.
    pub s: usize,
    /// Inter-cycle w≥3 moves.
    pub doors: usize,
    /// Whether the loop-count relation holds.
    pub holds: bool,
}

/// Evaluate the loop-count relation on a traced walk (mirrors
/// `analysis/counting/loop_census.py`).
pub fn loop_relation(n: usize, g: &Graph, trace: &Trace) -> LoopCheck {
    let mut loops = std::collections::HashSet::new();
    let mut doors = 0usize;
    let mut s = 1usize;
    for i in 0..trace.path.len() - 1 {
        let w = trace.weights[i];
        if w >= 2 {
            s += 1;
        }
        if w == 2 {
            loops.insert(loop_id(n, trace.path[i]));
        } else if w >= 3 && cycle_id(g, trace.path[i]) != cycle_id(g, trace.path[i + 1]) {
            doors += 1;
        }
    }
    let l = loops.len();
    LoopCheck {
        l,
        s,
        doors,
        holds: l + factorial(n - 1) == s + doors + 1,
    }
}

/// Phase-specific 2-loop id of the loop a w2 move out of `a` rides: min
/// rank over the g-orbit of rot(a), g(q) = q₂…q_{n−1} q₁ q_n (the
/// loop_census.py definition).
fn loop_id(n: usize, a: u32) -> u32 {
    let pa = unrank(n, a as usize);
    let mut q: Vec<u8> = pa[1..].to_vec();
    q.push(pa[0]);
    let mut m = crate::graph::rank(&q) as u32;
    for _ in 0..n - 2 {
        let q0 = q[0];
        for i in 0..n - 2 {
            q[i] = q[i + 1];
        }
        q[n - 2] = q0;
        m = m.min(crate::graph::rank(&q) as u32);
    }
    m
}

/// Classification of one recomp2 find.
#[derive(PartialEq, Eq, Clone, Copy)]
pub enum R2Kind {
    /// Materialized walk is SHORTER than the source — candidate ritual.
    Shorter,
    /// Equal length, different L0 allocation.
    EqualNew,
    /// Equal length, same allocation (sampled for offline m3_check).
    EqualSame,
}

/// One materialized, validator-complete recomp2 find.
pub struct R2Find {
    pub kind: R2Kind,
    pub s: String,
    pub alloc: (usize, usize, usize, usize),
    pub desc: String,
    pub lambda_ok: bool,
}

/// Per-walk report of the recomp2 sweep.
#[derive(Default)]
pub struct R2Report {
    /// Extraction candidates found (straddling, single prefix part).
    pub ext_candidates: usize,
    /// Distinct-cycle variant pairs before any filter (all contexts).
    pub raw_pairs: u64,
    /// Pairs surviving T1 (before T2).
    pub t1_pairs: u64,
    /// Exact re-solves performed (post-T2 pairs + extraction identity +
    /// extraction-context singles).
    pub solved: u64,
    /// Re-solves by combined net split: index 0/1/2 = net −2/−1/0.
    pub solved_by_net: [u64; 3],
    pub improved: u64,
    pub equal_new: u64,
    pub equal_same: u64,
    /// Loop-relation violations among complete finds (tripwire).
    pub lambda_bad: u64,
    /// Equal-length new-allocation counts by allocation (uncapped).
    pub eq_new_allocs: std::collections::BTreeMap<(usize, usize, usize, usize), u64>,
    /// Materialized finds (Shorter uncapped; EqualNew/EqualSame capped).
    pub finds: Vec<R2Find>,
}

fn perm_str(n: usize, r: u32) -> String {
    unrank(n, r as usize)
        .iter()
        .map(|&d| (b'0' + d) as char)
        .collect()
}

fn mv_str(n: usize, g: &Graph, inst: &TailInstance, mv: &RecompMove) -> String {
    let cid = cycle_id(g, inst.blocks[mv.remove[0]].entry);
    let arcs: Vec<String> = mv
        .arcs
        .iter()
        .map(|&(e, l)| format!("{}x{}", perm_str(n, e), l))
        .collect();
    format!(
        "{}:{}->{}",
        perm_str(n, cid),
        mv.remove.len(),
        arcs.join("|")
    )
}

struct R2Ctx<'a> {
    n: usize,
    g: &'a Graph,
    src_len: usize,
    src_alloc: (usize, usize, usize, usize),
    cap_eq_new: usize,
    cap_eq_same: usize,
    kept_eq_new: usize,
    kept_eq_same: usize,
}

impl R2Ctx<'_> {
    /// Solve one candidate instance and classify/record the outcome.
    fn solve_one(
        &mut self,
        rep: &mut R2Report,
        m: &TailInstance,
        prefix: &str,
        inc: usize,
        net: i64,
        desc: &dyn Fn() -> String,
    ) {
        rep.solved += 1;
        rep.solved_by_net[(net + 2) as usize] += 1;
        let (mopt, morder, _) = solve_bb(m, false, 0);
        if mopt >= inc {
            return;
        }
        let s = materialize_from_prefix(self.n, self.g, prefix, m, &morder);
        let v = crate::validate::validate(self.n, &s);
        if !v.complete {
            return;
        }
        debug_assert_eq!(s.len(), m.prefix_chars + m.intra + mopt);
        let t = crate::trace::trace_string(self.g, &s).expect("recomp2 trace");
        let alloc = allocation_of(&t);
        let lc = loop_relation(self.n, self.g, &t);
        if !lc.holds {
            rep.lambda_bad += 1;
        }
        if s.len() < self.src_len {
            rep.improved += 1;
            rep.finds.push(R2Find {
                kind: R2Kind::Shorter,
                s,
                alloc,
                desc: desc(),
                lambda_ok: lc.holds,
            });
        } else if alloc != self.src_alloc {
            rep.equal_new += 1;
            *rep.eq_new_allocs.entry(alloc).or_default() += 1;
            if self.kept_eq_new < self.cap_eq_new || !lc.holds {
                self.kept_eq_new += 1;
                rep.finds.push(R2Find {
                    kind: R2Kind::EqualNew,
                    s,
                    alloc,
                    desc: desc(),
                    lambda_ok: lc.holds,
                });
            }
        } else {
            rep.equal_same += 1;
            if self.kept_eq_same < self.cap_eq_same || !lc.holds {
                self.kept_eq_same += 1;
                rep.finds.push(R2Find {
                    kind: R2Kind::EqualSame,
                    s,
                    alloc,
                    desc: desc(),
                    lambda_ok: lc.holds,
                });
            }
        }
    }

    /// Sweep one context (an instance + its prefix): all distinct-cycle
    /// variant pairs under T1(+T2); with `singles`, also every single
    /// move (the extraction contexts — extraction + one recomp is itself
    /// a 2-edit compound recomp-1 never tried). `singleton_prefix` =
    /// cycles whose remaining prefix parts include a size-1 part, so any
    /// move on them leaves the cycle's full composition out of the M-R1
    /// vocabulary.
    #[allow(clippy::too_many_arguments)]
    fn sweep(
        &mut self,
        rep: &mut R2Report,
        inst: &TailInstance,
        prefix: &str,
        wide: bool,
        net0: bool,
        singles: bool,
        singleton_prefix: &std::collections::HashSet<u32>,
        ext_desc: &str,
    ) {
        let (n, g) = (self.n, self.g);
        let groups = recomp_variants_by_cycle(n, g, inst);
        let admissible = |cid: u32, mv: &RecompMove| {
            wide || (!has_singleton_arc(mv) && !singleton_prefix.contains(&cid))
        };
        let net_lo = -2i64;
        let net_hi = if net0 { 0i64 } else { -1 };
        if singles {
            for (cid, mvs) in &groups {
                for mv in mvs {
                    let net = net_split(mv);
                    if !(net_lo..=net_hi).contains(&net) || !admissible(*cid, mv) {
                        continue;
                    }
                    let intra_m = inst.intra + mv.remove.len() - mv.arcs.len();
                    let inc = self.src_len + 1 - inst.prefix_chars - intra_m;
                    let m = apply_recomp_multi(n, g, inst, &[mv], inc);
                    self.solve_one(rep, &m, prefix, inc, net, &|| {
                        format!("{ext_desc}{}", mv_str(n, g, inst, mv))
                    });
                }
            }
        }
        for i in 0..groups.len() {
            for j in i + 1..groups.len() {
                let (ca, va) = (&groups[i].0, &groups[i].1);
                let (cb, vb) = (&groups[j].0, &groups[j].1);
                rep.raw_pairs += (va.len() * vb.len()) as u64;
                for a in va {
                    let na = net_split(a);
                    for b in vb {
                        let net = na + net_split(b);
                        if !(net_lo..=net_hi).contains(&net) {
                            continue;
                        }
                        rep.t1_pairs += 1;
                        if !admissible(*ca, a) || !admissible(*cb, b) {
                            continue;
                        }
                        let intra_m = inst.intra + a.remove.len() + b.remove.len()
                            - a.arcs.len()
                            - b.arcs.len();
                        let inc = self.src_len + 1 - inst.prefix_chars - intra_m;
                        let m = apply_recomp_multi(n, g, inst, &[a, b], inc);
                        self.solve_one(rep, &m, prefix, inc, net, &|| {
                            format!(
                                "{ext_desc}{} x {}",
                                mv_str(n, g, inst, a),
                                mv_str(n, g, inst, b)
                            )
                        });
                    }
                }
            }
        }
    }
}

/// The full I3 sweep of one walk: the tail-pair context, plus one
/// context per extraction candidate (float the part, then identity /
/// singles / pairs on the extended instance). The caller guarantees the
/// base instance is block-order-optimal (I1 handles improvements there).
#[allow(clippy::too_many_arguments)]
pub fn recomp2_walk(
    n: usize,
    g: &Graph,
    source: &str,
    trace: &Trace,
    inst: &TailInstance,
    wide: bool,
    net0: bool,
    cap_eq_new: usize,
    cap_eq_same: usize,
) -> R2Report {
    let mut rep = R2Report::default();
    let mut ctx = R2Ctx {
        n,
        g,
        src_len: source.len(),
        src_alloc: allocation_of(trace),
        cap_eq_new,
        cap_eq_same,
        kept_eq_new: 0,
        kept_eq_same: 0,
    };
    // T2 ingredient: cycles whose prefix parts include a size-1 part —
    // any tail recomposition leaves their full composition out of the
    // M-R1 vocabulary.
    let base_singleton: std::collections::HashSet<u32> = prefix_parts(g, trace, inst.anchor_depth)
        .iter()
        .filter(|(_, ps)| ps.iter().any(|&(a, b)| a == b))
        .map(|(c, _)| *c)
        .collect();
    // Context 0: no extraction. Singles here are recomp-1's move space —
    // already swept corpus-wide — so pairs only.
    let base_prefix = &source[..inst.prefix_chars];
    ctx.sweep(
        &mut rep,
        inst,
        base_prefix,
        wide,
        net0,
        false,
        &base_singleton,
        "",
    );
    // One context per extraction candidate.
    let exts = enumerate_extractions(n, g, trace, inst);
    rep.ext_candidates = exts.len();
    for ext in &exts {
        let ei = apply_extraction(n, g, inst, ext, 0);
        let prefix = healed_prefix(n, source, inst.prefix_chars, ext);
        debug_assert_eq!(prefix.len(), ei.prefix_chars);
        // the extracted cycle's only prefix part is now in the tail
        let mut singleton = base_singleton.clone();
        singleton.remove(&ext.cycle);
        let ext_desc = format!(
            "ext {}@{}x{} + ",
            perm_str(n, ext.cycle),
            ext.entry_depth,
            ext.nperms
        );
        // extraction identity: float the part, just re-solve the order
        let inc0 = ctx.src_len + 1 - ei.prefix_chars - ei.intra;
        let m0 = apply_recomp_multi(n, g, &ei, &[], inc0);
        ctx.solve_one(&mut rep, &m0, &prefix, inc0, 0, &|| {
            format!("{ext_desc}float-only")
        });
        ctx.sweep(
            &mut rep, &ei, &prefix, wide, net0, true, &singleton, &ext_desc,
        );
    }
    rep
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::graph::Graph;
    use crate::trace::trace_string;

    fn instance_for(n: usize, s: &str, min_depth: usize) -> (Graph, Trace, TailInstance) {
        let g = Graph::new(n);
        let t = trace_string(&g, s).expect("trace");
        let inst = decompose(n, &t, min_depth).expect("decompose");
        (g, t, inst)
    }

    /// n=5 control: greedy's 153 is PROVEN optimal, so every tail must
    /// be block-order-optimal — any "improvement" is a solver bug.
    #[test]
    fn n5_greedy_tail_is_block_order_optimal() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        assert_eq!(res.string.len(), 153);
        for min_depth in [60, 80, 100] {
            let t = trace_string(&g, &res.string).unwrap();
            if let Some(inst) = decompose(5, &t, min_depth) {
                let (opt, _, _) = solve_bb(&inst, false, 0);
                assert_eq!(opt, inst.actual, "n=5 anchor {min_depth}");
                if let Some(hk) = solve_hk(&inst) {
                    assert_eq!(hk, opt, "HK/B&B must agree");
                }
            }
        }
    }

    /// A deliberately mangled order must cost strictly more than the
    /// optimum, and the solver must recover the optimum regardless.
    #[test]
    fn mangled_order_costs_more() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        let t = trace_string(&g, &res.string).unwrap();
        let inst = decompose(5, &t, 80).expect("decompose");
        let b = inst.blocks.len();
        assert!(b >= 3, "need blocks to mangle");
        let (opt, order, _) = solve_bb(&inst, false, 0);
        assert_eq!(opt, inst.actual);
        // swap two blocks in the walk's own order
        let mut mangled: Vec<usize> = (0..b).collect();
        mangled.swap(0, b - 1);
        let cost_of = |ord: &[usize]| -> usize {
            let mut at = 0usize;
            let mut c = 0usize;
            for &j in ord {
                c += inst.cost[at][j + 1] as usize;
                at = j + 1;
            }
            c
        };
        assert!(cost_of(&mangled) > opt);
        assert_eq!(cost_of(&order), opt);
    }

    /// Materializing the walk's own order must reproduce the source
    /// string byte-identically.
    #[test]
    fn materialize_identity_roundtrip() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        let t = trace_string(&g, &res.string).unwrap();
        let inst = decompose(5, &t, 80).expect("decompose");
        let own: Vec<usize> = (0..inst.blocks.len()).collect();
        let s = materialize(5, &g, &res.string, &inst, &own);
        assert_eq!(s, res.string);
    }

    /// The s28 surgery oracle: from the (143,5) side of the natural
    /// specimen pair (`data/surgery_specimens/`, byte-identical to
    /// depth 584), the tie search anchored at the natural cut must
    /// re-derive the (142,6) partner BYTE-IDENTICALLY — the full
    /// pipeline (anchor → blocks → exact search → materialize) crossing
    /// an allocation boundary end-to-end.
    #[test]
    fn tie_oracle_rederives_partner_across_allocations() {
        let g = Graph::new(6);
        let dir = std::path::Path::new("data/surgery_specimens");
        let corpus = crate::corpus::load_corpus(&g, &[dir]).expect("pair");
        assert_eq!(corpus.len(), 2);
        let c5 = corpus
            .iter()
            .find(|r| r.name.contains("0105a4b77ce8"))
            .expect("(143,5) side");
        let c6 = corpus
            .iter()
            .find(|r| r.name.contains("b020caf20414"))
            .expect("(142,6) side");
        assert_eq!(allocation_of(&c5.trace), (143, 5, 0, 0));
        assert_eq!(allocation_of(&c6.trace), (142, 6, 0, 0));
        let inst = decompose(6, &c5.trace, 580).expect("decompose");
        let (opt, _, ties) = solve_bb(&inst, true, 512);
        assert_eq!(opt, inst.actual, "pair is block-order-optimal");
        let rederived = ties.iter().any(|ord| {
            let s = materialize(6, &g, &c5.string, &inst, ord);
            s == c6.string
        });
        assert!(rederived, "tie search must re-derive the (142,6) partner");
    }

    /// I2a control: n=5's 153 is PROVEN optimal, so no merge move may
    /// complete below it — a merged junction total ≤ optimum − 2 would
    /// be a 152, i.e. a solver bug. Equal-cost merges (optimum − 1) are
    /// legal (equal-length walks in an S−1 allocation). Also cross-check
    /// every merged instance against Held–Karp at a loose incumbent.
    #[test]
    fn n5_no_merge_beats_proven_optimum() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        for min_depth in [60, 80, 100] {
            let t = trace_string(&g, &res.string).unwrap();
            let Some(inst) = decompose(5, &t, min_depth) else {
                continue;
            };
            let (opt, _, _) = solve_bb(&inst, false, 0);
            assert_eq!(opt, inst.actual);
            for mv in enumerate_merges(5, &g, &inst) {
                let loose = apply_merge(5, &g, &inst, &mv, 10_000);
                let (true_opt, _, _) = solve_bb(&loose, false, 0);
                if let Some(hk) = solve_hk(&loose) {
                    assert_eq!(hk, true_opt, "HK/B&B must agree on merged instance");
                }
                assert!(
                    true_opt + 2 > opt,
                    "merge at anchor {min_depth} would give a 152 — solver bug"
                );
            }
        }
    }

    /// I2a oracle: anchored SHALLOWER than the natural seam (so both
    /// parts of cycle 135462 are in the tail), merging the (143,5)
    /// side's 2|4 into a whole-6 and re-solving with ties must re-derive
    /// the (142,6) partner BYTE-IDENTICALLY at equal length — the s29
    /// census's unit trade, now driven by the instrument end-to-end.
    #[test]
    fn merge_oracle_rederives_partner_from_shallow_anchor() {
        let g = Graph::new(6);
        let dir = std::path::Path::new("data/surgery_specimens");
        let corpus = crate::corpus::load_corpus(&g, &[dir]).expect("pair");
        let c5 = corpus
            .iter()
            .find(|r| r.name.contains("0105a4b77ce8"))
            .expect("(143,5) side");
        let c6 = corpus
            .iter()
            .find(|r| r.name.contains("b020caf20414"))
            .expect("(142,6) side");
        let inst = decompose(6, &c5.trace, 570).expect("decompose");
        assert!(inst.anchor_depth < 583, "seam parts must both be in-tail");
        let (opt, _, _) = solve_bb(&inst, false, 0);
        assert_eq!(opt, inst.actual, "specimen is block-order-optimal");
        // The seam merge: whole-cycle variant entered at 462135.
        let seam_entry: Vec<u8> = vec![4, 6, 2, 1, 3, 5];
        let mv = enumerate_merges(6, &g, &inst)
            .into_iter()
            .find(|m| m.nperms == 6 && unrank(6, m.entry as usize) == seam_entry)
            .expect("seam merge variant must exist");
        let merged = apply_merge(6, &g, &inst, &mv, opt - 1);
        let (mopt, _, ties) = solve_bb(&merged, true, 4096);
        assert_eq!(mopt, opt - 1, "seam merge re-prices to equal length");
        let rederived = ties.iter().any(|ord| {
            let s = materialize(6, &g, &c5.string, &merged, ord);
            s == c6.string
        });
        assert!(rederived, "merge + tie search must re-derive the partner");
    }

    /// Recomp-1 control: n=5's 153 is proven optimal, so no single-cycle
    /// recomposition may complete below it. Also pins the bookkeeping
    /// identity on every recomposed instance: materialized length =
    /// prefix + intra' + optimal junction total.
    #[test]
    fn n5_no_recomp_beats_proven_optimum() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        let t = trace_string(&g, &res.string).unwrap();
        let inst = decompose(5, &t, 100).expect("decompose");
        let (opt, _, _) = solve_bb(&inst, false, 0);
        assert_eq!(opt, inst.actual);
        let moves = enumerate_recomps(5, &g, &inst);
        assert!(!moves.is_empty(), "n=5 tail must admit recompositions");
        for mv in &moves {
            let m = apply_recomp(5, &g, &inst, mv, 10_000);
            let (true_opt, order, _) = solve_bb(&m, false, 0);
            if let Some(hk) = solve_hk(&m) {
                assert_eq!(hk, true_opt, "HK/B&B must agree on recomposed instance");
            }
            let s = materialize(5, &g, &res.string, &m, &order);
            assert_eq!(
                s.len(),
                m.prefix_chars + m.intra + true_opt,
                "length bookkeeping must be exact"
            );
            assert!(s.len() >= 153, "a sub-153 would be a solver bug");
            let v = crate::validate::validate(5, &s);
            assert!(v.complete, "recomposed walks must stay complete covers");
        }
    }

    /// Recomp-1 subsumes the seam merge: from the shallow anchor, the
    /// whole-6 recomposition of cycle 135462 entered at 462135 must
    /// re-price to exactly one junction unit below the unmerged optimum
    /// (the equal-length S−1 edit the merge oracle pins byte-exactly).
    #[test]
    fn recomp_finds_the_seam_edit() {
        let g = Graph::new(6);
        let dir = std::path::Path::new("data/surgery_specimens");
        let corpus = crate::corpus::load_corpus(&g, &[dir]).expect("pair");
        let c5 = corpus
            .iter()
            .find(|r| r.name.contains("0105a4b77ce8"))
            .expect("(143,5) side");
        let inst = decompose(6, &c5.trace, 570).expect("decompose");
        let (opt, _, _) = solve_bb(&inst, false, 0);
        let seam_entry: Vec<u8> = vec![4, 6, 2, 1, 3, 5];
        let mv = enumerate_recomps(6, &g, &inst)
            .into_iter()
            .find(|m| {
                m.arcs.len() == 1
                    && m.arcs[0].1 == 6
                    && unrank(6, m.arcs[0].0 as usize) == seam_entry
            })
            .expect("whole-6 seam variant must be enumerated");
        assert_eq!(mv.remove.len(), 2, "seam cycle has two tail parts");
        let inc = opt + mv.arcs.len() + 1 - mv.remove.len();
        let m = apply_recomp(6, &g, &inst, &mv, inc);
        let (mopt, _, _) = solve_bb(&m, false, 0);
        assert_eq!(
            mopt,
            inc - 1,
            "seam recomposition re-prices to equal length"
        );
    }

    /// I3 control (§10.4): no pair compound — nor any extraction
    /// compound — may beat n=5's proven optimum. Runs the full recomp2
    /// sweep in wide mode (singletons in, the broadest negative).
    #[test]
    fn n5_no_pair_compound_beats_proven_optimum() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        let t = trace_string(&g, &res.string).unwrap();
        let inst = decompose(5, &t, 100).expect("decompose");
        let (opt, _, _) = solve_bb(&inst, false, 0);
        assert_eq!(opt, inst.actual);
        let rep = recomp2_walk(5, &g, &res.string, &t, &inst, true, true, 64, 64);
        assert!(rep.solved > 0, "control must exercise the solver");
        assert_eq!(rep.improved, 0, "a sub-153 pair compound is a solver bug");
        assert_eq!(rep.lambda_bad, 0, "loop relation must hold on every find");
        for f in &rep.finds {
            assert_eq!(f.s.len(), 153);
            assert!(crate::validate::validate(5, &f.s).complete);
        }
    }

    /// I3 solver cross-check: on n=5-sized pair instances, Held–Karp and
    /// B&B must agree (loose incumbent recovers the true optimum).
    #[test]
    fn n5_pair_apply_hk_bb_agree() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        let t = trace_string(&g, &res.string).unwrap();
        let inst = decompose(5, &t, 100).expect("decompose");
        let groups = recomp_variants_by_cycle(5, &g, &inst);
        let mut checked = 0;
        'outer: for i in 0..groups.len() {
            for j in i + 1..groups.len() {
                for a in &groups[i].1 {
                    for b in &groups[j].1 {
                        if !(-2..=0).contains(&(net_split(a) + net_split(b))) {
                            continue;
                        }
                        let m = apply_recomp_multi(5, &g, &inst, &[a, b], 10_000);
                        let (bb, _, _) = solve_bb(&m, false, 0);
                        assert_eq!(solve_hk(&m), Some(bb), "HK/B&B must agree");
                        checked += 1;
                        if checked >= 40 {
                            break 'outer;
                        }
                    }
                }
            }
        }
        assert!(checked > 0, "cross-check must exercise pair instances");
    }

    /// §10.4 control — synthetic composition: two recomp-1 moves on
    /// disjoint cycles that each complete at equal cost must be
    /// composable by the pair enumerator at the composed (equal) cost.
    /// (Below it would be a sub-153 — a bug.)
    #[test]
    fn synthetic_composition_re_finds_composed_cost() {
        let g = Graph::new(5);
        let res = crate::greedy::greedy(&g);
        let t = trace_string(&g, &res.string).unwrap();
        let inst = decompose(5, &t, 100).expect("decompose");
        let (opt, _, _) = solve_bb(&inst, false, 0);
        assert_eq!(opt, inst.actual);
        let groups = recomp_variants_by_cycle(5, &g, &inst);
        // equal-cost singles, grouped by cycle
        let mut eq: Vec<(usize, &RecompMove)> = Vec::new();
        for (gi, (_, mvs)) in groups.iter().enumerate() {
            for mv in mvs {
                let intra_m = inst.intra + mv.remove.len() - mv.arcs.len();
                let inc = res.string.len() + 1 - inst.prefix_chars - intra_m;
                let m = apply_recomp_multi(5, &g, &inst, &[mv], inc);
                let (mopt, _, _) = solve_bb(&m, false, 0);
                if mopt + 1 == inc {
                    eq.push((gi, mv));
                }
            }
        }
        let mut composed = 0;
        for x in 0..eq.len() {
            for y in x + 1..eq.len() {
                let ((ga, a), (gb, b)) = (&eq[x], &eq[y]);
                if ga == gb {
                    continue;
                }
                let intra_m =
                    inst.intra + a.remove.len() + b.remove.len() - a.arcs.len() - b.arcs.len();
                let inc = res.string.len() + 1 - inst.prefix_chars - intra_m;
                let m = apply_recomp_multi(5, &g, &inst, &[a, b], inc);
                let (mopt, _, _) = solve_bb(&m, false, 0);
                assert!(mopt + 1 >= inc, "sub-153 composition is a solver bug");
                if mopt + 1 == inc {
                    composed += 1;
                }
            }
        }
        assert!(
            composed > 0,
            "at least one pair of equal-cost moves must compose at the composed cost"
        );
    }

    /// §10.4 control — the seam edit composed with a length-neutral
    /// second move must still price at exactly inc − 1 (equal length),
    /// stay validator-complete, and satisfy the loop relation.
    #[test]
    fn seam_plus_neutral_pair_prices_equal() {
        let g = Graph::new(6);
        let dir = std::path::Path::new("data/surgery_specimens");
        let corpus = crate::corpus::load_corpus(&g, &[dir]).expect("pair");
        let c5 = corpus
            .iter()
            .find(|r| r.name.contains("0105a4b77ce8"))
            .expect("(143,5) side");
        let inst = decompose(6, &c5.trace, 570).expect("decompose");
        let (opt, _, _) = solve_bb(&inst, false, 0);
        assert_eq!(opt, inst.actual);
        let src_len = c5.string.len();
        let groups = recomp_variants_by_cycle(6, &g, &inst);
        let seam_entry: Vec<u8> = vec![4, 6, 2, 1, 3, 5];
        let seam_cycle = cycle_id(&g, crate::graph::rank(&seam_entry) as u32);
        let (sg, seam) = groups
            .iter()
            .enumerate()
            .find_map(|(gi, (cid, mvs))| {
                if *cid != seam_cycle {
                    return None;
                }
                mvs.iter()
                    .find(|m| {
                        m.arcs.len() == 1
                            && m.arcs[0].1 == 6
                            && unrank(6, m.arcs[0].0 as usize) == seam_entry
                    })
                    .map(|m| (gi, m))
            })
            .expect("seam variant");
        // a second, length-neutral move on a different cycle: net +1 and
        // equal-cost on its own, so the pair is net 0 — inside T1
        let mut partner: Option<(usize, &RecompMove)> = None;
        'hunt: for (gi, (_, mvs)) in groups.iter().enumerate() {
            if gi == sg {
                continue;
            }
            for mv in mvs {
                if net_split(mv) != 1 || has_singleton_arc(mv) {
                    continue;
                }
                let intra_m = inst.intra + mv.remove.len() - mv.arcs.len();
                let inc = src_len + 1 - inst.prefix_chars - intra_m;
                let m = apply_recomp_multi(6, &g, &inst, &[mv], inc);
                let (mopt, _, _) = solve_bb(&m, false, 0);
                if mopt + 1 != inc {
                    continue;
                }
                // compose with the seam edit (pair net 0, T1-admissible)
                let intra_p = inst.intra + seam.remove.len() + mv.remove.len()
                    - seam.arcs.len()
                    - mv.arcs.len();
                let inc_p = src_len + 1 - inst.prefix_chars - intra_p;
                let p = apply_recomp_multi(6, &g, &inst, &[seam, mv], inc_p);
                let (popt, porder, _) = solve_bb(&p, false, 0);
                assert!(
                    popt + 1 >= inc_p,
                    "a sub-872 here would be an 871 — investigate"
                );
                if popt + 1 == inc_p {
                    let s = materialize(6, &g, &c5.string, &p, &porder);
                    assert_eq!(s.len(), src_len);
                    assert!(crate::validate::validate(6, &s).complete);
                    let t = trace_string(&g, &s).unwrap();
                    assert!(loop_relation(6, &g, &t).holds, "loop relation tripwire");
                    partner = Some((gi, mv));
                    break 'hunt;
                }
            }
        }
        assert!(
            partner.is_some(),
            "the seam edit must compose with a length-neutral partner at equal length"
        );
    }

    /// §10.6's natural-compound oracle — s38 MEASURED VERDICT, pinned:
    /// the compound is NOT expressible at anchored reach, and the
    /// instrument proves it. From the (145,3) A side, extraction of
    /// cycle 126354's prefix part @181 (heal = w6: the part is entered
    /// by a w2 edge whose only local repair is a full re-spell) plus the
    /// two whole-6 merges refutes EVERY entry pair at equal length; the
    /// extraction-identity and the B-entry compound both price exactly
    /// +6 over their equal targets. Nature's compound pays w3 doors into
    /// the whole-6s that only a globally different midgame ORDER can
    /// offer — the compound tier lives in midgame order, not merely
    /// midgame depth (sharpens M-2b′ and re-indicts the s24 blocked
    /// zone). §10.7's extraction hope is dead; this test is the
    /// regression pin of that measurement and of the T1-widening (net
    /// −2) plus extraction/heal bookkeeping.
    #[test]
    fn natural_compound_refuted_at_anchored_reach() {
        let g = Graph::new(6);
        let dir = std::path::Path::new("data/compound_specimens");
        let corpus = crate::corpus::load_corpus(&g, &[dir]).expect("compound specimens");
        assert_eq!(corpus.len(), 4, "both mirrored pairs committed");
        let a_side = corpus
            .iter()
            .find(|r| r.name.contains("55088ebb4107"))
            .expect("A side");
        let b_side = corpus
            .iter()
            .find(|r| r.name.contains("d141177d85e1"))
            .expect("B side");
        assert_eq!(allocation_of(&a_side.trace), (145, 3, 0, 0));
        assert_eq!(allocation_of(&b_side.trace), (143, 5, 0, 0));
        let inst = decompose(6, &a_side.trace, 520).expect("decompose");
        let (opt, _, _) = solve_bb(&inst, false, 0);
        assert_eq!(opt, inst.actual, "A side is block-order-optimal");
        let exts = enumerate_extractions(6, &g, &a_side.trace, &inst);
        let c126354 = crate::graph::rank(&[1, 2, 6, 3, 5, 4]) as u32;
        let c123654 = crate::graph::rank(&[1, 2, 3, 6, 5, 4]) as u32;
        let ext = exts
            .iter()
            .find(|e| e.cycle == c126354 && e.entry_depth == 181)
            .expect("the 126354@181 extraction candidate");
        assert_eq!(ext.nperms, 4);
        assert_eq!(
            ext.heal, 6,
            "the w2-entered seam heals only at full re-spell"
        );
        let ei = apply_extraction(6, &g, &inst, ext, 0);
        let prefix = healed_prefix(6, &a_side.string, inst.prefix_chars, ext);
        assert_eq!(prefix.len(), ei.prefix_chars, "heal bookkeeping");
        let src_len = a_side.string.len();
        // extraction-identity: floating the part costs exactly +6
        let id_target = src_len - ei.prefix_chars - ei.intra;
        let m0 = apply_recomp_multi(6, &g, &ei, &[], 10_000);
        let (id_opt, _, _) = solve_bb(&m0, false, 0);
        assert_eq!(id_opt, id_target + 6, "extraction is +6-lossy on this seam");
        let groups = recomp_variants_by_cycle(6, &g, &ei);
        let whole6 = |cid: u32| -> Vec<&RecompMove> {
            groups
                .iter()
                .find(|(c, _)| *c == cid)
                .expect("cycle")
                .1
                .iter()
                .filter(|m| m.arcs.len() == 1 && m.arcs[0].1 == 6)
                .collect()
        };
        let va = whole6(c126354);
        let vb = whole6(c123654);
        assert_eq!((va.len(), vb.len()), (6, 6));
        for a in &va {
            for b in &vb {
                assert_eq!(net_split(a) + net_split(b), -2, "two merges = net -2");
                let intra_m =
                    ei.intra + a.remove.len() + b.remove.len() - a.arcs.len() - b.arcs.len();
                let inc = src_len + 1 - ei.prefix_chars - intra_m;
                let m = apply_recomp_multi(6, &g, &ei, &[a, b], inc);
                let (mopt, _, _) = solve_bb(&m, false, 0);
                assert_eq!(
                    mopt, inc,
                    "an equal-or-better compound completion here would overturn the s38 verdict"
                );
            }
        }
        // the B-entry compound's true optimum is exactly +6 over equal
        // and materializes to a valid 878
        let a = va
            .iter()
            .find(|m| unrank(6, m.arcs[0].0 as usize) == [2, 6, 3, 5, 4, 1])
            .unwrap();
        let b = vb
            .iter()
            .find(|m| unrank(6, m.arcs[0].0 as usize) == [2, 3, 6, 5, 4, 1])
            .unwrap();
        let intra_m = ei.intra + a.remove.len() + b.remove.len() - a.arcs.len() - b.arcs.len();
        let equal_target = src_len - ei.prefix_chars - intra_m;
        let m = apply_recomp_multi(6, &g, &ei, &[a, b], 10_000);
        let (topt, torder, _) = solve_bb(&m, false, 0);
        assert_eq!(topt, equal_target + 6, "the compound prices +6 over equal");
        let s = materialize_from_prefix(6, &g, &prefix, &m, &torder);
        assert_eq!(s.len(), src_len + 6);
        assert!(crate::validate::validate(6, &s).complete);
    }

    /// The loop-count relation (s35) holds on every committed specimen,
    /// with Λ = 29 across the whole n=6 872 shell — heavy doors
    /// substituting at (w−3) loops per door.
    #[test]
    fn loop_relation_holds_on_committed_specimens() {
        let g = Graph::new(6);
        for dir in [
            "data/upstream872_specimens",
            "data/surgery_specimens",
            "data/compound_specimens",
        ] {
            let corpus =
                crate::corpus::load_corpus(&g, &[std::path::Path::new(dir)]).expect("specimens");
            for rec in &corpus {
                let lc = loop_relation(6, &g, &rec.trace);
                assert!(lc.holds, "{}: loop relation must hold", rec.name);
                let lam = lc.l
                    + rec.trace.hist.get(4).copied().unwrap_or(0)
                    + 2 * rec.trace.hist.get(5).copied().unwrap_or(0);
                assert_eq!(lam, 29, "{}: Λ must be 29 on the 872 shell", rec.name);
            }
        }
    }

    /// Committed specimen pins (one per L0 allocation, s27): every
    /// specimen tail at anchor ≥ 585 is block-order-optimal — the s28
    /// mini-sweep found 249/249 optimal; these 8 are the committed
    /// regression pins of that fact.
    #[test]
    fn specimen_tails_block_order_optimal() {
        let g = Graph::new(6);
        let dir = std::path::Path::new("data/upstream872_specimens");
        let corpus = crate::corpus::load_corpus(&g, &[dir]).expect("specimens");
        assert_eq!(corpus.len(), 8, "one specimen per allocation");
        for rec in &corpus {
            let inst = decompose(6, &rec.trace, 585).expect("decompose");
            assert!(inst.blocks.len() <= 30, "{}: unexpectedly wide", rec.name);
            let (opt, _, _) = solve_bb(&inst, false, 0);
            assert_eq!(opt, inst.actual, "{}", rec.name);
        }
    }
}
