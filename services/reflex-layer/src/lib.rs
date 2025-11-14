//! OctoLLM Reflex Layer Library
//!
//! This library provides PII detection, prompt injection detection, caching,
//! rate limiting, and other reflex layer functionality that can be used both
//! by the server and in tests.

pub mod cache;
pub mod config;
pub mod error;
pub mod injection;
pub mod pii;
pub mod ratelimit;
pub mod redis_client;

// Re-export commonly used items
pub use cache::{Cache, CacheError, CacheStats, CacheTTL, RedisCache, generate_cache_key};
pub use injection::{
    DetectionMode, InjectionConfig, InjectionDetector, InjectionMatch, InjectionType, Severity,
};
pub use pii::{PIIConfig, PIIDetector, PIIMatch, PIIType, PatternSet, RedactionStrategy, redact};
pub use ratelimit::{
    MultiDimensionalRateLimiter, RateLimitConfig, RateLimitError, RateLimitKey,
    RateLimitResult, RateLimitTier, RedisRateLimiter, TokenBucket,
};
