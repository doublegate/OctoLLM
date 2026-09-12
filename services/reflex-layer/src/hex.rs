//! Lowercase hex encoding for fixed-size digests.
//!
//! `sha2` 0.11 returns `hybrid_array::Array` rather than `generic_array::GenericArray`,
//! and `Array` deliberately does not implement `LowerHex`, so `format!("{:x}", digest)`
//! no longer compiles. This helper replaces it without pulling in another dependency
//! and without allocating per byte, which matters on the cache-key path (<10ms budget).

/// Encode bytes as a lowercase hex string.
///
/// # Examples
///
/// ```
/// use reflex_layer::hex::encode_lower;
///
/// assert_eq!(encode_lower(&[0x00, 0x0f, 0xa5, 0xff]), "000fa5ff");
/// assert_eq!(encode_lower(&[]), "");
/// ```
#[must_use]
pub fn encode_lower(bytes: &[u8]) -> String {
    const DIGITS: [char; 16] = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f',
    ];

    // Pushing `char`s keeps this infallible: there is no UTF-8 validation step to
    // unwrap, and one allocation covers the whole output.
    let mut out = String::with_capacity(bytes.len() * 2);
    for &b in bytes {
        out.push(DIGITS[usize::from(b >> 4)]);
        out.push(DIGITS[usize::from(b & 0x0f)]);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::encode_lower;
    use sha2::{Digest, Sha256};

    #[test]
    fn encodes_empty_slice() {
        assert_eq!(encode_lower(&[]), "");
    }

    #[test]
    fn pads_each_byte_to_two_digits() {
        assert_eq!(encode_lower(&[0x00]), "00");
        assert_eq!(encode_lower(&[0x05]), "05");
        assert_eq!(encode_lower(&[0x0f]), "0f");
        assert_eq!(encode_lower(&[0xff]), "ff");
    }

    #[test]
    fn encodes_full_byte_range() {
        let all: Vec<u8> = (0u8..=255).collect();
        let encoded = encode_lower(&all);
        assert_eq!(encoded.len(), 512);
        assert_eq!(&encoded[..4], "0001");
        assert_eq!(&encoded[508..], "feff");
        assert!(encoded
            .chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_uppercase()));
    }

    /// Pins the exact output that `format!("{:x}", digest)` produced under sha2 0.10,
    /// so the 0.11 migration is verified against a known vector rather than itself.
    #[test]
    fn matches_known_sha256_vector() {
        let mut hasher = Sha256::new();
        hasher.update(b"abc");
        assert_eq!(
            encode_lower(&hasher.finalize()),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }
}
