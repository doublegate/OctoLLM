//! Cache types and traits for the Reflex Layer
//!
//! Defines the core caching abstractions including TTL management, cache operations,
//! and statistics tracking.

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, Ordering};
use thiserror::Error;

/// Time-to-live (TTL) configuration for cache entries
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum CacheTTL {
    /// Short-lived cache entry (60 seconds)
    Short,
    /// Medium-lived cache entry (300 seconds / 5 minutes) - Default
    #[default]
    Medium,
    /// Long-lived cache entry (3600 seconds / 1 hour)
    Long,
    /// Persistent entry with no automatic expiration
    Persistent,
    /// Custom TTL in seconds
    Custom(u64),
}

impl CacheTTL {
    /// Convert TTL to seconds
    ///
    /// # Returns
    /// * `Some(u64)` - Number of seconds for the TTL
    /// * `None` - For persistent entries (no expiration)
    pub fn as_seconds(&self) -> Option<u64> {
        match self {
            CacheTTL::Short => Some(60),
            CacheTTL::Medium => Some(300),
            CacheTTL::Long => Some(3600),
            CacheTTL::Persistent => None,
            CacheTTL::Custom(secs) => Some(*secs),
        }
    }

    /// Get human-readable description of TTL
    pub fn description(&self) -> String {
        match self {
            CacheTTL::Short => "1 minute".to_string(),
            CacheTTL::Medium => "5 minutes".to_string(),
            CacheTTL::Long => "1 hour".to_string(),
            CacheTTL::Persistent => "No expiration".to_string(),
            CacheTTL::Custom(secs) => format!("{} seconds", secs),
        }
    }
}

/// Cache operation errors
#[derive(Error, Debug)]
pub enum CacheError {
    /// Redis connection or operation error
    #[error("Redis error: {0}")]
    Redis(#[from] redis::RedisError),

    /// Serialization/deserialization error
    #[error("Serialization error: {0}")]
    Serialization(String),

    /// Connection pool error
    #[error("Connection pool error: {0}")]
    Pool(String),

    /// Key generation error
    #[error("Key generation error: {0}")]
    KeyGeneration(String),

    /// Operation timeout
    #[error("Operation timeout after {0}ms")]
    Timeout(u64),

    /// Invalid pattern for invalidation
    #[error("Invalid pattern: {0}")]
    InvalidPattern(String),

    /// Reflex error (for compatibility with main error type)
    #[error("Reflex error: {0}")]
    Reflex(String),
}

// Convert ReflexError to CacheError for compatibility
impl From<crate::error::ReflexError> for CacheError {
    fn from(err: crate::error::ReflexError) -> Self {
        match err {
            crate::error::ReflexError::Redis(e) => CacheError::Redis(e),
            other => CacheError::Reflex(other.to_string()),
        }
    }
}

/// Cache statistics for monitoring and optimization
#[derive(Debug, Default)]
pub struct CacheStats {
    /// Total number of cache hits
    pub hits: AtomicU64,
    /// Total number of cache misses
    pub misses: AtomicU64,
    /// Total number of set operations
    pub sets: AtomicU64,
    /// Total number of delete operations
    pub deletes: AtomicU64,
    /// Total number of errors
    pub errors: AtomicU64,
}

impl CacheStats {
    /// Create new cache statistics tracker
    pub fn new() -> Self {
        Self::default()
    }

    /// Calculate cache hit rate
    ///
    /// # Returns
    /// Hit rate as a float between 0.0 and 1.0
    pub fn hit_rate(&self) -> f64 {
        let hits = self.hits.load(Ordering::Relaxed) as f64;
        let misses = self.misses.load(Ordering::Relaxed) as f64;
        let total = hits + misses;

        if total == 0.0 {
            0.0
        } else {
            hits / total
        }
    }

    /// Calculate cache miss rate
    ///
    /// # Returns
    /// Miss rate as a float between 0.0 and 1.0
    pub fn miss_rate(&self) -> f64 {
        1.0 - self.hit_rate()
    }

