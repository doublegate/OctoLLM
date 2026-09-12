//! OctoLLM Reflex Layer
//!
//! Fast preprocessing layer for common patterns without LLM involvement.

mod handlers;
mod metrics;
mod middleware;

use axum::{
    extract::State,
    http::StatusCode,
    middleware as axum_middleware,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use prometheus::TextEncoder;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::signal;
use tower_http::{
    cors::CorsLayer,
    trace::{DefaultMakeSpan, DefaultOnResponse, TraceLayer},
};
use tracing::Level;

use reflex_layer::{
    cache::RedisCache,
    config::Config,
    error::{ReflexError, ReflexResult},
    injection::{DetectionMode, InjectionConfig, InjectionDetector, Severity},
    pii::{PIIConfig, PIIDetector, PatternSet},
    ratelimit::RedisRateLimiter,
    redis_client::RedisClient,
};

/// Application state shared across all handlers
pub struct AppState {
    pub config: Arc<Config>,
    pub redis: RedisClient,
    pub pii_detector: Arc<PIIDetector>,
    pub injection_detector: Arc<InjectionDetector>,
    pub cache: Arc<RedisCache>,
    pub rate_limiter: Arc<RedisRateLimiter>,
    pub start_time: std::time::Instant,
}

/// Health check response
#[derive(Debug, Serialize, Deserialize)]
struct HealthResponse {
    status: String,
    version: String,
    uptime_seconds: u64,
}

/// Readiness check response
#[derive(Debug, Serialize, Deserialize)]
struct ReadinessResponse {
    status: String,
    ready: bool,
    checks: ReadinessChecks,
}

/// Individual readiness checks
#[derive(Debug, Serialize, Deserialize)]
struct ReadinessChecks {
    redis: bool,
    config: bool,
}

#[tokio::main]
async fn main() -> ReflexResult<()> {
    // Load configuration from environment
    let config = Config::from_env().map_err(|e| ReflexError::Config(e.to_string()))?;

    // Initialize logging based on configuration
    let log_format = config.logging.format.to_lowercase();
    let log_level = config.logging.level.to_lowercase();

    let subscriber = tracing_subscriber::fmt()
        .with_target(true)
        .with_thread_ids(true)
        .with_line_number(true);

    match log_format.as_str() {
        "json" => subscriber
            .json()
            .with_max_level(parse_log_level(&log_level))
            .init(),
        _ => subscriber
            .with_max_level(parse_log_level(&log_level))
            .init(),
    }

    tracing::info!(
        "Starting Reflex Layer v{} on {}:{}",
        env!("CARGO_PKG_VERSION"),
        config.server.host,
        config.server.port
    );

    // Create Redis client (wrapped in Arc for sharing)
    let redis_client = Arc::new(RedisClient::new(config.redis.clone()).map_err(|e| {
        ReflexError::Redis(redis::RedisError::from((
            redis::ErrorKind::Io,
            "Failed to create Redis client",
            e.to_string(),
        )))
    })?);
    tracing::info!("Redis client initialized");

    // Verify Redis connectivity
    match redis_client.health_check().await {
        Ok(_) => tracing::info!("Redis connection verified"),
        Err(e) => {
            tracing::warn!("Redis health check failed: {}. Continuing without Redis", e);
            // Note: In production, you might want to fail fast here
        }
    }

    // Initialize PII detector
    let pii_config = PIIConfig {
        pattern_set: PatternSet::Standard,
        enable_validation: true,
        enable_context: false,
    };
    let pii_detector = Arc::new(PIIDetector::new(pii_config));
    tracing::info!("PII detector initialized with Standard pattern set");

    // Initialize Injection detector
    let injection_config = InjectionConfig {
        detection_mode: DetectionMode::Standard,
        enable_context_analysis: true,
        enable_entropy_check: true,
        severity_threshold: Severity::Low,
    };
    let injection_detector = Arc::new(InjectionDetector::new(injection_config));
    tracing::info!("Injection detector initialized with Standard detection mode");

    // Initialize Redis cache
    let cache = Arc::new(RedisCache::new(redis_client.clone()));
    tracing::info!("Redis cache initialized");

    // Initialize Redis rate limiter
    let rate_limiter = Arc::new(RedisRateLimiter::new(redis_client.clone()));
    tracing::info!("Redis rate limiter initialized");

    // Create application state
    let state = Arc::new(AppState {
        config: Arc::new(config.clone()),
        redis: (*redis_client).clone(), // Clone the inner RedisClient
        pii_detector,
        injection_detector,
        cache,
        rate_limiter,
        start_time: std::time::Instant::now(),
    });

    let app = build_router(state.clone());

    // Create TCP listener
    let addr = format!("{}:{}", config.server.host, config.server.port);
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .map_err(|e| ReflexError::Internal(format!("Failed to bind to {}: {}", addr, e)))?;

    tracing::info!("Reflex layer listening on {}", addr);
    tracing::info!("Configuration loaded: {:?}", config);

    serve(listener, app, shutdown_signal()).await?;

    tracing::info!("Reflex layer shutdown complete");
    Ok(())
}

/// Build the application router.
///
/// Extracted so that `main` and the tests construct the SAME router. A test that
/// assembles its own `Router` cannot catch a defect in how the real one is wired,
/// which is precisely what happened with `/process`.
pub fn build_router(state: Arc<AppState>) -> Router {
    Router::new()
        // Main processing endpoint
        .route("/process", post(handlers::process_text))
        // Health and readiness endpoints
        .route("/health", get(health_handler))
        .route("/ready", get(readiness_handler))
        // Metrics endpoint
        .route("/metrics", get(metrics_handler))
        .with_state(state.clone())
        // Middleware stack (applied in reverse order)
        .layer(axum_middleware::from_fn(middleware::metrics_middleware))
        .layer(axum_middleware::from_fn(middleware::logging_middleware))
        .layer(axum_middleware::from_fn(middleware::request_id_middleware))
        .layer(
            TraceLayer::new_for_http()
                .make_span_with(DefaultMakeSpan::new().level(Level::INFO))
                .on_response(DefaultOnResponse::new().level(Level::INFO)),
        )
        .layer(CorsLayer::permissive()) // TODO(#2): Configure CORS properly for production
}

/// Serve the router.
///
/// `into_make_service_with_connect_info` is load-bearing, not boilerplate.
/// `handlers::process_text` extracts `ConnectInfo<SocketAddr>` to get the client
/// address for per-IP rate limiting. `axum::serve(listener, router)` accepts a bare
/// `Router` and inserts no connection info, so that extractor failed on EVERY request
/// and `POST /process` -- the only endpoint with business logic -- returned 500 for
/// the entire life of the service. Nothing caught it because no test built the real
/// router or bound a real socket.
pub async fn serve(
    listener: tokio::net::TcpListener,
    app: Router,
    shutdown: impl std::future::Future<Output = ()> + Send + 'static,
) -> ReflexResult<()> {
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<std::net::SocketAddr>(),
    )
    .with_graceful_shutdown(shutdown)
    .await
    .map_err(|e| ReflexError::Internal(format!("Server error: {}", e)))
}

