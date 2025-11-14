// PII Detection Patterns
//
// This module contains all regex patterns used for PII detection, compiled at startup
// using lazy_static for optimal performance.

use lazy_static::lazy_static;
use regex::Regex;
use std::collections::HashMap;

use crate::pii::types::{PIIType, PatternSet};

/// Severity level for different PII types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Severity {
    /// Critical severity (e.g., SSN, credit cards)
    Critical,
    /// High severity (e.g., API keys, passwords)
    High,
    /// Medium severity (e.g., email, phone)
    Medium,
    /// Low severity (e.g., IP addresses)
    Low,
}

/// Metadata about a PII pattern
#[derive(Debug, Clone)]
pub struct PatternMetadata {
    /// Human-readable name
    pub name: &'static str,
    /// Description of what this pattern detects
    pub description: &'static str,
    /// Severity level
    pub severity: Severity,
    /// Whether validation is required
    pub requires_validation: bool,
}

lazy_static! {
    /// US Social Security Number (XXX-XX-XXXX or XXXXXXXXX)
    /// Note: This pattern matches the format; validation logic filters invalid area/group/serial numbers
    pub static ref SSN_PATTERN: Regex = Regex::new(
        r"\b\d{3}-?\d{2}-?\d{4}\b"
    ).unwrap();

    /// Credit Card Numbers (Visa, MasterCard, Amex, Discover)
    /// Visa: 16 digits starting with 4
    /// MasterCard: 16 digits starting with 51-55 or 2221-2720
    /// Amex: 15 digits starting with 34 or 37
    /// Discover: 16 digits starting with 6011, 622126-622925, 644-649, 65
    pub static ref CREDIT_CARD_PATTERN: Regex = Regex::new(
        r"\b(?:4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}|6(?:011|5\d{2})[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})\b"
    ).unwrap();

    /// Email Address (RFC 5322 simplified)
    pub static ref EMAIL_PATTERN: Regex = Regex::new(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ).unwrap();

    /// Phone Number (US and International)
    /// Matches: (XXX) XXX-XXXX, XXX-XXX-XXXX, +1-XXX-XXX-XXXX
    pub static ref PHONE_PATTERN: Regex = Regex::new(
        r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
    ).unwrap();

    /// IPv4 Address
    pub static ref IPV4_PATTERN: Regex = Regex::new(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    ).unwrap();

    /// IPv6 Address (simplified pattern)
    pub static ref IPV6_PATTERN: Regex = Regex::new(
        r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    ).unwrap();

    /// API Keys (AWS, GitHub, Stripe, generic)
    /// AWS: AKIA[0-9A-Z]{16}
    /// GitHub: ghp_[a-zA-Z0-9]{36}
    /// Stripe: sk_live_[a-zA-Z0-9]{24}
    pub static ref API_KEY_PATTERN: Regex = Regex::new(
        r"\b(?:AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|sk_live_[a-zA-Z0-9]{24})\b"
    ).unwrap();

    /// Bitcoin Address
    /// Legacy (P2PKH): starts with 1, 26-35 characters
    /// SegWit (P2SH): starts with 3, 26-35 characters
    /// Bech32: starts with bc1, 42-62 characters
    pub static ref BITCOIN_ADDRESS_PATTERN: Regex = Regex::new(
        r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b"
    ).unwrap();

    /// Ethereum Address (0x followed by 40 hexadecimal characters)
    pub static ref ETHEREUM_ADDRESS_PATTERN: Regex = Regex::new(
        r"\b0x[a-fA-F0-9]{40}\b"
    ).unwrap();

    /// MAC Address
    pub static ref MAC_ADDRESS_PATTERN: Regex = Regex::new(
        r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b"
    ).unwrap();

    /// US Driver's License Number (California example: 1 letter + 7 digits)
    /// Note: This is a simplified pattern; actual DL formats vary by state
    pub static ref DRIVERS_LICENSE_PATTERN: Regex = Regex::new(
        r"\b[A-Z][0-9]{7}\b"
    ).unwrap();

    /// Passport Number (US and international)
    /// 1-2 letters followed by 6-9 digits
    pub static ref PASSPORT_PATTERN: Regex = Regex::new(
        r"\b[A-Z]{1,2}[0-9]{6,9}\b"
    ).unwrap();

    /// Medical Record Number (MRN)
    pub static ref MEDICAL_RECORD_NUMBER_PATTERN: Regex = Regex::new(
        r"\bMRN[:-]?\s*[0-9]{6,10}\b"
    ).unwrap();

    /// Bank Account Number (US, 8-17 digits)
    pub static ref BANK_ACCOUNT_PATTERN: Regex = Regex::new(
        r"\b[0-9]{8,17}\b"
    ).unwrap();

    /// US Routing Number (9 digits)
    pub static ref ROUTING_NUMBER_PATTERN: Regex = Regex::new(
        r"\b[0-9]{9}\b"
    ).unwrap();

    /// ITIN (Individual Taxpayer Identification Number)
    /// Format: 9XX-XX-XXXX (starts with 9)
    pub static ref ITIN_PATTERN: Regex = Regex::new(
        r"\b9\d{2}-?\d{2}-?\d{4}\b"
    ).unwrap();

    /// Date of Birth (MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD)
    pub static ref DATE_OF_BIRTH_PATTERN: Regex = Regex::new(
        r"\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12][0-9]|3[01])[-/](?:19|20)\d{2}\b"
    ).unwrap();
}

