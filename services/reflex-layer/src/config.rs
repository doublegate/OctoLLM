//! Configuration management for the Reflex Layer
//!
//! Loads configuration from environment variables with sensible defaults.
//! Supports environment-based overrides for development, staging, and production.

use serde::Deserialize;
use std::time::Duration;

/// Main configuration structure for the Reflex Layer
#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    /// Server configuration
    pub server: ServerConfig,

    /// Redis configuration
    pub redis: RedisConfig,

    /// Security configuration (PII detection, injection detection)
    pub security: SecurityConfig,

    /// Rate limiting configuration
    pub rate_limit: RateLimitConfig,

    /// Performance tuning
    pub performance: PerformanceConfig,

    /// Logging configuration
    pub logging: LoggingConfig,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ServerConfig {
    /// Host to bind to (default: 0.0.0.0)
    pub host: String,

    /// Port to listen on (default: 8080)
    pub port: u16,

    /// Maximum request body size in bytes (default: 10MB)
    pub max_body_size: usize,

    /// Request timeout in seconds (default: 30)
    pub request_timeout_secs: u64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RedisConfig {
    /// Redis connection URL
    pub url: String,

    /// Connection pool size (default: 10)
    pub pool_size: usize,

    /// Connection timeout in milliseconds (default: 1000)
    pub connection_timeout_ms: u64,

    /// Command timeout in milliseconds (default: 100)
    pub command_timeout_ms: u64,

    /// Default cache TTL in seconds (default: 3600 = 1 hour)
    pub cache_ttl_secs: u64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SecurityConfig {
    /// Enable PII detection (default: true)
    pub enable_pii_detection: bool,

    /// Enable prompt injection detection (default: true)
    pub enable_injection_detection: bool,

    /// Block requests on high-risk injection (default: true)
    pub block_on_high_risk: bool,

    /// Alert on critical security events (default: true)
    pub alert_on_critical: bool,

    /// Maximum query length in characters (default: 10000)
    pub max_query_length: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RateLimitConfig {
    /// Enable rate limiting (default: true)
    pub enabled: bool,

    /// Free tier: requests per minute (default: 10)
    pub free_tier_rpm: usize,

    /// Basic tier: requests per minute (default: 60)
    pub basic_tier_rpm: usize,

    /// Pro tier: requests per minute (default: 300)
    pub pro_tier_rpm: usize,

    /// Token bucket capacity (default: 60)
    pub capacity: usize,

    /// Token refill rate per second (default: 1.0)
    pub refill_rate: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PerformanceConfig {
    /// Maximum concurrent requests (default: 1000)
    pub max_concurrent_requests: usize,

    /// Worker threads (default: number of CPU cores)
    pub worker_threads: usize,
}

#[derive(Debug, Clone, Deserialize)]
pub struct LoggingConfig {
    /// Log level: trace, debug, info, warn, error (default: info)
    pub level: String,

    /// Log format: json or pretty (default: json)
    pub format: String,
}

impl Config {
    /// Load configuration from environment variables
    pub fn from_env() -> Result<Self, config::ConfigError> {
        let config = config::Config::builder()
            // Server defaults
            .set_default("server.host", "0.0.0.0")?
            .set_default("server.port", 8080)?
            .set_default("server.max_body_size", 10_485_760)? // 10MB
            .set_default("server.request_timeout_secs", 30)?
            // Redis defaults
            .set_default("redis.url", "redis://localhost:6379")?
            .set_default("redis.pool_size", 10)?
            .set_default("redis.connection_timeout_ms", 1000)?
            .set_default("redis.command_timeout_ms", 100)?
            .set_default("redis.cache_ttl_secs", 3600)?
            // Security defaults
            .set_default("security.enable_pii_detection", true)?
            .set_default("security.enable_injection_detection", true)?
            .set_default("security.block_on_high_risk", true)?
            .set_default("security.alert_on_critical", true)?
            .set_default("security.max_query_length", 10000)?
            // Rate limiting defaults
            .set_default("rate_limit.enabled", true)?
            .set_default("rate_limit.free_tier_rpm", 10)?
            .set_default("rate_limit.basic_tier_rpm", 60)?
            .set_default("rate_limit.pro_tier_rpm", 300)?
            .set_default("rate_limit.capacity", 60)?
            .set_default("rate_limit.refill_rate", 1.0)?
            // Performance defaults
            .set_default("performance.max_concurrent_requests", 1000)?
            .set_default("performance.worker_threads", num_cpus::get() as i64)?
            // Logging defaults
            .set_default("logging.level", "info")?
            .set_default("logging.format", "json")?
            // Override with environment variables, prefix REFLEX_, section separator `__`.
            //
            // The separator was `_`, which made most of this struct unreachable. With a
            // single underscore the crate cannot tell a section boundary from a word
            // boundary, so `REFLEX_REDIS_POOL_SIZE` resolved to `redis.pool.size` rather
            // than `redis.pool_size`, and `REFLEX_RATE_LIMIT_ENABLED` to
            // `rate.limit.enabled` -- meaning the ENTIRE rate_limit section, every
            // security field, and every multi-word field elsewhere could not be set by
            // any environment variable at all. Five of twenty-four fields were reachable.
            //
            // With `__` the section is explicit: REFLEX_RATE_LIMIT__FREE_TIER_RPM.
            // `prefix_separator` is set independently: without it the crate reuses
            // `separator` for the prefix too and expects REFLEX__SERVER__PORT.
            .add_source(
                config::Environment::with_prefix("REFLEX")
                    .prefix_separator("_")
                    .separator("__"),
            )
            .build()?;

        config.try_deserialize()
    }
}

impl ServerConfig {
    /// Get bind address (host:port)
    pub fn bind_address(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }

    /// Get request timeout as Duration
    pub fn request_timeout(&self) -> Duration {
        Duration::from_secs(self.request_timeout_secs)
    }
}

impl RedisConfig {
    /// Get connection timeout as Duration
    pub fn connection_timeout(&self) -> Duration {
        Duration::from_millis(self.connection_timeout_ms)
    }

    /// Get command timeout as Duration
    pub fn command_timeout(&self) -> Duration {
        Duration::from_millis(self.command_timeout_ms)
    }

    /// Get cache TTL as Duration
    pub fn cache_ttl(&self) -> Duration {
        Duration::from_secs(self.cache_ttl_secs)
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    /// Serialises the tests that mutate process-global environment variables.
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    use super::*;

    /// Guards the separator. This is the test that would have caught the original
    /// `_` separator: with it, every assertion below fails because the variable
    /// resolves to a nested key that does not exist and the default survives.
    #[test]
    fn env_vars_reach_multi_word_and_sectioned_fields() {
        // Env is process-global; keep the mutating tests serialised against each other.
        let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());

        let vars = [
            ("REFLEX_SERVER__PORT", "9191"),
            ("REFLEX_SERVER__MAX_BODY_SIZE", "2048"),
            ("REFLEX_REDIS__POOL_SIZE", "42"),
            ("REFLEX_REDIS__CACHE_TTL_SECS", "77"),
            ("REFLEX_SECURITY__ENABLE_PII_DETECTION", "false"),
            ("REFLEX_SECURITY__MAX_QUERY_LENGTH", "1234"),
            ("REFLEX_RATE_LIMIT__ENABLED", "false"),
            ("REFLEX_RATE_LIMIT__FREE_TIER_RPM", "7"),
        ];
        for (k, v) in vars {
            std::env::set_var(k, v);
        }

        let config = Config::from_env().expect("config should load");

        for (k, _) in vars {
            std::env::remove_var(k);
        }

        assert_eq!(config.server.port, 9191, "single-word field in a section");
        assert_eq!(config.server.max_body_size, 2048, "multi-word field");
        assert_eq!(config.redis.pool_size, 42, "multi-word field");
        assert_eq!(config.redis.cache_ttl_secs, 77, "multi-word field");
        assert!(!config.security.enable_pii_detection, "security section");
        assert_eq!(config.security.max_query_length, 1234, "security section");
        assert!(!config.rate_limit.enabled, "multi-word SECTION name");
        assert_eq!(
            config.rate_limit.free_tier_rpm, 7,
            "multi-word section AND field"
        );
    }

    #[test]
    fn test_default_config() {
        // Takes the same lock as the env-mutating test. Without it the two race:
        // cargo runs them on threads of one process, so REFLEX_SERVER__PORT set by
        // the other test leaks in here and this one fails asserting the default.
        let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());

        // Test that default configuration loads
        let config = Config::from_env();
        assert!(
            config.is_ok(),
            "Default configuration should load successfully"
        );

        let config = config.unwrap();
        assert_eq!(config.server.port, 8080);
        assert_eq!(config.redis.pool_size, 10);
        assert!(config.security.enable_pii_detection);
    }

    #[test]
    fn test_bind_address() {
        let server_config = ServerConfig {
            host: "127.0.0.1".to_string(),
            port: 9000,
            max_body_size: 1024,
            request_timeout_secs: 10,
        };

        assert_eq!(server_config.bind_address(), "127.0.0.1:9000");
    }
}
