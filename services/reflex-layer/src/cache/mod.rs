//! Caching module for the Reflex Layer
//!
//! Provides Redis-backed caching with TTL management, pattern invalidation,
//! and comprehensive statistics tracking for performance optimization.

pub mod key;
pub mod redis_cache;
pub mod types;

// Re-export commonly used items
pub use key::{
    generate_cache_key, generate_cache_key_fast, generate_custom_cache_key, validate_cache_pattern,
    DEFAULT_NAMESPACE,
};
pub use redis_cache::RedisCache;
pub use types::{Cache, CacheError, CacheStats, CacheStatsSnapshot, CacheTTL};
