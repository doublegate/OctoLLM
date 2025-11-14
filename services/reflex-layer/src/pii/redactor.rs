// PII Redaction Strategies
//
// This module provides various strategies for redacting detected PII.

use crate::pii::types::PIIMatch;
use sha2::{Digest, Sha256};

/// Redaction strategy enum
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RedactionStrategy {
    /// Replace with asterisks: "test@example.com" → "****************"
    Mask,
    /// Replace with SHA-256 hash (first 16 chars): "test@example.com" → "a3f8d2e1b4c5..."
    Hash,
    /// Keep last N characters: "123-45-6789" → "XXX-XX-6789"
    Partial,
    /// Remove entirely: "test@example.com" → ""
    Remove,
    /// Replace with typed token: "test@example.com" → "<EMAIL-TOKEN-123>"
    Token,
}

/// Redact PII from text using the specified strategy
///
/// # Arguments
///
/// * `text` - The original text containing PII
/// * `matches` - Slice of PIIMatch instances indicating what to redact
/// * `strategy` - The redaction strategy to use
///
/// # Returns
///
/// A new string with all PII redacted according to the strategy
///
/// # Examples
///
/// ```
/// use reflex_layer::pii::{redact, RedactionStrategy, PIIMatch, PIIType};
///
/// let text = "Contact: test@example.com";
/// let matches = vec![
///     PIIMatch::new(PIIType::Email, 9, 25, "test@example.com".to_string(), 0.95)
/// ];
///
/// let redacted = redact(text, &matches, RedactionStrategy::Mask);
/// assert_eq!(redacted, "Contact: ****************");
/// ```
pub fn redact(text: &str, matches: &[PIIMatch], strategy: RedactionStrategy) -> String {
    if matches.is_empty() {
        return text.to_string();
    }

    let mut result = text.to_string();

    // Sort matches by position (reverse order for in-place replacement)
    let mut sorted_matches = matches.to_vec();
    sorted_matches.sort_by_key(|m| std::cmp::Reverse(m.start));

    // Apply redaction for each match (from end to start to preserve offsets)
    for pii_match in sorted_matches {
        let replacement = match strategy {
            RedactionStrategy::Mask => mask_replacement(&pii_match),
            RedactionStrategy::Hash => hash_replacement(&pii_match),
            RedactionStrategy::Partial => partial_replacement(&pii_match),
            RedactionStrategy::Remove => String::new(),
            RedactionStrategy::Token => token_replacement(&pii_match),
        };

        result.replace_range(pii_match.start..pii_match.end, &replacement);
    }

    result
}

/// Replace with asterisks
fn mask_replacement(pii_match: &PIIMatch) -> String {
    "*".repeat(pii_match.len())
}

/// Replace with SHA-256 hash (first 16 characters)
fn hash_replacement(pii_match: &PIIMatch) -> String {
    let mut hasher = Sha256::new();
    hasher.update(pii_match.matched_text.as_bytes());
    let hash_result = hasher.finalize();
    format!("{:x}", hash_result)[..16].to_string()
}

/// Keep last 4 characters, replace rest with 'X'
fn partial_replacement(pii_match: &PIIMatch) -> String {
    let text = &pii_match.matched_text;
    let len = text.len();

    if len <= 4 {
        // If text is 4 chars or less, fully mask
        "X".repeat(len)
    } else {
        // Keep last 4 characters
        let prefix_len = len - 4;
        format!("{}{}", "X".repeat(prefix_len), &text[prefix_len..])
    }
}

/// Replace with typed token
fn token_replacement(pii_match: &PIIMatch) -> String {
    format!("<{}-TOKEN-{}>", pii_match.pii_type, pii_match.start)
}

