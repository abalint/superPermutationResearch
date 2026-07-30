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
    let mut s: String = source[..inst.prefix_chars].to_string();
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
