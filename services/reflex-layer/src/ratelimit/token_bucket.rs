//! Local in-memory token bucket implementation
//!
//! Provides a thread-safe, local token bucket for rate limiting without Redis.
//! Useful for testing and single-instance deployments.

use crate::ratelimit::types::{RateLimitConfig, RateLimitResult};
use std::sync::{Arc, Mutex};
use std::time::Instant;

/// Local token bucket for rate limiting
///
/// This is a thread-safe, in-memory implementation suitable for single-instance
/// deployments or testing. For distributed systems, use RedisRateLimiter instead.
#[derive(Clone)]
pub struct TokenBucket {
    state: Arc<Mutex<TokenBucketState>>,
    config: RateLimitConfig,
}

struct TokenBucketState {
    /// Current number of tokens (can be fractional)
    tokens: f64,
    /// Last time tokens were refilled
    last_refill: Instant,
}

impl TokenBucket {
    /// Create a new token bucket
    ///
    /// # Arguments
    /// * `config` - Rate limit configuration
    ///
    /// # Returns
    /// * `Self` - New token bucket initialized with full capacity
    pub fn new(config: RateLimitConfig) -> Self {
        Self {
            state: Arc::new(Mutex::new(TokenBucketState {
                tokens: config.capacity as f64,
                last_refill: Instant::now(),
            })),
            config,
        }
    }

    /// Try to consume tokens from the bucket
    ///
    /// # Arguments
    /// * `tokens` - Number of tokens to consume (typically 1.0)
    ///
    /// # Returns
    /// * `RateLimitResult::Allowed` - Request allowed, tokens consumed
    /// * `RateLimitResult::Limited` - Request denied, insufficient tokens
    pub fn try_consume(&self, tokens: f64) -> RateLimitResult {
        let mut state = self.state.lock().unwrap();

        // Refill tokens based on elapsed time
        self.refill(&mut state);

        if state.tokens >= tokens {
            // Enough tokens available
            state.tokens -= tokens;

            RateLimitResult::Allowed {
                remaining: state.tokens,
                reset_after_ms: self.calculate_reset_time(state.tokens),
            }
        } else {
            // Insufficient tokens
            use crate::ratelimit::types::RateLimitReason;

            let retry_after_ms = self.calculate_retry_time(state.tokens, tokens);

            RateLimitResult::Limited {
                reason: RateLimitReason::Custom,
                retry_after_ms,
                current_tokens: state.tokens,
            }
        }
    }

    /// Refill tokens based on elapsed time
    fn refill(&self, state: &mut TokenBucketState) {
        let now = Instant::now();
        let elapsed = now.duration_since(state.last_refill).as_secs_f64();

        // Calculate new tokens
        let new_tokens = elapsed * self.config.refill_rate;
        state.tokens = (state.tokens + new_tokens).min(self.config.capacity as f64);
        state.last_refill = now;
    }

    /// Calculate time until bucket is fully reset
    fn calculate_reset_time(&self, current_tokens: f64) -> u64 {
        if current_tokens >= self.config.capacity as f64 {
            return 0;
        }

        let tokens_needed = self.config.capacity as f64 - current_tokens;
        let seconds_until_full = tokens_needed / self.config.refill_rate;

        (seconds_until_full * 1000.0) as u64
    }

    /// Calculate time to wait before retrying
    fn calculate_retry_time(&self, current_tokens: f64, tokens_needed: f64) -> u64 {
        let tokens_deficit = tokens_needed - current_tokens;
        let seconds_to_wait = tokens_deficit / self.config.refill_rate;

        // Add small buffer (100ms)
        ((seconds_to_wait * 1000.0) + 100.0) as u64
    }

    /// Get current token count (without consuming)
    pub fn current_tokens(&self) -> f64 {
        let mut state = self.state.lock().unwrap();
        self.refill(&mut state);
        state.tokens
    }

    /// Reset the bucket to full capacity
    pub fn reset(&self) {
        let mut state = self.state.lock().unwrap();
        state.tokens = self.config.capacity as f64;
        state.last_refill = Instant::now();
    }

    /// Get the configuration for this bucket
    pub fn config(&self) -> &RateLimitConfig {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread::sleep;
    use std::time::Duration;

    #[test]
    fn test_token_bucket_creation() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };
        let bucket = TokenBucket::new(config);