    /// Get total number of cache operations (hits + misses)
    pub fn total_operations(&self) -> u64 {
        self.hits.load(Ordering::Relaxed) + self.misses.load(Ordering::Relaxed)
    }

    /// Get total number of write operations
    pub fn total_writes(&self) -> u64 {
        self.sets.load(Ordering::Relaxed) + self.deletes.load(Ordering::Relaxed)
    }

    /// Record a cache hit
    pub fn record_hit(&self) {
        self.hits.fetch_add(1, Ordering::Relaxed);
    }

    /// Record a cache miss
    pub fn record_miss(&self) {
        self.misses.fetch_add(1, Ordering::Relaxed);
    }

    /// Record a set operation
    pub fn record_set(&self) {
        self.sets.fetch_add(1, Ordering::Relaxed);
    }

    /// Record a delete operation
    pub fn record_delete(&self) {
        self.deletes.fetch_add(1, Ordering::Relaxed);
    }

    /// Record an error
    pub fn record_error(&self) {
        self.errors.fetch_add(1, Ordering::Relaxed);
    }

    /// Reset all statistics
    pub fn reset(&self) {
        self.hits.store(0, Ordering::Relaxed);
        self.misses.store(0, Ordering::Relaxed);
        self.sets.store(0, Ordering::Relaxed);
        self.deletes.store(0, Ordering::Relaxed);
        self.errors.store(0, Ordering::Relaxed);
    }

    /// Get snapshot of current statistics
    pub fn snapshot(&self) -> CacheStatsSnapshot {
        CacheStatsSnapshot {
            hits: self.hits.load(Ordering::Relaxed),
            misses: self.misses.load(Ordering::Relaxed),
            sets: self.sets.load(Ordering::Relaxed),
            deletes: self.deletes.load(Ordering::Relaxed),
            errors: self.errors.load(Ordering::Relaxed),
            hit_rate: self.hit_rate(),
            miss_rate: self.miss_rate(),
        }
    }
}

/// Snapshot of cache statistics at a point in time
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheStatsSnapshot {
    pub hits: u64,
    pub misses: u64,
    pub sets: u64,
    pub deletes: u64,
    pub errors: u64,
    pub hit_rate: f64,
    pub miss_rate: f64,
}

/// Core cache trait defining all cache operations
#[async_trait]
pub trait Cache: Send + Sync {
    /// Get a value from the cache by key
    ///
    /// # Arguments
    /// * `key` - The cache key to lookup
    ///
    /// # Returns
    /// * `Ok(Some(String))` - Cache hit with the cached value
    /// * `Ok(None)` - Cache miss
    /// * `Err(CacheError)` - Error during operation
    async fn get(&self, key: &str) -> Result<Option<String>, CacheError>;

    /// Set a value in the cache with TTL
    ///
    /// # Arguments
    /// * `key` - The cache key
    /// * `value` - The value to cache
    /// * `ttl` - Time-to-live configuration
    ///
    /// # Returns
    /// * `Ok(())` - Value successfully cached
    /// * `Err(CacheError)` - Error during operation
    async fn set(&self, key: &str, value: &str, ttl: CacheTTL) -> Result<(), CacheError>;

    /// Delete a value from the cache
    ///
    /// # Arguments
    /// * `key` - The cache key to delete
    ///
    /// # Returns
    /// * `Ok(())` - Key successfully deleted (or didn't exist)
    /// * `Err(CacheError)` - Error during operation
    async fn delete(&self, key: &str) -> Result<(), CacheError>;

    /// Check if a key exists in the cache
    ///
    /// # Arguments
    /// * `key` - The cache key to check
    ///
    /// # Returns
    /// * `Ok(true)` - Key exists
    /// * `Ok(false)` - Key does not exist
    /// * `Err(CacheError)` - Error during operation
    async fn exists(&self, key: &str) -> Result<bool, CacheError>;

