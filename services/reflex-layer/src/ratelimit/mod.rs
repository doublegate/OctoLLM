//! Rate limiting module for the Reflex Layer
//!
//! Provides distributed rate limiting using Redis with token bucket algorithm,
//! supporting multi-dimensional rate limits (user, IP, endpoint, global).

pub mod redis_limiter;
pub mod token_bucket;
pub mod types;

// Re-export commonly used items
pub use redis_limiter::{MultiDimensionalRateLimiter, RedisRateLimiter};
pub use token_bucket::TokenBucket;
pub use types::{
    RateLimitConfig, RateLimitError, RateLimitKey, RateLimitReason, RateLimitResult, RateLimitTier,
};