/// Redact with custom partial strategy (specify how many chars to keep)
///
/// # Arguments
///
/// * `text` - The original text containing PII
/// * `matches` - Slice of PIIMatch instances indicating what to redact
/// * `keep_chars` - Number of characters to keep at the end
///
/// # Returns
///
/// A new string with PII partially redacted
pub fn redact_partial_custom(text: &str, matches: &[PIIMatch], keep_chars: usize) -> String {
    if matches.is_empty() {
        return text.to_string();
    }

    let mut result = text.to_string();
    let mut sorted_matches = matches.to_vec();
    sorted_matches.sort_by_key(|m| std::cmp::Reverse(m.start));

    for pii_match in sorted_matches {
        let replacement = if pii_match.len() <= keep_chars {
            "X".repeat(pii_match.len())
        } else {
            let prefix_len = pii_match.len() - keep_chars;
            format!(
                "{}{}",
                "X".repeat(prefix_len),
                &pii_match.matched_text[prefix_len..]
            )
        };

        result.replace_range(pii_match.start..pii_match.end, &replacement);
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pii::types::PIIType;

    fn create_test_match(start: usize, end: usize, text: &str) -> PIIMatch {
        PIIMatch::new(PIIType::Email, start, end, text.to_string(), 0.95)
    }

    #[test]
    fn test_mask_redaction() {
        let text = "Email: test@example.com";
        let matches = vec![create_test_match(7, 23, "test@example.com")];
        let redacted = redact(text, &matches, RedactionStrategy::Mask);
        assert_eq!(redacted, "Email: ****************");
    }

    #[test]
    fn test_partial_redaction() {
        let text = "SSN: 123-45-6789";
        let matches = vec![create_test_match(5, 16, "123-45-6789")];
        let redacted = redact(text, &matches, RedactionStrategy::Partial);
        assert_eq!(redacted, "SSN: XXXXXXX6789");
    }

    #[test]
    fn test_remove_redaction() {
        let text = "Email: test@example.com";
        let matches = vec![create_test_match(7, 23, "test@example.com")];
        let redacted = redact(text, &matches, RedactionStrategy::Remove);
        assert_eq!(redacted, "Email: ");
    }

    #[test]
    fn test_token_redaction() {
        let text = "Email: test@example.com";
        let matches = vec![create_test_match(7, 23, "test@example.com")];
        let redacted = redact(text, &matches, RedactionStrategy::Token);
        assert_eq!(redacted, "Email: <Email-TOKEN-7>");
    }

    #[test]
    fn test_hash_redaction() {
        let text = "Email: test@example.com";
        let matches = vec![create_test_match(7, 23, "test@example.com")];
        let redacted = redact(text, &matches, RedactionStrategy::Hash);

        // Hash should be 16 characters
        let hash_part = &redacted[7..];
        assert_eq!(hash_part.len(), 16);
        assert!(hash_part.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_multiple_matches() {
        let text = "Email: test@example.com, Phone: 555-1234";
        let matches = vec![
            create_test_match(7, 23, "test@example.com"),
            create_test_match(32, 40, "555-1234"),
        ];
        let redacted = redact(text, &matches, RedactionStrategy::Mask);
        assert_eq!(redacted, "Email: ****************, Phone: ********");
    }

    #[test]
    fn test_empty_matches() {
        let text = "No PII here";
        let matches = vec![];
        let redacted = redact(text, &matches, RedactionStrategy::Mask);
        assert_eq!(redacted, text);
    }

    #[test]
    fn test_overlapping_matches() {
        // Note: Real detector shouldn't produce overlapping matches,
        // but test the behavior anyway
        let text = "test@example.com";
        let matches = vec![
            create_test_match(0, 16, "test@example.com"),
            create_test_match(5, 12, "example"),
        ];

        // Should handle gracefully (reverse order ensures no offset issues)
        let redacted = redact(text, &matches, RedactionStrategy::Mask);
        assert_eq!(redacted.len(), 16);
    }

    #[test]
    fn test_partial_custom() {
        let text = "SSN: 123-45-6789";
        let matches = vec![create_test_match(5, 16, "123-45-6789")];

        // Keep last 6 characters
        let redacted = redact_partial_custom(text, &matches, 6);
        assert_eq!(redacted, "SSN: XXXXX5-6789");

        // Keep last 2 characters
        let redacted = redact_partial_custom(text, &matches, 2);
        assert_eq!(redacted, "SSN: XXXXXXXXX89");
    }

    #[test]
    fn test_mask_replacement_direct() {
        let pii_match = create_test_match(0, 10, "test@email");
        let result = mask_replacement(&pii_match);
        assert_eq!(result, "**********");
    }

    #[test]
    fn test_partial_replacement_short_text() {
        let pii_match = create_test_match(0, 3, "abc");
        let result = partial_replacement(&pii_match);
        assert_eq!(result, "XXX"); // Fully masked if <= 4 chars
    }

    #[test]
    fn test_token_replacement_direct() {
        let pii_match = PIIMatch::new(PIIType::SSN, 10, 21, "123-45-6789".to_string(), 0.95);
        let result = token_replacement(&pii_match);
        assert_eq!(result, "<SSN-TOKEN-10>");
    }
}