    /// Invalidate all keys matching a pattern
    ///
    /// # Arguments
    /// * `pattern` - Redis pattern (e.g., "reflex:cache:*")
    ///
    /// # Returns
    /// * `Ok(u64)` - Number of keys deleted
    /// * `Err(CacheError)` - Error during operation
    async fn invalidate_pattern(&self, pattern: &str) -> Result<u64, CacheError>;

    /// Get cache statistics
    fn stats(&self) -> &CacheStats;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cache_ttl_as_seconds() {
        assert_eq!(CacheTTL::Short.as_seconds(), Some(60));
        assert_eq!(CacheTTL::Medium.as_seconds(), Some(300));
        assert_eq!(CacheTTL::Long.as_seconds(), Some(3600));
        assert_eq!(CacheTTL::Persistent.as_seconds(), None);
        assert_eq!(CacheTTL::Custom(1234).as_seconds(), Some(1234));
    }

    #[test]
    fn test_cache_ttl_default() {
        assert_eq!(CacheTTL::default(), CacheTTL::Medium);
    }

    #[test]
    fn test_cache_ttl_description() {
        assert_eq!(CacheTTL::Short.description(), "1 minute");
        assert_eq!(CacheTTL::Medium.description(), "5 minutes");
        assert_eq!(CacheTTL::Long.description(), "1 hour");
        assert_eq!(CacheTTL::Persistent.description(), "No expiration");
        assert_eq!(CacheTTL::Custom(90).description(), "90 seconds");
    }

    #[test]
    fn test_cache_stats_new() {
        let stats = CacheStats::new();
        assert_eq!(stats.hits.load(Ordering::Relaxed), 0);
        assert_eq!(stats.misses.load(Ordering::Relaxed), 0);
        assert_eq!(stats.sets.load(Ordering::Relaxed), 0);
        assert_eq!(stats.deletes.load(Ordering::Relaxed), 0);
        assert_eq!(stats.errors.load(Ordering::Relaxed), 0);
    }

    #[test]
    fn test_cache_stats_hit_rate() {
        let stats = CacheStats::new();
        assert_eq!(stats.hit_rate(), 0.0);

        stats.record_hit();
        assert_eq!(stats.hit_rate(), 1.0);

        stats.record_miss();
        assert_eq!(stats.hit_rate(), 0.5);

        stats.record_hit();
        assert_eq!(stats.hit_rate(), 2.0 / 3.0);
    }

    #[test]
    fn test_cache_stats_miss_rate() {
        let stats = CacheStats::new();
        stats.record_hit();
        stats.record_hit();
        stats.record_miss();

        let miss_rate = stats.miss_rate();
        assert!((miss_rate - 1.0 / 3.0).abs() < 0.0001); // Floating point comparison
    }

    #[test]
    fn test_cache_stats_operations() {
        let stats = CacheStats::new();
        stats.record_hit();
        stats.record_miss();
        stats.record_set();
        stats.record_delete();

        assert_eq!(stats.total_operations(), 2);
        assert_eq!(stats.total_writes(), 2);
    }

    #[test]
    fn test_cache_stats_reset() {
        let stats = CacheStats::new();
        stats.record_hit();
        stats.record_miss();
        stats.record_set();

        stats.reset();

        assert_eq!(stats.hits.load(Ordering::Relaxed), 0);
        assert_eq!(stats.misses.load(Ordering::Relaxed), 0);
        assert_eq!(stats.sets.load(Ordering::Relaxed), 0);
    }

    #[test]
    fn test_cache_stats_snapshot() {
        let stats = CacheStats::new();
        stats.record_hit();
        stats.record_hit();
        stats.record_miss();

        let snapshot = stats.snapshot();
        assert_eq!(snapshot.hits, 2);
        assert_eq!(snapshot.misses, 1);
        assert_eq!(snapshot.hit_rate, 2.0 / 3.0);
    }
}