        assert_eq!(bucket.current_tokens(), 10.0);
    }

    #[test]
    fn test_token_bucket_consume_success() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };
        let bucket = TokenBucket::new(config);

        let result = bucket.try_consume(5.0);
        assert!(result.is_allowed());

        if let RateLimitResult::Allowed { remaining, .. } = result {
            assert_eq!(remaining, 5.0);
        }
    }

    #[test]
    fn test_token_bucket_consume_failure() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };
        let bucket = TokenBucket::new(config);

        // Consume all tokens
        bucket.try_consume(10.0);

        // Next consumption should fail
        let result = bucket.try_consume(1.0);
        assert!(result.is_limited());

        if let RateLimitResult::Limited { current_tokens, .. } = result {
            assert!(current_tokens < 1.0);
        }
    }

    #[test]
    fn test_token_bucket_refill() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 10.0, // 10 tokens per second
        };
        let bucket = TokenBucket::new(config);

        // Consume all tokens
        bucket.try_consume(10.0);
        assert!(bucket.current_tokens() < 1.0);

        // Wait for refill (100ms = 1 token at 10 tokens/sec)
        sleep(Duration::from_millis(100));

        let tokens = bucket.current_tokens();
        assert!(tokens >= 0.9 && tokens <= 1.1); // Allow for timing variance
    }

    #[test]
    fn test_token_bucket_refill_cap() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 100.0, // Very fast refill
        };
        let bucket = TokenBucket::new(config);

        // Consume 5 tokens
        bucket.try_consume(5.0);

        // Wait for more than enough time to refill
        sleep(Duration::from_millis(200));

        // Tokens should be capped at capacity
        let tokens = bucket.current_tokens();
        assert!(tokens <= 10.0);
    }

    #[test]
    fn test_token_bucket_fractional_tokens() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };
        let bucket = TokenBucket::new(config);

        let result = bucket.try_consume(2.5);
        assert!(result.is_allowed());

        if let RateLimitResult::Allowed { remaining, .. } = result {
            assert_eq!(remaining, 7.5);
        }
    }

    #[test]
    fn test_token_bucket_multiple_consume() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };
        let bucket = TokenBucket::new(config);

        // Consume tokens multiple times
        for _ in 0..5 {
            let result = bucket.try_consume(2.0);
            assert!(result.is_allowed());
        }

        // 11th token should fail
        let result = bucket.try_consume(1.0);
        assert!(result.is_limited());
    }

    #[test]
    fn test_token_bucket_reset() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };
        let bucket = TokenBucket::new(config);

        // Consume all tokens
        bucket.try_consume(10.0);
        assert!(bucket.current_tokens() < 1.0);

        // Reset
        bucket.reset();
        assert_eq!(bucket.current_tokens(), 10.0);
    }

    #[test]
    fn test_token_bucket_concurrent_access() {
        use std::thread;

        let config = RateLimitConfig {
            capacity: 100,
            refill_rate: 10.0,
        };
        let bucket = Arc::new(TokenBucket::new(config));

        let mut handles = vec![];

        // Spawn 10 threads, each consuming 10 tokens
        for _ in 0..10 {
            let bucket_clone = Arc::clone(&bucket);
            let handle = thread::spawn(move || bucket_clone.try_consume(10.0));
            handles.push(handle);
        }

        // Collect results
        let results: Vec<_> = handles.into_iter().map(|h| h.join().unwrap()).collect();

        // All should succeed since we have exactly 100 tokens
        assert_eq!(results.iter().filter(|r| r.is_allowed()).count(), 10);
    }

    #[test]
    fn test_token_bucket_burst_then_sustained() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 2.0, // 2 tokens per second
        };
        let bucket = TokenBucket::new(config);

        // Burst: consume all 10 tokens quickly
        for _ in 0..10 {
            assert!(bucket.try_consume(1.0).is_allowed());
        }

        // Next request should fail
        assert!(bucket.try_consume(1.0).is_limited());

        // Wait for 1 second (should refill 2 tokens)
        sleep(Duration::from_secs(1));

        // Should be able to consume 2 more tokens
        assert!(bucket.try_consume(1.0).is_allowed());
        assert!(bucket.try_consume(1.0).is_allowed());

        // Third should fail
        assert!(bucket.try_consume(1.0).is_limited());
    }

    #[test]
    fn test_token_bucket_config_access() {
        let config = RateLimitConfig {
            capacity: 10,
            refill_rate: 1.0,
        };
        let bucket = TokenBucket::new(config);

        assert_eq!(bucket.config().capacity, 10);
        assert_eq!(bucket.config().refill_rate, 1.0);
    }
}
