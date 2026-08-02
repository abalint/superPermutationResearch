//! Nested Rollout Policy Adaptation over the sojourn move grammar
//! (TRACKB-DESIGN §4 step 4a; built s25).
//!
//! The s24 verdict: the ≤872 tree through the records-class openings is
//! width-truncated because every scorer misranks record-style states in
//! the midgame (levels ~60–450), and no bound, cap, width, jitter, or α
//! fixes it — the failure is a *ranking* problem, i.e. a policy
//! problem. NRPA is the technique of record for exactly this shape
//! (Rosin 2011, Morpion Solitaire): a softmax policy over move
//! features, rollouts sampled from it, and at each nesting level the
//! policy adapted toward the best rollout seen so far.
//!
//! Division of labour per the design: the policy owns the contested
//! opening/midgame — rollouts play sojourn-grammar moves
//! ([`Grammar::children`]: ride / skip / door, class caps + split
//! profile enforced, so completion is HELD in-class through the levels
//! where the s24 874s escaped) — and from `switch_depth` visited perms
//! the walk is finished by the capped beam (s24: a fast, sound
//! completion oracle from depth ≥ ~450). Dead rollouts (grammar
//! dead-end, or the capped tail proving no completion ≤ `max_len`)
//! score `u32::MAX` and are never adapted toward.
//!
//! Policy representation: a move contributes three feature codes —
//! move species, door context (weight, exit-part length, target-cycle
//! residual/parts), and exact identity `(cur, target)` — and its logit
//! is the sum of their weights. The species/context codes generalize
//! across states; the identity code lets the nesting memorize a
//! specific line (the classic NRPA behaviour). Adaptation is the
//! standard replay: +α on the chosen move's codes, −α·softmax on every
//! legal move's codes, walking the best sequence through the grammar.

use std::collections::HashMap;
use std::time::Instant;

use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};

use crate::beam::{beam_search_multi_seeded, beam_search_multi_seeded_capped, Scorer};
use crate::endgame::spell_path;
use crate::graph::Graph;
use crate::sojourn::{ClassCaps, Grammar, MoveKind, SojournMove, SplitProfile, State};

/// NRPA configuration.
pub struct NrpaCfg<'g, 'm> {
    pub g: &'g Graph,
    pub caps: ClassCaps,
    pub profile: Option<SplitProfile>,
    /// Restrict weight-3/4/5 doors to untouched cycles (see
    /// [`Grammar::fresh_doors`]; corpus-calibrated, off by default).
    pub fresh_doors: bool,
    /// Nesting depth (1 = adapt over plain rollouts; 2–3 typical).
    pub level: u32,
    /// Iterations per nesting level (`iters^level` rollouts total).
    pub iters: u32,
    /// Adaptation step size (Rosin's α; 1.0 is the standard choice).
    pub adapt_alpha: f64,
    /// RNG seed; the whole run is deterministic given it.
    pub seed: u64,
    /// Visited-perm count at which the rollout hands the walk to the
    /// beam tail (clamped to n!; a rollout completing in-grammar before
    /// the switch scores its own length).
    pub switch_depth: usize,
    /// Beam width of the tail completion.
    pub tail_width: usize,
    /// Admissible length cap for the tail beam (0 = uncapped; capped
    /// tails can die, scoring the rollout dead — spend the width only
    /// on lines that can still beat the cap).
    pub max_len: u32,
    /// Tail beam scorer (residual bound is the best completer, s23;
    /// composed residual+model was the s24 winner).
    pub tail_scorer: Scorer<'m>,
    /// Waste prior β on the softmax logits: every move's logit gets
    /// `−β · waste(move)` added (ride 0, skip k → k−1, door w → w−1),
    /// so the untrained policy already favours cheap moves instead of
    /// sampling uniformly over move species. 0 = classic NRPA (uniform
    /// start). The prior is a fixed additive term — adaptation learns
    /// weights on top of it and can override it anywhere.
    pub prior: f64,
    /// On an in-grammar dead-end, hand the partial prefix to the beam
    /// tail instead of scoring the rollout dead. The tail search is
    /// unconstrained (full graph, fallback edges), so every rollout
    /// completes and returns a graded score — without this, a class
    /// too tight for random play (n=6 records: rollouts die within a
    /// few sojourns) gives the adaptation zero gradient to start from.
    /// The policy prefix itself stays in-class; only the tail escapes.
    pub early_tail: bool,
    /// Warm-start sequences (move-target lists, root excluded): before
    /// the search, the root policy is adapted toward each sequence
    /// `warm_reps` times. The Track C §5 "NRPA policy initialization"
    /// deployment point — a known record's first-visit path is a legal
    /// in-grammar move sequence (T0), so warm-starting from it puts the
    /// rollout distribution near record-shaped play from iteration 1,
    /// which the s25 cold-start runs showed the raw length gradient
    /// cannot reach on its own (rollouts plateau at depth ~85 of 450).
    pub warm_start: Vec<Vec<u32>>,
    /// Adapt passes per warm-start sequence.
    pub warm_reps: u32,
    /// Collect every distinct completed walk of length ≤ this (0 =
    /// off). The M3 gate needs walks *distinct from all known records*
    /// at ≤ 872 — the single best is usually the memorized seed line,
    /// so the interesting objects are the whole collection.
    pub collect_max: u32,
    /// Print top-level iteration progress lines.
    pub verbose: bool,
}

