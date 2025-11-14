// Comprehensive PII Module Tests
//
// This test suite covers all aspects of the PII detection system including
// patterns, detection, validation, and redaction.

#[cfg(test)]
mod integration_tests {
    use crate::pii::*;

    // Integration tests for full workflow
    #[test]
    fn test_full_workflow_detect_and_redact() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "Contact john.doe@example.com or call 555-123-4567. SSN: 123-45-6789";

        // Detect PII
        let matches = detector.detect(text);
        assert!(matches.len() >= 3);

        // Redact with different strategies
        let masked = redact(text, &matches, RedactionStrategy::Mask);
        assert!(!masked.contains("john.doe@example.com"));
        assert!(!masked.contains("555-123-4567"));
        assert!(!masked.contains("123-45-6789"));

        let tokens = redact(text, &matches, RedactionStrategy::Token);
        assert!(tokens.contains("TOKEN"));
    }

    #[test]
    fn test_all_pattern_types() {
        let detector = PIIDetector::new(PIIConfig {
            pattern_set: PatternSet::Relaxed,
            enable_validation: false,
            enable_context: false,
        });

        // Test text with various PII types
        let test_cases = vec![
            ("SSN: 123-45-6789", PIIType::SSN),
            ("Email: test@example.com", PIIType::Email),
            ("Phone: 555-123-4567", PIIType::Phone),
            ("IP: 192.168.1.1", PIIType::IPv4),
            (
                "Bitcoin: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                PIIType::BitcoinAddress,
            ),
            (
                "ETH: 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbC",
                PIIType::EthereumAddress,
            ), // Fixed: 40 hex chars
        ];

        for (text, expected_type) in test_cases {
            let matches = detector.detect(text);
            assert!(
                matches.iter().any(|m| m.pii_type == expected_type),
                "Failed to detect {} in text: {}",
                expected_type,
                text
            );
        }
    }

    #[test]
    fn test_pattern_set_filtering() {
        let text = "Email: test@example.com, SSN: 123-45-6789, MAC: 00:11:22:33:44:55";

        // Strict mode
        let strict_detector = PIIDetector::new(PIIConfig {
            pattern_set: PatternSet::Strict,
            ..Default::default()
        });
        let strict_matches = strict_detector.detect(text);
        assert!(strict_matches.iter().any(|m| m.pii_type == PIIType::SSN));
        assert!(!strict_matches.iter().any(|m| m.pii_type == PIIType::Email));
        assert!(!strict_matches
            .iter()
            .any(|m| m.pii_type == PIIType::MacAddress));

        // Standard mode
        let standard_detector = PIIDetector::new(PIIConfig {
            pattern_set: PatternSet::Standard,
            ..Default::default()
        });
        let standard_matches = standard_detector.detect(text);
        assert!(standard_matches.iter().any(|m| m.pii_type == PIIType::SSN));
        assert!(standard_matches
            .iter()
            .any(|m| m.pii_type == PIIType::Email));
        assert!(!standard_matches
            .iter()
            .any(|m| m.pii_type == PIIType::MacAddress));

        // Relaxed mode
        let relaxed_detector = PIIDetector::new(PIIConfig {
            pattern_set: PatternSet::Relaxed,
            ..Default::default()
        });
        let relaxed_matches = relaxed_detector.detect(text);
        assert!(relaxed_matches.iter().any(|m| m.pii_type == PIIType::SSN));
        assert!(relaxed_matches.iter().any(|m| m.pii_type == PIIType::Email));
        assert!(relaxed_matches
            .iter()
            .any(|m| m.pii_type == PIIType::MacAddress));
    }

    #[test]
    fn test_validation_filtering() {
        let text = "Valid: 4532-0151-1283-0366, Invalid: 4532-0151-1283-0367";

        // With validation enabled
        let detector_with_validation = PIIDetector::new(PIIConfig {
            enable_validation: true,
            ..Default::default()
        });
        let matches = detector_with_validation.detect(text);
        let cc_matches: Vec<_> = matches
            .iter()
            .filter(|m| m.pii_type == PIIType::CreditCard)
            .collect();
        assert_eq!(cc_matches.len(), 1); // Only valid card detected

        // Without validation
        let detector_no_validation = PIIDetector::new(PIIConfig {
            enable_validation: false,
            ..Default::default()
        });
        let matches = detector_no_validation.detect(text);
        let cc_matches: Vec<_> = matches
            .iter()
            .filter(|m| m.pii_type == PIIType::CreditCard)
            .collect();
        assert_eq!(cc_matches.len(), 2); // Both detected
    }

    #[test]
    fn test_edge_cases() {
        let detector = PIIDetector::new(PIIConfig::default());

        // Empty string
        let matches = detector.detect("");
        assert_eq!(matches.len(), 0);

        // Very long string
        let long_text = "No PII here. ".repeat(1000);
        let matches = detector.detect(&long_text);
        assert_eq!(matches.len(), 0);

        // Multiple same PII
        let text = "test1@example.com and test2@example.com and test3@example.com";
        let matches = detector.detect(text);
        let email_count = matches
            .iter()
            .filter(|m| m.pii_type == PIIType::Email)
            .count();
        assert_eq!(email_count, 3);

        // PII at start/end
        let text = "test@example.com middle 123-45-6789";
        let matches = detector.detect(text);
        assert!(matches.len() >= 2);
        assert_eq!(matches[0].start, 0); // Email at start
    }

    #[test]
    fn test_confidence_scoring() {
        let detector_validated = PIIDetector::new(PIIConfig {
            enable_validation: true,
            ..Default::default()
        });
        let detector_unvalidated = PIIDetector::new(PIIConfig {
            enable_validation: false,
            ..Default::default()
        });

        let text = "Valid SSN: 123-45-6789";

        let validated_matches = detector_validated.detect(text);
        let unvalidated_matches = detector_unvalidated.detect(text);

        // Validated matches should have higher confidence
        if let (Some(v), Some(u)) = (validated_matches.first(), unvalidated_matches.first()) {
            assert!(v.confidence >= u.confidence);
        }
    }

    #[test]
    fn test_redaction_strategies_comprehensive() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "Secret: test@example.com";
        let matches = detector.detect(text);

        assert!(!matches.is_empty());

        // Test all strategies
        let masked = redact(text, &matches, RedactionStrategy::Mask);
        assert!(masked.contains("****************"));

        let partial = redact(text, &matches, RedactionStrategy::Partial);
        assert!(partial.ends_with(".com")); // Last 4 chars preserved

        let removed = redact(text, &matches, RedactionStrategy::Remove);
        assert_eq!(removed, "Secret: ");

        let token = redact(text, &matches, RedactionStrategy::Token);
        assert!(token.contains("TOKEN"));

        let hash = redact(text, &matches, RedactionStrategy::Hash);
        assert_eq!(hash.chars().skip(8).take(16).count(), 16); // Hash is 16 chars
    }

    #[test]
    fn test_detect_by_type_filtering() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789";

        // Detect only emails
        let email_matches = detector.detect_by_type(text, &[PIIType::Email]);
        assert_eq!(email_matches.len(), 1);
        assert_eq!(email_matches[0].pii_type, PIIType::Email);

        // Detect multiple specific types
        let specific_matches = detector.detect_by_type(text, &[PIIType::Email, PIIType::SSN]);
        assert_eq!(specific_matches.len(), 2);
        assert!(specific_matches
            .iter()
            .all(|m| m.pii_type == PIIType::Email || m.pii_type == PIIType::SSN));
    }

    #[test]
    fn test_count_pii_functionality() {
        let detector = PIIDetector::new(PIIConfig::default());
        let text = "test1@example.com, test2@example.com, 555-123-4567";

        let counts = detector.count_pii(text);

        assert_eq!(counts.get(&PIIType::Email), Some(&2));
        assert_eq!(counts.get(&PIIType::Phone), Some(&1));
        assert_eq!(counts.get(&PIIType::SSN), None);
    }

    #[test]
    fn test_context_awareness() {
        let detector = PIIDetector::new(PIIConfig {
            enable_context: true,
            ..Default::default()
        });

        let text_with_context = "SSN: 123-45-6789";
        let text_without_context = "Random: 123-45-6789";

        let with_context = detector.detect_with_context(text_with_context, 10);
        let without_context = detector.detect_with_context(text_without_context, 10);

        // Both should detect SSN, but confidence might differ
        assert_eq!(with_context.len(), 1);
        assert_eq!(without_context.len(), 1);

        // Context should boost confidence
        assert!(with_context[0].confidence >= without_context[0].confidence);
    }

    #[test]
    fn test_unicode_text() {
        let detector = PIIDetector::new(PIIConfig::default());

        // Unicode text with embedded PII
        let text = "用户邮箱：test@example.com，电话：555-123-4567";
        let matches = detector.detect(text);

        assert!(matches.iter().any(|m| m.pii_type == PIIType::Email));
        assert!(matches.iter().any(|m| m.pii_type == PIIType::Phone));
    }

    #[test]
    fn test_special_characters() {
        let detector = PIIDetector::new(PIIConfig::default());

        // SSN with hyphens
        let matches = detector.detect("123-45-6789");
        assert!(!matches.is_empty(), "Should match hyphenated SSN");

        // SSN with no separator
        let matches = detector.detect("123456789");
        assert!(!matches.is_empty(), "Should match plain SSN");

        // Phone with parens and space
        let matches = detector.detect("(555) 123-4567");
        assert!(!matches.is_empty(), "Should match phone with parens");

        // Phone with country code
        let matches = detector.detect("+1-555-123-4567");
        assert!(!matches.is_empty(), "Should match phone with country code");
    }

    #[test]
    fn test_performance_large_text() {
        use std::time::Instant;

        let detector = PIIDetector::new(PIIConfig::default());

        // Generate large text (10KB)
        let large_text = format!(
            "This is a large text with some PII: test@example.com and 555-123-4567. {}",
            "Lorem ipsum dolor sit amet. ".repeat(300)
        );

        let start = Instant::now();
        let matches = detector.detect(&large_text);
        let duration = start.elapsed();

        assert!(matches.len() >= 2);
        // Performance target: <10ms for 10KB text
        assert!(duration.as_millis() < 10, "Detection took {:?}", duration);
    }
}
