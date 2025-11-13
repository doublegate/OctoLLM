/// OpenTelemetry Instrumentation for OctoLLM Reflex Layer (Rust)
///
/// This module configures distributed tracing with Jaeger using OpenTelemetry.
/// Automatically instruments Axum handlers and provides custom span creation.
///
/// # Usage
///
/// ```rust
/// use crate::telemetry::init_telemetry;
///
/// // Initialize at application startup
/// init_telemetry("reflex-layer", "production").await;
/// ```
///
/// # Environment Variables
///
/// - `JAEGER_ENDPOINT`: Jaeger collector endpoint (default: http://jaeger-collector.octollm-monitoring.svc.cluster.local:4317)
/// - `OTEL_SAMPLING_RATE`: Sampling rate 0.0-1.0 (default: 0.10 for prod, 1.0 for dev)
/// - `ENVIRONMENT`: dev/staging/prod (default: dev)

use opentelemetry::{
    global,
    sdk::{
        export::trace::stdout,
        propagation::TraceContextPropagator,
        trace::{self, RandomIdGenerator, Sampler},
        Resource,
    },
    KeyValue,
};
use opentelemetry_otlp::WithExportConfig;
use std::env;
use tracing_subscriber::{layer::SubscriberExt, Registry};

/// Initialize OpenTelemetry tracing with Jaeger exporter
///
/// # Arguments
///
/// * `service_name` - Name of the service (e.g., "reflex-layer")
/// * `environment` - Deployment environment (dev/staging/prod)
///
/// # Example
///
/// ```rust
/// init_telemetry("reflex-layer", "production").await;
/// ```
pub async fn init_telemetry(service_name: &str, environment: &str) {
    // Get configuration from environment
    let jaeger_endpoint = env::var("JAEGER_ENDPOINT").unwrap_or_else(|_| {
        "http://jaeger-collector.octollm-monitoring.svc.cluster.local:4317".to_string()
    });

    // Set sampling rate based on environment
    let sampling_rate: f64 = env::var("OTEL_SAMPLING_RATE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or_else(|| if environment == "dev" { 1.0 } else { 0.10 });

    // Create resource with service metadata
    let resource = Resource::new(vec![
        KeyValue::new("service.name", service_name.to_string()),
        KeyValue::new("service.namespace", "octollm"),
        KeyValue::new(
            "service.instance.id",
            env::var("HOSTNAME").unwrap_or_else(|_| "unknown".to_string()),
        ),
        KeyValue::new("deployment.environment", environment.to_string()),
        KeyValue::new(
            "service.version",
            env::var("APP_VERSION").unwrap_or_else(|_| "0.9.0".to_string()),
        ),
    ]);

    // Configure tracer provider with sampling
    let sampler = Sampler::ParentBased(Box::new(Sampler::TraceIdRatioBased(sampling_rate)));

    // Configure OTLP exporter to Jaeger
    let tracer = opentelemetry_otlp::new_pipeline()
        .tracing()
        .with_exporter(
            opentelemetry_otlp::new_exporter()
                .tonic()
                .with_endpoint(jaeger_endpoint),
        )
        .with_trace_config(
            trace::config()
                .with_sampler(sampler)
                .with_id_generator(RandomIdGenerator::default())
                .with_resource(resource),
        )
        .install_batch(opentelemetry::runtime::Tokio)
        .expect("Failed to initialize tracer");

    // Set global tracer provider
    global::set_text_map_propagator(TraceContextPropagator::new());

    // Create tracing layer
    let telemetry_layer = tracing_opentelemetry::layer().with_tracer(tracer);

    // Combine with tracing subscriber
    let subscriber = Registry::default().with(telemetry_layer);

    tracing::subscriber::set_global_default(subscriber)
        .expect("Failed to set subscriber");

    println!(
        "✓ OpenTelemetry initialized: {} (sampling: {:.0}%)",
        service_name,
        sampling_rate * 100.0
    );
}

/// Create a custom span for tracing operations
///
/// # Example
///
/// ```rust
/// use tracing::{info_span, instrument};
///
/// #[instrument]
/// async fn detect_pii(input: &str) -> bool {
///     // PII detection logic
///     let span = info_span!("pii_detection", input_length = input.len());
///     let _enter = span.enter();
///
///     // Add custom attributes
///     tracing::info!(pii_detected = false, redaction_count = 0);
///
///     false
/// }
/// ```

// Example usage in Axum handlers:
//
// use axum::{routing::post, Router};
// use tower_http::trace::TraceLayer;
//
// let app = Router::new()
//     .route("/detect-pii", post(detect_pii_handler))
//     .layer(TraceLayer::new_for_http());