/// Health check endpoint
///
/// Returns basic service health information including version and uptime.
async fn health_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let uptime = state.start_time.elapsed().as_secs();

    let response = HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        uptime_seconds: uptime,
    };

    (StatusCode::OK, Json(response))
}

/// Readiness check endpoint
///
/// Returns service readiness status including dependency checks.
async fn readiness_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    // Check Redis connectivity
    let redis_ready = match state.redis.health_check().await {
        Ok(_) => true,
        Err(e) => {
            tracing::warn!("Redis readiness check failed: {}", e);
            false
        }
    };

    let config_ready = true; // Config is always ready if we got here

    let all_ready = redis_ready && config_ready;

    let response = ReadinessResponse {
        status: if all_ready { "ready" } else { "not_ready" }.to_string(),
        ready: all_ready,
        checks: ReadinessChecks {
            redis: redis_ready,
            config: config_ready,
        },
    };

    let status = if all_ready {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (status, Json(response))
}

/// Metrics endpoint
///
/// Returns Prometheus-compatible metrics.
async fn metrics_handler(State(_state): State<Arc<AppState>>) -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();

    match encoder.encode_to_string(&metric_families) {
        Ok(metrics) => (StatusCode::OK, metrics),
        Err(e) => {
            tracing::error!("Failed to encode metrics: {}", e);
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "# Error encoding metrics\n".to_string(),
            )
        }
    }
}

