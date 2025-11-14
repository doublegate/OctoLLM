//! OctoLLM Reflex Layer
//!
//! Fast preprocessing layer for common patterns without LLM involvement.

mod config;
mod error;
mod redis_client;

use axum::{
    extract::State,
    http::StatusCode,
    response::IntoResponse,
    routing::get,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::signal;
use tower_http::{
    cors::CorsLayer,
    trace::{DefaultMakeSpan, DefaultOnResponse, TraceLayer},
};
use tracing::Level;

use crate::config::Config;
use crate::error::{ReflexError, ReflexResult};
use crate::redis_client::RedisClient;

/// Application state shared across all handlers
#[derive(Clone)]
struct AppState {
    config: Arc<Config>,
    redis: RedisClient,
    start_time: std::time::Instant,
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

    // Create Redis client
    let redis_client = RedisClient::new(config.redis.clone())?;
    tracing::info!("Redis client initialized");

    // Verify Redis connectivity
    match redis_client.health_check().await {
        Ok(_) => tracing::info!("Redis connection verified"),
        Err(e) => {
            tracing::warn!("Redis health check failed: {}. Continuing without Redis", e);
            // Note: In production, you might want to fail fast here
        }
    }

    // Create application state
    let state = AppState {
        config: Arc::new(config.clone()),
        redis: redis_client,
        start_time: std::time::Instant::now(),
    };

    // Build router with middleware
    let app = Router::new()
        // Health and readiness endpoints
        .route("/health", get(health_handler))
        .route("/ready", get(readiness_handler))
        // Metrics endpoint (placeholder for now)
        .route("/metrics", get(metrics_handler))
        // Future endpoints
        // .route("/process", post(process_handler))
        .with_state(state)
        // Middleware stack (applied in reverse order)
        .layer(
            TraceLayer::new_for_http()
                .make_span_with(DefaultMakeSpan::new().level(Level::INFO))
                .on_response(DefaultOnResponse::new().level(Level::INFO)),
        )
        .layer(CorsLayer::permissive()); // TODO(#2): Configure CORS properly for production

    // Create TCP listener
    let addr = format!("{}:{}", config.server.host, config.server.port);
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .map_err(|e| ReflexError::Internal(format!("Failed to bind to {}: {}", addr, e)))?;

    tracing::info!("Reflex layer listening on {}", addr);
    tracing::info!("Configuration loaded: {:?}", config);

    // Start server with graceful shutdown
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .map_err(|e| ReflexError::Internal(format!("Server error: {}", e)))?;

    tracing::info!("Reflex layer shutdown complete");
    Ok(())
}

/// Health check endpoint
///
/// Returns basic service health information including version and uptime.
async fn health_handler(State(state): State<AppState>) -> impl IntoResponse {
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
async fn readiness_handler(State(state): State<AppState>) -> impl IntoResponse {
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

/// Metrics endpoint (placeholder)
///
/// Returns Prometheus-compatible metrics.
async fn metrics_handler(State(_state): State<AppState>) -> impl IntoResponse {
    // TODO(#4): Implement Prometheus metrics collection
    (StatusCode::OK, "# Placeholder for Prometheus metrics\n")
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
