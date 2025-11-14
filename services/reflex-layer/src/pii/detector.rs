// PII Detector Implementation
//
// This module implements the main PII detection algorithm.

use std::collections::HashMap;

use crate::pii::patterns::{get_pattern_metadata, get_patterns};
use crate::pii::types::{PIIConfig, PIIMatch, PIIType};
use crate::pii::validator::{validate_email, validate_luhn, validate_phone, validate_ssn};

/// Main PII detector that finds PII in text
pub struct PIIDetector {
    /// Configuration for detection
    config: PIIConfig,
    /// Pattern metadata for severity and validation requirements
    metadata: HashMap<PIIType, crate::pii::patterns::PatternMetadata>,
}

impl PIIDetector {
    /// Create a new PII detector with the given configuration
    ///
    /// # Arguments
    ///
    /// * `config` - Configuration specifying pattern set and validation options
    ///
    /// # Examples
    ///
    /// ```
    /// use reflex_layer::pii::{PIIDetector, PIIConfig, PatternSet};
    ///
    /// let config = PIIConfig {
    ///     pattern_set: PatternSet::Standard,
    ///     enable_validation: true,
    ///     enable_context: false,
    /// };
    /// let detector = PIIDetector::new(config);
    /// ```
    pub fn new(config: PIIConfig) -> Self {
        let metadata = get_pattern_metadata();
        Self { config, metadata }
    }

    /// Detect all PII in the given text
    ///
    /// # Arguments
    ///
    /// * `text` - The text to scan for PII
    ///
    /// # Returns
    ///
    /// A vector of PIIMatch instances, one for each detected PII occurrence
    ///
    /// # Examples
    ///
    /// ```
    /// use reflex_layer::pii::{PIIDetector, PIIConfig};
    ///
    /// let detector = PIIDetector::new(PIIConfig::default());
    /// let text = "Contact me at john@example.com or 555-123-4567";
    /// let matches = detector.detect(text);
    ///
    /// assert!(matches.len() > 0);
    /// ```
    pub fn detect(&self, text: &str) -> Vec<PIIMatch> {
        let mut matches = Vec::new();
        let patterns = get_patterns(&self.config.pattern_set);

        // Iterate through all enabled patterns
        for (pii_type, pattern) in &patterns {
            // Find all matches for this pattern
            for capture in pattern.find_iter(text) {
                let matched_text = capture.as_str().to_string();

                // Validate if enabled and required
                if self.config.enable_validation {
                    if let Some(meta) = self.metadata.get(pii_type) {
                        if meta.requires_validation && !self.validate(pii_type, &matched_text) {
                            // Skip this match if validation fails
                            continue;
                        }
                    }
                }

                // Calculate confidence score
                let confidence = self.calculate_confidence(pii_type, &matched_text);

                matches.push(PIIMatch::new(
                    pii_type.clone(),
                    capture.start(),
                    capture.end(),
                    matched_text,
                    confidence,
                ));
            }
        }

        // Sort matches by position for consistent output
        matches.sort_by_key(|m| m.start);
        matches
    }

    /// Detect PII with context awareness
    ///
    /// This method looks for context clues near PII (e.g., "SSN:", "Email:")
    /// to increase confidence in detection.
    ///
    /// # Arguments
    ///
    /// * `text` - The text to scan for PII
    /// * `context_window` - Number of characters before/after to check for context
    ///
    /// # Returns
    ///
    /// A vector of PIIMatch instances with adjusted confidence scores
    pub fn detect_with_context(&self, text: &str, context_window: usize) -> Vec<PIIMatch> {
        let mut matches = self.detect(text);

        if !self.config.enable_context {
            return matches;
        }

        // Adjust confidence based on context
        for match_ in &mut matches {
            let context_start = match_.start.saturating_sub(context_window);
            let context_end = (match_.end + context_window).min(text.len());
            let context = &text[context_start..context_end].to_lowercase();

            // Look for context clues
            let confidence_boost = match &match_.pii_type {
                PIIType::SSN if context.contains("ssn") || context.contains("social") => 0.1,
                PIIType::Email if context.contains("email") || context.contains("contact") => 0.1,
                PIIType::Phone if context.contains("phone") || context.contains("call") => 0.1,
                PIIType::CreditCard if context.contains("card") || context.contains("payment") => {
                    0.1
                }
                _ => 0.0,
            };

            match_.confidence = (match_.confidence + confidence_boost).min(1.0);
        }

        matches
    }

    /// Detect only specific types of PII
    ///
    /// # Arguments
    ///
    /// * `text` - The text to scan for PII
    /// * `types` - Slice of PIIType to search for
    ///
    /// # Returns
    ///
    /// A vector of PIIMatch instances for only the specified types
    pub fn detect_by_type(&self, text: &str, types: &[PIIType]) -> Vec<PIIMatch> {
        let all_matches = self.detect(text);
        all_matches
            .into_iter()
            .filter(|m| types.contains(&m.pii_type))
            .collect()
    }

