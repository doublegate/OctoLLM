// PII Type Definitions
//
// This module defines the core data structures used throughout the PII detection system.

use serde::{Deserialize, Serialize};
use std::fmt;

/// Enumeration of all PII types detected by the system
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PIIType {
    /// US Social Security Number (XXX-XX-XXXX)
    SSN,
    /// Credit card number (Visa, MasterCard, Amex, Discover)
    CreditCard,
    /// Email address
    Email,
    /// Phone number (US/International)
    Phone,
    /// IPv4 address
    IPv4,
    /// IPv6 address
    IPv6,
    /// API keys (AWS, GitHub, Stripe, etc.)
    ApiKey,
    /// Bitcoin address (legacy, SegWit, Bech32)
    BitcoinAddress,
    /// Ethereum address (0x + 40 hex chars)
    EthereumAddress,
    /// MAC address
    MacAddress,
    /// US Driver's License number
    DriversLicense,
    /// Passport number
    Passport,
    /// Medical Record Number (MRN)
    MedicalRecordNumber,
    /// Bank account number
    BankAccount,
    /// US routing number (9 digits)
    RoutingNumber,
    /// Individual Taxpayer Identification Number (9XX-XX-XXXX)
    ITIN,
    /// Date of birth
    DateOfBirth,
    /// Custom user-defined PII pattern
    Custom(String),
}

impl fmt::Display for PIIType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PIIType::SSN => write!(f, "SSN"),
            PIIType::CreditCard => write!(f, "CreditCard"),
            PIIType::Email => write!(f, "Email"),
            PIIType::Phone => write!(f, "Phone"),
            PIIType::IPv4 => write!(f, "IPv4"),
            PIIType::IPv6 => write!(f, "IPv6"),
            PIIType::ApiKey => write!(f, "ApiKey"),
            PIIType::BitcoinAddress => write!(f, "BitcoinAddress"),
            PIIType::EthereumAddress => write!(f, "EthereumAddress"),
            PIIType::MacAddress => write!(f, "MacAddress"),
            PIIType::DriversLicense => write!(f, "DriversLicense"),
            PIIType::Passport => write!(f, "Passport"),
            PIIType::MedicalRecordNumber => write!(f, "MedicalRecordNumber"),
            PIIType::BankAccount => write!(f, "BankAccount"),
            PIIType::RoutingNumber => write!(f, "RoutingNumber"),
            PIIType::ITIN => write!(f, "ITIN"),
            PIIType::DateOfBirth => write!(f, "DateOfBirth"),
            PIIType::Custom(name) => write!(f, "Custom({})", name),
        }
    }
}

/// Represents a single PII detection match
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PIIMatch {
    /// Type of PII detected
    pub pii_type: PIIType,
    /// Start byte offset in the original text
    pub start: usize,
    /// End byte offset in the original text
    pub end: usize,
    /// The matched text (actual PII value)
    pub matched_text: String,
    /// Confidence score (0.0-1.0)
    pub confidence: f64,
}

impl PIIMatch {
    /// Create a new PIIMatch instance
    pub fn new(
        pii_type: PIIType,
        start: usize,
        end: usize,
        matched_text: String,
        confidence: f64,
    ) -> Self {
        Self {
            pii_type,
            start,
            end,
            matched_text,
            confidence,
        }
    }

    /// Get the length of the matched text
    pub fn len(&self) -> usize {
        self.end - self.start
    }

    /// Check if the match is empty
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

/// Pattern set determines which patterns are enabled
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum PatternSet {
    /// Strict mode: High confidence patterns only, fewest false positives
    Strict,
    /// Standard mode: Balanced approach (default)
    #[default]
    Standard,
    /// Relaxed mode: Maximum detection, more false positives acceptable
    Relaxed,
}

/// Configuration for PII detection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PIIConfig {
    /// Which pattern set to use
    pub pattern_set: PatternSet,
    /// Enable validation (e.g., Luhn for credit cards)
    pub enable_validation: bool,
    /// Enable context-aware detection
    pub enable_context: bool,
}

impl Default for PIIConfig {
    fn default() -> Self {
        Self {
            pattern_set: PatternSet::Standard,
            enable_validation: true,
            enable_context: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pii_type_display() {
        assert_eq!(PIIType::SSN.to_string(), "SSN");
        assert_eq!(PIIType::Email.to_string(), "Email");
        assert_eq!(
            PIIType::Custom("TEST".to_string()).to_string(),
            "Custom(TEST)"
        );
    }

    #[test]
    fn test_pii_match_creation() {
        let m = PIIMatch::new(PIIType::Email, 0, 20, "test@example.com".to_string(), 0.95);
        assert_eq!(m.pii_type, PIIType::Email);
        assert_eq!(m.start, 0);
        assert_eq!(m.end, 20);
        assert_eq!(m.len(), 20);
        assert!(!m.is_empty());
    }

    #[test]
    fn test_pattern_set_default() {
        let ps = PatternSet::default();
        assert_eq!(ps, PatternSet::Standard);
    }

    #[test]
    fn test_pii_config_default() {
        let config = PIIConfig::default();
        assert_eq!(config.pattern_set, PatternSet::Standard);
        assert!(config.enable_validation);
        assert!(!config.enable_context);
    }
}
