//! Redis client module for the Reflex Layer
//!
//! Provides connection pooling, retry logic, and health checking for Redis.

use deadpool_redis::{Config as PoolConfig, Connection, Pool, Runtime};
use std::time::Duration;
use tokio::time::sleep;
use tracing::{debug, error, warn};

use crate::config::RedisConfig;
use crate::error::{ReflexError, ReflexResult};

/// Redis client with connection pooling and retry logic
#[derive(Clone)]
pub struct RedisClient {
    pool: Pool,
    config: RedisConfig,
}

impl RedisClient {
    /// Create a new Redis client from configuration
    ///
    /// # Arguments
    /// * `config` - Redis configuration including URL, pool size, and timeouts
    ///
    /// # Returns
    /// * `Result<Self>` - Redis client or error
    pub fn new(config: RedisConfig) -> ReflexResult<Self> {
        debug!("Creating Redis connection pool");

        // Create deadpool-redis configuration
        let pool_config = PoolConfig {
            url: Some(config.url.clone()),
            pool: Some(deadpool_redis::PoolConfig {
                max_size: config.pool_size,
                timeouts: deadpool_redis::Timeouts {
                    wait: Some(Duration::from_millis(config.connection_timeout_ms)),
                    create: Some(Duration::from_millis(config.connection_timeout_ms)),
                    recycle: Some(Duration::from_millis(config.connection_timeout_ms)),
                },
                queue_mode: deadpool::managed::QueueMode::Fifo,
            }),
            connection: None,
        };

        // Create the connection pool
        let pool = pool_config
            .create_pool(Some(Runtime::Tokio1))
            .map_err(|e| ReflexError::Config(format!("Failed to create Redis pool: {:?}", e)))?;

        Ok(Self { pool, config })
    }

    /// Get a connection from the pool with retry logic
    ///
    /// Implements exponential backoff with configurable max retries.
    ///
    /// # Returns
    /// * `Result<Connection>` - Pooled Redis connection or error
    pub async fn get_connection(&self) -> ReflexResult<Connection> {
        let max_retries = 3;
        let mut retry_count = 0;
        let mut backoff_ms = 100;

        loop {
            match self.pool.get().await {
                Ok(conn) => {
                    debug!("Successfully obtained Redis connection");
                    return Ok(conn);
                }
                Err(e) => {
                    retry_count += 1;
                    if retry_count >= max_retries {
                        error!(
                            "Failed to get Redis connection after {} retries: {}",
                            max_retries, e
                        );
                        return Err(ReflexError::Redis(redis::RedisError::from((
                            redis::ErrorKind::IoError,
                            "Connection pool exhausted",
                        ))));
                    }

                    warn!(
                        "Failed to get Redis connection (attempt {}/{}): {}. Retrying in {}ms",
                        retry_count, max_retries, e, backoff_ms
                    );

                    sleep(Duration::from_millis(backoff_ms)).await;
                    backoff_ms = std::cmp::min(backoff_ms * 2, 5000); // Cap at 5 seconds
                }
            }
        }
    }

    /// Check if Redis is healthy by attempting to ping
    ///
    /// # Returns
    /// * `Result<bool>` - True if ping succeeds, error otherwise
    pub async fn health_check(&self) -> ReflexResult<bool> {
        debug!("Performing Redis health check");

        let mut conn = self.get_connection().await?;

        // Attempt to ping Redis using the PING command
        match redis::cmd("PING").query_async::<String>(&mut *conn).await {
            Ok(response) if response == "PONG" => {
                debug!("Redis health check passed");
                Ok(true)
            }
            Ok(response) => {
                error!("Unexpected ping response: {}", response);
                Err(ReflexError::Redis(redis::RedisError::from((
                    redis::ErrorKind::ResponseError,
                    "Unexpected ping response",
                ))))
            }
            Err(e) => {
                error!("Redis ping failed: {}", e);
                Err(ReflexError::Redis(e))
            }
        }
    }

    /// Get pool status information
    ///
    /// # Returns
    /// * `PoolStatus` - Current pool statistics
    pub fn pool_status(&self) -> PoolStatus {
        let status = self.pool.status();
        PoolStatus {
            size: status.size,
            available: status.available,
            max_size: status.max_size,
        }
    }

    /// Get Redis configuration
    pub fn config(&self) -> &RedisConfig {
        &self.config
    }
}

/// Pool status information
#[derive(Debug, Clone)]
pub struct PoolStatus {
    /// Current pool size
    pub size: usize,
    /// Available connections
    pub available: usize,
    /// Maximum pool size
    pub max_size: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_config() -> RedisConfig {
        RedisConfig {
            url: "redis://localhost:6379".to_string(),
            pool_size: 10,
            connection_timeout_ms: 5000,
            command_timeout_ms: 3000,
            cache_ttl_secs: 300,
        }
    }

    #[test]
    fn test_redis_client_creation() {
        let config = test_config();
        let client = RedisClient::new(config.clone());
        assert!(client.is_ok());

        let client = client.unwrap();
        assert_eq!(client.config().url, "redis://localhost:6379");
        assert_eq!(client.config().pool_size, 10);
    }

    #[test]
    fn test_pool_status() {
        let config = test_config();
        let client = RedisClient::new(config).unwrap();
        let status = client.pool_status();

        assert_eq!(status.max_size, 10);
        assert!(status.available <= status.max_size);
    }

    // Integration test - requires Redis to be running
    #[tokio::test]
    #[ignore] // Ignore by default, run with --ignored flag
    async fn test_redis_connection() {
        let config = test_config();
        let client = RedisClient::new(config).unwrap();

        let conn = client.get_connection().await;
        assert!(conn.is_ok());
    }

    // Integration test - requires Redis to be running
    #[tokio::test]
    #[ignore] // Ignore by default, run with --ignored flag
    async fn test_redis_health_check() {
        let config = test_config();
        let client = RedisClient::new(config).unwrap();

        let result = client.health_check().await;
        assert!(result.is_ok());
        assert!(result.unwrap());
    }
}
