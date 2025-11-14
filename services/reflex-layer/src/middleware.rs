//! Middleware components for the Reflex Layer
//!
//! Provides request ID generation, logging, and metrics collection middleware.

use axum::{extract::Request, http::header::HeaderValue, middleware::Next, response::Response};
use std::time::Instant;
use uuid::Uuid;

/// Request ID header name
pub const REQUEST_ID_HEADER: &str = "X-Request-ID";

/// Middleware that adds a unique request ID to each request and response
///
/// If the client provides an X-Request-ID header, it will be preserved.
/// Otherwise, a new UUID will be generated.
pub async fn request_id_middleware(mut request: Request, next: Next) -> Response {
    // Get or generate request ID
    let request_id = request
        .headers()
        .get(REQUEST_ID_HEADER)
        .and_then(|v| v.to_str().ok())
        .map(String::from)
        .unwrap_or_else(|| Uuid::new_v4().to_string());

    // Store in request extensions for access by handlers
    request.extensions_mut().insert(request_id.clone());

    // Add to request headers
    if let Ok(header_value) = HeaderValue::from_str(&request_id) {
        request
            .headers_mut()
            .insert(REQUEST_ID_HEADER, header_value.clone());
    }

    // Process request
    let mut response = next.run(request).await;

    // Add to response headers
    if let Ok(header_value) = HeaderValue::from_str(&request_id) {
        response
            .headers_mut()
            .insert(REQUEST_ID_HEADER, header_value);
    }

    response
}

/// Middleware that logs request details and duration
pub async fn logging_middleware(request: Request, next: Next) -> Response {
    let start = Instant::now();
    let method = request.method().clone();
    let uri = request.uri().clone();
    let request_id = request
        .extensions()
        .get::<String>()
        .cloned()
        .unwrap_or_else(|| "unknown".to_string());

    tracing::info!(
        request_id = %request_id,
        method = %method,
        uri = %uri,
        "Processing request"
    );

    let response = next.run(request).await;

    let duration = start.elapsed();
    let status = response.status();

    tracing::info!(
        request_id = %request_id,
        method = %method,
        uri = %uri,
        status = %status,
        duration_ms = %duration.as_millis(),
        "Request completed"
    );

    response
}

/// Middleware that collects metrics for Prometheus
pub async fn metrics_middleware(request: Request, next: Next) -> Response {
    let start = Instant::now();
    let method = request.method().clone();
    let path = request.uri().path().to_string();

    // Increment request counter
    crate::metrics::REQUEST_COUNT
        .with_label_values(&[method.as_str(), &path])
        .inc();

    let response = next.run(request).await;

    // Record request duration
    let duration = start.elapsed().as_secs_f64();
    crate::metrics::REQUEST_DURATION
        .with_label_values(&[method.as_str(), &path, response.status().as_str()])
        .observe(duration);

    response
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Method, Request as HttpRequest, StatusCode},
        middleware,
        response::IntoResponse,
        routing::get,
        Router,
    };
    use tower::ServiceExt;

    async fn test_handler() -> impl IntoResponse {
        (StatusCode::OK, "test response")
    }

    #[tokio::test]
    async fn test_request_id_middleware_generates_id() {
        let app = Router::new()
            .route("/test", get(test_handler))
            .layer(middleware::from_fn(request_id_middleware));

        let request = HttpRequest::builder()
            .method(Method::GET)
            .uri("/test")
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Should have X-Request-ID header
        let request_id = response.headers().get(REQUEST_ID_HEADER);
        assert!(request_id.is_some());

        let id_str = request_id.unwrap().to_str().unwrap();
        assert!(!id_str.is_empty());

        // Should be a valid UUID
        assert!(Uuid::parse_str(id_str).is_ok());
    }

    #[tokio::test]
    async fn test_request_id_middleware_preserves_existing_id() {
        let app = Router::new()
            .route("/test", get(test_handler))
            .layer(middleware::from_fn(request_id_middleware));

        let custom_id = "custom-request-id-123";
        let request = HttpRequest::builder()
            .method(Method::GET)
            .uri("/test")
            .header(REQUEST_ID_HEADER, custom_id)
            .body(Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Should preserve the custom ID
        let request_id = response.headers().get(REQUEST_ID_HEADER).unwrap();
        assert_eq!(request_id.to_str().unwrap(), custom_id);
    }
}