/// Outcome of one NRPA run.
pub struct NrpaResult {
    /// Best complete length found (`None` if every rollout died).
    pub best_len: Option<u32>,
    /// The best walk's string (validated by the caller before belief).
    pub string: Option<String>,
    /// First-visit rank path of the best walk (starts with rank 0).
    pub path: Vec<u32>,
    /// Rollouts played.
    pub rollouts: u64,
    /// Rollouts that died (grammar dead-end or capped tail death).
    pub dead: u64,
    /// Of the dead rollouts, how many died in-grammar before the
    /// switch depth (the rest died in the capped tail).
    pub dead_in_grammar: u64,
    /// Distribution of in-grammar termination depths (visited perms at
    /// tail hand-off or in-grammar death): (min, mean, max). Watching
    /// the mean climb toward `switch_depth` is the cheapest view of the
    /// policy actually learning to survive in-class.
    pub depth_min: u32,
    pub depth_mean: f64,
    pub depth_max: u32,
    /// Distinct completed strings of length ≤ `collect_max`, sorted by
    /// (length, string); empty when collection is off.
    pub collected: Vec<String>,
}

/// Softmax policy: feature-code -> weight, absent = 0.
#[derive(Clone, Default)]
struct Policy {
    w: HashMap<u64, f64>,
}

impl Policy {
    fn logit(&self, codes: &[u64; 3]) -> f64 {
        codes
            .iter()
            .map(|c| self.w.get(c).copied().unwrap_or(0.0))
            .sum()
    }
}

/// Deterministic 64-bit mixing for feature codes (splitmix64).
#[inline]
fn mix(mut z: u64) -> u64 {
    z = z.wrapping_add(0x9e3779b97f4a7c15);
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
    z ^ (z >> 31)
}

/// The three feature codes of a move out of `st` (see module docs).
fn move_codes(g: &Graph, st: &State, mv: &SojournMove) -> [u64; 3] {
    let species = match mv.kind {
        MoveKind::Ride => 1,
        MoveKind::Skip(k) => (2 << 8) | k as u64,
        MoveKind::Door(w) => (3 << 8) | w as u64,
    };
    let ctx = match mv.kind {
        MoveKind::Door(w) => {
            // door context: weight, closing part length, target-cycle
            // residual count and completed-part count before entry
            let tc = g.cycle_id[mv.target as usize] as usize;
            let rem = st.cyc.cycle_rem[tc] as u64;
            let tparts = st.parts[tc] as u64; // 18 bits (6 parts x 3)
            (4 << 44) | (w as u64) << 36 | (st.cur_part as u64) << 28 | rem << 20 | tparts
        }
        // rides/skips carry the current part length as context
        _ => (5 << 44) | species << 8 | st.cur_part as u64,
    };
    let ident = (6 << 44) | (st.cyc.cur as u64) << 20 | mv.target as u64;
    [mix(species), mix(ctx), mix(ident)]
}