/// Parse log level string to tracing Level
fn parse_log_level(level: &str) -> Level {
    match level.to_lowercase().as_str() {
        "trace" => Level::TRACE,
        "debug" => Level::DEBUG,
        "info" => Level::INFO,
        "warn" => Level::WARN,
        "error" => Level::ERROR,
        _ => Level::INFO,
    }
}

/// Graceful shutdown signal handler
///
/// Listens for SIGTERM (Docker/K8s) and SIGINT (Ctrl+C) signals.
async fn shutdown_signal() {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("Failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {
            tracing::info!("Received Ctrl+C signal, initiating graceful shutdown");
        }
        _ = terminate => {
            tracing::info!("Received SIGTERM signal, initiating graceful shutdown");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Regression test for the `/process` routing defect.
    ///
    /// This binds a REAL socket and drives the request through the same `serve()`
    /// the binary uses, because the defect lived in `serve()` and nowhere else.
    /// A `Router::oneshot` test could not have caught it: oneshot never establishes
    /// a connection, so `ConnectInfo` is absent there too, and such a test either
    /// fails for the wrong reason or -- if it hand-builds its own router -- passes
    /// while production returns 500 on every request.
    ///
    /// Before the fix this asserted 500 with an extractor-rejection body. After it,
    /// any status other than 500 proves `ConnectInfo` was inserted, since that is the
    /// only thing that failed before the handler's own logic ran.
    #[tokio::test]
    #[ignore = "requires Redis on localhost:6379"]
    async fn process_endpoint_receives_connect_info() {
        let config = Config::from_env().expect("default config should load");
        let redis_client = Arc::new(RedisClient::new(config.redis.clone()).expect("redis client"));

        let state = Arc::new(AppState {
            config: Arc::new(config),
            redis: (*redis_client).clone(),
            pii_detector: Arc::new(PIIDetector::new(PIIConfig {
                pattern_set: PatternSet::Standard,
                enable_validation: true,
                enable_context: false,
            })),
            injection_detector: Arc::new(InjectionDetector::new(InjectionConfig {
                detection_mode: DetectionMode::Standard,
                enable_context_analysis: true,
                enable_entropy_check: true,
                severity_threshold: Severity::Low,
            })),
            cache: Arc::new(RedisCache::new(redis_client.clone())),
            rate_limiter: Arc::new(RedisRateLimiter::new(redis_client.clone())),
            start_time: std::time::Instant::now(),
        });

        // Port 0 lets the OS choose, so the test never collides with a running service.
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind ephemeral port");
        let addr = listener.local_addr().expect("local addr");

        let (tx, rx) = tokio::sync::oneshot::channel::<()>();
        let server = tokio::spawn(async move {
            serve(listener, build_router(state), async {
                let _ = rx.await;
            })
            .await
        });

        let response = reqwest::Client::new()
            .post(format!("http://{addr}/process"))
            .json(&serde_json::json!({
                "text": "a benign request with no PII and no injection",
                "use_cache": false
            }))
            .send()
            .await
            .expect("request should reach the server");

        let status = response.status();
        let body = response.text().await.unwrap_or_default();

        let _ = tx.send(());
        let _ = server.await;

        assert_ne!(
            status.as_u16(),
            500,
            "POST /process returned 500. If the body mentions ConnectInfo or a missing \
             extension, `serve()` has stopped calling into_make_service_with_connect_info \
             and every request is failing again. Body: {body}"
        );
    }

    #[test]
    fn test_parse_log_level() {
        assert!(matches!(parse_log_level("trace"), Level::TRACE));
        assert!(matches!(parse_log_level("DEBUG"), Level::DEBUG));
        assert!(matches!(parse_log_level("info"), Level::INFO));
        assert!(matches!(parse_log_level("WARN"), Level::WARN));
        assert!(matches!(parse_log_level("error"), Level::ERROR));
        assert!(matches!(parse_log_level("invalid"), Level::INFO));
    }
}
