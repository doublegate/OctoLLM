//! Rate limiting types and configurations
//!
//! Defines tier-based rate limits, token bucket configurations, and result types.

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Rate limit tier definitions
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum RateLimitTier {
    /// Free tier: 100 requests/hour, burst of 10
    #[default]
    Free,
    /// Basic tier: 1,000 requests/hour, burst of 50
    Basic,
    /// Pro tier: 10,000 requests/hour, burst of 100
    Pro,
    /// Enterprise tier: 100,000 requests/hour, burst of 500
    Enterprise,
    /// Unlimited tier: No rate limits (internal/admin use)
    Unlimited,
}

impl RateLimitTier {
    /// Get the rate limit configuration for this tier
    pub fn config(&self) -> RateLimitConfig {
        match self {
            RateLimitTier::Free => RateLimitConfig {
                capacity: 10,
                refill_rate: 100.0 / 3600.0, // 100 per hour
            },
            RateLimitTier::Basic => RateLimitConfig {
                capacity: 50,
                refill_rate: 1000.0 / 3600.0, // 1000 per hour
            },
            RateLimitTier::Pro => RateLimitConfig {
                capacity: 100,
                refill_rate: 10000.0 / 3600.0, // 10,000 per hour
            },
            RateLimitTier::Enterprise => RateLimitConfig {
                capacity: 500,
                refill_rate: 100000.0 / 3600.0, // 100,000 per hour
            },
            RateLimitTier::Unlimited => RateLimitConfig {
                capacity: u64::MAX,
                refill_rate: f64::MAX,
            },
        }
    }

    /// Get human-readable description of the tier
    pub fn description(&self) -> &'static str {
        match self {
            RateLimitTier::Free => "100 requests/hour, burst 10",
            RateLimitTier::Basic => "1,000 requests/hour, burst 50",
            RateLimitTier::Pro => "10,000 requests/hour, burst 100",
            RateLimitTier::Enterprise => "100,000 requests/hour, burst 500",
            RateLimitTier::Unlimited => "No limits",
        }
    }
}

/// Rate limit configuration
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct RateLimitConfig {
    /// Maximum number of tokens (burst capacity)
    pub capacity: u64,
    /// Token refill rate (tokens per second)
    pub refill_rate: f64,
}

impl RateLimitConfig {
    /// Create a custom rate limit configuration
    pub fn custom(capacity: u64, requests_per_hour: f64) -> Self {
        Self {
            capacity,
            refill_rate: requests_per_hour / 3600.0,
        }
    }

    /// Create configuration from requests per minute
    pub fn from_rpm(capacity: u64, requests_per_minute: f64) -> Self {
        Self {
            capacity,
            refill_rate: requests_per_minute / 60.0,
        }
    }

    /// Get requests per hour for this configuration
    pub fn requests_per_hour(&self) -> f64 {
        self.refill_rate * 3600.0
    }

    /// Get requests per minute for this configuration
    pub fn requests_per_minute(&self) -> f64 {
        self.refill_rate * 60.0
    }
}

/// Result of a rate limit check
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum RateLimitResult {
    /// Request is allowed
    Allowed {
        /// Remaining tokens in the bucket
        remaining: f64,
        /// Time until next token refill (milliseconds)
        reset_after_ms: u64,
    },
    /// Request is rate limited
    Limited {
        /// Reason for rate limiting
        reason: RateLimitReason,
        /// Time to wait before retrying (milliseconds)
        retry_after_ms: u64,
        /// Current token count (may be fractional)
        current_tokens: f64,
    },
}

impl RateLimitResult {
    /// Check if the request is allowed
    pub fn is_allowed(&self) -> bool {
        matches!(self, RateLimitResult::Allowed { .. })
    }

    /// Check if the request is limited
    pub fn is_limited(&self) -> bool {
        matches!(self, RateLimitResult::Limited { .. })
    }
}

/// Reason for rate limiting
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RateLimitReason {
    /// User quota exceeded
    UserQuota,
    /// IP address quota exceeded
    IPQuota,
    /// Endpoint quota exceeded
    EndpointQuota,
    /// Global system quota exceeded
    GlobalQuota,
    /// Custom quota exceeded
    Custom,
}

impl RateLimitReason {
    /// Get human-readable description
    pub fn description(&self) -> &'static str {
        match self {
            RateLimitReason::UserQuota => "User request quota exceeded",
            RateLimitReason::IPQuota => "IP address request quota exceeded",
            RateLimitReason::EndpointQuota => "Endpoint request quota exceeded",
            RateLimitReason::GlobalQuota => "System-wide quota exceeded",
            RateLimitReason::Custom => "Custom quota exceeded",
        }
    }
}

