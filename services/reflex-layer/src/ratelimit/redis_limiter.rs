//! Redis-backed distributed rate limiter
//!
//! Provides distributed rate limiting using Redis with atomic Lua scripts.
//! Supports multi-dimensional rate limiting (user, IP, endpoint, global).

use crate::ratelimit::types::{
    RateLimitConfig, RateLimitError, RateLimitKey, RateLimitReason, RateLimitResult,
};
use crate::redis_client::RedisClient;
use redis::Script;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tracing::{debug, error};

/// Redis-backed distributed rate limiter
pub struct RedisRateLimiter {
    /// Redis client with connection pooling
    redis: Arc<RedisClient>,
    /// Compiled Lua script for atomic token bucket operations
    script: Script,
}

impl RedisRateLimiter {
    /// Create a new Redis rate limiter
    ///
    /// # Arguments
    /// * `redis` - Arc to configured RedisClient
    ///
    /// # Returns
    /// * `Self` - New RedisRateLimiter instance
    pub fn new(redis: Arc<RedisClient>) -> Self {
        debug!("Creating RedisRateLimiter");

        // Load the Lua script
        let lua_script = include_str!("token_bucket.lua");
        let script = Script::new(lua_script);

        Self { redis, script }
    }

    /// Check rate limit for a given key
    ///
    /// # Arguments
    /// * `key` - Rate limit key (user, IP, endpoint, etc.)
    /// * `config` - Rate limit configuration
    /// * `tokens_to_consume` - Number of tokens to consume (typically 1.0)
    ///
    /// # Returns
    /// * `Ok(RateLimitResult)` - Result of rate limit check
    /// * `Err(RateLimitError)` - Error during operation
    pub async fn check_rate_limit(
        &self,
        key: &RateLimitKey,
        config: &RateLimitConfig,
        tokens_to_consume: f64,
    ) -> Result<RateLimitResult, RateLimitError> {
        let redis_key = key.to_redis_key();
        debug!(
            "Rate limit check: key={}, capacity={}, refill_rate={}, consume={}",
            redis_key, config.capacity, config.refill_rate, tokens_to_consume
        );

        let mut conn = self.redis.get_connection().await?;

        // Get current timestamp in milliseconds
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|e| RateLimitError::Internal(format!("Time error: {}", e)))?
            .as_millis() as u64;

        // Execute Lua script
        let result: Vec<i64> = self
            .script
            .key(&redis_key)
            .arg(config.capacity)
            .arg(config.refill_rate)
            .arg(tokens_to_consume)
            .arg(now)
            .invoke_async(&mut *conn)
            .await
            .map_err(|e| {
                error!("Lua script execution failed: {}", e);
                RateLimitError::ScriptError(format!("Script execution error: {}", e))
            })?;

        // Parse result
        let allowed = result[0] == 1;
        let current_tokens = result[1] as f64;
        let time_ms = result[2] as u64;

        if allowed {
            debug!("Rate limit ALLOWED: remaining={}", current_tokens);
            Ok(RateLimitResult::Allowed {
                remaining: current_tokens,
                reset_after_ms: time_ms,
            })
        } else {
            debug!(
                "Rate limit DENIED: current={}, retry_after={}ms",
                current_tokens, time_ms
            );
            Ok(RateLimitResult::Limited {
                reason: RateLimitReason::Custom,
                retry_after_ms: time_ms,
                current_tokens,
            })
        }
    }

    /// Reset rate limit for a key (clear all tokens)
    ///
    /// # Arguments
    /// * `key` - Rate limit key to reset
    ///
    /// # Returns
    /// * `Ok(())` - Successfully reset
    /// * `Err(RateLimitError)` - Error during operation
    pub async fn reset(&self, key: &RateLimitKey) -> Result<(), RateLimitError> {
        use redis::AsyncCommands;

        let redis_key = key.to_redis_key();
        debug!("Resetting rate limit: {}", redis_key);

        let mut conn = self.redis.get_connection().await?;

        conn.del::<_, ()>(&redis_key)
            .await
            .map_err(RateLimitError::Redis)?;

        Ok(())
    }
}

