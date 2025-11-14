// Prompt Injection Detection Patterns
//
// This module contains all regex patterns used for prompt injection detection, compiled at startup
// using lazy_static for optimal performance.

use lazy_static::lazy_static;
use regex::Regex;
use std::collections::HashMap;

use crate::injection::types::{DetectionMode, InjectionType, Severity};

/// Metadata about an injection pattern
#[derive(Debug, Clone)]
pub struct PatternMetadata {
    /// Human-readable name
    pub name: &'static str,
    /// Description of what this pattern detects
    pub description: &'static str,
    /// Severity level
    pub severity: Severity,
    /// Example attack strings
    pub examples: Vec<&'static str>,
}

lazy_static! {
    pub static ref IGNORE_PREVIOUS: Regex = Regex::new(
        r"(?i)(ignore|disregard|forget|override)\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions?|prompts?|directions?|commands?)"
    ).unwrap();

    pub static ref NEW_INSTRUCTION: Regex = Regex::new(
        r"(?i)(now|from\s+now\s+on|henceforth|starting\s+now)\s+(you\s+are|act\s+as|behave\s+like|your\s+role\s+is|your\s+task\s+is)"
    ).unwrap();

    pub static ref SYSTEM_ROLE: Regex = Regex::new(
        r"(?i)(pretend|act\s+as|simulate|imagine|you\s+are\s+now|you're\s+now)\s+(an?\s+)?(assistant|AI|bot|system|chatbot|agent|human|person)"
    ).unwrap();

    pub static ref DIRECT_PROMPT_EXTRACTION: Regex = Regex::new(
        r"(?i)(show|reveal|display|print|output|tell\s+me|what\s+is|what's)\s+(your|the)?\s*(system\s+)?(prompt|instructions?|directives?|configuration|guidelines?)"
    ).unwrap();

    pub static ref INDIRECT_PROMPT_EXTRACTION: Regex = Regex::new(
        r"(?i)(tell\s+me|explain|describe|what\s+are)\s+(what\s+you\s+were\s+told|your\s+programming|your\s+rules|your\s+guidelines|your\s+constraints|your\s+limitations|your\s+capabilities)"
    ).unwrap();

    pub static ref ROLEPLAY_JAILBREAK: Regex = Regex::new(
        r"(?i)(let's\s+play|imagine|hypothetically|in\s+a\s+hypothetical\s+scenario|for\s+(educational|research|academic)\s+purposes)\s+(a\s+)?(game|scenario|simulation|exercise)"
    ).unwrap();

    pub static ref DAN_VARIANT: Regex = Regex::new(
        r"(?i)(DAN|do\s+anything\s+now|no\s+restrictions?|unrestricted\s+mode|jailbreak\s+mode|developer\s+mode|god\s+mode|admin\s+mode)"
    ).unwrap();

    pub static ref DELIMITER_INJECTION: Regex = Regex::new(
        r"(?i)(</?system>|</?prompt>|<!--\s*end|--!>|:::\s*end\s*:::|\\[END\\]|\{/?prompt\})"
    ).unwrap();

    pub static ref NESTED_PROMPT: Regex = Regex::new(
        r"(?i)(respond\s+to|execute|process|evaluate):\s*['`].*(?:ignore|override|bypass)"
    ).unwrap();

    pub static ref ENCODED_INSTRUCTION: Regex = Regex::new(
        r"(?i)(decode|decrypt|deobfuscate)\s+(and\s+)?(then\s+)?(execute|run|process)"
    ).unwrap();

    pub static ref COMMAND_INJECTION: Regex = Regex::new(
        r"\$\([^)]*\)|`.+`|&&|\|\||;\s*(?:rm|curl|wget|nc|bash)"
    ).unwrap();

    pub static ref TEMPLATE_INJECTION: Regex = Regex::new(
        r"\{\{[^}]*\}\}|\{%[^%]*%\}|\$\{[^}]+\}"
    ).unwrap();

    pub static ref DATA_EXFILTRATION: Regex = Regex::new(
        r"(?i)(send|email|post|upload|transmit|export)\s+(all\s+)?(data|conversation|history|logs|messages)|(https?://|mailto:)"
    ).unwrap();

    pub static ref MEMORY_STATE_ACCESS: Regex = Regex::new(
        r"(?i)(show|list|display|dump|access)\s+(all\s+)?(memory|cache|history|state|context|buffer|previous\s+conversations?)"
    ).unwrap();
}
