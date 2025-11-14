//! Redis-backed cache implementation
//!
//! Provides a production-ready Redis cache with connection pooling, retry logic,
//! TTL management, and pattern-based invalidation.

use crate::cache::types::{Cache, CacheError, CacheStats, CacheTTL};
use crate::redis_client::RedisClient;
use async_trait::async_trait;
use redis::AsyncCommands;
use std::sync::Arc;
use tracing::{debug, error};

/// Redis-backed cache implementation
pub struct RedisCache {
    /// Redis client with connection pooling
    redis: Arc<RedisClient>,
    /// Cache statistics tracker
    stats: Arc<CacheStats>,
}

impl RedisCache {
    /// Create a new Redis cache
    ///
    /// # Arguments
    /// * `redis` - Arc to configured RedisClient
    ///
    /// # Returns
    /// * `Self` - New RedisCache instance
    pub fn new(redis: Arc<RedisClient>) -> Self {
        debug!("Creating RedisCache");
        Self {
            redis,
            stats: Arc::new(CacheStats::new()),
        }
    }

    /// Get statistics reference for this cache
    pub fn stats_ref(&self) -> Arc<CacheStats> {
        Arc::clone(&self.stats)
    }
}

#[async_trait]
impl Cache for RedisCache {
    async fn get(&self, key: &str) -> Result<Option<String>, CacheError> {
        debug!("Cache GET: {}", key);

        let mut conn = self.redis.get_connection().await?;

        match conn.get::<_, Option<String>>(key).await {
            Ok(Some(value)) => {
                self.stats.record_hit();
                debug!("Cache HIT: {}", key);
                Ok(Some(value))
            }
            Ok(None) => {
                self.stats.record_miss();
                debug!("Cache MISS: {}", key);
                Ok(None)
            }
            Err(e) => {
                self.stats.record_error();
                error!("Cache GET error for key {}: {}", key, e);
                Err(CacheError::Redis(e))
            }
        }
    }

    async fn set(&self, key: &str, value: &str, ttl: CacheTTL) -> Result<(), CacheError> {
        debug!("Cache SET: {} (TTL: {:?})", key, ttl);

        let mut conn = self.redis.get_connection().await?;

        let result = match ttl.as_seconds() {
            Some(seconds) => {
                // Set with expiration using SETEX
                conn.set_ex::<_, _, ()>(key, value, seconds as u64).await
            }
            None => {
                // Set without expiration
                conn.set::<_, _, ()>(key, value).await
            }
        };

        match result {
            Ok(_) => {
                self.stats.record_set();
                debug!("Cache SET successful: {}", key);
                Ok(())
            }
            Err(e) => {
                self.stats.record_error();
                error!("Cache SET error for key {}: {}", key, e);
                Err(CacheError::Redis(e))
            }
        }
    }

    async fn delete(&self, key: &str) -> Result<(), CacheError> {
        debug!("Cache DELETE: {}", key);

        let mut conn = self.redis.get_connection().await?;

        match conn.del::<_, ()>(key).await {
            Ok(_) => {
                self.stats.record_delete();
                debug!("Cache DELETE successful: {}", key);
                Ok(())
            }
            Err(e) => {
                self.stats.record_error();
                error!("Cache DELETE error for key {}: {}", key, e);
                Err(CacheError::Redis(e))
            }
        }
    }

    async fn exists(&self, key: &str) -> Result<bool, CacheError> {
        debug!("Cache EXISTS: {}", key);

        let mut conn = self.redis.get_connection().await?;

        match conn.exists::<_, bool>(key).await {
            Ok(exists) => {
                debug!("Cache EXISTS result for {}: {}", key, exists);
                Ok(exists)
            }
            Err(e) => {
                self.stats.record_error();
                error!("Cache EXISTS error for key {}: {}", key, e);
                Err(CacheError::Redis(e))
            }
        }
    }

    async fn invalidate_pattern(&self, pattern: &str) -> Result<u64, CacheError> {
        use crate::cache::key::validate_cache_pattern;

        debug!("Cache INVALIDATE pattern: {}", pattern);

        // Validate pattern for safety
        validate_cache_pattern(pattern)?;

        let mut conn = self.redis.get_connection().await?;

        // Use KEYS for simplicity (note: blocks Redis, consider SCAN for production at scale)
        let keys: Vec<String> = match conn.keys(pattern).await {
            Ok(keys) => keys,
            Err(e) => {
                self.stats.record_error();
                error!("Cache pattern lookup error: {}", e);
                return Err(CacheError::Redis(e));
            }
        };

        if keys.is_empty() {
            debug!("No keys found matching pattern: {}", pattern);
            return Ok(0);
        }

        let count = keys.len() as u64;
        debug!("Found {} keys matching pattern: {}", count, pattern);

        // Delete all matching keys
        match conn.del::<_, ()>(&keys).await {
            Ok(_) => {
                for _ in 0..count {
                    self.stats.record_delete();
                }
                debug!(
                    "Successfully invalidated {} keys matching pattern: {}",
                    count, pattern
                );
                Ok(count)
            }
            Err(e) => {
                self.stats.record_error();
                error!("Cache bulk DELETE error: {}", e);
                Err(CacheError::Redis(e))
            }
        }
    }

    fn stats(&self) -> &CacheStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cache::key::generate_cache_key;
    use crate::config::RedisConfig;

    fn test_redis_config() -> RedisConfig {
        RedisConfig {
            url: "redis://localhost:6379".to_string(),
            pool_size: 10,
            connection_timeout_ms: 5000,
            command_timeout_ms: 3000,
            cache_ttl_secs: 300,
        }
    }