/// Pattern metadata registry
pub fn get_pattern_metadata() -> HashMap<PIIType, PatternMetadata> {
    let mut metadata = HashMap::new();

    metadata.insert(
        PIIType::SSN,
        PatternMetadata {
            name: "Social Security Number",
            description: "US Social Security Number (XXX-XX-XXXX)",
            severity: Severity::Critical,
            requires_validation: true,
        },
    );

    metadata.insert(
        PIIType::CreditCard,
        PatternMetadata {
            name: "Credit Card",
            description: "Credit card number (Visa, MC, Amex, Discover)",
            severity: Severity::Critical,
            requires_validation: true,
        },
    );

    metadata.insert(
        PIIType::Email,
        PatternMetadata {
            name: "Email Address",
            description: "Email address",
            severity: Severity::Medium,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::Phone,
        PatternMetadata {
            name: "Phone Number",
            description: "Phone number (US/International)",
            severity: Severity::Medium,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::IPv4,
        PatternMetadata {
            name: "IPv4 Address",
            description: "IPv4 network address",
            severity: Severity::Low,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::IPv6,
        PatternMetadata {
            name: "IPv6 Address",
            description: "IPv6 network address",
            severity: Severity::Low,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::ApiKey,
        PatternMetadata {
            name: "API Key",
            description: "API key (AWS, GitHub, Stripe, etc.)",
            severity: Severity::High,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::BitcoinAddress,
        PatternMetadata {
            name: "Bitcoin Address",
            description: "Bitcoin cryptocurrency address",
            severity: Severity::High,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::EthereumAddress,
        PatternMetadata {
            name: "Ethereum Address",
            description: "Ethereum cryptocurrency address",
            severity: Severity::High,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::MacAddress,
        PatternMetadata {
            name: "MAC Address",
            description: "Network MAC address",
            severity: Severity::Low,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::DriversLicense,
        PatternMetadata {
            name: "Driver's License",
            description: "US driver's license number",
            severity: Severity::Critical,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::Passport,
        PatternMetadata {
            name: "Passport Number",
            description: "Passport number",
            severity: Severity::Critical,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::MedicalRecordNumber,
        PatternMetadata {
            name: "Medical Record Number",
            description: "Medical record number (MRN)",
            severity: Severity::Critical,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::BankAccount,
        PatternMetadata {
            name: "Bank Account",
            description: "Bank account number",
            severity: Severity::Critical,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::RoutingNumber,
        PatternMetadata {
            name: "Routing Number",
            description: "US bank routing number",
            severity: Severity::High,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::ITIN,
        PatternMetadata {
            name: "ITIN",
            description: "Individual Taxpayer Identification Number",
            severity: Severity::Critical,
            requires_validation: false,
        },
    );

    metadata.insert(
        PIIType::DateOfBirth,
        PatternMetadata {
            name: "Date of Birth",
            description: "Date of birth",
            severity: Severity::High,
            requires_validation: false,
        },
    );

    metadata
}

/// Get patterns for a specific pattern set
pub fn get_patterns(pattern_set: &PatternSet) -> HashMap<PIIType, &'static Regex> {
    let mut patterns = HashMap::new();

    match pattern_set {
        PatternSet::Strict => {
            // Strict mode: Only high-confidence, critical PII
            patterns.insert(PIIType::SSN, &*SSN_PATTERN);
            patterns.insert(PIIType::CreditCard, &*CREDIT_CARD_PATTERN);
            patterns.insert(PIIType::ApiKey, &*API_KEY_PATTERN);
            patterns.insert(PIIType::Passport, &*PASSPORT_PATTERN);
            patterns.insert(
                PIIType::MedicalRecordNumber,
                &*MEDICAL_RECORD_NUMBER_PATTERN,
            );
        }
        PatternSet::Standard => {
            // Standard mode: Balanced approach (all common patterns)
            patterns.insert(PIIType::SSN, &*SSN_PATTERN);
            patterns.insert(PIIType::CreditCard, &*CREDIT_CARD_PATTERN);
            patterns.insert(PIIType::Email, &*EMAIL_PATTERN);
            patterns.insert(PIIType::Phone, &*PHONE_PATTERN);
            patterns.insert(PIIType::IPv4, &*IPV4_PATTERN);
            patterns.insert(PIIType::ApiKey, &*API_KEY_PATTERN);
            patterns.insert(PIIType::BitcoinAddress, &*BITCOIN_ADDRESS_PATTERN);
            patterns.insert(PIIType::EthereumAddress, &*ETHEREUM_ADDRESS_PATTERN);
            patterns.insert(PIIType::DriversLicense, &*DRIVERS_LICENSE_PATTERN);
            patterns.insert(PIIType::Passport, &*PASSPORT_PATTERN);
            patterns.insert(
                PIIType::MedicalRecordNumber,
                &*MEDICAL_RECORD_NUMBER_PATTERN,
            );
            patterns.insert(PIIType::ITIN, &*ITIN_PATTERN);
            patterns.insert(PIIType::DateOfBirth, &*DATE_OF_BIRTH_PATTERN);
        }
        PatternSet::Relaxed => {
            // Relaxed mode: All patterns (maximum detection)
            patterns.insert(PIIType::SSN, &*SSN_PATTERN);
            patterns.insert(PIIType::CreditCard, &*CREDIT_CARD_PATTERN);
            patterns.insert(PIIType::Email, &*EMAIL_PATTERN);
            patterns.insert(PIIType::Phone, &*PHONE_PATTERN);
            patterns.insert(PIIType::IPv4, &*IPV4_PATTERN);
            patterns.insert(PIIType::IPv6, &*IPV6_PATTERN);
            patterns.insert(PIIType::ApiKey, &*API_KEY_PATTERN);
            patterns.insert(PIIType::BitcoinAddress, &*BITCOIN_ADDRESS_PATTERN);
            patterns.insert(PIIType::EthereumAddress, &*ETHEREUM_ADDRESS_PATTERN);
            patterns.insert(PIIType::MacAddress, &*MAC_ADDRESS_PATTERN);
            patterns.insert(PIIType::DriversLicense, &*DRIVERS_LICENSE_PATTERN);
            patterns.insert(PIIType::Passport, &*PASSPORT_PATTERN);
            patterns.insert(
                PIIType::MedicalRecordNumber,
                &*MEDICAL_RECORD_NUMBER_PATTERN,
            );
            patterns.insert(PIIType::BankAccount, &*BANK_ACCOUNT_PATTERN);
            patterns.insert(PIIType::RoutingNumber, &*ROUTING_NUMBER_PATTERN);
            patterns.insert(PIIType::ITIN, &*ITIN_PATTERN);
            patterns.insert(PIIType::DateOfBirth, &*DATE_OF_BIRTH_PATTERN);
        }
    }

    patterns
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ssn_pattern() {
        // Pattern matches format (validation filters invalid values)
        assert!(SSN_PATTERN.is_match("123-45-6789"));
        assert!(SSN_PATTERN.is_match("123456789"));
        assert!(SSN_PATTERN.is_match("000-12-3456")); // Pattern matches (validator rejects)
        assert!(SSN_PATTERN.is_match("666-12-3456")); // Pattern matches (validator rejects)
        assert!(SSN_PATTERN.is_match("900-12-3456")); // Pattern matches (validator rejects)
        assert!(!SSN_PATTERN.is_match("12-345-6789")); // Wrong format
        assert!(!SSN_PATTERN.is_match("abc-de-fghi")); // Non-digits
    }

    #[test]
    fn test_credit_card_pattern() {
        assert!(CREDIT_CARD_PATTERN.is_match("4532-1234-5678-9010")); // Visa
        assert!(CREDIT_CARD_PATTERN.is_match("5425 2334 3010 9903")); // MasterCard
        assert!(CREDIT_CARD_PATTERN.is_match("3782 822463 10005")); // Amex
    }

    #[test]
    fn test_email_pattern() {
        assert!(EMAIL_PATTERN.is_match("user@example.com"));
        assert!(EMAIL_PATTERN.is_match("test.user+tag@sub.example.co.uk"));
        assert!(!EMAIL_PATTERN.is_match("not-an-email"));
    }

    #[test]
    fn test_phone_pattern() {
        assert!(PHONE_PATTERN.is_match("555-123-4567"));
        assert!(PHONE_PATTERN.is_match("(555) 123-4567"));
        assert!(PHONE_PATTERN.is_match("+1-555-123-4567"));
    }

    #[test]
    fn test_ipv4_pattern() {
        assert!(IPV4_PATTERN.is_match("192.168.1.1"));
        assert!(IPV4_PATTERN.is_match("10.0.0.0"));
        assert!(!IPV4_PATTERN.is_match("256.1.1.1")); // Invalid octet
    }

    #[test]
    fn test_api_key_pattern() {
        assert!(API_KEY_PATTERN.is_match("AKIAIOSFODNN7EXAMPLE"));
        assert!(API_KEY_PATTERN.is_match("ghp_1234567890abcdefghijklmnopqrstuvwxyz"));
        assert!(API_KEY_PATTERN.is_match("sk_test_1234567890abcdefghijklm")); // Test key, not real
    }

    #[test]
    fn test_pattern_set_strict() {
        let patterns = get_patterns(&PatternSet::Strict);
        assert!(patterns.contains_key(&PIIType::SSN));
        assert!(patterns.contains_key(&PIIType::CreditCard));
        assert!(!patterns.contains_key(&PIIType::Email)); // Not in strict mode
    }

    #[test]
    fn test_pattern_set_standard() {
        let patterns = get_patterns(&PatternSet::Standard);
        assert!(patterns.contains_key(&PIIType::SSN));
        assert!(patterns.contains_key(&PIIType::Email));
        assert!(!patterns.contains_key(&PIIType::MacAddress)); // Not in standard
    }

    #[test]
    fn test_pattern_set_relaxed() {
        let patterns = get_patterns(&PatternSet::Relaxed);
        assert!(patterns.contains_key(&PIIType::SSN));
        assert!(patterns.contains_key(&PIIType::Email));
        assert!(patterns.contains_key(&PIIType::MacAddress)); // All patterns enabled
    }

    #[test]
    fn test_pattern_metadata() {
        let metadata = get_pattern_metadata();
        let ssn_meta = metadata.get(&PIIType::SSN).unwrap();
        assert_eq!(ssn_meta.severity, Severity::Critical);
        assert!(ssn_meta.requires_validation);
    }
}