    /// Count PII occurrences by type
    ///
    /// # Arguments
    ///
    /// * `text` - The text to scan for PII
    ///
    /// # Returns
    ///
    /// A HashMap mapping PIIType to count of occurrences
    pub fn count_pii(&self, text: &str) -> HashMap<PIIType, usize> {
        let matches = self.detect(text);
        let mut counts: HashMap<PIIType, usize> = HashMap::new();

        for match_ in matches {
            *counts.entry(match_.pii_type).or_insert(0) += 1;
        }

        counts
    }

    /// Validate a PII value based on its type
    fn validate(&self, pii_type: &PIIType, text: &str) -> bool {
        match pii_type {
            PIIType::CreditCard => validate_luhn(text),
            PIIType::SSN => validate_ssn(text),
            PIIType::Email => validate_email(text),
            PIIType::Phone => validate_phone(text),
            // Other types don't require validation
            _ => true,
        }
    }

    /// Calculate confidence score for a PII match
    fn calculate_confidence(&self, pii_type: &PIIType, text: &str) -> f64 {
        let base_confidence = if self.config.enable_validation {
            // If validation is enabled and this type was validated, high confidence
            if let Some(meta) = self.metadata.get(pii_type) {
                if meta.requires_validation && self.validate(pii_type, text) {
                    1.0 // Validated patterns get full confidence
                } else if meta.requires_validation {
                    0.7 // Pattern match without validation
                } else {
                    0.9 // No validation required
                }
            } else {
                0.8 // Default confidence
            }
        } else {
            // Without validation, moderate confidence
            0.8
        };

        base_confidence
    }
}

impl Default for PIIDetector {
    fn default() -> Self {
        Self::new(PIIConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pii::types::PatternSet;

    #[test]
    fn test_detector_creation() {
        let detector = PIIDetector::new(PIIConfig::default());
        assert_eq!(detector.config.pattern_set, PatternSet::Standard);
    }

    #[test]
    fn test_detect_ssn() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "My SSN is 123-45-6789";
        let matches = detector.detect(text);

        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].pii_type, PIIType::SSN);
        assert_eq!(matches[0].matched_text, "123-45-6789");
        assert_eq!(matches[0].start, 10);
        assert_eq!(matches[0].end, 21);
    }

    #[test]
    fn test_detect_email() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "Contact john.doe@example.com for more info";
        let matches = detector.detect(text);

        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].pii_type, PIIType::Email);
        assert_eq!(matches[0].matched_text, "john.doe@example.com");
    }

    #[test]
    fn test_detect_multiple_pii() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789";
        let matches = detector.detect(text);

        assert!(matches.len() >= 3);
        assert!(matches.iter().any(|m| m.pii_type == PIIType::Email));
        assert!(matches.iter().any(|m| m.pii_type == PIIType::Phone));
        assert!(matches.iter().any(|m| m.pii_type == PIIType::SSN));
    }

    #[test]
    fn test_detect_credit_card() {
        let detector = PIIDetector::new(PIIConfig {
            enable_validation: true,
            ..Default::default()
        });
        let text = "Card: 4532-0151-1283-0366";
        let matches = detector.detect(text);

        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].pii_type, PIIType::CreditCard);
    }

    #[test]
    fn test_detect_with_validation_rejects_invalid() {
        let detector = PIIDetector::new(PIIConfig {
            enable_validation: true,
            ..Default::default()
        });
        // Invalid Luhn checksum
        let text = "Card: 4532-0151-1283-0367";
        let matches = detector.detect(text);

        // Should not detect invalid credit card
        let cc_matches: Vec<_> = matches
            .iter()
            .filter(|m| m.pii_type == PIIType::CreditCard)
            .collect();
        assert_eq!(cc_matches.len(), 0);
    }

    #[test]
    fn test_detect_by_type() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "Email: test@example.com, Phone: 555-123-4567";
        let matches = detector.detect_by_type(text, &[PIIType::Email]);

        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].pii_type, PIIType::Email);
    }

    #[test]
    fn test_count_pii() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "test1@example.com and test2@example.com";
        let counts = detector.count_pii(text);

        assert_eq!(counts.get(&PIIType::Email), Some(&2));
    }

    #[test]
    fn test_detect_with_context() {
        let detector = PIIDetector::new(PIIConfig {
            enable_context: true,
            ..Default::default()
        });
        let text = "SSN: 123-45-6789";
        let matches = detector.detect_with_context(text, 10);

        assert_eq!(matches.len(), 1);
        // Context "SSN:" should boost confidence
        assert!(matches[0].confidence > 0.9);
    }

    #[test]
    fn test_pattern_set_strict() {
        let detector = PIIDetector::new(PIIConfig {
            pattern_set: PatternSet::Strict,
            ..Default::default()
        });
        let text = "Email: test@example.com, SSN: 123-45-6789";
        let matches = detector.detect(text);

        // Strict mode should detect SSN but not Email
        assert!(matches.iter().any(|m| m.pii_type == PIIType::SSN));
        assert!(!matches.iter().any(|m| m.pii_type == PIIType::Email));
    }

    #[test]
    fn test_empty_text() {
        let detector = PIIDetector::new(PIIConfig::default());
        let matches = detector.detect("");
        assert_eq!(matches.len(), 0);
    }

    #[test]
    fn test_no_pii_text() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "This text contains no PII information at all";
        let matches = detector.detect(text);
        assert_eq!(matches.len(), 0);
    }
}
