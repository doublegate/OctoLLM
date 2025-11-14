//! Cache key generation utilities
//!
//! Provides deterministic key generation using SHA-256 and xxHash for cache operations.
//! Keys are namespace-prefixed to avoid collisions between different cache categories.

use crate::cache::types::CacheError;
use sha2::{Digest, Sha256};

/// Default namespace for cache keys
pub const DEFAULT_NAMESPACE: &str = "reflex";

/// Generate a cache key using SHA-256 hashing
///
/// Creates a deterministic, collision-resistant key suitable for cache operations.
/// The key format is: `namespace:cache:hash[..32]`
///
/// # Arguments
/// * `namespace` - Cache namespace (e.g., "reflex", "pii", "injection")
/// * `data` - The data to hash
///
/// # Returns
/// * `Ok(String)` - Generated cache key
/// * `Err(CacheError)` - Error if data is empty or invalid
///
/// # Example
/// ```
/// use reflex_layer::cache::key::generate_cache_key;
///
/// let key = generate_cache_key("reflex", "user query").unwrap();
/// assert!(key.starts_with("reflex:cache:"));
/// assert_eq!(key.len(), "reflex:cache:".len() + 32);
/// ```
pub fn generate_cache_key(namespace: &str, data: &str) -> Result<String, CacheError> {
    if data.is_empty() {
        return Err(CacheError::KeyGeneration(
            "Data cannot be empty".to_string(),
        ));
    }

    if namespace.is_empty() {
        return Err(CacheError::KeyGeneration(
            "Namespace cannot be empty".to_string(),
        ));
    }

    // Normalize data (trim whitespace, lowercase)
    let normalized = data.trim().to_lowercase();

    if normalized.is_empty() {
        return Err(CacheError::KeyGeneration(
            "Data cannot be empty after normalization".to_string(),
        ));
    }

    // Hash using SHA-256
    let mut hasher = Sha256::new();
    hasher.update(normalized.as_bytes());
    let hash = format!("{:x}", hasher.finalize());

    // Take first 32 characters for reasonable key length
    Ok(format!("{}:cache:{}", namespace, &hash[..32]))
}

/// Generate a fast cache key using xxHash
///
/// Creates a deterministic key optimized for speed. Suitable for high-throughput
/// scenarios where cryptographic strength is not required.
/// The key format is: `namespace:cache:hash`
///
/// # Arguments
/// * `namespace` - Cache namespace
/// * `data` - The data to hash
///
/// # Returns
/// * `Ok(String)` - Generated cache key
/// * `Err(CacheError)` - Error if data is empty or invalid
///
/// # Example
/// ```
/// use reflex_layer::cache::key::generate_cache_key_fast;
///
/// let key = generate_cache_key_fast("reflex", "user query").unwrap();
/// assert!(key.starts_with("reflex:cache:"));
/// ```
pub fn generate_cache_key_fast(namespace: &str, data: &str) -> Result<String, CacheError> {
    if data.is_empty() {
        return Err(CacheError::KeyGeneration(
            "Data cannot be empty".to_string(),
        ));
    }

    if namespace.is_empty() {
        return Err(CacheError::KeyGeneration(
            "Namespace cannot be empty".to_string(),
        ));
    }

    // Normalize data
    let normalized = data.trim().to_lowercase();

    if normalized.is_empty() {
        return Err(CacheError::KeyGeneration(
            "Data cannot be empty after normalization".to_string(),
        ));
    }

    // Use xxHash for fast hashing
    let hash = xxhash_rust::xxh3::xxh3_64(normalized.as_bytes());

    Ok(format!("{}:cache:{:x}", namespace, hash))
}

/// Generate a namespaced cache key with custom suffix
///
/// Allows more control over key structure for specific use cases.
///
/// # Arguments
/// * `namespace` - Cache namespace
/// * `category` - Category within namespace (e.g., "pii", "injection")
/// * `identifier` - Unique identifier for this cache entry
///
/// # Returns
/// * `Ok(String)` - Generated cache key in format `namespace:category:identifier`
/// * `Err(CacheError)` - Error if any parameter is empty
pub fn generate_custom_cache_key(
    namespace: &str,
    category: &str,
    identifier: &str,
) -> Result<String, CacheError> {
    if namespace.is_empty() || category.is_empty() || identifier.is_empty() {
        return Err(CacheError::KeyGeneration(
            "Namespace, category, and identifier must all be non-empty".to_string(),
        ));
    }

    Ok(format!("{}:{}:{}", namespace, category, identifier))
}