/// Priced waste of a move (characters beyond the 1-per-perm baseline).
fn move_waste(mv: &SojournMove) -> f64 {
    match mv.kind {
        MoveKind::Ride => 0.0,
        MoveKind::Skip(k) => (k - 1) as f64,
        MoveKind::Door(w) => (w - 1) as f64,
    }
}

/// Softmax probabilities of the given logits (max-shifted).
fn softmax(logits: &[f64]) -> Vec<f64> {
    let m = logits.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let exps: Vec<f64> = logits.iter().map(|&l| (l - m).exp()).collect();
    let z: f64 = exps.iter().sum();
    exps.into_iter().map(|e| e / z).collect()
}

struct Ctx<'a, 'g, 'm> {
    cfg: &'a NrpaCfg<'g, 'm>,
    grammar: Grammar<'g>,
    rng: StdRng,
    switch: usize,
    rollouts: u64,
    dead: u64,
    dead_in_grammar: u64,
    depth_min: u32,
    depth_sum: u64,
    depth_max: u32,
    /// Best complete walk ever seen: (length, full first-visit path).
    global_best: Option<(u32, Vec<u32>)>,
    /// Distinct completed strings of length ≤ `cfg.collect_max`.
    collected: std::collections::HashSet<String>,
    t0: Instant,
}

/// One rollout's outcome: score (`u32::MAX` = dead) and the
/// policy-played move targets (excluding the root), the adaptable part.
struct Rollout {
    score: u32,
    seq: Vec<u32>,
}

