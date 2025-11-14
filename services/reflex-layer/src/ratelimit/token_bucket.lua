-- Token Bucket Rate Limiting with Redis
-- This Lua script implements atomic token bucket rate limiting
--
-- KEYS[1] = rate limit key (e.g., "ratelimit:user:123")
-- ARGV[1] = capacity (maximum tokens)
-- ARGV[2] = refill_rate (tokens per second)
-- ARGV[3] = tokens_to_consume (typically 1.0)
-- ARGV[4] = current_time (milliseconds since epoch)
--
-- Returns:
-- [1] = 1 if allowed, 0 if denied
-- [2] = current tokens after operation
-- [3] = retry_after_ms (if denied) or reset_after_ms (if allowed)

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local tokens_to_consume = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

-- Get current bucket state
local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

-- Calculate token refill based on elapsed time
local elapsed = (now - last_refill) / 1000.0  -- Convert to seconds
local new_tokens = math.min(capacity, tokens + (elapsed * refill_rate))

-- Try to consume tokens
if new_tokens >= tokens_to_consume then
    -- Success: consume tokens
    new_tokens = new_tokens - tokens_to_consume

    -- Update Redis with new state
    redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill', now)

    -- Set expiration to prevent stale keys (1 hour)
    redis.call('EXPIRE', key, 3600)

    -- Calculate time until bucket is full again
    local tokens_needed = capacity - new_tokens
    local reset_after_ms = 0
    if tokens_needed > 0 then
        reset_after_ms = math.ceil((tokens_needed / refill_rate) * 1000)
    end

    return {1, new_tokens, reset_after_ms}
else
    -- Failure: insufficient tokens
    -- Update state with refilled tokens (but don't consume)
    redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)

    -- Calculate retry time
    local tokens_deficit = tokens_to_consume - new_tokens
    local retry_after_ms = math.ceil((tokens_deficit / refill_rate) * 1000) + 100  -- Add 100ms buffer

    return {0, new_tokens, retry_after_ms}
end
