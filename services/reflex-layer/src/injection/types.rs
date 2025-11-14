// Injection Detection Type Definitions
//
// This module defines the core data structures used throughout the prompt injection detection system.

use serde::{Deserialize, Serialize};
use std::fmt;

/// Enumeration of all injection attack types detected by the system
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum InjectionType {
    /// Ignore/Disregard previous instructions
    IgnorePreviousInstructions,
    /// New instruction injection (now you are, from now on)
    NewInstructionInjection,
    /// System role manipulation (pretend you are, act as)
    SystemRoleManipulation,
    /// Direct prompt extraction (show me your prompt)
    DirectPromptExtraction,
    /// Indirect prompt extraction (tell me your rules)
    IndirectPromptExtraction,
    /// Role-playing jailbreak (let's play a game where)
    RolePlayingJailbreak,
    /// DAN (Do Anything Now) variants
    DANVariant,
    /// Delimiter injection (</system>, <!-- end prompt -->)
    DelimiterInjection,
    /// Nested prompts (respond to: "...")
    NestedPrompt,
    /// Encoded instructions (decode and execute)
    EncodedInstruction,
    /// Command injection markers ($(), ``, |, ;)
    CommandInjection,
    /// Template injection ({{}}, {%%}, ${})
    TemplateInjection,
    /// Data exfiltration attempts
    DataExfiltration,
    /// Memory/State access attempts
    MemoryStateAccess,
    /// Custom user-defined injection pattern
    Custom(String),
}

impl fmt::Display for InjectionType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            InjectionType::IgnorePreviousInstructions => write!(f, "IgnorePreviousInstructions"),
            InjectionType::NewInstructionInjection => write!(f, "NewInstructionInjection"),
            InjectionType::SystemRoleManipulation => write!(f, "SystemRoleManipulation"),
            InjectionType::DirectPromptExtraction => write!(f, "DirectPromptExtraction"),
            InjectionType::IndirectPromptExtraction => write!(f, "IndirectPromptExtraction"),
            InjectionType::RolePlayingJailbreak => write!(f, "RolePlayingJailbreak"),
            InjectionType::DANVariant => write!(f, "DANVariant"),
            InjectionType::DelimiterInjection => write!(f, "DelimiterInjection"),
            InjectionType::NestedPrompt => write!(f, "NestedPrompt"),
            InjectionType::EncodedInstruction => write!(f, "EncodedInstruction"),
            InjectionType::CommandInjection => write!(f, "CommandInjection"),
            InjectionType::TemplateInjection => write!(f, "TemplateInjection"),
            InjectionType::DataExfiltration => write!(f, "DataExfiltration"),
            InjectionType::MemoryStateAccess => write!(f, "MemoryStateAccess"),
            InjectionType::Custom(name) => write!(f, "Custom({})", name),
        }
    }
}

/// Severity level for different injection types
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Severity {
    /// Low severity (score 1-3) - Suspicious but might be legitimate
    Low,
    /// Medium severity (score 4-6) - Potential attack, requires review
    Medium,
    /// High severity (score 7-8) - Likely attack, should be blocked
    High,
    /// Critical severity (score 9-10) - Definite attack, block immediately
    Critical,
}

impl Severity {
    /// Get numeric score for this severity level
    pub fn score(&self) -> u8 {
        match self {
            Severity::Low => 2,
            Severity::Medium => 5,
            Severity::High => 7,
            Severity::Critical => 9,
        }
    }
}

impl fmt::Display for Severity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Severity::Low => write!(f, "Low"),
            Severity::Medium => write!(f, "Medium"),
            Severity::High => write!(f, "High"),
            Severity::Critical => write!(f, "Critical"),
        }
    }
}

/// Represents a single injection detection match
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InjectionMatch {
    /// Type of injection detected
    pub injection_type: InjectionType,
    /// Start byte offset in the original text
    pub start: usize,
    /// End byte offset in the original text
    pub end: usize,
    /// The matched text (actual injection attempt)
    pub matched_text: String,
    /// Severity level of this injection
    pub severity: Severity,
    /// Confidence score (0.0-1.0)
    pub confidence: f64,
    /// List of indicators that contributed to detection
    pub indicators: Vec<String>,
}

impl InjectionMatch {
    /// Create a new InjectionMatch instance
    pub fn new(
        injection_type: InjectionType,
        start: usize,
        end: usize,
        matched_text: String,
        severity: Severity,
        confidence: f64,
        indicators: Vec<String>,
    ) -> Self {
        Self {
            injection_type,
            start,
            end,
            matched_text,
            severity,
            confidence,
            indicators,
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

/// Detection mode determines which patterns are enabled and how strict filtering is
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum DetectionMode {
    /// Strict mode: Block on first critical match
    Strict,
    /// Standard mode: Block on high severity or multiple medium (default)
    #[default]
    Standard,
    /// Relaxed mode: Flag but don't block unless critical
    Relaxed,
}

/// Configuration for injection detection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InjectionConfig {
    /// Which detection mode to use
    pub detection_mode: DetectionMode,
    /// Enable context analysis (reduces false positives)
    pub enable_context_analysis: bool,
    /// Enable entropy check for encoding detection
    pub enable_entropy_check: bool,
    /// Minimum severity threshold to report
    pub severity_threshold: Severity,
}

impl Default for InjectionConfig {
    fn default() -> Self {
        Self {
            detection_mode: DetectionMode::Standard,
            enable_context_analysis: true,
            enable_entropy_check: true,
            severity_threshold: Severity::Low,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_injection_type_display() {
        assert_eq!(
            InjectionType::IgnorePreviousInstructions.to_string(),
            "IgnorePreviousInstructions"
        );
        assert_eq!(InjectionType::DANVariant.to_string(), "DANVariant");
        assert_eq!(
            InjectionType::Custom("TEST".to_string()).to_string(),
            "Custom(TEST)"
        );
    }

    #[test]
    fn test_severity_ordering() {
        assert!(Severity::Low < Severity::Medium);
        assert!(Severity::Medium < Severity::High);
        assert!(Severity::High < Severity::Critical);
    }

    #[test]
    fn test_severity_score() {
        assert_eq!(Severity::Low.score(), 2);
        assert_eq!(Severity::Medium.score(), 5);
        assert_eq!(Severity::High.score(), 7);
        assert_eq!(Severity::Critical.score(), 9);
    }

    #[test]
    fn test_injection_match_creation() {
        let m = InjectionMatch::new(
            InjectionType::DANVariant,
            0,
            20,
            "DAN mode activated".to_string(),
            Severity::Critical,
            0.95,
            vec!["DAN".to_string()],
        );
        assert_eq!(m.injection_type, InjectionType::DANVariant);
        assert_eq!(m.severity, Severity::Critical);
        assert_eq!(m.confidence, 0.95);
        assert_eq!(m.len(), 20);
        assert!(!m.is_empty());
    }

    #[test]
    fn test_detection_mode_default() {
        let mode = DetectionMode::default();
        assert_eq!(mode, DetectionMode::Standard);
    }

    #[test]
    fn test_injection_config_default() {
        let config = InjectionConfig::default();
        assert_eq!(config.detection_mode, DetectionMode::Standard);
        assert!(config.enable_context_analysis);
        assert!(config.enable_entropy_check);
        assert_eq!(config.severity_threshold, Severity::Low);
    }
}