/// Rate limiting errors
#[derive(Error, Debug)]
pub enum RateLimitError {
    /// Redis connection or operation error
    #[error("Redis error: {0}")]
    Redis(#[from] redis::RedisError),

    /// Configuration error
    #[error("Configuration error: {0}")]
    Config(String),

    /// Invalid key format
    #[error("Invalid key: {0}")]
    InvalidKey(String),

    /// Lua script execution error
    #[error("Script error: {0}")]
    ScriptError(String),

    /// Serialization error
    #[error("Serialization error: {0}")]
    Serialization(String),

    /// Internal error
    #[error("Internal error: {0}")]
    Internal(String),

    /// Reflex error (for compatibility)
    #[error("Reflex error: {0}")]
    Reflex(String),
}

// Convert ReflexError to RateLimitError for compatibility
impl From<crate::error::ReflexError> for RateLimitError {
    fn from(err: crate::error::ReflexError) -> Self {
        match err {
            crate::error::ReflexError::Redis(e) => RateLimitError::Redis(e),
            other => RateLimitError::Reflex(other.to_string()),
        }
    }
}

/// Rate limit key type for multi-dimensional limiting
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum RateLimitKey {
    /// Rate limit by user ID
    User(String),
    /// Rate limit by IP address
    IP(String),
    /// Rate limit by endpoint
    Endpoint(String),
    /// Global rate limit
    Global,
    /// Custom key
    Custom(String),
}

impl RateLimitKey {
    /// Convert to Redis key string
    pub fn to_redis_key(&self) -> String {
        match self {
            RateLimitKey::User(id) => format!("ratelimit:user:{}", id),
            RateLimitKey::IP(ip) => format!("ratelimit:ip:{}", ip),
            RateLimitKey::Endpoint(endpoint) => format!("ratelimit:endpoint:{}", endpoint),
            RateLimitKey::Global => "ratelimit:global".to_string(),
            RateLimitKey::Custom(key) => format!("ratelimit:custom:{}", key),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rate_limit_tier_config() {
        let free = RateLimitTier::Free.config();
        assert_eq!(free.capacity, 10);
        assert!((free.refill_rate - (100.0 / 3600.0)).abs() < 0.0001);

        let pro = RateLimitTier::Pro.config();
        assert_eq!(pro.capacity, 100);
        assert!((pro.refill_rate - (10000.0 / 3600.0)).abs() < 0.001);
    }

    #[test]
    fn test_rate_limit_tier_default() {
        assert_eq!(RateLimitTier::default(), RateLimitTier::Free);
    }

    #[test]
    fn test_rate_limit_tier_description() {
        assert_eq!(
            RateLimitTier::Free.description(),
            "100 requests/hour, burst 10"
        );
        assert_eq!(RateLimitTier::Unlimited.description(), "No limits");
    }

    #[test]
    fn test_rate_limit_config_custom() {
        let config = RateLimitConfig::custom(50, 1200.0);
        assert_eq!(config.capacity, 50);
        assert!((config.refill_rate - (1200.0 / 3600.0)).abs() < 0.0001);
    }

    #[test]
    fn test_rate_limit_config_from_rpm() {
        let config = RateLimitConfig::from_rpm(30, 120.0);
        assert_eq!(config.capacity, 30);
        assert!((config.refill_rate - 2.0).abs() < 0.0001); // 120/60 = 2
    }

    #[test]
    fn test_rate_limit_config_conversions() {
        let config = RateLimitConfig::custom(100, 3600.0);
        assert!((config.requests_per_hour() - 3600.0).abs() < 0.1);
        assert!((config.requests_per_minute() - 60.0).abs() < 0.1);
    }

    #[test]
    fn test_rate_limit_result_allowed() {
        let result = RateLimitResult::Allowed {
            remaining: 50.0,
            reset_after_ms: 1000,
        };
        assert!(result.is_allowed());
        assert!(!result.is_limited());
    }

    #[test]
    fn test_rate_limit_result_limited() {
        let result = RateLimitResult::Limited {
            reason: RateLimitReason::UserQuota,
            retry_after_ms: 5000,
            current_tokens: 0.0,
        };
        assert!(!result.is_allowed());
        assert!(result.is_limited());
    }

    #[test]
    fn test_rate_limit_reason_description() {
        assert_eq!(
            RateLimitReason::UserQuota.description(),
            "User request quota exceeded"
        );
        assert_eq!(
            RateLimitReason::GlobalQuota.description(),
            "System-wide quota exceeded"
        );
    }

    #[test]
    fn test_rate_limit_key_to_redis_key() {
        assert_eq!(
            RateLimitKey::User("user123".to_string()).to_redis_key(),
            "ratelimit:user:user123"
        );
        assert_eq!(
            RateLimitKey::IP("192.168.1.1".to_string()).to_redis_key(),
            "ratelimit:ip:192.168.1.1"
        );
        assert_eq!(
            RateLimitKey::Endpoint("/api/v1/tasks".to_string()).to_redis_key(),
            "ratelimit:endpoint:/api/v1/tasks"
        );
        assert_eq!(RateLimitKey::Global.to_redis_key(), "ratelimit:global");
    }

    #[test]
    fn test_rate_limit_key_custom() {
        let key = RateLimitKey::Custom("special:limit".to_string());
        assert_eq!(key.to_redis_key(), "ratelimit:custom:special:limit");
    }
}