/// Multi-dimensional rate limiter
///
/// Checks rate limits across multiple dimensions (user, IP, endpoint, global)
/// and returns the first exceeded limit or allows the request.
pub struct MultiDimensionalRateLimiter {
    limiter: Arc<RedisRateLimiter>,
    user_config: RateLimitConfig,
    ip_config: RateLimitConfig,
    endpoint_config: RateLimitConfig,
    global_config: RateLimitConfig,
}

impl MultiDimensionalRateLimiter {
    /// Create a new multi-dimensional rate limiter
    ///
    /// # Arguments
    /// * `limiter` - Arc to RedisRateLimiter
    /// * `user_config` - Rate limit config for per-user limits
    /// * `ip_config` - Rate limit config for per-IP limits
    /// * `endpoint_config` - Rate limit config for per-endpoint limits
    /// * `global_config` - Rate limit config for global limits
    pub fn new(
        limiter: Arc<RedisRateLimiter>,
        user_config: RateLimitConfig,
        ip_config: RateLimitConfig,
        endpoint_config: RateLimitConfig,
        global_config: RateLimitConfig,
    ) -> Self {
        Self {
            limiter,
            user_config,
            ip_config,
            endpoint_config,
            global_config,
        }
    }

    /// Check all rate limits
    ///
    /// Checks in order: user -> IP -> endpoint -> global
    /// Returns immediately on first limit exceeded.
    ///
    /// # Arguments
    /// * `user_id` - Optional user identifier
    /// * `ip` - IP address
    /// * `endpoint` - Endpoint being accessed
    ///
    /// # Returns
    /// * `Ok(RateLimitResult::Allowed)` - All checks passed
    /// * `Ok(RateLimitResult::Limited)` - One check failed
    /// * `Err(RateLimitError)` - Error during checks
    pub async fn check_all(
        &self,
        user_id: Option<&str>,
        ip: &str,
        endpoint: &str,
    ) -> Result<RateLimitResult, RateLimitError> {
        // Check user limit if user_id provided
        if let Some(uid) = user_id {
            let key = RateLimitKey::User(uid.to_string());
            let result = self
                .limiter
                .check_rate_limit(&key, &self.user_config, 1.0)
                .await?;

            if result.is_limited() {
                if let RateLimitResult::Limited {
                    retry_after_ms,
                    current_tokens,
                    ..
                } = result
                {
                    return Ok(RateLimitResult::Limited {
                        reason: RateLimitReason::UserQuota,
                        retry_after_ms,
                        current_tokens,
                    });
                }
            }
        }

        // Check IP limit
        let ip_key = RateLimitKey::IP(ip.to_string());
        let result = self
            .limiter
            .check_rate_limit(&ip_key, &self.ip_config, 1.0)
            .await?;

        if result.is_limited() {
            if let RateLimitResult::Limited {
                retry_after_ms,
                current_tokens,
                ..
            } = result
            {
                return Ok(RateLimitResult::Limited {
                    reason: RateLimitReason::IPQuota,
                    retry_after_ms,
                    current_tokens,
                });
            }
        }

        // Check endpoint limit
        let endpoint_key = RateLimitKey::Endpoint(endpoint.to_string());
        let result = self
            .limiter
            .check_rate_limit(&endpoint_key, &self.endpoint_config, 1.0)
            .await?;

        if result.is_limited() {
            if let RateLimitResult::Limited {
                retry_after_ms,
                current_tokens,
                ..
            } = result
            {
                return Ok(RateLimitResult::Limited {
                    reason: RateLimitReason::EndpointQuota,
                    retry_after_ms,
                    current_tokens,
                });
            }
        }

        // Check global limit
        let global_key = RateLimitKey::Global;
        let result = self
            .limiter
            .check_rate_limit(&global_key, &self.global_config, 1.0)
            .await?;

        if result.is_limited() {
            if let RateLimitResult::Limited {
                retry_after_ms,
                current_tokens,
                ..
            } = result
            {
                return Ok(RateLimitResult::Limited {
                    reason: RateLimitReason::GlobalQuota,
                    retry_after_ms,
                    current_tokens,
                });
            }
        }

        // All checks passed
        Ok(RateLimitResult::Allowed {
            remaining: 0.0, // Don't expose internal state
            reset_after_ms: 0,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
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

    async fn setup_limiter() -> Result<RedisRateLimiter, RateLimitError> {
        let config = test_redis_config();
        let redis = RedisClient::new(config)
            .map_err(|e| RateLimitError::Config(format!("Failed to create Redis client: {}", e)))?;
        Ok(RedisRateLimiter::new(Arc::new(redis)))
    }

    #[tokio::test]
    #[ignore] // Requires Redis
    async fn test_rate_limit_allow() {
        let limiter = setup_limiter().await.unwrap();
        let key = RateLimitKey::User("test_user_allow".to_string());
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };

        // First request should succeed
        let result = limiter.check_rate_limit(&key, &config, 1.0).await.unwrap();
        assert!(result.is_allowed());

        // Cleanup
        limiter.reset(&key).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_rate_limit_deny() {
        let limiter = setup_limiter().await.unwrap();
        let key = RateLimitKey::User("test_user_deny".to_string());
        let config = RateLimitConfig {
            capacity: 5,
            refill_rate: 0.1, // Very slow refill
        };

        // Consume all tokens
        for _ in 0..5 {
            let result = limiter.check_rate_limit(&key, &config, 1.0).await.unwrap();
            assert!(result.is_allowed());
        }

        // Next request should be denied
        let result = limiter.check_rate_limit(&key, &config, 1.0).await.unwrap();
        assert!(result.is_limited());

        // Cleanup
        limiter.reset(&key).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_rate_limit_reset() {
        let limiter = setup_limiter().await.unwrap();
        let key = RateLimitKey::User("test_user_reset".to_string());
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };

        // Consume all tokens
        for _ in 0..10 {
            limiter.check_rate_limit(&key, &config, 1.0).await.unwrap();
        }

        // Reset
        limiter.reset(&key).await.unwrap();

        // Should be able to consume again
        let result = limiter.check_rate_limit(&key, &config, 1.0).await.unwrap();
        assert!(result.is_allowed());

        // Cleanup
        limiter.reset(&key).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_rate_limit_different_keys() {
        let limiter = setup_limiter().await.unwrap();
        let config = RateLimitConfig {
            capacity: 5,
            refill_rate: 1.0,
        };

        let key1 = RateLimitKey::User("user1".to_string());
        let key2 = RateLimitKey::User("user2".to_string());

        // Consume all tokens for key1
        for _ in 0..5 {
            limiter.check_rate_limit(&key1, &config, 1.0).await.unwrap();
        }

        // key1 should be limited
        assert!(limiter
            .check_rate_limit(&key1, &config, 1.0)
            .await
            .unwrap()
            .is_limited());

        // key2 should still work
        assert!(limiter
            .check_rate_limit(&key2, &config, 1.0)
            .await
            .unwrap()
            .is_allowed());

        // Cleanup
        limiter.reset(&key1).await.unwrap();
        limiter.reset(&key2).await.unwrap();
    }

    #[tokio::test]
    #[ignore]
    async fn test_multi_dimensional_limiter() {
        let limiter = Arc::new(setup_limiter().await.unwrap());

        let multi = MultiDimensionalRateLimiter::new(
            limiter,
            RateLimitConfig {
                capacity: 10,
                refill_rate: 1.0,
            }, // User
            RateLimitConfig {
                capacity: 50,
                refill_rate: 5.0,
            }, // IP
            RateLimitConfig {
                capacity: 100,
                refill_rate: 10.0,
            }, // Endpoint
            RateLimitConfig {
                capacity: 1000,
                refill_rate: 100.0,
            }, // Global
        );

        let result = multi
            .check_all(Some("user123"), "192.168.1.1", "/api/test")
            .await
            .unwrap();
        assert!(result.is_allowed());
    }
}
