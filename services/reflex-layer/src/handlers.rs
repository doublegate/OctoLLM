//! HTTP handlers for the Reflex Layer API
//!
//! This module contains all HTTP request handlers including the main /process endpoint
//! that orchestrates PII detection, injection detection, caching, and rate limiting.

use axum::{
    extract::{ConnectInfo, State},
    Json,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Instant;
use uuid::Uuid;

use crate::AppState;
use reflex_layer::{
    cache::{generate_cache_key, Cache, CacheTTL},
    error::ApiError,
    injection::{InjectionMatch, Severity},
    pii::PIIMatch,
    ratelimit::{RateLimitKey, RateLimitTier},
};

/// Request payload for /process endpoint
#[derive(Debug, Deserialize)]
pub struct ProcessRequest {
    /// Text to analyze
    pub text: String,

    /// Optional user ID for rate limiting
    #[serde(default)]
    pub user_id: Option<String>,

    /// Whether to check for PII (default: true)
    #[serde(default = "default_true")]
    pub check_pii: bool,

    /// Whether to check for injection attempts (default: true)
    #[serde(default = "default_true")]
    pub check_injection: bool,

    /// Whether to use caching (default: true)
    #[serde(default = "default_true")]
    pub use_cache: bool,
}

fn default_true() -> bool {
    true
}

/// Response payload for /process endpoint
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ProcessResponse {
    /// Unique request identifier
    pub request_id: String,

    /// Processing status
    pub status: ProcessStatus,

    /// Whether PII was detected
    pub pii_detected: bool,

    /// PII matches found
    pub pii_matches: Vec<PIIMatch>,

    /// Whether injection attempt was detected
    pub injection_detected: bool,

    /// Injection matches found
    pub injection_matches: Vec<InjectionMatch>,

    /// Whether response came from cache
    pub cache_hit: bool,

    /// Processing time in milliseconds
    pub processing_time_ms: f64,
}

/// Processing status enum
#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum ProcessStatus {
    /// Request processed successfully
    Success,

    /// Request blocked due to critical injection
    Blocked,

    /// Request rejected due to rate limiting
    RateLimited,

    /// Processing error occurred
    Error,
}