    async fn setup_cache() -> Result<RedisCache, CacheError> {
        let config = test_redis_config();
        let redis = RedisClient::new(config)
            .map_err(|e| CacheError::Pool(format!("Failed to create Redis client: {}", e)))?;
        Ok(RedisCache::new(Arc::new(redis)))
    }

    #[tokio::test]
    #[ignore] // Requires Redis to be running
    async fn test_cache_set_and_get() {
        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "set_get").unwrap();

        // Set a value
        cache.set(&key, "test_value", CacheTTL::Short).await.unwrap();

        // Get the value
        let result = cache.get(&key).await.unwrap();
        assert_eq!(result, Some("test_value".to_string()));

        // Cleanup
        cache.delete(&key).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_miss() {
        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "nonexistent").unwrap();

        let result = cache.get(&key).await.unwrap();
        assert_eq!(result, None);
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_delete() {
        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "delete").unwrap();

        // Set a value
        cache.set(&key, "value", CacheTTL::Medium).await.unwrap();

        // Verify it exists
        assert!(cache.exists(&key).await.unwrap());

        // Delete it
        cache.delete(&key).await.unwrap();

        // Verify it's gone
        assert!(!cache.exists(&key).await.unwrap());
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_exists() {
        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "exists").unwrap();

        // Key should not exist initially
        assert!(!cache.exists(&key).await.unwrap());

        // Set a value
        cache.set(&key, "value", CacheTTL::Medium).await.unwrap();

        // Now it should exist
        assert!(cache.exists(&key).await.unwrap());

        // Cleanup
        cache.delete(&key).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_ttl_expiry() {
        use tokio::time::{sleep, Duration};

        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "ttl_expiry").unwrap();

        // Set with 1-second TTL
        cache
            .set(&key, "expires_soon", CacheTTL::Custom(1))
            .await
            .unwrap();

        // Should exist immediately
        assert!(cache.exists(&key).await.unwrap());

        // Wait for expiry
        sleep(Duration::from_secs(2)).await;

        // Should be expired now
        assert!(!cache.exists(&key).await.unwrap());
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_persistent_no_expiry() {
        use tokio::time::{sleep, Duration};

        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "persistent").unwrap();

        // Set with no expiry
        cache
            .set(&key, "never_expires", CacheTTL::Persistent)
            .await
            .unwrap();

        // Wait a bit
        sleep(Duration::from_millis(500)).await;

        // Should still exist
        assert!(cache.exists(&key).await.unwrap());

        // Cleanup
        cache.delete(&key).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_invalidate_pattern() {
        let cache = setup_cache().await.unwrap();

        // Set multiple keys with same prefix
        let keys = vec![
            ("test:pattern:key1", "value1"),
            ("test:pattern:key2", "value2"),
            ("test:pattern:key3", "value3"),
            ("test:other:key4", "value4"), // Different prefix
        ];

        for (key, value) in &keys {
            cache.set(key, value, CacheTTL::Medium).await.unwrap();
        }

        // Invalidate only test:pattern:* keys
        let deleted = cache.invalidate_pattern("test:pattern:*").await.unwrap();

        assert_eq!(deleted, 3);

        // Verify pattern keys are gone
        assert!(!cache.exists("test:pattern:key1").await.unwrap());
        assert!(!cache.exists("test:pattern:key2").await.unwrap());
        assert!(!cache.exists("test:pattern:key3").await.unwrap());

        // Verify other key still exists
        assert!(cache.exists("test:other:key4").await.unwrap());

        // Cleanup
        cache.delete("test:other:key4").await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_stats() {
        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "stats").unwrap();

        // Reset stats
        cache.stats().reset();

        // Perform operations
        cache.set(&key, "value", CacheTTL::Short).await.unwrap(); // +1 set
        cache.get(&key).await.unwrap(); // +1 hit
        cache.get("nonexistent").await.unwrap(); // +1 miss
        cache.delete(&key).await.unwrap(); // +1 delete

        // Check stats
        let stats = cache.stats().snapshot();
        assert_eq!(stats.sets, 1);
        assert_eq!(stats.hits, 1);
        assert_eq!(stats.misses, 1);
        assert_eq!(stats.deletes, 1);
        assert_eq!(stats.hit_rate, 0.5); // 1 hit / (1 hit + 1 miss)
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_overwrite() {
        let cache = setup_cache().await.unwrap();
        let key = generate_cache_key("test", "overwrite").unwrap();

        // Set initial value
        cache.set(&key, "value1", CacheTTL::Medium).await.unwrap();

        // Overwrite with new value
        cache.set(&key, "value2", CacheTTL::Medium).await.unwrap();

        // Verify new value
        let result = cache.get(&key).await.unwrap();
        assert_eq!(result, Some("value2".to_string()));

        // Cleanup
        cache.delete(&key).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_cache_different_ttls() {
        let cache = setup_cache().await.unwrap();

        let keys_ttls = vec![
            (
                generate_cache_key("test", "short").unwrap(),
                CacheTTL::Short,
            ),
            (
                generate_cache_key("test", "medium").unwrap(),
                CacheTTL::Medium,
            ),
            (
                generate_cache_key("test", "long").unwrap(),
                CacheTTL::Long,
            ),
        ];

        // Set with different TTLs
        for (key, ttl) in &keys_ttls {
            cache.set(key, "value", *ttl).await.unwrap();
        }

        // All should exist
        for (key, _) in &keys_ttls {
            assert!(cache.exists(key).await.unwrap());
        }

        // Cleanup
        for (key, _) in &keys_ttls {
            cache.delete(key).await.unwrap();
        }
    }
}
