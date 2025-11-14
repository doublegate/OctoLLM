//! Error handling for the Reflex Layer
//!
//! Provides comprehensive error types and conversions for all reflex layer operations.

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Main error type for the Reflex Layer
#[derive(Error, Debug)]
pub enum ReflexError {
    /// Configuration error
    #[error("Configuration error: {0}")]
    Config(String),

    /// Redis connection error
    #[error("Redis error: {0}")]
    Redis(#[from] redis::RedisError),

    /// Cache operation failed
    #[error("Cache error: {0}")]
    Cache(String),

    /// Rate limit exceeded
    #[error("Rate limit exceeded: {0}")]
    RateLimit(String),

    /// PII detection error
    #[error("PII detection error: {0}")]
    PiiDetection(String),

    /// Injection detection error
    #[error("Injection detected: {0}")]
    InjectionDetected(String),

    /// Validation error
    #[error("Validation error: {0}")]
    Validation(String),

    /// Request too large
    #[error("Request too large: {0}")]
    RequestTooLarge(String),

    /// Timeout error
    #[error("Operation timed out: {0}")]
    Timeout(String),

    /// Internal server error
    #[error("Internal error: {0}")]
    Internal(String),

    /// Database error
    #[error("Database error: {0}")]
    Database(String),

    /// Serialization error
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    /// HTTP error
    #[error("HTTP error: {0}")]
    Http(String),
}

/// Result type alias for Reflex Layer operations
pub type ReflexResult<T> = Result<T, ReflexError>;

/// Error response structure returned to clients
#[derive(Debug, Serialize, Deserialize)]
pub struct ErrorResponse {
    /// Error code (HTTP status code)
    pub code: u16,

    /// Error message
    pub message: String,

    /// Detailed error (optional, for debugging)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,

    /// Request ID for tracing
    #[serde(skip_serializing_if = "Option::is_none")]
    pub request_id: Option<String>,