/// Main processing endpoint handler
///
/// Processes text through the full Reflex Layer pipeline:
/// 1. Rate limiting (IP-based and optionally user-based)
/// 2. Cache check
/// 3. PII detection
/// 4. Injection detection
/// 5. Cache storage
///
/// # Arguments
///
/// * `state` - Shared application state
/// * `addr` - Client socket address for IP-based rate limiting
/// * `request` - Processing request payload
///
/// # Returns
///
/// Returns a `ProcessResponse` with detection results and metadata
pub async fn process_text(
    State(state): State<Arc<AppState>>,
    ConnectInfo(addr): ConnectInfo<SocketAddr>,
    Json(request): Json<ProcessRequest>,
) -> Result<Json<ProcessResponse>, ApiError> {
    let request_id = Uuid::new_v4().to_string();
    let start = Instant::now();

    // Input validation
    if request.text.is_empty() {
        return Err(ApiError::ValidationError(
            "Text cannot be empty".to_string(),
        ));
    }

    if request.text.len() > 100_000 {
        return Err(ApiError::ValidationError(
            "Text exceeds maximum length of 100,000 characters".to_string(),
        ));
    }

    // 1. Rate Limiting
    let ip = addr.ip().to_string();
    let rate_limit_key = RateLimitKey::IP(ip.clone());

    // Use Free tier config for IP: 100 requests/hour, burst of 10
    let ip_config = RateLimitTier::Free.config();

    let result = state
        .rate_limiter
        .check_rate_limit(&rate_limit_key, &ip_config, 1.0)
        .await
        .map_err(|e| ApiError::RateLimitError(format!("Rate limit check failed: {}", e)))?;

    if !result.is_allowed() {
        tracing::warn!("Rate limit exceeded for IP: {}", ip);
        return Ok(Json(ProcessResponse {
            request_id,
            status: ProcessStatus::RateLimited,
            pii_detected: false,
            pii_matches: vec![],
            injection_detected: false,
            injection_matches: vec![],
            cache_hit: false,
            processing_time_ms: start.elapsed().as_secs_f64() * 1000.0,
        }));
    }

    // Also check user-based rate limit if user_id provided
    if let Some(ref user_id) = request.user_id {
        let user_rate_limit_key = RateLimitKey::User(user_id.clone());
        // Use Basic tier for users: 1000 requests/hour, burst of 50
        let user_config = RateLimitTier::Basic.config();

        let user_result = state
            .rate_limiter
            .check_rate_limit(&user_rate_limit_key, &user_config, 1.0)
            .await
            .map_err(|e| {
                ApiError::RateLimitError(format!("User rate limit check failed: {}", e))
            })?;

        if !user_result.is_allowed() {
            tracing::warn!("Rate limit exceeded for user: {}", user_id);
            return Ok(Json(ProcessResponse {
                request_id,
                status: ProcessStatus::RateLimited,
                pii_detected: false,
                pii_matches: vec![],
                injection_detected: false,
                injection_matches: vec![],
                cache_hit: false,
                processing_time_ms: start.elapsed().as_secs_f64() * 1000.0,
            }));
        }
    }

    // 2. Cache Check
    let mut cache_hit = false;
    let cache_key = if request.use_cache {
        match generate_cache_key("reflex:process", &request.text) {
            Ok(key) => Some(key),
            Err(e) => {
                tracing::warn!("Failed to generate cache key: {}", e);
                None
            }
        }
    } else {
        None
    };

    if let Some(ref key) = cache_key {
        if let Ok(Some(cached)) = state.cache.get(key).await {
            cache_hit = true;
            tracing::debug!("Cache hit for key: {}", key);

            // Deserialize cached response
            if let Ok(mut response) = serde_json::from_str::<ProcessResponse>(&cached) {
                response.cache_hit = true;
                response.request_id = request_id; // Update with new request ID
                response.processing_time_ms = start.elapsed().as_secs_f64() * 1000.0;
                return Ok(Json(response));
            } else {
                tracing::warn!("Failed to deserialize cached response, proceeding with detection");
            }
        } else {
            tracing::debug!("Cache miss for key: {}", key);
        }
    }

    // 3. PII Detection
    let pii_matches = if request.check_pii {
        let pii_start = Instant::now();
        let matches = state.pii_detector.detect(&request.text);
        let pii_duration = pii_start.elapsed();
        tracing::debug!(
            "PII detection completed in {:?}, found {} matches",
            pii_duration,
            matches.len()
        );
        matches
    } else {
        vec![]
    };

    let pii_detected = !pii_matches.is_empty();

    // 4. Injection Detection
    let injection_matches = if request.check_injection {
        let injection_start = Instant::now();
        let matches = state.injection_detector.detect(&request.text);
        let injection_duration = injection_start.elapsed();
        tracing::debug!(
            "Injection detection completed in {:?}, found {} matches",
            injection_duration,
            matches.len()
        );
        matches
    } else {
        vec![]
    };

    let injection_detected = !injection_matches.is_empty();

    // 5. Determine Status
    // Block if critical injection detected
    let status = if injection_detected
        && injection_matches
            .iter()
            .any(|m| matches!(m.severity, Severity::Critical))
    {
        tracing::warn!("Critical injection detected, blocking request");
        ProcessStatus::Blocked
    } else {
        ProcessStatus::Success
    };

    // 6. Build Response
    let response = ProcessResponse {
        request_id,
        status,
        pii_detected,
        pii_matches,
        injection_detected,
        injection_matches,
        cache_hit,
        processing_time_ms: start.elapsed().as_secs_f64() * 1000.0,
    };

    // 7. Cache Response (if caching enabled and processing was successful)
    if let Some(key) = cache_key {
        if let Ok(serialized) = serde_json::to_string(&response) {
            let cache_ttl = if pii_detected || injection_detected {
                CacheTTL::Short // Cache positive detections for shorter time
            } else {
                CacheTTL::Medium // Cache clean text for longer
            };

            if let Err(e) = state.cache.set(&key, &serialized, cache_ttl).await {
                tracing::warn!("Failed to cache response: {}", e);
                // Non-fatal, continue
            } else {
                tracing::debug!("Cached response with TTL {:?}", cache_ttl);
            }
        }
    }

    Ok(Json(response))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_process_request_defaults() {
        let json = r#"{"text": "test"}"#;
        let req: ProcessRequest = serde_json::from_str(json).unwrap();

        assert_eq!(req.text, "test");
        assert!(req.check_pii);
        assert!(req.check_injection);
        assert!(req.use_cache);
        assert!(req.user_id.is_none());
    }

    #[test]
    fn test_process_request_custom() {
        let json = r#"{"text": "test", "check_pii": false, "user_id": "user123"}"#;
        let req: ProcessRequest = serde_json::from_str(json).unwrap();

        assert_eq!(req.text, "test");
        assert!(!req.check_pii);
        assert!(req.check_injection); // still default true
        assert_eq!(req.user_id, Some("user123".to_string()));
    }

    #[test]
    fn test_process_response_serialization() {
        let response = ProcessResponse {
            request_id: "test-123".to_string(),
            status: ProcessStatus::Success,
            pii_detected: false,
            pii_matches: vec![],
            injection_detected: false,
            injection_matches: vec![],
            cache_hit: false,
            processing_time_ms: 1.23,
        };

        let json = serde_json::to_string(&response).unwrap();
        assert!(json.contains("test-123"));
        assert!(json.contains("success"));
    }
}
