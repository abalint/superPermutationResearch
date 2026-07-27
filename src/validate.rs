//! Sliding-window superpermutation validator.
//!
//! Slides a window of width `n` across the candidate string; every
//! window whose characters are exactly the symbols `1..=n` (each once)
//! is a covered permutation. The string is a complete superpermutation
//! iff all `n!` permutations are covered.

use crate::graph::{factorial, rank};

/// Outcome of validating a candidate string for a given `n`.
pub struct Validation {
    /// Number of symbols the string was checked against.
    pub n: usize,
    /// Length of the candidate string in characters.
    pub length: usize,
    /// Distinct permutations of `{1..n}` covered as contiguous windows.
    pub distinct: usize,
    /// Total permutations required (`n!`).
    pub total: usize,
    /// Whether all `n!` permutations are covered.
    pub complete: bool,
}

/// Validate `s` as a candidate superpermutation on `n` symbols
/// (rendered as ASCII digits `'1'..='8'`).
///
/// Characters outside `'1'..='8'` (or digits above `n`) never form a
/// valid window; they simply contribute no coverage.
pub fn validate(n: usize, s: &str) -> Validation {
    assert!((3..=8).contains(&n), "n must be in 3..=8");
    let total = factorial(n);
    // Map chars to symbol values, 0 for anything that is not a digit in
    // range (0 can never be part of a valid window).
    let vals: Vec<u8> = s
        .chars()
        .map(|c| match c {
            '1'..='8' => c as u8 - b'0',
            _ => 0,
        })
        .map(|v| if (v as usize) <= n { v } else { 0 })
        .collect();

    let mut seen = vec![false; total];
    let mut distinct = 0usize;
    if vals.len() >= n {
        for win in vals.windows(n) {
            // A window is a permutation iff the value bitmask is exactly
            // {1..n}; duplicates or zeros leave a bit missing.
            let mut mask = 0u16;
            for &v in win {
                mask |= 1u16 << v;
            }
            if mask == ((1u16 << n) - 1) << 1 {
                let r = rank(win);
                if !seen[r] {
                    seen[r] = true;
                    distinct += 1;
                }
            }
        }
    }

    Validation {
        n,
        length: vals.len(),
        distinct,
        total,
        complete: distinct == total,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_n3_superperm_validates() {
        let v = validate(3, "123121321");
        assert_eq!(v.length, 9);
        assert_eq!(v.distinct, 6);
        assert!(v.complete);
    }

    #[test]
    fn incomplete_string_rejected() {
        let v = validate(3, "123121");
        assert_eq!(v.distinct, 3); // 123, 231, 312
        assert!(!v.complete);
    }

    #[test]
    fn garbage_and_duplicates_do_not_count() {
        let v = validate(3, "12x321133");
        assert!(v.distinct <= 2);
        assert!(!v.complete);
        // Digits above n are not symbols.
        let v = validate(3, "123412341234");
        assert_eq!(v.distinct, 1); // only 123 windows are valid
    }
}
