//! Small fixed-size bitset over `Box<[u64]>`.
//!
//! Used as the "visited permutations" set during search. The capacity is
//! fixed at construction (`n!` bits in practice, so at most `8! = 40320`
//! bits ⇒ 630 words). Derives `Hash`/`Eq` so beam-search states can be
//! deduplicated by `(current permutation, visited set)`.

/// Fixed-capacity bitset backed by a boxed slice of `u64` words.
///
/// Bits beyond the requested capacity exist as padding in the last word
/// but are never set by [`BitSet::set`], so equality and hashing over the
/// raw words are well-defined for same-capacity sets.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct BitSet {
    words: Box<[u64]>,
}

impl BitSet {
    /// Create an empty bitset with capacity for `nbits` bits (all clear).
    pub fn new(nbits: usize) -> Self {
        BitSet {
            words: vec![0u64; nbits.div_ceil(64)].into_boxed_slice(),
        }
    }

    /// Set bit `i` (must be within capacity).
    #[inline]
    pub fn set(&mut self, i: usize) {
        self.words[i >> 6] |= 1u64 << (i & 63);
    }

    /// Return whether bit `i` is set (must be within capacity).
    #[inline]
    pub fn get(&self, i: usize) -> bool {
        (self.words[i >> 6] >> (i & 63)) & 1 != 0
    }

    /// Number of set bits.
    pub fn popcount(&self) -> u32 {
        self.words.iter().map(|w| w.count_ones()).sum()
    }

    /// The backing words (padding bits beyond the capacity are clear).
    pub fn words(&self) -> &[u64] {
        &self.words
    }

    /// Index of the lowest clear bit strictly below `limit`, if any.
    ///
    /// Used to find the lowest-ranked unvisited permutation for the
    /// weight-`n` fallback jump. `limit` masks off the padding bits in
    /// the last word (which are always clear).
    pub fn first_clear(&self, limit: usize) -> Option<usize> {
        for (wi, &w) in self.words.iter().enumerate() {
            if w != u64::MAX {
                let i = (wi << 6) + (!w).trailing_zeros() as usize;
                // Bits below `i` in this word are set and all earlier
                // words are full, so `i` is the global lowest clear bit.
                return if i < limit { Some(i) } else { None };
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn set_get_popcount() {
        let mut b = BitSet::new(130);
        assert_eq!(b.popcount(), 0);
        for i in [0usize, 63, 64, 127, 129] {
            assert!(!b.get(i));
            b.set(i);
            assert!(b.get(i));
        }
        assert_eq!(b.popcount(), 5);
        // Setting an already-set bit is idempotent.
        b.set(63);
        assert_eq!(b.popcount(), 5);
    }

    #[test]
    fn first_clear_scans_words() {
        let mut b = BitSet::new(130);
        assert_eq!(b.first_clear(130), Some(0));
        for i in 0..70 {
            b.set(i);
        }
        assert_eq!(b.first_clear(130), Some(70));
        for i in 70..130 {
            b.set(i);
        }
        assert_eq!(b.first_clear(130), None);
    }

    #[test]
    fn eq_and_hash() {
        let mut a = BitSet::new(200);
        let mut b = BitSet::new(200);
        a.set(5);
        b.set(5);
        assert_eq!(a, b);
        let mut s = HashSet::new();
        s.insert(a.clone());
        assert!(s.contains(&b));
        b.set(199);
        assert_ne!(a, b);
        assert!(!s.contains(&b));
    }
}