impl Ctx<'_, '_, '_> {
    fn rollout(&mut self, policy: &Policy) -> Rollout {
        let g = self.cfg.g;
        self.rollouts += 1;
        let mut st = self.grammar.root(false);
        let mut seq: Vec<u32> = Vec::with_capacity(self.switch);
        loop {
            let visited = g.nfact - st.cyc.r as usize;
            if visited == g.nfact {
                // completed in-grammar before the switch
                self.note_depth(visited);
                let score = st.cyc.len;
                if self.cfg.max_len > 0 && score > self.cfg.max_len {
                    self.dead += 1;
                    return Rollout {
                        score: u32::MAX,
                        seq,
                    };
                }
                self.record_best(score, &seq);
                return Rollout { score, seq };
            }
            if visited >= self.switch {
                self.note_depth(visited);
                return self.tail(seq);
            }
            let kids = self.grammar.children(&st);
            if kids.is_empty() {
                self.note_depth(visited);
                if self.cfg.early_tail && !seq.is_empty() {
                    return self.tail(seq);
                }
                self.dead += 1;
                self.dead_in_grammar += 1;
                return Rollout {
                    score: u32::MAX,
                    seq,
                };
            }
            let logits: Vec<f64> = kids
                .iter()
                .map(|(mv, _)| {
                    policy.logit(&move_codes(g, &st, mv)) - self.cfg.prior * move_waste(mv)
                })
                .collect();
            let probs = softmax(&logits);
            let mut u: f64 = self.rng.gen();
            let mut idx = probs.len() - 1;
            for (i, &p) in probs.iter().enumerate() {
                if u < p {
                    idx = i;
                    break;
                }
                u -= p;
            }
            let (mv, child) = kids.into_iter().nth(idx).expect("sampled index in range");
            seq.push(mv.target);
            st = child;
        }
    }

    /// Finish a policy prefix with the beam tail; score it and fold the
    /// completion into the global best.
    fn tail(&mut self, seq: Vec<u32>) -> Rollout {
        let mut seed = Vec::with_capacity(seq.len() + 1);
        seed.push(0u32);
        seed.extend_from_slice(&seq);
        let seeds = [seed];
        let cfg = self.cfg;
        let result = if cfg.max_len > 0 {
            beam_search_multi_seeded_capped(
                cfg.g,
                cfg.tail_width,
                cfg.tail_scorer,
                None,
                &seeds,
                None,
                cfg.max_len,
            )
        } else {
            Some(beam_search_multi_seeded(
                cfg.g,
                cfg.tail_width,
                cfg.tail_scorer,
                None,
                &seeds,
                None,
            ))
        };
        match result {
            Some(b) => {
                let score = b.len as u32;
                self.record_best_path(score, b.path);
                Rollout { score, seq }
            }
            None => {
                self.dead += 1;
                Rollout {
                    score: u32::MAX,
                    seq,
                }
            }
        }
    }

    fn note_depth(&mut self, visited: usize) {
        let d = visited as u32;
        self.depth_min = self.depth_min.min(d);
        self.depth_max = self.depth_max.max(d);
        self.depth_sum += d as u64;
    }

    fn record_best(&mut self, score: u32, seq: &[u32]) {
        let mut path = Vec::with_capacity(seq.len() + 1);
        path.push(0u32);
        path.extend_from_slice(seq);
        self.record_best_path(score, path);
    }

    fn record_best_path(&mut self, score: u32, path: Vec<u32>) {
        if self.cfg.collect_max > 0 && score <= self.cfg.collect_max {
            let s = spell_path(self.cfg.g, &path);
            if self.collected.insert(s) && self.cfg.verbose {
                println!(
                    "  collected #{}: length {score} (rollout {})",
                    self.collected.len(),
                    self.rollouts
                );
            }
        }
        if self.global_best.as_ref().is_none_or(|(s, _)| score < *s) {
            if self.cfg.verbose {
                println!(
                    "  new best {score} (rollout {}, {:.1}s)",
                    self.rollouts,
                    self.t0.elapsed().as_secs_f64()
                );
            }
            self.global_best = Some((score, path));
        }
    }

    /// Standard NRPA adaptation: replay `seq` through the grammar with
    /// the adapting policy, +α on the chosen codes, −α·p on every legal
    /// move's codes at each step. Returns how many steps were applied
    /// (a replay stops early if a target is not a legal grammar move —
    /// cannot happen for sequences the rollouts played, but a
    /// warm-start sequence from an external record is only trusted as
    /// far as it replays).
    fn adapt(&mut self, policy: &mut Policy, seq: &[u32]) -> usize {
        let g = self.cfg.g;
        let alpha = self.cfg.adapt_alpha;
        let mut st = self.grammar.root(false);
        for (done, &target) in seq.iter().enumerate() {
            let kids = self.grammar.children(&st);
            let Some(idx) = kids.iter().position(|(mv, _)| mv.target == target) else {
                return done;
            };
            let codesv: Vec<[u64; 3]> = kids.iter().map(|(mv, _)| move_codes(g, &st, mv)).collect();
            // the adaptation gradient must use the same distribution the
            // rollouts sample from — prior included
            let logits: Vec<f64> = codesv
                .iter()
                .zip(&kids)
                .map(|(c, (mv, _))| policy.logit(c) - self.cfg.prior * move_waste(mv))
                .collect();
            let probs = softmax(&logits);
            for (codes, p) in codesv.iter().zip(&probs) {
                for &c in codes {
                    *policy.w.entry(c).or_insert(0.0) -= alpha * p;
                }
            }
            for &c in &codesv[idx] {
                *policy.w.entry(c).or_insert(0.0) += alpha;
            }
            st = kids.into_iter().nth(idx).expect("index from position").1;
        }
        seq.len()
    }

    fn nrpa(&mut self, level: u32, policy: &mut Policy) -> Rollout {
        if level == 0 {
            return self.rollout(policy);
        }
        let mut best = Rollout {
            score: u32::MAX,
            seq: Vec::new(),
        };
        for i in 0..self.cfg.iters {
            let mut child = policy.clone();
            let r = self.nrpa(level - 1, &mut child);
            if r.score <= best.score && r.score != u32::MAX {
                best = r;
            }
            if best.score != u32::MAX {
                let seq = std::mem::take(&mut best.seq);
                self.adapt(policy, &seq);
                best.seq = seq;
            }
            if self.cfg.verbose && level == self.cfg.level {
                println!(
                    "level {level} iter {}/{}: best {} ({} rollouts, {} dead, {:.1}s)",
                    i + 1,
                    self.cfg.iters,
                    match self.global_best {
                        Some((s, _)) => s.to_string(),
                        None => "-".into(),
                    },
                    self.rollouts,
                    self.dead,
                    self.t0.elapsed().as_secs_f64()
                );
            }
        }
        best
    }
}