/// Validate a cache key pattern for use with invalidation operations
///
/// Ensures the pattern is safe to use with Redis KEYS/SCAN commands.
///
/// # Arguments
/// * `pattern` - The pattern to validate (e.g., "reflex:cache:*")
///
/// # Returns
/// * `Ok(())` - Pattern is valid
/// * `Err(CacheError)` - Pattern is invalid or unsafe
pub fn validate_cache_pattern(pattern: &str) -> Result<(), CacheError> {
    if pattern.is_empty() {
        return Err(CacheError::InvalidPattern(
            "Pattern cannot be empty".to_string(),
        ));
    }

    // Pattern must contain at least one colon (namespace separator)
    if !pattern.contains(':') {
        return Err(CacheError::InvalidPattern(
            "Pattern must include namespace (e.g., 'reflex:*')".to_string(),
        ));
    }

    // Pattern should not be too broad (prevent accidental deletion of everything)
    if pattern == "*" || pattern == "*:*" {
        return Err(CacheError::InvalidPattern(
            "Pattern is too broad and may delete unrelated keys".to_string(),
        ));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_cache_key_deterministic() {
        let key1 = generate_cache_key("reflex", "test query").unwrap();
        let key2 = generate_cache_key("reflex", "test query").unwrap();
        assert_eq!(key1, key2);
    }

    #[test]
    fn test_generate_cache_key_format() {
        let key = generate_cache_key("reflex", "test").unwrap();
        assert!(key.starts_with("reflex:cache:"));
        assert_eq!(key.len(), "reflex:cache:".len() + 32);
    }

    #[test]
    fn test_generate_cache_key_normalization() {
        let key1 = generate_cache_key("reflex", "  TEST Query  ").unwrap();
        let key2 = generate_cache_key("reflex", "test query").unwrap();
        assert_eq!(key1, key2);
    }

    #[test]
    fn test_generate_cache_key_empty_data() {
        let result = generate_cache_key("reflex", "");
        assert!(result.is_err());
        assert!(matches!(result, Err(CacheError::KeyGeneration(_))));
    }

    #[test]
    fn test_generate_cache_key_empty_namespace() {
        let result = generate_cache_key("", "test");
        assert!(result.is_err());
    }

    #[test]
    fn test_generate_cache_key_whitespace_only() {
        let result = generate_cache_key("reflex", "   ");
        assert!(result.is_err());
    }

    #[test]
    fn test_generate_cache_key_different_namespaces() {
        let key1 = generate_cache_key("reflex", "test").unwrap();
        let key2 = generate_cache_key("other", "test").unwrap();
        assert_ne!(key1, key2);
        assert!(key1.starts_with("reflex:"));
        assert!(key2.starts_with("other:"));
    }

    #[test]
    fn test_generate_cache_key_fast_deterministic() {
        let key1 = generate_cache_key_fast("reflex", "test query").unwrap();
        let key2 = generate_cache_key_fast("reflex", "test query").unwrap();
        assert_eq!(key1, key2);
    }

    #[test]
    fn test_generate_cache_key_fast_format() {
        let key = generate_cache_key_fast("reflex", "test").unwrap();
        assert!(key.starts_with("reflex:cache:"));
    }

    #[test]
    fn test_generate_cache_key_fast_vs_secure() {
        let key_fast = generate_cache_key_fast("reflex", "test").unwrap();
        let key_secure = generate_cache_key("reflex", "test").unwrap();
        // Both should work but produce different hashes
        assert_ne!(key_fast, key_secure);
        assert!(key_fast.len() < key_secure.len()); // xxHash produces shorter hash
    }

    #[test]
    fn test_generate_custom_cache_key() {
        let key = generate_custom_cache_key("reflex", "pii", "user123").unwrap();
        assert_eq!(key, "reflex:pii:user123");
    }

    #[test]
    fn test_generate_custom_cache_key_empty_params() {
        assert!(generate_custom_cache_key("", "pii", "id").is_err());
        assert!(generate_custom_cache_key("reflex", "", "id").is_err());
        assert!(generate_custom_cache_key("reflex", "pii", "").is_err());
    }

    #[test]
    fn test_validate_cache_pattern_valid() {
        assert!(validate_cache_pattern("reflex:cache:*").is_ok());
        assert!(validate_cache_pattern("reflex:pii:*").is_ok());
        assert!(validate_cache_pattern("reflex:*").is_ok());
    }

    #[test]
    fn test_validate_cache_pattern_empty() {
        assert!(validate_cache_pattern("").is_err());
    }

    #[test]
    fn test_validate_cache_pattern_no_namespace() {
        assert!(validate_cache_pattern("test").is_err());
    }

    #[test]
    fn test_validate_cache_pattern_too_broad() {
        assert!(validate_cache_pattern("*").is_err());
        assert!(validate_cache_pattern("*:*").is_err());
    }

    #[test]
    fn test_key_uniqueness_different_inputs() {
        let keys: Vec<String> = vec![
            generate_cache_key("reflex", "query1").unwrap(),
            generate_cache_key("reflex", "query2").unwrap(),
            generate_cache_key("reflex", "query3").unwrap(),
        ];

        // All keys should be unique
        assert_eq!(keys.len(), 3);
        assert_ne!(keys[0], keys[1]);
        assert_ne!(keys[1], keys[2]);
        assert_ne!(keys[0], keys[2]);
    }

    #[test]
    fn test_key_collision_resistance() {
        // Similar strings should produce different keys
        let key1 = generate_cache_key("reflex", "hello world").unwrap();
        let key2 = generate_cache_key("reflex", "hello worlD").unwrap();

        // After normalization (lowercase), these should be the same
        assert_eq!(key1, key2);

        // But truly different strings should differ
        let key3 = generate_cache_key("reflex", "hello world!").unwrap();
        assert_ne!(key1, key3);
    }
}