    /// Timestamp of error
    pub timestamp: String,
}

impl ReflexError {
    /// Convert error to HTTP status code
    pub fn status_code(&self) -> StatusCode {
        match self {
            ReflexError::Config(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ReflexError::Redis(_) => StatusCode::SERVICE_UNAVAILABLE,
            ReflexError::Cache(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ReflexError::RateLimit(_) => StatusCode::TOO_MANY_REQUESTS,
            ReflexError::PiiDetection(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ReflexError::InjectionDetected(_) => StatusCode::BAD_REQUEST,
            ReflexError::Validation(_) => StatusCode::BAD_REQUEST,
            ReflexError::RequestTooLarge(_) => StatusCode::PAYLOAD_TOO_LARGE,
            ReflexError::Timeout(_) => StatusCode::REQUEST_TIMEOUT,
            ReflexError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ReflexError::Database(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ReflexError::Serialization(_) => StatusCode::BAD_REQUEST,
            ReflexError::Http(_) => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }

    /// Get error message suitable for client display
    pub fn client_message(&self) -> String {
        match self {
            ReflexError::Config(_) => "Service configuration error".to_string(),
            ReflexError::Redis(_) => "Cache service unavailable".to_string(),
            ReflexError::Cache(_) => "Cache operation failed".to_string(),
            ReflexError::RateLimit(msg) => msg.clone(),
            ReflexError::PiiDetection(_) => "Security check failed".to_string(),
            ReflexError::InjectionDetected(msg) => msg.clone(),
            ReflexError::Validation(msg) => msg.clone(),
            ReflexError::RequestTooLarge(msg) => msg.clone(),
            ReflexError::Timeout(msg) => msg.clone(),
            ReflexError::Internal(_) => "Internal server error".to_string(),
            ReflexError::Database(_) => "Database error".to_string(),
            ReflexError::Serialization(_) => "Invalid request format".to_string(),
            ReflexError::Http(msg) => msg.clone(),
        }
    }

    /// Check if error should be logged at ERROR level (vs WARN)
    pub fn is_severe(&self) -> bool {
        matches!(
            self,
            ReflexError::Config(_)
                | ReflexError::Redis(_)
                | ReflexError::Internal(_)
                | ReflexError::Database(_)
        )
    }
}

/// Convert ReflexError to HTTP response
impl IntoResponse for ReflexError {
    fn into_response(self) -> Response {
        let status = self.status_code();
        let message = self.client_message();
        let detail = if cfg!(debug_assertions) {
            Some(self.to_string())
        } else {
            None
        };

        let error_response = ErrorResponse {
            code: status.as_u16(),
            message,
            detail,
            request_id: None, // TODO(#1): Extract request ID from middleware context
            timestamp: Utc::now().to_rfc3339(),
        };

        // Log the error
        if self.is_severe() {
            tracing::error!(error = %self, "Reflex layer error");
        } else {
            tracing::warn!(error = %self, "Reflex layer warning");
        }

        (status, Json(error_response)).into_response()
    }
}

/// Convert config::ConfigError to ReflexError
impl From<config::ConfigError> for ReflexError {
    fn from(err: config::ConfigError) -> Self {
        ReflexError::Config(err.to_string())
    }
}

/// Convert std::io::Error to ReflexError
impl From<std::io::Error> for ReflexError {
    fn from(err: std::io::Error) -> Self {
        ReflexError::Internal(format!("IO error: {}", err))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_status_codes() {
        assert_eq!(
            ReflexError::RateLimit("test".to_string()).status_code(),
            StatusCode::TOO_MANY_REQUESTS
        );
        assert_eq!(
            ReflexError::Validation("test".to_string()).status_code(),
            StatusCode::BAD_REQUEST
        );
        assert_eq!(
            ReflexError::Internal("test".to_string()).status_code(),
            StatusCode::INTERNAL_SERVER_ERROR
        );
    }

    #[test]
    fn test_error_severity() {
        assert!(ReflexError::Config("test".to_string()).is_severe());
        assert!(ReflexError::Redis(redis::RedisError::from((
            redis::ErrorKind::IoError,
            "connection failed"
        )))
        .is_severe());
        assert!(!ReflexError::Validation("test".to_string()).is_severe());
        assert!(!ReflexError::RateLimit("test".to_string()).is_severe());
    }

    #[test]
    fn test_client_messages() {
        let err = ReflexError::RateLimit("Rate limit exceeded for user".to_string());
        assert_eq!(err.client_message(), "Rate limit exceeded for user");

        let err = ReflexError::Internal("Database connection pool exhausted".to_string());
        assert_eq!(err.client_message(), "Internal server error");
    }
}

/// API-specific error type for handlers
///
/// This is a simpler error type for use in API handlers that wraps ReflexError
/// but provides additional context for HTTP responses.
#[derive(Error, Debug)]
pub enum ApiError {
    /// Validation error (400 Bad Request)
    #[error("Validation error: {0}")]
    ValidationError(String),

    /// Rate limit exceeded (429 Too Many Requests)
    #[error("Rate limit exceeded: {0}")]
    RateLimitError(String),

    /// Cache error (500 Internal Server Error)
    #[error("Cache error: {0}")]
    CacheError(String),

    /// Detection error (500 Internal Server Error)
    #[error("Detection error: {0}")]
    DetectionError(String),

    /// Internal error (500 Internal Server Error)
    #[error("Internal error: {0}")]
    InternalError(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            ApiError::ValidationError(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            ApiError::RateLimitError(_) => (
                StatusCode::TOO_MANY_REQUESTS,
                "Rate limit exceeded".to_string(),
            ),
            ApiError::CacheError(_) => {
                (StatusCode::INTERNAL_SERVER_ERROR, "Cache error".to_string())
            }
            ApiError::DetectionError(_) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "Detection error".to_string(),
            ),
            ApiError::InternalError(_) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "Internal server error".to_string(),
            ),
        };

        let detail = if cfg!(debug_assertions) {
            Some(self.to_string())
        } else {
            None
        };

        let error_response = ErrorResponse {
            code: status.as_u16(),
            message,
            detail,
            request_id: None,
            timestamp: Utc::now().to_rfc3339(),
        };

        // Log the error
        match self {
            ApiError::ValidationError(_) | ApiError::RateLimitError(_) => {
                tracing::warn!(error = %self, "API request rejected");
            }
            _ => {
                tracing::error!(error = %self, "API error");
            }
        }

        (status, Json(error_response)).into_response()
    }
}