/// Run NRPA; deterministic given the config.
pub fn nrpa_search(cfg: &NrpaCfg) -> NrpaResult {
    let mut grammar = Grammar::new(cfg.g, cfg.caps, cfg.profile.clone());
    grammar.fresh_doors = cfg.fresh_doors;
    let mut ctx = Ctx {
        grammar,
        rng: StdRng::seed_from_u64(cfg.seed),
        switch: cfg.switch_depth.min(cfg.g.nfact),
        rollouts: 0,
        dead: 0,
        dead_in_grammar: 0,
        depth_min: u32::MAX,
        depth_sum: 0,
        depth_max: 0,
        global_best: None,
        collected: std::collections::HashSet::new(),
        t0: Instant::now(),
        cfg,
    };
    let mut policy = Policy::default();
    for rep in 0..cfg.warm_reps {
        for (i, seq) in cfg.warm_start.iter().enumerate() {
            let done = ctx.adapt(&mut policy, seq);
            if cfg.verbose && rep == 0 {
                println!(
                    "warm-start seq {}: {} of {} moves replay in-grammar",
                    i + 1,
                    done,
                    seq.len()
                );
            }
        }
    }
    ctx.nrpa(cfg.level, &mut policy);
    let (best_len, path) = match ctx.global_best {
        Some((s, p)) => (Some(s), p),
        None => (None, Vec::new()),
    };
    let string = best_len.map(|_| spell_path(cfg.g, &path));
    NrpaResult {
        best_len,
        string,
        path,
        rollouts: ctx.rollouts,
        dead: ctx.dead,
        dead_in_grammar: ctx.dead_in_grammar,
        depth_min: if ctx.depth_min == u32::MAX {
            0
        } else {
            ctx.depth_min
        },
        depth_mean: if ctx.rollouts > 0 {
            ctx.depth_sum as f64 / ctx.rollouts as f64
        } else {
            0.0
        },
        depth_max: ctx.depth_max,
        collected: {
            let mut v: Vec<String> = ctx.collected.into_iter().collect();
            v.sort_by_key(|s| (s.len(), s.clone()));
            v
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::beam::{Bound, Scorer};
    use crate::validate::validate;

    fn generous_caps_n4() -> ClassCaps {
        ClassCaps {
            s: 12,
            d3: 6,
            d4: 0,
            d5: 0,
            ip: 4,
        }
    }

    #[test]
    fn n4_nrpa_finds_optimum() {
        let g = Graph::new(4);
        let cfg = NrpaCfg {
            g: &g,
            caps: generous_caps_n4(),
            profile: None,
            fresh_doors: false,
            level: 2,
            iters: 10,
            adapt_alpha: 1.0,
            seed: 0,
            switch_depth: 10,
            tail_width: 256,
            max_len: 0,
            tail_scorer: Scorer::Bound(Bound::Residual),
            prior: 0.0,
            early_tail: false,
            warm_start: Vec::new(),
            warm_reps: 0,
            collect_max: 0,
            verbose: false,
        };
        let r = nrpa_search(&cfg);
        assert_eq!(r.best_len, Some(33));
        let s = r.string.expect("best string");
        let v = validate(4, &s);
        assert!(v.complete);
        assert_eq!(v.length, 33);
    }

    #[test]
    fn nrpa_is_deterministic() {
        let g = Graph::new(4);
        let mk = || NrpaCfg {
            g: &g,
            caps: generous_caps_n4(),
            profile: None,
            fresh_doors: false,
            level: 1,
            iters: 6,
            adapt_alpha: 1.0,
            seed: 42,
            switch_depth: 10,
            tail_width: 128,
            max_len: 0,
            tail_scorer: Scorer::Bound(Bound::Arc),
            prior: 0.0,
            early_tail: false,
            warm_start: Vec::new(),
            warm_reps: 0,
            collect_max: 0,
            verbose: false,
        };
        let a = nrpa_search(&mk());
        let b = nrpa_search(&mk());
        assert_eq!(a.best_len, b.best_len);
        assert_eq!(a.path, b.path);
        assert_eq!(a.rollouts, b.rollouts);
    }

    #[test]
    fn n5_nrpa_control_finds_153() {
        // C2-style control: NRPA with the waste prior re-finds the
        // proven n=5 optimum (measured s25: 153 within 100 rollouts;
        // without the prior the same budget plateaus at ~193).
        let g = Graph::new(5);
        let cfg = NrpaCfg {
            g: &g,
            caps: ClassCaps {
                s: 60,
                d3: 10,
                d4: 0,
                d5: 0,
                ip: 10,
            },
            profile: None,
            fresh_doors: false,
            level: 2,
            iters: 10,
            adapt_alpha: 1.0,
            seed: 0,
            switch_depth: 40,
            tail_width: 1000,
            max_len: 0,
            tail_scorer: Scorer::Bound(Bound::Residual),
            prior: 1.0,
            early_tail: false,
            warm_start: Vec::new(),
            warm_reps: 0,
            collect_max: 0,
            verbose: false,
        };
        let r = nrpa_search(&cfg);
        assert_eq!(r.best_len, Some(153));
        let v = validate(5, &r.string.expect("best string"));
        assert!(v.complete);
        assert_eq!(v.length, 153);
    }

    #[test]
    fn early_tail_gives_graded_scores_in_tight_class() {
        // n=6 records class: without early-tail every random rollout
        // dies in-grammar (measured s25); with it every rollout must
        // complete and validate. Tiny budget — this is a wiring test,
        // not a quality test.
        let g = Graph::new(6);
        let cfg = NrpaCfg {
            g: &g,
            caps: ClassCaps {
                s: 145,
                d3: 3,
                d4: 0,
                d5: 0,
                ip: 0,
            },
            profile: Some(SplitProfile::records_n6()),
            fresh_doors: false,
            level: 1,
            iters: 2,
            adapt_alpha: 1.0,
            seed: 0,
            switch_depth: 450,
            tail_width: 100,
            max_len: 0,
            tail_scorer: Scorer::Bound(Bound::Residual),
            prior: 3.0,
            early_tail: true,
            warm_start: Vec::new(),
            warm_reps: 0,
            collect_max: 0,
            verbose: false,
        };
        let r = nrpa_search(&cfg);
        assert_eq!(r.dead, 0);
        assert!(r.depth_max > 0);
        let len = r.best_len.expect("early-tail always completes");
        let v = validate(6, &r.string.expect("best string"));
        assert!(v.complete);
        assert_eq!(v.length as u32, len);
    }

    #[test]
    fn capped_nrpa_reports_dead_rollouts_honestly() {
        // A cap below the proven optimum (33) must kill every rollout.
        let g = Graph::new(4);
        let cfg = NrpaCfg {
            g: &g,
            caps: generous_caps_n4(),
            profile: None,
            fresh_doors: false,
            level: 1,
            iters: 4,
            adapt_alpha: 1.0,
            seed: 0,
            switch_depth: 10,
            tail_width: 256,
            max_len: 32,
            tail_scorer: Scorer::Bound(Bound::Residual),
            prior: 0.0,
            early_tail: false,
            warm_start: Vec::new(),
            warm_reps: 0,
            collect_max: 0,
            verbose: false,
        };
        let r = nrpa_search(&cfg);
        assert_eq!(r.best_len, None);
        assert!(r.string.is_none());
        assert_eq!(r.dead, r.rollouts);
    }
}
